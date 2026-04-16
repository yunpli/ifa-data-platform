from __future__ import annotations

import json
import os
import subprocess

REPO = "/Users/neoclaw/repos/ifa-data-platform"
ENV = {
    **os.environ,
    "PYTHONPATH": "src",
    "DATABASE_URL": "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp",
    "IFA_DB_SCHEMA": "ifa2",
}


def run_cli(*args: str) -> dict:
    cmd = ["python", "scripts/runtime_manifest_cli.py", *args]
    proc = subprocess.run(cmd, cwd=REPO, env=ENV, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def test_highfreq_unified_runtime_skeleton_exists_and_runs() -> None:
    payload = run_cli("run-once", "--lane", "highfreq", "--owner-type", "default", "--owner-id", "default")
    assert payload["lane"] == "highfreq"
    assert payload["execution_mode"] == "skeleton_ready"
    assert payload["executed_dataset_count"] >= 5
    assert {"stock_1m_ohlcv", "index_1m_ohlcv", "event_time_stream"} <= set(payload["planned_dataset_names"])
    assert all(r["status"] == "skeleton_ready" for r in payload["dataset_results"])


def test_highfreq_run_status_surface_exists() -> None:
    payload = run_cli("run-status", "--lane", "highfreq", "--limit", "3")
    assert isinstance(payload, list)
