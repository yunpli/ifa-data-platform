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


def test_surface_summary_exposes_support_handoff_state_and_manifest_pointers() -> None:
    surface = {
        "workflow_handoff": {
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
                "workflow_state": "ready_to_send",
                "send_ready": True,
                "review_required": False,
            },
            "manifest_pointers": {
                "send_manifest_path": "/tmp/pkg/send_manifest.json",
                "workflow_manifest_path": "/tmp/pkg/workflow_manifest.json",
            },
        }
    }

    summary = _surface_summary(surface, store=type("_Store", (), {"report_workflow_handoff_from_surface": lambda self, value: value["workflow_handoff"]})())

    assert summary["artifact"]["artifact_id"] == "artifact-macro-active"
    assert summary["selected_handoff"]["selected_artifact_id"] == "artifact-macro-active"
    assert summary["state"]["workflow_state"] == "ready_to_send"
    assert summary["manifest_pointers"]["send_manifest_path"] == "/tmp/pkg/send_manifest.json"



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
                "workflow_state": "review_required",
                "send_ready": False,
                "review_required": True,
                "package_state": "ready",
                "ready_for_delivery": True,
                "qa_score": 94,
                "blocker_count": 0,
                "warning_count": 2,
            },
            "manifest_pointers": {
                "delivery_manifest_path": "/tmp/pkg/delivery_manifest.json",
                "send_manifest_path": "/tmp/pkg/send_manifest.json",
                "review_manifest_path": "/tmp/pkg/review_manifest.json",
                "workflow_manifest_path": "/tmp/pkg/workflow_manifest.json",
                "package_index_path": "/tmp/pkg/package_index.json",
                "delivery_zip_path": "/tmp/pkg.zip",
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
    assert "send_manifest_path=/tmp/pkg/send_manifest.json" in output
    assert "history_count=2" in output



def test_build_status_payload_includes_resolution_metadata(monkeypatch) -> None:
    class _DummyStore:
        def get_active_report_delivery_surface(self, **_: object) -> dict:
            return {
                "artifact": {"artifact_id": "artifact-1", "report_run_id": "run-1", "business_date": "2099-04-22", "status": "active"},
                "delivery_package": {"package_state": "ready", "ready_for_delivery": True, "quality_gate": {}, "workflow": {}, "artifacts": {}},
                "workflow_linkage": {},
            }

        def list_report_delivery_surfaces(self, **_: object) -> list[dict]:
            return []

        def report_workflow_handoff_from_surface(self, surface: dict) -> dict:
            return {
                "artifact": {"artifact_id": surface["artifact"]["artifact_id"]},
                "selected_handoff": {},
                "state": {},
                "manifest_pointers": {},
                "version_pointers": {},
            }

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



def test_resolve_latest_support_business_date_uses_store_latest_delivery_surface(monkeypatch) -> None:
    class _DummyStore:
        def get_latest_active_report_delivery_surface(self, **kwargs: object) -> dict:
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
                "delivery_package": {
                    "slot": "early",
                },
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



def test_resolve_latest_support_business_date_rejects_unknown_slot() -> None:
    with pytest.raises(ValueError, match="unsupported slot"):
        resolve_latest_support_business_date(agent_domain="macro", slot="mid")



def test_resolve_latest_support_business_date_rejects_unknown_domain() -> None:
    with pytest.raises(ValueError, match="unsupported agent_domain"):
        resolve_latest_support_business_date(agent_domain="rates")
