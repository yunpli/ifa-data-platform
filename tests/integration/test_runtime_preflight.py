from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path('/Users/neoclaw/repos/ifa-data-platform')
PY = REPO / '.venv/bin/python'


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
                'DAEMON_MATCH_PATTERN': 'ifa_data_platform.runtime.unified_daemon --loop',
            },
        )
        assert proc.returncode == 1
        assert 'stale_pid_file' in proc.stdout
        assert 'reason=command_mismatch' in proc.stdout
        assert f'pid={sleeper.pid}' in proc.stdout
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
