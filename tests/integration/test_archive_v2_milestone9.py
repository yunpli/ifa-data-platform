from __future__ import annotations

import json
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text

from ifa_data_platform.runtime.schedule_policy import DEFAULT_SCHEDULE_POLICY

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def _run(*args: str) -> dict:
    proc = subprocess.run(
        [str(PY), *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def test_archive_v2_milestone9_production_runtime_path_and_manual_path_separation() -> None:
    nightly = _run('scripts/archive_v2_production_cli.py', 'nightly', '--business-date', '2026-04-17')
    assert nightly['ok'] is True
    assert nightly['status'] in {'completed', 'partial'}

    runtime = _run('scripts/runtime_manifest_cli.py', 'run-once', '--lane', 'archive_v2', '--owner-type', 'default', '--owner-id', 'default')
    assert runtime['lane'] == 'archive_v2'
    assert runtime['legacy_archive_superseded_for_nightly'] is True
    assert runtime['archive_v2_status'] in {'completed', 'partial'}

    backfill = _run('scripts/archive_v2_production_cli.py', 'backfill', '--start-date', '2026-04-15', '--end-date', '2026-04-17')
    assert backfill['ok'] is True
    assert backfill['status'] in {'completed', 'partial'}

    with ENGINE.begin() as conn:
        triggers = conn.execute(text("""
            select trigger_source, count(*) as cnt
            from ifa2.ifa_archive_runs
            where trigger_source in ('production_nightly_archive_v2', 'runtime_archive_v2_nightly', 'manual_archive_v2_backfill', 'operator_repair_batch')
            group by trigger_source
        """)).mappings().all()
        seen = {row['trigger_source'] for row in triggers}
    assert 'production_nightly_archive_v2' in seen
    assert 'runtime_archive_v2_nightly' in seen
    assert 'manual_archive_v2_backfill' in seen


def test_archive_v2_milestone9_schedule_policy_makes_archive_v2_the_nightly_default() -> None:
    rows = {(row.worker_type, row.day_type): row for row in DEFAULT_SCHEDULE_POLICY}
    assert rows[('archive_v2', 'trading_day')].should_run is True
    assert rows[('archive', 'trading_day')].should_run is False
    assert 'nightly' in rows[('archive_v2', 'trading_day')].purpose.lower()
    assert 'production' in rows[('archive_v2', 'trading_day')].purpose.lower()
    assert 'legacy archive path' in rows[('archive', 'trading_day')].purpose.lower()


def test_archive_v2_milestone9_operator_surfaces_distinguish_nightly_vs_repair() -> None:
    _run('scripts/archive_v2_production_cli.py', 'nightly', '--business-date', '2026-04-17')
    recent = _run('scripts/archive_v2_operator_cli.py', 'recent-runs', '--limit', '20')
    run_status = _run('scripts/runtime_manifest_cli.py', 'run-status', '--lane', 'archive_v2', '--limit', '10')
    plan = _run('scripts/archive_v2_production_cli.py', 'plan', '--business-date', '2026-04-17')

    assert any(row['profile_name'] == 'archive_v2_production_nightly_daily_final' for row in recent)
    assert any(row['lane'] == 'archive_v2' for row in run_status)
    assert plan['nightly_profile_name'] == 'archive_v2_production_nightly_daily_final'
    assert plan['family_count'] >= 10
