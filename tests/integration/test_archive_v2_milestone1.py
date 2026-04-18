from __future__ import annotations

import json
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def test_archive_v2_profile_validation_and_run_logging():
    proc = subprocess.run(
        [str(PY), 'scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_daily_skeleton.json'],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload['ok'] is True
    assert payload['status'] == 'partial'
    run_id = payload['run_id']
    with engine.begin() as conn:
        run = conn.execute(text('select status, mode, profile_name from ifa2.ifa_archive_runs where run_id=:r'), {'r': run_id}).mappings().one()
        assert run['status'] == 'partial'
        assert run['mode'] == 'single_day'
        items = conn.execute(text('select count(*) from ifa2.ifa_archive_run_items where run_id=:r'), {'r': run_id}).scalar_one()
        assert items > 0
        comp = conn.execute(text("select count(*) from ifa2.ifa_archive_completeness where business_date='2026-04-17'" )).scalar_one()
        assert comp > 0
