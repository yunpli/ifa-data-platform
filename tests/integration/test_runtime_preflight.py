from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'
ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def test_runtime_preflight_outputs_findings_file(tmp_path: Path):
    out = tmp_path / 'preflight.json'
    subprocess.run([
        str(PY), 'scripts/runtime_preflight.py', '--out', str(out)
    ], cwd=REPO, check=True)
    payload = json.loads(out.read_text())
    assert 'generated_at' in payload
    assert 'findings' in payload
    assert 'summary' in payload
    assert 'trade_calendar' in payload
    assert 'trade_calendar_status' in payload['summary']
    assert isinstance(payload['findings'], list)


def test_unified_daemon_service_preflight_command_runs(tmp_path: Path):
    proc = subprocess.run(
        ['zsh', 'scripts/unified_daemon_service.sh', 'preflight'],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    assert 'total_findings' in proc.stdout


def test_unified_daemon_service_status_rejects_reused_pid(tmp_path: Path):
    sleeper = subprocess.Popen(['sleep', '30'])
    try:
        log_dir = tmp_path / 'service'
        pid_file = log_dir / 'unified_daemon.pid'
        log_dir.mkdir(parents=True)
        pid_file.write_text(f'{sleeper.pid}\n')

        proc = subprocess.run(
            ['zsh', 'scripts/unified_daemon_service.sh', 'status'],
            cwd=REPO,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                'LOG_DIR': str(log_dir),
                'PID_FILE': str(pid_file),
                'DAEMON_MATCH_PATTERN': 'ifa_data_platform.runtime.unified_daemon --loop --sentinel no-such-daemon',
            },
        )
        assert proc.returncode == 1
        assert 'stale_pid_file' in proc.stdout
        assert 'reason=command_mismatch' in proc.stdout
        assert f'pid={sleeper.pid}' in proc.stdout
        assert 'not_running reason=stale_pid_file' in proc.stdout
    finally:
        sleeper.terminate()
        sleeper.wait(timeout=5)


def test_unified_daemon_service_stop_clears_stale_pid_without_killing_other_process(tmp_path: Path):
    sleeper = subprocess.Popen(['sleep', '30'])
    try:
        log_dir = tmp_path / 'service'
        pid_file = log_dir / 'unified_daemon.pid'
        log_dir.mkdir(parents=True)
        pid_file.write_text(f'{sleeper.pid}\n')

        proc = subprocess.run(
            ['zsh', 'scripts/unified_daemon_service.sh', 'stop'],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
            env={
                **os.environ,
                'LOG_DIR': str(log_dir),
                'PID_FILE': str(pid_file),
                'DAEMON_MATCH_PATTERN': 'ifa_data_platform.runtime.unified_daemon --loop',
            },
        )
        assert 'cleared_stale_pid_file' in proc.stdout
        assert f'pid={sleeper.pid}' in proc.stdout
        assert pid_file.exists() is False
        assert sleeper.poll() is None
    finally:
        sleeper.terminate()
        sleeper.wait(timeout=5)


def test_unified_daemon_service_status_recovers_when_pid_file_is_stale_but_real_daemon_exists(tmp_path: Path):
    sentinel = 'test-status-recover-stale'
    stale = subprocess.Popen(['sleep', '30'])
    daemon = subprocess.Popen([
        'python3', '-c', 'import time; time.sleep(30)', '-m', 'ifa_data_platform.runtime.unified_daemon', '--loop', '--sentinel', sentinel
    ])
    try:
        log_dir = tmp_path / 'service'
        pid_file = log_dir / 'unified_daemon.pid'
        heartbeat_file = log_dir / 'unified_daemon.heartbeat.json'
        log_dir.mkdir(parents=True)
        pid_file.write_text(f'{stale.pid}\n')
        heartbeat_file.write_text(json.dumps({'pid': daemon.pid, 'generated_at': '2999-01-01T00:00:00+00:00', 'phase': 'running'}))

        proc = subprocess.run(
            ['zsh', 'scripts/unified_daemon_service.sh', 'status'],
            cwd=REPO,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                'LOG_DIR': str(log_dir),
                'PID_FILE': str(pid_file),
                'HEARTBEAT_FILE': str(heartbeat_file),
                'DAEMON_MATCH_PATTERN': f'ifa_data_platform.runtime.unified_daemon --loop --sentinel {sentinel}',
            },
        )
        assert proc.returncode == 0
        assert 'stale_pid_file' in proc.stdout
        assert f'pid={stale.pid}' in proc.stdout
        assert f'alive pid={daemon.pid} source=process_scan refreshed_pid_file=1' in proc.stdout
        assert pid_file.read_text().strip() == str(daemon.pid)
    finally:
        stale.terminate()
        stale.wait(timeout=5)
        daemon.terminate()
        daemon.wait(timeout=5)



def test_unified_daemon_service_status_recovers_without_pid_file_when_real_daemon_exists(tmp_path: Path):
    sentinel = 'test-status-recover-no-pid'
    daemon = subprocess.Popen([
        'python3', '-c', 'import time; time.sleep(30)', '-m', 'ifa_data_platform.runtime.unified_daemon', '--loop', '--sentinel', sentinel
    ])
    try:
        log_dir = tmp_path / 'service'
        pid_file = log_dir / 'unified_daemon.pid'
        heartbeat_file = log_dir / 'unified_daemon.heartbeat.json'
        log_dir.mkdir(parents=True)
        heartbeat_file.write_text(json.dumps({'pid': daemon.pid, 'generated_at': '2999-01-01T00:00:00+00:00', 'phase': 'running'}))

        proc = subprocess.run(
            ['zsh', 'scripts/unified_daemon_service.sh', 'status'],
            cwd=REPO,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                'LOG_DIR': str(log_dir),
                'PID_FILE': str(pid_file),
                'HEARTBEAT_FILE': str(heartbeat_file),
                'DAEMON_MATCH_PATTERN': f'ifa_data_platform.runtime.unified_daemon --loop --sentinel {sentinel}',
            },
        )
        assert proc.returncode == 0
        assert f'alive pid={daemon.pid} source=process_scan refreshed_pid_file=1' in proc.stdout
        assert pid_file.read_text().strip() == str(daemon.pid)
    finally:
        daemon.terminate()
        daemon.wait(timeout=5)


def test_unified_daemon_service_start_detects_existing_daemon_via_process_scan(tmp_path: Path):
    sentinel = 'test-start-detect-existing'
    daemon = subprocess.Popen([
        'python3', '-c', 'import time; time.sleep(30)', '-m', 'ifa_data_platform.runtime.unified_daemon', '--loop', '--sentinel', sentinel
    ])
    try:
        log_dir = tmp_path / 'service'
        pid_file = log_dir / 'unified_daemon.pid'
        heartbeat_file = log_dir / 'unified_daemon.heartbeat.json'
        log_dir.mkdir(parents=True)
        heartbeat_file.write_text(json.dumps({'pid': daemon.pid, 'generated_at': '2999-01-01T00:00:00+00:00', 'phase': 'running'}))

        proc = subprocess.run(
            ['zsh', 'scripts/unified_daemon_service.sh', 'start'],
            cwd=REPO,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                'LOG_DIR': str(log_dir),
                'PID_FILE': str(pid_file),
                'HEARTBEAT_FILE': str(heartbeat_file),
                'PREFLIGHT_JSON': str(log_dir / 'runtime_preflight_latest.json'),
                'DAEMON_MATCH_PATTERN': f'ifa_data_platform.runtime.unified_daemon --loop --sentinel {sentinel}',
            },
        )
        assert proc.returncode == 0
        assert f'already_running pid={daemon.pid} source=process_scan refreshed_pid_file=1' in proc.stdout
        assert pid_file.read_text().strip() == str(daemon.pid)
    finally:
        daemon.terminate()
        daemon.wait(timeout=5)


def test_unified_daemon_service_start_reports_state_drift_for_existing_daemon_with_stale_heartbeat(tmp_path: Path):
    sentinel = 'test-start-detect-existing-stale-heartbeat'
    daemon = subprocess.Popen([
        'python3', '-c', 'import time; time.sleep(30)', '-m', 'ifa_data_platform.runtime.unified_daemon', '--loop', '--sentinel', sentinel
    ])
    try:
        log_dir = tmp_path / 'service'
        pid_file = log_dir / 'unified_daemon.pid'
        heartbeat_file = log_dir / 'unified_daemon.heartbeat.json'
        log_dir.mkdir(parents=True)
        heartbeat_file.write_text(json.dumps({'pid': daemon.pid, 'generated_at': '2000-01-01T00:00:00+00:00', 'phase': 'running'}))

        proc = subprocess.run(
            ['zsh', 'scripts/unified_daemon_service.sh', 'start'],
            cwd=REPO,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                'LOG_DIR': str(log_dir),
                'PID_FILE': str(pid_file),
                'HEARTBEAT_FILE': str(heartbeat_file),
                'HEARTBEAT_STALE_SEC': '60',
                'PREFLIGHT_JSON': str(log_dir / 'runtime_preflight_latest.json'),
                'DAEMON_MATCH_PATTERN': f'ifa_data_platform.runtime.unified_daemon --loop --sentinel {sentinel}',
            },
        )
        assert proc.returncode == 0
        assert f'already_running pid={daemon.pid} source=process_scan refreshed_pid_file=1' in proc.stdout
        assert 'heartbeat_status=stale' in proc.stdout
        assert f'already_running_state_drift pid={daemon.pid} kind=heartbeat' in proc.stdout
        assert pid_file.read_text().strip() == str(daemon.pid)
    finally:
        daemon.terminate()
        daemon.wait(timeout=5)


def test_runtime_preflight_repairs_orphan_running_unified_runtime_row(tmp_path: Path):
    run_id = '11111111-1111-1111-1111-111111111111'
    with ENGINE.begin() as conn:
        conn.execute(text("delete from ifa2.unified_runtime_runs where id = cast(:id as uuid)"), {'id': run_id})
        conn.execute(text("delete from ifa2.job_runs where id = cast(:id as uuid)"), {'id': run_id})
        conn.execute(text("""
            insert into ifa2.job_runs (
                id, job_name, status, started_at, records_processed, created_at
            ) values (
                cast(:id as uuid), 'unified_runtime:midfreq', 'running', now() - interval '4 hours', 0, now() - interval '4 hours'
            )
        """), {'id': run_id})
        conn.execute(text("""
            insert into ifa2.unified_runtime_runs (
                id, lane, worker_type, trigger_mode, manifest_snapshot_id,
                manifest_id, manifest_hash, status, started_at,
                records_processed, created_at
            ) values (
                cast(:id as uuid), 'midfreq', 'midfreq_pending_worker', 'scheduled', null,
                'test-orphan-manifest', 'test-orphan-hash', 'running', now() - interval '4 hours',
                0, now() - interval '4 hours'
            )
        """), {'id': run_id})

    out = tmp_path / 'preflight_orphan.json'
    try:
        subprocess.run([
            str(PY), 'scripts/runtime_preflight.py', '--repair', '--out', str(out), '--runtime-stale-min', '120'
        ], cwd=REPO, check=True)
        payload = json.loads(out.read_text())
        orphan_findings = [f for f in payload['findings'] if f['kind'] == 'unified_runtime_run_orphan_active' and f['detail']['run_id'] == run_id]
        assert orphan_findings
        assert orphan_findings[0]['action'] == 'auto_clear_orphan_unified_runtime_run'
        assert payload['summary']['orphan_unified_runtime_active'] >= 1

        with ENGINE.begin() as conn:
            row = conn.execute(text("""
                select status, governance_state, completed_at is not null as completed,
                       error_count, summary->>'runtime_preflight_reason' as repair_reason
                from ifa2.unified_runtime_runs
                where id = cast(:id as uuid)
            """), {'id': run_id}).mappings().one()
        assert row['status'] == 'timed_out'
        assert row['governance_state'] == 'timed_out'
        assert row['completed'] is True
        assert row['error_count'] >= 1
        assert row['repair_reason'] == 'orphan_active_unified_runtime_run'
    finally:
        with ENGINE.begin() as conn:
            conn.execute(text("delete from ifa2.unified_runtime_runs where id = cast(:id as uuid)"), {'id': run_id})
            conn.execute(text("delete from ifa2.job_runs where id = cast(:id as uuid)"), {'id': run_id})


def test_unified_daemon_service_status_fails_when_heartbeat_is_stale(tmp_path: Path):
    sentinel = 'test-status-stale-heartbeat'
    daemon = subprocess.Popen([
        'python3', '-c', 'import time; time.sleep(30)', '-m', 'ifa_data_platform.runtime.unified_daemon', '--loop', '--sentinel', sentinel
    ])
    try:
        log_dir = tmp_path / 'service'
        pid_file = log_dir / 'unified_daemon.pid'
        heartbeat_file = log_dir / 'unified_daemon.heartbeat.json'
        log_dir.mkdir(parents=True)
        pid_file.write_text(f'{daemon.pid}\n')
        heartbeat_file.write_text(json.dumps({'pid': daemon.pid, 'generated_at': '2000-01-01T00:00:00+00:00', 'phase': 'running'}))

        proc = subprocess.run(
            ['zsh', 'scripts/unified_daemon_service.sh', 'status'],
            cwd=REPO,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                'LOG_DIR': str(log_dir),
                'PID_FILE': str(pid_file),
                'HEARTBEAT_FILE': str(heartbeat_file),
                'HEARTBEAT_STALE_SEC': '60',
                'DAEMON_MATCH_PATTERN': f'ifa_data_platform.runtime.unified_daemon --loop --sentinel {sentinel}',
            },
        )
        assert proc.returncode == 1
        assert f'alive pid={daemon.pid} source=pid_file' in proc.stdout
        assert 'heartbeat_status=stale' in proc.stdout
    finally:
        daemon.terminate()
        daemon.wait(timeout=5)
