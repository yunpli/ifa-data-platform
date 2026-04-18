from __future__ import annotations

import json
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text

from ifa_data_platform.archive_v2.db import ensure_schema

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
ensure_schema()

INTRADAY_TABLES = [
    'ifa_archive_equity_60m', 'ifa_archive_index_60m',
    'ifa_archive_equity_15m', 'ifa_archive_index_15m',
    'ifa_archive_equity_1m', 'ifa_archive_index_1m',
]


def _run(*args: str) -> dict:
    proc = subprocess.run([str(PY), *args], cwd=REPO, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def _cleanup_intraday_scope() -> None:
    with ENGINE.begin() as conn:
        for table in INTRADAY_TABLES:
            conn.execute(text(f"delete from ifa2.{table} where business_date='2026-04-15'"))
        conn.execute(text("delete from ifa2.ifa_archive_completeness where business_date='2026-04-15' and family_name in ('equity_60m','index_60m','equity_15m','index_15m','equity_1m','index_1m') and frequency in ('60m','15m','1m') and coverage_scope='broad_market'"))
        conn.execute(text("delete from ifa2.ifa_archive_repair_queue where business_date='2026-04-15' and family_name in ('equity_60m','index_60m','equity_15m','index_15m','equity_1m','index_1m') and frequency in ('60m','15m','1m') and coverage_scope='broad_market'"))


def test_archive_v2_milestone10_intraday_layers_exist_and_write_rows() -> None:
    _cleanup_intraday_scope()
    payload = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone10_intraday_sample.json')
    assert payload['ok'] is True
    assert payload['status'] in {'completed', 'partial'}

    with ENGINE.begin() as conn:
        counts = {
            table: conn.execute(text(f"select count(*) from ifa2.{table} where business_date='2026-04-15'" )).scalar_one()
            for table in INTRADAY_TABLES
        }
        completeness = conn.execute(text("""
            select family_name, frequency, status, row_count
            from ifa2.ifa_archive_completeness
            where business_date='2026-04-15'
              and family_name in ('equity_60m','index_60m','equity_15m','index_15m','equity_1m','index_1m')
            order by frequency, family_name
        """)).mappings().all()
        run_items = conn.execute(text("""
            select frequency, sum(rows_written) as rows_written
            from ifa2.ifa_archive_run_items
            where run_id=cast(:run_id as uuid)
            group by frequency
        """), {'run_id': payload['run_id']}).mappings().all()
    rows_by_freq = {row['frequency']: int(row['rows_written']) for row in run_items}
    assert {row['frequency'] for row in completeness} == {'60m', '15m', '1m'}
    assert set(rows_by_freq) == {'60m', '15m', '1m'}
    assert rows_by_freq['60m'] > 0 and rows_by_freq['15m'] > 0 and rows_by_freq['1m'] > 0
    assert counts['ifa_archive_equity_60m'] + counts['ifa_archive_index_60m'] > 0
    assert counts['ifa_archive_equity_15m'] + counts['ifa_archive_index_15m'] > 0
    assert counts['ifa_archive_equity_1m'] + counts['ifa_archive_index_1m'] > 0


def test_archive_v2_milestone10_additive_60m_does_not_rerun_daily_layers() -> None:
    with ENGINE.begin() as conn:
        conn.execute(text("delete from ifa2.ifa_archive_index_daily where business_date='2026-04-15'"))
        conn.execute(text("delete from ifa2.ifa_archive_index_60m where business_date='2026-04-15'"))
        conn.execute(text("delete from ifa2.ifa_archive_completeness where business_date='2026-04-15' and family_name in ('index_daily','index_60m') and coverage_scope='broad_market'"))
        conn.execute(text("delete from ifa2.ifa_archive_repair_queue where business_date='2026-04-15' and family_name in ('index_daily','index_60m') and coverage_scope='broad_market'"))

    daily = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone10_daily_index_only.json')
    assert daily['ok'] is True
    assert daily['status'] == 'completed'

    intraday = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone10_add_60m_only.json')
    assert intraday['ok'] is True
    assert intraday['status'] == 'completed'

    with ENGINE.begin() as conn:
        intraday_items = conn.execute(text("select family_name, frequency from ifa2.ifa_archive_run_items where run_id=cast(:run_id as uuid) order by family_name"), {'run_id': intraday['run_id']}).mappings().all()
        daily_completeness = conn.execute(text("select status from ifa2.ifa_archive_completeness where business_date='2026-04-15' and family_name='index_daily' and frequency='daily' and coverage_scope='broad_market'" )).scalar_one()
        m60_completeness = conn.execute(text("select status from ifa2.ifa_archive_completeness where business_date='2026-04-15' and family_name='index_60m' and frequency='60m' and coverage_scope='broad_market'" )).scalar_one()
        m60_rows = conn.execute(text("select count(*) from ifa2.ifa_archive_index_60m where business_date='2026-04-15'" )).scalar_one()
    assert intraday_items == [{'family_name': 'index_60m', 'frequency': '60m'}]
    assert daily_completeness == 'completed'
    assert m60_completeness == 'completed'
    assert m60_rows > 0


def test_archive_v2_milestone10_profile_flags_drive_intraday_execution() -> None:
    dry = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone10_intraday_sample.json')
    assert dry['ok'] is True
    with ENGINE.begin() as conn:
        rows = conn.execute(text("""
            select distinct frequency
            from ifa2.ifa_archive_run_items
            where run_id=cast(:run_id as uuid)
            order by frequency
        """), {'run_id': dry['run_id']}).scalars().all()
    assert set(rows) == {'15m', '1m', '60m'}
