from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.runtime.replay_evidence import ReplayEvidenceStore, artifact_from_path

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PYTHON = REPO / '.venv' / 'bin' / 'python'
DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
TRADE_DATE = '2099-04-18'


def engine():
    return sa.create_engine(DB_URL, future=True)


def run_cli(*args: str) -> dict:
    env = {
        'PYTHONPATH': str(REPO / 'src'),
        'DATABASE_URL': DB_URL,
        'IFA_DB_SCHEMA': 'ifa2',
        **os.environ,
    }
    p = subprocess.run(
        [str(PYTHON), str(REPO / 'scripts' / 'slot_replay_evidence_cli.py'), *args],
        cwd=str(REPO),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(p.stdout)


def _insert_manifest(conn, manifest_id: str, owner_suffix: str) -> str:
    manifest_hash = f'{manifest_id:0<64}'[:64]
    conn.execute(
        text(
            """
            INSERT INTO ifa2.target_manifest_snapshots (
                id, manifest_hash, generated_at, owner_type, owner_id,
                selector_scope, item_count, payload
            ) VALUES (
                CAST(:id AS uuid), :manifest_hash, now(), 'test', :owner_id,
                CAST(:selector_scope AS jsonb), 1, CAST(:payload AS jsonb)
            )
            ON CONFLICT (manifest_hash) DO NOTHING
            """
        ),
        {
            'id': manifest_id,
            'manifest_hash': manifest_hash,
            'owner_id': f'owner-{owner_suffix}',
            'selector_scope': json.dumps({'owner_type': 'test', 'owner_id': f'owner-{owner_suffix}'}),
            'payload': json.dumps({'manifest_id': manifest_hash[:16], 'manifest_hash': manifest_hash, 'items': [], 'selector_scope': {'owner_type': 'test', 'owner_id': f'owner-{owner_suffix}'}}),
        },
    )
    return manifest_hash


def _insert_run(conn, *, run_id: str, manifest_id: str, manifest_hash: str, lane: str, started_at: str, completed_at: str, schedule_key: str | None, triggered_time: str | None, summary: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO ifa2.unified_runtime_runs (
                id, lane, worker_type, trigger_mode, manifest_snapshot_id,
                manifest_id, manifest_hash, status, started_at, completed_at,
                records_processed, summary, created_at, schedule_key,
                triggered_for_beijing_time, runtime_budget_sec, duration_ms,
                governance_state, error_count, tables_updated, tasks_executed
            ) VALUES (
                CAST(:id AS uuid), :lane, :worker_type, 'test_trigger', CAST(:manifest_snapshot_id AS uuid),
                :manifest_id, :manifest_hash, 'succeeded', :started_at, :completed_at,
                :records_processed, CAST(:summary AS jsonb), :created_at, :schedule_key,
                :triggered_for_beijing_time, 900, 1111,
                'ok', 0, CAST(:tables_updated AS jsonb), CAST(:tasks_executed AS jsonb)
            )
            """
        ),
        {
            'id': run_id,
            'lane': lane,
            'worker_type': f'{lane}_test_worker',
            'manifest_snapshot_id': manifest_id,
            'manifest_id': manifest_hash[:16],
            'manifest_hash': manifest_hash,
            'started_at': started_at,
            'completed_at': completed_at,
            'records_processed': sum(int((x or {}).get('records_processed') or 0) for x in summary.get('dataset_results', [])),
            'summary': json.dumps(summary),
            'created_at': started_at,
            'schedule_key': schedule_key,
            'triggered_for_beijing_time': triggered_time,
            'tables_updated': json.dumps(['ifa2.unified_runtime_runs']),
            'tasks_executed': json.dumps([x.get('dataset_name') for x in summary.get('dataset_results', [])]),
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO ifa2.job_runs (id, job_name, status, started_at, completed_at, error_message, records_processed, created_at)
            VALUES (CAST(:id AS uuid), :job_name, 'succeeded', :started_at, :completed_at, NULL, 0, :created_at)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {'id': run_id, 'job_name': f'test:{lane}', 'started_at': started_at, 'completed_at': completed_at, 'created_at': started_at},
    )


def test_slot_replay_evidence_capture_observed_and_corrected_selection(tmp_path: Path):
    store = ReplayEvidenceStore()
    store.ensure_schema()
    owner_suffix = str(uuid.uuid4())[:8]
    manifest_id = str(uuid.uuid4())
    run_early = str(uuid.uuid4())
    run_corrected = str(uuid.uuid4())
    run_mid = str(uuid.uuid4())
    manifest_hash = None
    observed = None
    corrected = None
    artifact_path = tmp_path / 'report.html'
    artifact_path.write_text('<html><body>slot replay evidence</body></html>')
    with engine().begin() as conn:
        manifest_hash = _insert_manifest(conn, manifest_id, owner_suffix)
        _insert_run(
            conn,
            run_id=run_early,
            manifest_id=manifest_id,
            manifest_hash=manifest_hash,
            lane='highfreq',
            started_at='2099-04-18T01:27:00+00:00',
            completed_at='2099-04-18T01:28:00+00:00',
            schedule_key='highfreq:trade_day_0927',
            triggered_time='09:27',
            summary={'dataset_results': [{'dataset_name': 'close_auction_snapshot', 'status': 'succeeded', 'records_processed': 88, 'watermark': '2099-04-18T09:27:00+08:00'}]},
        )
        _insert_run(
            conn,
            run_id=run_corrected,
            manifest_id=manifest_id,
            manifest_hash=manifest_hash,
            lane='highfreq',
            started_at='2099-04-18T02:15:00+00:00',
            completed_at='2099-04-18T02:16:00+00:00',
            schedule_key='highfreq:trade_day_1015',
            triggered_time='10:15',
            summary={'dataset_results': [{'dataset_name': 'close_auction_snapshot', 'status': 'succeeded', 'records_processed': 99, 'watermark': '2099-04-18T10:15:00+08:00'}]},
        )
        _insert_run(
            conn,
            run_id=run_mid,
            manifest_id=manifest_id,
            manifest_hash=manifest_hash,
            lane='midfreq',
            started_at='2099-04-18T05:05:00+00:00',
            completed_at='2099-04-18T05:06:00+00:00',
            schedule_key='midfreq:trade_day_1305',
            triggered_time='13:05',
            summary={'dataset_results': [{'dataset_name': 'limit_up_detail', 'status': 'succeeded', 'records_processed': 12, 'watermark': '2099-04-18'}]},
        )
    try:
        observed = store.capture_slot_evidence(
            trade_date=TRADE_DATE,
            slot_key='early',
            perspective='observed',
            capture_reason='test_capture',
            artifact=artifact_from_path(str(artifact_path), producer='pytest'),
            notes='observed snapshot',
        )
        corrected = store.capture_slot_evidence(
            trade_date=TRADE_DATE,
            slot_key='early',
            perspective='corrected',
            capture_reason='test_capture',
            notes='corrected snapshot',
        )

        observed_runs = observed['linked_runs']
        corrected_runs = corrected['linked_runs']
        assert [r['run_id'] for r in observed_runs] == [run_early]
        assert run_corrected in [r['run_id'] for r in corrected_runs]
        assert run_mid in [r['run_id'] for r in corrected_runs]
        observed_ds = next(x for x in observed['dataset_context']['datasets'] if x['dataset_name'] == 'close_auction_snapshot')
        corrected_ds = next(x for x in corrected['dataset_context']['datasets'] if x['dataset_name'] == 'close_auction_snapshot')
        assert observed_ds['watermark'] == '2099-04-18T09:27:00+08:00'
        assert corrected_ds['watermark'] == '2099-04-18T10:15:00+08:00'
        assert observed['artifact_context']['status'] == 'present'
        assert observed['artifact_context']['sha256']
        assert corrected['artifact_context']['status'] == 'pending_integration'

        listed = store.list_evidence(trade_date=TRADE_DATE, slot_key='early')
        ids = {str(row['id']) for row in listed}
        assert str(observed['id']) in ids
        assert str(corrected['id']) in ids
    finally:
        with engine().begin() as conn:
            evidence_ids = [str(x['id']) for x in (observed, corrected) if x]
            if evidence_ids:
                conn.execute(text("DELETE FROM ifa2.slot_replay_evidence_runs WHERE evidence_id = ANY(CAST(:ids AS uuid[]))"), {'ids': evidence_ids})
                conn.execute(text("DELETE FROM ifa2.slot_replay_evidence WHERE id = ANY(CAST(:ids AS uuid[]))"), {'ids': evidence_ids})
            conn.execute(text("DELETE FROM ifa2.unified_runtime_runs WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid), CAST(:c AS uuid))"), {'a': run_early, 'b': run_corrected, 'c': run_mid})
            conn.execute(text("DELETE FROM ifa2.job_runs WHERE id IN (CAST(:a AS uuid), CAST(:b AS uuid), CAST(:c AS uuid))"), {'a': run_early, 'b': run_corrected, 'c': run_mid})
            conn.execute(text("DELETE FROM ifa2.target_manifest_snapshots WHERE id = CAST(:id AS uuid)"), {'id': manifest_id})


def test_slot_replay_evidence_cli_capture_with_explicit_run_id(tmp_path: Path):
    store = ReplayEvidenceStore()
    store.ensure_schema()
    owner_suffix = str(uuid.uuid4())[:8]
    manifest_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    artifact_path = tmp_path / 'late.md'
    artifact_path.write_text('# late report')
    with engine().begin() as conn:
        manifest_hash = _insert_manifest(conn, manifest_id, owner_suffix)
        _insert_run(
            conn,
            run_id=run_id,
            manifest_id=manifest_id,
            manifest_hash=manifest_hash,
            lane='midfreq',
            started_at='2099-04-18T08:00:00+00:00',
            completed_at='2099-04-18T08:02:00+00:00',
            schedule_key='midfreq:trade_day_1600',
            triggered_time='16:00',
            summary={'dataset_results': [{'dataset_name': 'limit_up_detail', 'status': 'succeeded', 'records_processed': 18, 'watermark': '2099-04-18'}]},
        )
    try:
        payload = run_cli('capture', '--trade-date', TRADE_DATE, '--slot', 'late', '--perspective', 'observed', '--run-id', run_id, '--artifact-path', str(artifact_path), '--artifact-producer', 'pytest-cli')
        assert payload['slot_key'] == 'late'
        assert payload['linked_runs'][0]['run_id'] == run_id
        assert payload['artifact_context']['producer'] == 'pytest-cli'
        fetched = run_cli('get', str(payload['id']))
        assert fetched['id'] == payload['id']
    finally:
        with engine().begin() as conn:
            rows = conn.execute(text("SELECT id FROM ifa2.slot_replay_evidence WHERE trade_date=:trade_date AND slot_key='late' AND capture_reason='manual_capture' ORDER BY captured_at DESC LIMIT 5"), {'trade_date': TRADE_DATE}).scalars().all()
            if rows:
                conn.execute(text("DELETE FROM ifa2.slot_replay_evidence_runs WHERE evidence_id = ANY(CAST(:ids AS uuid[]))"), {'ids': [str(x) for x in rows]})
                conn.execute(text("DELETE FROM ifa2.slot_replay_evidence WHERE id = ANY(CAST(:ids AS uuid[]))"), {'ids': [str(x) for x in rows]})
            conn.execute(text("DELETE FROM ifa2.unified_runtime_runs WHERE id = CAST(:id AS uuid)"), {'id': run_id})
            conn.execute(text("DELETE FROM ifa2.job_runs WHERE id = CAST(:id AS uuid)"), {'id': run_id})
            conn.execute(text("DELETE FROM ifa2.target_manifest_snapshots WHERE id = CAST(:id AS uuid)"), {'id': manifest_id})
