#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp"
ENGINE = create_engine(DB_URL)
OUT_JSON = Path("artifacts/db_reality_snapshot_v2_20260424.json")
OUT_MD = Path("docs/DB_REALITY_SNAPSHOT_V2_2026-04-24.md")

TABLES: dict[str, list[dict[str, Any]]] = {
    "highfreq": [
        {"table": "highfreq_stock_1m_working", "time_col": "trade_time", "sample_sql": 'select ts_code, trade_time, open, high, low, close, vol, amount from ifa2.highfreq_stock_1m_working order by trade_time desc, ts_code limit 3'},
        {"table": "highfreq_open_auction_working", "time_col": "trade_date", "sample_sql": 'select ts_code, trade_date, open, high, low, close, vol, amount, vwap from ifa2.highfreq_open_auction_working order by trade_date desc, ts_code limit 3'},
        {"table": "highfreq_event_stream_working", "time_col": "event_time", "sample_sql": 'select event_type, symbol, event_time, title, source, url from ifa2.highfreq_event_stream_working order by event_time desc limit 3'},
        {"table": "highfreq_sector_breadth_working", "time_col": "trade_time", "sample_sql": 'select trade_time, sector_code, up_count, down_count, limit_up_count, strong_count, spread_ratio from ifa2.highfreq_sector_breadth_working order by trade_time desc, sector_code limit 3'},
        {"table": "highfreq_sector_heat_working", "time_col": "trade_time", "sample_sql": 'select trade_time, sector_code, heat_score from ifa2.highfreq_sector_heat_working order by trade_time desc, sector_code limit 3'},
        {"table": "highfreq_leader_candidate_working", "time_col": "trade_time", "sample_sql": 'select trade_time, symbol, candidate_score, confirmation_state, continuation_health from ifa2.highfreq_leader_candidate_working order by trade_time desc, symbol limit 3'},
        {"table": "highfreq_intraday_signal_state_working", "time_col": "trade_time", "sample_sql": 'select trade_time, scope_key, emotion_stage, validation_state, risk_opportunity_state, turnover_progress, amount_progress from ifa2.highfreq_intraday_signal_state_working order by trade_time desc limit 3'},
    ],
    "midfreq": [
        {"table": "limit_up_detail_history", "time_col": "trade_date", "sample_sql": 'select ts_code, trade_date, "limit", pre_limit, created_at from ifa2.limit_up_detail_history order by trade_date desc, ts_code limit 3'},
        {"table": "dragon_tiger_list_history", "time_col": "trade_date", "sample_sql": 'select ts_code, trade_date, buy_amount, sell_amount, net_amount from ifa2.dragon_tiger_list_history order by trade_date desc, ts_code limit 3'},
        {"table": "sector_performance_history", "time_col": "trade_date", "sample_sql": 'select sector_code, sector_name, trade_date, close, pct_chg, turnover_rate from ifa2.sector_performance_history order by trade_date desc, sector_code limit 3'},
        {"table": "northbound_flow_history", "time_col": "trade_date", "sample_sql": 'select trade_date, north_money, north_bal, north_buy, north_sell from ifa2.northbound_flow_history order by trade_date desc limit 3'},
        {"table": "equity_daily_bar_history", "time_col": "trade_date", "sample_sql": 'select ts_code, trade_date, open, high, low, close, vol, amount from ifa2.equity_daily_bar_history order by trade_date desc, ts_code limit 3'},
        {"table": "etf_daily_bar_history", "time_col": "trade_date", "sample_sql": 'select ts_code, trade_date, open, high, low, close, vol, amount from ifa2.etf_daily_bar_history order by trade_date desc, ts_code limit 3'},
        {"table": "midfreq_datasets", "time_col": None, "sample_sql": 'select dataset_name, source_name, enabled, description from ifa2.midfreq_datasets order by dataset_name limit 5'},
    ],
    "lowfreq": [
        {"table": "announcements_history", "time_col": "ann_date", "sample_sql": 'select ann_date, ts_code, title, url, rec_time from ifa2.announcements_history order by ann_date desc, rec_time desc nulls last limit 3'},
        {"table": "news_history", "time_col": "datetime", "sample_sql": 'select datetime, source, classify, title, url from ifa2.news_history order by datetime desc limit 3'},
        {"table": "research_reports_history", "time_col": "trade_date", "sample_sql": 'select trade_date, coalesce(ts_code,\'(null)\') as ts_code, title, report_type, author, inst_csname from ifa2.research_reports_history order by trade_date desc limit 3'},
        {"table": "investor_qa_history", "time_col": "trade_date", "sample_sql": 'select trade_date, ts_code, pub_time, length(q) as q_len, length(a) as a_len from ifa2.investor_qa_history order by trade_date desc, pub_time desc limit 3'},
        {"table": "trade_cal_history", "time_col": "cal_date", "sample_sql": 'select exchange, cal_date, is_open, pretrade_date from ifa2.trade_cal_history order by cal_date desc limit 3'},
        {"table": "stock_basic_history", "time_col": "created_at", "sample_sql": 'select ts_code, symbol, name, industry, list_status, list_date from ifa2.stock_basic_history order by created_at desc limit 3'},
        {"table": "lowfreq_datasets", "time_col": None, "sample_sql": 'select dataset_name, source_name, enabled, description from ifa2.lowfreq_datasets order by dataset_name limit 5'},
    ],
    "archive_v2": [
        {"table": "ifa_archive_announcements_daily", "time_col": "business_date", "sample_sql": 'select business_date, row_key, ts_code, title, url, rec_time from ifa2.ifa_archive_announcements_daily order by business_date desc, rec_time desc nulls last limit 3'},
        {"table": "ifa_archive_news_daily", "time_col": "business_date", "sample_sql": 'select business_date, row_key, src, title, url, news_time from ifa2.ifa_archive_news_daily order by business_date desc, news_time desc nulls last limit 3'},
        {"table": "ifa_archive_research_reports_daily", "time_col": "business_date", "sample_sql": 'select business_date, row_key, ts_code, title, report_type, trade_date from ifa2.ifa_archive_research_reports_daily order by business_date desc, trade_date desc nulls last limit 3'},
        {"table": "ifa_archive_investor_qa_daily", "time_col": "business_date", "sample_sql": 'select business_date, row_key, ts_code, pub_time, trade_date from ifa2.ifa_archive_investor_qa_daily order by business_date desc, pub_time desc nulls last limit 3'},
        {"table": "ifa_archive_equity_daily_daily", "time_col": "business_date", "sample_sql": 'select business_date, row_key, ts_code, trade_date, close, vol, amount from ifa2.ifa_archive_equity_daily_daily order by business_date desc, trade_date desc, ts_code limit 3'},
        {"table": "ifa_archive_runs", "time_col": "started_at", "sample_sql": 'select run_id, trigger_source, status, started_at, completed_at from ifa2.ifa_archive_runs order by started_at desc limit 5'},
        {"table": "ifa_archive_run_items", "time_col": "business_date", "sample_sql": 'select run_id, business_date, family_name, status, rows_written, family_observed_rows from ifa2.ifa_archive_run_items order by business_date desc, family_name limit 5'},
        {"table": "ifa_archive_completeness", "time_col": "business_date", "sample_sql": 'select business_date, family_name, coverage_scope, status, last_run_id from ifa2.ifa_archive_completeness order by business_date desc, family_name limit 5'},
    ],
    "focus": [
        {"table": "focus_lists", "time_col": "updated_at", "sample_sql": 'select id, owner_type, owner_id, list_type, name, asset_type, is_active, updated_at from ifa2.focus_lists order by updated_at desc, name limit 5'},
        {"table": "focus_list_items", "time_col": "updated_at", "sample_sql": 'select list_id, symbol, name, asset_category, priority, source, is_active, updated_at from ifa2.focus_list_items order by updated_at desc, priority, symbol limit 5'},
        {"table": "focus_list_rules", "time_col": "updated_at", "sample_sql": 'select list_id, rule_key, rule_value, updated_at from ifa2.focus_list_rules order by updated_at desc, rule_key limit 5'},
    ],
}

SPECIAL_CHECKS = {
    "news_related_nonempty": {
        "news_history": 'select count(*) from ifa2.news_history',
        "announcements_history": 'select count(*) from ifa2.announcements_history',
        "research_reports_history": 'select count(*) from ifa2.research_reports_history',
        "investor_qa_history": 'select count(*) from ifa2.investor_qa_history',
    },
    "focus_key_focus_lists": """
        select list_type, count(*) as list_count
        from ifa2.focus_lists
        where list_type in ('focus', 'key_focus')
        group by list_type
        order by list_type
    """,
    "focus_named_examples": """
        select name, list_type, asset_type, is_active
        from ifa2.focus_lists
        where list_type in ('focus', 'key_focus')
        order by updated_at desc nulls last, name
        limit 20
    """,
}


def scalar(conn, sql: str, params: dict[str, Any] | None = None) -> Any:
    return conn.execute(text(sql), params or {}).scalar_one()


def rows(conn, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(text(sql), params or {}).mappings().all()]


def table_exists(conn, table: str) -> bool:
    return bool(scalar(conn, "select count(*) from information_schema.tables where table_schema='ifa2' and table_name=:t", {"t": table}))


def latest_bounds(conn, table: str, time_col: str | None) -> dict[str, Any] | None:
    if not time_col:
        return None
    min_v, max_v = conn.execute(text(f'select min("{time_col}"), max("{time_col}") from ifa2."{table}"')).one()
    return {"earliest": min_v, "latest": max_v}


def actual_columns(conn, table: str) -> list[str]:
    return [
        r[0]
        for r in conn.execute(
            text("select column_name from information_schema.columns where table_schema='ifa2' and table_name=:t order by ordinal_position"),
            {"t": table},
        ).fetchall()
    ]


def inspect_table(conn, spec: dict[str, Any]) -> dict[str, Any]:
    table = spec["table"]
    exists = table_exists(conn, table)
    out: dict[str, Any] = {"table": table, "exists": exists}
    if not exists:
        out["non_empty"] = False
        return out
    cols = actual_columns(conn, table)
    row_count = scalar(conn, f'select count(*) from ifa2."{table}"')
    out["columns"] = cols
    out["row_count"] = int(row_count)
    out["non_empty"] = row_count > 0
    out["time_bounds"] = latest_bounds(conn, table, spec.get("time_col")) if spec.get("time_col") in cols else None
    if row_count > 0:
        try:
            out["sample_rows"] = rows(conn, spec["sample_sql"])
        except Exception as exc:
            conn.rollback()
            select_cols = ", ".join(f'"{c}"' for c in cols[: min(6, len(cols))])
            fallback_sql = f'select {select_cols} from ifa2."{table}" limit 3'
            out["sample_error"] = f"{type(exc).__name__}: {exc}"
            out["sample_rows"] = rows(conn, fallback_sql)
    else:
        out["sample_rows"] = []
    return out


def markdown_table(items: list[dict[str, Any]]) -> list[str]:
    lines = ["| Table | Exists | Row Count | Non-empty | Earliest | Latest |", "|---|---:|---:|---:|---|---|"]
    for item in items:
        tb = item.get("time_bounds") or {}
        lines.append(
            f"| `{item['table']}` | {'yes' if item.get('exists') else 'no'} | {item.get('row_count', 0)} | {'yes' if item.get('non_empty') else 'no'} | {tb.get('earliest', '-')} | {tb.get('latest', '-')} |"
        )
    return lines


def main() -> None:
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "db_url": DB_URL,
        "scope": "V2-R0-002 DB reality probe re-verification",
        "groups": {},
        "special_checks": {},
    }

    with ENGINE.connect() as conn:
        for group, specs in TABLES.items():
            payload["groups"][group] = [inspect_table(conn, spec) for spec in specs]

        payload["special_checks"]["news_related_nonempty"] = {
            name: int(scalar(conn, sql)) for name, sql in SPECIAL_CHECKS["news_related_nonempty"].items()
        }
        payload["special_checks"]["focus_key_focus_lists"] = rows(conn, SPECIAL_CHECKS["focus_key_focus_lists"])
        payload["special_checks"]["focus_named_examples"] = rows(conn, SPECIAL_CHECKS["focus_named_examples"])

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    md: list[str] = [
        "# DB Reality Snapshot V2 — 2026-04-24",
        "",
        "Task: `V2-R0-002 DB reality probe 复核与快照固化`",
        "",
        f"Evidence JSON: `{OUT_JSON}`",
        "",
        "## Executive Summary",
        "",
    ]

    news = payload["special_checks"]["news_related_nonempty"]
    focus_counts = payload["special_checks"]["focus_key_focus_lists"]
    md.extend([
        f"- `highfreq / midfreq / lowfreq / archive_v2 / focus` probe completed against live `ifa2` schema.",
        f"- News-related families non-empty status: announcements={news['announcements_history']}, news={news['news_history']}, research_reports={news['research_reports_history']}, investor_qa={news['investor_qa_history']}",
        f"- Focus/key-focus list counts: {json.dumps(focus_counts, ensure_ascii=False)}",
        "",
    ])

    for group, items in payload["groups"].items():
        md.append(f"## {group}")
        md.append("")
        md.extend(markdown_table(items))
        md.append("")

    md.extend([
        "## Focus / Key-Focus Named Examples",
        "",
        "```json",
        json.dumps(payload["special_checks"]["focus_named_examples"], ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## Notes",
        "",
        "- This is a read-only reality probe; no collector expansion and no collection-layer refactor were performed.",
        "- `exists=yes` means physical table exists in `ifa2`; `non-empty=yes` means row count > 0 at probe time.",
    ])

    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps({"json": str(OUT_JSON), "md": str(OUT_MD)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
