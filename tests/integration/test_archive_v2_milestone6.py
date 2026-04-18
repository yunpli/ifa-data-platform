from __future__ import annotations

import json
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text

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


def test_archive_v2_milestone6_broad_validation_and_operator_recent_runs() -> None:
    payload = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_broad_range_history_write_sample.json')
    assert payload['ok'] is True
    assert payload['status'] == 'completed'

    _run('scripts/runtime_manifest_cli.py', 'run-once', '--lane', 'highfreq', '--owner-type', 'default', '--owner-id', 'default')
    highfreq = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_highfreq_selected_write_sample.json')
    assert highfreq['ok'] is True
    assert highfreq['status'] == 'completed'

    recent = _run('scripts/archive_v2_operator_cli.py', 'recent-runs', '--limit', '6')
    family_health = _run('scripts/archive_v2_operator_cli.py', 'family-health', '--limit', '20')

    assert any(row['profile_name'] == 'archive_v2_milestone6_broad_range_history_write_sample' for row in recent)
    assert any(row['profile_name'] == 'archive_v2_milestone6_highfreq_selected_write_sample' for row in recent)
    assert any(row['family_name'] == 'dragon_tiger_daily' and row['completed_dates'] >= 3 for row in family_health)
    assert any(row['family_name'] == 'highfreq_event_stream_daily' and row['completed_dates'] >= 1 for row in family_health)


def test_archive_v2_milestone6_backfill_and_operator_alignment() -> None:
    _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_broad_range_history_write_sample.json')
    with ENGINE.begin() as conn:
        conn.execute(text("delete from ifa2.ifa_archive_research_reports_daily where business_date='2026-04-16'"))
        conn.execute(text("delete from ifa2.ifa_archive_dragon_tiger_daily where business_date='2026-04-17'"))
        conn.execute(text("delete from ifa2.ifa_archive_completeness where business_date='2026-04-16' and family_name='research_reports_daily' and frequency='daily' and coverage_scope='broad_market'"))
        conn.execute(text("delete from ifa2.ifa_archive_completeness where business_date='2026-04-17' and family_name='dragon_tiger_daily' and frequency='daily' and coverage_scope='broad_market'"))

    payload = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_broad_backfill_write_sample.json')
    assert payload['ok'] is True
    assert payload['status'] == 'completed'

    gaps = _run('scripts/archive_v2_operator_cli.py', 'gaps', '--days', '14')
    backlog = _run('scripts/archive_v2_operator_cli.py', 'repair-backlog', '--limit', '50')

    assert not any(row['family_name'] == 'research_reports_daily' and str(row['business_date']) == '2026-04-16' for row in gaps)
    assert not any(row['family_name'] == 'dragon_tiger_daily' and str(row['business_date']) == '2026-04-17' for row in gaps)
    assert not any(row['family_name'] == 'research_reports_daily' and str(row['business_date']) == '2026-04-16' for row in backlog)
    assert not any(row['family_name'] == 'dragon_tiger_daily' and str(row['business_date']) == '2026-04-17' for row in backlog)


def test_archive_v2_milestone6_retry_policy_and_operator_summary_surface() -> None:
    first = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_incomplete_policy_sample.json')
    second = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone6_incomplete_policy_sample.json')
    assert first['ok'] is True and second['ok'] is True
    assert first['status'] == 'partial' and second['status'] == 'partial'

    backlog = _run('scripts/archive_v2_operator_cli.py', 'repair-backlog', '--limit', '20')
    summary = _run('scripts/archive_v2_operator_cli.py', 'summary', '--days', '14', '--limit', '10')

    target = next(row for row in backlog if row['family_name'] == 'sector_performance_daily' and str(row['business_date']) == '2026-04-15')
    assert target['reason_code'] == 'source_empty'
    assert target['retry_count'] >= 2
    assert target['priority'] >= 65
    assert target['urgency'] in {'normal', 'high', 'critical'}
    assert target['escalation_level'] >= 1
    assert '2026-04-15' in summary['incomplete_dates']
    assert summary['repair_backlog_count'] >= 1
    assert any(row['family_name'] == 'sector_performance_daily' for row in summary['repair_backlog'])
