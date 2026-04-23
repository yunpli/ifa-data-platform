from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from ifa_data_platform.lowfreq.trade_calendar_maintenance import TradeCalendarMaintenanceService

engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


@dataclass
class Finding:
    kind: str
    action: str
    detail: dict[str, Any]


def _utc(v):
    if v is None:
        return None
    if getattr(v, 'tzinfo', None) is None:
        return v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repair', action='store_true')
    ap.add_argument('--out', type=str)
    ap.add_argument('--runtime-stale-min', type=int, default=120)
    ap.add_argument('--checkpoint-stale-hours', type=int, default=12)
    ap.add_argument('--catchup-stale-hours', type=int, default=24)
    ap.add_argument('--calendar-exchange', type=str, default='SSE')
    ap.add_argument('--calendar-past-days-required', type=int, default=30)
    ap.add_argument('--calendar-future-days-required', type=int, default=180)
    ap.add_argument('--calendar-max-active-version-age-days', type=int, default=45)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    findings: list[Finding] = []

    with engine.begin() as conn:
        worker_states = conn.execute(text("select * from ifa2.runtime_worker_state order by worker_type")).mappings().all()
        active_run_ids: set[str] = set()
        for ws in worker_states:
            active_run_id = ws.get('active_run_id')
            active_started_at = _utc(ws.get('active_started_at'))
            if active_run_id:
                active_run_ids.add(str(active_run_id))
            if active_run_id and active_started_at:
                age_min = (now - active_started_at).total_seconds() / 60.0
                if age_min >= args.runtime_stale_min:
                    action = 'auto_clear_active_runtime_state' if args.repair else 'would_clear_active_runtime_state'
                    findings.append(Finding('runtime_worker_state_stale_active', action, {
                        'worker_type': ws['worker_type'],
                        'active_run_id': str(active_run_id),
                        'active_started_at': active_started_at.isoformat(),
                        'age_min': round(age_min, 1),
                    }))
                    if args.repair:
                        conn.execute(text("""
                            update ifa2.runtime_worker_state
                            set active_run_id = null,
                                active_schedule_key = null,
                                active_started_at = null,
                                last_status = case
                                    when coalesce(last_status, '') in ('running', 'active') then 'timed_out'
                                    else last_status
                                end,
                                last_error = coalesce(last_error, 'cleared by runtime_preflight after abnormal termination'),
                                updated_at = now()
                            where worker_type = :worker_type
                        """), {'worker_type': ws['worker_type']})
                        conn.execute(text("""
                            update ifa2.unified_runtime_runs
                            set status = case
                                    when coalesce(status, '') in ('running', 'active') then 'timed_out'
                                    else status
                                end,
                                governance_state = case
                                    when coalesce(governance_state, '') in ('', 'ok', 'running', 'active') then 'timed_out'
                                    else governance_state
                                end,
                                completed_at = coalesce(completed_at, now()),
                                duration_ms = coalesce(
                                    duration_ms,
                                    greatest(0, floor(extract(epoch from (now() - started_at)) * 1000))::bigint
                                ),
                                error_count = greatest(coalesce(error_count, 0), 1),
                                summary = coalesce(summary, '{}'::jsonb) || jsonb_build_object(
                                    'runtime_preflight_repaired', true,
                                    'runtime_preflight_repaired_at', now(),
                                    'runtime_preflight_reason', 'stale_active_runtime_state'
                                )
                            where id = cast(:run_id as uuid)
                        """), {'run_id': str(active_run_id)})

        orphan_runs = conn.execute(text("""
            select id, lane, worker_type, trigger_mode, schedule_key, started_at, completed_at, status, governance_state
            from ifa2.unified_runtime_runs
            where coalesce(status, '') in ('running', 'active')
            order by started_at asc
        """)).mappings().all()
        for run in orphan_runs:
            run_id = str(run['id'])
            if run_id in active_run_ids:
                continue
            started_at = _utc(run.get('started_at'))
            age_min = (now - started_at).total_seconds() / 60.0 if started_at else None
            if age_min is None or age_min < args.runtime_stale_min:
                continue
            action = 'auto_clear_orphan_unified_runtime_run' if args.repair else 'would_clear_orphan_unified_runtime_run'
            findings.append(Finding('unified_runtime_run_orphan_active', action, {
                'run_id': run_id,
                'lane': run.get('lane'),
                'worker_type': run.get('worker_type'),
                'trigger_mode': run.get('trigger_mode'),
                'schedule_key': run.get('schedule_key'),
                'started_at': started_at.isoformat() if started_at else None,
                'age_min': round(age_min, 1),
                'status': run.get('status'),
                'governance_state': run.get('governance_state'),
                'reason': 'running row has no matching runtime_worker_state.active_run_id',
            }))
            if args.repair:
                conn.execute(text("""
                    update ifa2.unified_runtime_runs
                    set status = case
                            when coalesce(status, '') in ('running', 'active') then 'timed_out'
                            else status
                        end,
                        governance_state = case
                            when coalesce(governance_state, '') in ('', 'ok', 'running', 'active') then 'timed_out'
                            else governance_state
                        end,
                        completed_at = coalesce(completed_at, now()),
                        duration_ms = coalesce(
                            duration_ms,
                            greatest(0, floor(extract(epoch from (now() - started_at)) * 1000))::bigint
                        ),
                        error_count = greatest(coalesce(error_count, 0), 1),
                        summary = coalesce(summary, '{}'::jsonb) || jsonb_build_object(
                            'runtime_preflight_repaired', true,
                            'runtime_preflight_repaired_at', now(),
                            'runtime_preflight_reason', 'orphan_active_unified_runtime_run'
                        )
                    where id = cast(:run_id as uuid)
                """), {'run_id': run_id})

        cps = conn.execute(text("select * from ifa2.archive_checkpoints where status = 'in_progress' order by dataset_name, asset_type")).mappings().all()
        for cp in cps:
            updated_at = _utc(cp.get('updated_at'))
            age_h = (now - updated_at).total_seconds() / 3600.0 if updated_at else None
            stale = age_h is not None and age_h >= args.checkpoint_stale_hours
            action = 'report_only_in_progress_checkpoint'
            if stale and args.repair:
                action = 'mark_checkpoint_abandoned'
                conn.execute(text("""
                    update ifa2.archive_checkpoints
                    set status = 'abandoned',
                        updated_at = now()
                    where id = :id
                """), {'id': str(cp['id'])})
            elif stale:
                action = 'would_mark_checkpoint_abandoned'
            findings.append(Finding('archive_checkpoint_in_progress', action, {
                'id': str(cp['id']),
                'dataset_name': cp['dataset_name'],
                'asset_type': cp['asset_type'],
                'last_completed_date': str(cp['last_completed_date']) if cp.get('last_completed_date') else None,
                'updated_at': updated_at.isoformat() if updated_at else None,
                'age_h': round(age_h, 2) if age_h is not None else None,
                'stale': stale,
            }))

        catchups = conn.execute(text("""
            select * from ifa2.archive_target_catchup
            where status in ('pending','observed')
            order by updated_at desc nulls last, created_at desc
        """)).mappings().all()
        for c in catchups:
            updated_at = _utc(c.get('updated_at') or c.get('created_at'))
            age_h = (now - updated_at).total_seconds() / 3600.0 if updated_at else None
            stale = age_h is not None and age_h >= args.catchup_stale_hours
            findings.append(Finding('archive_target_catchup_pending_or_observed', 'report_only' if not stale else 'report_stale_pending_or_observed', {
                'id': str(c['id']),
                'asset_category': c['asset_category'],
                'granularity': c['granularity'],
                'symbol_or_series_id': c['symbol_or_series_id'],
                'status': c['status'],
                'checkpoint_dataset_name': c.get('checkpoint_dataset_name'),
                'updated_at': updated_at.isoformat() if updated_at else None,
                'age_h': round(age_h, 2) if age_h is not None else None,
                'stale': stale,
                'reason': c.get('reason'),
                'progress_note': c.get('progress_note'),
            }))

    calendar_report = TradeCalendarMaintenanceService().health_check(
        exchange=args.calendar_exchange,
        past_days_required=args.calendar_past_days_required,
        future_days_required=args.calendar_future_days_required,
        max_active_version_age_days=args.calendar_max_active_version_age_days,
    )
    for item in calendar_report.findings:
        findings.append(Finding('trade_calendar_health', 'report_only', item))

    payload = {
        'generated_at': now.isoformat(),
        'repair': args.repair,
        'runtime_stale_min': args.runtime_stale_min,
        'checkpoint_stale_hours': args.checkpoint_stale_hours,
        'catchup_stale_hours': args.catchup_stale_hours,
        'trade_calendar': calendar_report.to_dict(),
        'findings': [asdict(f) for f in findings],
        'summary': {
            'total_findings': len(findings),
            'stale_runtime_active': sum(1 for f in findings if f.kind == 'runtime_worker_state_stale_active'),
            'orphan_unified_runtime_active': sum(1 for f in findings if f.kind == 'unified_runtime_run_orphan_active'),
            'in_progress_checkpoints': sum(1 for f in findings if f.kind == 'archive_checkpoint_in_progress'),
            'catchup_pending_or_observed': sum(1 for f in findings if f.kind == 'archive_target_catchup_pending_or_observed'),
            'trade_calendar_status': calendar_report.status,
            'trade_calendar_findings': len(calendar_report.findings),
        }
    }
    if args.out:
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(args.out)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
