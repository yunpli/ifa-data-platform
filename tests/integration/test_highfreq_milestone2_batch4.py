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


def run_cli(*args: str) -> dict:
    cmd = ["python", "scripts/runtime_manifest_cli.py", *args]
    proc = subprocess.run(cmd, cwd=REPO, env=ENV, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def test_highfreq_futures_family_path_lands() -> None:
    payload = run_cli("run-once", "--lane", "highfreq", "--owner-type", "default", "--owner-id", "default")
    results = {r["dataset_name"]: r for r in payload["dataset_results"]}
    assert results["futures_commodity_pm_1m_ohlcv"]["status"] == "succeeded"
    assert results["futures_commodity_pm_1m_ohlcv"]["records_processed"] > 0


def test_highfreq_futures_family_working_table_populated() -> None:
    with ENGINE.connect() as conn:
        count = conn.execute(text("select count(*) from ifa2.highfreq_futures_minute_working")).scalar_one()
    assert count > 0
