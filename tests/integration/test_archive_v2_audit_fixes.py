from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text

from ifa_data_platform.archive_v2.db import engine, ensure_schema
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner
from ifa_data_platform.archive_v2.profile import ArchiveProfile


PROFILE_DIR = Path(tempfile.gettempdir()) / 'ifa_archive_v2_pytest_profiles'
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _profile_path(profile: ArchiveProfile) -> str:
    path = PROFILE_DIR / f"{profile.profile_name}.json"
    path.write_text(json.dumps(profile.__dict__, ensure_ascii=False, indent=2))
    return str(path)


def _reset_state(profile_name_prefix: str) -> None:
    ensure_schema()
    with engine.begin() as conn:
        conn.execute(text("delete from ifa2.ifa_archive_run_items where run_id in (select run_id from ifa2.ifa_archive_runs where profile_name like :prefix)"), {'prefix': f'{profile_name_prefix}%'})
        conn.execute(text("delete from ifa2.ifa_archive_runs where profile_name like :prefix"), {'prefix': f'{profile_name_prefix}%'})
        conn.execute(text("delete from ifa2.ifa_archive_profiles where profile_name like :prefix"), {'prefix': f'{profile_name_prefix}%'})
        conn.execute(text("delete from ifa2.ifa_archive_completeness where family_name in ('index_daily', 'sector_performance_daily')"))
        conn.execute(text("delete from ifa2.ifa_archive_repair_queue where family_name in ('index_daily', 'sector_performance_daily')"))
        conn.execute(text("delete from ifa2.trade_cal_current where cal_date between '2026-04-16' and '2026-04-20' and exchange='SSE'"))
        conn.execute(text("delete from ifa2.index_daily_bar_history where trade_date between '2026-04-16' and '2026-04-20' and ts_code in ('000001.SH', '399001.SZ')"))
        conn.execute(text("delete from ifa2.index_daily_bar_history where id in ('00000000-0000-0000-0000-000000000211','00000000-0000-0000-0000-000000000212','00000000-0000-0000-0000-000000000221','00000000-0000-0000-0000-000000000222','00000000-0000-0000-0000-000000000223','00000000-0000-0000-0000-000000000224','00000000-0000-0000-0000-000000000225')"))
        conn.execute(text("delete from ifa2.trade_cal_current where id='00000000-0000-0000-0000-000000000201'"))


def test_archive_v2_dry_run_is_side_effect_free_and_tracks_would_write_metrics() -> None:
    _reset_state('pytest_archive_v2_dry_run')
    profile = ArchiveProfile(
        profile_name='pytest_archive_v2_dry_run',
        mode='single_day',
        family_groups=['index_daily'],
        start_date='2026-04-17',
        dry_run=True,
        write_enabled=True,
    )
    runner = ArchiveV2Runner(_profile_path(profile))
    runner._execute_family = lambda family, business_date: (8, ['ifa_archive_index_daily'], 'completed', 'expected=8 actual=8 coverage=1.000', None)

    result = runner.run_with_context(trigger_source='pytest_archive_v2_dry_run')

    assert result['ok'] is True
    with engine.begin() as conn:
        run_row = conn.execute(text("select dry_run, status from ifa2.ifa_archive_runs where run_id=cast(:run_id as uuid)"), {'run_id': result['run_id']}).mappings().one()
        item = conn.execute(text("select rows_written, would_write_rows, tables_touched, would_write_tables from ifa2.ifa_archive_run_items where run_id=cast(:run_id as uuid)"), {'run_id': result['run_id']}).mappings().one()
        profile_count = conn.execute(text("select count(*) from ifa2.ifa_archive_profiles where profile_name='pytest_archive_v2_dry_run'" )).scalar_one()
        completeness_count = conn.execute(text("select count(*) from ifa2.ifa_archive_completeness where family_name='index_daily' and business_date='2026-04-17'" )).scalar_one()
        queue_count = conn.execute(text("select count(*) from ifa2.ifa_archive_repair_queue where family_name='index_daily' and business_date='2026-04-17'" )).scalar_one()
    assert run_row['dry_run'] is True
    assert run_row['status'] == 'completed'
    assert item['rows_written'] == 0
    assert item['would_write_rows'] == 8
    assert item['tables_touched'] == []
    assert item['would_write_tables'] == ['ifa_archive_index_daily']
    assert profile_count == 0
    assert completeness_count == 0
    assert queue_count == 0


def test_archive_v2_historical_range_and_backfill_use_trading_days_with_observed_calendar_fallback() -> None:
    _reset_state('pytest_archive_v2_calendar')
    with engine.begin() as conn:
        conn.execute(text("""
            insert into ifa2.trade_cal_current(id, cal_date, exchange, is_open, pretrade_date)
            values
              ('00000000-0000-0000-0000-000000000201', '2026-04-20', 'SSE', 1, '2026-04-17')
        """))
        conn.execute(text("""
            insert into ifa2.index_daily_bar_history(id, version_id, trade_date, ts_code)
            values
              ('00000000-0000-0000-0000-000000000211', 'pytest', '2026-04-17', '000001.SH'),
              ('00000000-0000-0000-0000-000000000212', 'pytest', '2026-04-20', '399001.SZ')
        """))

    profile = ArchiveProfile(
        profile_name='pytest_archive_v2_calendar',
        mode='date_range',
        family_groups=['index_daily'],
        start_date='2026-04-17',
        end_date='2026-04-20',
    )
    runner = ArchiveV2Runner(_profile_path(profile))
    assert runner._expand_date_range(['index_daily']) == ['2026-04-17', '2026-04-20']

    backfill_profile = ArchiveProfile(
        profile_name='pytest_archive_v2_calendar_backfill',
        mode='backfill',
        family_groups=['index_daily'],
        end_date='2026-04-20',
        backfill_days=2,
    )
    backfill_runner = ArchiveV2Runner(_profile_path(backfill_profile))
    assert backfill_runner._resolve_backfill_dates(['index_daily']) == ['2026-04-17', '2026-04-20']


def test_archive_v2_backfill_fills_sparse_historical_calendar_with_weekday_fallback() -> None:
    _reset_state('pytest_archive_v2_sparse_backfill')
    with engine.begin() as conn:
        conn.execute(text("""
            insert into ifa2.index_daily_bar_history(id, version_id, trade_date, ts_code)
            values
              ('00000000-0000-0000-0000-000000000221', 'pytest', '2026-04-14', '000001.SH'),
              ('00000000-0000-0000-0000-000000000222', 'pytest', '2026-04-15', '000001.SH'),
              ('00000000-0000-0000-0000-000000000223', 'pytest', '2026-04-16', '000001.SH'),
              ('00000000-0000-0000-0000-000000000224', 'pytest', '2026-04-17', '000001.SH'),
              ('00000000-0000-0000-0000-000000000225', 'pytest', '2026-04-20', '000001.SH')
        """))

    backfill_profile = ArchiveProfile(
        profile_name='pytest_archive_v2_sparse_backfill',
        mode='backfill',
        family_groups=['index_daily'],
        end_date='2026-04-20',
        backfill_days=10,
    )
    backfill_runner = ArchiveV2Runner(_profile_path(backfill_profile))
    assert backfill_runner._resolve_backfill_dates(['index_daily']) == [
        '2026-04-07',
        '2026-04-08',
        '2026-04-09',
        '2026-04-10',
        '2026-04-13',
        '2026-04-14',
        '2026-04-15',
        '2026-04-16',
        '2026-04-17',
        '2026-04-20',
    ]


def test_archive_v2_stale_running_runs_are_auto_closed_before_new_execution() -> None:
    _reset_state('pytest_archive_v2_stale')
    with engine.begin() as conn:
        conn.execute(text("""
            insert into ifa2.ifa_archive_runs(run_id, trigger_source, profile_name, profile_path, mode, start_time, status, notes, dry_run)
            values ('00000000-0000-0000-0000-000000000111', 'pytest', 'pytest_archive_v2_stale_old', '/tmp/old.json', 'single_day', now() - interval '10 minutes', 'running', 'stale', false)
        """))

    profile = ArchiveProfile(
        profile_name='pytest_archive_v2_stale_new',
        mode='single_day',
        family_groups=['index_daily'],
        start_date='2026-04-17',
        dry_run=True,
        write_enabled=True,
    )
    runner = ArchiveV2Runner(_profile_path(profile))
    runner._execute_family = lambda family, business_date: (1, ['ifa_archive_index_daily'], 'completed', 'expected=1 actual=1 coverage=1.000', None)
    runner.run_with_context(trigger_source='pytest_archive_v2_stale_new')

    with engine.begin() as conn:
        stale = conn.execute(text("select status, end_time is not null as has_end_time, error_text from ifa2.ifa_archive_runs where run_id='00000000-0000-0000-0000-000000000111'" )).mappings().one()
    assert stale['status'] == 'aborted'
    assert stale['has_end_time'] is True
    assert 'auto-closed stale running run' in stale['error_text']


def test_archive_v2_operator_surfaces_expose_actual_vs_would_write_and_family_coverage() -> None:
    _reset_state('pytest_archive_v2_operator')
    profile = ArchiveProfile(
        profile_name='pytest_archive_v2_operator',
        mode='single_day',
        family_groups=['sector_performance_daily'],
        start_date='2026-04-17',
        dry_run=False,
        write_enabled=True,
    )
    runner = ArchiveV2Runner(_profile_path(profile))
    runner._execute_family = lambda family, business_date: (80, ['ifa_archive_sector_performance_daily'], 'incomplete', 'ths_index+ths_daily supported-universe expected=100 actual=80 coverage=0.800 threshold=0.900 excluded_types=I,BB', None)
    result = runner.run_with_context(trigger_source='pytest_archive_v2_operator')

    with engine.begin() as conn:
        recent = conn.execute(text("select dry_run, rows_written, would_write_rows from ifa2.ifa_archive_operator_recent_runs_v where run_id=cast(:run_id as uuid)"), {'run_id': result['run_id']}).mappings().one()
        family = conn.execute(text("select worst_family_coverage_ratio, latest_family_expected_rows, latest_family_observed_rows from ifa2.ifa_archive_operator_family_health_v where family_name='sector_performance_daily' and frequency='daily'" )).mappings().one()
        gap = conn.execute(text("select family_expected_rows, family_observed_rows, family_coverage_ratio from ifa2.ifa_archive_operator_gap_summary_v where family_name='sector_performance_daily' and business_date='2026-04-17'" )).mappings().one()
    assert recent['dry_run'] is False
    assert recent['rows_written'] == 80
    assert recent['would_write_rows'] == 80
    assert float(family['worst_family_coverage_ratio']) == 0.8
    assert family['latest_family_expected_rows'] == 100
    assert family['latest_family_observed_rows'] == 80
    assert gap['family_expected_rows'] == 100
    assert gap['family_observed_rows'] == 80
    assert float(gap['family_coverage_ratio']) == 0.8


def test_archive_v2_business_contract_bulk_first_fetchers_use_single_day_calls() -> None:
    profile = ArchiveProfile(
        profile_name='pytest_archive_v2_bulk_fetchers',
        mode='single_day',
        family_groups=['sector_performance_daily'],
        start_date='2026-04-17',
        dry_run=True,
        write_enabled=False,
    )
    runner = ArchiveV2Runner(_profile_path(profile))
    calls: list[tuple[str, dict]] = []

    def fake_query(api_name: str, params: dict, timeout_sec: int = 30, max_retries: int = 2):
        calls.append((api_name, dict(params)))
        if api_name == 'anns_d':
            return [{'ann_date': '20260417', 'ts_code': '000001.SZ', 'title': 'a1', 'url': 'u1'}]
        if api_name == 'research_report':
            return [{'trade_date': '20260417', 'title': 'r1', 'report_type': '个股研报', 'author': 'a', 'ts_code': '000001.SZ', 'inst_csname': 'b'}]
        if api_name == 'limit_list_d':
            return [{'trade_date': '20260417', 'ts_code': '000001.SZ', 'limit': 'U', 'first_time': '093000', 'last_time': '145500', 'limit_times': 1}]
        if api_name == 'ths_daily':
            return [{'ts_code': '885001.TI', 'trade_date': '20260417', 'close': 1.0}]
        raise AssertionError(f'unexpected api call: {api_name} {params}')

    runner.client = SimpleNamespace(query=fake_query)
    runner._load_ths_sector_universe = lambda: [{'ts_code': '885001.TI', 'name': 'Sector1', 'type': 'N'}]

    announcements = runner._fetch_announcements_contract_rows('2026-04-17')
    research = runner._fetch_research_reports_contract_rows('2026-04-17')
    limit_detail = runner._fetch_limit_up_detail_contract_rows('2026-04-17')
    sector = runner._fetch_sector_performance_contract_rows('2026-04-17')

    assert announcements['status'] == 'completed'
    assert research['status'] == 'completed'
    assert limit_detail['status'] == 'completed'
    assert sector['status'] == 'completed'
    assert calls == [
        ('anns_d', {'ann_date': '20260417'}),
        ('research_report', {'trade_date': '20260417'}),
        ('limit_list_d', {'trade_date': '20260417'}),
        ('ths_daily', {'trade_date': '20260417'}),
    ]
