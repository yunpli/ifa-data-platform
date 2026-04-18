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
NON_ACTIONABLE_REASON_CODES = {'not_archive_worthy', 'unsupported_family', 'intentional_exclusion', 'legacy_placeholder'}
NON_ACTIONABLE_FAMILIES = {'generic_structured_output_daily', 'highfreq_signal_daily'}


def infer_reason_code(status: str, detail_text: str | None, family_name: str | None = None) -> str:
    detail = (detail_text or '').lower()
    if family_name in NON_ACTIONABLE_FAMILIES:
        return 'legacy_placeholder' if family_name == 'highfreq_signal_daily' else 'not_archive_worthy'
    if 'not archive-v2 worthy' in detail:
        return 'not_archive_worthy'
    if 'legacy placeholder' in detail:
        return 'legacy_placeholder'
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


def classify_actionability(reason_code: str, family_name: str | None = None) -> str:
    if family_name in NON_ACTIONABLE_FAMILIES:
        return 'non_actionable'
    if reason_code in NON_ACTIONABLE_REASON_CODES:
        return 'non_actionable'
    return 'actionable'


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
    if classify_actionability(reason_code, family_name) == 'non_actionable':
        base = min(base, 20)
    if retry_count >= 3:
        base += min(15, retry_count * 2)
    return min(base, 100)


def compute_urgency(priority: int, retry_count: int, actionability: str) -> str:
    if actionability == 'non_actionable':
        return 'deferred'
    if priority >= 90 or retry_count >= 5:
        return 'critical'
    if priority >= 75 or retry_count >= 3:
        return 'high'
    if priority >= 55:
        return 'normal'
    return 'low'


def compute_escalation_level(retry_count: int, priority: int, actionability: str) -> int:
    if actionability == 'non_actionable':
        return 0
    if priority >= 90 or retry_count >= 5:
        return 3
    if priority >= 75 or retry_count >= 3:
        return 2
    if retry_count >= 1:
        return 1
    return 0


def compute_retry_after(status: str, retry_count: int, reason_code: str, actionability: str) -> datetime | None:
    if actionability == 'non_actionable':
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
    reason_code = infer_reason_code(status, detail_text, family_name)
    actionability = classify_actionability(reason_code, family_name)
    priority = compute_priority(family_name, status, retry_count, reason_code)
    urgency = compute_urgency(priority, retry_count, actionability)
    escalation_level = compute_escalation_level(retry_count, priority, actionability)
    retry_after = compute_retry_after(status, retry_count, reason_code, actionability)
    return {
        'reason_code': reason_code,
        'actionability': actionability,
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


def _repair_backlog_base_sql() -> str:
    return """
        select *
        from ifa2.ifa_archive_operator_repair_backlog_v
        where 1=1
    """


def select_repair_targets(
    limit: int = 20,
    business_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    family_names: list[str] | None = None,
    statuses: list[str] | None = None,
    urgencies: list[str] | None = None,
    min_priority: int | None = None,
    retry_due_only: bool = False,
    actionable_only: bool = True,
    include_non_actionable: bool = False,
) -> list[dict[str, Any]]:
    sql = [_repair_backlog_base_sql()]
    params: dict[str, Any] = {'limit': limit}
    if business_date:
        sql.append('and business_date = :business_date')
        params['business_date'] = business_date
    if start_date:
        sql.append('and business_date >= :start_date')
        params['start_date'] = start_date
    if end_date:
        sql.append('and business_date <= :end_date')
        params['end_date'] = end_date
    if family_names:
        placeholders = []
        for idx, family in enumerate(family_names):
            key = f'family_{idx}'
            placeholders.append(f':{key}')
            params[key] = family
        sql.append(f"and family_name in ({', '.join(placeholders)})")
    if statuses:
        placeholders = []
        for idx, status in enumerate(statuses):
            key = f'status_{idx}'
            placeholders.append(f':{key}')
            params[key] = status
        sql.append(f"and repair_status in ({', '.join(placeholders)})")
    if urgencies:
        placeholders = []
        for idx, urgency in enumerate(urgencies):
            key = f'urgency_{idx}'
            placeholders.append(f':{key}')
            params[key] = urgency
        sql.append(f"and urgency in ({', '.join(placeholders)})")
    if min_priority is not None:
        sql.append('and priority >= :min_priority')
        params['min_priority'] = min_priority
    if retry_due_only:
        sql.append('and (retry_after is null or retry_after <= now())')
    if actionable_only and not include_non_actionable:
        sql.append("and actionability = 'actionable'")
    elif not include_non_actionable:
        sql.append("and actionability <> 'non_actionable'")
    sql.append("order by actionability_sort asc, priority desc, coalesce(retry_after, now()) asc, updated_at asc, business_date asc, family_name asc")
    sql.append('limit :limit')
    return fetch_rows('\n'.join(sql), params)


def repair_backlog(limit: int = 20, actionable_only: bool = False, include_non_actionable: bool = True) -> list[dict[str, Any]]:
    return select_repair_targets(limit=limit, actionable_only=actionable_only, include_non_actionable=include_non_actionable)


def actionable_backlog(limit: int = 20) -> list[dict[str, Any]]:
    return select_repair_targets(limit=limit, actionable_only=True, include_non_actionable=False)


def non_actionable_backlog(limit: int = 20) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_repair_backlog_v
        where actionability = 'non_actionable'
        order by priority desc, updated_at asc, business_date asc, family_name asc
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
    actionable_rows = actionable_backlog(limit)
    non_actionable_rows = non_actionable_backlog(limit)
    run_rows = recent_runs(limit)
    family_rows = family_health(limit)
    date_rows = date_health(days)
    return {
        'window_days': days,
        'incomplete_dates': sorted({str(r['business_date']) for r in gap_rows}, reverse=True),
        'gap_item_count': len(gap_rows),
        'repair_backlog_count': len(backlog_rows),
        'actionable_backlog_count': len(actionable_rows),
        'non_actionable_backlog_count': len(non_actionable_rows),
        'retry_due_count': sum(1 for r in actionable_rows if r.get('retry_after') is None or str(r.get('retry_after')) <= datetime.now(timezone.utc).isoformat()),
        'lagging_families': family_rows[:10],
        'recent_runs': run_rows,
        'date_health': date_rows,
        'actionable_backlog': actionable_rows,
        'non_actionable_backlog': non_actionable_rows,
    }


def build_repair_batch_notes(targets: list[dict[str, Any]], filters: dict[str, Any]) -> str:
    families = sorted({t['family_name'] for t in targets})
    dates = sorted({str(t['business_date']) for t in targets})
    return json.dumps({
        'repair_batch': True,
        'selected_count': len(targets),
        'families': families,
        'dates': dates,
        'filters': filters,
    }, ensure_ascii=False)


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
