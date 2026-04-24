from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError as LiveIsolationError


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_main_delivery_status.py"
_spec = importlib.util.spec_from_file_location("fsj_main_delivery_status_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
_surface_summary = _module._surface_summary
_artifact_row = _module._artifact_row
_print_text = _module._print_text
build_status_payload = _module.build_status_payload
resolve_latest_main_business_date = _module.resolve_latest_main_business_date


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"
LIVE_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp"


def _clear_caches() -> None:
    make_engine.cache_clear()
    get_settings.cache_clear()


def test_surface_summary_exposes_canonical_operator_review_surface() -> None:
    surface = {
        "artifact": {
            "artifact_id": "artifact-active",
            "report_run_id": "run-active",
            "business_date": "2099-04-22",
            "status": "active",
            "supersedes_artifact_id": "artifact-old",
        },
        "selected_handoff": {
            "selected_artifact_id": "artifact-active",
            "selected_report_run_id": "run-active",
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
            "next_step": "dispatch_send_manifest",
            "selection_reason": "best_ready_candidate strongest_slot=late qa_score=96",
            "dispatch_selected_artifact_id": "artifact-active",
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

    assert summary["artifact"]["artifact_id"] == "artifact-active"
    assert summary["selected_handoff"]["selected_artifact_id"] == "artifact-active"
    assert summary["selected_handoff"]["selected_is_current"] is True
    assert summary["state"]["recommended_action"] == "send"
    assert summary["state"]["dispatch_recommended_action"] == "send"
    assert summary["state"]["workflow_state"] == "ready_to_send"
    assert summary["state"]["send_ready"] is True
    assert summary["state"]["next_step"] == "dispatch_send_manifest"
    assert summary["state"]["selection_reason"] == "best_ready_candidate strongest_slot=late qa_score=96"
    assert summary["state"]["dispatch_selected_artifact_id"] == "artifact-active"
    assert summary["state"]["send_blockers"] == []
    assert summary["package_paths"]["send_manifest_path"] == "/tmp/pkg/send_manifest.json"
    assert summary["package_paths"]["workflow_manifest_path"] == "/tmp/pkg/workflow_manifest.json"
    assert summary["package_versions"]["send_manifest_version"] == "send_manifest.json"
    assert summary["review_summary"]["go_no_go_decision"] == "GO"


def test_surface_summary_falls_back_to_store_normalized_handoff() -> None:
    surface = {
        "artifact": {
            "artifact_id": "artifact-active",
            "report_run_id": "run-active",
            "business_date": "2099-04-22",
            "status": "active",
        },
        "delivery_package": {
            "package_state": "ready",
            "ready_for_delivery": True,
        },
        "workflow_linkage": {
            "send_manifest_path": "/tmp/pkg/send_manifest.json",
        },
    }

    class _DummyStore:
        def report_operator_review_surface_from_surface(self, value: dict) -> dict:
            assert value is surface
            return {
                "artifact": {"artifact_id": "artifact-normalized"},
                "selected_handoff": {"selected_artifact_id": "artifact-normalized"},
                "state": {"recommended_action": "send"},
                "package_paths": {"send_manifest_path": "/normalized/send_manifest.json"},
                "package_versions": {},
                "review_summary": {"go_no_go_decision": "GO"},
            }

    summary = _surface_summary(surface, store=_DummyStore())

    assert summary["artifact"]["artifact_id"] == "artifact-normalized"
    assert summary["selected_handoff"]["selected_artifact_id"] == "artifact-normalized"
    assert summary["package_paths"]["send_manifest_path"] == "/normalized/send_manifest.json"
    assert summary["review_summary"]["go_no_go_decision"] == "GO"


def test_artifact_row_projects_canonical_lifecycle_fields() -> None:
    row = _artifact_row(
        {
            "artifact": {"artifact_id": "artifact-1", "report_run_id": "run-1", "status": "superseded"},
            "state": {
                "workflow_state": "review_required",
                "recommended_action": "send_review",
                "package_state": "ready",
                "ready_for_delivery": True,
                "send_ready": False,
                "review_required": True,
            },
            "selected_handoff": {"selected_is_current": False},
            "canonical_lifecycle": {"state": "review_ready", "reason": "manual_review_required"},
            "review_summary": {"qa_score": 94, "blocker_count": 0, "warning_count": 2},
        }
    )

    assert row == {
        "artifact_id": "artifact-1",
        "report_run_id": "run-1",
        "status": "superseded",
        "workflow_state": "review_required",
        "recommended_action": "send_review",
        "package_state": "ready",
        "ready_for_delivery": True,
        "send_ready": False,
        "review_required": True,
        "canonical_lifecycle_state": "review_ready",
        "canonical_lifecycle_reason": "manual_review_required",
        "selected_is_current": False,
        "qa_score": 94,
        "blocker_count": 0,
        "warning_count": 2,
        "go_no_go_decision": None,
        "operator_decision_rationale": None,
        "operator_next_step": None,
        "operator_action_required": None,
        "promotion_authority_status": None,
        "promotion_authority_approved": None,
        "promotion_authority_required_action": None,
        "promotion_authority_rationale": None,
        "promotion_authority_summary": None,
        "promotion_authority_approver_kind": None,
        "promotion_authority_approver_id": None,
        "promotion_authority_approver_label": None,
        "promotion_authority_decided_at": None,
        "promotion_authority_approver_summary": None,
        "review_blocking_item_count": None,
        "review_warning_item_count": None,
        "send_blocker_count": None,
        "governance_blocking_reasons": [],
        "bundle_count": None,
        "missing_bundle_count": None,
        "dispatch_state": None,
        "provider_message_id": None,
    }



def test_print_text_emits_single_operator_read_surface(capsys) -> None:
    payload = {
        "business_date": "2099-04-22",
        "db_candidate_alignment_summary": {
            "verdict": "mismatch",
            "reason_code": "better_ready_candidate_selected_current_outdated",
            "summary_line": "Current MAIN artifact artifact-active is not the best DB candidate; selected artifact artifact-selected supersedes it as the best ready candidate.",
            "current_artifact_id": "artifact-active",
            "selected_artifact_id": "artifact-selected",
            "best_candidate_artifact_id": "artifact-selected",
            "candidate_count": 2,
            "ready_candidate_count": 1,
            "selected_matches_best": True,
            "current_matches_best": False,
        },
        "rerun_compare_summary": {
            "subject": "main",
            "verdict": "mismatch",
            "reason_code": "better_ready_candidate_selected_current_outdated",
            "summary_line": "Current MAIN artifact artifact-active is not the best DB candidate; selected artifact artifact-selected supersedes it as the best ready candidate.",
            "current_artifact_id": "artifact-active",
            "selected_artifact_id": "artifact-selected",
            "best_candidate_artifact_id": "artifact-selected",
            "compare_outcome": "supersede_candidate_available",
            "rerun_outcome": "supersede",
            "rerun_outcome_summary": "supersede | current=artifact-active | selected=artifact-selected | best=artifact-selected | action=review_and_promote_selected_candidate",
            "operator_action": "review_and_promote_selected_candidate",
            "operator_summary": "main rerun/replay compare found a better candidate: current=artifact-active selected=artifact-selected best=artifact-selected; operator should review and promote the selected candidate if evidence is accepted.",
            "rerun_candidate_present": True,
            "rerun_candidate_differs_from_current": True,
            "selected_candidate_differs_from_current": True,
        },
        "db_candidate_history_summary": [
            {
                "subject": "history:1",
                "verdict": "mismatch",
                "reason_code": "better_ready_candidate_selected_current_outdated",
                "summary_line": "Current MAIN artifact artifact-active is not the best DB candidate; selected artifact artifact-selected supersedes it as the best ready candidate.",
                "current_artifact_id": "artifact-active",
                "selected_artifact_id": "artifact-selected",
                "best_candidate_artifact_id": "artifact-selected",
            }
        ],
        "resolution": {
            "mode": "latest_active_lookup",
            "requested_slot": "late",
            "resolved_artifact_id": "artifact-active",
            "resolved_strongest_slot": "late",
        },
        "active_surface": {
            "artifact": {
                "artifact_id": "artifact-active",
                "report_run_id": "run-active",
                "status": "active",
            },
            "selected_handoff": {
                "selected_artifact_id": "artifact-selected",
                "selected_is_current": False,
            },
            "state": {
                "recommended_action": "send_review",
                "dispatch_recommended_action": "send",
                "workflow_state": "review_required",
                "send_ready": False,
                "review_required": True,
                "next_step": "operator_review_selected_candidate",
                "selection_reason": "best_ready_candidate strongest_slot=late qa_score=94",
                "dispatch_selected_artifact_id": "artifact-selected",
                "package_state": "ready",
                "ready_for_delivery": True,
                "qa_score": 94,
                "blocker_count": 0,
                "warning_count": 2,
            },
            "canonical_lifecycle": {"state": "review_ready", "reason": "manual_review_required"},
            "package_paths": {
                "delivery_manifest_path": "/tmp/pkg/delivery_manifest.json",
                "send_manifest_path": "/tmp/pkg/send_manifest.json",
                "review_manifest_path": "/tmp/pkg/review_manifest.json",
                "workflow_manifest_path": "/tmp/pkg/workflow_manifest.json",
                "package_index_path": "/tmp/pkg/package_index.json",
                "delivery_zip_path": "/tmp/pkg.zip",
            },
            "artifact_lineage": {
                "bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 1, "slots": ["early", "late"], "section_keys": ["pre_open_main", "post_close_main"]},
                "what_user_received": {"dispatch_state": "dispatch_succeeded", "channel": "telegram_document", "provider_message_id": "tg-42", "sent_at": "2099-04-22T10:00:03Z", "error": None},
            },
            "llm_lineage_summary": {
                "status": "degraded",
                "summary_line": "degraded [applied=1/2 | fallback=1 | degraded=1 | tags=llm_timeout | slots=early,late | models=gemini31_pro_jmr,grok41_thinking | tokens=579 | usage=2 | unpriced=2]",
                "models": ["gemini31_pro_jmr", "grok41_thinking"],
                "usage_bundle_count": 2,
                "token_totals": {"total_tokens": 579},
                "estimated_cost_usd": None,
                "uncosted_bundle_count": 2,
            },
            "llm_role_policy": {
                "policy_versions": ["fsj_llm_role_policy_v1"],
                "boundary_modes": ["same_day_close"],
                "forbidden_decisions": ["upgrade_provisional_close_without_required_same_day_evidence"],
                "deterministic_owner_fields": ["judgment.action", "workflow_state_and_send_readiness"],
                "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                "slot_boundary_modes": {"late": "same_day_close"},
            },
            "review_summary": {
                "go_no_go_decision": "REVIEW",
                "operator_decision_rationale": "manual review is required before sending",
                "operator_action_required": True,
                "promotion_authority_status": "review_required",
                "promotion_authority_approved": False,
                "promotion_authority_required_action": "operator_review_selected_candidate",
                "promotion_authority_rationale": "manual review is required before sending",
                "promotion_authority_summary": "review_required | decision=REVIEW | selected_is_current=False | required_action=operator_review_selected_candidate | rationale=manual review is required before sending",
                "promotion_authority_approver_kind": "human_operator",
                "promotion_authority_approver_id": "op-main-1",
                "promotion_authority_approver_label": "main-reviewer",
                "promotion_authority_decided_at": "2099-04-22T09:58:00Z",
                "promotion_authority_approver_summary": "kind=human_operator | id=op-main-1 | label=main-reviewer | decided_at=2099-04-22T09:58:00Z",
                "review_blocking_item_count": 0,
                "review_warning_item_count": 2,
                "send_blocker_count": 1,
                "governance_blocking_reasons": ["manual_review_required", "selected_candidate_not_current"],
            },
        },
        "history": [
            {
                "artifact": {"artifact_id": "artifact-active", "status": "active"},
                "state": {"workflow_state": "review_required", "recommended_action": "send_review"},
                "selected_handoff": {"selected_is_current": False},
                "canonical_lifecycle": {"state": "review_ready", "reason": "manual_review_required"},
                "review_summary": {
                    "qa_score": 94,
                    "blocker_count": 0,
                    "warning_count": 2,
                    "go_no_go_decision": "REVIEW",
                    "operator_decision_rationale": "manual review is required before sending",
                    "operator_next_step": "operator_review_selected_candidate",
                    "operator_action_required": True,
                    "promotion_authority_status": "review_required",
                    "promotion_authority_approved": False,
                    "promotion_authority_required_action": "operator_review_selected_candidate",
                    "promotion_authority_rationale": "manual review is required before sending",
                    "promotion_authority_summary": "review_required | decision=REVIEW | selected_is_current=False | required_action=operator_review_selected_candidate | rationale=manual review is required before sending",
                    "promotion_authority_approver_kind": "human_operator",
                    "promotion_authority_approver_id": "op-main-1",
                    "promotion_authority_approver_label": "main-reviewer",
                    "promotion_authority_decided_at": "2099-04-22T09:58:00Z",
                    "promotion_authority_approver_summary": "kind=human_operator | id=op-main-1 | label=main-reviewer | decided_at=2099-04-22T09:58:00Z",
                    "review_blocking_item_count": 0,
                    "review_warning_item_count": 2,
                    "send_blocker_count": 1,
                    "governance_blocking_reasons": ["manual_review_required", "selected_candidate_not_current"],
                },
                "artifact_lineage": {"bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 1}, "what_user_received": {"dispatch_state": "dispatch_succeeded", "provider_message_id": "tg-42"}},
            },
            {
                "artifact": {"artifact_id": "artifact-old", "status": "superseded"},
                "state": {"workflow_state": "ready_to_send", "recommended_action": "send"},
                "selected_handoff": {"selected_is_current": True},
                "canonical_lifecycle": {"state": "superseded", "reason": "artifact_status_superseded"},
                "review_summary": {
                    "qa_score": 92,
                    "blocker_count": 0,
                    "warning_count": 0,
                    "go_no_go_decision": "GO",
                    "operator_decision_rationale": "quality gate and artifact integrity both pass",
                    "operator_next_step": "send_selected_package_to_primary_channel",
                    "operator_action_required": False,
                    "promotion_authority_status": "approved_to_send",
                    "promotion_authority_approved": True,
                    "promotion_authority_required_action": "send_selected_package_to_primary_channel",
                    "promotion_authority_rationale": "quality gate and artifact integrity both pass",
                    "promotion_authority_summary": "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass",
                    "promotion_authority_approver_kind": "system",
                    "promotion_authority_approver_id": None,
                    "promotion_authority_approver_label": "fsj_policy_projection",
                    "promotion_authority_decided_at": None,
                    "promotion_authority_approver_summary": "kind=system | id=- | label=fsj_policy_projection | decided_at=-",
                    "review_blocking_item_count": 0,
                    "review_warning_item_count": 0,
                    "send_blocker_count": 0,
                    "governance_blocking_reasons": [],
                },
                "artifact_lineage": {"bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 0}, "what_user_received": {"dispatch_state": "dispatch_failed", "provider_message_id": "tg-41"}},
            },
        ],
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "business_date=2099-04-22" in output
    assert "resolution_mode=latest_active_lookup" in output
    assert "requested_slot=late" in output
    assert "resolved_artifact_id=artifact-active" in output
    assert "resolved_strongest_slot=late" in output
    assert "active_artifact_id=artifact-active" in output
    assert "selected_artifact_id=artifact-selected" in output
    assert "recommended_action=send_review" in output
    assert "dispatch_recommended_action=send" in output
    assert "workflow_state=review_required" in output
    assert "canonical_lifecycle_state=review_ready" in output
    assert "canonical_lifecycle_reason=manual_review_required" in output
    assert "go_no_go_decision=REVIEW" in output
    assert "operator_decision_rationale=manual review is required before sending" in output
    assert "operator_action_required=True" in output
    assert "promotion_authority_status=review_required" in output
    assert "promotion_authority_approved=False" in output
    assert "promotion_authority_required_action=operator_review_selected_candidate" in output
    assert "promotion_authority_approver_kind=human_operator" in output
    assert "promotion_authority_approver_id=op-main-1" in output
    assert "promotion_authority_approver_label=main-reviewer" in output
    assert "promotion_authority_decided_at=2099-04-22T09:58:00Z" in output
    assert "promotion_authority_approver_summary=kind=human_operator | id=op-main-1 | label=main-reviewer | decided_at=2099-04-22T09:58:00Z" in output
    assert "review_blocking_item_count=0" in output
    assert "review_warning_item_count=2" in output
    assert "send_blocker_count=1" in output
    assert "governance_blocking_reasons=manual_review_required,selected_candidate_not_current" in output
    assert "next_step=operator_review_selected_candidate" in output
    assert "selection_reason=best_ready_candidate strongest_slot=late qa_score=94" in output
    assert "dispatch_selected_artifact_id=artifact-selected" in output
    assert "send_manifest_path=/tmp/pkg/send_manifest.json" in output
    assert "lineage_bundle_count=2" in output
    assert "lineage_missing_bundle_count=1" in output
    assert "lineage_bundle_slots=early,late" in output
    assert "lineage_bundle_section_keys=pre_open_main,post_close_main" in output
    assert "lineage_dispatch_state=dispatch_succeeded" in output
    assert "lineage_dispatch_channel=telegram_document" in output
    assert "lineage_provider_message_id=tg-42" in output
    assert "lineage_sent_at=2099-04-22T10:00:03Z" in output
    assert "lineage_dispatch_error=None" in output
    assert "llm_lineage_status=degraded" in output
    assert "llm_models=gemini31_pro_jmr,grok41_thinking" in output
    assert "llm_total_tokens=579" in output
    assert "llm_uncosted_bundle_count=2" in output
    assert "llm_lineage_summary=degraded [applied=1/2 | fallback=1 | degraded=1 | tags=llm_timeout | slots=early,late | models=gemini31_pro_jmr,grok41_thinking | tokens=579 | usage=2 | unpriced=2]" in output
    assert "llm_policy_versions=fsj_llm_role_policy_v1" in output
    assert "llm_boundary_modes=same_day_close" in output
    assert "llm_forbidden_decision_count=1" in output
    assert "llm_deterministic_owner_fields=judgment.action,workflow_state_and_send_readiness" in output
    assert "llm_override_precedence=deterministic_input_contract>validated_llm_text_fields_only" in output
    assert "llm_slot_boundary_modes=late:same_day_close" in output
    assert "db_candidate_verdict=mismatch" in output
    assert "db_candidate_reason=better_ready_candidate_selected_current_outdated" in output
    assert "db_candidate_best_artifact_id=artifact-selected" in output
    assert "db_candidate_candidate_count=2" in output
    assert "db_candidate_ready_candidate_count=1" in output
    assert "rerun_compare_outcome=supersede_candidate_available" in output
    assert "rerun_compare_rerun_outcome=supersede" in output
    assert "rerun_compare_rerun_outcome_summary=supersede | current=artifact-active | selected=artifact-selected | best=artifact-selected | action=review_and_promote_selected_candidate" in output
    assert "rerun_compare_operator_action=review_and_promote_selected_candidate" in output
    assert "rerun_compare_candidate_present=True" in output
    assert "rerun_compare_candidate_differs_from_current=True" in output
    assert "rerun_compare_selected_differs_from_current=True" in output
    assert "rerun_compare_summary=main rerun/replay compare found a better candidate: current=artifact-active selected=artifact-selected best=artifact-selected; operator should review and promote the selected candidate if evidence is accepted." in output
    assert "db_candidate_history_count=1" in output
    assert "db_candidate_history_1_subject=history:1" in output
    assert "db_candidate_history_1_verdict=mismatch" in output
    assert "history_count=2" in output
    assert "history_1_artifact_id=artifact-active" in output
    assert "history_1_canonical_lifecycle_state=review_ready" in output
    assert "history_1_canonical_lifecycle_reason=manual_review_required" in output
    assert "history_1_go_no_go_decision=REVIEW" in output
    assert "history_1_operator_decision_rationale=manual review is required before sending" in output
    assert "history_1_operator_next_step=operator_review_selected_candidate" in output
    assert "history_1_operator_action_required=True" in output
    assert "history_1_promotion_authority_status=review_required" in output
    assert "history_1_promotion_authority_approved=False" in output
    assert "history_1_promotion_authority_approver_kind=human_operator" in output
    assert "history_1_promotion_authority_approver_id=op-main-1" in output
    assert "history_1_promotion_authority_approver_label=main-reviewer" in output
    assert "history_1_promotion_authority_decided_at=2099-04-22T09:58:00Z" in output
    assert "history_1_promotion_authority_approver_summary=kind=human_operator | id=op-main-1 | label=main-reviewer | decided_at=2099-04-22T09:58:00Z" in output
    assert "history_1_review_blocking_item_count=0" in output
    assert "history_1_review_warning_item_count=2" in output
    assert "history_1_send_blocker_count=1" in output
    assert "history_1_governance_blocking_reasons=manual_review_required,selected_candidate_not_current" in output
    assert "history_1_bundle_count=2" in output
    assert "history_1_missing_bundle_count=1" in output
    assert "history_1_dispatch_state=dispatch_succeeded" in output
    assert "history_1_provider_message_id=tg-42" in output
    assert "history_2_artifact_id=artifact-old" in output
    assert "history_2_canonical_lifecycle_state=superseded" in output
    assert "history_2_canonical_lifecycle_reason=artifact_status_superseded" in output
    assert "history_2_go_no_go_decision=GO" in output
    assert "history_2_operator_decision_rationale=quality gate and artifact integrity both pass" in output
    assert "history_2_operator_next_step=send_selected_package_to_primary_channel" in output
    assert "history_2_operator_action_required=False" in output
    assert "history_2_promotion_authority_status=approved_to_send" in output
    assert "history_2_promotion_authority_approved=True" in output
    assert "history_2_promotion_authority_approver_kind=system" in output
    assert "history_2_promotion_authority_approver_label=fsj_policy_projection" in output
    assert "history_2_promotion_authority_approver_summary=kind=system | id=- | label=fsj_policy_projection | decided_at=-" in output
    assert "history_2_review_blocking_item_count=0" in output
    assert "history_2_review_warning_item_count=0" in output
    assert "history_2_send_blocker_count=0" in output
    assert "history_2_governance_blocking_reasons=" in output
    assert "history_2_bundle_count=1" in output
    assert "history_2_missing_bundle_count=0" in output
    assert "history_2_dispatch_state=dispatch_failed" in output
    assert "history_2_provider_message_id=tg-41" in output


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

        def report_artifact_lineage_from_surface(self, surface: dict) -> dict:
            return {"artifact": surface.get("artifact")}

        def summarize_rerun_compare_surface(self, surface: dict | None, db_candidates: list[dict], *, subject: str) -> dict:
            assert subject == "main"
            return {"subject": subject, "verdict": "aligned", "candidate_count": len(db_candidates), "compare_outcome": "no_rerun_gap"}

        def summarize_db_candidate_history(self, history_surfaces: list[dict], db_candidates: list[dict]) -> list[dict]:
            assert history_surfaces == []
            return []

    class _DummyHelper:
        def list_db_delivery_candidates(self, **_: object) -> list[dict]:
            return [{"artifact_id": "artifact-1", "ready_for_delivery": True}]

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())
    monkeypatch.setattr(_module, "MainReportDeliveryDispatchHelper", lambda: _DummyHelper())

    payload = build_status_payload(
        business_date="2099-04-22",
        history_limit=3,
        resolution={"mode": "latest_active_lookup", "requested_slot": "mid", "business_date": "2099-04-22"},
    )

    assert payload["resolution"]["mode"] == "latest_active_lookup"
    assert payload["resolution"]["requested_slot"] == "mid"
    assert payload["business_date"] == "2099-04-22"
    assert payload["db_candidates"][0]["artifact_id"] == "artifact-1"
    assert payload["db_candidate_alignment_summary"]["verdict"] == "aligned"
    assert payload["rerun_compare_summary"]["compare_outcome"] == "no_rerun_gap"


def test_resolve_latest_main_business_date_uses_store_latest_operator_review_surface(monkeypatch) -> None:
    class _DummyStore:
        def get_latest_active_report_operator_review_surface(self, **kwargs: object) -> dict:
            assert kwargs["agent_domain"] == "main"
            assert kwargs["artifact_family"] == "main_final_report"
            assert kwargs["strongest_slot"] == "late"
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
                        "strongest_slot": "late",
                    },
                },
                "review_summary": {"go_no_go_decision": "GO"},
            }

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())

    resolved = resolve_latest_main_business_date(slot="late")

    assert resolved == {
        "business_date": "2099-04-22",
        "artifact_id": "artifact-active",
        "report_run_id": "run-active",
        "status": "active",
        "updated_at": "2099-04-22T08:00:00+00:00",
        "strongest_slot": "late",
    }


def test_main_cli_json_contract_uses_operator_review_payload(monkeypatch, capsys) -> None:
    class _DummyStore:
        def get_active_report_operator_review_surface(self, **kwargs: object) -> dict:
            assert kwargs["business_date"] == "2099-04-22"
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
                    "slot_evaluation": {"strongest_slot": "late"},
                },
                "llm_lineage_summary": {
                    "status": "applied",
                    "summary_line": "applied [applied=1/1 | primary=1 | models=grok41_thinking]",
                },
                "review_summary": {
                    "go_no_go_decision": "REVIEW",
                    "selected_artifact_id": "artifact-selected",
                    "current_artifact_id": "artifact-active",
                },
            }

        def list_report_operator_review_surfaces(self, **_: object) -> list[dict]:
            return []

        def report_artifact_lineage_from_surface(self, surface: dict) -> dict:
            return {"artifact": surface.get("artifact")}

        def summarize_rerun_compare_surface(self, surface: dict | None, db_candidates: list[dict], *, subject: str) -> dict:
            return {"subject": subject, "verdict": "aligned", "candidate_count": len(db_candidates), "compare_outcome": "no_rerun_gap"}

        def summarize_db_candidate_history(self, history_surfaces: list[dict], db_candidates: list[dict]) -> list[dict]:
            return []

    class _DummyHelper:
        def list_db_delivery_candidates(self, **_: object) -> list[dict]:
            return [{"artifact_id": "artifact-selected", "ready_for_delivery": True}]

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())
    monkeypatch.setattr(_module, "MainReportDeliveryDispatchHelper", lambda: _DummyHelper())
    monkeypatch.setattr("sys.argv", ["fsj_main_delivery_status.py", "--business-date", "2099-04-22", "--format", "json"])

    _module.main()
    output = capsys.readouterr().out

    assert '"artifact_id": "artifact-active"' in output
    assert '"operator_review_bundle_path": "/tmp/pkg/operator_review_bundle.json"' in output
    assert '"go_no_go_decision": "REVIEW"' in output
    assert '"llm_lineage_summary": {' in output
    assert '"summary_line": "applied [applied=1/1 | primary=1 | models=grok41_thinking]"' in output
    assert '"db_candidate_alignment_summary": {' in output
    assert '"rerun_compare_summary": {' in output
    assert '"compare_outcome": "no_rerun_gap"' in output
    assert '"candidate_count": 1' in output


def test_resolve_latest_main_business_date_rejects_unknown_slot() -> None:
    with pytest.raises(ValueError, match="unsupported slot"):
        resolve_latest_main_business_date(slot="close")


@pytest.mark.parametrize("entrypoint", ["resolve_latest_main_business_date", "build_status_payload"])
def test_default_store_main_status_entrypoints_require_explicit_non_live_db_under_pytest(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    _clear_caches()

    with pytest.raises(LiveIsolationError, match="DATABASE_URL must be set explicitly"):
        if entrypoint == "resolve_latest_main_business_date":
            resolve_latest_main_business_date(slot="late")
        else:
            build_status_payload(business_date="2099-04-22")


@pytest.mark.parametrize("entrypoint", ["resolve_latest_main_business_date", "build_status_payload"])
def test_default_store_main_status_entrypoints_reject_canonical_live_db_under_pytest(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", LIVE_DB_URL)
    _clear_caches()

    with pytest.raises(LiveIsolationError, match="canonical/live DB"):
        if entrypoint == "resolve_latest_main_business_date":
            resolve_latest_main_business_date(slot="late")
        else:
            build_status_payload(business_date="2099-04-22")


def test_resolve_latest_main_business_date_allows_explicit_test_db_when_store_is_injected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    _clear_caches()

    class _DummyLatestStore:
        def get_latest_active_report_operator_review_surface(self, **_: object) -> dict[str, object] | None:
            return {
                "artifact": {
                    "business_date": "2099-04-22",
                    "artifact_id": "artifact-active",
                    "report_run_id": "run-active",
                    "status": "active",
                    "updated_at": "2099-04-22T10:00:00+00:00",
                },
                "package_state": {"slot_evaluation": {"strongest_slot": "late"}},
            }

    resolved = resolve_latest_main_business_date(slot="late", store=_DummyLatestStore())

    assert resolved == {
        "business_date": "2099-04-22",
        "artifact_id": "artifact-active",
        "report_run_id": "run-active",
        "status": "active",
        "updated_at": "2099-04-22T10:00:00+00:00",
        "strongest_slot": "late",
    }
