import json
import subprocess
from pathlib import Path

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PYTHON = REPO / '.venv' / 'bin' / 'python'


def run_cli(*args: str) -> dict:
    env = {
        'PYTHONPATH': str(REPO / 'src'),
        'DATABASE_URL': 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp',
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


def test_manifest_cli_outputs_default_scope_manifest():
    payload = run_cli('manifest', '--owner-type', 'default', '--owner-id', 'default')
    assert payload['item_count'] > 0
    assert payload['manifest_id']


def test_unified_runtime_run_once_lowfreq_manifest_only():
    payload = run_cli('run-once', '--lane', 'lowfreq', '--owner-type', 'default', '--owner-id', 'default', '--manifest-only')
    assert payload['lane'] == 'lowfreq'
    assert payload['mode'] == 'dry_run_manifest_only'
    assert payload['manifest_item_count'] > 0


def test_unified_runtime_run_once_archive_dry_run_executes():
    payload = run_cli('run-once', '--lane', 'archive', '--owner-type', 'default', '--owner-id', 'default', '--list-type', 'archive_targets')
    assert payload['lane'] == 'archive'
    assert 'manifest_id' in payload
    assert payload['manifest_item_count'] > 0
