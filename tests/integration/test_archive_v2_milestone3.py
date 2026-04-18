from __future__ import annotations

import json
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def test_archive_v2_milestone3_writes_index_and_business_daily_archive_rows():
    proc = subprocess.run(
        [str(PY), 'scripts/archive_v2_run.py', '--profile', 'profiles/archive_v2_daily_business_write_sample.json'],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload['ok'] is True
    assert payload['status'] == 'completed'
    run_id = payload['run_id']
    with engine.begin() as conn:
        run = conn.execute(text('select status, profile_name from ifa2.ifa_archive_runs where run_id=:r'), {'r': run_id}).mappings().one()
        assert run['status'] == 'completed'
        counts = {
            'ifa_archive_index_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_index_daily where business_date='2026-04-17'" )).scalar_one(),
            'ifa_archive_announcements_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_announcements_daily where business_date='2026-04-17'" )).scalar_one(),
            'ifa_archive_news_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_news_daily where business_date='2026-04-17'" )).scalar_one(),
            'ifa_archive_research_reports_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_research_reports_daily where business_date='2026-04-17'" )).scalar_one(),
            'ifa_archive_investor_qa_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_investor_qa_daily where business_date='2026-04-17'" )).scalar_one(),
            'ifa_archive_dragon_tiger_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_dragon_tiger_daily where business_date='2026-04-17'" )).scalar_one(),
            'ifa_archive_limit_up_detail_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_limit_up_detail_daily where business_date='2026-04-17'" )).scalar_one(),
            'ifa_archive_limit_up_down_status_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_limit_up_down_status_daily where business_date='2026-04-17'" )).scalar_one(),
            'ifa_archive_sector_performance_daily': conn.execute(text("select count(*) from ifa2.ifa_archive_sector_performance_daily where business_date='2026-04-17'" )).scalar_one(),
        }
        for value in counts.values():
            assert value > 0
        incomplete_item = conn.execute(text("select count(*) from ifa2.ifa_archive_run_items where run_id=:r and status='incomplete'"), {'r': run_id}).scalar_one()
        assert incomplete_item == 0
