#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.daemon_config import get_daemon_config
from ifa_data_platform.lowfreq.daemon_health import get_daemon_health

LA = ZoneInfo("America/Los_Angeles")
CN = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc

DATASET_LABELS = {
    "trade_cal": "交易日历",
    "stock_basic": "A股股票基础名录",
    "index_basic": "指数基础名录",
    "fund_basic_etf": "ETF基础名录",
    "sw_industry_mapping": "申万行业归属映射",
    "company_basic": "上市公司基础信息",
    "name_change": "证券简称/名称变更",
    "new_share": "新股发行/上市信息",
    "stk_managers": "上市公司高管信息",
    "stk_holdernumber": "股东户数",
    "share_float": "流通股本/流通盘变化",
    "announcements": "上市公司公告",
    "news": "新闻快讯",
    "research_reports": "券商研报",
    "investor_qa": "投资者问答",
    "index_weight": "指数成分权重",
    "etf_daily_basic": "ETF日度基础指标",
    "top10_holders": "前十大股东",
    "top10_floatholders": "前十大流通股东",
    "pledge_stat": "股权质押情况",
    "forecast": "业绩预告",
    "margin": "融资融券数据",
    "north_south_flow": "北向/南向资金流",
    "management": "管理层变动",
    "stock_equity_change": "股本/股权结构变化",
}


def dataset_label(name: str) -> str:
    return DATASET_LABELS.get(name, name)


def fmt_ts(ts):
    if not ts:
        return "-"
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(LA).strftime("%Y-%m-%d %H:%M %Z")


def infer_current_window(cfg):
    now_cn = datetime.now(CN).replace(second=0, microsecond=0)
    matched = cfg.get_matching_window(now_cn)
    if matched:
        return {
            "state": "matched_window",
            "label": f"matched window: {matched.window_type} / {matched.group_name}",
            "matched": matched,
            "next_window": matched,
            "now_cn": now_cn,
        }

    next_window = None
    next_dt = None
    for w in cfg.schedule_windows:
        candidate_date = now_cn.date()
        for plus_days in range(0, 8):
            d = candidate_date + timedelta(days=plus_days)
            candidate = datetime.combine(d, datetime.strptime(w.time_str, "%H:%M").time(), tzinfo=w.timezone)
            if w.day_of_week is not None and candidate.weekday() != w.day_of_week:
                continue
            if candidate >= now_cn:
                if next_dt is None or candidate < next_dt:
                    next_dt = candidate
                    next_window = w
                break

    if next_window and next_dt:
        delta = next_dt - now_cn
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return {
            "state": "waiting",
            "label": f"waiting for next window: {next_window.window_type} / {next_window.group_name} in {hours}h {minutes}m",
            "matched": None,
            "next_window": next_window,
            "next_dt": next_dt,
            "now_cn": now_cn,
        }

    return {
        "state": "waiting",
        "label": "idle / waiting",
        "matched": None,
        "next_window": None,
        "now_cn": now_cn,
    }


def get_db_snapshot():
    eng = make_engine()
    out: dict = {}
    with eng.connect() as c:
        group_rows = c.execute(text("""
            SELECT group_name,last_run_at_utc,last_success_at_utc,last_status,retry_count,is_degraded,in_fallback,updated_at_utc
            FROM ifa2.lowfreq_group_state
            ORDER BY group_name
        """)).mappings().all()
        out["group_state"] = [dict(r) for r in group_rows]

        recent_runs = c.execute(text("""
            SELECT dataset_name,status,started_at,completed_at,records_processed,error_message,run_type,dry_run
            FROM ifa2.lowfreq_runs
            ORDER BY COALESCE(completed_at, started_at) DESC NULLS LAST, created_at DESC NULLS LAST
            LIMIT 200
        """)).mappings().all()
        out["recent_runs"] = [dict(r) for r in recent_runs]

        latest_by_dataset = c.execute(text("""
            WITH ranked AS (
              SELECT dataset_name,status,started_at,completed_at,records_processed,error_message,run_type,dry_run,
                     ROW_NUMBER() OVER (
                        PARTITION BY dataset_name
                        ORDER BY COALESCE(completed_at, started_at) DESC NULLS LAST, created_at DESC NULLS LAST
                     ) AS rn
              FROM ifa2.lowfreq_runs
            )
            SELECT dataset_name,status,started_at,completed_at,records_processed,error_message,run_type,dry_run
            FROM ranked
            WHERE rn = 1
            ORDER BY COALESCE(completed_at, started_at) DESC NULLS LAST
        """)).mappings().all()
        out["latest_by_dataset"] = [dict(r) for r in latest_by_dataset]

        latest_counts = c.execute(text("""
            SELECT dataset_name, status, COUNT(*) AS cnt
            FROM ifa2.dataset_versions
            GROUP BY dataset_name, status
            ORDER BY dataset_name, status
        """)).mappings().all()
        out["version_counts"] = [dict(r) for r in latest_counts]

        dataset_latest = c.execute(text("""
            WITH ranked AS (
              SELECT dataset_name,status,is_active,created_at_utc,promoted_at_utc,
                     ROW_NUMBER() OVER (PARTITION BY dataset_name ORDER BY created_at_utc DESC) AS rn
              FROM ifa2.dataset_versions
            )
            SELECT dataset_name,status,is_active,created_at_utc,promoted_at_utc
            FROM ranked WHERE rn=1
            ORDER BY created_at_utc DESC NULLS LAST
            LIMIT 80
        """)).mappings().all()
        out["dataset_latest_versions"] = [dict(r) for r in dataset_latest]
    return out


def build_report():
    cfg = get_daemon_config()
    health = get_daemon_health(cfg)
    snap = get_db_snapshot()
    window_info = infer_current_window(cfg)

    recent_runs = snap["recent_runs"]
    latest_dataset_rows = snap["latest_by_dataset"]

    latest_by_dataset = {r["dataset_name"]: r for r in latest_dataset_rows}
    completed_rows = [r for r in recent_runs if r.get("completed_at")]
    last_run = completed_rows[0] if completed_rows else None

    success = sum(1 for r in latest_by_dataset.values() if r["status"] == "succeeded")
    failed = sum(1 for r in latest_by_dataset.values() if r["status"] == "failed")
    skipped = sum(1 for r in latest_by_dataset.values() if r["status"] == "skipped")

    datasets_latest = sorted(
        latest_by_dataset.items(),
        key=lambda kv: kv[1].get("completed_at") or kv[1].get("started_at") or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )

    ran_lines = []
    for ds, r in datasets_latest[:12]:
        label = dataset_label(ds)
        rp = r.get("records_processed")
        ended = fmt_ts(r.get("completed_at") or r.get("started_at"))
        status = r.get("status")
        if status == "succeeded":
            if rp is not None:
                ran_lines.append(f"- {label}：已更新，新增/处理 {rp} 条 @ {ended}")
            else:
                ran_lines.append(f"- {label}：已更新 @ {ended}")
        elif status == "skipped":
            ran_lines.append(f"- {label}：本轮跳过 @ {ended}")
        elif r.get("error_message") and status == "failed":
            err = str(r["error_message"]).strip().replace("\n", " ")[:100]
            ran_lines.append(f"- {label}：运行失败 @ {ended} | {err}")
        else:
            ran_lines.append(f"- {label}：状态 {status} @ {ended}")

    waiting_lines = []
    blocker_lines = []

    now_utc_dt = datetime.now(UTC)
    for ds, freshness in sorted(health.dataset_freshness.items()):
        latest = latest_by_dataset.get(ds)
        status = latest.get("status") if latest else None
        ts = (latest or {}).get("completed_at") or (latest or {}).get("started_at")
        age_days = None
        if ts is not None:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            else:
                ts = ts.astimezone(UTC)
            age_days = (now_utc_dt - ts).total_seconds() / 86400

        label = dataset_label(ds)
        if status == "failed":
            blocker_lines.append(f"- {label}：最新一次运行失败（{freshness}）")
        elif freshness == "no run recorded":
            blocker_lines.append(f"- {label}：没有任何运行记录")
        elif freshness.startswith("very stale"):
            waiting_lines.append(f"- {label}：长期未更新（{freshness}），更像慢频/周频等待，需结合窗口判断")
        elif freshness.startswith("stale"):
            waiting_lines.append(f"- {label}：待下轮更新（{freshness}），当前更像等待下一窗口，不单独视为故障")

    for g in snap["group_state"]:
        if g.get("is_degraded") or g.get("in_fallback"):
            blocker_lines.append(
                f"- group {g['group_name']}: degraded={g.get('is_degraded')} fallback={g.get('in_fallback')} retry={g.get('retry_count')}"
            )

    daemon_summary = "健康"
    if health.status == "stale":
        if window_info["state"] == "waiting":
            daemon_summary = "进程/链路未见新 loop 记录，但当前处于等待下一窗口；这更像监控口径偏严，不等同于系统故障"
        else:
            daemon_summary = "状态偏陈旧，需结合当前窗口进一步确认"
    elif health.status == "no_runs":
        daemon_summary = "未见有效运行记录"

    report_lines = [
        f"低频监控报告｜{datetime.now(LA).strftime('%Y-%m-%d %H:%M %Z')}",
        f"daemon 当前状态：{health.status}（{daemon_summary}）",
        f"当前窗口状态：{window_info['label']}",
        f"最近一次真实执行时间：{fmt_ts(last_run.get('completed_at') if last_run else None)}",
        f"最近样本摘要：成功 {success} / 失败 {failed} / 跳过 {skipped}",
        "",
        "本轮 / 最近一轮更新了什么数据：",
        *(ran_lines or ["- 暂无最近运行记录"]),
        "",
        "group 状态：",
    ]

    for g in snap["group_state"]:
        report_lines.append(
            f"- {g['group_name']}: 最近状态={g.get('last_status') or '-'}, 最近成功={fmt_ts(g.get('last_success_at_utc'))}, retry={g.get('retry_count')}, degraded={g.get('is_degraded')}"
        )

    report_lines.extend([
        "",
        "合理等待 / 口径提示：",
        *(waiting_lines[:12] if waiting_lines else ["- 当前没有明显的“仅因等待窗口而显得陈旧”的项目"]),
        "",
        "真正异常 / blocker：",
        *(blocker_lines[:12] if blocker_lines else ["- 无明显 blocker"]),
    ])
    return "\n".join(report_lines)


def send_telegram(text_msg: str, target: str, account: str = "main"):
    cmd = [
        "/opt/homebrew/opt/node@24/bin/node",
        "/opt/homebrew/lib/node_modules/openclaw/openclaw.mjs",
        "message", "send",
        "--channel", "telegram",
        "--account", account,
        "--target", target,
        "--message", text_msg,
        "--json",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--target", default="1628724839")
    ap.add_argument("--account", default="main")
    args = ap.parse_args()

    report = build_report()
    print(report)
    if args.send:
        res = send_telegram(report, args.target, args.account)
        print("\n=== send_result ===")
        print(res.stdout.strip() or res.stderr.strip())


if __name__ == "__main__":
    main()
