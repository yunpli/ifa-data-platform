from __future__ import annotations

import json
import os
import subprocess

from sqlalchemy import create_engine, text

REPO = "/Users/neoclaw/repos/ifa-data-platform"
ENV = {
    **os.environ,
    "PYTHONPATH": "src",
    "DATABASE_URL": "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp",
    "IFA_DB_SCHEMA": "ifa2",
}
ENGINE = create_engine("postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp", future=True)


def test_highfreq_health_and_watchdog_exist() -> None:
    for args in (["python", "src/ifa_data_platform/highfreq/daemon.py", "--health"], ["python", "src/ifa_data_platform/highfreq/daemon.py", "--watchdog"]):
        proc = subprocess.run(args, cwd=REPO, env=ENV, capture_output=True, text=True, check=True)
        payload = json.loads(proc.stdout)
        assert "status" in payload


def test_highfreq_schedule_state_tables_populated() -> None:
    with ENGINE.connect() as conn:
        daemon_rows = conn.execute(text("select count(*) from ifa2.highfreq_daemon_state")).scalar_one()
        window_rows = conn.execute(text("select count(*) from ifa2.highfreq_window_state")).scalar_one()
        summary_rows = conn.execute(text("select count(*) from ifa2.highfreq_execution_summary")).scalar_one()
    assert daemon_rows > 0
    assert window_rows > 0
    assert summary_rows > 0
