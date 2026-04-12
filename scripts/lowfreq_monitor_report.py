#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.daemon_config import get_daemon_config
from ifa_data_platform.lowfreq.daemon_health import get_daemon_health

LA = ZoneInfo("America/Los_Angeles")
CN = ZoneInfo("Asia/Shanghai")


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
        return f"matched window: {matched.window_type} / {matched.group_name}"
    return "idle / waiting"


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
            SELECT dataset_name,status,started_at,completed_at,records_processed,error_message
            FROM ifa2.lowfreq_runs
            ORDER BY started_at DESC NULLS LAST, created_at DESC NULLS LAST
            LIMIT 120
        """)).mappings().all()
        out["recent_runs"] = [dict(r) for r in recent_runs]

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

    recent_runs = snap["recent_runs"]
    recent_completed = [r for r in recent_runs if r.get("completed_at")]
    last_run = recent_completed[0] if recent_completed else None

    latest_by_dataset = {}
    for r in recent_runs:
        ds = r["dataset_name"]
        if ds not in latest_by_dataset:
            latest_by_dataset[ds] = r

    success = sum(1 for r in latest_by_dataset.values() if r["status"] == "succeeded")
    failed = sum(1 for r in latest_by_dataset.values() if r["status"] == "failed")
    skipped = sum(1 for r in latest_by_dataset.values() if r["status"] == "skipped")

    datasets_latest = sorted(latest_by_dataset.items(), key=lambda kv: kv[1].get("completed_at") or kv[1].get("started_at") or datetime.min, reverse=True)
    ran_lines = []
    for ds, r in datasets_latest[:12]:
        rp = r.get("records_processed")
        extra = f", Δ={rp}" if rp is not None else ""
        ended = fmt_ts(r.get("completed_at") or r.get("started_at"))
        status = r.get("status")
        if r.get("error_message") and status == "failed":
            err = str(r["error_message"]).strip().replace("\n", " ")[:80]
            ran_lines.append(f"- {ds}: {status}{extra} @ {ended} | {err}")
        else:
            ran_lines.append(f"- {ds}: {status}{extra} @ {ended}")

    blockers = []
    for ds, freshness in sorted(health.dataset_freshness.items()):
        if "failed" in freshness or freshness.startswith("stale") or freshness.startswith("very stale"):
            blockers.append(f"- {ds}: {freshness}")
    for g in snap["group_state"]:
        if g.get("is_degraded") or g.get("in_fallback"):
            blockers.append(
                f"- group {g['group_name']}: degraded={g.get('is_degraded')} fallback={g.get('in_fallback')} retry={g.get('retry_count')}"
            )

    report_lines = [
        f"低频监控报告｜{datetime.now(LA).strftime('%Y-%m-%d %H:%M %Z')}",
        f"daemon 当前状态：{health.status}",
        f"当前窗口判断：{infer_current_window(cfg)}",
        f"上一轮执行时间：{fmt_ts(last_run.get('completed_at') if last_run else None)}",
        f"上一轮/最近样本统计：成功 {success} / 失败 {failed} / 跳过 {skipped}",
        "",
        "最近运行到的 dataset：",
        *(ran_lines or ["- 暂无最近运行记录"]),
        "",
        "group 状态：",
    ]

    for g in snap["group_state"]:
        report_lines.append(
            f"- {g['group_name']}: last_status={g.get('last_status') or '-'}, last_success={fmt_ts(g.get('last_success_at_utc'))}, retry={g.get('retry_count')}, degraded={g.get('is_degraded')}"
        )

    report_lines.extend([
        "",
        "健康结论：" + ("存在异常/需关注" if blockers else "整体可运行"),
        "异常 / blocker：",
        *(blockers[:12] if blockers else ["- 无明显 blocker"]),
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
