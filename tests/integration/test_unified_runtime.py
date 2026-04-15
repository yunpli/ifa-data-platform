import json
import subprocess
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PYTHON = REPO / '.venv' / 'bin' / 'python'
DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'


def run_cli(*args: str) -> dict:
    env = {
        'PYTHONPATH': str(REPO / 'src'),
        'DATABASE_URL': DB_URL,
        'IFA_DB_SCHEMA': 'ifa2',
    }
    p = subprocess.run(
        [str(PYTHON), str(REPO / 'scripts' / 'runtime_manifest_cli.py'), *args],
        cwd=str(REPO),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(p.stdout)


def engine():
    return sa.create_engine(DB_URL, future=True)


def test_manifest_cli_outputs_default_scope_manifest():
    payload = run_cli('manifest', '--owner-type', 'default', '--owner-id', 'default')
    assert payload['item_count'] > 0
    assert payload['manifest_id']


def test_unified_runtime_run_once_lowfreq_manifest_only():
    payload = run_cli('run-once', '--lane', 'lowfreq', '--owner-type', 'default', '--owner-id', 'default', '--manifest-only')
    assert payload['lane'] == 'lowfreq'
    assert payload['mode'] == 'dry_run_manifest_only'
    assert payload['manifest_item_count'] > 0
    assert payload['manifest_snapshot_id']


def test_unified_runtime_run_once_archive_dry_run_executes():
    payload = run_cli('run-once', '--lane', 'archive', '--owner-type', 'default', '--owner-id', 'default', '--list-type', 'archive_targets')
    assert payload['lane'] == 'archive'
    assert 'manifest_id' in payload
    assert payload['manifest_item_count'] > 0
    assert payload['archive_total_jobs'] == 3
    assert payload['archive_catchup_rows_inserted'] >= 1


def test_unified_runtime_persists_manifest_snapshot_and_archive_catchup_rows():
    payload = run_cli('run-once', '--lane', 'archive', '--owner-type', 'default', '--owner-id', 'default', '--list-type', 'archive_targets')
    with engine().connect() as conn:
        snapshot = conn.execute(
            text('select manifest_hash, item_count from ifa2.target_manifest_snapshots where id=:id'),
            {'id': payload['manifest_snapshot_id']},
        ).mappings().first()
        assert snapshot is not None
        assert snapshot['manifest_hash'] == payload['manifest_hash']
        catchups = conn.execute(
            text('select count(*) from ifa2.archive_target_catchup where manifest_snapshot_id=:id'),
            {'id': payload['manifest_snapshot_id']},
        ).scalar_one()
        assert catchups >= 1
