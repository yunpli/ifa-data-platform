from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text

from ifa_data_platform.archive_v2.runner import ALL_FAMILY_META, DIRECT_DEST_TABLES

ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
TZ_SH = ZoneInfo('Asia/Shanghai')
TZ_UTC = timezone.utc


def fam_table(family: str) -> str | None:
    meta = ALL_FAMILY_META.get(family, {})
    return meta.get('dest_table') or DIRECT_DEST_TABLES.get(family)


def fmt_dt(dt) -> str:
    if dt is None:
        return '-'
    return dt.astimezone(TZ_SH).strftime('%Y-%m-%d %H:%M:%S %Z')


def duration_str(start, end) -> str:
    if not start or not end:
        return '-'
    sec = int((end - start).total_seconds())
    return f'{sec}s'


def load_schedule_truth(conn):
    rows = conn.execute(text("select worker_type, day_type, schedule_key, beijing_time_hm, enabled, trigger_type, group_name, purpose from ifa2.runtime_worker_schedules order by worker_type, day_type, beijing_time_hm")).mappings().all()
    return [dict(r) for r in rows]


def load_unified_runs(conn, hours: int):
    rows = conn.execute(text("select id::text as run_id, lane, worker_type, trigger_mode, schedule_key, status, started_at, completed_at, records_processed, duration_ms, tables_updated, tasks_executed, summary from ifa2.unified_runtime_runs where started_at >= now() - make_interval(hours => :hours) order by started_at desc"), {'hours': hours}).mappings().all()
    return [dict(r) for r in rows]


def load_archive_v2_runs(conn, hours: int):
    rows = conn.execute(text("select run_id::text, trigger_source, profile_name, status, start_time, end_time, notes from ifa2.ifa_archive_runs where start_time >= now() - make_interval(hours => :hours) order by start_time desc"), {'hours': hours}).mappings().all()
    out = []
    for row in rows:
        run_id = row['run_id']
        items = conn.execute(text("select family_name, business_date::text as business_date, status, rows_written from ifa2.ifa_archive_run_items where run_id = cast(:rid as uuid) order by business_date, family_name"), {'rid': run_id}).mappings().all()
        table_rows = defaultdict(int)
        status_counts = defaultdict(int)
        touched = set()
        for item in items:
            status_counts[item['status']] += 1
            table = fam_table(item['family_name'])
            if table:
                table_rows[table] += int(item['rows_written'] or 0)
                if int(item['rows_written'] or 0) > 0:
                    touched.add(table)
        out.append({
            **dict(row),
            'items': [dict(i) for i in items],
            'table_rows': dict(table_rows),
            'touched_tables': sorted(touched),
            'status_counts': dict(status_counts),
        })
    return out


def current_archive_backlog(conn):
    incomplete = conn.execute(text("select family_name, business_date::text as business_date, status from ifa2.ifa_archive_completeness where status in ('incomplete','partial') order by business_date desc, family_name limit 100")).mappings().all()
    repair = conn.execute(text("select family_name, business_date::text as business_date, status, claimed_by, suppressed_until from ifa2.ifa_archive_repair_queue order by business_date desc, family_name limit 100")).mappings().all()
    return [dict(r) for r in incomplete], [dict(r) for r in repair]


def summarize_lane_run(run: dict) -> dict:
    summary = run.get('summary') or {}
    main_tables = list(run.get('tables_updated') or [])
    table_rows = {}
    if isinstance(summary, dict):
        ds = summary.get('dataset_results') or summary.get('datasets') or {}
        if isinstance(ds, dict):
            for k, v in ds.items():
                if isinstance(v, dict):
                    rows = v.get('rows') or v.get('rows_written') or v.get('records') or v.get('count')
                    if rows is not None:
                        table_rows[k] = rows
    return {
        'start': fmt_dt(run['started_at']),
        'end': fmt_dt(run['completed_at']),
        'duration': duration_str(run['started_at'], run['completed_at']),
        'status': run['status'],
        'trigger': run['trigger_mode'],
        'records_processed': run['records_processed'],
        'main_tables': main_tables,
        'table_rows': table_rows,
    }


def render_markdown(hours: int, schedules, unified_runs, archive_runs, incomplete, repair) -> str:
    now_sh = datetime.now(TZ_SH)
    lines = []
    lines.append(f'# Runtime Daily Report')
    lines.append('')
    lines.append(f'- Window: last {hours} hours')
    lines.append(f'- Generated: {now_sh.strftime("%Y-%m-%d %H:%M:%S %Z")}')
    lines.append('')
    lines.append('## Schedule truth')
    lines.append('')
    for row in schedules:
        lines.append(f"- {row['worker_type']} | {row['day_type']} | {row['beijing_time_hm']} | enabled={row['enabled']} | trigger={row['trigger_type']} | {row['schedule_key']} | {row['purpose']}")
    lines.append('')
    lines.append('## Lane run overview')
    lines.append('')
    for lane in ['lowfreq', 'midfreq', 'highfreq']:
        lane_runs = [r for r in unified_runs if (r.get('lane') or r.get('worker_type')) == lane]
        lines.append(f'### {lane}')
        if not lane_runs:
            lines.append('- no runs in window')
        for run in lane_runs:
            s = summarize_lane_run(run)
            lines.append(f"- start={s['start']} | end={s['end']} | duration={s['duration']} | status={s['status']} | trigger={s['trigger']} | records={s['records_processed']}")
            lines.append(f"  - main_tables: {', '.join(s['main_tables']) if s['main_tables'] else '-'}")
            lines.append(f"  - table_rows: {json.dumps(s['table_rows'], ensure_ascii=False)}")
        lines.append('')
    lines.append('### archive_v2')
    if not archive_runs:
        lines.append('- no runs in window')
    for run in archive_runs:
        lines.append(f"- start={fmt_dt(run['start_time'])} | end={fmt_dt(run['end_time'])} | duration={duration_str(run['start_time'], run['end_time'])} | status={run['status']} | trigger={run['trigger_source']} | profile={run['profile_name']}")
        lines.append(f"  - touched_tables: {', '.join(run['touched_tables']) if run['touched_tables'] else '-'}")
        lines.append(f"  - rows_by_table: {json.dumps(run['table_rows'], ensure_ascii=False)}")
        lines.append(f"  - item_status_counts: {json.dumps(run['status_counts'], ensure_ascii=False)}")
    lines.append('')
    lines.append('## Archive backlog / repair summary')
    lines.append('')
    lines.append(f'- incomplete_or_partial_count: {len(incomplete)}')
    lines.append(f'- repair_queue_count: {len(repair)}')
    lines.append('- incomplete sample:')
    for row in incomplete[:20]:
        lines.append(f"  - {row['business_date']} | {row['family_name']} | {row['status']}")
    lines.append('- repair queue sample:')
    for row in repair[:20]:
        lines.append(f"  - {row['business_date']} | {row['family_name']} | {row['status']} | claimed_by={row.get('claimed_by')} | suppressed_until={row.get('suppressed_until')}")
    lines.append('')
    lines.append('## Operator-readable conclusion')
    lines.append('')
    archive_bad = [r for r in archive_runs if r['status'] not in ('completed', 'success')]
    lane_bad = [r for r in unified_runs if r['status'] not in ('success', 'completed')]
    if not archive_bad and not lane_bad:
        lines.append('- Overall window appears healthy for all lanes in scope.')
    else:
        lines.append(f'- Non-healthy runs detected: unified={len(lane_bad)}, archive_v2={len(archive_bad)}.')
        if archive_bad:
            lines.append('- archive_v2 notable issues:')
            for r in archive_bad[:10]:
                lines.append(f"  - {fmt_dt(r['start_time'])} | {r['trigger_source']} | {r['status']} | {r['profile_name']}")
    return '\n'.join(lines) + '\n'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--hours', type=int, default=24)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    with ENGINE.begin() as conn:
        schedules = load_schedule_truth(conn)
        unified_runs = load_unified_runs(conn, args.hours)
        archive_runs = load_archive_v2_runs(conn, args.hours)
        incomplete, repair = current_archive_backlog(conn)
    md = render_markdown(args.hours, schedules, unified_runs, archive_runs, incomplete, repair)
    Path(args.output).write_text(md)
    print(args.output)


if __name__ == '__main__':
    main()
