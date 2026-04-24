from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_send_dispatch_failure_status.py"
_spec = importlib.util.spec_from_file_location("fsj_send_dispatch_failure_status_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
_classify_dispatch_failure = _module._classify_dispatch_failure
_print_text = _module._print_text
build_dispatch_failure_payload = _module.build_dispatch_failure_payload


def test_classify_dispatch_failure_reports_ready_to_dispatch(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    required = {
        "delivery_manifest_path": pkg / "delivery_manifest.json",
        "send_manifest_path": pkg / "send_manifest.json",
        "review_manifest_path": pkg / "review_manifest.json",
        "workflow_manifest_path": pkg / "workflow_manifest.json",
        "delivery_zip_path": pkg / "delivery.zip",
    }
    for path in required.values():
        path.write_text("{}", encoding="utf-8")

    surface = {
        "artifact": {"artifact_id": "artifact-ready"},
        "selected_handoff": {"selected_is_current": True},
        "state": {
            "recommended_action": "send",
            "workflow_state": "ready_to_send",
            "send_ready": True,
            "review_required": False,
            "send_blockers": [],
            "next_step": "send_selected_package_to_primary_channel",
        },
        "operator_go_no_go": {"decision": "GO"},
        "send_manifest": {"send_blockers": []},
        "review_manifest": {"blocking_items": []},
        "package_paths": {key: str(value) for key, value in required.items()},
    }

    summary = _classify_dispatch_failure(surface)

    assert summary["dispatch_posture"] == "ready_to_dispatch"
    assert summary["failure_reasons"] == []
    assert summary["missing_required_artifacts"] == []
    assert summary["channel_delivery_truth"] == "unknown_not_modeled"


def test_classify_dispatch_failure_reports_switch_package_and_missing_artifacts(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "review_manifest.json").write_text("{}", encoding="utf-8")

    surface = {
        "artifact": {"artifact_id": "artifact-current"},
        "selected_handoff": {"selected_is_current": False},
        "state": {
            "recommended_action": "send",
            "workflow_state": "superseded_by_better_candidate",
            "send_ready": False,
            "review_required": False,
            "send_blockers": ["current_package_not_selected"],
            "dispatch_selected_artifact_id": "artifact-selected",
            "next_step": "switch_to_selected_package_and_do_not_send_current",
        },
        "operator_go_no_go": {"decision": "NO_GO"},
        "send_manifest": {"send_blockers": ["current_package_not_selected"]},
        "review_manifest": {"blocking_items": []},
        "package_paths": {
            "delivery_manifest_path": str(pkg / "delivery_manifest.json"),
            "send_manifest_path": str(pkg / "send_manifest.json"),
            "review_manifest_path": str(pkg / "review_manifest.json"),
            "workflow_manifest_path": str(pkg / "workflow_manifest.json"),
            "delivery_zip_path": str(pkg / "delivery.zip"),
        },
    }

    summary = _classify_dispatch_failure(surface)

    assert summary["dispatch_posture"] == "artifact_integrity_failed"
    assert "current_package_not_selected" in summary["failure_reasons"]
    assert "required_delivery_artifacts_missing" in summary["failure_reasons"]
    assert sorted(summary["missing_required_artifacts"]) == [
        "delivery_manifest_path",
        "delivery_zip_path",
        "send_manifest_path",
        "workflow_manifest_path",
    ]


def test_build_dispatch_failure_payload_uses_main_status_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        _module,
        "build_main_status_payload",
        lambda **_: {
            "business_date": "2099-04-23",
            "resolution": {"mode": "explicit_business_date", "business_date": "2099-04-23"},
            "active_surface": {
                "artifact": {"artifact_id": "artifact-1"},
                "selected_handoff": {"selected_is_current": True},
                "state": {"recommended_action": "hold", "send_ready": False, "review_required": False, "send_blockers": ["recommended_action_hold"]},
                "operator_go_no_go": {"decision": "NO_GO"},
                "send_manifest": {"send_blockers": ["recommended_action_hold"]},
                "review_manifest": {"blocking_items": []},
                "package_paths": {},
                "review_summary": {"go_no_go_decision": "NO_GO"},
            },
            "history": [],
        },
    )

    payload = build_dispatch_failure_payload(business_date="2099-04-23", history_limit=3)

    assert payload["business_date"] == "2099-04-23"
    assert payload["dispatch_failure"]["dispatch_posture"] == "artifact_integrity_failed"
    assert "recommended_action_hold" in payload["dispatch_failure"]["failure_reasons"]


def test_print_text_emits_dispatch_failure_summary(capsys) -> None:
    payload = {
        "business_date": "2099-04-23",
        "resolution": {
            "mode": "latest_active_lookup",
            "requested_slot": "late",
            "resolved_artifact_id": "artifact-active",
        },
        "active_surface": {
            "package_paths": {
                "delivery_manifest_path": "/tmp/pkg/delivery_manifest.json",
                "send_manifest_path": "/tmp/pkg/send_manifest.json",
                "review_manifest_path": "/tmp/pkg/review_manifest.json",
                "workflow_manifest_path": "/tmp/pkg/workflow_manifest.json",
                "operator_review_bundle_path": "/tmp/pkg/operator_review_bundle.json",
                "operator_review_readme_path": "/tmp/pkg/OPERATOR_REVIEW.md",
                "delivery_zip_path": "/tmp/pkg.zip",
            },
        },
        "history": [{}, {}],
        "dispatch_failure": {
            "dispatch_posture": "review_required",
            "failure_reasons": ["manual_review_required", "operator_go_no_go_review"],
            "missing_required_artifacts": [],
            "action_summary": "operator review is required before dispatch; inspect review manifest and operator review bundle",
            "channel_delivery_truth": "unknown_not_modeled",
            "current_artifact_id": "artifact-active",
            "dispatch_selected_artifact_id": "artifact-selected",
            "selected_is_current": True,
            "recommended_action": "send_review",
            "workflow_state": "review_required",
            "send_ready": False,
            "review_required": True,
            "go_no_go_decision": "REVIEW",
            "next_step": "review_current_package_then_send_if_accepted",
            "artifact_checks": [
                {"artifact": "delivery_manifest_path", "required": True, "exists": True, "path": "/tmp/pkg/delivery_manifest.json"},
                {"artifact": "send_manifest_path", "required": True, "exists": True, "path": "/tmp/pkg/send_manifest.json"},
            ],
        },
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "dispatch_posture=review_required" in output
    assert "failure_reasons=manual_review_required,operator_go_no_go_review" in output
    assert "channel_delivery_truth=unknown_not_modeled" in output
    assert "go_no_go_decision=REVIEW" in output
    assert "operator_review_bundle_path=/tmp/pkg/operator_review_bundle.json" in output
    assert "artifact_check_1=delivery_manifest_path|required=True|exists=True|path=/tmp/pkg/delivery_manifest.json" in output
    assert "history_count=2" in output


def test_main_cli_json_contract_handles_missing_latest(monkeypatch, capsys) -> None:
    class _DummyStore:
        def get_latest_active_report_operator_review_surface(self, **_: object) -> None:
            return None

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())
    monkeypatch.setattr("sys.argv", ["fsj_send_dispatch_failure_status.py", "--latest", "--format", "json"])

    _module.main()
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload["dispatch_failure"]["dispatch_posture"] == "no_active_artifact"
    assert payload["dispatch_failure"]["channel_delivery_truth"] == "unknown_not_modeled"


def test_main_cli_json_contract_uses_latest_active_surface(monkeypatch, capsys) -> None:
    surface = {
        "artifact": {
            "artifact_id": "artifact-active",
            "report_run_id": "run-active",
            "business_date": "2099-04-23",
            "status": "active",
        },
        "package_state": {"slot_evaluation": {"strongest_slot": "late"}},
        "selected_handoff": {"selected_is_current": True},
        "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "send_ready": True, "review_required": False, "send_blockers": []},
        "operator_go_no_go": {"decision": "GO"},
        "send_manifest": {"send_blockers": []},
        "review_manifest": {"blocking_items": []},
        "package_paths": {},
        "review_summary": {"go_no_go_decision": "GO"},
    }

    class _DummyStore:
        def get_latest_active_report_operator_review_surface(self, **kwargs: object) -> dict:
            assert kwargs["agent_domain"] == "main"
            assert kwargs["artifact_family"] == "main_final_report"
            assert kwargs["strongest_slot"] == "late"
            return surface

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())
    monkeypatch.setattr(
        _module,
        "build_dispatch_failure_payload",
        lambda **kwargs: {
            "business_date": kwargs["business_date"],
            "resolution": kwargs["resolution"],
            "active_surface": surface,
            "history": [],
            "dispatch_failure": {"dispatch_posture": "ready_to_dispatch", "channel_delivery_truth": "unknown_not_modeled"},
        },
    )
    monkeypatch.setattr("sys.argv", ["fsj_send_dispatch_failure_status.py", "--latest", "--slot", "late", "--format", "json"])

    _module.main()
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload["resolution"]["resolved_artifact_id"] == "artifact-active"
    assert payload["resolution"]["resolved_strongest_slot"] == "late"
    assert payload["dispatch_failure"]["dispatch_posture"] == "ready_to_dispatch"


def test_main_cli_rejects_unknown_slot(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["fsj_send_dispatch_failure_status.py", "--latest", "--slot", "close"])
    with pytest.raises(SystemExit):
        _module.main()
