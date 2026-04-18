from __future__ import annotations

import json
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def _run(*args: str) -> dict:
    proc = subprocess.run(
        [str(PY), *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def test_archive_v2_milestone4_writes_highfreq_archive_rows_and_marks_generic_catchall_truthfully():
    _run('scripts/runtime_manifest_cli.py', 'run-once', '--lane', 'highfreq', '--owner-type', 'default', '--owner-id', 'default')
    payload = _run('scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_milestone4_highfreq_write_sample.json')
    assert payload['ok'] is True
    assert payload['status'] == 'partial'
    run_id = payload['run_id']
    with engine.begin() as conn:
        run = conn.execute(text('select status, profile_name from ifa2.ifa_archive_runs where run_id=:r'), {'r': run_id}).mappings().one()
        assert run['status'] == 'partial'
        counts = {
            'ifa_archive_highfreq_event_stream_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_event_stream_daily where business_date='2026-04-15'" )).scalar_one(),
            'ifa_archive_highfreq_limit_event_stream_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_limit_event_stream_daily where business_date='2026-04-15'" )).scalar_one(),
            'ifa_archive_highfreq_sector_breadth_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_sector_breadth_daily where business_date='2026-04-15'" )).scalar_one(),
            'ifa_archive_highfreq_sector_heat_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_sector_heat_daily where business_date='2026-04-15'" )).scalar_one(),
            'ifa_archive_highfreq_leader_candidate_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_leader_candidate_daily where business_date='2026-04-15'" )).scalar_one(),
            'ifa_archive_highfreq_intraday_signal_state_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_highfreq_intraday_signal_state_daily where business_date='2026-04-15'" )).scalar_one(),
        }
        for value in counts.values():
            assert value > 0
        generic = conn.execute(text("select status, notes from ifa2.ifa_archive_run_items where run_id=:r and family_name='generic_structured_output_daily'"), {'r': run_id}).mappings().one()
        assert generic['status'] == 'incomplete'
        assert 'not archive-v2 worthy' in (generic['notes'] or '')
        completeness = conn.execute(text("select status, last_error from ifa2.ifa_archive_completeness where business_date='2026-04-15' and family_name='generic_structured_output_daily'" )).mappings().one()
        assert completeness['status'] == 'incomplete'
        assert 'not archive-v2 worthy' in (completeness['last_error'] or '')
