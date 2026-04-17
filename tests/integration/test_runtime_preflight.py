from __future__ import annotations

import json
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
