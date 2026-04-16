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


def _run(*args: str) -> dict:
    proc = subprocess.run(["python", "src/ifa_data_platform/highfreq/daemon.py", *args], cwd=REPO, env=ENV, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def test_highfreq_operator_status_surface_exists() -> None:
    payload = _run("--status")
    assert payload["lane"] == "highfreq"
    assert "latest_run" in payload
    assert "recent_windows" in payload


def test_highfreq_retention_surface_exists() -> None:
    payload = _run("--retention-run", "--keep-days", "30")
    assert payload["keep_days"] == 30
    assert "deleted_rows" in payload
