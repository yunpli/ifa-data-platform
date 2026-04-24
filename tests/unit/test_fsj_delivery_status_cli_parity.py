from __future__ import annotations

import importlib.util
import json
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAIN_MODULE_PATH = _REPO_ROOT / "scripts" / "fsj_main_delivery_status.py"
_SUPPORT_MODULE_PATH = _REPO_ROOT / "scripts" / "fsj_support_delivery_status.py"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


main_module = _load_module("fsj_main_delivery_status_parity_script", _MAIN_MODULE_PATH)
support_module = _load_module("fsj_support_delivery_status_parity_script", _SUPPORT_MODULE_PATH)


class _ParityStore:
    def __init__(self, *, domain: str) -> None:
        self.domain = domain

    def get_active_report_operator_review_surface(self, **kwargs: object) -> dict:
        assert kwargs["business_date"] == "2099-04-22"
        assert kwargs["artifact_family"] in {"main_final_report", "support_domain_report"}
        artifact_id = "main-artifact" if self.domain == "main" else f"{self.domain}-artifact"
        selected_artifact_id = f"{artifact_id}-selected"
        slot = "late" if self.domain == "main" else "early"
        return {
            "artifact": {
                "artifact_id": artifact_id,
                "report_run_id": f"{artifact_id}-run",
                "business_date": "2099-04-22",
                "status": "active",
                "artifact_family": kwargs["artifact_family"],
            },
            "selected_handoff": {
                "selected_artifact_id": selected_artifact_id,
                "selected_is_current": False,
            },
            "state": {
                "recommended_action": "send_review",
                "dispatch_recommended_action": "send",
                "workflow_state": "review_required",
                "send_ready": False,
                "review_required": True,
                "next_step": "operator_review_selected_candidate",
                "selection_reason": f"parity_candidate domain={self.domain} slot={slot}",
                "dispatch_selected_artifact_id": selected_artifact_id,
                "package_state": "ready",
                "ready_for_delivery": True,
                "qa_score": 94,
                "blocker_count": 0,
                "warning_count": 1,
            },
            "package_paths": {
                "delivery_manifest_path": f"/tmp/{artifact_id}/delivery_manifest.json",
                "send_manifest_path": f"/tmp/{artifact_id}/send_manifest.json",
                "review_manifest_path": f"/tmp/{artifact_id}/review_manifest.json",
                "workflow_manifest_path": f"/tmp/{artifact_id}/workflow_manifest.json",
                "package_index_path": f"/tmp/{artifact_id}/package_index.json",
                "delivery_zip_path": f"/tmp/{artifact_id}.zip",
                "operator_review_bundle_path": f"/tmp/{artifact_id}/operator_review_bundle.json",
            },
            "package_versions": {
                "operator_review_bundle_version": "operator_review_bundle.json",
            },
            "package_state": {
                "package_state": "ready",
                "ready_for_delivery": True,
                "slot_evaluation": {"strongest_slot": slot},
            },
            "artifact_lineage": {
                "artifact": {"artifact_id": artifact_id},
                "bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 0, "slots": [slot], "section_keys": ["mainline"]},
                "what_user_received": {"dispatch_state": "dispatch_succeeded", "channel": "telegram_document", "provider_message_id": f"msg-{artifact_id}"},
            },
            "workflow_handoff": {
                "artifact": {"artifact_id": artifact_id},
                "selected_handoff": {"selected_artifact_id": selected_artifact_id},
                "state": {"workflow_state": "review_required"},
            },
            "llm_lineage": {
                "artifact_id": artifact_id,
                "bundle_ids": [f"{artifact_id}-bundle"],
                "summary": {
                    "bundle_count": 1,
                    "applied_count": 1,
                    "degraded_count": 0,
                    "primary_applied_count": 1,
                    "fallback_applied_count": 0,
                    "operator_tags": [],
                },
                "bundles": [
                    {
                        "bundle_id": f"{artifact_id}-bundle",
                        "slot": slot,
                        "section_key": "mainline",
                        "applied": True,
                        "model_alias": "grok41_thinking",
                        "prompt_version": "fsj_v1",
                        "outcome": "primary_applied",
                    }
                ],
            },
            "llm_lineage_summary": {
                "status": "applied",
                "bundle_count": 1,
                "applied_count": 1,
                "primary_applied_count": 1,
                "fallback_applied_count": 0,
                "degraded_count": 0,
                "deterministic_degrade_count": 0,
                "missing_bundle_count": 0,
                "operator_tags": [],
                "slots": [slot],
                "summary_line": f"applied [applied=1/1 | primary=1 | slots={slot}]",
            },
            "candidate_comparison": {
                "selected_artifact_id": selected_artifact_id,
                "current_artifact_id": artifact_id,
                "candidate_count": 2,
                "ready_candidate_count": 1,
            },
            "operator_go_no_go": {"decision": "REVIEW"},
            "review_manifest": {"artifact_id": artifact_id},
            "send_manifest": {"artifact_id": artifact_id},
            "review_summary": {
                "recommended_action": "send_review",
                "workflow_state": "review_required",
                "selected_artifact_id": selected_artifact_id,
                "current_artifact_id": artifact_id,
                "selected_is_current": False,
                "candidate_count": 2,
                "ready_candidate_count": 1,
                "qa_score": 94,
                "blocker_count": 0,
                "warning_count": 1,
                "go_no_go_decision": "REVIEW",
                "llm_bundle_count": 1,
                "llm_applied_count": 1,
                "llm_degraded_count": 0,
                "llm_primary_count": 1,
                "llm_fallback_count": 0,
            },
        }

    def list_report_operator_review_surfaces(self, **_: object) -> list[dict]:
        return []

    def report_artifact_lineage_from_surface(self, surface: dict) -> dict:
        return dict(surface.get("artifact_lineage") or {})


def _active_schema(payload: dict) -> dict:
    active = payload["active_surface"]
    return {
        "artifact_keys": sorted(active["artifact"].keys()),
        "selected_handoff_keys": sorted(active["selected_handoff"].keys()),
        "state_keys": sorted(active["state"].keys()),
        "package_path_keys": sorted(active["package_paths"].keys()),
        "package_version_keys": sorted(active["package_versions"].keys()),
        "package_state_keys": sorted(active["package_state"].keys()),
        "review_summary_keys": sorted(active["review_summary"].keys()),
        "artifact_lineage_keys": sorted(active["artifact_lineage"].keys()),
        "llm_lineage_summary_keys": sorted(active["llm_lineage_summary"].keys()),
        "llm_lineage_keys": sorted(active["llm_lineage"].keys()),
        "llm_summary_keys": sorted(active["llm_lineage"]["summary"].keys()),
    }


def test_main_and_support_status_cli_json_contracts_are_symmetric(monkeypatch, capsys) -> None:
    monkeypatch.setattr(main_module, "FSJStore", lambda: _ParityStore(domain="main"))
    monkeypatch.setattr(support_module, "FSJStore", lambda: _ParityStore(domain="macro"))

    monkeypatch.setattr("sys.argv", ["fsj_main_delivery_status.py", "--business-date", "2099-04-22", "--format", "json"])
    main_module.main()
    main_payload = json.loads(capsys.readouterr().out)

    monkeypatch.setattr(
        "sys.argv",
        ["fsj_support_delivery_status.py", "--agent-domain", "macro", "--business-date", "2099-04-22", "--format", "json"],
    )
    support_module.main()
    support_payload = json.loads(capsys.readouterr().out)

    assert _active_schema(main_payload) == _active_schema(support_payload)
    assert main_payload["active_surface"]["review_summary"]["go_no_go_decision"] == "REVIEW"
    assert support_payload["active_surface"]["review_summary"]["go_no_go_decision"] == "REVIEW"
    assert main_payload["active_surface"]["package_paths"]["operator_review_bundle_path"].endswith("operator_review_bundle.json")
    assert support_payload["active_surface"]["package_paths"]["operator_review_bundle_path"].endswith("operator_review_bundle.json")
    assert main_payload["active_surface"]["llm_lineage"]["summary"]["applied_count"] == 1
    assert support_payload["active_surface"]["llm_lineage"]["summary"]["applied_count"] == 1
    assert main_payload["active_surface"]["llm_lineage_summary"]["status"] == "applied"
    assert support_payload["active_surface"]["llm_lineage_summary"]["status"] == "applied"
