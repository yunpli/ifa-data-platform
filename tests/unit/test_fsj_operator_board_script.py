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


class _DummyHelper:
    def list_db_delivery_candidates(self, **_: object) -> list[dict]:
        return [{"artifact": {"artifact_id": "main-artifact"}, "delivery_manifest": {"artifact_id": "main-artifact", "package_state": "ready", "ready_for_delivery": True, "quality_gate": {"score": 100, "blocker_count": 0, "warning_count": 0}, "slot_evaluation": {"strongest_slot": "late"}}, "report_evaluation": {"summary": {"slot_scores": {"early": 100, "mid": 100, "late": 100}}}, "source": "db_active_delivery_surface"}]

    def summarize_candidate(self, candidate: dict) -> dict:
        return {"artifact_id": candidate["artifact"]["artifact_id"], "recommended_action": "send", "selection_reason": "best_ready_candidate strongest_slot=late qa_score=100"}


def test_build_board_payload_composes_main_and_support_views(monkeypatch) -> None:
    store = _DummyStore()
    monkeypatch.setattr(_module, "FSJStore", lambda: store)
    monkeypatch.setattr(_module, "MainReportDeliveryDispatchHelper", lambda: _DummyHelper())

    payload = _build_board_payload(business_date="2099-04-22", history_limit=2)

    assert payload["business_date"] == "2099-04-22"
    assert payload["main"]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["support"]["macro"]["artifact"]["artifact_id"] == "macro-artifact"
    assert payload["support"]["commodities"]["artifact"]["artifact_id"] == "commodities-artifact"
    assert payload["support"]["ai_tech"]["artifact"]["artifact_id"] == "ai_tech-artifact"
    assert payload["history"][0]["artifact"]["artifact_id"] == "main-artifact"
    assert payload["db_candidates"][0]["artifact_id"] == "main-artifact"


def test_build_board_payload_can_resolve_latest_business_date(monkeypatch) -> None:
    store = _DummyStore()
    monkeypatch.setattr(_module, "FSJStore", lambda: store)
    monkeypatch.setattr(_module, "MainReportDeliveryDispatchHelper", lambda: _DummyHelper())

    payload = _build_board_payload(business_date=None, history_limit=1)

    assert payload["resolution"]["mode"] == "latest_active_lookup"
    assert payload["business_date"] == "2099-04-22"


def test_print_text_emits_operator_board_summary(capsys) -> None:
    payload = {
        "business_date": "2099-04-22",
        "resolution": {"mode": "explicit_business_date", "business_date": "2099-04-22"},
        "main": {"artifact": {"artifact_id": "main-artifact"}, "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready"}},
        "support": {
            "ai_tech": {"artifact": {"artifact_id": "ai-tech-artifact"}, "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready"}},
            "commodities": {"artifact": {"artifact_id": "commodities-artifact"}, "state": {"recommended_action": "send_review", "workflow_state": "review_required", "package_state": "ready"}},
            "macro": None,
        },
        "history": [{}, {}],
        "db_candidates": [{}, {}],
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "business_date=2099-04-22" in output
    assert "resolution_mode=explicit_business_date" in output
    assert "main_artifact_id=main-artifact" in output
    assert "main_recommended_action=send" in output
    assert "support_ai_tech_artifact_id=ai-tech-artifact" in output
    assert "support_commodities_recommended_action=send_review" in output
    assert "support_macro=NONE" in output
    assert "candidate_count=2" in output
