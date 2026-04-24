from __future__ import annotations

from scripts.fsj_artifact_lineage import _print_text, build_payload


class _DummyStore:
    def get_latest_active_report_artifact_lineage(self, **_: object) -> dict:
        return {"artifact": {"business_date": "2099-04-22"}}

    def get_active_report_artifact_lineage(self, **_: object) -> dict:
        return {
            "artifact": {"artifact_id": "artifact-active", "status": "active", "report_run_id": "run-1"},
            "canonical_lifecycle": {"state": "sent", "reason": "dispatch_receipt_succeeded"},
            "selection": {"selected_artifact_id": "artifact-active", "selected_is_current": True},
            "package": {"paths": {"send_manifest_path": "/tmp/send_manifest.json", "review_manifest_path": "/tmp/review_manifest.json", "workflow_manifest_path": "/tmp/workflow_manifest.json", "delivery_manifest_path": "/tmp/delivery_manifest.json"}},
            "review": {"operator_go_no_go": {"decision": "GO"}, "candidate_comparison": {"candidate_count": 2}},
            "governance": {"decision": "GO", "rationale": "quality gate and artifact integrity both pass", "next_step": "send_selected_package_to_primary_channel", "action_required": False},
            "promotion_authority": {"status": "approved_to_send", "approved": True, "required_action": "send_selected_package_to_primary_channel", "rationale": "quality gate and artifact integrity both pass", "summary_line": "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass", "source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"},
            "review_summary": {"go_no_go_decision": "GO", "operator_decision_rationale": "quality gate and artifact integrity both pass", "operator_next_step": "send_selected_package_to_primary_channel", "operator_action_required": False, "promotion_authority_status": "approved_to_send", "promotion_authority_approved": True, "promotion_authority_required_action": "send_selected_package_to_primary_channel", "promotion_authority_rationale": "quality gate and artifact integrity both pass", "promotion_authority_summary": "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass", "promotion_authority_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"},
            "board_state_source": {"state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step"},
            "canonical_state_vocabulary": {"status_semantic": "sent", "operator_bucket": "terminal_dispatch"},
            "what_user_received": {"dispatch_state": "dispatch_succeeded", "channel": "telegram_document", "provider_message_id": "42", "sent_at": "2099-04-22T10:00:03Z", "error": None},
            "bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 0, "slots": ["early", "late"], "section_keys": ["pre_open_main", "post_close_main"]},
            "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=2/2]"},
        }

    def list_report_artifact_lineages(self, **_: object) -> list[dict]:
        return [
            {"artifact": {"artifact_id": "artifact-active"}},
            {"artifact": {"artifact_id": "artifact-prev"}},
        ]


def test_build_payload_uses_artifact_lineage_store_helpers() -> None:
    payload = build_payload(
        business_date=None,
        agent_domain="main",
        artifact_family="main_final_report",
        strongest_slot="late",
        history_limit=5,
        store=_DummyStore(),
    )

    assert payload["business_date"] == "2099-04-22"
    assert payload["active"]["artifact"]["artifact_id"] == "artifact-active"
    assert payload["active"]["what_user_received"]["provider_message_id"] == "42"
    assert payload["active"]["promotion_authority"]["status"] == "approved_to_send"
    assert payload["active"]["governance"]["next_step"] == "send_selected_package_to_primary_channel"
    assert payload["active"]["review_summary"]["promotion_authority_source_of_truth"] == "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"
    assert payload["active"]["board_state_source"]["state_source_of_truth"] == "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"
    assert len(payload["history"]) == 2


def test_print_text_exposes_governance_and_promotion_authority_fields(capsys) -> None:
    payload = build_payload(
        business_date=None,
        agent_domain="main",
        artifact_family="main_final_report",
        strongest_slot="late",
        history_limit=5,
        store=_DummyStore(),
    )

    _print_text(payload)
    output = capsys.readouterr().out

    assert "governance_decision=GO" in output
    assert "governance_next_step=send_selected_package_to_primary_channel" in output
    assert "promotion_authority_status=approved_to_send" in output
    assert "promotion_authority_summary=approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass" in output
    assert "promotion_authority_source_of_truth=ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff" in output
    assert "board_state_source=ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff" in output
    assert "canonical_operator_bucket=terminal_dispatch" in output
