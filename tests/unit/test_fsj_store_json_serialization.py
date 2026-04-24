from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from ifa_data_platform.fsj.store import FSJStore


def test_json_dumps_normalizes_non_native_json_types() -> None:
    store = FSJStore()

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

    store = FSJStore()
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
    assert summary["state"]["next_step"] == "operator_review_selected_candidate"
    assert summary["state"]["selection_reason"] == "best_ready_candidate strongest_slot=late qa_score=93"
    assert summary["state"]["dispatch_selected_artifact_id"] == "artifact-selected"
    assert summary["state"]["send_blockers"] == ["selected_candidate_differs_from_current"]


def test_report_package_surface_projection_preserves_review_and_send_package_pointers() -> None:
    store = FSJStore()
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
    assert summary["workflow_handoff"]["state"]["workflow_state"] == "selected_candidate_mismatch"
