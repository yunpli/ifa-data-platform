from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def fmt_ts(v):
    if v is None:
        return '-'
    if isinstance(v, str):
        return v
    if getattr(v, 'tzinfo', None) is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hours', type=int, default=24)
    ap.add_argument('--out', type=str)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=args.hours)

    with engine.begin() as conn:
        runs = conn.execute(text("""
            select lane, worker_type, trigger_mode, schedule_key, status, governance_state,
                   runtime_budget_sec, duration_ms, records_processed, error_count,
                   started_at, completed_at, tables_updated, tasks_executed, summary
            from ifa2.unified_runtime_runs
            where started_at >= :since
            order by started_at desc
        """), {'since': since}).mappings().all()
        worker_states = conn.execute(text("select * from ifa2.runtime_worker_state order by worker_type")).mappings().all()
        job_runs = conn.execute(text("""
            select job_name, status, started_at, completed_at, records_processed
            from ifa2.job_runs
            where started_at >= :since
            order by started_at desc
            limit 200
        """), {'since': since}).mappings().all()
        archive_runs = conn.execute(text("""
            select job_name, dataset_name, asset_type, status, records_processed, started_at, completed_at
            from ifa2.archive_runs
            where started_at >= :since
            order by started_at desc
            limit 100
        """), {'since': since}).mappings().all()
        checkpoints = conn.execute(text("""
            select dataset_name, asset_type, last_completed_date, status
            from ifa2.archive_checkpoints
            order by dataset_name, asset_type
        """)).mappings().all()

    by_lane = defaultdict(list)
    for r in runs:
        by_lane[r['lane']].append(r)

    lines = []
    lines.append('Collection Layer Runtime Report (Last 24 Hours)')
    lines.append(f'Report generated: {fmt_ts(now)}')
    lines.append(f'Time range: {fmt_ts(since)} -> {fmt_ts(now)}')
    lines.append('')

    recent_worker_activity = []
    for ws in worker_states:
        lc = ws.get('last_completed_at')
        if lc is not None:
            if getattr(lc, 'tzinfo', None) is None:
                lc = lc.replace(tzinfo=timezone.utc)
            if lc >= since:
                recent_worker_activity.append((ws['worker_type'], lc, ws.get('last_status')))

    lines.append('1. Unified daemon summary')
    lines.append(f'- Total unified runs: {len(runs)}')
    lines.append(f'- Job-run rows in window: {len(job_runs)}')
    lines.append(f'- Archive-run rows in window: {len(archive_runs)}')
    lines.append(f'- Worker-state completions in window: {len(recent_worker_activity)}')
    if runs:
        ok = sum(1 for r in runs if r['status'] == 'succeeded')
        partial = sum(1 for r in runs if r['status'] == 'partial')
        failed = sum(1 for r in runs if r['status'] not in {'succeeded', 'partial'})
        lines.append(f'- Succeeded: {ok}')
        lines.append(f'- Partial: {partial}')
        lines.append(f'- Other/non-success: {failed}')
        lines.append('- Interpretation: unified runtime rows exist for the window.')
    elif recent_worker_activity or job_runs or archive_runs:
        lines.append('- No unified_runtime_runs rows found in window.')
        lines.append('- But other evidence shows recent runtime activity exists in the window.')
        if recent_worker_activity:
            for wt, lc, st in recent_worker_activity:
                lines.append(f'- Worker-state evidence: {wt} last_completed={fmt_ts(lc)} status={st}')
        lines.append('- Interpretation: recent execution evidence exists, but unified run-row evidence is absent/missing for this window.')
    else:
        lines.append('- No unified_runtime_runs rows found in window.')
        lines.append('- No worker-state completion evidence in window.')
        lines.append('- No job/archive evidence in window.')
        lines.append('- Interpretation: no observed runtime activity in the last 24 hours.')
    lines.append('')

    for lane in ['lowfreq', 'midfreq', 'highfreq', 'archive']:
        lane_runs = by_lane.get(lane, [])
        lines.append(f'{2 + ["lowfreq","midfreq","highfreq","archive"].index(lane)}. {lane} summary')
        if not lane_runs:
            lines.append('- No runs in window')
            lines.append('')
            continue
        lines.append(f'- Run count: {len(lane_runs)}')
        for r in lane_runs[:5]:
            lines.append(
                f"- {fmt_ts(r['started_at'])} | status={r['status']} governance={r['governance_state']} "
                f"records={r['records_processed']} duration_ms={r['duration_ms']} schedule={r['schedule_key'] or '-'}"
            )
        total_records = sum(int(r['records_processed'] or 0) for r in lane_runs)
        total_errors = sum(int(r['error_count'] or 0) for r in lane_runs)
        lines.append(f'- Total records processed: {total_records}')
        lines.append(f'- Total reported error_count: {total_errors}')
        if lane == 'midfreq':
            sector_zero = any('sector_performance' in str((r.get('summary') or {})) for r in lane_runs)
            if sector_zero:
                lines.append('- Note: sector_performance is now corrected to THS .TI path; prior zero-row runs may still appear in history before correction.')
        if lane == 'highfreq':
            lines.append('- Note: highfreq derived-state is now wired into intended runtime path after event_time_stream.')
        if lane == 'archive':
            lines.append(f'- Archive jobs in window: {len(archive_runs)}')
        lines.append('')

    lines.append('6. Major table/archive progression summary')
    if archive_runs:
        for r in archive_runs[:12]:
            lines.append(
                f"- Archive job {r['job_name']} ({r['dataset_name']}/{r['asset_type']}) status={r['status']} "
                f"records={r['records_processed']} started={fmt_ts(r['started_at'])}"
            )
    else:
        lines.append('- No archive jobs in window')
    lines.append('')

    lines.append('7. Current worker state snapshot')
    for ws in worker_states:
        lines.append(
            f"- {ws['worker_type']}: last_status={ws.get('last_status') or '-'} "
            f"active_run_id={ws.get('active_run_id') or '-'} last_completed={fmt_ts(ws.get('last_completed_at'))} next_due={fmt_ts(ws.get('next_due_at_utc'))}"
        )
    lines.append('')

    lines.append('8. Current archive checkpoint snapshot')
    for cp in checkpoints[:12]:
        lines.append(
            f"- {cp['dataset_name']} / {cp['asset_type']}: last_completed_date={cp['last_completed_date']} status={cp['status']}"
        )
    lines.append('')

    lines.append('9. Overall judgment')
    if runs:
        lines.append('- Unified runtime rows exist in the last 24 hours; runtime activity is directly evidenced in unified_runtime_runs.')
    elif recent_worker_activity or job_runs or archive_runs:
        lines.append('- No unified_runtime_runs rows were found in the last 24 hours, but other evidence sources show recent runtime activity in the window.')
        lines.append('- This is an evidence mismatch/alignment issue, not a truthful "no activity" case.')
    else:
        lines.append('- No unified_runtime_runs rows, no worker-state completions, and no job/archive evidence were observed in the last 24 hours.')
        lines.append('- This is the only case that should be interpreted as no observed activity in the window.')
    lines.append('- Watchdog/governance exists at DB/operator layer (timeout/overlap/stale visibility).')
    lines.append('- External hard-kill/restart supervisor still does not exist yet.')

    text_out = '\n'.join(lines) + '\n'
    if args.out:
        Path(args.out).write_text(text_out)
        print(args.out)
    else:
        print(text_out)


if __name__ == '__main__':
    main()
