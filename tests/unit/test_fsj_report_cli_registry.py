from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import fsj_report_cli


class _Completed:
    def __init__(self, *, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_registry_parser_requires_support_agent_domain() -> None:
    parser = fsj_report_cli.build_parser()
    args = parser.parse_args(["registry", "--subject", "main", "--business-date", "2099-04-22"])
    assert args.command == "registry"
    assert args.subject == "main"


def test_cmd_registry_wraps_artifact_lineage_for_main(monkeypatch, capsys) -> None:
    seen: dict[str, object] = {}

    def _fake_run(cmd, capture_output=True, text=True):  # noqa: ANN001
        seen["cmd"] = cmd
        return _Completed(stdout=json.dumps({"business_date": "2099-04-22", "registry": {"chain_depth": 2}}))

    monkeypatch.setattr(fsj_report_cli.subprocess, "run", _fake_run)
    parser = fsj_report_cli.build_parser()
    args = parser.parse_args([
        "registry",
        "--subject", "main",
        "--business-date", "2099-04-22",
        "--slot", "late",
        "--format", "json",
    ])

    fsj_report_cli.main.__globals__["build_parser"] = lambda: parser
    args.func(args)
    payload = json.loads(capsys.readouterr().out)

    assert payload["command_group"] == "registry"
    assert payload["status"] == "ready"
    assert payload["wrapped_result"]["payload"]["registry"]["chain_depth"] == 2
    cmd = seen["cmd"]
    assert "fsj_artifact_lineage.py" in cmd[1]
    assert "main_final_report" in cmd
    assert "late" in cmd


def test_generate_replay_writes_mode_contract_intent_file(monkeypatch, capsys, tmp_path: Path) -> None:
    def _fake_run(cmd, capture_output=True, text=True):  # noqa: ANN001
        return _Completed(stdout=json.dumps({"ok": True, "cmd": cmd}))

    monkeypatch.setattr(fsj_report_cli.subprocess, "run", _fake_run)
    parser = fsj_report_cli.build_parser()
    args = parser.parse_args([
        "generate",
        "--subject", "main",
        "--business-date", "2099-04-22",
        "--slot", "early",
        "--mode", "replay",
        "--output-profile", "customer",
        "--output-root", str(tmp_path),
    ])

    args.func(args)
    payload = json.loads(capsys.readouterr().out)
    intent_path = tmp_path / "main_early_2099-04-22_replay" / "fsj_report_cli_intent.json"
    assert payload["mode_contract"]["effective_mode"] == "isolated_wrapper_intent"
    assert intent_path.exists()
    persisted = json.loads(intent_path.read_text(encoding="utf-8"))
    assert persisted["mode_contract"]["native_mode_switch_applied"] is False


def test_generate_rejects_non_realtime_morning_delivery(tmp_path: Path) -> None:
    parser = fsj_report_cli.build_parser()
    args = parser.parse_args([
        "generate",
        "--subject", "main",
        "--business-date", "2099-04-22",
        "--slot", "early",
        "--mode", "replay",
        "--main-flow", "morning-delivery",
        "--output-root", str(tmp_path),
    ])

    with pytest.raises(SystemExit, match="realtime-only"):
        args.func(args)
