from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


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
                "delivery_package": {"package_state": "ready", "ready_for_delivery": True, "quality_gate": {"score": 100, "blocker_count": 0, "warning_count": 0}, "workflow": {"recommended_action": "send", "dispatch_recommended_action": "send", "workflow_state": "ready_to_send"}, "artifacts": {}},
                "workflow_linkage": {},
            }
        return {
            "artifact": {"artifact_id": f"{domain}-artifact", "report_run_id": f"{domain}-run", "business_date": kwargs["business_date"], "status": "active"},
            "delivery_package": {"package_state": "ready", "ready_for_delivery": True, "quality_gate": {"score": 95, "blocker_count": 0, "warning_count": 0}, "workflow": {"recommended_action": "send", "dispatch_recommended_action": "send", "workflow_state": "ready_to_send"}, "artifacts": {}, "slot": "early"},
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
            "state": {"recommended_action": workflow.get("recommended_action"), "dispatch_recommended_action": workflow.get("dispatch_recommended_action"), "workflow_state": workflow.get("workflow_state"), "package_state": delivery_package.get("package_state"), "qa_score": quality_gate.get("score"), "blocker_count": quality_gate.get("blocker_count"), "warning_count": quality_gate.get("warning_count")},
            "manifest_pointers": {},
            "version_pointers": {},
        }

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
        return {
            "artifact": handoff["artifact"],
            "selected_handoff": handoff["selected_handoff"],
            "state": handoff["state"],
            "package_paths": package_surface["package_paths"],
            "package_versions": package_surface["package_versions"],
            "package_state": {"package_state": handoff["state"].get("package_state")},
            "workflow_handoff": handoff,
            "llm_lineage_summary": lineage_summary,
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
    assert payload["llm_lineage_summary"]["aggregate"]["overall_status"] == "degraded"
    assert payload["llm_lineage_summary"]["aggregate"]["attention_subjects"] == ["support:commodities"]
    assert payload["board_readiness_summary"]["aggregate"]["overall_posture"] == "review_required"
    assert payload["board_readiness_summary"]["aggregate"]["review_required_subjects"] == ["support:commodities"]


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
        "main": {"artifact": {"artifact_id": "main-artifact"}, "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready"}, "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=1/1]"}},
        "support": {
            "ai_tech": {"artifact": {"artifact_id": "ai-tech-artifact"}, "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready"}, "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=1/1]"}},
            "commodities": {"artifact": {"artifact_id": "commodities-artifact"}, "state": {"recommended_action": "send_review", "workflow_state": "review_required", "package_state": "ready"}, "llm_lineage_summary": {"status": "degraded", "summary_line": "degraded [applied=1/1]"}},
            "macro": None,
        },
        "history": [{}, {}],
        "db_candidates": [{}, {}],
        "llm_lineage_summary": {
            "main": {"status": "applied", "summary_line": "applied [applied=1/1]"},
            "support": {
                "ai_tech": {"status": "applied", "summary_line": "applied [applied=1/1]"},
                "commodities": {"status": "degraded", "summary_line": "degraded [applied=1/1]"},
                "macro": None,
            },
            "aggregate": {"overall_status": "degraded", "attention_subjects": ["support:commodities"], "reported_subject_count": 3},
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
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "business_date=2099-04-22" in output
    assert "resolution_mode=explicit_business_date" in output
    assert "main_artifact_id=main-artifact" in output
    assert "main_recommended_action=send" in output
    assert "main_llm_lineage_status=applied" in output
    assert "support_ai_tech_artifact_id=ai-tech-artifact" in output
    assert "support_commodities_recommended_action=send_review" in output
    assert "support_commodities_llm_lineage_status=degraded" in output
    assert "fleet_llm_lineage_status=degraded" in output
    assert "fleet_llm_attention_subjects=support:commodities" in output
    assert "fleet_board_posture=review_required" in output
    assert "fleet_review_subjects=support:commodities" in output
    assert "fleet_attention_subjects=support:commodities" in output
    assert "support_macro=NONE" in output
    assert "candidate_count=2" in output



def test_store_build_operator_board_surface_uses_canonical_facade(monkeypatch) -> None:
    store = _BoardStore()
    monkeypatch.setattr(_module, "FSJStore", lambda: store)
    payload = store.build_operator_board_surface(business_date="2099-04-22", history_limit=1)
    assert payload["main"]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["main"]["review_summary"]["go_no_go_decision"] == "GO"
    assert payload["llm_lineage_summary"]["aggregate"]["overall_status"] == "degraded"
    assert payload["support"]["macro"]["artifact"]["artifact_id"] == "macro-artifact"
    assert payload["support"]["macro"]["review_summary"]["go_no_go_decision"] == "GO"
    assert payload["history"][0]["artifact"]["artifact_id"] == "main-artifact"
