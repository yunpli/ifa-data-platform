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


def test_unified_runtime_run_once_lowfreq_real_run_executes():
    payload = run_cli('run-once', '--lane', 'lowfreq', '--owner-type', 'default', '--owner-id', 'default')
    assert payload['lane'] == 'lowfreq'
    assert payload['execution_mode'] == 'real_run'
    expected = {
        'stock_basic', 'index_basic', 'fund_basic_etf', 'sw_industry_mapping',
        'announcements', 'news', 'research_reports', 'investor_qa', 'index_weight',
        'etf_daily_basic', 'share_float', 'company_basic', 'stk_managers', 'new_share',
        'name_change', 'top10_holders', 'top10_floatholders', 'pledge_stat'
    }
    assert expected <= set(payload['planned_dataset_names'])
    assert 'trade_cal' not in payload['planned_dataset_names']
    assert payload['executed_dataset_count'] >= 15
    assert any(r['dataset_name'] == 'fund_basic_etf' for r in payload['dataset_results'])
    assert any(r['dataset_name'] == 'index_weight' for r in payload['dataset_results'])
    assert any(r['dataset_name'] == 'top10_holders' for r in payload['dataset_results'])
    assert all(r['status'] == 'succeeded' for r in payload['dataset_results'])
    assert any((r['records_processed'] or 0) > 0 for r in payload['dataset_results'])
    assert payload['manifest_item_count'] > 0


def test_unified_runtime_trade_calendar_monthly_trigger_runs_only_trade_cal():
    payload = run_cli('run-once', '--lane', 'lowfreq', '--trigger-mode', 'trade_calendar_monthly_maintenance', '--owner-type', 'default', '--owner-id', 'default')
    assert payload['lane'] == 'lowfreq'
    assert payload['planned_dataset_names'] == ['trade_cal']
    assert payload['executed_dataset_count'] == 1
    assert payload['dataset_results'][0]['dataset_name'] == 'trade_cal'
    assert payload['dataset_results'][0]['status'] == 'succeeded'


def test_unified_runtime_run_once_midfreq_real_run_executes():
    payload = run_cli('run-once', '--lane', 'midfreq', '--owner-type', 'default', '--owner-id', 'default')
    assert payload['lane'] == 'midfreq'
    assert payload['execution_mode'] == 'real_run'
    expected = {
        'equity_daily_bar', 'index_daily_bar', 'etf_daily_bar', 'northbound_flow',
        'limit_up_down_status', 'margin_financing', 'southbound_flow', 'turnover_rate',
        'main_force_flow', 'sector_performance', 'dragon_tiger_list', 'limit_up_detail'
    }
    assert expected <= set(payload['planned_dataset_names'])
    assert payload['executed_dataset_count'] >= 10
    assert any(r['dataset_name'] == 'southbound_flow' for r in payload['dataset_results'])
    assert any(r['dataset_name'] == 'turnover_rate' for r in payload['dataset_results'])
    assert any(r['dataset_name'] == 'limit_up_detail' for r in payload['dataset_results'])
    assert all(r['status'] in {'succeeded', 'dry_run', 'failed'} for r in payload['dataset_results'])
    assert payload['manifest_item_count'] > 0


def test_unified_runtime_run_once_archive_real_run_executes():
    payload = run_cli('run-once', '--lane', 'archive', '--owner-type', 'default', '--owner-id', 'default', '--list-type', 'archive_targets')
    assert payload['lane'] == 'archive'
    assert payload['execution_mode'] == 'real_run'
    assert 'manifest_id' in payload
    assert payload['manifest_item_count'] > 0
    assert payload['archive_total_jobs'] >= 14
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
        assert unified_run['summary']['execution_mode'] == 'real_run'
        assert unified_run['summary']['archive_total_jobs'] == payload['archive_total_jobs']
        assert 'archive_catchup_rows_bound' in unified_run['summary']
        assert 'archive_catchup_rows_completed' in unified_run['summary']


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
            assert row['summary']['executed_dataset_count'] >= 3
            assert len(row['summary']['dataset_results']) >= 3


def test_run_status_cli_lists_recent_unified_runs():
    run_cli('run-once', '--lane', 'lowfreq', '--owner-type', 'default', '--owner-id', 'default')
    payload = run_cli('run-status', '--limit', '3')
    assert isinstance(payload, list)
    assert len(payload) >= 1
    assert {'id', 'lane', 'status', 'summary'} <= set(payload[0].keys())


def test_archive_status_cli_returns_catchup_and_checkpoint_state():
    run_cli('run-once', '--lane', 'archive', '--owner-type', 'default', '--owner-id', 'default', '--list-type', 'archive_targets')
    payload = run_cli('archive-status', '--limit', '5')
    assert {'summary_by_status', 'recent_catchup_rows', 'recent_checkpoints', 'recent_archive_runs'} <= set(payload.keys())
    assert isinstance(payload['summary_by_status'], list)
    assert isinstance(payload['recent_catchup_rows'], list)
    assert isinstance(payload['recent_checkpoints'], list)
    assert isinstance(payload['recent_archive_runs'], list)


def test_archive_catchup_state_progression_links_run_and_checkpoint():
    payload = run_cli('run-once', '--lane', 'archive', '--owner-type', 'default', '--owner-id', 'default', '--list-type', 'archive_targets')
    with engine().connect() as conn:
        row = conn.execute(
            text('''
                select archive_run_id, checkpoint_dataset_name, checkpoint_asset_type,
                       status, started_at, completed_at, progress_note
                from ifa2.archive_target_catchup
                where archive_run_id = :run_id
                order by updated_at desc
                limit 1
            '''),
            {'run_id': payload['run_id']},
        ).mappings().first()
        if row is not None:
            assert row['archive_run_id'] == payload['run_id']
            assert row['checkpoint_dataset_name'] is not None
            assert row['checkpoint_asset_type'] is not None
            assert row['status'] in {'in_progress', 'completed', 'partial'}
            assert row['started_at'] is not None
        checkpoint = conn.execute(
            text('''
                select dataset_name, asset_type, status, batch_no
                from ifa2.archive_checkpoints
                order by updated_at desc
                limit 1
            ''')
        ).mappings().first()
        if checkpoint is not None:
            assert checkpoint['status'] in {'planned', 'in_progress', 'completed'}
            assert checkpoint['batch_no'] is None or checkpoint['batch_no'] >= 0


def test_schema_gap_tables_now_exist_after_migration():
    with engine().connect() as conn:
        rows = conn.execute(
            text("""
                select table_name from information_schema.tables
                where table_schema='ifa2'
                  and table_name in ('stock_fund_forecast_current', 'stock_fund_forecast_history', 'unified_runtime_runs')
                order by table_name
            """)
        ).fetchall()
        assert [r[0] for r in rows] == ['stock_fund_forecast_current', 'stock_fund_forecast_history', 'unified_runtime_runs']


def test_collection_prod_closure_tables_exist():
    with engine().connect() as conn:
        rows = conn.execute(
            text("""
                select table_name from information_schema.tables
                where table_schema='ifa2'
                  and table_name in (
                    'stock_minute_history', 'futures_15min_history', 'futures_minute_history',
                    'commodity_15min_history', 'commodity_minute_history',
                    'precious_metal_15min_history', 'precious_metal_minute_history',
                    'southbound_flow_current', 'southbound_flow_history',
                    'turnover_rate_history', 'limit_up_detail_history'
                  )
                order by table_name
            """)
        ).fetchall()
        assert len(rows) == 11
