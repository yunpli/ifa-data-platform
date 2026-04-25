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
            "package": {"report_scope": "main", "output_profile": "review", "paths": {"send_manifest_path": "/tmp/send_manifest.json", "review_manifest_path": "/tmp/review_manifest.json", "workflow_manifest_path": "/tmp/workflow_manifest.json", "delivery_manifest_path": "/tmp/delivery_manifest.json", "formal_output_root_dir": "/tmp/reports", "formal_primary_report_path": "/tmp/reports/report.html", "formal_source_report_path": "/tmp/publish/report.html"}},
            "review": {"operator_go_no_go": {"decision": "GO", "approver_kind": "system", "approver_label": "fsj_policy_projection"}, "candidate_comparison": {"candidate_count": 2}},
            "governance": {"decision": "GO", "rationale": "quality gate and artifact integrity both pass", "next_step": "send_selected_package_to_primary_channel", "action_required": False},
            "promotion_authority": {"status": "approved_to_send", "approved": True, "required_action": "send_selected_package_to_primary_channel", "rationale": "quality gate and artifact integrity both pass", "summary_line": "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass", "source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "approver_kind": "system", "approver_id": None, "approver_label": "fsj_policy_projection", "decided_at": None, "approver_summary": "kind=system | id=- | label=fsj_policy_projection | decided_at=-"},
            "review_summary": {"go_no_go_decision": "GO", "operator_decision_rationale": "quality gate and artifact integrity both pass", "operator_next_step": "send_selected_package_to_primary_channel", "operator_action_required": False, "promotion_authority_status": "approved_to_send", "promotion_authority_approved": True, "promotion_authority_required_action": "send_selected_package_to_primary_channel", "promotion_authority_rationale": "quality gate and artifact integrity both pass", "promotion_authority_summary": "approved_to_send | decision=GO | selected_is_current=True | required_action=send_selected_package_to_primary_channel | rationale=quality gate and artifact integrity both pass", "promotion_authority_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.operator_go_no_go + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "promotion_authority_approver_kind": "system", "promotion_authority_approver_id": None, "promotion_authority_approver_label": "fsj_policy_projection", "promotion_authority_decided_at": None, "promotion_authority_approver_summary": "kind=system | id=- | label=fsj_policy_projection | decided_at=-"},
            "board_state_source": {"state_source_of_truth": "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff", "next_action_source_of_truth": "ifa_fsj_report_artifacts.metadata_json.review_surface.review_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.review_surface.send_manifest.next_step + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow.next_step"},
            "canonical_state_vocabulary": {"status_semantic": "sent", "operator_bucket": "terminal_dispatch"},
            "what_user_received": {"dispatch_state": "dispatch_succeeded", "channel": "telegram_document", "provider_message_id": "42", "sent_at": "2099-04-22T10:00:03Z", "error": None},
            "bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 0, "slots": ["early", "late"], "section_keys": ["pre_open_main", "post_close_main"]},
            "llm_lineage_summary": {
                "status": "applied",
                "summary_line": "applied [applied=2/2 | prompts=fsj_early_main_v1,fsj_late_main_v1 | adopted_fields=12 | replay_ready=2 | usage=2 | cost_usd=0.012560]",
                "prompt_versions": ["fsj_early_main_v1", "fsj_late_main_v1"],
                "field_replay_ready_count": 2,
                "adopted_output_field_count": 12,
                "discarded_output_field_count": 0,
                "discard_reasons": [],
                "usage_bundle_count": 2,
                "priced_bundle_count": 2,
                "uncosted_bundle_count": 0,
                "estimated_cost_usd": 0.01256,
                "budget_posture": "fully_priced",
                "budget_attention": False,
                "budget_summary_line": "fully_priced [2/2]",
                "budget_governance_status": "within_budget",
                "budget_governance_required_action": None,
                "budget_governance_summary_line": "within_budget | scope=per_artifact | within_configured_budget_policy | policy=cost<=0.020000,tokens<=12000,fallback_rate<=0.500,degraded_rate<=0.500,pricing=required",
                "budget_governance": {
                    "scope": "per_artifact",
                    "estimated_cost_limit_usd": 0.02,
                    "token_limit": 12000,
                    "require_pricing_for_all_usage": True,
                    "fallback_rate": 0.0,
                    "max_fallback_rate": 0.5,
                    "degraded_rate": 0.0,
                    "max_degraded_rate": 0.5,
                },
            },
        }

    def list_report_artifact_lineages(self, **_: object) -> list[dict]:
        return [
            {"artifact": {"artifact_id": "artifact-active"}},
            {"artifact": {"artifact_id": "artifact-prev"}},
        ]

    def summarize_report_artifact_registry(self, **_: object) -> dict:
        return {
            "active_artifact_id": "artifact-active",
            "chain_depth": 2,
            "superseded_count": 1,
            "withdrawn_count": 0,
            "sent_count": 1,
            "head_matches_history": True,
            "dangling_supersedes_ids": [],
            "multiply_superseded_artifact_ids": [],
            "summary_line": "head=artifact-active | depth=2 | superseded=1 | withdrawn=0 | sent=1 | dangling_supersedes=0 | multiply_superseded=0",
        }


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
    assert payload["active"]["review_summary"]["promotion_authority_approver_kind"] == "system"
    assert payload["active"]["review_summary"]["promotion_authority_approver_label"] == "fsj_policy_projection"
    assert payload["active"]["board_state_source"]["state_source_of_truth"] == "ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff"
    assert len(payload["history"]) == 2
    assert payload["registry"]["chain_depth"] == 2
    assert payload["registry"]["head_matches_history"] is True


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
    assert "promotion_authority_approver_kind=system" in output
    assert "promotion_authority_approver_label=fsj_policy_projection" in output
    assert "promotion_authority_approver_summary=kind=system | id=- | label=fsj_policy_projection | decided_at=-" in output
    assert "board_state_source=ifa_fsj_report_artifacts.status + ifa_fsj_report_artifacts.metadata_json.delivery_package.workflow + ifa_fsj_report_artifacts.metadata_json.workflow_linkage.selected_handoff" in output
    assert "report_scope=main" in output
    assert "output_profile=review" in output
    assert "formal_output_root_dir=/tmp/reports" in output
    assert "formal_primary_report_path=/tmp/reports/report.html" in output
    assert "formal_source_report_path=/tmp/publish/report.html" in output
    assert "canonical_operator_bucket=terminal_dispatch" in output
    assert "llm_prompt_versions=fsj_early_main_v1,fsj_late_main_v1" in output
    assert "llm_field_replay_ready_count=2" in output
    assert "llm_adopted_output_field_count=12" in output
    assert "llm_discarded_output_field_count=0" in output
    assert "llm_discard_reasons=" in output
    assert "llm_usage_bundle_count=2" in output
    assert "llm_priced_bundle_count=2" in output
    assert "llm_uncosted_bundle_count=0" in output
    assert "llm_estimated_cost_usd=0.01256" in output
    assert "llm_budget_posture=fully_priced" in output
    assert "llm_budget_attention=False" in output
    assert "llm_budget_summary_line=fully_priced [2/2]" in output
    assert "llm_budget_governance_status=within_budget" in output
    assert "llm_budget_governance_required_action=None" in output
    assert "llm_budget_governance_summary_line=within_budget | scope=per_artifact | within_configured_budget_policy | policy=cost<=0.020000,tokens<=12000,fallback_rate<=0.500,degraded_rate<=0.500,pricing=required" in output
    assert "llm_budget_governance_scope=per_artifact" in output
    assert "llm_budget_governance_estimated_cost_limit_usd=0.02" in output
    assert "llm_budget_governance_token_limit=12000" in output
    assert "llm_budget_governance_require_pricing_for_all_usage=True" in output
    assert "llm_budget_governance_fallback_rate=0.0" in output
    assert "llm_budget_governance_max_fallback_rate=0.5" in output
    assert "llm_budget_governance_degraded_rate=0.0" in output
    assert "llm_budget_governance_max_degraded_rate=0.5" in output
    assert "registry_chain_depth=2" in output
    assert "registry_summary=head=artifact-active | depth=2 | superseded=1 | withdrawn=0 | sent=1 | dangling_supersedes=0 | multiply_superseded=0" in output
