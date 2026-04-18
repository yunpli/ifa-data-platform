from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import text

from ifa_data_platform.archive_v2.db import engine, ensure_schema

NON_COMPLETED_STATUSES = {'partial', 'incomplete', 'retry_needed', 'missing'}
CRITICAL_FAMILIES = {'equity_daily', 'index_daily', 'etf_daily', 'non_equity_daily', 'macro_daily', 'limit_up_down_status_daily'}
HIGHFREQ_FAMILIES = {
    'highfreq_event_stream_daily', 'highfreq_limit_event_stream_daily', 'highfreq_sector_breadth_daily',
    'highfreq_sector_heat_daily', 'highfreq_leader_candidate_daily', 'highfreq_intraday_signal_state_daily',
}


def infer_reason_code(status: str, detail_text: str | None) -> str:
    detail = (detail_text or '').lower()
    if 'not archive-v2 worthy' in detail:
        return 'not_archive_worthy'
    if 'unsupported family group' in detail:
        return 'unsupported_family'
    if 'source returned no rows' in detail or 'source/history returned no rows' in detail or 'no macro snapshot rows' in detail:
        return 'source_empty'
    if status == 'retry_needed':
        return 'retry_needed'
    if status == 'missing':
        return 'missing_archive_state'
    if status == 'partial':
        return 'partial_result'
    if status == 'incomplete':
        return 'incomplete_result'
    return 'unknown'


def compute_priority(family_name: str, status: str, retry_count: int, reason_code: str) -> int:
    base = {
        'retry_needed': 90,
        'missing': 85,
        'partial': 75,
        'incomplete': 65,
    }.get(status, 50)
    if family_name in CRITICAL_FAMILIES:
        base += 10
    elif family_name in HIGHFREQ_FAMILIES:
        base += 5
    if reason_code == 'not_archive_worthy':
        base = 20
    if retry_count >= 3:
        base += min(15, retry_count * 2)
    return min(base, 100)


def compute_urgency(priority: int, retry_count: int) -> str:
    if priority >= 90 or retry_count >= 5:
        return 'critical'
    if priority >= 75 or retry_count >= 3:
        return 'high'
    if priority >= 55:
        return 'normal'
    return 'low'


def compute_escalation_level(retry_count: int, priority: int) -> int:
    if priority >= 90 or retry_count >= 5:
        return 3
    if priority >= 75 or retry_count >= 3:
        return 2
    if retry_count >= 1:
        return 1
    return 0


def compute_retry_after(status: str, retry_count: int, reason_code: str) -> datetime | None:
    if reason_code == 'not_archive_worthy':
        return datetime.now(timezone.utc) + timedelta(days=7)
    base_minutes = {
        'retry_needed': 15,
        'missing': 30,
        'partial': 90,
        'incomplete': 180,
    }.get(status, 240)
    multiplier = min(2 ** max(retry_count - 1, 0), 16)
    return datetime.now(timezone.utc) + timedelta(minutes=base_minutes * multiplier)


def build_repair_state(existing_row: dict[str, Any] | None, family_name: str, status: str, detail_text: str | None) -> dict[str, Any]:
    previous_retries = int(existing_row['retry_count']) if existing_row and existing_row.get('retry_count') is not None else 0
    retry_count = previous_retries + 1
    reason_code = infer_reason_code(status, detail_text)
    priority = compute_priority(family_name, status, retry_count, reason_code)
    urgency = compute_urgency(priority, retry_count)
    escalation_level = compute_escalation_level(retry_count, priority)
    retry_after = compute_retry_after(status, retry_count, reason_code)
    return {
        'reason_code': reason_code,
        'priority': priority,
        'urgency': urgency,
        'retry_count': retry_count,
        'escalation_level': escalation_level,
        'retry_after': retry_after,
        'last_error': detail_text,
    }


def fetch_rows(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ensure_schema()
    with engine.begin() as conn:
        return [dict(r) for r in conn.execute(text(sql), params or {}).mappings().all()]


def recent_runs(limit: int = 10) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_recent_runs_v
        order by start_time desc
        limit :limit
        """,
        {'limit': limit},
    )


def repair_backlog(limit: int = 20) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_repair_backlog_v
        order by priority desc, coalesce(retry_after, now()) asc, updated_at asc
        limit :limit
        """,
        {'limit': limit},
    )


def gaps(days: int = 14) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_gap_summary_v
        where business_date >= current_date - cast(:days as integer)
        order by business_date desc, priority desc nulls last, family_name
        """,
        {'days': days},
    )


def family_health(limit: int = 30) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_family_health_v
        order by non_completed_dates desc, latest_business_date desc, family_name
        limit :limit
        """,
        {'limit': limit},
    )


def date_health(days: int = 14) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_date_health_v
        where business_date >= current_date - cast(:days as integer)
        order by business_date desc
        """,
        {'days': days},
    )


def summary(days: int = 14, limit: int = 10) -> dict[str, Any]:
    gap_rows = gaps(days)
    backlog_rows = repair_backlog(limit)
    run_rows = recent_runs(limit)
    family_rows = family_health(limit)
    date_rows = date_health(days)
    return {
        'window_days': days,
        'incomplete_dates': sorted({str(r['business_date']) for r in gap_rows}, reverse=True),
        'gap_item_count': len(gap_rows),
        'repair_backlog_count': len(backlog_rows),
        'retry_due_count': sum(1 for r in backlog_rows if r.get('retry_after') is None or str(r.get('retry_after')) <= datetime.now(timezone.utc).isoformat()),
        'lagging_families': family_rows[:10],
        'recent_runs': run_rows,
        'date_health': date_rows,
        'repair_backlog': backlog_rows,
    }


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
