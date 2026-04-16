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


def test_highfreq_raw_layer_first_real_path_runs() -> None:
    payload = run_cli("run-once", "--lane", "highfreq", "--owner-type", "default", "--owner-id", "default")
    assert payload["lane"] == "highfreq"
    results = {r["dataset_name"]: r for r in payload["dataset_results"]}
    assert results["stock_1m_ohlcv"]["status"] == "succeeded"
    assert results["open_auction_snapshot"]["status"] == "succeeded"
    assert results["close_auction_snapshot"]["status"] == "succeeded"
    assert results["stock_1m_ohlcv"]["records_processed"] > 0


def test_highfreq_working_tables_populated() -> None:
    with ENGINE.connect() as conn:
        stock_count = conn.execute(text("select count(*) from ifa2.highfreq_stock_1m_working")).scalar_one()
        open_count = conn.execute(text("select count(*) from ifa2.highfreq_open_auction_working")).scalar_one()
        close_count = conn.execute(text("select count(*) from ifa2.highfreq_close_auction_working")).scalar_one()
        run_count = conn.execute(text("select count(*) from ifa2.highfreq_runs")).scalar_one()
    assert stock_count > 0
    assert open_count > 0
    assert close_count > 0
    assert run_count > 0
