from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.store import FSJStore
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError as LiveIsolationError


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_operator_board.py"
_spec = importlib.util.spec_from_file_location("fsj_operator_board_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
_build_board_payload = _module.build_board_payload
_print_text = _module._print_text


LIVE_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp"


def _clear_caches() -> None:
    make_engine.cache_clear()
    get_settings.cache_clear()


class _DummyStore:
    def __init__(self) -> None:
        self.latest_calls: list[dict] = []

    def get_latest_active_report_delivery_surface(self, **kwargs: object) -> dict | None:
        self.latest_calls.append(dict(kwargs))
        if kwargs["agent_domain"] == "main":
            return {
                "artifact": {"artifact_id": "main-artifact", "report_run_id": "main-run", "business_date": "2099-04-22", "status": "active", "updated_at": "2099-04-22T10:00:00+00:00"},
                "delivery_package": {"slot_evaluation": {"strongest_slot": "late"}},
            }
        return {
            "artifact": {"artifact_id": f"{kwargs['agent_domain']}-artifact", "report_run_id": f"{kwargs['agent_domain']}-run", "business_date": "2099-04-22", "status": "active", "updated_at": "2099-04-22T10:00:00+00:00"},
            "delivery_package": {"slot": "early"},
        }

    def get_active_report_delivery_surface(self, **kwargs: object) -> dict | None:
        domain = kwargs["agent_domain"]
        if domain == "main":
            return {
                "artifact": {"artifact_id": "main-artifact", "report_run_id": "main-run", "business_date": kwargs["business_date"], "status": "active"},
                "delivery_package": {"package_state": "ready", "ready_for_delivery": True, "quality_gate": {"score": 100, "blocker_count": 0, "warning_count": 0, "qa_axes": {"structural": {"ready": True, "score": 100, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "lineage": {"ready": True, "score": 100, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "policy": {"ready": True, "score": 100, "blocker_count": 0, "warning_count": 0, "issue_codes": []}}}, "workflow": {"recommended_action": "send", "dispatch_recommended_action": "send", "workflow_state": "ready_to_send"}, "artifacts": {}},
                "workflow_linkage": {},
            }
        quality_gate = {"score": 95, "blocker_count": 0, "warning_count": 0, "qa_axes": {"structural": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "lineage": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "policy": {"ready": domain != "commodities", "score": 87 if domain == "commodities" else 95, "blocker_count": 0, "warning_count": 1 if domain == "commodities" else 0, "issue_codes": ["support_source_health_degraded"] if domain == "commodities" else []}}}
        return {
            "artifact": {"artifact_id": f"{domain}-artifact", "report_run_id": f"{domain}-run", "business_date": kwargs["business_date"], "status": "active"},
            "delivery_package": {"package_state": "ready", "ready_for_delivery": True, "quality_gate": quality_gate, "workflow": {"recommended_action": "send", "dispatch_recommended_action": "send", "workflow_state": "ready_to_send"}, "artifacts": {}, "slot": "early"},
            "workflow_linkage": {},
        }

    def list_report_delivery_surfaces(self, **kwargs: object) -> list[dict]:
        return [{"artifact": {"artifact_id": "main-artifact", "report_run_id": "main-run", "business_date": kwargs["business_date"], "status": "active"}, "delivery_package": {"package_state": "ready", "ready_for_delivery": True, "quality_gate": {"score": 100, "blocker_count": 0, "warning_count": 0}, "workflow": {"recommended_action": "send", "dispatch_recommended_action": "send", "workflow_state": "ready_to_send"}, "artifacts": {}, "slot_evaluation": {"strongest_slot": "late"}}, "workflow_linkage": {}}]

    def report_workflow_handoff_from_surface(self, surface: dict) -> dict:
        artifact = surface["artifact"]
        delivery_package = surface.get("delivery_package") or {}
        workflow = dict(delivery_package.get("workflow") or {})
        quality_gate = dict(delivery_package.get("quality_gate") or {})
        lifecycle_state = "review_ready" if workflow.get("recommended_action") == "send_review" else "send_ready"
        lifecycle_reason = "manual_review_required" if lifecycle_state == "review_ready" else "ready_for_delivery_send"
        return {
            "artifact": {"artifact_id": artifact.get("artifact_id"), "report_run_id": artifact.get("report_run_id"), "business_date": artifact.get("business_date"), "status": artifact.get("status")},
            "selected_handoff": {"selected_artifact_id": artifact.get("artifact_id"), "selected_is_current": True},
            "state": {"recommended_action": workflow.get("recommended_action"), "dispatch_recommended_action": workflow.get("dispatch_recommended_action"), "workflow_state": workflow.get("workflow_state"), "package_state": delivery_package.get("package_state"), "qa_score": quality_gate.get("score"), "blocker_count": quality_gate.get("blocker_count"), "warning_count": quality_gate.get("warning_count"), "qa_axes": dict(quality_gate.get("qa_axes") or {})},
            "canonical_lifecycle": {"state": lifecycle_state, "reason": lifecycle_reason},
            "manifest_pointers": {},
            "version_pointers": {},
        }


    def list_report_business_dates(self, **kwargs: object) -> list[str]:
        return [str(kwargs.get("business_date") or "2099-04-22")]

    def get_active_report_operator_review_surface(self, **kwargs: object) -> dict | None:
        return self.report_operator_review_surface_from_surface(self.get_active_report_delivery_surface(**kwargs))
    def report_package_surface_from_surface(self, surface: dict) -> dict:
        handoff = self.report_workflow_handoff_from_surface(surface)
        delivery_package = surface.get("delivery_package") or {}
        return {
            "artifact": handoff["artifact"],
            "selected_handoff": handoff["selected_handoff"],
            "state": handoff["state"],
            "package_paths": {"delivery_package_dir": delivery_package.get("delivery_package_dir")},
            "package_versions": {},
            "package_state": {"package_state": delivery_package.get("package_state")},
            "package_artifacts": dict(delivery_package.get("artifacts") or {}),
            "workflow_handoff": handoff,
        }




class _BoardStore(_DummyStore):
    def report_artifact_lineage_from_surface(self, surface: dict) -> dict:
        artifact = dict(surface.get("artifact") or {})
        artifact_id = artifact.get("artifact_id")
        return {
            "artifact": artifact,
            "bundle_lineage_summary": {
                "bundle_count": 2 if artifact_id == "main-artifact" else 1,
                "missing_bundle_count": 1 if artifact_id == "commodities-artifact" else 0,
                "slots": ["late"] if artifact_id == "main-artifact" else ["early"],
                "section_keys": [artifact_id or "unknown"],
            },
            "what_user_received": {
                "dispatch_state": "dispatch_failed" if artifact_id == "commodities-artifact" else "dispatch_succeeded",
                "provider_message_id": None if artifact_id == "commodities-artifact" else f"msg-{artifact_id}",
            },
        }

    def report_operator_review_surface_from_surface(self, surface: dict) -> dict:
        package_surface = self.report_package_surface_from_surface(surface)
        handoff = self.report_workflow_handoff_from_surface(surface)
        artifact_id = handoff["artifact"].get("artifact_id")
        lineage_status = "degraded" if artifact_id == "commodities-artifact" else "applied"
        lineage_summary = {
            "status": lineage_status,
            "summary_line": f"{lineage_status} [applied=1/1]",
        }
        slot_boundary_mode = "same_day_close" if artifact_id == "main-artifact" else "candidate_only"
        generated_at = "2099-04-22T10:00:00+00:00"
        strongest_slot = "late" if artifact_id == "main-artifact" else "early"
        dispatch_receipt = {
            "dispatch_state": "dispatch_failed" if artifact_id == "commodities-artifact" else "dispatch_succeeded",
            "attempted_at": generated_at,
            "failed_at": generated_at if artifact_id == "commodities-artifact" else None,
            "succeeded_at": None if artifact_id == "commodities-artifact" else generated_at,
            "channel": "telegram_document",
            "error": None if artifact_id != "commodities-artifact" else "bundle missing",
        }
        canonical_state = "review_ready" if artifact_id == "commodities-artifact" else "send_ready"
        canonical_reason = "manual_review_required" if artifact_id == "commodities-artifact" else "ready_for_delivery_send"
        canonical_state_vocabulary = {
            "canonical_state": canonical_state,
            "canonical_reason": canonical_reason,
            "status_semantic": "review" if artifact_id == "commodities-artifact" else "ready",
            "operator_bucket": "operator_gate" if artifact_id == "commodities-artifact" else "dispatch_gate",
            "terminal": False,
            "summary_line": f"canonical={canonical_state} | status={'review' if artifact_id == 'commodities-artifact' else 'ready'} | bucket={'operator_gate' if artifact_id == 'commodities-artifact' else 'dispatch_gate'}",
        }
        return {
            "artifact": handoff["artifact"],
            "selected_handoff": {**handoff["selected_handoff"], "selected_generated_at_utc": generated_at},
            "state": handoff["state"],
            "package_paths": {**package_surface["package_paths"], "generated_at_utc": generated_at},
            "package_versions": {**package_surface["package_versions"], "delivery_manifest_version": "v1"},
            "package_state": {"package_state": handoff["state"].get("package_state"), "slot_evaluation": {"strongest_slot": strongest_slot}, "generated_at_utc": generated_at, "lineage": {"bundle_ids": [f"bundle-{artifact_id}"]}},
            "workflow_handoff": handoff,
            "dispatch_receipt": dispatch_receipt,
            "dispatch_state": dispatch_receipt["dispatch_state"],
            "llm_lineage_summary": lineage_summary,
            "llm_role_policy": {
                "policy_versions": ["fsj_llm_role_policy_v1"],
                "boundary_modes": [slot_boundary_mode],
                "deterministic_owner_fields": ["judgment.action"],
                "forbidden_decisions": ["declare_close_final_confirmation"],
                "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                "slot_boundary_modes": {"late": slot_boundary_mode},
            },
            "candidate_comparison": {},
            "operator_go_no_go": {"decision": "GO", "rationale": "quality gate and artifact integrity both pass" if artifact_id != "commodities-artifact" else "manual review is required before sending"},
            "review_manifest": {"next_step": "review_current_package_then_send_if_accepted" if artifact_id == "commodities-artifact" else "send_selected_package_to_primary_channel"},
            "send_manifest": {"next_step": "review_current_package_then_send_if_accepted" if artifact_id == "commodities-artifact" else "send_selected_package_to_primary_channel"},
            "governance": {
                "decision": "REVIEW" if artifact_id == "commodities-artifact" else "GO",
                "rationale": "manual review is required before sending" if artifact_id == "commodities-artifact" else "quality gate and artifact integrity both pass",
                "next_step": "review_current_package_then_send_if_accepted" if artifact_id == "commodities-artifact" else "send_selected_package_to_primary_channel",
                "action_required": artifact_id == "commodities-artifact",
                "blocking_reasons": ["bundle_missing"] if artifact_id == "commodities-artifact" else [],
            },
            "promotion_authority": {
                "scope": "review_ready_to_send_ready",
                "status": "review_required" if artifact_id == "commodities-artifact" else "approved_to_send",
                "approved": artifact_id != "commodities-artifact",
                "authority_kind": "system_policy_projection",
                "decision": "REVIEW" if artifact_id == "commodities-artifact" else "GO",
                "approver_ref": "operator_go_no_go",
                "artifact_id": artifact_id,
                "selected_artifact_id": artifact_id,
                "selected_is_current": True,
                "required_action": "review_current_package_then_send_if_accepted" if artifact_id == "commodities-artifact" else "send_selected_package_to_primary_channel",
                "rationale": "manual review is required before sending" if artifact_id == "commodities-artifact" else "quality gate and artifact integrity both pass",
                "source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff",
                "summary_line": "review_required | decision=REVIEW | selected_is_current=True | required_action=review_current_package_then_send_if_accepted | rationale=manual review is required before sending" if artifact_id == "commodities-artifact" else "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass",
            },
            "canonical_state_vocabulary": canonical_state_vocabulary,
            "board_state_source": {
                "canonical_state": canonical_state,
                "canonical_reason": canonical_reason,
                "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff",
                "blocking_reason_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.send_blockers" if artifact_id == "commodities-artifact" else None,
                "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step",
                "version_source_of_truth": "ifa_fsj_report_artifacts.artifact_id + ifa_fsj_report_artifacts.report_run_id + ifa_fsj_report_artifacts.supersedes_artifact_id + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff",
                "bundle_source_of_truth": "ifa_fsj_bundles(bundle_ids from ifa_fsj_report_artifacts.metadata_json.bundle_ids)",
                "dispatch_source_of_truth": None,
                "selected_artifact_id": artifact_id,
                "selected_is_current": True,
                "summary_line": "state=review_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step | blockers via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.send_blockers" if artifact_id == "commodities-artifact" else "state=send_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step",
            },
            "review_summary": {"go_no_go_decision": "GO", "llm_lineage_status": lineage_status, "llm_lineage_summary": lineage_summary["summary_line"], "canonical_lifecycle_state": canonical_state, "operator_decision_rationale": "manual review is required before sending" if artifact_id == "commodities-artifact" else "quality gate and artifact integrity both pass", "operator_next_step": "review_current_package_then_send_if_accepted" if artifact_id == "commodities-artifact" else "send_selected_package_to_primary_channel", "operator_action_required": artifact_id == "commodities-artifact", "promotion_authority_status": "review_required" if artifact_id == "commodities-artifact" else "approved_to_send", "promotion_authority_approved": artifact_id != "commodities-artifact", "promotion_authority_required_action": "review_current_package_then_send_if_accepted" if artifact_id == "commodities-artifact" else "send_selected_package_to_primary_channel", "promotion_authority_rationale": "manual review is required before sending" if artifact_id == "commodities-artifact" else "quality gate and artifact integrity both pass", "promotion_authority_summary": "review_required | decision=REVIEW | selected_is_current=True | required_action=review_current_package_then_send_if_accepted | rationale=manual review is required before sending" if artifact_id == "commodities-artifact" else "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass", "promotion_authority_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "source_health_status": "degraded" if artifact_id == "commodities-artifact" else "healthy", "source_health_blocking_slot_count": 0, "source_health_degraded_slot_count": 1 if artifact_id == "commodities-artifact" else 0, "source_health_degrade_reason": "missing_background_support" if artifact_id == "commodities-artifact" else None, "source_health": {"overall_status": "degraded" if artifact_id == "commodities-artifact" else "healthy", "blocking_slot_count": 0, "degraded_slot_count": 1 if artifact_id == "commodities-artifact" else 0, "degrade_reason": "missing_background_support" if artifact_id == "commodities-artifact" else None}},
        }

    def build_operator_board_surface(self, *, business_date: str | None = None, history_limit: int = 5) -> dict:
        business_date = business_date or "2099-04-22"
        resolution_mode = "latest_active_lookup" if business_date == "2099-04-22" else "explicit_business_date"
        main = self.get_active_report_delivery_surface(business_date=business_date, agent_domain="main", artifact_family="main_final_report")
        support = {
            domain: self.get_active_report_delivery_surface(business_date=business_date, agent_domain=domain, artifact_family="support_domain_report")
            for domain in ("ai_tech", "commodities", "macro")
        }
        history = self.list_report_delivery_surfaces(business_date=business_date, agent_domain="main", artifact_family="main_final_report", statuses=["active", "superseded"], limit=history_limit)
        main_review = self.report_operator_review_surface_from_surface(main) if main else None
        support_reviews = {domain: self.report_operator_review_surface_from_surface(surface) if surface else None for domain, surface in support.items()}
        history_reviews = [self.report_operator_review_surface_from_surface(surface) for surface in history]
        return {
            "business_date": business_date,
            "resolution": {"mode": resolution_mode, "business_date": business_date},
            "main": main_review,
            "main_package": self.report_package_surface_from_surface(main) if main else None,
            "main_review": main_review,
            "main_workflow": self.report_workflow_handoff_from_surface(main) if main else None,
            "support": support_reviews,
            "support_packages": {domain: self.report_package_surface_from_surface(surface) if surface else None for domain, surface in support.items()},
            "support_workflow": {domain: self.report_workflow_handoff_from_surface(surface) if surface else None for domain, surface in support.items()},
            "history": history_reviews,
            "history_packages": [self.report_package_surface_from_surface(surface) for surface in history],
            "history_reviews": history_reviews,
            "history_workflow": [self.report_workflow_handoff_from_surface(surface) for surface in history],
            "db_candidates": [{"artifact_id": "main-artifact", "recommended_action": "send", "selection_reason": "best_ready_candidate strongest_slot=late qa_score=100"}],
            "db_candidate_fleet_summary": {
                "subject": "main",
                "verdict": "aligned",
                "reason_code": "current_selected_match_best_candidate",
                "summary_line": "Current MAIN artifact main-artifact matches the best DB candidate.",
                "current_artifact_id": "main-artifact",
                "selected_artifact_id": "main-artifact",
                "best_candidate_artifact_id": "main-artifact",
                "selected_matches_best": True,
                "current_matches_best": True,
            },
            "db_candidate_history_summary": [
                {
                    "subject": "history:1",
                    "history_index": 1,
                    "artifact_status": "active",
                    "verdict": "aligned",
                    "reason_code": "current_selected_match_best_candidate",
                    "summary_line": "Current MAIN artifact main-artifact matches the best DB candidate.",
                    "current_artifact_id": "main-artifact",
                    "selected_artifact_id": "main-artifact",
                    "best_candidate_artifact_id": "main-artifact",
                }
            ],
            "artifact_lineage_summary": {
            "main": {"bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 0}, "what_user_received": {"dispatch_state": "dispatch_succeeded", "provider_message_id": "msg-main-artifact"}},
            "support": {
                "ai_tech": {"bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 0}, "what_user_received": {"dispatch_state": "dispatch_succeeded", "provider_message_id": "msg-ai-tech-artifact"}},
                "commodities": {"bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 1}, "what_user_received": {"dispatch_state": "dispatch_failed", "provider_message_id": None}},
                "macro": None,
            },
            "aggregate": {"bundle_count": 4, "missing_bundle_count": 1, "dispatch_succeeded_count": 2, "dispatch_failed_count": 1},
        },
        "llm_lineage_summary": {
                "main": main_review["llm_lineage_summary"] if main_review else None,
                "support": {domain: (review["llm_lineage_summary"] if review else None) for domain, review in support_reviews.items()},
                "history": [review["llm_lineage_summary"] for review in history_reviews],
                "aggregate": {
                    "overall_status": "degraded",
                    "reported_subject_count": 5,
                    "attention_subjects": ["support:commodities"],
                    "model_usage_breakdown": {
                        "gemini31_pro_jmr": {"bundle_count": 1, "applied_count": 1, "fallback_applied_count": 1, "total_tokens": 355, "estimated_cost_usd": None},
                        "grok41_thinking": {"bundle_count": 4, "applied_count": 4, "fallback_applied_count": 0, "total_tokens": 628, "estimated_cost_usd": 0.01256},
                    },
                    "slot_usage_breakdown": {
                        "early": {"bundle_count": 3, "applied_count": 3, "fallback_applied_count": 1, "total_tokens": 642},
                        "late": {"bundle_count": 2, "applied_count": 2, "fallback_applied_count": 0, "total_tokens": 341},
                    },
                },
            },
            "llm_role_policy_review": {
                "main": main_review["llm_role_policy"] if main_review else None,
                "support": {domain: (review["llm_role_policy"] if review else None) for domain, review in support_reviews.items()},
                "history": [review["llm_role_policy"] for review in history_reviews],
                "aggregate": {
                    "reported_subject_count": 5,
                    "policy_versions": ["fsj_llm_role_policy_v1"],
                    "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                    "attention_subjects": ["main", "support:ai_tech", "support:commodities", "support:macro", "history:1"],
                    "slot_boundary_modes_by_subject": {
                        "main": {"late": "same_day_close"},
                        "support:commodities": {"late": "candidate_only"},
                    },
                },
            },
            "board_readiness_summary": {
                "main": {"subject": "main", "posture": "ready_to_send", "send_ready": True, "review_required": False, "blocked": False, "lineage_attention": False, "source_health_attention": False, "needs_attention": False, "source_health_status": "healthy", "source_health_blocking_slot_count": 0, "source_health_degraded_slot_count": 0, "canonical_lifecycle_state": "send_ready", "canonical_lifecycle_reason": "ready_for_delivery_send"},
                "support": {
                    "ai_tech": {"subject": "support:ai_tech", "posture": "ready_to_send", "send_ready": True, "review_required": False, "blocked": False, "lineage_attention": False, "source_health_attention": False, "needs_attention": False, "source_health_status": "healthy", "source_health_blocking_slot_count": 0, "source_health_degraded_slot_count": 0, "canonical_lifecycle_state": "send_ready", "canonical_lifecycle_reason": "ready_for_delivery_send"},
                    "commodities": {"subject": "support:commodities", "posture": "review_required", "send_ready": False, "review_required": True, "blocked": False, "lineage_attention": True, "source_health_attention": True, "needs_attention": True, "source_health_status": "degraded", "source_health_blocking_slot_count": 0, "source_health_degraded_slot_count": 1, "source_health_degrade_reason": "missing_background_support", "canonical_lifecycle_state": "review_ready", "canonical_lifecycle_reason": "manual_review_required"},
                    "macro": {"subject": "support:macro", "posture": "ready_to_send", "send_ready": True, "review_required": False, "blocked": False, "lineage_attention": False, "source_health_attention": False, "needs_attention": False, "source_health_status": "healthy", "source_health_blocking_slot_count": 0, "source_health_degraded_slot_count": 0, "canonical_lifecycle_state": "send_ready", "canonical_lifecycle_reason": "ready_for_delivery_send"},
                },
                "aggregate": {
                    "overall_posture": "review_required",
                    "ready_subjects": ["main", "support:ai_tech", "support:macro"],
                    "review_required_subjects": ["support:commodities"],
                    "blocked_subjects": [],
                    "attention_subjects": ["support:commodities"],
                    "governance_action_required_subjects": ["support:commodities"],
                    "source_health_status_counts": {"healthy": 3, "degraded": 1},
                    "source_health_attention_subjects": ["support:commodities"],
                    "source_health_blocked_subjects": [],
                    "source_health_degraded_subjects": ["support:commodities"],
                    "canonical_lifecycle_state_counts": {"review_ready": 1, "send_ready": 3},
                    "canonical_lifecycle_subjects": {"review_ready": ["support:commodities"], "send_ready": ["main", "support:ai_tech", "support:macro"]},
                },
            },
            "board_rows": {
                "main": {"subject": "main", "artifact_id": "main-artifact", "status_semantic": "ready", "canonical_state_vocabulary": {"canonical_state": "send_ready", "canonical_reason": "ready_for_delivery_send", "status_semantic": "ready", "operator_bucket": "dispatch_gate", "terminal": False, "summary_line": "canonical=send_ready | status=ready | bucket=dispatch_gate"}, "operator_bucket": "dispatch_gate", "canonical_lifecycle_state": "send_ready", "canonical_lifecycle_reason": "ready_for_delivery_send", "posture": "ready_to_send", "recommended_action": "send", "next_action": "send_selected_package_to_primary_channel", "blocking_reason": None, "selected_artifact_id": "main-artifact", "selected_is_current": True, "strongest_slot": "late", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_succeeded", "bundle_count": 2, "missing_bundle_count": 0, "lineage_sla_summary": "selected=main-artifact | slot=late | bundles=2 | missing=0 | dispatch=dispatch_succeeded | generated=2099-04-22T10:00:00+00:00", "failure_taxonomy": {"class": "none", "reason": None, "summary_line": "none | no failure taxonomy attention currently projected", "operator_visible": False}, "failure_taxonomy_class": "none", "failure_taxonomy_reason": None, "failure_taxonomy_summary": "none | no failure taxonomy attention currently projected", "governance_action_required": False, "needs_attention": False, "summary_line": "main | status=ready | canonical=send_ready | action=send_selected_package_to_primary_channel"},
                "support": {
                    "ai_tech": {"subject": "support:ai_tech", "artifact_id": "ai_tech-artifact", "status_semantic": "ready", "canonical_lifecycle_state": "send_ready", "canonical_lifecycle_reason": "ready_for_delivery_send", "posture": "ready_to_send", "recommended_action": "send", "next_action": "send_selected_package_to_primary_channel", "blocking_reason": None, "selected_artifact_id": "ai_tech-artifact", "selected_is_current": True, "strongest_slot": "early", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_succeeded", "bundle_count": 1, "missing_bundle_count": 0, "lineage_sla_summary": "selected=ai_tech-artifact | slot=early | bundles=1 | missing=0 | dispatch=dispatch_succeeded | generated=2099-04-22T10:00:00+00:00", "governance_action_required": False, "needs_attention": False, "summary_line": "support:ai_tech | status=ready | canonical=send_ready | action=send_selected_package_to_primary_channel"},
                    "commodities": {"subject": "support:commodities", "artifact_id": "commodities-artifact", "status_semantic": "review", "canonical_state_vocabulary": {"canonical_state": "review_ready", "canonical_reason": "manual_review_required", "status_semantic": "review", "operator_bucket": "operator_gate", "terminal": False, "summary_line": "canonical=review_ready | status=review | bucket=operator_gate"}, "operator_bucket": "operator_gate", "canonical_lifecycle_state": "review_ready", "canonical_lifecycle_reason": "manual_review_required", "posture": "review_required", "recommended_action": "send_review", "next_action": "review_current_package_then_send_if_accepted", "blocking_reason": "bundle_missing", "selected_artifact_id": "commodities-artifact", "selected_is_current": True, "strongest_slot": "early", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_failed", "bundle_count": 1, "missing_bundle_count": 1, "lineage_sla_summary": "selected=commodities-artifact | slot=early | bundles=1 | missing=1 | dispatch=dispatch_failed | generated=2099-04-22T10:00:00+00:00", "failure_taxonomy": {"class": "hold_review", "reason": "bundle_missing", "summary_line": "hold_review | operator intervention or review remains required", "operator_visible": True}, "failure_taxonomy_class": "hold_review", "failure_taxonomy_reason": "bundle_missing", "failure_taxonomy_summary": "hold_review | operator intervention or review remains required", "governance_action_required": True, "needs_attention": True, "summary_line": "support:commodities | status=review | canonical=review_ready | action=review_current_package_then_send_if_accepted | failure_taxonomy=hold_review | blocker=bundle_missing"},
                    "macro": {"subject": "support:macro", "artifact_id": "macro-artifact", "status_semantic": "ready", "canonical_lifecycle_state": "send_ready", "canonical_lifecycle_reason": "ready_for_delivery_send", "posture": "ready_to_send", "recommended_action": "send", "next_action": "send_selected_package_to_primary_channel", "blocking_reason": None, "selected_artifact_id": "macro-artifact", "selected_is_current": True, "strongest_slot": "early", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_succeeded", "bundle_count": 1, "missing_bundle_count": 0, "lineage_sla_summary": "selected=macro-artifact | slot=early | bundles=1 | missing=0 | dispatch=dispatch_succeeded | generated=2099-04-22T10:00:00+00:00", "governance_action_required": False, "needs_attention": False, "summary_line": "support:macro | status=ready | canonical=send_ready | action=send_selected_package_to_primary_channel"},
                },
                "history": [
                    {"subject": "history:1", "history_index": 1, "artifact_id": "main-artifact", "status_semantic": "ready", "canonical_lifecycle_state": "send_ready", "canonical_lifecycle_reason": "ready_for_delivery_send", "posture": "ready_to_send", "recommended_action": "send", "next_action": "send_selected_package_to_primary_channel", "blocking_reason": None, "selected_artifact_id": "main-artifact", "selected_is_current": True, "strongest_slot": "late", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_succeeded", "bundle_count": 2, "missing_bundle_count": 0, "lineage_sla_summary": "selected=main-artifact | slot=late | bundles=2 | missing=0 | dispatch=dispatch_succeeded | generated=2099-04-22T10:00:00+00:00", "governance_action_required": False, "needs_attention": False, "summary_line": "history:1 | status=ready | canonical=send_ready | action=send_selected_package_to_primary_channel"}
                ],
                "aggregate": {"reported_subject_count": 4, "status_semantic_counts": {"ready": 3, "review": 1}, "dispatch_state_counts": {"dispatch_succeeded": 3, "dispatch_failed": 1}, "strongest_slot_counts": {"early": 3, "late": 1}, "failure_taxonomy_counts": {"hold_review": 1}, "failure_taxonomy_subjects": {"hold_review": ["support:commodities"]}, "subjects_with_blocking_reason": ["support:commodities"], "subjects_with_next_action": ["main", "support:ai_tech", "support:commodities", "support:macro"], "selected_mismatch_subjects": [], "subjects_with_missing_bundles": ["support:commodities"]},
            },
            "board_state_source_summary": {
                "main": {"subject": "main", "canonical_state": "send_ready", "canonical_reason": "ready_for_delivery_send", "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "blocking_reason_source_of_truth": None, "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step", "summary_line": "state=send_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step"},
                "support": {
                    "ai_tech": {"subject": "support:ai_tech", "canonical_state": "send_ready", "canonical_reason": "ready_for_delivery_send", "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "blocking_reason_source_of_truth": None, "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step", "summary_line": "state=send_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step"},
                    "commodities": {"subject": "support:commodities", "canonical_state": "review_ready", "canonical_reason": "manual_review_required", "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "blocking_reason_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.send_blockers", "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step", "summary_line": "state=review_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step | blockers via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.send_blockers"},
                    "macro": {"subject": "support:macro", "canonical_state": "send_ready", "canonical_reason": "ready_for_delivery_send", "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "blocking_reason_source_of_truth": None, "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step", "summary_line": "state=send_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step"},
                },
                "aggregate": {"reported_subject_count": 4, "state_source_counts": {"ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff": 4}, "subjects_with_next_action_source": ["main", "support:ai_tech", "support:commodities", "support:macro"], "subjects_with_blocking_reason_source": ["support:commodities"]},
            },
            "qa_axes_summary": {
                "main": {"subject": "main", "qa_axes": {"structural": {"ready": True, "score": 100, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "lineage": {"ready": True, "score": 100, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "policy": {"ready": True, "score": 100, "blocker_count": 0, "warning_count": 0, "issue_codes": []}}, "axes_with_attention": [], "not_ready_axes": []},
                "support": {
                    "ai_tech": {"subject": "support:ai_tech", "qa_axes": {"structural": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "lineage": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "policy": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}}, "axes_with_attention": [], "not_ready_axes": []},
                    "commodities": {"subject": "support:commodities", "qa_axes": {"structural": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "lineage": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "policy": {"ready": False, "score": 87, "blocker_count": 0, "warning_count": 1, "issue_codes": ["support_source_health_degraded"]}}, "axes_with_attention": ["policy"], "not_ready_axes": ["policy"]},
                    "macro": {"subject": "support:macro", "qa_axes": {"structural": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "lineage": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}, "policy": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []}}, "axes_with_attention": [], "not_ready_axes": []},
                },
                "aggregate": {"overall_posture": "blocked", "subjects_with_attention": ["support:commodities"], "not_ready_subjects": ["support:commodities"], "axes": {"structural": {"ready": True}, "lineage": {"ready": True}, "policy": {"ready": False}}},
            },
        }
class _DummyHelper:
    def list_db_delivery_candidates(self, **_: object) -> list[dict]:
        return [{"artifact": {"artifact_id": "main-artifact"}, "delivery_manifest": {"artifact_id": "main-artifact", "package_state": "ready", "ready_for_delivery": True, "quality_gate": {"score": 100, "blocker_count": 0, "warning_count": 0}, "slot_evaluation": {"strongest_slot": "late"}}, "report_evaluation": {"summary": {"slot_scores": {"early": 100, "mid": 100, "late": 100}}}, "source": "db_active_delivery_surface"}]

    def summarize_candidate(self, candidate: dict) -> dict:
        return {"artifact_id": candidate["artifact"]["artifact_id"], "recommended_action": "send", "selection_reason": "best_ready_candidate strongest_slot=late qa_score=100"}


def test_build_board_payload_composes_main_and_support_views(monkeypatch) -> None:
    store = _BoardStore()
    monkeypatch.setattr(_module, "FSJStore", lambda: store)
    payload = _build_board_payload(business_date="2099-04-22", history_limit=2)

    assert payload["business_date"] == "2099-04-22"
    assert payload["main"]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["main"]["review_summary"]["go_no_go_decision"] == "GO"
    assert payload["main"]["llm_lineage_summary"]["status"] == "applied"
    assert payload["main_package"]["package_paths"]["delivery_package_dir"] is None
    assert payload["main_review"]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["main_workflow"]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["support"]["macro"]["artifact"]["artifact_id"] == "macro-artifact"
    assert payload["support"]["macro"]["review_summary"]["go_no_go_decision"] == "GO"
    assert payload["support"]["commodities"]["llm_lineage_summary"]["status"] == "degraded"
    assert payload["support_packages"]["macro"]["artifact"]["artifact_id"] == "macro-artifact"
    assert payload["support_workflow"]["macro"]["artifact"]["artifact_id"] == "macro-artifact"
    assert payload["support"]["commodities"]["artifact"]["artifact_id"] == "commodities-artifact"
    assert payload["support"]["ai_tech"]["artifact"]["artifact_id"] == "ai_tech-artifact"
    assert payload["history"][0]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["history"][0]["review_summary"]["go_no_go_decision"] == "GO"
    assert payload["history_packages"][0]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["history_reviews"][0]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["history_workflow"][0]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["db_candidates"][0]["artifact_id"] == "main-artifact"
    assert payload["db_candidate_fleet_summary"]["subject"] == "main"
    assert payload["db_candidate_fleet_summary"]["verdict"] == "aligned"
    assert payload["db_candidate_fleet_summary"]["best_candidate_artifact_id"] == "main-artifact"
    assert payload["db_candidate_history_summary"][0]["subject"] == "history:1"
    assert payload["db_candidate_history_summary"][0]["best_candidate_artifact_id"] == "main-artifact"
    assert payload["artifact_lineage_summary"]["main"]["bundle_lineage_summary"]["bundle_count"] == 2
    assert payload["artifact_lineage_summary"]["support"]["commodities"]["what_user_received"]["dispatch_state"] == "dispatch_failed"
    assert payload["artifact_lineage_summary"]["aggregate"] == {
        "bundle_count": 7,
        "missing_bundle_count": 1,
        "dispatch_succeeded_count": 4,
        "dispatch_failed_count": 1,
    }
    assert payload["llm_lineage_summary"]["aggregate"]["overall_status"] == "degraded"
    assert payload["llm_lineage_summary"]["aggregate"]["attention_subjects"] == ["support:commodities"]
    assert payload["llm_lineage_summary"]["aggregate"]["model_usage_breakdown"]["grok41_thinking"]["estimated_cost_usd"] == 0.01256
    assert payload["llm_lineage_summary"]["aggregate"]["slot_usage_breakdown"]["early"]["fallback_applied_count"] == 1
    assert payload["llm_role_policy_review"]["aggregate"]["policy_versions"] == ["fsj_llm_role_policy_v1"]
    assert payload["board_readiness_summary"]["aggregate"]["source_health_status_counts"] == {"healthy": 3, "degraded": 1}
    assert payload["llm_role_policy_review"]["aggregate"]["override_precedence"] == ["deterministic_input_contract", "validated_llm_text_fields_only"]
    assert payload["llm_role_policy_review"]["aggregate"]["slot_boundary_modes_by_subject"]["main"] == {"late": "same_day_close"}
    assert payload["board_readiness_summary"]["aggregate"]["overall_posture"] == "review_required"
    assert payload["board_readiness_summary"]["aggregate"]["review_required_subjects"] == ["support:commodities"]
    assert payload["board_readiness_summary"]["aggregate"]["canonical_lifecycle_state_counts"] == {"review_ready": 1, "send_ready": 3}
    assert payload["board_rows"]["main"]["status_semantic"] == "ready"
    assert payload["board_rows"]["main"]["canonical_state_vocabulary"] == {
        "canonical_state": "send_ready",
        "canonical_reason": "ready_for_delivery_send",
        "status_semantic": "ready",
        "operator_bucket": "dispatch_gate",
        "terminal": False,
        "summary_line": "canonical=send_ready | status=ready | bucket=dispatch_gate",
    }
    assert payload["board_rows"]["main"]["operator_bucket"] == "dispatch_gate"
    assert payload["board_rows"]["main"]["selected_artifact_id"] == "main-artifact"
    assert payload["board_rows"]["main"]["strongest_slot"] == "late"
    assert payload["board_rows"]["main"]["dispatch_state"] == "dispatch_succeeded"
    assert payload["board_rows"]["support"]["commodities"]["blocking_reason"] == "bundle_missing"
    assert payload["board_rows"]["support"]["commodities"]["canonical_state_vocabulary"] == {
        "canonical_state": "review_ready",
        "canonical_reason": "manual_review_required",
        "status_semantic": "review",
        "operator_bucket": "operator_gate",
        "terminal": False,
        "summary_line": "canonical=review_ready | status=review | bucket=operator_gate",
    }
    assert payload["board_rows"]["support"]["commodities"]["operator_bucket"] == "operator_gate"
    assert payload["board_rows"]["support"]["commodities"]["failure_taxonomy_class"] == "hold_review"
    assert payload["board_rows"]["support"]["commodities"]["missing_bundle_count"] == 1
    assert payload["board_rows"]["aggregate"]["status_semantic_counts"] == {"ready": 3, "review": 1}
    assert payload["board_rows"]["aggregate"]["dispatch_state_counts"] == {"dispatch_succeeded": 3, "dispatch_failed": 1}
    assert payload["board_rows"]["aggregate"]["strongest_slot_counts"] == {"early": 3, "late": 1}
    assert payload["board_rows"]["aggregate"]["failure_taxonomy_counts"] == {"hold_review": 1}
    assert payload["board_rows"]["aggregate"]["failure_taxonomy_subjects"] == {"hold_review": ["support:commodities"]}
    assert payload["board_rows"]["aggregate"]["subjects_with_missing_bundles"] == ["support:commodities"]
    assert payload["qa_axes_summary"]["support"]["commodities"]["axes_with_attention"] == ["policy"]
    assert payload["qa_axes_summary"]["aggregate"]["overall_posture"] == "blocked"
    assert payload["qa_axes_summary"]["aggregate"]["subjects_with_attention"] == ["support:commodities"]
    assert payload["qa_axes_summary"]["aggregate"]["not_ready_subjects"] == ["support:commodities"]


def test_build_board_payload_includes_drift_summary_lines(monkeypatch) -> None:
    store = _BoardStore()
    monkeypatch.setattr(_module, "FSJStore", lambda: store)
    payload = _build_board_payload(business_date="2099-04-22", history_limit=2)

    assert payload["drift_summary_lines"] == {
        "main": "7d drift main: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 0/1",
        "support:ai_tech": "7d drift support:ai_tech: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 0/1",
        "support:commodities": "7d drift support:commodities: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 1/1",
        "support:macro": "7d drift support:macro: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 0/1",
    }
    assert payload["fleet_drift_digest"] == {
        "window_days": 7,
        "main": {
            "label": "main",
            "scope_count": 1,
            "reported_day_count": 1,
            "hold_count": 1,
            "fallback_count": 0,
            "mismatch_count": 0,
            "qa_attention_count": 0,
            "llm_model_counts": {},
            "llm_slot_counts": {},
            "llm_total_tokens": 0,
            "llm_usage_bundle_count": 0,
            "llm_uncosted_bundle_count": 0,
            "llm_estimated_cost_usd": None,
        },
        "support": {
            "label": "support",
            "scope_count": 3,
            "reported_day_count": 3,
            "hold_count": 3,
            "fallback_count": 0,
            "mismatch_count": 0,
            "qa_attention_count": 1,
            "llm_model_counts": {},
            "llm_slot_counts": {},
            "llm_total_tokens": 0,
            "llm_usage_bundle_count": 0,
            "llm_uncosted_bundle_count": 0,
            "llm_estimated_cost_usd": None,
        },
    }
    assert payload["fleet_drift_digest_line"] == "7d fleet drift: main hold 1/1 (1 scope) | fallback 0/1 | mismatch 0/1 | qa_attn 0/1 || support hold 3/3 (3 scope) | fallback 0/3 | mismatch 0/3 | qa_attn 1/3"


def test_build_board_payload_can_resolve_latest_business_date(monkeypatch) -> None:
    store = _BoardStore()
    monkeypatch.setattr(_module, "FSJStore", lambda: store)
    payload = _build_board_payload(business_date=None, history_limit=1)

    assert payload["resolution"]["mode"] == "latest_active_lookup"
    assert payload["business_date"] == "2099-04-22"


def test_script_help_runs_without_pythonpath() -> None:
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    result = subprocess.run(
        [
            sys.executable,
            str(_MODULE_PATH),
            "--help",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


def test_print_text_emits_operator_board_summary(capsys) -> None:
    payload = {
        "business_date": "2099-04-22",
        "resolution": {"mode": "explicit_business_date", "business_date": "2099-04-22"},
        "main": {"artifact": {"artifact_id": "main-artifact", "status": "active"}, "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready", "ready_for_delivery": True, "review_required": False}, "canonical_lifecycle": {"state": "send_ready", "reason": "ready_for_delivery_send"}, "local_to_canonical_state_mapping": {"summary_line": "artifact_status=active | workflow_state=ready_to_send | package_state=ready | recommended_action=send | ready_for_delivery=True | review_required=False | dispatch_state=dispatch_attempted | selected_is_current=True => canonical=send_ready (ready/dispatch_gate)"}, "promotion_authority": {"status": "approved_to_send", "approved": True, "required_action": "send_selected_package_to_primary_channel", "rationale": "quality gate and artifact integrity both pass", "summary_line": "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass"}, "governance": {"decision": "GO", "rationale": "quality gate and artifact integrity both pass", "next_step": "send_selected_package_to_primary_channel", "action_required": False}, "dispatch_state": "dispatch_attempted", "dispatch_receipt": {"dispatch_state": "dispatch_attempted", "channel": "telegram_document", "error": None}, "review_summary": {"source_health_status": "healthy", "source_health_blocking_slot_count": 0, "source_health_degraded_slot_count": 0, "source_health_degrade_reason": None}, "artifact_lineage": {"bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 0}, "what_user_received": {"dispatch_state": "dispatch_succeeded", "provider_message_id": "msg-main-artifact"}}, "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=1/1]", "models": ["grok41_thinking"], "token_totals": {"total_tokens": 341}, "estimated_cost_usd": None}, "llm_role_policy": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"late": "same_day_close"}}},
        "support": {
            "ai_tech": {"artifact": {"artifact_id": "ai-tech-artifact"}, "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready"}, "canonical_lifecycle": {"state": "send_ready", "reason": "ready_for_delivery_send"}, "governance": {"decision": "GO", "rationale": "quality gate and artifact integrity both pass", "next_step": "send_selected_package_to_primary_channel", "action_required": False}, "review_summary": {"source_health_status": "healthy", "source_health_blocking_slot_count": 0, "source_health_degraded_slot_count": 0, "source_health_degrade_reason": None}, "artifact_lineage": {"bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 0}, "what_user_received": {"dispatch_state": "dispatch_succeeded", "provider_message_id": "msg-ai-tech-artifact"}}, "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=1/1]", "models": ["grok41_thinking"], "token_totals": {"total_tokens": 287}, "estimated_cost_usd": None}, "llm_role_policy": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"early": "candidate_only"}}},
            "commodities": {"artifact": {"artifact_id": "commodities-artifact", "status": "active"}, "state": {"recommended_action": "send_review", "workflow_state": "review_required", "package_state": "ready", "ready_for_delivery": True, "review_required": True}, "canonical_lifecycle": {"state": "review_ready", "reason": "manual_review_required"}, "local_to_canonical_state_mapping": {"summary_line": "artifact_status=active | workflow_state=review_required | package_state=ready | recommended_action=send_review | ready_for_delivery=True | review_required=True | dispatch_state=dispatch_failed | selected_is_current=True => canonical=failed (held/terminal_attention)"}, "promotion_authority": {"status": "review_required", "approved": False, "required_action": "review_current_package_then_send_if_accepted", "rationale": "manual review is required before sending", "summary_line": "review_required | decision=REVIEW | selected_is_current=True | required_action=review_current_package_then_send_if_accepted | rationale=manual review is required before sending"}, "governance": {"decision": "REVIEW", "rationale": "manual review is required before sending", "next_step": "review_current_package_then_send_if_accepted", "action_required": True}, "review_summary": {"source_health_status": "degraded", "source_health_blocking_slot_count": 0, "source_health_degraded_slot_count": 1, "source_health_degrade_reason": "missing_background_support"}, "artifact_lineage": {"bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 1}, "what_user_received": {"dispatch_state": "dispatch_failed", "provider_message_id": None}}, "llm_lineage_summary": {"status": "degraded", "summary_line": "degraded [applied=1/1]", "models": ["gemini31_pro_jmr"], "token_totals": {"total_tokens": 355}, "estimated_cost_usd": None}, "llm_role_policy": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"late": "candidate_only"}}},
            "macro": None,
        },
        "history": [{}, {}],
        "db_candidates": [{}, {}],
        "db_candidate_fleet_summary": {
            "subject": "main",
            "verdict": "review_held",
            "reason_code": "review_held_selected_candidate_differs_from_current",
            "summary_line": "Current MAIN artifact main-artifact is not the selected DB candidate; operator selection is held on main-artifact-v2 for review.",
            "current_artifact_id": "main-artifact",
            "selected_artifact_id": "main-artifact-v2",
            "best_candidate_artifact_id": "main-artifact-v2",
            "selected_matches_best": True,
            "current_matches_best": False,
        },
        "artifact_lineage_summary": {
            "main": {"bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 0}, "what_user_received": {"dispatch_state": "dispatch_succeeded", "provider_message_id": "msg-main-artifact"}},
            "support": {
                "ai_tech": {"bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 0}, "what_user_received": {"dispatch_state": "dispatch_succeeded", "provider_message_id": "msg-ai-tech-artifact"}},
                "commodities": {"bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 1}, "what_user_received": {"dispatch_state": "dispatch_failed", "provider_message_id": None}},
                "macro": None,
            },
            "aggregate": {"bundle_count": 4, "missing_bundle_count": 1, "dispatch_succeeded_count": 2, "dispatch_failed_count": 1},
        },
        "db_candidate_history_summary": [
            {
                "subject": "history:1",
                "history_index": 1,
                "artifact_status": "superseded",
                "verdict": "mismatch",
                "reason_code": "better_ready_candidate_selected_current_outdated",
                "summary_line": "Current MAIN artifact main-artifact is not the best DB candidate; selected artifact main-artifact-v2 supersedes it as the best ready candidate.",
                "current_artifact_id": "main-artifact",
                "best_candidate_artifact_id": "main-artifact-v2",
                "canonical_lifecycle_state": "failed",
                "canonical_lifecycle_reason": "dispatch_receipt_failed",
                "dispatch_state": "dispatch_failed",
                "dispatch_receipt_state": "dispatch_failed",
                "dispatch_receipt_channel": "telegram_document",
                "dispatch_receipt_error": "429 rate limit",
            }
        ],
        "llm_lineage_summary": {
            "main": {"status": "applied", "summary_line": "applied [applied=1/1]", "models": ["grok41_thinking"], "token_totals": {"total_tokens": 341}, "estimated_cost_usd": 0.00682, "priced_bundle_count": 1, "costed_bundle_count": 1, "budget_posture": "fully_priced", "budget_attention": False, "budget_summary_line": "fully_priced [1/1]"},
            "support": {
                "ai_tech": {"status": "applied", "summary_line": "applied [applied=1/1]", "models": ["grok41_thinking"], "token_totals": {"total_tokens": 287}, "estimated_cost_usd": 0.00574, "priced_bundle_count": 1, "costed_bundle_count": 1, "budget_posture": "fully_priced", "budget_attention": False, "budget_summary_line": "fully_priced [1/1]"},
                "commodities": {"status": "degraded", "summary_line": "degraded [applied=1/1]", "models": ["gemini31_pro_jmr"], "token_totals": {"total_tokens": 355}, "estimated_cost_usd": None, "priced_bundle_count": 0, "costed_bundle_count": 0, "budget_posture": "unpriced", "budget_attention": True, "budget_summary_line": "unpriced [0/1 priced | unpriced=1]"},
                "macro": None,
            },
            "aggregate": {"overall_status": "degraded", "attention_subjects": ["support:commodities"], "reported_subject_count": 3, "models": ["gemini31_pro_jmr", "grok41_thinking"], "total_tokens": 983, "estimated_cost_usd": 0.01256, "uncosted_bundle_count": 1, "model_usage_breakdown": {"gemini31_pro_jmr": {"bundle_count": 1, "applied_count": 1, "fallback_applied_count": 1, "total_tokens": 355, "estimated_cost_usd": None}, "grok41_thinking": {"bundle_count": 2, "applied_count": 2, "fallback_applied_count": 0, "total_tokens": 628, "estimated_cost_usd": 0.01256}}, "slot_usage_breakdown": {"early": {"bundle_count": 2, "applied_count": 2, "fallback_applied_count": 1, "total_tokens": 642}, "late": {"bundle_count": 1, "applied_count": 1, "fallback_applied_count": 0, "total_tokens": 341}}},
        },
        "llm_role_policy_review": {
            "main": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"late": "same_day_close"}},
            "support": {
                "ai_tech": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"early": "candidate_only"}},
                "commodities": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"late": "candidate_only"}},
                "macro": None,
            },
            "aggregate": {
                "policy_versions": ["fsj_llm_role_policy_v1"],
                "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                "attention_subjects": ["main", "support:ai_tech", "support:commodities"],
            },
        },
        "board_readiness_summary": {
            "aggregate": {
                "overall_posture": "review_required",
                "ready_subjects": ["main", "support:ai_tech"],
                "review_required_subjects": ["support:commodities"],
                "governance_action_required_subjects": ["support:commodities"],
                "blocked_subjects": [],
                "attention_subjects": ["support:commodities"],
                "source_health_status_counts": {"degraded": 1, "healthy": 2},
                "source_health_attention_subjects": ["support:commodities"],
                "source_health_blocked_subjects": [],
                "source_health_degraded_subjects": ["support:commodities"],
                "canonical_lifecycle_state_counts": {"review_ready": 1, "send_ready": 2},
            },
        },
        "board_rows": {
            "main": {"subject": "main", "artifact_id": "main-artifact", "status_semantic": "ready", "canonical_lifecycle_state": "send_ready", "next_action": "send_selected_package_to_primary_channel", "blocking_reason": None, "selected_artifact_id": "main-artifact", "selected_is_current": True, "strongest_slot": "late", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_succeeded", "bundle_count": 2, "missing_bundle_count": 0, "lineage_sla_summary": "selected=main-artifact | slot=late | bundles=2 | missing=0 | dispatch=dispatch_succeeded | generated=2099-04-22T10:00:00+00:00", "failure_taxonomy_class": "none", "failure_taxonomy_reason": None, "failure_taxonomy_summary": "none | no failure taxonomy attention currently projected", "summary_line": "main | status=ready | canonical=send_ready | action=send_selected_package_to_primary_channel"},
            "support": {
                "ai_tech": {"subject": "support:ai_tech", "artifact_id": "ai-tech-artifact", "status_semantic": "ready", "canonical_lifecycle_state": "send_ready", "next_action": "send_selected_package_to_primary_channel", "blocking_reason": None, "selected_artifact_id": "ai-tech-artifact", "selected_is_current": True, "strongest_slot": "early", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_succeeded", "bundle_count": 1, "missing_bundle_count": 0, "lineage_sla_summary": "selected=ai-tech-artifact | slot=early | bundles=1 | missing=0 | dispatch=dispatch_succeeded | generated=2099-04-22T10:00:00+00:00", "summary_line": "support:ai_tech | status=ready | canonical=send_ready | action=send_selected_package_to_primary_channel"},
                "commodities": {"subject": "support:commodities", "artifact_id": "commodities-artifact", "status_semantic": "review", "canonical_lifecycle_state": "review_ready", "next_action": "review_current_package_then_send_if_accepted", "blocking_reason": "bundle_missing", "selected_artifact_id": "commodities-artifact", "selected_is_current": True, "strongest_slot": "late", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_failed", "bundle_count": 1, "missing_bundle_count": 1, "lineage_sla_summary": "selected=commodities-artifact | slot=late | bundles=1 | missing=1 | dispatch=dispatch_failed | generated=2099-04-22T10:00:00+00:00", "failure_taxonomy_class": "hold_review", "failure_taxonomy_reason": "bundle_missing", "failure_taxonomy_summary": "hold_review | operator intervention or review remains required", "summary_line": "support:commodities | status=review | canonical=review_ready | action=review_current_package_then_send_if_accepted | blocker=bundle_missing"},
                "macro": None,
            },
            "history": [
                {"subject": "history:1", "history_index": 1, "artifact_id": "main-artifact", "status_semantic": "held", "canonical_lifecycle_state": "failed", "next_action": None, "blocking_reason": "dispatch_receipt_failed", "selected_artifact_id": "main-artifact-v2", "selected_is_current": False, "strongest_slot": "late", "generated_at_utc": "2099-04-22T10:00:00+00:00", "dispatch_state": "dispatch_failed", "bundle_count": 2, "missing_bundle_count": 0, "lineage_sla_summary": "selected=main-artifact-v2 | slot=late | bundles=2 | missing=0 | dispatch=dispatch_failed | generated=2099-04-22T10:00:00+00:00", "failure_taxonomy_class": "hold_review", "failure_taxonomy_reason": "dispatch_receipt_failed", "failure_taxonomy_summary": "hold_review | operator intervention or review remains required", "summary_line": "history:1 | status=held | canonical=failed | action=- | failure_taxonomy=hold_review | blocker=dispatch_receipt_failed"}
            ],
            "aggregate": {"reported_subject_count": 3, "status_semantic_counts": {"ready": 2, "review": 1}, "dispatch_state_counts": {"dispatch_failed": 1, "dispatch_succeeded": 2}, "strongest_slot_counts": {"early": 1, "late": 2}, "failure_taxonomy_counts": {"hold_review": 2}, "failure_taxonomy_subjects": {"hold_review": ["support:commodities", "history:1"]}, "subjects_with_blocking_reason": ["support:commodities"], "subjects_with_next_action": ["main", "support:ai_tech", "support:commodities"], "selected_mismatch_subjects": ["history:1"], "subjects_with_missing_bundles": ["support:commodities"]},
        },
        "board_state_source_summary": {
            "main": {"subject": "main", "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step", "blocking_reason_source_of_truth": None, "summary_line": "state=send_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step"},
            "support": {
                "ai_tech": {"subject": "support:ai_tech", "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step", "blocking_reason_source_of_truth": None, "summary_line": "state=send_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step"},
                "commodities": {"subject": "support:commodities", "state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step", "blocking_reason_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.send_blockers", "summary_line": "state=review_ready via ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff | next_action via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step | blockers via ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.send_blockers"},
                "macro": None,
            },
            "aggregate": {"state_source_counts": {"ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff": 3}, "subjects_with_next_action_source": ["main", "support:ai_tech", "support:commodities"], "subjects_with_blocking_reason_source": ["support:commodities"]},
        },
        "qa_axes_summary": {
            "main": {"subject": "main", "qa_axes": {"structural": {"ready": True, "blocker_count": 0, "warning_count": 0}, "lineage": {"ready": True, "blocker_count": 0, "warning_count": 0}, "policy": {"ready": True, "blocker_count": 0, "warning_count": 0}}, "axes_with_attention": [], "not_ready_axes": []},
            "support": {
                "ai_tech": {"subject": "support:ai_tech", "qa_axes": {"structural": {"ready": True, "blocker_count": 0, "warning_count": 0}, "lineage": {"ready": True, "blocker_count": 0, "warning_count": 0}, "policy": {"ready": True, "blocker_count": 0, "warning_count": 0}}, "axes_with_attention": [], "not_ready_axes": []},
                "commodities": {"subject": "support:commodities", "qa_axes": {"structural": {"ready": True, "blocker_count": 0, "warning_count": 0}, "lineage": {"ready": True, "blocker_count": 0, "warning_count": 0}, "policy": {"ready": False, "blocker_count": 0, "warning_count": 1}}, "axes_with_attention": ["policy"], "not_ready_axes": ["policy"]},
                "macro": None,
            },
            "aggregate": {"overall_posture": "blocked", "subjects_with_attention": ["support:commodities"], "not_ready_subjects": ["support:commodities"], "axes": {"structural": {"ready": True}, "lineage": {"ready": True}, "policy": {"ready": False}}},
        },
        "drift_summary_lines": {
            "main": "7d drift main: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 0/1",
            "support:ai_tech": "7d drift support:ai_tech: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 0/1",
            "support:commodities": "7d drift support:commodities: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 1/1",
            "support:macro": "7d drift support:macro: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 0/1",
        },
        "fleet_drift_digest": {
            "window_days": 7,
            "main": {
                "label": "main",
                "scope_count": 1,
                "reported_day_count": 1,
                "hold_count": 1,
                "fallback_count": 0,
                "mismatch_count": 0,
                "qa_attention_count": 0,
                "llm_model_counts": {"grok41_thinking": 1},
                "llm_slot_counts": {"late": 1},
                "llm_total_tokens": 341,
                "llm_usage_bundle_count": 1,
                "priced_bundle_count": 1,
                "costed_bundle_count": 1,
                "budget_posture": "fully_priced",
                "budget_attention": False,
                "budget_summary_line": "fully_priced [1/1]",
                "llm_uncosted_bundle_count": 0,
                "llm_estimated_cost_usd": 0.00682,
            },
            "support": {
                "label": "support",
                "scope_count": 3,
                "reported_day_count": 3,
                "hold_count": 3,
                "fallback_count": 0,
                "mismatch_count": 0,
                "qa_attention_count": 1,
                "llm_model_counts": {"gemini31_pro_jmr": 1, "grok41_thinking": 1},
                "llm_slot_counts": {"early": 1, "late": 1},
                "llm_total_tokens": 642,
                "llm_usage_bundle_count": 2,
                "priced_bundle_count": 1,
                "costed_bundle_count": 1,
                "budget_posture": "mixed",
                "budget_attention": True,
                "budget_summary_line": "mixed [1/2 priced | unpriced=1]",
                "llm_uncosted_bundle_count": 1,
                "llm_estimated_cost_usd": 0.00574,
            },
        },
        "fleet_drift_digest_line": "7d fleet drift: main hold 1/1 (1 scope) | fallback 0/1 | mismatch 0/1 | qa_attn 0/1 || support hold 3/3 (3 scope) | fallback 0/3 | mismatch 0/3 | qa_attn 1/3"
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "business_date=2099-04-22" in output
    assert "resolution_mode=explicit_business_date" in output
    assert "main_artifact_id=main-artifact" in output
    assert "main_recommended_action=send" in output
    assert "main_source_health_status=healthy" in output
    assert "main_source_health_blocking_slots=0" in output
    assert "main_source_health_degraded_slots=0" in output
    assert "main_source_health_degrade_reason=None" in output
    assert "main_canonical_lifecycle_state=send_ready" in output
    assert "main_canonical_lifecycle_reason=ready_for_delivery_send" in output
    assert "main_local_to_canonical_state_mapping_summary=artifact_status=active | workflow_state=ready_to_send | package_state=ready | recommended_action=send | ready_for_delivery=True | review_required=False | dispatch_state=dispatch_attempted | selected_is_current=True => canonical=send_ready (ready/dispatch_gate)" in output
    assert "main_board_status=ready" in output
    assert "main_board_blocking_reason=None" in output
    assert "main_board_next_action=send_selected_package_to_primary_channel" in output
    assert "main_board_selected_artifact_id=main-artifact" in output
    assert "main_board_selected_is_current=True" in output
    assert "main_board_strongest_slot=late" in output
    assert "main_board_generated_at_utc=2099-04-22T10:00:00+00:00" in output
    assert "main_board_dispatch_state=dispatch_succeeded" in output
    assert "main_board_bundle_count=2" in output
    assert "main_board_missing_bundle_count=0" in output
    assert "main_board_lineage_sla_summary=selected=main-artifact | slot=late | bundles=2 | missing=0 | dispatch=dispatch_succeeded | generated=2099-04-22T10:00:00+00:00" in output
    assert "main_board_failure_taxonomy_class=none" in output
    assert "main_board_failure_taxonomy_reason=None" in output
    assert "main_board_failure_taxonomy_summary=none | no failure taxonomy attention currently projected" in output
    assert "main_board_row_summary=main | status=ready | canonical=send_ready | action=send_selected_package_to_primary_channel" in output
    assert "main_board_state_source=ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff" in output
    assert "main_board_next_action_source=ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step" in output
    assert "main_dispatch_state=dispatch_attempted" in output
    assert "main_dispatch_receipt_state=dispatch_attempted" in output
    assert "main_dispatch_receipt_channel=telegram_document" in output
    assert "main_dispatch_receipt_error=None" in output
    assert "main_governance_decision=GO" in output
    assert "main_governance_rationale=quality gate and artifact integrity both pass" in output
    assert "main_promotion_authority_status=approved_to_send" in output
    assert "main_promotion_authority_approved=True" in output
    assert "main_promotion_authority_required_action=send_selected_package_to_primary_channel" in output
    assert "main_governance_next_step=send_selected_package_to_primary_channel" in output
    assert "main_governance_action_required=False" in output
    assert "main_lineage_bundle_count=2" in output
    assert "main_lineage_missing_bundle_count=0" in output
    assert "main_lineage_dispatch_state=dispatch_succeeded" in output
    assert "main_lineage_provider_message_id=msg-main-artifact" in output
    assert "main_llm_lineage_status=applied" in output
    assert "main_llm_models=grok41_thinking" in output
    assert "main_llm_total_tokens=341" in output
    assert "main_llm_override_precedence=deterministic_input_contract>validated_llm_text_fields_only" in output
    assert "main_llm_slot_boundary_modes=late:same_day_close" in output
    assert "support_ai_tech_artifact_id=ai-tech-artifact" in output
    assert "support_commodities_recommended_action=send_review" in output
    assert "support_commodities_source_health_status=degraded" in output
    assert "support_commodities_source_health_blocking_slots=0" in output
    assert "support_commodities_source_health_degraded_slots=1" in output
    assert "support_commodities_source_health_degrade_reason=missing_background_support" in output
    assert "support_commodities_canonical_lifecycle_state=review_ready" in output
    assert "support_commodities_canonical_lifecycle_reason=manual_review_required" in output
    assert "support_commodities_local_to_canonical_state_mapping_summary=artifact_status=active | workflow_state=review_required | package_state=ready | recommended_action=send_review | ready_for_delivery=True | review_required=True | dispatch_state=dispatch_failed | selected_is_current=True => canonical=failed (held/terminal_attention)" in output
    assert "support_commodities_board_status=review" in output
    assert "support_commodities_board_blocking_reason=bundle_missing" in output
    assert "support_commodities_board_next_action=review_current_package_then_send_if_accepted" in output
    assert "support_commodities_board_selected_artifact_id=commodities-artifact" in output
    assert "support_commodities_board_selected_is_current=True" in output
    assert "support_commodities_board_strongest_slot=late" in output
    assert "support_commodities_board_generated_at_utc=2099-04-22T10:00:00+00:00" in output
    assert "support_commodities_board_dispatch_state=dispatch_failed" in output
    assert "support_commodities_board_bundle_count=1" in output
    assert "support_commodities_board_missing_bundle_count=1" in output
    assert "support_commodities_board_lineage_sla_summary=selected=commodities-artifact | slot=late | bundles=1 | missing=1 | dispatch=dispatch_failed | generated=2099-04-22T10:00:00+00:00" in output
    assert "support_commodities_board_failure_taxonomy_class=hold_review" in output
    assert "support_commodities_board_failure_taxonomy_reason=bundle_missing" in output
    assert "support_commodities_board_failure_taxonomy_summary=hold_review | operator intervention or review remains required" in output
    assert "support_commodities_board_row_summary=support:commodities | status=review | canonical=review_ready | action=review_current_package_then_send_if_accepted | blocker=bundle_missing" in output
    assert "support_commodities_board_blocking_reason_source=ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.send_blockers" in output
    assert "support_commodities_governance_decision=REVIEW" in output
    assert "support_commodities_governance_rationale=manual review is required before sending" in output
    assert "support_commodities_promotion_authority_status=review_required" in output
    assert "support_commodities_promotion_authority_approved=False" in output
    assert "support_commodities_promotion_authority_required_action=review_current_package_then_send_if_accepted" in output
    assert "support_commodities_governance_next_step=review_current_package_then_send_if_accepted" in output
    assert "support_commodities_governance_action_required=True" in output
    assert "support_commodities_lineage_bundle_count=1" in output
    assert "support_commodities_lineage_missing_bundle_count=1" in output
    assert "support_commodities_lineage_dispatch_state=dispatch_failed" in output
    assert "support_commodities_lineage_provider_message_id=None" in output
    assert "support_commodities_llm_lineage_status=degraded" in output
    assert "support_commodities_llm_models=gemini31_pro_jmr" in output
    assert "support_commodities_llm_total_tokens=355" in output
    assert "support_commodities_llm_slot_boundary_modes=late:candidate_only" in output
    assert "fleet_artifact_lineage_bundle_count=4" in output
    assert "fleet_artifact_lineage_missing_bundle_count=1" in output
    assert "fleet_artifact_lineage_dispatches_sent=2" in output
    assert "fleet_artifact_lineage_dispatches_failed=1" in output
    assert "fleet_llm_lineage_status=degraded" in output
    assert "fleet_llm_attention_subjects=support:commodities" in output
    assert "fleet_llm_models=gemini31_pro_jmr,grok41_thinking" in output
    assert "fleet_llm_total_tokens=983" in output
    assert "fleet_llm_uncosted_bundle_count=1" in output
    assert "fleet_llm_model_usage_breakdown=gemini31_pro_jmr:b1:a1:f1:t355:cNone,grok41_thinking:b2:a2:f0:t628:c0.01256" in output
    assert "fleet_llm_slot_usage_breakdown=early:b2:a2:f1:t642,late:b1:a1:f0:t341" in output
    assert "fleet_llm_policy_versions=fsj_llm_role_policy_v1" in output
    assert "fleet_llm_override_precedence=deterministic_input_contract>validated_llm_text_fields_only" in output
    assert "fleet_llm_attention_policy_subjects=main,support:ai_tech,support:commodities" in output
    assert "fleet_board_posture=review_required" in output
    assert "fleet_source_health_status_counts=degraded:1,healthy:2" in output
    assert "fleet_source_health_attention_subjects=support:commodities" in output
    assert "fleet_source_health_blocked_subjects=" in output
    assert "fleet_source_health_degraded_subjects=support:commodities" in output
    assert "fleet_canonical_lifecycle_state_counts=review_ready:1,send_ready:2" in output
    assert "fleet_board_status_counts=ready:2,review:1" in output
    assert "fleet_board_dispatch_state_counts=dispatch_failed:1,dispatch_succeeded:2" in output
    assert "fleet_board_strongest_slot_counts=early:1,late:2" in output
    assert "fleet_board_failure_taxonomy_counts=hold_review:2" in output
    assert "fleet_board_failure_taxonomy_subjects_hold_review=support:commodities,history:1" in output
    assert "fleet_board_next_action_subjects=main,support:ai_tech,support:commodities" in output
    assert "fleet_board_blocking_reason_subjects=support:commodities" in output
    assert "fleet_board_selected_mismatch_subjects=history:1" in output
    assert "fleet_board_missing_bundle_subjects=support:commodities" in output
    assert "fleet_board_state_source_counts=ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff:3" in output
    assert "fleet_board_blocking_reason_source_subjects=support:commodities" in output
    assert "fleet_drift_digest_line=7d fleet drift: main hold 1/1 (1 scope) | fallback 0/1 | mismatch 0/1 | qa_attn 0/1 || support hold 3/3 (3 scope) | fallback 0/3 | mismatch 0/3 | qa_attn 1/3" in output
    assert "fleet_drift_main_llm_model_counts=grok41_thinking:1" in output
    assert "fleet_drift_main_llm_slot_counts=late:1" in output
    assert "fleet_drift_main_llm_total_tokens=341" in output
    assert "fleet_drift_main_llm_usage_bundle_count=1" in output
    assert "fleet_drift_main_llm_uncosted_bundle_count=0" in output
    assert "fleet_drift_main_llm_estimated_cost_usd=0.00682" in output
    assert "fleet_drift_support_llm_model_counts=gemini31_pro_jmr:1,grok41_thinking:1" in output
    assert "fleet_drift_support_llm_slot_counts=early:1,late:1" in output
    assert "fleet_drift_support_llm_total_tokens=642" in output
    assert "fleet_drift_support_llm_usage_bundle_count=2" in output
    assert "fleet_drift_support_llm_uncosted_bundle_count=1" in output
    assert "fleet_drift_support_llm_estimated_cost_usd=0.00574" in output
    assert "main_qa_axes=lineage:ready:b0:w0,policy:ready:b0:w0,structural:ready:b0:w0" in output
    assert "support_commodities_qa_axes=lineage:ready:b0:w0,policy:attention:b0:w1,structural:ready:b0:w0" in output
    assert "support_commodities_qa_axes_attention=policy" in output
    assert "main_drift_summary_line=7d drift main: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 0/1" in output
    assert "support_commodities_drift_summary_line=7d drift support:commodities: hold 1/1 | fallback 0/1 | mismatch 0/1 | qa_attn 1/1" in output
    assert "fleet_qa_axes_posture=blocked" in output
    assert "fleet_qa_axes_attention_subjects=support:commodities" in output
    assert "fleet_qa_axes_not_ready_subjects=support:commodities" in output
    assert "fleet_qa_axes_axes=lineage,policy,structural" in output
    assert "db_candidate_fleet_verdict=review_held" in output
    assert "db_candidate_fleet_reason=review_held_selected_candidate_differs_from_current" in output
    assert "db_candidate_selected_artifact_id=main-artifact-v2" in output
    assert "db_candidate_current_matches_best=False" in output
    assert "board_history_1_subject=history:1" in output
    assert "board_history_1_status=held" in output
    assert "board_history_1_blocking_reason=dispatch_receipt_failed" in output
    assert "board_history_1_next_action=None" in output
    assert "board_history_1_selected_artifact_id=main-artifact-v2" in output
    assert "board_history_1_selected_is_current=False" in output
    assert "board_history_1_strongest_slot=late" in output
    assert "board_history_1_generated_at_utc=2099-04-22T10:00:00+00:00" in output
    assert "board_history_1_dispatch_state=dispatch_failed" in output
    assert "board_history_1_bundle_count=2" in output
    assert "board_history_1_missing_bundle_count=0" in output
    assert "board_history_1_lineage_sla_summary=selected=main-artifact-v2 | slot=late | bundles=2 | missing=0 | dispatch=dispatch_failed | generated=2099-04-22T10:00:00+00:00" in output
    assert "board_history_1_failure_taxonomy_class=hold_review" in output
    assert "board_history_1_failure_taxonomy_reason=dispatch_receipt_failed" in output
    assert "board_history_1_failure_taxonomy_summary=hold_review | operator intervention or review remains required" in output
    assert "board_history_1_summary=history:1 | status=held | canonical=failed | action=- | failure_taxonomy=hold_review | blocker=dispatch_receipt_failed" in output
    assert "db_candidate_history_count=1" in output
    assert "db_candidate_history_1_subject=history:1" in output
    assert "db_candidate_history_1_reason=better_ready_candidate_selected_current_outdated" in output
    assert "db_candidate_history_1_canonical_lifecycle_state=failed" in output
    assert "db_candidate_history_1_canonical_lifecycle_reason=dispatch_receipt_failed" in output
    assert "db_candidate_history_1_dispatch_state=dispatch_failed" in output
    assert "db_candidate_history_1_dispatch_receipt_state=dispatch_failed" in output
    assert "db_candidate_history_1_dispatch_receipt_channel=telegram_document" in output
    assert "db_candidate_history_1_dispatch_receipt_error=429 rate limit" in output
    assert "fleet_review_subjects=support:commodities" in output
    assert "fleet_governance_action_required_subjects=support:commodities" in output
    assert "fleet_attention_subjects=support:commodities" in output
    assert "support_macro=NONE" in output
    assert "candidate_count=2" in output



class _ActualBoardStore(FSJStore):
    def __init__(self) -> None:
        pass

    def get_latest_active_report_delivery_surface(self, **kwargs: object) -> dict | None:
        if kwargs["agent_domain"] == "main":
            return {
                "artifact": {"artifact_id": "artifact-current", "report_run_id": "run-current", "business_date": "2099-04-22", "status": "active"},
                "delivery_package": {"slot_evaluation": {"strongest_slot": "late"}},
            }
        return None

    def get_active_report_delivery_surface(self, **kwargs: object) -> dict | None:
        domain = kwargs["agent_domain"]
        if domain == "main":
            return {
                "artifact": {"artifact_id": "artifact-current", "report_run_id": "run-current", "business_date": kwargs["business_date"], "status": "active", "metadata_json": {"bundle_ids": ["bundle-late"]}},
                "delivery_package": {
                    "package_state": "ready",
                    "ready_for_delivery": False,
                    "quality_gate": {"score": 91, "blocker_count": 1, "warning_count": 1},
                    "workflow": {"recommended_action": "send_review", "dispatch_recommended_action": "send_review", "workflow_state": "review_required"},
                    "artifacts": {},
                },
                "workflow_linkage": {
                    "selected_handoff": {"selected_artifact_id": "artifact-selected", "selected_is_current": False},
                    "review_surface": {
                        "candidate_comparison": {
                            "selected_artifact_id": "artifact-selected",
                            "current_artifact_id": "artifact-current",
                            "candidate_count": 3,
                            "ready_candidate_count": 1,
                            "ranked_candidates": [
                                {"artifact_id": "artifact-selected", "rank": 1, "ready_for_delivery": False, "recommended_action": "send_review", "selection_reason": "best_available_candidate provisional_close_only_requires_review"},
                                {"artifact_id": "artifact-current", "rank": 2, "ready_for_delivery": False, "recommended_action": "send_review", "selection_reason": "best_available_candidate provisional_close_only_requires_review"},
                                {"artifact_id": "artifact-old", "rank": 3, "ready_for_delivery": False, "recommended_action": "hold", "selection_reason": "best_available_candidate blocked_requires_hold"},
                            ],
                            "current_vs_selected": {
                                "current_artifact_id": "artifact-current",
                                "selected_artifact_id": "artifact-selected",
                                "current_rank": 2,
                                "selected_rank": 1,
                            },
                        },
                        "dispatch_receipt": {
                            "dispatch_state": "dispatch_failed",
                            "attempted_at": "2099-04-22T09:31:00Z",
                            "failed_at": "2099-04-22T09:31:04Z",
                            "channel": "telegram_document",
                            "error": "429 rate limit",
                        },
                    },
                },
            }
        return {
            "artifact": {"artifact_id": f"{domain}-artifact", "report_run_id": f"{domain}-run", "business_date": kwargs["business_date"], "status": "active", "metadata_json": {"bundle_ids": [f"bundle-{domain}"]}},
            "delivery_package": {"package_state": "ready", "ready_for_delivery": True, "quality_gate": {"score": 95, "blocker_count": 0, "warning_count": 0}, "workflow": {"recommended_action": "send", "dispatch_recommended_action": "send", "workflow_state": "ready_to_send"}, "artifacts": {}, "slot": "early"},
            "workflow_linkage": {},
        }

    def list_report_delivery_surfaces(self, **kwargs: object) -> list[dict]:
        return [self.get_active_report_delivery_surface(**kwargs)]

    def get_bundle_graph(self, bundle_id: str) -> dict | None:
        boundary_mode = {
            "bundle-late": "same_day_close",
            "bundle-ai_tech": "candidate_only",
            "bundle-commodities": "candidate_only",
            "bundle-macro": "candidate_only",
        }.get(bundle_id)
        if boundary_mode is None:
            return None
        return {
            "bundle": {
                "bundle_id": bundle_id,
                "slot": "late" if bundle_id == "bundle-late" else "early",
                "section_key": bundle_id,
                "summary": bundle_id,
                "payload_json": {
                    "llm_role_policy": {
                        "policy_version": "fsj_llm_role_policy_v1",
                        "boundary_mode": boundary_mode,
                        "deterministic_owner_fields": ["judgment.action"],
                        "forbidden_decisions": ["declare_close_final_confirmation"],
                        "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                    }
                },
            }
        }


def test_store_build_operator_board_surface_uses_canonical_facade(monkeypatch) -> None:
    store = _BoardStore()
    monkeypatch.setattr(_module, "FSJStore", lambda: store)
    payload = store.build_operator_board_surface(business_date="2099-04-22", history_limit=1)
    assert payload["main"]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["main"]["review_summary"]["go_no_go_decision"] == "GO"
    assert payload["llm_lineage_summary"]["aggregate"]["overall_status"] == "degraded"
    assert payload["llm_role_policy_review"]["aggregate"]["policy_versions"] == ["fsj_llm_role_policy_v1"]
    assert payload["llm_role_policy_review"]["aggregate"]["override_precedence"] == ["deterministic_input_contract", "validated_llm_text_fields_only"]
    assert payload["board_rows"]["aggregate"]["status_semantic_counts"] == {"ready": 3, "review": 1}
    assert payload["board_rows"]["aggregate"]["dispatch_state_counts"] == {"dispatch_succeeded": 3, "dispatch_failed": 1}
    assert payload["board_rows"]["aggregate"]["strongest_slot_counts"] == {"early": 3, "late": 1}
    assert payload["board_rows"]["aggregate"]["failure_taxonomy_counts"] == {"hold_review": 1}
    assert payload["board_rows"]["support"]["commodities"]["blocking_reason"] == "bundle_missing"
    assert payload["board_state_source_summary"]["aggregate"]["reported_subject_count"] == 4
    assert payload["board_state_source_summary"]["aggregate"]["subjects_with_blocking_reason_source"] == ["support:commodities"]
    assert payload["support"]["macro"]["artifact"]["artifact_id"] == "macro-artifact"
    assert payload["support"]["macro"]["review_summary"]["go_no_go_decision"] == "GO"
    assert payload["history"][0]["artifact"]["artifact_id"] == "main-artifact"


def test_store_build_operator_board_surface_projects_review_held_db_candidate_summary(monkeypatch) -> None:
    class _Helper:
        def list_db_delivery_candidates(self, **_: object) -> list[dict]:
            return [
                {"artifact": {"artifact_id": "artifact-selected"}, "delivery_manifest": {"artifact_id": "artifact-selected", "package_state": "ready", "ready_for_delivery": False, "quality_gate": {"score": 93, "blocker_count": 1, "warning_count": 0, "late_contract_mode": "provisional_close_only"}, "slot_evaluation": {"strongest_slot": "late"}}, "report_evaluation": {"summary": {"slot_scores": {"early": 88, "mid": 90, "late": 93}}}},
                {"artifact": {"artifact_id": "artifact-current"}, "delivery_manifest": {"artifact_id": "artifact-current", "package_state": "ready", "ready_for_delivery": False, "quality_gate": {"score": 91, "blocker_count": 1, "warning_count": 1, "late_contract_mode": "provisional_close_only"}, "slot_evaluation": {"strongest_slot": "late"}}, "report_evaluation": {"summary": {"slot_scores": {"early": 86, "mid": 88, "late": 91}}}},
            ]

        def summarize_candidate(self, candidate: dict) -> dict:
            artifact_id = candidate["artifact"]["artifact_id"]
            if artifact_id == "artifact-selected":
                return {"artifact_id": artifact_id, "ready_for_delivery": False, "recommended_action": "send_review", "selection_reason": "best_available_candidate provisional_close_only_requires_review"}
            return {"artifact_id": artifact_id, "ready_for_delivery": False, "recommended_action": "send_review", "selection_reason": "best_available_candidate provisional_close_only_requires_review"}

    monkeypatch.setattr("ifa_data_platform.fsj.report_dispatch.MainReportDeliveryDispatchHelper", _Helper)
    payload = _ActualBoardStore().build_operator_board_surface(business_date="2099-04-22", history_limit=2)

    summary = payload["db_candidate_fleet_summary"]
    assert summary["subject"] == "main"
    assert summary["verdict"] == "review_held"
    assert summary["reason_code"] == "review_held_selected_candidate_differs_from_current"
    assert summary["current_artifact_id"] == "artifact-current"
    assert summary["selected_artifact_id"] == "artifact-selected"
    assert summary["best_candidate_artifact_id"] == "artifact-selected"
    assert summary["selected_matches_best"] is True
    assert summary["current_matches_best"] is False
    assert payload["db_candidates"][0]["artifact_id"] == "artifact-selected"
    assert payload["db_candidate_history_summary"][0]["subject"] == "history:1"
    assert payload["db_candidate_history_summary"][0]["verdict"] == "review_held"
    assert payload["db_candidate_history_summary"][0]["current_artifact_id"] == "artifact-current"
    assert payload["db_candidate_history_summary"][0]["canonical_lifecycle_state"] == "failed"
    assert payload["db_candidate_history_summary"][0]["canonical_lifecycle_reason"] == "dispatch_receipt_failed"
    assert payload["db_candidate_history_summary"][0]["dispatch_state"] == "dispatch_failed"
    assert payload["board_rows"]["main"]["status_semantic"] == "held"
    assert payload["board_rows"]["main"]["blocking_reason"] == "dispatch_receipt_failed"
    assert payload["board_rows"]["history"][0]["status_semantic"] == "held"
    assert payload["db_candidate_history_summary"][0]["dispatch_receipt_channel"] == "telegram_document"
    assert payload["db_candidate_history_summary"][0]["dispatch_receipt_error"] == "429 rate limit"


def test_store_build_operator_board_surface_projects_better_ready_candidate_mismatch(monkeypatch) -> None:
    class _ReadyHelper:
        def list_db_delivery_candidates(self, **_: object) -> list[dict]:
            return [
                {"artifact": {"artifact_id": "artifact-ready-better"}, "delivery_manifest": {"artifact_id": "artifact-ready-better", "package_state": "ready", "ready_for_delivery": True, "quality_gate": {"score": 96, "blocker_count": 0, "warning_count": 0}, "slot_evaluation": {"strongest_slot": "late"}}, "report_evaluation": {"summary": {"slot_scores": {"early": 90, "mid": 94, "late": 96}}}},
                {"artifact": {"artifact_id": "artifact-current"}, "delivery_manifest": {"artifact_id": "artifact-current", "package_state": "ready", "ready_for_delivery": False, "quality_gate": {"score": 91, "blocker_count": 1, "warning_count": 1}, "slot_evaluation": {"strongest_slot": "late"}}, "report_evaluation": {"summary": {"slot_scores": {"early": 86, "mid": 88, "late": 91}}}},
            ]

        def summarize_candidate(self, candidate: dict) -> dict:
            artifact_id = candidate["artifact"]["artifact_id"]
            if artifact_id == "artifact-ready-better":
                return {
                    "artifact_id": artifact_id,
                    "rank": 1,
                    "ready_for_delivery": True,
                    "recommended_action": "send",
                    "selection_reason": "best_ready_candidate strongest_slot=late qa_score=96",
                }
            return {
                "artifact_id": artifact_id,
                "rank": 2,
                "ready_for_delivery": False,
                "recommended_action": "send_review",
                "selection_reason": "best_available_candidate provisional_close_only_requires_review",
            }

    monkeypatch.setattr("ifa_data_platform.fsj.report_dispatch.MainReportDeliveryDispatchHelper", _ReadyHelper)
    payload = _ActualBoardStore().build_operator_board_surface(business_date="2099-04-22", history_limit=2)

    summary = payload["db_candidate_fleet_summary"]
    assert summary["subject"] == "main"
    assert summary["verdict"] == "mismatch"
    assert summary["reason_code"] == "selection_state_diverged_from_best_ready_candidate"
    assert summary["current_artifact_id"] == "artifact-current"
    assert summary["selected_artifact_id"] == "artifact-selected"
    assert summary["best_candidate_artifact_id"] == "artifact-ready-better"
    assert summary["selected_matches_best"] is False
    assert summary["current_matches_best"] is False
    assert summary["best_candidate_recommended_action"] == "send"
    assert summary["best_candidate_selection_reason"] == "best_ready_candidate strongest_slot=late qa_score=96"
    assert summary["summary_line"] == (
        "Current MAIN artifact artifact-current and selected artifact artifact-selected "
        "both trail better ready DB candidate artifact-ready-better."
    )
    assert payload["db_candidates"][0]["artifact_id"] == "artifact-ready-better"
    assert payload["db_candidate_history_summary"][0]["subject"] == "history:1"
    assert payload["db_candidate_history_summary"][0]["verdict"] == "mismatch"
    assert payload["db_candidate_history_summary"][0]["reason_code"] == "selection_state_diverged_from_best_ready_candidate"
    assert payload["db_candidate_history_summary"][0]["best_candidate_artifact_id"] == "artifact-ready-better"


@pytest.mark.parametrize("database_url,expected_error", [(None, "DATABASE_URL must be set explicitly"), (LIVE_DB_URL, "canonical/live DB")])
def test_build_board_payload_blocks_default_store_live_db_paths_under_pytest(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str | None,
    expected_error: str,
) -> None:
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)
    _clear_caches()

    with pytest.raises(LiveIsolationError, match=expected_error):
        _build_board_payload(business_date="2099-04-22", history_limit=1)
