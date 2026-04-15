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


def test_unified_runtime_run_once_lowfreq_dry_run_executes():
    payload = run_cli('run-once', '--lane', 'lowfreq', '--owner-type', 'default', '--owner-id', 'default')
    assert payload['lane'] == 'lowfreq'
    assert 'stock_basic' in payload['planned_dataset_names']
    assert payload['executed_dataset_count'] >= 1
    assert any(r['dataset_name'] == 'stock_basic' for r in payload['dataset_results'])
    assert all(r['status'] in {'succeeded', 'dry_run'} for r in payload['dataset_results'])
    assert payload['manifest_item_count'] > 0


def test_unified_runtime_run_once_midfreq_dry_run_executes():
    payload = run_cli('run-once', '--lane', 'midfreq', '--owner-type', 'default', '--owner-id', 'default')
    assert payload['lane'] == 'midfreq'
    assert 'equity_daily_bar' in payload['planned_dataset_names']
    assert payload['executed_dataset_count'] >= 1
    assert any(r['dataset_name'] == 'equity_daily_bar' for r in payload['dataset_results'])
    assert all(r['status'] in {'succeeded', 'dry_run'} for r in payload['dataset_results'])
    assert payload['manifest_item_count'] > 0


def test_unified_runtime_run_once_archive_dry_run_executes():
    payload = run_cli('run-once', '--lane', 'archive', '--owner-type', 'default', '--owner-id', 'default', '--list-type', 'archive_targets')
    assert payload['lane'] == 'archive'
    assert 'manifest_id' in payload
    assert payload['manifest_item_count'] > 0
    assert payload['archive_total_jobs'] == 3
    assert payload['archive_catchup_rows_inserted'] >= 0


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
        assert catchups >= 0
        assert catchups == payload['archive_catchup_rows_inserted']
        unified_run = conn.execute(
            text('select lane, status, manifest_hash, summary from ifa2.unified_runtime_runs where id=:id'),
            {'id': payload['run_id']},
        ).mappings().first()
        assert unified_run is not None
        assert unified_run['lane'] == 'archive'
        assert unified_run['status'] in {'succeeded', 'partial'}
        assert unified_run['manifest_hash'] == payload['manifest_hash']
        assert unified_run['summary']['archive_total_jobs'] == payload['archive_total_jobs']


def test_unified_runtime_persists_runtime_audit_for_lowfreq_and_midfreq():
    lowfreq_payload = run_cli('run-once', '--lane', 'lowfreq', '--owner-type', 'default', '--owner-id', 'default')
    midfreq_payload = run_cli('run-once', '--lane', 'midfreq', '--owner-type', 'default', '--owner-id', 'default')
    with engine().connect() as conn:
        rows = conn.execute(
            text('''
                select id, lane, status, records_processed, summary
                from ifa2.unified_runtime_runs
                where id in (:lowfreq_id, :midfreq_id)
                order by lane
            '''),
            {'lowfreq_id': lowfreq_payload['run_id'], 'midfreq_id': midfreq_payload['run_id']},
        ).mappings().all()
        assert [row['lane'] for row in rows] == ['lowfreq', 'midfreq']
        for row in rows:
            assert row['status'] in {'succeeded', 'partial'}
            assert row['summary']['executed_dataset_count'] >= 1
            assert len(row['summary']['dataset_results']) >= 1


def test_schema_gap_tables_now_exist_after_migration():
    with engine().connect() as conn:
        rows = conn.execute(
            text("""
                select table_name from information_schema.tables
                where table_schema='ifa2'
                  and table_name in ('stock_fund_forecast_current', 'stock_fund_forecast_history')
                order by table_name
            """)
        ).fetchall()
        assert [r[0] for r in rows] == ['stock_fund_forecast_current', 'stock_fund_forecast_history']
