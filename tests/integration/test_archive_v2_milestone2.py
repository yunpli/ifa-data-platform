from __future__ import annotations

import json
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def test_archive_v2_milestone2_writes_real_daily_archive_rows():
    proc = subprocess.run(
        [str(PY), 'scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_daily_write_sample.json'],
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
        run = conn.execute(text('select status, profile_name from ifa2.ifa_archive_runs where run_id=:r'), {'r': run_id}).mappings().one()
        assert run['status'] == 'partial'
        equity = conn.execute(text("select count(*) from ifa2.ifa_archive_equity_daily where business_date='2026-04-17'" )).scalar_one()
        etf = conn.execute(text("select count(*) from ifa2.ifa_archive_etf_daily where business_date='2026-04-17'" )).scalar_one()
        non_eq = conn.execute(text("select count(*) from ifa2.ifa_archive_non_equity_daily where business_date='2026-04-17'" )).scalar_one()
        macro = conn.execute(text("select count(*) from ifa2.ifa_archive_macro_daily where business_date='2026-04-17'" )).scalar_one()
        assert equity > 0
        assert etf > 0
        assert macro > 0
        incomplete_item = conn.execute(text("select count(*) from ifa2.ifa_archive_run_items where run_id=:r and status='incomplete'"), {'r': run_id}).scalar_one()
        assert incomplete_item > 0
