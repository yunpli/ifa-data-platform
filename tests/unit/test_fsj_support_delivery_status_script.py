from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_support_delivery_status.py"
_spec = importlib.util.spec_from_file_location("fsj_support_delivery_status_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
_surface_summary = _module._surface_summary
_print_text = _module._print_text
build_status_payload = _module.build_status_payload
resolve_latest_support_business_date = _module.resolve_latest_support_business_date


def test_surface_summary_exposes_canonical_support_operator_review_surface() -> None:
    surface = {
        "artifact": {
            "artifact_id": "artifact-macro-active",
            "report_run_id": "run-macro-active",
            "business_date": "2099-04-22",
            "status": "active",
        },
        "selected_handoff": {
            "selected_artifact_id": "artifact-macro-active",
            "selected_report_run_id": "run-macro-active",
            "selected_business_date": "2099-04-22",
            "selected_is_current": True,
            "selected_delivery_package_dir": "/tmp/pkg",
            "selected_delivery_manifest_path": "/tmp/pkg/delivery_manifest.json",
            "selected_delivery_zip_path": "/tmp/pkg.zip",
        },
        "state": {
            "recommended_action": "send",
            "dispatch_recommended_action": "send",
            "workflow_state": "ready_to_send",
            "send_ready": True,
            "review_required": False,
            "next_step": "dispatch_send_manifest",
            "selection_reason": "support_ready_candidate slot=early qa_score=95",
            "dispatch_selected_artifact_id": "artifact-macro-active",
            "send_blockers": [],
        },
        "package_paths": {
            "send_manifest_path": "/tmp/pkg/send_manifest.json",
            "workflow_manifest_path": "/tmp/pkg/workflow_manifest.json",
        },
        "package_versions": {
            "send_manifest_version": "send_manifest.json",
        },
        "review_summary": {
            "go_no_go_decision": "GO",
        },
    }

    summary = _surface_summary(surface)

    assert summary["artifact"]["artifact_id"] == "artifact-macro-active"
    assert summary["selected_handoff"]["selected_artifact_id"] == "artifact-macro-active"
    assert summary["state"]["workflow_state"] == "ready_to_send"
    assert summary["state"]["dispatch_recommended_action"] == "send"
    assert summary["state"]["next_step"] == "dispatch_send_manifest"
    assert summary["state"]["selection_reason"] == "support_ready_candidate slot=early qa_score=95"
    assert summary["state"]["dispatch_selected_artifact_id"] == "artifact-macro-active"
    assert summary["state"]["send_blockers"] == []
    assert summary["package_paths"]["send_manifest_path"] == "/tmp/pkg/send_manifest.json"
    assert summary["review_summary"]["go_no_go_decision"] == "GO"



def test_print_text_emits_single_support_operator_read_surface(capsys) -> None:
    payload = {
        "business_date": "2099-04-22",
        "agent_domain": "macro",
        "resolution": {
            "mode": "latest_active_lookup",
            "requested_slot": "early",
            "resolved_artifact_id": "artifact-macro-active",
            "resolved_slot": "early",
        },
        "active_surface": {
            "artifact": {
                "artifact_id": "artifact-macro-active",
                "report_run_id": "run-macro-active",
                "status": "active",
            },
            "selected_handoff": {
                "selected_artifact_id": "artifact-macro-active",
                "selected_is_current": True,
            },
            "state": {
                "recommended_action": "send_review",
                "dispatch_recommended_action": "send",
                "workflow_state": "review_required",
                "send_ready": False,
                "review_required": True,
                "next_step": "operator_review_selected_candidate",
                "selection_reason": "support_ready_candidate slot=early qa_score=94",
                "dispatch_selected_artifact_id": "artifact-macro-active",
                "package_state": "ready",
                "ready_for_delivery": True,
                "qa_score": 94,
                "blocker_count": 0,
                "warning_count": 2,
            },
            "package_paths": {
                "delivery_manifest_path": "/tmp/pkg/delivery_manifest.json",
                "send_manifest_path": "/tmp/pkg/send_manifest.json",
                "review_manifest_path": "/tmp/pkg/review_manifest.json",
                "workflow_manifest_path": "/tmp/pkg/workflow_manifest.json",
                "package_index_path": "/tmp/pkg/package_index.json",
                "delivery_zip_path": "/tmp/pkg.zip",
            },
            "llm_lineage_summary": {
                "status": "degraded",
                "summary_line": "degraded [applied=1/2 | fallback=1 | degraded=1 | tags=llm_timeout | slots=early,late]",
            },
            "llm_role_policy": {
                "policy_versions": ["fsj_llm_role_policy_v1"],
                "boundary_modes": ["candidate_only"],
                "forbidden_decisions": ["promote_candidate_to_same_day_confirmed_theme"],
                "deterministic_owner_fields": ["judgment.action", "workflow_state_and_send_readiness"],
                "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                "slot_boundary_modes": {"late": "candidate_only"},
            },
            "review_summary": {
                "go_no_go_decision": "REVIEW",
            },
        },
        "history": [{}, {}],
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "business_date=2099-04-22" in output
    assert "agent_domain=macro" in output
    assert "resolution_mode=latest_active_lookup" in output
    assert "requested_slot=early" in output
    assert "resolved_artifact_id=artifact-macro-active" in output
    assert "resolved_slot=early" in output
    assert "active_artifact_id=artifact-macro-active" in output
    assert "recommended_action=send_review" in output
    assert "dispatch_recommended_action=send" in output
    assert "next_step=operator_review_selected_candidate" in output
    assert "selection_reason=support_ready_candidate slot=early qa_score=94" in output
    assert "dispatch_selected_artifact_id=artifact-macro-active" in output
    assert "send_manifest_path=/tmp/pkg/send_manifest.json" in output
    assert "llm_lineage_status=degraded" in output
    assert "llm_lineage_summary=degraded [applied=1/2 | fallback=1 | degraded=1 | tags=llm_timeout | slots=early,late]" in output
    assert "llm_policy_versions=fsj_llm_role_policy_v1" in output
    assert "llm_boundary_modes=candidate_only" in output
    assert "llm_forbidden_decision_count=1" in output
    assert "llm_deterministic_owner_fields=judgment.action,workflow_state_and_send_readiness" in output
    assert "llm_override_precedence=deterministic_input_contract>validated_llm_text_fields_only" in output
    assert "llm_slot_boundary_modes=late:candidate_only" in output
    assert "history_count=2" in output



def test_build_status_payload_includes_resolution_metadata(monkeypatch) -> None:
    class _DummyStore:
        def get_active_report_operator_review_surface(self, **_: object) -> dict:
            return {
                "artifact": {"artifact_id": "artifact-1", "report_run_id": "run-1", "business_date": "2099-04-22", "status": "active"},
                "selected_handoff": {},
                "state": {},
                "package_paths": {},
                "package_versions": {},
                "review_summary": {"go_no_go_decision": "GO"},
            }

        def list_report_operator_review_surfaces(self, **_: object) -> list[dict]:
            return []

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())

    payload = build_status_payload(
        business_date="2099-04-22",
        agent_domain="macro",
        history_limit=3,
        resolution={"mode": "latest_active_lookup", "requested_slot": "early", "business_date": "2099-04-22", "agent_domain": "macro"},
    )

    assert payload["resolution"]["mode"] == "latest_active_lookup"
    assert payload["resolution"]["requested_slot"] == "early"
    assert payload["agent_domain"] == "macro"
    assert payload["business_date"] == "2099-04-22"



def test_resolve_latest_support_business_date_uses_store_latest_operator_review_surface(monkeypatch) -> None:
    class _DummyStore:
        def get_latest_active_report_operator_review_surface(self, **kwargs: object) -> dict:
            assert kwargs["agent_domain"] == "macro"
            assert kwargs["artifact_family"] == "support_domain_report"
            assert kwargs["strongest_slot"] == "early"
            assert kwargs["max_business_date"] is not None
            return {
                "artifact": {
                    "business_date": "2099-04-22",
                    "artifact_id": "artifact-active",
                    "report_run_id": "run-active",
                    "status": "active",
                    "updated_at": "2099-04-22T08:00:00+00:00",
                },
                "package_state": {
                    "slot_evaluation": {
                        "strongest_slot": "early",
                    },
                },
                "review_summary": {"go_no_go_decision": "GO"},
            }

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())

    resolved = resolve_latest_support_business_date(agent_domain="macro", slot="early")

    assert resolved == {
        "business_date": "2099-04-22",
        "artifact_id": "artifact-active",
        "report_run_id": "run-active",
        "status": "active",
        "updated_at": "2099-04-22T08:00:00+00:00",
        "slot": "early",
    }



def test_support_cli_json_contract_uses_operator_review_payload(monkeypatch, capsys) -> None:
    class _DummyStore:
        def get_active_report_operator_review_surface(self, **kwargs: object) -> dict:
            assert kwargs["business_date"] == "2099-04-22"
            assert kwargs["agent_domain"] == "macro"
            return {
                "artifact": {
                    "artifact_id": "artifact-active",
                    "report_run_id": "run-active",
                    "business_date": "2099-04-22",
                    "status": "active",
                },
                "selected_handoff": {
                    "selected_artifact_id": "artifact-selected",
                    "selected_is_current": False,
                },
                "state": {
                    "recommended_action": "send_review",
                    "workflow_state": "review_required",
                },
                "package_paths": {
                    "operator_review_bundle_path": "/tmp/pkg/operator_review_bundle.json",
                    "review_manifest_path": "/tmp/pkg/review_manifest.json",
                },
                "package_versions": {},
                "package_state": {
                    "slot_evaluation": {"strongest_slot": "early"},
                },
                "llm_lineage_summary": {
                    "status": "applied",
                    "summary_line": "applied [applied=1/1 | primary=1]",
                },
                "review_summary": {
                    "go_no_go_decision": "REVIEW",
                    "selected_artifact_id": "artifact-selected",
                    "current_artifact_id": "artifact-active",
                },
            }

        def list_report_operator_review_surfaces(self, **_: object) -> list[dict]:
            return []

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())
    monkeypatch.setattr("sys.argv", ["fsj_support_delivery_status.py", "--agent-domain", "macro", "--business-date", "2099-04-22", "--format", "json"])

    _module.main()
    output = capsys.readouterr().out

    assert '"artifact_id": "artifact-active"' in output
    assert '"operator_review_bundle_path": "/tmp/pkg/operator_review_bundle.json"' in output
    assert '"go_no_go_decision": "REVIEW"' in output
    assert '"llm_lineage_summary": {' in output
    assert '"summary_line": "applied [applied=1/1 | primary=1]"' in output


def test_resolve_latest_support_business_date_rejects_unknown_slot() -> None:
    with pytest.raises(ValueError, match="unsupported slot"):
        resolve_latest_support_business_date(agent_domain="macro", slot="mid")



def test_resolve_latest_support_business_date_rejects_unknown_domain() -> None:
    with pytest.raises(ValueError, match="unsupported agent_domain"):
        resolve_latest_support_business_date(agent_domain="rates")
