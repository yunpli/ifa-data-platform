from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_main_early_publish.py"
spec = importlib.util.spec_from_file_location("fsj_main_early_publish", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class _StubProducer:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload or {
            "bundle": {
                "bundle_id": "bundle-early-1",
                "status": "active",
                "section_key": "pre_open_main",
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
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            output_root=str(tmp_path),
            generated_at="2026-04-23T08:20:43+00:00",
            report_run_id_prefix="fsj-main-early",
            include_empty=False,
        ),
    )
    monkeypatch.setattr(module, "EarlyMainFSJProducer", lambda: _StubProducer())
    monkeypatch.setattr(
        module,
        "_resolve_canonical_publish_surface",
        lambda **_: {
            "workflow_handoff": {
                "artifact": {"artifact_id": "artifact-db", "report_run_id": "run-db"},
                "selected_handoff": {"selected_artifact_id": "artifact-db", "selected_is_current": True},
                "state": {
                    "workflow_state": "ready_to_send",
                    "recommended_action": "send",
                    "dispatch_recommended_action": "send",
                    "package_state": "ready",
                    "next_step": "dispatch_send_manifest",
                    "selection_reason": "best_ready_candidate strongest_slot=early qa_score=96",
                    "dispatch_selected_artifact_id": "artifact-db",
                },
                "manifest_pointers": {
                    "delivery_manifest_path": "/tmp/db/delivery_manifest.json",
                    "send_manifest_path": "/tmp/db/send_manifest.json",
                },
            },
            "operator_review_surface": {
                "llm_lineage_summary": {"status": "applied"},
                "llm_role_policy": {
                    "policy_versions": ["fsj_llm_role_policy_v1"],
                    "boundary_modes": ["candidate_only"],
                    "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                    "forbidden_decisions": ["declare_close_final_confirmation"],
                    "slot_boundary_modes": {"early": "candidate_only"},
                },
            },
        },
    )

    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], capture_output: bool, text: bool):
        assert capture_output is True
        assert text is True
        calls.append(cmd)
        assert cmd[1].endswith("fsj_main_report_publish.py")
        assert cmd[2:] == [
            "--business-date", "2026-04-23",
            "--output-dir", str(tmp_path / "publish"),
            "--generated-at", "2026-04-23T08:20:43+00:00",
            "--report-run-id", "fsj-main-early:2026-04-23:early:20260423T082043Z",
        ]
        return module.subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps({
                "artifact": {"artifact_id": "artifact-1"},
                "delivery_manifest": {"package_state": "ready", "lineage": {"bundle_id": "bundle-early-1"}},
                "delivery_package_dir": str(tmp_path / "publish" / "pkg"),
            }),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert payload["persist"]["bundle_id"] == "bundle-early-1"
    assert payload["publish"]["status"] == "ready"
    assert len(calls) == 1
    summary = json.loads((tmp_path / "main_early_publish_summary.json").read_text(encoding="utf-8"))
    assert summary["persist"]["evidence_link_count"] == 3
    assert summary["publish"]["workflow_handoff"]["selected_handoff"]["selected_artifact_id"] == "artifact-db"
    assert summary["publish"]["operator_review_surface"]["llm_role_policy"]["policy_versions"] == ["fsj_llm_role_policy_v1"]
    operator_summary = (tmp_path / "operator_summary.txt").read_text(encoding="utf-8")
    assert "FSJ MAIN early publish｜2026-04-23｜early" in operator_summary
    assert "workflow_state=ready_to_send" in operator_summary
    assert "dispatch_recommended_action=send" in operator_summary
    assert "selected_is_current=True" in operator_summary
    assert "selected_artifact_id=artifact-db" in operator_summary
    assert "dispatch_selected_artifact_id=artifact-db" in operator_summary
    assert "next_step=dispatch_send_manifest" in operator_summary
    assert "selection_reason=best_ready_candidate strongest_slot=early qa_score=96" in operator_summary
    assert "send_manifest_path=/tmp/db/send_manifest.json" in operator_summary
    assert "llm_lineage_status=applied llm_policy_versions=fsj_llm_role_policy_v1" in operator_summary
    assert "llm_boundary_modes=candidate_only llm_override_precedence=deterministic_input_contract>validated_llm_text_fields_only" in operator_summary
    assert "llm_slot_boundary_modes=early:candidate_only llm_forbidden_decision_count=1" in operator_summary


def test_main_exits_nonzero_and_skips_publish_when_persist_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            output_root=str(tmp_path),
            generated_at="2026-04-23T08:20:43+00:00",
            report_run_id_prefix="fsj-main-early",
            include_empty=False,
        ),
    )
    monkeypatch.setattr(module, "EarlyMainFSJProducer", lambda: _StubProducer(error=RuntimeError("db unavailable")))

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


def test_main_blocks_pytest_flow_on_canonical_live_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_artifacts_root = Path(__file__).resolve().parents[2] / "artifacts" / "pytest-should-block"
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp")
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            output_root=str(live_artifacts_root),
            generated_at="2026-04-23T08:20:43+00:00",
            report_run_id_prefix="fsj-main-early",
            include_empty=False,
        ),
    )

    with pytest.raises(module.TestLiveIsolationError, match="canonical/live DB"):
        module.main()
