from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_main_late_publish.py"
spec = importlib.util.spec_from_file_location("fsj_main_late_publish", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class _StubProducer:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload or {
            "bundle": {
                "bundle_id": "bundle-late-1",
                "status": "active",
                "section_key": "post_close_main",
            },
            "objects": [{}, {}, {}],
            "edges": [{}, {}],
            "evidence_links": [{}, {}, {}],
            "observed_records": [{}, {}],
        }
        self.error = error

    def produce_and_persist(self, *, business_date: str) -> dict:
        assert business_date == "2026-04-23"
        if self.error:
            raise self.error
        return self.payload


def test_main_persists_then_publishes_and_writes_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            output_root=str(tmp_path),
            generated_at="2026-04-23T12:20:43+00:00",
            report_run_id_prefix="fsj-main-late",
            include_empty=False,
        ),
    )
    monkeypatch.setattr(module, "LateMainFSJProducer", lambda: _StubProducer())

    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], capture_output: bool, text: bool):
        assert capture_output is True
        assert text is True
        calls.append(cmd)
        assert cmd[1].endswith("fsj_main_report_publish.py")
        assert cmd[2:] == [
            "--business-date", "2026-04-23",
            "--output-dir", str(tmp_path / "publish"),
            "--generated-at", "2026-04-23T12:20:43+00:00",
            "--report-run-id", "fsj-main-late:2026-04-23:late:20260423T122043Z",
        ]
        return module.subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps({
                "artifact": {"artifact_id": "artifact-1"},
                "delivery_manifest": {"package_state": "ready", "lineage": {"bundle_id": "bundle-late-1"}},
                "delivery_package_dir": str(tmp_path / "publish" / "pkg"),
            }),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert payload["persist"]["bundle_id"] == "bundle-late-1"
    assert payload["publish"]["status"] == "ready"
    assert len(calls) == 1
    summary = json.loads((tmp_path / "main_late_publish_summary.json").read_text(encoding="utf-8"))
    assert summary["persist"]["evidence_link_count"] == 3
    assert "FSJ MAIN late publish｜2026-04-23｜late" in (tmp_path / "operator_summary.txt").read_text(encoding="utf-8")


def test_main_exits_nonzero_and_skips_publish_when_persist_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            output_root=str(tmp_path),
            generated_at="2026-04-23T12:20:43+00:00",
            report_run_id_prefix="fsj-main-late",
            include_empty=False,
        ),
    )
    monkeypatch.setattr(module, "LateMainFSJProducer", lambda: _StubProducer(error=RuntimeError("db unavailable")))

    def _unexpected_run(*args, **kwargs):
        raise AssertionError("publish should not run when persist fails")

    monkeypatch.setattr(module.subprocess, "run", _unexpected_run)

    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "blocked"
    assert payload["persist"]["reason"] == "RuntimeError: db unavailable"
    assert payload["publish"] is None
