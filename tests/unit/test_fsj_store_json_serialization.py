from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import ifa_data_platform.fsj.store as store_module
from ifa_data_platform.fsj.store import FSJStore


class _ProjectionOnlyStore(FSJStore):
    def __init__(self) -> None:
        pass


def test_json_dumps_normalizes_non_native_json_types() -> None:
    store = _ProjectionOnlyStore()

    dumped = store._json_dumps(
        {
            "whole": Decimal("12"),
            "fraction": Decimal("12.34"),
            "date": date(2026, 4, 23),
            "dt": datetime(2026, 4, 23, 11, 42, 0),
            "path": Path("/tmp/example"),
        }
    )

    payload = json.loads(dumped)
    assert payload == {
        "whole": 12,
        "fraction": 12.34,
        "date": "2026-04-23",
        "dt": "2026-04-23T11:42:00",
        "path": "/tmp/example",
    }


def test_report_workflow_handoff_projection_preserves_operator_readiness_fields() -> None:
    from ifa_data_platform.fsj.store import FSJStore

    store = _ProjectionOnlyStore()
    summary = store.report_workflow_handoff_from_surface({
        "artifact": {
            "artifact_id": "artifact-current",
            "report_run_id": "run-current",
            "business_date": "2099-04-22",
            "status": "active",
        },
        "delivery_package": {
            "package_state": "ready",
            "ready_for_delivery": True,
            "quality_gate": {
                "score": 93,
                "blocker_count": 0,
                "warning_count": 1,
                "qa_axes": {"structural": {"ready": True, "score": 92, "blocker_count": 0, "warning_count": 1, "issue_codes": ["html_too_small"]}},
                "late_contract_mode": "full_close_package",
            },
            "workflow": {
                "recommended_action": "send_review",
                "dispatch_recommended_action": "send",
                "workflow_state": "selected_candidate_mismatch",
                "next_step": "operator_review_selected_candidate",
                "selection_reason": "best_ready_candidate strongest_slot=late qa_score=93",
                "dispatch_selected_artifact_id": "artifact-selected",
                "send_blockers": ["selected_candidate_differs_from_current"],
            },
        },
        "workflow_linkage": {
            "selected_handoff": {
                "selected_artifact_id": "artifact-selected",
                "selected_report_run_id": "run-selected",
                "selected_business_date": "2099-04-22",
                "selected_is_current": False,
                "delivery_package_dir": "/tmp/selected-pkg",
                "delivery_manifest_path": "/tmp/selected-pkg/delivery_manifest.json",
                "delivery_zip_path": "/tmp/selected-pkg.zip",
                "telegram_caption_path": "/tmp/selected-pkg/telegram_caption.txt",
            },
            "send_manifest_path": "/tmp/current/send_manifest.json",
        },
    })

    assert summary["selected_handoff"]["selected_is_current"] is False
    assert summary["selected_handoff"]["selected_artifact_id"] == "artifact-selected"
    assert summary["state"]["dispatch_recommended_action"] == "send"
    assert summary["state"]["qa_axes"]["structural"]["score"] == 92
    assert summary["state"]["next_step"] == "operator_review_selected_candidate"
    assert summary["state"]["selection_reason"] == "best_ready_candidate strongest_slot=late qa_score=93"
    assert summary["state"]["dispatch_selected_artifact_id"] == "artifact-selected"
    assert summary["state"]["send_blockers"] == ["selected_candidate_differs_from_current"]


def test_report_package_surface_projection_preserves_review_and_send_package_pointers() -> None:
    store = _ProjectionOnlyStore()
    surface = {
        "artifact": {
            "artifact_id": "artifact-current",
            "report_run_id": "run-current",
            "business_date": "2099-04-22",
            "status": "active",
            "artifact_version": "v1",
        },
        "delivery_package": {
            "delivery_package_dir": "/tmp/current-pkg",
            "package_state": "ready",
            "ready_for_delivery": True,
            "quality_gate": {"score": 93, "blocker_count": 0, "warning_count": 1},
            "slot_evaluation": {"strongest_slot": "late"},
            "dispatch_advice": {"recommended_action": "send_review"},
            "support_summary_aggregate": {"domain_count": 3},
            "lineage": {"bundle_id": "bundle-selected"},
            "artifacts": {
                "delivery_manifest": "delivery_manifest.json",
                "send_manifest": "send_manifest.json",
                "review_manifest": "review_manifest.json",
                "workflow_manifest": "workflow_manifest.json",
                "package_index": "package_index.json",
            },
            "workflow": {
                "recommended_action": "send_review",
                "workflow_state": "selected_candidate_mismatch",
            },
        },
        "workflow_linkage": {
            "selected_handoff": {
                "selected_artifact_id": "artifact-selected",
                "selected_report_run_id": "run-selected",
                "selected_business_date": "2099-04-22",
                "selected_is_current": False,
                "delivery_package_dir": "/tmp/selected-pkg",
                "delivery_manifest_path": "/tmp/selected-pkg/delivery_manifest.json",
                "delivery_zip_path": "/tmp/selected-pkg.zip",
                "telegram_caption_path": "/tmp/selected-pkg/telegram_caption.txt",
            },
            "send_manifest_path": "/tmp/current/send_manifest.json",
            "review_manifest_path": "/tmp/current/review_manifest.json",
            "workflow_manifest_path": "/tmp/current/workflow_manifest.json",
            "operator_review_bundle_path": "/tmp/current/operator_review_bundle.json",
            "operator_review_readme_path": "/tmp/current/OPERATOR_REVIEW.md",
        },
    }

    summary = store.report_package_surface_from_surface(surface)

    assert summary["artifact"]["artifact_id"] == "artifact-current"
    assert summary["selected_handoff"]["selected_artifact_id"] == "artifact-selected"
    assert summary["package_paths"]["delivery_package_dir"] == "/tmp/selected-pkg"
    assert summary["package_paths"]["delivery_manifest_path"] == "/tmp/selected-pkg/delivery_manifest.json"
    assert summary["package_paths"]["send_manifest_path"] == "/tmp/current/send_manifest.json"
    assert summary["package_paths"]["review_manifest_path"] == "/tmp/current/review_manifest.json"
    assert summary["package_paths"]["operator_review_bundle_path"] == "/tmp/current/operator_review_bundle.json"
    assert summary["package_versions"]["artifact_version"] == "v1"
    assert summary["package_versions"]["review_manifest_version"] == "review_manifest.json"
    assert summary["package_state"]["support_summary_aggregate"]["domain_count"] == 3
    assert summary["package_state"]["lineage"]["bundle_id"] == "bundle-selected"
    assert summary["workflow_handoff"]["state"]["workflow_state"] == "selected_candidate_mismatch"


def test_report_operator_review_surface_projection_prefers_db_backed_review_payload() -> None:
    class _Store(_ProjectionOnlyStore):
        def get_bundle_graph(self, bundle_id: str) -> dict | None:
            graphs = {
                "bundle-early": {
                    "bundle": {
                        "bundle_id": "bundle-early",
                        "slot": "early",
                        "section_key": "pre_open_main",
                        "summary": "early summary",
                        "payload_json": {
                            "llm_assist": {
                                "applied": False,
                                "model_alias": "grok41_thinking",
                                "prompt_version": "fsj_early_main_v1",
                                "failure_classification": "timeout",
                                "policy": {
                                    "outcome": "deterministic_degrade",
                                    "operator_tag": "llm_timeout",
                                    "attempted_model_chain": ["grok41_thinking", "gemini31_pro_jmr"],
                                },
                            }
                        },
                    }
                },
                "bundle-late": {
                    "bundle": {
                        "bundle_id": "bundle-late",
                        "slot": "late",
                        "section_key": "post_close_main",
                        "summary": "late summary",
                        "payload_json": {
                            "llm_assist": {
                                "applied": True,
                                "model_alias": "gemini31_pro_jmr",
                                "prompt_version": "fsj_late_main_v1",
                                "policy": {
                                    "outcome": "fallback_applied",
                                    "attempted_model_chain": ["grok41_thinking", "gemini31_pro_jmr"],
                                },
                            }
                        },
                    }
                },
            }
            return graphs.get(bundle_id)

    store = _Store()
    surface = {
        "artifact": {
            "artifact_id": "artifact-current",
            "report_run_id": "run-current",
            "business_date": "2099-04-22",
            "status": "active",
            "artifact_version": "v2",
            "metadata_json": {"bundle_ids": ["bundle-early", "bundle-late"]},
        },
        "delivery_package": {
            "delivery_package_dir": "/tmp/current-pkg",
            "package_state": "ready",
            "ready_for_delivery": False,
            "quality_gate": {"score": 91, "blocker_count": 1, "warning_count": 2},
            "workflow": {
                "recommended_action": "send_review",
                "workflow_state": "review_required",
            },
        },
        "workflow_linkage": {
            "selected_handoff": {
                "selected_artifact_id": "artifact-selected",
                "selected_is_current": False,
                "delivery_package_dir": "/tmp/selected-pkg",
                "delivery_manifest_path": "/tmp/selected-pkg/delivery_manifest.json",
            },
            "review_surface": {
                "candidate_comparison": {
                    "selected_artifact_id": "artifact-selected",
                    "current_artifact_id": "artifact-current",
                    "candidate_count": 2,
                    "ready_candidate_count": 1,
                    "ranked_candidates": [
                        {"artifact_id": "artifact-selected", "ready_for_delivery": True},
                        {"artifact_id": "artifact-current", "ready_for_delivery": False},
                    ],
                    "current_vs_selected": {
                        "current_artifact_id": "artifact-current",
                        "selected_artifact_id": "artifact-selected",
                        "current_rank": 2,
                        "selected_rank": 1,
                    },
                },
                "operator_go_no_go": {
                    "decision": "NO_GO",
                    "artifact_integrity_ok": True,
                    "missing_artifacts": [],
                    "approver_kind": "human_operator",
                    "approver_id": "op-17",
                    "approver_label": "night-shift-operator",
                    "decided_at": "2099-04-22T09:58:00Z",
                },
                "review_manifest": {"next_step": "switch_to_selected_package_and_do_not_send_current"},
                "send_manifest": {"next_step": "switch_to_selected_package_and_do_not_send_current"},
            },
        },
    }

    summary = store.report_operator_review_surface_from_surface(surface)

    assert summary["candidate_comparison"]["selected_artifact_id"] == "artifact-selected"
    assert summary["candidate_comparison"]["current_artifact_id"] == "artifact-current"
    assert summary["candidate_comparison"]["candidate_count"] == 2
    assert summary["candidate_comparison"]["ready_candidate_count"] == 1
    assert summary["operator_go_no_go"]["decision"] == "NO_GO"
    assert summary["review_manifest"]["next_step"] == "switch_to_selected_package_and_do_not_send_current"
    assert summary["promotion_authority"] == {
        "scope": "review_ready_to_send_ready",
        "status": "blocked",
        "approved": False,
        "authority_kind": "system_policy_projection",
        "decision": "NO_GO",
        "approver_ref": "operator_go_no_go",
        "artifact_id": "artifact-current",
        "selected_artifact_id": "artifact-selected",
        "selected_is_current": False,
        "required_action": "switch_to_selected_package_and_do_not_send_current",
        "rationale": None,
        "source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff",
        "summary_line": "blocked | decision=NO_GO | selected_is_current=False | required_action=switch_to_selected_package_and_do_not_send_current | rationale=-",
        "approver_kind": "human_operator",
        "approver_id": "op-17",
        "approver_label": "night-shift-operator",
        "decided_at": "2099-04-22T09:58:00Z",
        "approver_summary": "kind=human_operator | id=op-17 | label=night-shift-operator | decided_at=2099-04-22T09:58:00Z",
    }
    assert summary["governance"] == {
        "decision": "NO_GO",
        "rationale": None,
        "next_step": "switch_to_selected_package_and_do_not_send_current",
        "selected_is_current": False,
        "action_required": True,
        "review_blocking_item_count": 0,
        "review_warning_item_count": 0,
        "send_blocker_count": 0,
        "blocking_reasons": [],
    }
    assert summary["review_summary"]["go_no_go_decision"] == "NO_GO"
    assert summary["review_summary"]["operator_next_step"] == "switch_to_selected_package_and_do_not_send_current"
    assert summary["review_summary"]["promotion_authority_status"] == "blocked"
    assert summary["review_summary"]["promotion_authority_approved"] is False
    assert summary["review_summary"]["promotion_authority_required_action"] == "switch_to_selected_package_and_do_not_send_current"
    assert summary["review_summary"]["promotion_authority_summary"] == "blocked | decision=NO_GO | selected_is_current=False | required_action=switch_to_selected_package_and_do_not_send_current | rationale=-"
    assert summary["review_summary"]["promotion_authority_source_of_truth"] == "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"
    assert summary["review_summary"]["promotion_authority_approver_kind"] == "human_operator"
    assert summary["review_summary"]["promotion_authority_approver_id"] == "op-17"
    assert summary["review_summary"]["promotion_authority_approver_label"] == "night-shift-operator"
    assert summary["review_summary"]["promotion_authority_decided_at"] == "2099-04-22T09:58:00Z"
    assert summary["review_summary"]["promotion_authority_approver_summary"] == "kind=human_operator | id=op-17 | label=night-shift-operator | decided_at=2099-04-22T09:58:00Z"
    assert summary["review_summary"]["governance_blocking_reasons"] == []
    assert summary["dispatch_state"] is None
    assert summary["review_summary"]["selected_is_current"] is False
    assert summary["package_paths"]["delivery_package_dir"] == "/tmp/selected-pkg"
    assert summary["llm_lineage"]["summary"]["bundle_count"] == 2
    assert summary["llm_lineage"]["summary"]["applied_count"] == 1
    assert summary["llm_lineage"]["summary"]["degraded_count"] == 1
    assert summary["llm_lineage"]["summary"]["fallback_applied_count"] == 1
    assert summary["llm_lineage"]["summary"]["operator_tags"] == ["llm_timeout"]
    assert summary["llm_lineage_summary"]["status"] == "degraded"
    assert summary["llm_lineage_summary"]["models"] == ["gemini31_pro_jmr", "grok41_thinking"]
    assert summary["llm_lineage_summary"]["usage_bundle_count"] == 0
    assert summary["llm_lineage_summary"]["token_totals"]["total_tokens"] == 0
    assert summary["llm_lineage_summary"]["uncosted_bundle_count"] == 0
    assert summary["llm_lineage_summary"]["summary_line"] == "degraded [applied=1/2 | fallback=1 | degraded=1 | deterministic=1 | tags=llm_timeout | slots=early,late | models=gemini31_pro_jmr,grok41_thinking | prompts=fsj_early_main_v1,fsj_late_main_v1]"
    assert summary["review_summary"]["llm_bundle_count"] == 2
    assert summary["review_summary"]["llm_applied_count"] == 1
    assert summary["review_summary"]["llm_degraded_count"] == 1
    assert summary["review_summary"]["llm_fallback_count"] == 1
    assert summary["review_summary"]["llm_lineage_status"] == "degraded"
    assert summary["review_summary"]["llm_total_tokens"] == 0
    assert summary["review_summary"]["llm_models"] == ["gemini31_pro_jmr", "grok41_thinking"]
    assert summary["review_summary"]["llm_uncosted_bundle_count"] == 0
    assert summary["review_summary"]["llm_lineage_summary"] == "degraded [applied=1/2 | fallback=1 | degraded=1 | deterministic=1 | tags=llm_timeout | slots=early,late | models=gemini31_pro_jmr,grok41_thinking | prompts=fsj_early_main_v1,fsj_late_main_v1]"
    assert summary["llm_role_policy"]["slot_boundary_modes"] == {}
    assert summary["review_summary"]["llm_deterministic_owner_fields"] == []
    assert summary["review_summary"]["llm_override_precedence"] == []
    assert summary["review_summary"]["llm_slot_boundary_modes"] == {}
    assert summary["board_state_source"]["canonical_state"] == "review_ready"
    assert summary["board_state_source"]["state_source_of_truth"] == "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"
    assert summary["board_state_source"]["blocking_reason_source_of_truth"] is None
    assert summary["board_state_source"]["next_action_source_of_truth"] == "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step"
    assert summary["review_summary"]["board_state_source"]["canonical_reason"] == "manual_review_required"
    assert summary["canonical_state_vocabulary"] == {
        "canonical_state": "review_ready",
        "canonical_reason": "manual_review_required",
        "status_semantic": "review",
        "operator_bucket": "operator_gate",
        "terminal": False,
        "summary_line": "canonical=review_ready | status=review | bucket=operator_gate",
    }


def test_report_artifact_lineage_projection_unifies_package_review_send_and_bundle_surfaces() -> None:
    class _Store(_ProjectionOnlyStore):
        def get_bundle_graph(self, bundle_id: str) -> dict | None:
            if bundle_id == "bundle-missing":
                return None
            return {
                "bundle": {
                    "bundle_id": bundle_id,
                    "status": "active",
                    "slot": "late",
                    "agent_domain": "main",
                    "section_key": "post_close_main",
                    "section_type": "thesis",
                    "bundle_topic_key": "theme:robotics",
                    "report_run_id": "run-current",
                    "summary": "late summary",
                }
            }

    summary = _Store().report_artifact_lineage_from_surface(
        {
            "artifact": {
                "artifact_id": "artifact-current",
                "artifact_family": "main_final_report",
                "artifact_type": "html",
                "title": "Main report",
                "business_date": "2099-04-22",
                "agent_domain": "main",
                "status": "active",
                "report_run_id": "run-current",
                "supersedes_artifact_id": "artifact-prev",
                "metadata_json": {"bundle_ids": ["bundle-1", "bundle-missing"]},
            },
            "delivery_package": {
                "delivery_package_dir": "/tmp/current-pkg",
                "package_state": "ready",
                "ready_for_delivery": True,
                "lineage": {"bundle_ids": ["bundle-1", "bundle-missing"]},
                "quality_gate": {"score": 99, "blocker_count": 0, "warning_count": 0},
                "artifacts": {
                    "delivery_manifest": "delivery_manifest.json",
                    "send_manifest": "send_manifest.json",
                    "review_manifest": "review_manifest.json",
                    "workflow_manifest": "workflow_manifest.json",
                    "package_index": "package_index.json",
                },
                "workflow": {
                    "recommended_action": "send",
                    "workflow_state": "ready_to_send",
                    "next_step": "send_selected_package_to_primary_channel",
                    "selection_reason": "best_ready_candidate strongest_slot=late qa_score=99",
                },
            },
            "workflow_linkage": {
                "selected_handoff": {
                    "selected_artifact_id": "artifact-current",
                    "selected_report_run_id": "run-current",
                    "selected_business_date": "2099-04-22",
                    "selected_is_current": True,
                },
                "send_manifest_path": "/tmp/current-pkg/send_manifest.json",
                "review_manifest_path": "/tmp/current-pkg/review_manifest.json",
                "workflow_manifest_path": "/tmp/current-pkg/workflow_manifest.json",
                "review_surface": {
                    "operator_go_no_go": {"decision": "GO"},
                    "candidate_comparison": {"candidate_count": 2, "selected_artifact_id": "artifact-current"},
                    "send_manifest": {"next_step": "send_selected_package_to_primary_channel"},
                    "review_manifest": {"next_step": "send_selected_package_to_primary_channel"},
                    "governance": {
                        "decision": "GO",
                        "rationale": "quality gate and artifact integrity both pass",
                        "next_step": "send_selected_package_to_primary_channel",
                        "action_required": False,
                    },
                    "promotion_authority": {
                        "status": "approved_to_send",
                        "approved": True,
                        "required_action": "send_selected_package_to_primary_channel",
                        "rationale": "quality gate and artifact integrity both pass",
                        "summary_line": "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass",
                        "source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff",
                    },
                    "review_summary": {
                        "go_no_go_decision": "GO",
                        "operator_decision_rationale": "quality gate and artifact integrity both pass",
                        "operator_next_step": "send_selected_package_to_primary_channel",
                        "operator_action_required": False,
                        "promotion_authority_status": "approved_to_send",
                        "promotion_authority_approved": True,
                        "promotion_authority_required_action": "send_selected_package_to_primary_channel",
                        "promotion_authority_rationale": "quality gate and artifact integrity both pass",
                        "promotion_authority_summary": "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass",
                        "promotion_authority_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff",
                    },
                    "board_state_source": {
                        "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff",
                        "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step",
                    },
                    "canonical_state_vocabulary": {
                        "status_semantic": "ready",
                        "operator_bucket": "dispatch_gate",
                    },
                    "dispatch_receipt": {
                        "dispatch_state": "dispatch_succeeded",
                        "channel": "telegram_document",
                        "provider_message_id": "42",
                        "succeeded_at": "2099-04-22T10:00:03Z",
                    },
                },
            },
        }
    )

    assert summary is not None
    assert summary["artifact"]["artifact_id"] == "artifact-current"
    assert summary["selection"]["selected_is_current"] is True
    assert summary["package"]["manifests"]["send_manifest"]["path"] == "/tmp/current-pkg/send_manifest.json"
    assert summary["review"]["operator_go_no_go"]["decision"] == "GO"
    assert summary["governance"]["decision"] == "GO"
    assert summary["governance"]["next_step"] == "send_selected_package_to_primary_channel"
    assert summary["governance"]["action_required"] is False
    assert summary["promotion_authority"]["status"] == "approved_to_send"
    assert summary["promotion_authority"]["source_of_truth"] == "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"
    assert summary["review_summary"]["go_no_go_decision"] == "GO"
    assert summary["review_summary"]["promotion_authority_source_of_truth"] == "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"
    assert summary["board_state_source"]["state_source_of_truth"].startswith(
        "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"
    )
    assert summary["canonical_state_vocabulary"]["status_semantic"] == "sent"
    assert summary["canonical_state_vocabulary"]["operator_bucket"] == "terminal"
    assert summary["dispatch"]["dispatch_state"] == "dispatch_succeeded"
    assert summary["what_user_received"]["provider_message_id"] == "42"
    assert summary["what_user_received"]["channel"] == "telegram_document"
    assert summary["bundle_lineage_summary"]["bundle_count"] == 2
    assert summary["bundle_lineage_summary"]["missing_bundle_count"] == 1
    assert summary["bundle_lineage"][0]["section_key"] == "post_close_main"
    assert summary["bundle_lineage"][1]["missing"] is True


def test_summarize_report_artifact_registry_exposes_version_chain_audit_surface() -> None:
    store = _ProjectionOnlyStore()

    active = {
        "artifact": {
            "artifact_id": "artifact-current",
            "artifact_family": "main_final_report",
            "business_date": "2099-04-22",
            "agent_domain": "main",
            "report_run_id": "run-current",
        },
        "what_user_received": {"dispatch_state": "dispatch_succeeded"},
        "bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 0},
    }
    history = [
        {
            "artifact": {
                "artifact_id": "artifact-current",
                "status": "active",
                "report_run_id": "run-current",
                "artifact_family": "main_final_report",
                "business_date": "2099-04-22",
                "agent_domain": "main",
                "supersedes_artifact_id": "artifact-prev",
            },
            "selection": {"selected_is_current": True, "selected_artifact_id": "artifact-current"},
            "canonical_lifecycle": {"state": "sent", "reason": "dispatch_receipt_succeeded"},
            "what_user_received": {"dispatch_state": "dispatch_succeeded", "provider_message_id": "42"},
            "bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 0},
            "governance": {"decision": "GO"},
            "promotion_authority": {"status": "approved_to_send"},
        },
        {
            "artifact": {
                "artifact_id": "artifact-prev",
                "status": "superseded",
                "report_run_id": "run-prev",
                "artifact_family": "main_final_report",
                "business_date": "2099-04-22",
                "agent_domain": "main",
                "supersedes_artifact_id": "artifact-root",
            },
            "selection": {"selected_is_current": False, "selected_artifact_id": "artifact-current"},
            "canonical_lifecycle": {"state": "superseded", "reason": "artifact_status_superseded"},
            "what_user_received": {"dispatch_state": None, "provider_message_id": None},
            "bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 0},
            "governance": {"decision": "HOLD"},
            "promotion_authority": {"status": "blocked"},
        },
    ]

    summary = store.summarize_report_artifact_registry(active_lineage=active, history_lineages=history)

    assert summary["active_artifact_id"] == "artifact-current"
    assert summary["chain_depth"] == 2
    assert summary["superseded_count"] == 1
    assert summary["withdrawn_count"] == 0
    assert summary["sent_count"] == 1
    assert summary["head_matches_history"] is True
    assert summary["dangling_supersedes_ids"] == ["artifact-root"]
    assert summary["multiply_superseded_artifact_ids"] == []
    assert summary["version_chain"][0]["is_active_head"] is True
    assert summary["version_chain"][0]["dispatch_state"] == "dispatch_succeeded"
    assert summary["version_chain"][1]["supersedes_artifact_id"] == "artifact-root"
    assert summary["summary_line"] == "head=artifact-current | depth=2 | superseded=1 | withdrawn=0 | sent=1 | dangling_supersedes=1 | multiply_superseded=0"


def test_project_report_state_vocabulary_exposes_explicit_canonical_mapping() -> None:
    store = _ProjectionOnlyStore()

    assert store.project_report_state_vocabulary(canonical_state="planned") == {
        "canonical_state": "planned",
        "canonical_reason": None,
        "status_semantic": "planned",
        "operator_bucket": "pre_runtime",
        "terminal": False,
        "summary_line": "canonical=planned | status=planned | bucket=pre_runtime",
    }
    assert store.project_report_state_vocabulary(canonical_state="collecting") == {
        "canonical_state": "collecting",
        "canonical_reason": None,
        "status_semantic": "running",
        "operator_bucket": "inflight",
        "terminal": False,
        "summary_line": "canonical=collecting | status=running | bucket=inflight",
    }
    assert store.project_report_state_vocabulary(canonical_state="send_ready") == {
        "canonical_state": "send_ready",
        "canonical_reason": None,
        "status_semantic": "ready",
        "operator_bucket": "dispatch_gate",
        "terminal": False,
        "summary_line": "canonical=send_ready | status=ready | bucket=dispatch_gate",
    }
    assert store.project_report_state_vocabulary(
        canonical_lifecycle={"state": "sent", "reason": "dispatch_receipt_succeeded"}
    ) == {
        "canonical_state": "sent",
        "canonical_reason": "dispatch_receipt_succeeded",
        "status_semantic": "sent",
        "operator_bucket": "terminal",
        "terminal": True,
        "summary_line": "canonical=sent | status=sent | bucket=terminal",
    }
    assert store.project_report_state_vocabulary(
        canonical_lifecycle={"state": "failed", "reason": "dispatch_receipt_failed"}
    ) == {
        "canonical_state": "failed",
        "canonical_reason": "dispatch_receipt_failed",
        "status_semantic": "held",
        "operator_bucket": "terminal_attention",
        "terminal": True,
        "summary_line": "canonical=failed | status=held | bucket=terminal_attention",
    }


def test_project_report_transition_integrity_flags_dispatch_without_sendable_workflow() -> None:
    store = _ProjectionOnlyStore()

    assert store.project_report_transition_integrity(
        recommended_action="hold",
        ready_for_delivery=True,
        dispatch_state="dispatch_succeeded",
    ) == {
        "valid": False,
        "invalid_transition": True,
        "reason_code": "dispatch_receipt_without_sendable_workflow",
        "summary_line": "invalid | dispatch_receipt_without_sendable_workflow | dispatch_state=dispatch_succeeded | recommended_action=hold | ready_for_delivery=True",
    }



def test_report_operator_review_surface_projects_dispatch_state_from_receipt_and_send_ready() -> None:
    store = _ProjectionOnlyStore()

    ready_summary = store.report_operator_review_surface_from_surface(
        {
            "artifact": {"artifact_id": "artifact-ready"},
            "delivery_package": {
                "package_state": "ready",
                "ready_for_delivery": True,
                "quality_gate": {"score": 98, "blocker_count": 0, "warning_count": 0},
                "workflow": {"recommended_action": "send", "workflow_state": "ready_to_send"},
            },
            "workflow_linkage": {
                "review_surface": {
                    "send_manifest": {"next_step": "send_selected_package_to_primary_channel"},
                    "review_manifest": {"next_step": "send_selected_package_to_primary_channel"},
                }
            },
        }
    )
    attempted_summary = store.report_operator_review_surface_from_surface(
        {
            "artifact": {"artifact_id": "artifact-attempted"},
            "delivery_package": {
                "package_state": "ready",
                "ready_for_delivery": True,
                "quality_gate": {"score": 98, "blocker_count": 0, "warning_count": 0},
                "workflow": {"recommended_action": "send", "workflow_state": "ready_to_send"},
            },
            "workflow_linkage": {
                "dispatch_receipt": {
                    "dispatch_state": "dispatch_attempted",
                    "attempted_at": "2099-04-22T10:00:00Z",
                    "channel": "telegram_document",
                },
                "review_surface": {
                    "send_manifest": {"next_step": "send_selected_package_to_primary_channel"},
                    "review_manifest": {"next_step": "send_selected_package_to_primary_channel"},
                },
            },
        }
    )
    failed_summary = store.report_operator_review_surface_from_surface(
        {
            "artifact": {"artifact_id": "artifact-failed"},
            "delivery_package": {
                "package_state": "ready",
                "ready_for_delivery": True,
                "quality_gate": {"score": 98, "blocker_count": 0, "warning_count": 0},
                "workflow": {"recommended_action": "send", "workflow_state": "ready_to_send"},
            },
            "workflow_linkage": {
                "review_surface": {
                    "dispatch_receipt": {
                        "dispatch_state": "dispatch_failed",
                        "attempted_at": "2099-04-22T10:00:00Z",
                        "failed_at": "2099-04-22T10:00:02Z",
                        "error": "429 rate limit",
                    },
                    "send_manifest": {"next_step": "send_selected_package_to_primary_channel"},
                    "review_manifest": {"next_step": "send_selected_package_to_primary_channel"},
                }
            },
        }
    )

    assert ready_summary["dispatch_state"] == "ready_to_dispatch"
    assert ready_summary["canonical_lifecycle"]["state"] == "send_ready"
    assert ready_summary["review_summary"]["dispatch_state"] == "ready_to_dispatch"
    assert ready_summary["review_summary"]["canonical_lifecycle_state"] == "send_ready"
    assert attempted_summary["dispatch_state"] == "dispatch_attempted"
    assert attempted_summary["canonical_lifecycle"]["state"] == "send_ready"
    assert attempted_summary["dispatch_receipt"]["channel"] == "telegram_document"
    assert attempted_summary["review_summary"]["dispatch_attempted"] is True
    assert failed_summary["dispatch_state"] == "dispatch_failed"
    assert failed_summary["canonical_lifecycle"]["state"] == "failed"
    assert failed_summary["dispatch_receipt"]["error"] == "429 rate limit"
    assert failed_summary["review_summary"]["dispatch_failed"] is True



def test_report_operator_review_surface_projects_invalid_dispatch_transition_as_failed_attention() -> None:
    store = _ProjectionOnlyStore()

    invalid_summary = store.report_operator_review_surface_from_surface(
        {
            "artifact": {"artifact_id": "artifact-invalid-dispatch"},
            "delivery_package": {
                "package_state": "ready",
                "ready_for_delivery": True,
                "quality_gate": {"score": 98, "blocker_count": 0, "warning_count": 0},
                "workflow": {"recommended_action": "hold", "workflow_state": "hold"},
            },
            "workflow_linkage": {
                "review_surface": {
                    "dispatch_receipt": {
                        "dispatch_state": "dispatch_succeeded",
                        "attempted_at": "2099-04-22T10:00:00Z",
                        "succeeded_at": "2099-04-22T10:00:03Z",
                        "channel": "telegram_document",
                        "provider_message_id": "42",
                    },
                    "send_manifest": {"next_step": "hold_and_fix_quality_gate_before_send"},
                    "review_manifest": {"next_step": "hold_and_fix_quality_gate_before_send"},
                }
            },
        }
    )

    assert invalid_summary["dispatch_state"] == "dispatch_succeeded"
    assert invalid_summary["canonical_lifecycle"]["state"] == "failed"
    assert invalid_summary["canonical_lifecycle"]["reason"] == "dispatch_receipt_without_sendable_workflow"
    assert invalid_summary["transition_integrity"] == {
        "valid": False,
        "invalid_transition": True,
        "reason_code": "dispatch_receipt_without_sendable_workflow",
        "summary_line": "invalid | dispatch_receipt_without_sendable_workflow | dispatch_state=dispatch_succeeded | recommended_action=hold | ready_for_delivery=True",
    }
    assert invalid_summary["review_summary"]["transition_integrity_invalid_transition"] is True
    assert invalid_summary["review_summary"]["transition_integrity_reason_code"] == "dispatch_receipt_without_sendable_workflow"


class _PersistDispatchReceiptConn:
    def __init__(self, row: dict[str, object]) -> None:
        self.row = row
        self.updated_metadata_json: str | None = None

    def execute(self, stmt, params=None):
        sql = str(stmt)
        if "SELECT metadata_json" in sql:
            return _PersistDispatchReceiptResult(self.row)
        if "UPDATE ifa2.ifa_fsj_report_artifacts" in sql:
            self.updated_metadata_json = params["metadata_json"]
            return _PersistDispatchReceiptResult(None)
        raise AssertionError(sql)


class _PersistDispatchReceiptResult:
    def __init__(self, row: dict[str, object] | None) -> None:
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class _PersistDispatchReceiptBegin:
    def __init__(self, conn: _PersistDispatchReceiptConn) -> None:
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class _PersistDispatchReceiptEngine:
    def __init__(self, conn: _PersistDispatchReceiptConn) -> None:
        self.conn = conn

    def begin(self):
        return _PersistDispatchReceiptBegin(self.conn)


class _PersistDispatchReceiptStore(FSJStore):
    def __init__(self, row: dict[str, object]) -> None:
        self.conn = _PersistDispatchReceiptConn(row)
        self.engine = _PersistDispatchReceiptEngine(self.conn)

    def ensure_schema(self) -> None:
        return None

    def get_report_artifact(self, artifact_id: str) -> dict[str, object] | None:
        payload = json.loads(self.conn.updated_metadata_json or "{}")
        return {"artifact_id": artifact_id, "metadata_json": payload}


def test_persist_report_dispatch_receipt_merges_into_workflow_and_review_surface() -> None:
    store = _PersistDispatchReceiptStore(
        {
            "metadata_json": {
                "workflow_linkage": {"send_manifest_path": "/tmp/send_manifest.json"},
                "review_surface": {"send_manifest": {"next_step": "send_selected_package_to_primary_channel"}},
                "delivery_package": {"workflow": {"recommended_action": "send", "workflow_state": "ready_to_send"}},
            }
        }
    )

    refreshed = store.persist_report_dispatch_receipt(
        "artifact-1",
        {
            "dispatch_state": "dispatch_succeeded",
            "attempted_at": "2099-04-22T10:00:00Z",
            "succeeded_at": "2099-04-22T10:00:03Z",
            "channel": "telegram_document",
            "provider_message_id": "42",
        },
    )

    assert refreshed is not None
    metadata = dict(refreshed["metadata_json"])
    assert metadata["workflow_linkage"]["dispatch_receipt"]["dispatch_state"] == "dispatch_succeeded"
    assert metadata["review_surface"]["dispatch_receipt"]["provider_message_id"] == "42"
    assert metadata["delivery_package"]["workflow"]["dispatch_state"] == "dispatch_succeeded"


def test_report_llm_lineage_from_artifact_projects_bundle_level_attempts() -> None:
    class _Store(_ProjectionOnlyStore):
        def get_bundle_graph(self, bundle_id: str) -> dict | None:
            if bundle_id == "bundle-missing":
                return None
            return {
                "bundle": {
                    "bundle_id": bundle_id,
                    "slot": "mid",
                    "section_key": "midday_main",
                    "summary": "mid summary",
                    "payload_json": {
                        "llm_assist": {
                            "applied": True,
                            "model_alias": "grok41_thinking",
                            "model_id": "grok-4.1-thinking",
                            "prompt_version": "fsj_mid_main_v1",
                            "adopted_output_fields": [
                                "bundle.summary",
                                "validation_signal.statement",
                                "afternoon_signal.statement",
                                "judgment.statement",
                                "judgment.invalidators",
                            ],
                            "adopted_output_field_count": 5,
                            "discarded_output_fields": [],
                            "discarded_output_field_count": 0,
                            "field_replay_ready": True,
                            "policy": {
                                "outcome": "primary_applied",
                                "attempted_model_chain": ["grok41_thinking"],
                            },
                        },
                        "llm_role_policy": {
                            "policy_version": "fsj_llm_role_policy_v1",
                            "boundary_mode": "intraday_working",
                            "forbidden_decisions": ["declare_close_final_confirmation"],
                            "deterministic_owner_fields": ["judgment.action"],
                            "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                        },
                    },
                }
            }

    lineage = _Store().report_llm_lineage_from_artifact(
        {
            "artifact_id": "artifact-1",
            "metadata_json": {"bundle_ids": ["bundle-mid", "bundle-missing"]},
        }
    )

    assert lineage["artifact_id"] == "artifact-1"
    assert lineage["summary"]["bundle_count"] == 2
    assert lineage["summary"]["primary_applied_count"] == 1
    assert lineage["summary"]["missing_bundle_count"] == 1
    assert lineage["summary"]["prompt_versions"] == ["fsj_mid_main_v1"]
    assert lineage["summary"]["role_policy_versions"] == ["fsj_llm_role_policy_v1"]
    assert lineage["summary"]["boundary_modes"] == ["intraday_working"]
    assert lineage["summary"]["adopted_output_field_count"] == 5
    assert lineage["summary"]["discarded_output_field_count"] == 0
    assert lineage["summary"]["field_replay_ready_count"] == 1
    assert lineage["summary"]["adopted_output_fields"] == [
        "afternoon_signal.statement",
        "bundle.summary",
        "judgment.invalidators",
        "judgment.statement",
        "validation_signal.statement",
    ]
    assert lineage["role_policy"]["deterministic_owner_fields"] == ["judgment.action"]
    assert lineage["role_policy"]["forbidden_decisions"] == ["declare_close_final_confirmation"]
    assert lineage["role_policy"]["override_precedence"] == ["deterministic_input_contract", "validated_llm_text_fields_only"]
    assert lineage["bundles"][0]["bundle_id"] == "bundle-mid"
    assert lineage["bundles"][0]["model_id"] == "grok-4.1-thinking"
    assert lineage["bundles"][0]["role_policy_boundary_mode"] == "intraday_working"
    assert lineage["bundles"][0]["adopted_output_field_count"] == 5
    assert lineage["bundles"][0]["discarded_output_fields"] == []
    assert lineage["bundles"][1]["missing"] is True


def test_report_llm_lineage_summary_estimates_cost_when_pricing_is_configured(tmp_path) -> None:
    pricing_path = tmp_path / "models.yaml"
    pricing_path.write_text(
        "fsj_budget_policy:\n  require_pricing_for_all_usage: true\n  max_total_tokens_per_artifact: 12000\n  max_total_tokens_fleet: 40000\n  max_fallback_rate: 0.50\n  max_degraded_rate: 0.50\nmodels:\n  grok41_thinking:\n    pricing:\n      usd_per_1m_total_tokens: 2.0\n",
        encoding="utf-8",
    )
    store_module._load_llm_model_pricing.cache_clear()
    store_module._load_llm_budget_policy.cache_clear()
    original_path = store_module.BUSINESS_REPO_MODELS_CONFIG
    store_module.BUSINESS_REPO_MODELS_CONFIG = pricing_path
    try:
        summary = _ProjectionOnlyStore().report_llm_lineage_summary(
            {
                "summary": {
                    "bundle_count": 1,
                    "applied_count": 1,
                    "primary_applied_count": 1,
                    "models": ["grok41_thinking"],
                    "prompt_versions": ["fsj_mid_main_v1"],
                    "adopted_output_field_count": 5,
                    "discarded_output_field_count": 0,
                    "field_replay_ready_count": 1,
                    "usage_bundle_count": 1,
                    "costed_bundle_count": 1,
                    "uncosted_bundle_count": 0,
                    "token_totals": {"total_tokens": 5000},
                    "estimated_cost_usd": store_module._estimate_usage_cost_usd(model_alias="grok41_thinking", usage={"total_tokens": 5000}),
                }
            }
        )
    finally:
        store_module.BUSINESS_REPO_MODELS_CONFIG = original_path
        store_module._load_llm_model_pricing.cache_clear()
        store_module._load_llm_budget_policy.cache_clear()

    assert summary["estimated_cost_usd"] == 0.01
    assert summary["summary_line"] == "applied [applied=1/1 | primary=1 | models=grok41_thinking | prompts=fsj_mid_main_v1 | tokens=5000 | adopted_fields=5 | replay_ready=1 | usage=1 | cost_usd=0.010000]"
    assert summary["budget_governance_status"] == "within_budget"
    assert summary["budget_governance_required_action"] is None
    assert summary["budget_governance_summary_line"] == "within_budget | scope=per_artifact | within_configured_budget_policy | policy=tokens<=12000,fallback_rate<=0.500,degraded_rate<=0.500,pricing=required"


def test_report_llm_lineage_summary_projects_field_audit_counts() -> None:
    summary = _ProjectionOnlyStore().report_llm_lineage_summary(
        {
            "summary": {
                "bundle_count": 2,
                "applied_count": 1,
                "degraded_count": 1,
                "fallback_applied_count": 0,
                "primary_applied_count": 1,
                "models": ["grok41_thinking"],
                "prompt_versions": ["fsj_early_main_v1"],
                "field_replay_ready_count": 1,
                "adopted_output_field_count": 6,
                "discarded_output_field_count": 6,
                "discard_reasons": ["timeout"],
            }
        }
    )

    assert summary["prompt_versions"] == ["fsj_early_main_v1"]
    assert summary["field_replay_ready_count"] == 1
    assert summary["adopted_output_field_count"] == 6
    assert summary["discarded_output_field_count"] == 6
    assert summary["discard_reasons"] == ["timeout"]
    assert summary["summary_line"] == "degraded [applied=1/2 | primary=1 | degraded=1 | models=grok41_thinking | prompts=fsj_early_main_v1 | adopted_fields=6 | discarded_fields=6 | replay_ready=1 | discard_reasons=timeout]"


def test_report_llm_lineage_summary_flags_pricing_incomplete_when_policy_requires_full_pricing(tmp_path) -> None:
    pricing_path = tmp_path / "models.yaml"
    pricing_path.write_text(
        "fsj_budget_policy:\n  require_pricing_for_all_usage: true\n  max_total_tokens_per_artifact: 12000\n  max_total_tokens_fleet: 40000\n  max_fallback_rate: 0.50\n  max_degraded_rate: 0.50\nmodels:\n  grok41_thinking:\n    pricing:\n      usd_per_1m_total_tokens: 2.0\n",
        encoding="utf-8",
    )
    store_module._load_llm_model_pricing.cache_clear()
    store_module._load_llm_budget_policy.cache_clear()
    original_path = store_module.BUSINESS_REPO_MODELS_CONFIG
    store_module.BUSINESS_REPO_MODELS_CONFIG = pricing_path
    try:
        summary = _ProjectionOnlyStore().report_llm_lineage_summary(
            {
                "summary": {
                    "bundle_count": 2,
                    "applied_count": 2,
                    "primary_applied_count": 1,
                    "fallback_applied_count": 1,
                    "models": ["gemini31_pro_jmr", "grok41_thinking"],
                    "usage_bundle_count": 2,
                    "costed_bundle_count": 1,
                    "uncosted_bundle_count": 1,
                    "degraded_count": 0,
                    "token_totals": {"total_tokens": 9000},
                    "estimated_cost_usd": 0.01,
                }
            }
        )
    finally:
        store_module.BUSINESS_REPO_MODELS_CONFIG = original_path
        store_module._load_llm_model_pricing.cache_clear()
        store_module._load_llm_budget_policy.cache_clear()

    assert summary["budget_governance_status"] == "pricing_incomplete"
    assert summary["budget_governance_required_action"] == "price_all_active_models_before_budget_enforcement"
    assert summary["budget_governance_summary_line"] == "pricing_incomplete | scope=per_artifact | unpriced_usage=1 | policy=tokens<=12000,fallback_rate<=0.500,degraded_rate<=0.500,pricing=required | action=price_all_active_models_before_budget_enforcement"


def test_report_operator_review_surface_prefers_exported_workflow_linkage_llm_lineage() -> None:
    store = _ProjectionOnlyStore()
    summary = store.report_operator_review_surface_from_surface(
        {
            "artifact": {"artifact_id": "artifact-exported"},
            "delivery_package": {
                "package_state": "ready",
                "ready_for_delivery": True,
                "quality_gate": {"score": 98, "blocker_count": 0, "warning_count": 0},
                "workflow": {"recommended_action": "send", "workflow_state": "ready_to_send"},
            },
            "workflow_linkage": {
                "llm_lineage": {
                    "artifact_id": "artifact-exported",
                    "bundle_ids": ["bundle-exported"],
                    "summary": {"bundle_count": 1, "applied_count": 1, "degraded_count": 0, "fallback_applied_count": 0, "primary_applied_count": 1},
                    "bundles": [{"bundle_id": "bundle-exported", "slot": "late", "outcome": "primary_applied", "applied": True}],
                }
            },
        }
    )

    assert summary["llm_lineage"]["artifact_id"] == "artifact-exported"
    assert summary["llm_lineage"]["summary"]["bundle_count"] == 1
    assert summary["llm_role_policy"]["slot_boundary_modes"] == {}
    assert summary["llm_lineage_summary"]["status"] == "applied"
    assert summary["llm_lineage_summary"]["summary_line"] == "applied [applied=1/1 | primary=1]"
    assert summary["review_summary"]["llm_applied_count"] == 1
    assert summary["review_summary"]["llm_lineage_status"] == "applied"
    assert summary["review_summary"]["llm_lineage_summary"] == "applied [applied=1/1 | primary=1]"


def test_report_operator_review_query_helpers_project_from_delivery_surfaces() -> None:
    class _Store(FSJStore):
        def __init__(self) -> None:
            pass

        def get_active_report_delivery_surface(self, **_: object) -> dict | None:
            return {
                "artifact": {"artifact_id": "artifact-active", "status": "active"},
                "delivery_package": {
                    "package_state": "ready",
                    "ready_for_delivery": True,
                    "quality_gate": {"score": 99, "blocker_count": 0, "warning_count": 0},
                    "workflow": {"recommended_action": "send", "workflow_state": "ready_to_send"},
                },
                "workflow_linkage": {},
            }

        def get_latest_active_report_delivery_surface(self, **_: object) -> dict | None:
            return self.get_active_report_delivery_surface()

        def list_report_delivery_surfaces(self, **_: object) -> list[dict]:
            return [self.get_active_report_delivery_surface()]

    store = _Store()

    active = store.get_active_report_operator_review_surface(
        business_date="2099-04-22",
        agent_domain="main",
        artifact_family="main_final_report",
    )
    latest = store.get_latest_active_report_operator_review_surface(
        agent_domain="main",
        artifact_family="main_final_report",
    )
    history = store.list_report_operator_review_surfaces(
        business_date="2099-04-22",
        agent_domain="main",
        artifact_family="main_final_report",
    )

    assert active is not None
    assert active["artifact"]["artifact_id"] == "artifact-active"
    assert active["review_summary"]["go_no_go_decision"] == "GO"
    assert latest is not None
    assert latest["artifact"]["artifact_id"] == "artifact-active"
    assert history[0]["artifact"]["artifact_id"] == "artifact-active"
