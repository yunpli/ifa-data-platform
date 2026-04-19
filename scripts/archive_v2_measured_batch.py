from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from ifa_data_platform.archive_v2.db import engine, ensure_schema
from ifa_data_platform.archive_v2.profile import ArchiveProfile
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner, ALL_FAMILY_META

EVIDENCE_TABLES = [
    'ifa_archive_runs',
    'ifa_archive_run_items',
    'ifa_archive_completeness',
    'ifa_archive_repair_queue',
]

DIRECT_DEST_TABLES = {
    'equity_daily': 'ifa_archive_equity_daily',
    'index_daily': 'ifa_archive_index_daily',
    'etf_daily': 'ifa_archive_etf_daily',
    'non_equity_daily': 'ifa_archive_non_equity_daily',
    'macro_daily': 'ifa_archive_macro_daily',
}


def _dest_table_for_family(family: str) -> str | None:
    meta = ALL_FAMILY_META.get(family, {})
    return meta.get('dest_table') or DIRECT_DEST_TABLES.get(family)


def _write_temp_profile(profile: ArchiveProfile) -> str:
    temp_dir = Path(tempfile.gettempdir()) / 'ifa_archive_v2_profiles'
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / f"{profile.profile_name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2))
    return str(path)


def _snapshot_tables(tables: list[str]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    with engine.begin() as conn:
        for table in tables:
            count = conn.execute(text(f"select count(*) from ifa2.{table}")).scalar_one()
            size = conn.execute(text("select pg_total_relation_size(:rel)"), {'rel': f'ifa2.{table}'}).scalar_one()
            out[table] = {'row_count': int(count or 0), 'bytes': int(size or 0)}
    return out


def _snapshot_scope_rows(dest_tables: list[str], dates: list[str]) -> dict[str, int]:
    date_values = [datetime.fromisoformat(d).date() for d in dates]
    out: dict[str, int] = {}
    with engine.begin() as conn:
        for table in dest_tables:
            out[table] = int(conn.execute(text(f"select count(*) from ifa2.{table} where business_date = any(:dates)"), {'dates': date_values}).scalar_one() or 0)
    return out


def _cleanup_scope(dates: list[str], families: list[str]) -> dict[str, Any]:
    dest_tables = sorted({table for f in families if (table := _dest_table_for_family(f))})
    cleanup_rows: dict[str, int] = {}
    date_values = [datetime.fromisoformat(d).date() for d in dates]
    with engine.begin() as conn:
        for table in dest_tables:
            deleted = conn.execute(text(f"delete from ifa2.{table} where business_date = any(:dates)"), {'dates': date_values})
            cleanup_rows[table] = int(deleted.rowcount or 0)
        deleted = conn.execute(text("delete from ifa2.ifa_archive_completeness where business_date = any(:dates) and family_name = any(:families) and coverage_scope='broad_market'"), {'dates': date_values, 'families': families})
        cleanup_rows['ifa_archive_completeness'] = int(deleted.rowcount or 0)
        deleted = conn.execute(text("delete from ifa2.ifa_archive_repair_queue where business_date = any(:dates) and family_name = any(:families) and coverage_scope='broad_market'"), {'dates': date_values, 'families': families})
        cleanup_rows['ifa_archive_repair_queue'] = int(deleted.rowcount or 0)
    return {'dates': dates, 'families': families, 'rows_deleted': cleanup_rows, 'dest_tables': dest_tables}


def _build_targets(dates: list[str], families: list[str]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for business_date in dates:
        for family in families:
            meta = ALL_FAMILY_META.get(family, {})
            targets.append({
                'business_date': business_date,
                'family_name': family,
                'frequency': meta.get('frequency', 'daily'),
                'priority': 'manual_measurement',
                'urgency': 'normal',
                'actionability': 'measure',
                'reason_code': 'manual_measured_batch',
            })
    return targets


def _aggregate_requested_rows(run_id: str) -> dict[str, int]:
    out: dict[str, int] = {}
    with engine.begin() as conn:
        rows = conn.execute(text("select family_name, rows_written, tables_touched from ifa2.ifa_archive_run_items where run_id=cast(:run_id as uuid)"), {'run_id': run_id}).mappings().all()
    for row in rows:
        touched = row['tables_touched'] or []
        if isinstance(touched, str):
            touched = json.loads(touched)
        for table in touched:
            out[table] = out.get(table, 0) + int(row['rows_written'] or 0)
    return out


def run_measured_batch(profile: ArchiveProfile, dates: list[str], trigger_source: str, notes: str | None = None) -> dict[str, Any]:
    ensure_schema()
    profile_path = _write_temp_profile(profile)
    runner = ArchiveV2Runner(profile_path)
    families = runner._resolve_requested_families()  # noqa: SLF001
    targets = _build_targets(dates, families)
    cleanup_summary = _cleanup_scope(dates, families)
    watch_tables = sorted(set(cleanup_summary['dest_tables'] + EVIDENCE_TABLES))
    before = _snapshot_tables(watch_tables)
    scope_before = _snapshot_scope_rows(cleanup_summary['dest_tables'], dates)
    started = datetime.now(timezone.utc)
    result = runner.run_selected_targets(targets, trigger_source=trigger_source, notes=notes)
    finished = datetime.now(timezone.utc)
    after = _snapshot_tables(watch_tables)
    scope_after = _snapshot_scope_rows(cleanup_summary['dest_tables'], dates)
    per_table: dict[str, dict[str, int]] = {}
    for table in watch_tables:
        per_table[table] = {
            'rows_before': before[table]['row_count'],
            'rows_after': after[table]['row_count'],
            'rows_added': after[table]['row_count'] - before[table]['row_count'],
            'bytes_before': before[table]['bytes'],
            'bytes_after': after[table]['bytes'],
            'bytes_added_rough': after[table]['bytes'] - before[table]['bytes'],
        }
        if table in scope_before:
            per_table[table]['scope_rows_before'] = scope_before[table]
            per_table[table]['scope_rows_after'] = scope_after[table]
            per_table[table]['scope_rows_added'] = scope_after[table] - scope_before[table]
    run_id = result.get('run_id')
    requested_by_table = _aggregate_requested_rows(run_id) if run_id else {}
    if run_id:
        with engine.begin() as conn:
            run_row = conn.execute(text("select run_id::text, trigger_source, profile_name, profile_path, mode, start_time, end_time, status, notes, error_text from ifa2.ifa_archive_runs where run_id=cast(:run_id as uuid)"), {'run_id': run_id}).mappings().first()
            run_items = [dict(r) for r in conn.execute(text("select family_name, frequency, business_date::text as business_date, status, rows_written, tables_touched, notes, error_text from ifa2.ifa_archive_run_items where run_id=cast(:run_id as uuid) order by business_date, frequency, family_name"), {'run_id': run_id}).mappings().all()]
    else:
        run_row = None
        run_items = []
    total_storage = sum(v['bytes_added_rough'] for v in per_table.values())
    return {
        'profile_path': profile_path,
        'profile': asdict(profile),
        'dates': dates,
        'families': families,
        'cleanup_scope': cleanup_summary,
        'started_at_utc': started.isoformat(),
        'finished_at_utc': finished.isoformat(),
        'duration_sec': (finished - started).total_seconds(),
        'result': result,
        'run_row': dict(run_row) if run_row else None,
        'run_items': run_items,
        'requested_rows_written_by_table': requested_by_table,
        'table_metrics': per_table,
        'total_storage_added_rough': total_storage,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile-name', required=True)
    ap.add_argument('--dates', nargs='+', required=True)
    ap.add_argument('--include-daily', action='store_true')
    ap.add_argument('--include-60m', action='store_true')
    ap.add_argument('--include-15m', action='store_true')
    ap.add_argument('--include-1m', action='store_true')
    ap.add_argument('--include-business-families', action='store_true')
    ap.add_argument('--include-tradable-families', action='store_true')
    ap.add_argument('--include-signal-families', action='store_true')
    ap.add_argument('--family-groups', nargs='*')
    ap.add_argument('--trigger-source', default='manual_measured_batch')
    ap.add_argument('--notes', default=None)
    ap.add_argument('--output', default=None)
    args = ap.parse_args()

    profile = ArchiveProfile(
        profile_name=args.profile_name,
        mode='single_day',
        start_date=args.dates[0],
        include_daily=args.include_daily,
        include_60m=args.include_60m,
        include_15m=args.include_15m,
        include_1m=args.include_1m,
        include_business_families=args.include_business_families,
        include_tradable_families=args.include_tradable_families,
        include_signal_families=args.include_signal_families,
        family_groups=list(args.family_groups or []),
        write_enabled=True,
        broad_market=True,
        notes=args.notes,
    )
    payload = run_measured_batch(profile, args.dates, trigger_source=args.trigger_source, notes=args.notes)
    text_out = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(text_out)
    print(text_out)


if __name__ == '__main__':
    main()
