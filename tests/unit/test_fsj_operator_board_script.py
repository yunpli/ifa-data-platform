from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from ifa_data_platform.fsj.store import FSJStore


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_operator_board.py"
_spec = importlib.util.spec_from_file_location("fsj_operator_board_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
_build_board_payload = _module.build_board_payload
_print_text = _module._print_text


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
        return {
            "artifact": {"artifact_id": artifact.get("artifact_id"), "report_run_id": artifact.get("report_run_id"), "business_date": artifact.get("business_date"), "status": artifact.get("status")},
            "selected_handoff": {"selected_artifact_id": artifact.get("artifact_id"), "selected_is_current": True},
            "state": {"recommended_action": workflow.get("recommended_action"), "dispatch_recommended_action": workflow.get("dispatch_recommended_action"), "workflow_state": workflow.get("workflow_state"), "package_state": delivery_package.get("package_state"), "qa_score": quality_gate.get("score"), "blocker_count": quality_gate.get("blocker_count"), "warning_count": quality_gate.get("warning_count"), "qa_axes": dict(quality_gate.get("qa_axes") or {})},
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
        return {
            "artifact": handoff["artifact"],
            "selected_handoff": handoff["selected_handoff"],
            "state": handoff["state"],
            "package_paths": package_surface["package_paths"],
            "package_versions": package_surface["package_versions"],
            "package_state": {"package_state": handoff["state"].get("package_state")},
            "workflow_handoff": handoff,
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
            "operator_go_no_go": {"decision": "GO"},
            "review_manifest": {},
            "send_manifest": {},
            "review_summary": {"go_no_go_decision": "GO", "llm_lineage_status": lineage_status, "llm_lineage_summary": lineage_summary["summary_line"]},
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
            "llm_lineage_summary": {
                "main": main_review["llm_lineage_summary"] if main_review else None,
                "support": {domain: (review["llm_lineage_summary"] if review else None) for domain, review in support_reviews.items()},
                "history": [review["llm_lineage_summary"] for review in history_reviews],
                "aggregate": {
                    "overall_status": "degraded",
                    "reported_subject_count": 5,
                    "attention_subjects": ["support:commodities"],
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
                "main": {"subject": "main", "posture": "ready_to_send", "send_ready": True, "review_required": False, "blocked": False, "lineage_attention": False, "needs_attention": False},
                "support": {
                    "ai_tech": {"subject": "support:ai_tech", "posture": "ready_to_send", "send_ready": True, "review_required": False, "blocked": False, "lineage_attention": False, "needs_attention": False},
                    "commodities": {"subject": "support:commodities", "posture": "review_required", "send_ready": False, "review_required": True, "blocked": False, "lineage_attention": True, "needs_attention": True},
                    "macro": {"subject": "support:macro", "posture": "ready_to_send", "send_ready": True, "review_required": False, "blocked": False, "lineage_attention": False, "needs_attention": False},
                },
                "aggregate": {
                    "overall_posture": "review_required",
                    "ready_subjects": ["main", "support:ai_tech", "support:macro"],
                    "review_required_subjects": ["support:commodities"],
                    "blocked_subjects": [],
                    "attention_subjects": ["support:commodities"],
                },
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
    assert payload["llm_lineage_summary"]["aggregate"]["overall_status"] == "degraded"
    assert payload["llm_lineage_summary"]["aggregate"]["attention_subjects"] == ["support:commodities"]
    assert payload["llm_role_policy_review"]["aggregate"]["policy_versions"] == ["fsj_llm_role_policy_v1"]
    assert payload["llm_role_policy_review"]["aggregate"]["override_precedence"] == ["deterministic_input_contract", "validated_llm_text_fields_only"]
    assert payload["llm_role_policy_review"]["aggregate"]["slot_boundary_modes_by_subject"]["main"] == {"late": "same_day_close"}
    assert payload["board_readiness_summary"]["aggregate"]["overall_posture"] == "review_required"
    assert payload["board_readiness_summary"]["aggregate"]["review_required_subjects"] == ["support:commodities"]
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
        },
        "support": {
            "label": "support",
            "scope_count": 3,
            "reported_day_count": 3,
            "hold_count": 3,
            "fallback_count": 0,
            "mismatch_count": 0,
            "qa_attention_count": 1,
        },
    }
    assert payload["fleet_drift_digest_line"] == "7d fleet drift: main hold 1/1 (1 scope) | fallback 0/1 | mismatch 0/1 | qa_attn 0/1 || support hold 3/3 (3 scope) | fallback 0/3 | mismatch 0/3 | qa_attn 1/3"


def test_build_board_payload_can_resolve_latest_business_date(monkeypatch) -> None:
    store = _BoardStore()
    monkeypatch.setattr(_module, "FSJStore", lambda: store)
    payload = _build_board_payload(business_date=None, history_limit=1)

    assert payload["resolution"]["mode"] == "latest_active_lookup"
    assert payload["business_date"] == "2099-04-22"


def test_print_text_emits_operator_board_summary(capsys) -> None:
    payload = {
        "business_date": "2099-04-22",
        "resolution": {"mode": "explicit_business_date", "business_date": "2099-04-22"},
        "main": {"artifact": {"artifact_id": "main-artifact"}, "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready"}, "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=1/1]", "models": ["grok41_thinking"], "token_totals": {"total_tokens": 341}, "estimated_cost_usd": None}, "llm_role_policy": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"late": "same_day_close"}}},
        "support": {
            "ai_tech": {"artifact": {"artifact_id": "ai-tech-artifact"}, "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready"}, "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=1/1]", "models": ["grok41_thinking"], "token_totals": {"total_tokens": 287}, "estimated_cost_usd": None}, "llm_role_policy": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"early": "candidate_only"}}},
            "commodities": {"artifact": {"artifact_id": "commodities-artifact"}, "state": {"recommended_action": "send_review", "workflow_state": "review_required", "package_state": "ready"}, "llm_lineage_summary": {"status": "degraded", "summary_line": "degraded [applied=1/1]", "models": ["gemini31_pro_jmr"], "token_totals": {"total_tokens": 355}, "estimated_cost_usd": None}, "llm_role_policy": {"override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"], "slot_boundary_modes": {"late": "candidate_only"}}},
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
            }
        ],
        "llm_lineage_summary": {
            "main": {"status": "applied", "summary_line": "applied [applied=1/1]", "models": ["grok41_thinking"], "token_totals": {"total_tokens": 341}, "estimated_cost_usd": None},
            "support": {
                "ai_tech": {"status": "applied", "summary_line": "applied [applied=1/1]", "models": ["grok41_thinking"], "token_totals": {"total_tokens": 287}, "estimated_cost_usd": None},
                "commodities": {"status": "degraded", "summary_line": "degraded [applied=1/1]", "models": ["gemini31_pro_jmr"], "token_totals": {"total_tokens": 355}, "estimated_cost_usd": None},
                "macro": None,
            },
            "aggregate": {"overall_status": "degraded", "attention_subjects": ["support:commodities"], "reported_subject_count": 3, "models": ["gemini31_pro_jmr", "grok41_thinking"], "total_tokens": 983, "estimated_cost_usd": None, "uncosted_bundle_count": 3},
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
                "blocked_subjects": [],
                "attention_subjects": ["support:commodities"],
            },
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
            },
            "support": {
                "label": "support",
                "scope_count": 3,
                "reported_day_count": 3,
                "hold_count": 3,
                "fallback_count": 0,
                "mismatch_count": 0,
                "qa_attention_count": 1,
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
    assert "main_llm_lineage_status=applied" in output
    assert "main_llm_models=grok41_thinking" in output
    assert "main_llm_total_tokens=341" in output
    assert "main_llm_override_precedence=deterministic_input_contract>validated_llm_text_fields_only" in output
    assert "main_llm_slot_boundary_modes=late:same_day_close" in output
    assert "support_ai_tech_artifact_id=ai-tech-artifact" in output
    assert "support_commodities_recommended_action=send_review" in output
    assert "support_commodities_llm_lineage_status=degraded" in output
    assert "support_commodities_llm_models=gemini31_pro_jmr" in output
    assert "support_commodities_llm_total_tokens=355" in output
    assert "support_commodities_llm_slot_boundary_modes=late:candidate_only" in output
    assert "fleet_llm_lineage_status=degraded" in output
    assert "fleet_llm_attention_subjects=support:commodities" in output
    assert "fleet_llm_models=gemini31_pro_jmr,grok41_thinking" in output
    assert "fleet_llm_total_tokens=983" in output
    assert "fleet_llm_uncosted_bundle_count=3" in output
    assert "fleet_llm_policy_versions=fsj_llm_role_policy_v1" in output
    assert "fleet_llm_override_precedence=deterministic_input_contract>validated_llm_text_fields_only" in output
    assert "fleet_llm_attention_policy_subjects=main,support:ai_tech,support:commodities" in output
    assert "fleet_board_posture=review_required" in output
    assert "fleet_drift_digest_line=7d fleet drift: main hold 1/1 (1 scope) | fallback 0/1 | mismatch 0/1 | qa_attn 0/1 || support hold 3/3 (3 scope) | fallback 0/3 | mismatch 0/3 | qa_attn 1/3" in output
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
    assert "db_candidate_history_count=1" in output
    assert "db_candidate_history_1_subject=history:1" in output
    assert "db_candidate_history_1_reason=better_ready_candidate_selected_current_outdated" in output
    assert "fleet_review_subjects=support:commodities" in output
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
                        }
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
