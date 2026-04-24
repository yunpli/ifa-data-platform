#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ifa_data_platform.fsj.store import FSJStore

_BEIJING = timezone(timedelta(hours=8))


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _resolve_business_date(*, store: FSJStore, agent_domain: str, artifact_family: str, strongest_slot: str | None) -> str | None:
    lineage = store.get_latest_active_report_artifact_lineage(
        agent_domain=agent_domain,
        artifact_family=artifact_family,
        strongest_slot=strongest_slot,
        max_business_date=datetime.now(_BEIJING).date(),
    )
    return _safe_dict(lineage.get("artifact") if lineage else {}).get("business_date")


def build_payload(
    *,
    business_date: str | None,
    agent_domain: str,
    artifact_family: str,
    strongest_slot: str | None,
    history_limit: int,
    store: FSJStore | None = None,
) -> dict[str, Any]:
    store = store or FSJStore()
    resolved_business_date = business_date or _resolve_business_date(
        store=store,
        agent_domain=agent_domain,
        artifact_family=artifact_family,
        strongest_slot=strongest_slot,
    )
    active = None
    history: list[dict[str, Any]] = []
    registry: dict[str, Any] | None = None
    if resolved_business_date:
        active = store.get_active_report_artifact_lineage(
            business_date=resolved_business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
        )
        history = store.list_report_artifact_lineages(
            business_date=resolved_business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
            statuses=["active", "superseded", "withdrawn"],
            limit=history_limit,
        )
        registry = store.summarize_report_artifact_registry(
            active_lineage=active,
            history_lineages=history,
        )
    return {
        "business_date": resolved_business_date,
        "agent_domain": agent_domain,
        "artifact_family": artifact_family,
        "strongest_slot": strongest_slot,
        "active": active,
        "history": history,
        "registry": registry,
    }


def _print_text(payload: dict[str, Any]) -> None:
    print(f"business_date={payload.get('business_date') or '-'}")
    print(f"agent_domain={payload.get('agent_domain')}")
    print(f"artifact_family={payload.get('artifact_family')}")
    active = _safe_dict(payload.get("active"))
    artifact = _safe_dict(active.get("artifact"))
    lifecycle = _safe_dict(active.get("canonical_lifecycle"))
    selection = _safe_dict(active.get("selection"))
    received = _safe_dict(active.get("what_user_received"))
    package = _safe_dict(active.get("package"))
    review = _safe_dict(active.get("review"))
    governance = _safe_dict(active.get("governance"))
    promotion_authority = _safe_dict(active.get("promotion_authority"))
    review_summary = _safe_dict(active.get("review_summary"))
    board_state_source = _safe_dict(active.get("board_state_source"))
    canonical_state_vocabulary = _safe_dict(active.get("canonical_state_vocabulary"))
    bundle_summary = _safe_dict(active.get("bundle_lineage_summary"))
    llm_summary = _safe_dict(active.get("llm_lineage_summary"))
    registry = _safe_dict(payload.get("registry"))
    if not artifact:
        print("active_artifact=NONE")
        print(f"history_count={len(payload.get('history') or [])}")
        return
    print(f"artifact_id={artifact.get('artifact_id')}")
    print(f"artifact_status={artifact.get('status')}")
    print(f"report_run_id={artifact.get('report_run_id')}")
    print(f"supersedes_artifact_id={artifact.get('supersedes_artifact_id')}")
    print(f"canonical_lifecycle_state={lifecycle.get('state')}")
    print(f"canonical_lifecycle_reason={lifecycle.get('reason')}")
    print(f"selected_artifact_id={selection.get('selected_artifact_id')}")
    print(f"selected_is_current={selection.get('selected_is_current')}")
    print(f"delivery_manifest_path={_safe_dict(package.get('paths')).get('delivery_manifest_path')}")
    print(f"send_manifest_path={_safe_dict(package.get('paths')).get('send_manifest_path')}")
    print(f"review_manifest_path={_safe_dict(package.get('paths')).get('review_manifest_path')}")
    print(f"workflow_manifest_path={_safe_dict(package.get('paths')).get('workflow_manifest_path')}")
    print(f"dispatch_state={received.get('dispatch_state')}")
    print(f"dispatch_channel={received.get('channel')}")
    print(f"provider_message_id={received.get('provider_message_id')}")
    print(f"sent_at={received.get('sent_at')}")
    print(f"dispatch_error={received.get('error')}")
    print(f"review_decision={_safe_dict(review.get('operator_go_no_go')).get('decision')}")
    print(f"governance_decision={governance.get('decision') or review_summary.get('go_no_go_decision')}")
    print(f"governance_rationale={governance.get('rationale') or review_summary.get('operator_decision_rationale')}")
    print(f"governance_next_step={governance.get('next_step') or review_summary.get('operator_next_step')}")
    print(f"governance_action_required={governance.get('action_required') if governance else review_summary.get('operator_action_required')}")
    print(f"promotion_authority_status={promotion_authority.get('status') or review_summary.get('promotion_authority_status')}")
    print(f"promotion_authority_approved={promotion_authority.get('approved') if promotion_authority else review_summary.get('promotion_authority_approved')}")
    print(f"promotion_authority_required_action={promotion_authority.get('required_action') or review_summary.get('promotion_authority_required_action')}")
    print(f"promotion_authority_rationale={promotion_authority.get('rationale') or review_summary.get('promotion_authority_rationale')}")
    print(f"promotion_authority_summary={promotion_authority.get('summary_line') or review_summary.get('promotion_authority_summary')}")
    print(f"promotion_authority_source_of_truth={promotion_authority.get('source_of_truth') or review_summary.get('promotion_authority_source_of_truth')}")
    print(f"promotion_authority_approver_kind={promotion_authority.get('approver_kind') or review_summary.get('promotion_authority_approver_kind')}")
    print(f"promotion_authority_approver_id={promotion_authority.get('approver_id') or review_summary.get('promotion_authority_approver_id')}")
    print(f"promotion_authority_approver_label={promotion_authority.get('approver_label') or review_summary.get('promotion_authority_approver_label')}")
    print(f"promotion_authority_decided_at={promotion_authority.get('decided_at') or review_summary.get('promotion_authority_decided_at')}")
    print(f"promotion_authority_approver_summary={promotion_authority.get('approver_summary') or review_summary.get('promotion_authority_approver_summary')}")
    print(f"board_state_source={board_state_source.get('state_source_of_truth')}")
    print(f"board_next_action_source={board_state_source.get('next_action_source_of_truth')}")
    print(f"canonical_status_semantic={canonical_state_vocabulary.get('status_semantic')}")
    print(f"canonical_operator_bucket={canonical_state_vocabulary.get('operator_bucket')}")
    print(f"candidate_count={_safe_dict(review.get('candidate_comparison')).get('candidate_count')}")
    print(f"bundle_count={bundle_summary.get('bundle_count')}")
    print(f"missing_bundle_count={bundle_summary.get('missing_bundle_count')}")
    print(f"bundle_slots={','.join(bundle_summary.get('slots') or [])}")
    print(f"bundle_section_keys={','.join(bundle_summary.get('section_keys') or [])}")
    print(f"llm_lineage_status={llm_summary.get('status')}")
    print(f"llm_lineage_summary={llm_summary.get('summary_line')}")
    print(f"llm_prompt_versions={','.join(llm_summary.get('prompt_versions') or [])}")
    print(f"llm_field_replay_ready_count={llm_summary.get('field_replay_ready_count')}")
    print(f"llm_adopted_output_field_count={llm_summary.get('adopted_output_field_count')}")
    print(f"llm_discarded_output_field_count={llm_summary.get('discarded_output_field_count')}")
    print(f"llm_discard_reasons={','.join(llm_summary.get('discard_reasons') or [])}")
    print(f"llm_usage_bundle_count={llm_summary.get('usage_bundle_count')}")
    print(f"llm_priced_bundle_count={llm_summary.get('priced_bundle_count')}")
    print(f"llm_uncosted_bundle_count={llm_summary.get('uncosted_bundle_count')}")
    print(f"llm_estimated_cost_usd={llm_summary.get('estimated_cost_usd')}")
    print(f"llm_budget_posture={llm_summary.get('budget_posture')}")
    print(f"llm_budget_attention={llm_summary.get('budget_attention')}")
    print(f"llm_budget_summary_line={llm_summary.get('budget_summary_line')}")
    print(f"llm_budget_governance_status={llm_summary.get('budget_governance_status')}")
    print(f"llm_budget_governance_required_action={llm_summary.get('budget_governance_required_action')}")
    print(f"llm_budget_governance_summary_line={llm_summary.get('budget_governance_summary_line')}")
    budget_governance = _safe_dict(llm_summary.get('budget_governance'))
    print(f"llm_budget_governance_scope={budget_governance.get('scope')}")
    print(f"llm_budget_governance_estimated_cost_limit_usd={budget_governance.get('estimated_cost_limit_usd')}")
    print(f"llm_budget_governance_token_limit={budget_governance.get('token_limit')}")
    print(f"llm_budget_governance_require_pricing_for_all_usage={budget_governance.get('require_pricing_for_all_usage')}")
    print(f"llm_budget_governance_fallback_rate={budget_governance.get('fallback_rate')}")
    print(f"llm_budget_governance_max_fallback_rate={budget_governance.get('max_fallback_rate')}")
    print(f"llm_budget_governance_degraded_rate={budget_governance.get('degraded_rate')}")
    print(f"llm_budget_governance_max_degraded_rate={budget_governance.get('max_degraded_rate')}")
    print(f"registry_active_artifact_id={registry.get('active_artifact_id')}")
    print(f"registry_chain_depth={registry.get('chain_depth')}")
    print(f"registry_superseded_count={registry.get('superseded_count')}")
    print(f"registry_withdrawn_count={registry.get('withdrawn_count')}")
    print(f"registry_sent_count={registry.get('sent_count')}")
    print(f"registry_head_matches_history={registry.get('head_matches_history')}")
    print(f"registry_dangling_supersedes_ids={','.join(registry.get('dangling_supersedes_ids') or [])}")
    print(f"registry_multiply_superseded_artifact_ids={','.join(registry.get('multiply_superseded_artifact_ids') or [])}")
    print(f"registry_summary={registry.get('summary_line')}")
    print(f"history_count={len(payload.get('history') or [])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query canonical FSJ artifact lineage across package/review/send seams.")
    parser.add_argument("--business-date")
    parser.add_argument("--agent-domain", default="main")
    parser.add_argument("--artifact-family", default="main_final_report")
    parser.add_argument("--strongest-slot")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    payload = build_payload(
        business_date=args.business_date,
        agent_domain=args.agent_domain,
        artifact_family=args.artifact_family,
        strongest_slot=args.strongest_slot,
        history_limit=args.history_limit,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
