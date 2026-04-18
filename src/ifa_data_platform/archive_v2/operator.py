from __future__ import annotations

import json
import uuid
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
SUPPRESSED_STATES = {'acknowledged', 'suppressed'}


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


def repair_history(limit: int = 20) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_repair_execution_history_v
        order by start_time desc, business_date desc, family_name
        limit :limit
        """,
        {'limit': limit},
    )


def claimed_backlog(limit: int = 20, include_expired: bool = True) -> list[dict[str, Any]]:
    sql = """
        select *
        from ifa2.ifa_archive_operator_claimed_backlog_v
        where 1=1
    """
    if not include_expired:
        sql += " and claim_state = 'active'"
    sql += " order by claim_state_sort asc, claim_expires_at asc, claimed_at asc, business_date asc, family_name asc limit :limit"
    return fetch_rows(sql, {'limit': limit})


def suppressed_backlog(limit: int = 20) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_suppressed_backlog_v
        order by coalesce(suppressed_until, acknowledged_at) desc nulls last, business_date desc, family_name
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
    include_claimed: bool = False,
    include_suppressed: bool = False,
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
    if not include_claimed:
        sql.append("and repair_status <> 'claimed'")
    if not include_suppressed:
        sql.append("and suppression_active = false")
    sql.append("order by actionability_sort asc, priority desc, coalesce(retry_after, now()) asc, updated_at asc, business_date asc, family_name asc")
    sql.append('limit :limit')
    return fetch_rows('\n'.join(sql), params)


def _queue_filter_sql(
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
    include_suppressed: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    clauses = [
        "(q.status in ('pending', 'retry_needed') or (q.status = 'claimed' and (q.claim_expires_at is null or q.claim_expires_at <= now())))"
    ]
    params: dict[str, Any] = {}
    if business_date:
        clauses.append('q.business_date = :business_date')
        params['business_date'] = business_date
    if start_date:
        clauses.append('q.business_date >= :start_date')
        params['start_date'] = start_date
    if end_date:
        clauses.append('q.business_date <= :end_date')
        params['end_date'] = end_date
    if family_names:
        placeholders = []
        for idx, family in enumerate(family_names):
            key = f'family_{idx}'
            placeholders.append(f':{key}')
            params[key] = family
        clauses.append(f"q.family_name in ({', '.join(placeholders)})")
    if statuses:
        placeholders = []
        for idx, status in enumerate(statuses):
            key = f'status_{idx}'
            placeholders.append(f':{key}')
            params[key] = status
        clauses.append(f"q.status in ({', '.join(placeholders)})")
    if urgencies:
        placeholders = []
        for idx, urgency in enumerate(urgencies):
            key = f'urgency_{idx}'
            placeholders.append(f':{key}')
            params[key] = urgency
        clauses.append(f"q.urgency in ({', '.join(placeholders)})")
    if min_priority is not None:
        clauses.append('q.priority >= :min_priority')
        params['min_priority'] = min_priority
    if retry_due_only:
        clauses.append('(q.retry_after is null or q.retry_after <= now())')
    if actionable_only and not include_non_actionable:
        clauses.append("coalesce(q.actionability, 'actionable') = 'actionable'")
    elif not include_non_actionable:
        clauses.append("coalesce(q.actionability, 'actionable') <> 'non_actionable'")
    if not include_suppressed:
        clauses.append("not (coalesce(q.suppression_state, 'active') in ('acknowledged', 'suppressed') and (q.suppressed_until is null or q.suppressed_until > now()))")
    return clauses, params


def claim_repair_targets(
    claimed_by: str,
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
    include_suppressed: bool = False,
    lease_minutes: int = 15,
) -> dict[str, Any]:
    ensure_schema()
    claim_id = str(uuid.uuid4())
    clauses, params = _queue_filter_sql(
        business_date=business_date,
        start_date=start_date,
        end_date=end_date,
        family_names=family_names,
        statuses=statuses,
        urgencies=urgencies,
        min_priority=min_priority,
        retry_due_only=retry_due_only,
        actionable_only=actionable_only,
        include_non_actionable=include_non_actionable,
        include_suppressed=include_suppressed,
    )
    params.update({'limit': limit, 'claim_id': claim_id, 'claimed_by': claimed_by, 'lease_minutes': lease_minutes})
    where_sql = ' and '.join(clauses)
    sql = f"""
        with candidates as (
          select q.business_date, q.family_name, q.frequency, q.coverage_scope
          from ifa2.ifa_archive_repair_queue q
          where {where_sql}
          order by
            case when coalesce(q.actionability, 'actionable') = 'actionable' then 0 else 1 end asc,
            q.priority desc,
            coalesce(q.retry_after, now()) asc,
            q.updated_at asc,
            q.business_date asc,
            q.family_name asc
          limit :limit
          for update skip locked
        ), updated as (
          update ifa2.ifa_archive_repair_queue q
             set status = 'claimed',
                 claim_id = cast(:claim_id as uuid),
                 claimed_at = now(),
                 claimed_by = :claimed_by,
                 claim_expires_at = now() + make_interval(mins => cast(:lease_minutes as integer)),
                 last_attempt_at = now(),
                 updated_at = now()
            from candidates c
           where q.business_date is not distinct from c.business_date
             and q.family_name = c.family_name
             and q.frequency = c.frequency
             and q.coverage_scope is not distinct from c.coverage_scope
          returning q.business_date, q.family_name, q.frequency, q.coverage_scope
        )
        select
          q.business_date,
          q.family_name,
          q.frequency,
          q.coverage_scope,
          q.status as repair_status,
          q.reason_code,
          q.actionability,
          q.priority,
          q.urgency,
          q.retry_count,
          q.retry_after,
          q.claim_id,
          q.claimed_at,
          q.claimed_by,
          q.claim_expires_at,
          q.suppression_state,
          q.suppressed_until,
          c.status as completeness_status,
          c.row_count,
          q.updated_at
        from ifa2.ifa_archive_repair_queue q
        join updated u
          on q.business_date is not distinct from u.business_date
         and q.family_name = u.family_name
         and q.frequency = u.frequency
         and q.coverage_scope is not distinct from u.coverage_scope
        left join ifa2.ifa_archive_completeness c
          on q.business_date = c.business_date
         and q.family_name = c.family_name
         and q.frequency = c.frequency
         and q.coverage_scope = c.coverage_scope
        order by q.priority desc, q.business_date asc, q.family_name asc
    """
    with engine.begin() as conn:
        rows = [dict(r) for r in conn.execute(text(sql), params).mappings().all()]
    return {'claim_id': claim_id, 'claimed_by': claimed_by, 'lease_minutes': lease_minutes, 'targets': rows}


def load_claimed_targets(claim_id: str, claimed_by: str | None = None, include_expired: bool = True) -> list[dict[str, Any]]:
    sql = """
        select
          business_date,
          family_name,
          frequency,
          coverage_scope,
          status as repair_status,
          reason_code,
          actionability,
          priority,
          urgency,
          retry_count,
          retry_after,
          claim_id,
          claimed_at,
          claimed_by,
          claim_expires_at,
          suppression_state,
          suppressed_until,
          updated_at
        from ifa2.ifa_archive_repair_queue
        where claim_id = cast(:claim_id as uuid)
          and status = 'claimed'
    """
    params: dict[str, Any] = {'claim_id': claim_id}
    if claimed_by:
        sql += ' and claimed_by = :claimed_by'
        params['claimed_by'] = claimed_by
    if not include_expired:
        sql += ' and (claim_expires_at is null or claim_expires_at > now())'
    sql += ' order by priority desc, business_date asc, family_name asc'
    return fetch_rows(sql, params)


def release_claims(claim_id: str, released_by: str, release_reason: str = 'manual_release') -> dict[str, Any]:
    ensure_schema()
    with engine.begin() as conn:
        rows = [dict(r) for r in conn.execute(text("""
            update ifa2.ifa_archive_repair_queue
               set status = case when coalesce(last_observed_status, 'pending') in ('retry_needed', 'partial', 'incomplete', 'missing') then 'pending' else 'pending' end,
                   claim_id = null,
                   claimed_at = null,
                   claimed_by = null,
                   claim_expires_at = null,
                   last_error = coalesce(last_error, :release_reason),
                   updated_at = now()
             where claim_id = cast(:claim_id as uuid)
               and status = 'claimed'
         returning business_date, family_name, frequency, coverage_scope, status, reason_code, actionability, priority, urgency, retry_count, updated_at
        """), {'claim_id': claim_id, 'release_reason': f'released by {released_by}: {release_reason}'}).mappings().all()]
    return {'claim_id': claim_id, 'released_by': released_by, 'released_count': len(rows), 'targets': rows}


def acknowledge_backlog(
    acknowledged_by: str,
    reason: str,
    business_date: str | None = None,
    family_names: list[str] | None = None,
    non_actionable_only: bool = True,
    suppress_hours: int | None = None,
) -> dict[str, Any]:
    ensure_schema()
    clauses = ["status in ('pending', 'retry_needed', 'claimed')"]
    params: dict[str, Any] = {'acknowledged_by': acknowledged_by, 'reason': reason}
    if business_date:
        clauses.append('business_date = :business_date')
        params['business_date'] = business_date
    if family_names:
        placeholders = []
        for idx, family in enumerate(family_names):
            key = f'family_{idx}'
            placeholders.append(f':{key}')
            params[key] = family
        clauses.append(f"family_name in ({', '.join(placeholders)})")
    if non_actionable_only:
        clauses.append("coalesce(actionability, 'actionable') = 'non_actionable'")
    suppress_expr = 'null'
    if suppress_hours is not None:
        params['suppress_hours'] = suppress_hours
        suppress_expr = "now() + make_interval(hours => cast(:suppress_hours as integer))"
    sql = f"""
        update ifa2.ifa_archive_repair_queue
           set suppression_state = case when {suppress_expr} is null then 'acknowledged' else 'suppressed' end,
               acknowledged_at = now(),
               acknowledged_by = :acknowledged_by,
               acknowledgement_reason = :reason,
               suppressed_until = {suppress_expr},
               updated_at = now()
         where {' and '.join(clauses)}
     returning business_date, family_name, status as repair_status, actionability, suppression_state, suppressed_until, acknowledged_by, acknowledgement_reason
    """
    with engine.begin() as conn:
        rows = [dict(r) for r in conn.execute(text(sql), params).mappings().all()]
    return {'acknowledged_by': acknowledged_by, 'count': len(rows), 'targets': rows}


def unsuppress_backlog(
    business_date: str | None = None,
    family_names: list[str] | None = None,
) -> dict[str, Any]:
    ensure_schema()
    clauses = ["coalesce(suppression_state, 'active') in ('acknowledged', 'suppressed')"]
    params: dict[str, Any] = {}
    if business_date:
        clauses.append('business_date = :business_date')
        params['business_date'] = business_date
    if family_names:
        placeholders = []
        for idx, family in enumerate(family_names):
            key = f'family_{idx}'
            placeholders.append(f':{key}')
            params[key] = family
        clauses.append(f"family_name in ({', '.join(placeholders)})")
    sql = f"""
        update ifa2.ifa_archive_repair_queue
           set suppression_state = 'active',
               suppressed_until = null,
               updated_at = now()
         where {' and '.join(clauses)}
     returning business_date, family_name, status as repair_status, actionability, suppression_state, suppressed_until
    """
    with engine.begin() as conn:
        rows = [dict(r) for r in conn.execute(text(sql), params).mappings().all()]
    return {'count': len(rows), 'targets': rows}


def repair_backlog(limit: int = 20, actionable_only: bool = False, include_non_actionable: bool = True, include_suppressed: bool = False) -> list[dict[str, Any]]:
    return select_repair_targets(limit=limit, actionable_only=actionable_only, include_non_actionable=include_non_actionable, include_suppressed=include_suppressed, include_claimed=True)


def actionable_backlog(limit: int = 20) -> list[dict[str, Any]]:
    return select_repair_targets(limit=limit, actionable_only=True, include_non_actionable=False, include_suppressed=False, include_claimed=False)


def non_actionable_backlog(limit: int = 20) -> list[dict[str, Any]]:
    return fetch_rows(
        """
        select *
        from ifa2.ifa_archive_operator_repair_backlog_v
        where actionability = 'non_actionable'
        order by suppression_active asc, priority desc, updated_at asc, business_date asc, family_name asc
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
    backlog_rows = repair_backlog(limit, include_suppressed=False)
    actionable_rows = actionable_backlog(limit)
    non_actionable_rows = non_actionable_backlog(limit)
    suppressed_rows = suppressed_backlog(limit)
    claimed_rows = claimed_backlog(limit)
    run_rows = recent_runs(limit)
    history_rows = repair_history(limit)
    family_rows = family_health(limit)
    date_rows = date_health(days)
    return {
        'window_days': days,
        'incomplete_dates': sorted({str(r['business_date']) for r in gap_rows}, reverse=True),
        'gap_item_count': len(gap_rows),
        'repair_backlog_count': len(backlog_rows),
        'actionable_backlog_count': len(actionable_rows),
        'non_actionable_backlog_count': len(non_actionable_rows),
        'suppressed_backlog_count': len(suppressed_rows),
        'claimed_backlog_count': len(claimed_rows),
        'retry_due_count': sum(1 for r in actionable_rows if r.get('retry_after') is None or str(r.get('retry_after')) <= datetime.now(timezone.utc).isoformat()),
        'lagging_families': family_rows[:10],
        'recent_runs': run_rows,
        'recent_repair_history': history_rows,
        'date_health': date_rows,
        'actionable_backlog': actionable_rows,
        'non_actionable_backlog': non_actionable_rows,
        'suppressed_backlog': suppressed_rows,
        'claimed_backlog': claimed_rows,
    }


def build_repair_batch_notes(targets: list[dict[str, Any]], filters: dict[str, Any], claim_id: str | None = None) -> str:
    families = sorted({t['family_name'] for t in targets})
    dates = sorted({str(t['business_date']) for t in targets})
    payload = {
        'repair_batch': True,
        'selected_count': len(targets),
        'families': families,
        'dates': dates,
        'filters': filters,
    }
    if claim_id:
        payload['claim_id'] = claim_id
    return json.dumps(payload, ensure_ascii=False)


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
