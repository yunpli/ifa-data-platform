from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_support_batch_publish.py"
spec = importlib.util.spec_from_file_location("fsj_support_batch_publish", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_main_persists_before_publish_and_writes_batch_summary(
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
            slot="early",
            output_root=str(tmp_path),
            agent_domains=["macro", "ai_tech"],
            generated_at="2026-04-23T11:50:24+00:00",
            report_run_id_prefix="fsj-support-batch",
            require_ready=True,
        ),
    )

    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], capture_output: bool, text: bool):
        assert capture_output is True
        assert text is True
        calls.append(cmd)
        if cmd[1].endswith("fsj_support_bundle_persist.py"):
            assert cmd[2:] == [
                "--business-date", "2026-04-23",
                "--slot", "early",
                "--output-root", str(tmp_path / "persist"),
                "--agent-domain", "macro",
                "--agent-domain", "ai_tech",
            ]
            return module.subprocess.CompletedProcess(
                cmd,
                0,
                stdout=json.dumps({
                    "artifact_type": "fsj_support_bundle_persist_summary",
                    "persisted_count": 2,
                    "blocked_count": 0,
                    "results": [
                        {"agent_domain": "macro", "status": "persisted", "bundle_id": "bundle-macro"},
                        {"agent_domain": "ai_tech", "status": "persisted", "bundle_id": "bundle-ai"},
                    ],
                    "summary_path": str(tmp_path / "persist" / "persist_summary.json"),
                }),
                stderr="",
            )
        assert cmd[1].endswith("fsj_support_report_publish.py")
        domain = cmd[cmd.index("--agent-domain") + 1]
        return module.subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps({
                "status": "ready",
                "bundle": {"bundle_id": f"bundle-{domain}"},
                "delivery_manifest": {"package_state": "ready", "lineage": {"bundle_id": f"bundle-{domain}"}},
            }),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(
        module,
        "_resolve_canonical_publish_surface",
        lambda **kwargs: {
            "delivery_surface": {
                "delivery_package": {
                    "package_state": "ready",
                    "lineage": {"bundle_id": f"bundle-db-{kwargs['agent_domain']}"},
                }
            },
            "workflow_handoff": {
                "artifact": {"artifact_id": f"artifact-{kwargs['agent_domain']}"},
                "selected_handoff": {"selected_artifact_id": f"artifact-{kwargs['agent_domain']}", "selected_is_current": True},
                "state": {
                    "workflow_state": "ready_to_send",
                    "recommended_action": "send",
                    "dispatch_recommended_action": "send",
                    "package_state": "ready",
                    "next_step": "dispatch_send_manifest",
                    "selection_reason": f"support_ready_candidate domain={kwargs['agent_domain']}",
                    "dispatch_selected_artifact_id": f"artifact-{kwargs['agent_domain']}",
                },
                "manifest_pointers": {
                    "delivery_manifest_path": f"/tmp/db/{kwargs['agent_domain']}/delivery_manifest.json",
                    "send_manifest_path": f"/tmp/db/{kwargs['agent_domain']}/send_manifest.json",
                },
            },
            "operator_review_surface": {
                "llm_lineage_summary": {"status": "applied"},
                "llm_role_policy": {
                    "policy_versions": ["fsj_llm_role_policy_v1"],
                    "boundary_modes": ["candidate_only"],
                    "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                    "forbidden_decisions": ["promote_candidate_to_same_day_confirmed_theme"],
                    "slot_boundary_modes": {"early": "candidate_only"},
                },
            },
        },
    )

    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert [Path(call[1]).name for call in calls] == [
        "fsj_support_bundle_persist.py",
        "fsj_support_report_publish.py",
        "fsj_support_report_publish.py",
    ]
    assert payload["persist"]["persisted_count"] == 2
    assert payload["persist"]["exit_code"] == 0
    assert payload["ready_count"] == 2
    summary = json.loads((tmp_path / "batch_summary.json").read_text(encoding="utf-8"))
    assert summary["artifact_version"] == "v2"
    assert summary["persist"]["persisted_count"] == 2
    assert summary["results"][0]["workflow_handoff"]["state"]["workflow_state"] == "ready_to_send"
    assert summary["results"][0]["bundle_id"].startswith("bundle-db-")
    operator_summary = (tmp_path / "operator_summary.txt").read_text(encoding="utf-8")
    assert "FSJ support batch publish｜2026-04-23｜early" in operator_summary
    assert "workflow_state=ready_to_send" in operator_summary
    assert "dispatch_recommended_action=send" in operator_summary
    assert "selected_is_current=True" in operator_summary
    assert "dispatch_selected_artifact_id=artifact-macro" in operator_summary
    assert "next_step=dispatch_send_manifest" in operator_summary
    assert "selection_reason=support_ready_candidate domain=macro" in operator_summary
    assert "send_manifest_path=/tmp/db/macro/send_manifest.json" in operator_summary
    assert "llm_lineage_status=applied llm_policy_versions=fsj_llm_role_policy_v1" in operator_summary
    assert "llm_boundary_modes=candidate_only llm_override_precedence=deterministic_input_contract>validated_llm_text_fields_only" in operator_summary
    assert "llm_slot_boundary_modes=early:candidate_only llm_forbidden_decision_count=1" in operator_summary


def test_main_keeps_publish_results_and_surfaces_persist_failure(
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
            slot="early",
            output_root=str(tmp_path),
            agent_domains=["macro"],
            generated_at="2026-04-23T11:46:03+00:00",
            report_run_id_prefix="fsj-support-batch",
            require_ready=True,
        ),
    )

    def _fake_run(cmd: list[str], capture_output: bool, text: bool):
        if cmd[1].endswith("fsj_support_bundle_persist.py"):
            return module.subprocess.CompletedProcess(
                cmd,
                2,
                stdout=json.dumps({
                    "artifact_type": "fsj_support_bundle_persist_summary",
                    "persisted_count": 0,
                    "blocked_count": 1,
                    "results": [{"agent_domain": "macro", "status": "blocked", "reason": "RuntimeError: db unavailable"}],
                }),
                stderr="",
            )
        return module.subprocess.CompletedProcess(
            cmd,
            2,
            stdout=json.dumps({
                "status": "blocked",
                "reason": "persisted_support_bundle_not_ready",
                "bundle": None,
                "delivery_manifest": {"package_state": "blocked", "lineage": {"bundle_id": None}},
            }),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module, "_resolve_canonical_publish_surface", lambda **_: None)

    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["persist"]["exit_code"] == 2
    assert payload["persist"]["blocked_count"] == 1
    assert payload["blocked_count"] == 1
    assert payload["results"][0]["reason"] == "persisted_support_bundle_not_ready"


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
            slot="early",
            output_root=str(live_artifacts_root),
            agent_domains=["macro"],
            generated_at="2026-04-23T11:46:03+00:00",
            report_run_id_prefix="fsj-support-batch",
            require_ready=True,
        ),
    )

    with pytest.raises(module.TestLiveIsolationError, match="canonical/live DB"):
        module.main()
