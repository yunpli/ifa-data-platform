#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from ifa_data_platform.fsj.store import FSJStore
from scripts.fsj_drift_monitor import (
    build_drift_payload,
    build_fleet_drift_digest,
    format_drift_summary_line,
    format_fleet_drift_digest_line,
)

_VALID_SLOT_KEYS = {"early", "mid", "late"}
_VALID_DOMAINS = {"macro", "commodities", "ai_tech"}
_BEIJING = timezone(timedelta(hours=8))


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _surface_summary(surface: dict[str, Any] | None, *, store: FSJStore | None = None) -> dict[str, Any] | None:
    if not surface:
        return None
    return (store or FSJStore()).report_workflow_handoff_from_surface(surface)


def _artifact_lineage_summary(surface: dict[str, Any] | None, *, store: FSJStore | None = None) -> dict[str, Any] | None:
    if not surface:
        return None
    resolver = store or FSJStore()
    return resolver.report_artifact_lineage_from_surface(surface)


def _resolve_main_latest(*, slot: str | None = None, store: FSJStore | None = None) -> dict[str, Any] | None:
    if slot is not None and slot not in _VALID_SLOT_KEYS:
        raise ValueError(f"unsupported slot: {slot}")
    store = store or FSJStore()
    surface = store.get_latest_active_report_delivery_surface(
        agent_domain="main",
        artifact_family="main_final_report",
        strongest_slot=slot,
        max_business_date=datetime.now(_BEIJING).date(),
    )
    if not surface:
        return None
    artifact = _safe_dict(surface.get("artifact"))
    delivery_package = _safe_dict(surface.get("delivery_package"))
    slot_evaluation = _safe_dict(delivery_package.get("slot_evaluation"))
    return {
        "business_date": artifact.get("business_date"),
        "artifact_id": artifact.get("artifact_id"),
        "report_run_id": artifact.get("report_run_id"),
        "status": artifact.get("status"),
        "updated_at": artifact.get("updated_at"),
        "strongest_slot": slot_evaluation.get("strongest_slot"),
    }


def _resolve_support_latest(*, agent_domain: str, slot: str | None = None, store: FSJStore | None = None) -> dict[str, Any] | None:
    if agent_domain not in _VALID_DOMAINS:
        raise ValueError(f"unsupported agent_domain: {agent_domain}")
    if slot is not None and slot not in {"early", "late"}:
        raise ValueError(f"unsupported slot: {slot}")
    store = store or FSJStore()
    surface = store.get_latest_active_report_delivery_surface(
        agent_domain=agent_domain,
        artifact_family="support_domain_report",
        strongest_slot=slot,
        max_business_date=datetime.now(_BEIJING).date(),
    )
    if not surface:
        return None
    artifact = _safe_dict(surface.get("artifact"))
    delivery_package = _safe_dict(surface.get("delivery_package"))
    return {
        "business_date": artifact.get("business_date"),
        "artifact_id": artifact.get("artifact_id"),
        "report_run_id": artifact.get("report_run_id"),
        "status": artifact.get("status"),
        "updated_at": artifact.get("updated_at"),
        "slot": delivery_package.get("slot"),
    }


def build_board_payload(*, business_date: str | None = None, history_limit: int = 5, store: FSJStore | None = None) -> dict[str, Any]:
    store = store or FSJStore()
    payload = store.build_operator_board_surface(business_date=business_date, history_limit=history_limit)
    main_artifact_lineage = _artifact_lineage_summary(payload.get("main"), store=store)
    support_artifact_lineage = {
        domain: _artifact_lineage_summary(surface, store=store)
        for domain, surface in _safe_dict(payload.get("support")).items()
    }
    history_artifact_lineage = [
        _artifact_lineage_summary(surface, store=store)
        for surface in (payload.get("history") or [])
    ]
    lineage_subjects = [main_artifact_lineage] + list(support_artifact_lineage.values()) + history_artifact_lineage
    bundle_count = sum(_safe_dict(_safe_dict(item).get("bundle_lineage_summary")).get("bundle_count") or 0 for item in lineage_subjects)
    missing_bundle_count = sum(_safe_dict(_safe_dict(item).get("bundle_lineage_summary")).get("missing_bundle_count") or 0 for item in lineage_subjects)
    dispatch_states = [
        _safe_dict(_safe_dict(item).get("what_user_received")).get("dispatch_state")
        for item in lineage_subjects
        if item
    ]
    payload["artifact_lineage_summary"] = {
        "main": main_artifact_lineage,
        "support": support_artifact_lineage,
        "history": history_artifact_lineage,
        "aggregate": {
            "bundle_count": bundle_count,
            "missing_bundle_count": missing_bundle_count,
            "dispatch_succeeded_count": sum(1 for state in dispatch_states if state == "dispatch_succeeded"),
            "dispatch_failed_count": sum(1 for state in dispatch_states if state == "dispatch_failed"),
        },
    }
    drift_payloads = {
        "main": build_drift_payload(scope="main", days=7, store=store),
    }
    if payload.get("support"):
        for domain in sorted(_VALID_DOMAINS):
            drift_payloads[f"support:{domain}"] = build_drift_payload(scope=f"support:{domain}", days=7, store=store)
    payload["drift_summary_lines"] = {
        key: format_drift_summary_line(drift_payload)
        for key, drift_payload in drift_payloads.items()
    }
    payload["fleet_drift_digest"] = build_fleet_drift_digest(drift_payloads)
    payload["fleet_drift_digest_line"] = format_fleet_drift_digest_line(payload["fleet_drift_digest"])
    return payload


def _print_text(payload: dict[str, Any]) -> None:
    resolution = _safe_dict(payload.get("resolution"))
    lineage = _safe_dict(payload.get("llm_lineage_summary"))
    lineage_aggregate = _safe_dict(lineage.get("aggregate"))
    artifact_lineage = _safe_dict(payload.get("artifact_lineage_summary"))
    artifact_lineage_aggregate = _safe_dict(artifact_lineage.get("aggregate"))
    role_policy = _safe_dict(payload.get("llm_role_policy_review"))
    role_policy_aggregate = _safe_dict(role_policy.get("aggregate"))
    board_readiness = _safe_dict(payload.get("board_readiness_summary"))
    board_aggregate = _safe_dict(board_readiness.get("aggregate"))
    board_rows = _safe_dict(payload.get("board_rows"))
    board_rows_aggregate = _safe_dict(board_rows.get("aggregate"))
    board_state_sources = _safe_dict(payload.get("board_state_source_summary"))
    board_state_sources_aggregate = _safe_dict(board_state_sources.get("aggregate"))
    qa_axes_summary = _safe_dict(payload.get("qa_axes_summary"))
    qa_axes_aggregate = _safe_dict(qa_axes_summary.get("aggregate"))
    db_candidate_fleet = _safe_dict(payload.get("db_candidate_fleet_summary"))
    db_candidate_history = [
        _safe_dict(item)
        for item in (payload.get("db_candidate_history_summary") or [])
        if isinstance(item, dict)
    ]
    print(f"business_date={payload.get('business_date') or '-'}")
    print(f"resolution_mode={resolution.get('mode') or '-'}")
    main = _safe_dict(payload.get("main"))
    main_lineage = _safe_dict(lineage.get("main") or (main.get("llm_lineage_summary") if main else None))
    main_artifact_lineage = _safe_dict(artifact_lineage.get("main") or (main.get("artifact_lineage") if main else None))
    main_board_row = _safe_dict(board_rows.get("main"))
    main_board_source = _safe_dict(board_state_sources.get("main") or (main.get("board_state_source") if main else None))
    if main:
        print(f"main_artifact_id={_safe_dict(main.get('artifact')).get('artifact_id')}")
        print(f"main_recommended_action={_safe_dict(main.get('state')).get('recommended_action')}")
        print(f"main_source_health_status={_safe_dict(main.get('review_summary')).get('source_health_status') or 'healthy'}")
        print(f"main_source_health_blocking_slots={_safe_dict(main.get('review_summary')).get('source_health_blocking_slot_count', 0)}")
        print(f"main_source_health_degraded_slots={_safe_dict(main.get('review_summary')).get('source_health_degraded_slot_count', 0)}")
        print(f"main_source_health_degrade_reason={_safe_dict(main.get('review_summary')).get('source_health_degrade_reason')}")
        print(f"main_workflow_state={_safe_dict(main.get('state')).get('workflow_state')}")
        print(f"main_package_state={_safe_dict(main.get('state')).get('package_state')}")
        print(f"main_canonical_lifecycle_state={_safe_dict(main.get('canonical_lifecycle')).get('state')}")
        print(f"main_canonical_lifecycle_reason={_safe_dict(main.get('canonical_lifecycle')).get('reason')}")
        print(f"main_dispatch_state={main.get('dispatch_state')}")
        print(f"main_dispatch_receipt_state={_safe_dict(main.get('dispatch_receipt')).get('dispatch_state') or _safe_dict(main.get('dispatch_receipt')).get('status')}")
        print(f"main_dispatch_receipt_channel={_safe_dict(main.get('dispatch_receipt')).get('channel')}")
        print(f"main_dispatch_receipt_error={_safe_dict(main.get('dispatch_receipt')).get('error')}")
        print(f"main_governance_decision={_safe_dict(main.get('governance')).get('decision')}")
        print(f"main_governance_rationale={_safe_dict(main.get('governance')).get('rationale')}")
        print(f"main_governance_next_step={_safe_dict(main.get('governance')).get('next_step')}")
        print(f"main_governance_action_required={_safe_dict(main.get('governance')).get('action_required')}")
        print(f"main_promotion_authority_status={_safe_dict(main.get('promotion_authority')).get('status')}")
        print(f"main_promotion_authority_approved={_safe_dict(main.get('promotion_authority')).get('approved')}")
        print(f"main_promotion_authority_required_action={_safe_dict(main.get('promotion_authority')).get('required_action')}")
        print(f"main_promotion_authority_rationale={_safe_dict(main.get('promotion_authority')).get('rationale')}")
        print(f"main_promotion_authority_summary={_safe_dict(main.get('promotion_authority')).get('summary_line')}")
        print(f"main_board_status={main_board_row.get('status_semantic')}")
        print(f"main_board_blocking_reason={main_board_row.get('blocking_reason')}")
        print(f"main_board_next_action={main_board_row.get('next_action')}")
        print(f"main_board_selected_artifact_id={main_board_row.get('selected_artifact_id')}")
        print(f"main_board_selected_is_current={main_board_row.get('selected_is_current')}")
        print(f"main_board_strongest_slot={main_board_row.get('strongest_slot')}")
        print(f"main_board_generated_at_utc={main_board_row.get('generated_at_utc')}")
        print(f"main_board_dispatch_state={main_board_row.get('dispatch_state')}")
        print(f"main_board_bundle_count={main_board_row.get('bundle_count')}")
        print(f"main_board_missing_bundle_count={main_board_row.get('missing_bundle_count')}")
        print(f"main_board_lineage_sla_summary={main_board_row.get('lineage_sla_summary')}")
        print(f"main_board_failure_taxonomy_class={main_board_row.get('failure_taxonomy_class')}")
        print(f"main_board_failure_taxonomy_reason={main_board_row.get('failure_taxonomy_reason')}")
        print(f"main_board_failure_taxonomy_summary={main_board_row.get('failure_taxonomy_summary')}")
        print(f"main_board_row_summary={main_board_row.get('summary_line')}")
        print(f"main_board_state_source={main_board_source.get('state_source_of_truth')}")
        print(f"main_board_next_action_source={main_board_source.get('next_action_source_of_truth')}")
        print(f"main_board_blocking_reason_source={main_board_source.get('blocking_reason_source_of_truth')}")
        print(f"main_board_source_summary={main_board_source.get('summary_line')}")
        print(f"main_lineage_bundle_count={_safe_dict(main_artifact_lineage.get('bundle_lineage_summary')).get('bundle_count')}")
        print(f"main_lineage_missing_bundle_count={_safe_dict(main_artifact_lineage.get('bundle_lineage_summary')).get('missing_bundle_count')}")
        print(f"main_lineage_dispatch_state={_safe_dict(main_artifact_lineage.get('what_user_received')).get('dispatch_state')}")
        print(f"main_lineage_provider_message_id={_safe_dict(main_artifact_lineage.get('what_user_received')).get('provider_message_id')}")
        print(f"main_llm_lineage_status={main_lineage.get('status')}")
        print(f"main_llm_lineage_summary={main_lineage.get('summary_line')}")
        print(f"main_llm_models={','.join(main_lineage.get('models') or [])}")
        print(f"main_llm_total_tokens={_safe_dict(main_lineage.get('token_totals')).get('total_tokens')}")
        print(f"main_llm_estimated_cost_usd={main_lineage.get('estimated_cost_usd')}")
        main_role_policy = _safe_dict(main.get('llm_role_policy') or _safe_dict(role_policy.get('main')))
        print(f"main_llm_override_precedence={'>'.join(main_role_policy.get('override_precedence') or [])}")
        print(
            "main_llm_slot_boundary_modes="
            + ",".join(f"{slot}:{mode}" for slot, mode in sorted((_safe_dict(main_role_policy.get('slot_boundary_modes'))).items()))
        )
        main_qa_axes = _safe_dict(_safe_dict(qa_axes_summary.get('main')).get('qa_axes'))
        print(
            "main_qa_axes="
            + ",".join(
                f"{axis}:{'ready' if _safe_dict(axis_payload).get('ready') else 'attention'}:b{_safe_dict(axis_payload).get('blocker_count', 0)}:w{_safe_dict(axis_payload).get('warning_count', 0)}"
                for axis, axis_payload in sorted(main_qa_axes.items())
            )
        )
        print(
            "main_qa_axes_attention="
            + ",".join(_safe_dict(qa_axes_summary.get('main')).get('axes_with_attention') or [])
        )
    else:
        print("main_artifact=NONE")
    support_lineage = _safe_dict(lineage.get("support"))
    for domain in sorted(_VALID_DOMAINS):
        item = _safe_dict((payload.get("support") or {}).get(domain))
        if not item:
            print(f"support_{domain}=NONE")
            continue
        state = _safe_dict(item.get("state"))
        item_lineage = _safe_dict(support_lineage.get(domain) or item.get("llm_lineage_summary"))
        item_artifact_lineage = _safe_dict(_safe_dict(artifact_lineage.get('support')).get(domain) or item.get('artifact_lineage'))
        item_board_row = _safe_dict(_safe_dict(board_rows.get('support')).get(domain))
        item_board_source = _safe_dict(_safe_dict(board_state_sources.get('support')).get(domain) or item.get('board_state_source'))
        print(f"support_{domain}_artifact_id={_safe_dict(item.get('artifact')).get('artifact_id')}")
        print(f"support_{domain}_recommended_action={state.get('recommended_action')}")
        print(f"support_{domain}_source_health_status={_safe_dict(item.get('review_summary')).get('source_health_status') or 'healthy'}")
        print(f"support_{domain}_source_health_blocking_slots={_safe_dict(item.get('review_summary')).get('source_health_blocking_slot_count', 0)}")
        print(f"support_{domain}_source_health_degraded_slots={_safe_dict(item.get('review_summary')).get('source_health_degraded_slot_count', 0)}")
        print(f"support_{domain}_source_health_degrade_reason={_safe_dict(item.get('review_summary')).get('source_health_degrade_reason')}")
        print(f"support_{domain}_workflow_state={state.get('workflow_state')}")
        print(f"support_{domain}_package_state={state.get('package_state')}")
        print(f"support_{domain}_canonical_lifecycle_state={_safe_dict(item.get('canonical_lifecycle')).get('state')}")
        print(f"support_{domain}_canonical_lifecycle_reason={_safe_dict(item.get('canonical_lifecycle')).get('reason')}")
        print(f"support_{domain}_governance_decision={_safe_dict(item.get('governance')).get('decision')}")
        print(f"support_{domain}_governance_rationale={_safe_dict(item.get('governance')).get('rationale')}")
        print(f"support_{domain}_governance_next_step={_safe_dict(item.get('governance')).get('next_step')}")
        print(f"support_{domain}_governance_action_required={_safe_dict(item.get('governance')).get('action_required')}")
        print(f"support_{domain}_promotion_authority_status={_safe_dict(item.get('promotion_authority')).get('status')}")
        print(f"support_{domain}_promotion_authority_approved={_safe_dict(item.get('promotion_authority')).get('approved')}")
        print(f"support_{domain}_promotion_authority_required_action={_safe_dict(item.get('promotion_authority')).get('required_action')}")
        print(f"support_{domain}_promotion_authority_rationale={_safe_dict(item.get('promotion_authority')).get('rationale')}")
        print(f"support_{domain}_promotion_authority_summary={_safe_dict(item.get('promotion_authority')).get('summary_line')}")
        print(f"support_{domain}_board_status={item_board_row.get('status_semantic')}")
        print(f"support_{domain}_board_blocking_reason={item_board_row.get('blocking_reason')}")
        print(f"support_{domain}_board_next_action={item_board_row.get('next_action')}")
        print(f"support_{domain}_board_selected_artifact_id={item_board_row.get('selected_artifact_id')}")
        print(f"support_{domain}_board_selected_is_current={item_board_row.get('selected_is_current')}")
        print(f"support_{domain}_board_strongest_slot={item_board_row.get('strongest_slot')}")
        print(f"support_{domain}_board_generated_at_utc={item_board_row.get('generated_at_utc')}")
        print(f"support_{domain}_board_dispatch_state={item_board_row.get('dispatch_state')}")
        print(f"support_{domain}_board_bundle_count={item_board_row.get('bundle_count')}")
        print(f"support_{domain}_board_missing_bundle_count={item_board_row.get('missing_bundle_count')}")
        print(f"support_{domain}_board_lineage_sla_summary={item_board_row.get('lineage_sla_summary')}")
        print(f"support_{domain}_board_failure_taxonomy_class={item_board_row.get('failure_taxonomy_class')}")
        print(f"support_{domain}_board_failure_taxonomy_reason={item_board_row.get('failure_taxonomy_reason')}")
        print(f"support_{domain}_board_failure_taxonomy_summary={item_board_row.get('failure_taxonomy_summary')}")
        print(f"support_{domain}_board_row_summary={item_board_row.get('summary_line')}")
        print(f"support_{domain}_board_state_source={item_board_source.get('state_source_of_truth')}")
        print(f"support_{domain}_board_next_action_source={item_board_source.get('next_action_source_of_truth')}")
        print(f"support_{domain}_board_blocking_reason_source={item_board_source.get('blocking_reason_source_of_truth')}")
        print(f"support_{domain}_board_source_summary={item_board_source.get('summary_line')}")
        print(f"support_{domain}_lineage_bundle_count={_safe_dict(item_artifact_lineage.get('bundle_lineage_summary')).get('bundle_count')}")
        print(f"support_{domain}_lineage_missing_bundle_count={_safe_dict(item_artifact_lineage.get('bundle_lineage_summary')).get('missing_bundle_count')}")
        print(f"support_{domain}_lineage_dispatch_state={_safe_dict(item_artifact_lineage.get('what_user_received')).get('dispatch_state')}")
        print(f"support_{domain}_lineage_provider_message_id={_safe_dict(item_artifact_lineage.get('what_user_received')).get('provider_message_id')}")
        print(f"support_{domain}_llm_lineage_status={item_lineage.get('status')}")
        print(f"support_{domain}_llm_lineage_summary={item_lineage.get('summary_line')}")
        print(f"support_{domain}_llm_models={','.join(item_lineage.get('models') or [])}")
        print(f"support_{domain}_llm_total_tokens={_safe_dict(item_lineage.get('token_totals')).get('total_tokens')}")
        print(f"support_{domain}_llm_estimated_cost_usd={item_lineage.get('estimated_cost_usd')}")
        item_role_policy = _safe_dict(item.get('llm_role_policy') or _safe_dict(_safe_dict(role_policy.get('support')).get(domain)))
        print(f"support_{domain}_llm_override_precedence={'>'.join(item_role_policy.get('override_precedence') or [])}")
        print(
            f"support_{domain}_llm_slot_boundary_modes="
            + ",".join(f"{slot}:{mode}" for slot, mode in sorted((_safe_dict(item_role_policy.get('slot_boundary_modes'))).items()))
        )
        item_qa_axes = _safe_dict(_safe_dict(_safe_dict(qa_axes_summary.get('support')).get(domain)).get('qa_axes'))
        print(
            f"support_{domain}_qa_axes="
            + ",".join(
                f"{axis}:{'ready' if _safe_dict(axis_payload).get('ready') else 'attention'}:b{_safe_dict(axis_payload).get('blocker_count', 0)}:w{_safe_dict(axis_payload).get('warning_count', 0)}"
                for axis, axis_payload in sorted(item_qa_axes.items())
            )
        )
        print(
            f"support_{domain}_qa_axes_attention="
            + ",".join(_safe_dict(_safe_dict(qa_axes_summary.get('support')).get(domain)).get('axes_with_attention') or [])
        )
    print(f"fleet_artifact_lineage_bundle_count={artifact_lineage_aggregate.get('bundle_count')}")
    print(f"fleet_artifact_lineage_missing_bundle_count={artifact_lineage_aggregate.get('missing_bundle_count')}")
    print(f"fleet_artifact_lineage_dispatches_sent={artifact_lineage_aggregate.get('dispatch_succeeded_count')}")
    print(f"fleet_artifact_lineage_dispatches_failed={artifact_lineage_aggregate.get('dispatch_failed_count')}")
    print(f"fleet_llm_lineage_status={lineage_aggregate.get('overall_status')}")
    print(f"fleet_llm_attention_subjects={','.join(lineage_aggregate.get('attention_subjects') or [])}")
    print(f"fleet_llm_reported_subject_count={lineage_aggregate.get('reported_subject_count')}")
    print(f"fleet_llm_models={','.join(lineage_aggregate.get('models') or [])}")
    print(f"fleet_llm_total_tokens={lineage_aggregate.get('total_tokens')}")
    print(f"fleet_llm_estimated_cost_usd={lineage_aggregate.get('estimated_cost_usd')}")
    print(f"fleet_llm_uncosted_bundle_count={lineage_aggregate.get('uncosted_bundle_count')}")
    print(f"fleet_llm_priced_bundle_count={lineage_aggregate.get('priced_bundle_count')}")
    print(f"fleet_llm_budget_posture={lineage_aggregate.get('budget_posture')}")
    print(f"fleet_llm_budget_attention={lineage_aggregate.get('budget_attention')}")
    print(f"fleet_llm_budget_summary_line={lineage_aggregate.get('budget_summary_line')}")
    print(
        "fleet_llm_model_usage_breakdown="
        + ",".join(
            f"{model}:b{_safe_dict(payload).get('bundle_count', 0)}:a{_safe_dict(payload).get('applied_count', 0)}:f{_safe_dict(payload).get('fallback_applied_count', 0)}:t{_safe_dict(payload).get('total_tokens', 0)}:c{_safe_dict(payload).get('estimated_cost_usd')}"
            for model, payload in sorted(_safe_dict(lineage_aggregate.get('model_usage_breakdown')).items())
        )
    )
    print(
        "fleet_llm_slot_usage_breakdown="
        + ",".join(
            f"{slot}:b{_safe_dict(payload).get('bundle_count', 0)}:a{_safe_dict(payload).get('applied_count', 0)}:f{_safe_dict(payload).get('fallback_applied_count', 0)}:t{_safe_dict(payload).get('total_tokens', 0)}"
            for slot, payload in sorted(_safe_dict(lineage_aggregate.get('slot_usage_breakdown')).items())
        )
    )
    print(f"fleet_llm_policy_versions={','.join(role_policy_aggregate.get('policy_versions') or [])}")
    print(f"fleet_llm_override_precedence={'>'.join(role_policy_aggregate.get('override_precedence') or [])}")
    print(f"fleet_llm_attention_policy_subjects={','.join(role_policy_aggregate.get('attention_subjects') or [])}")
    drift_lines = _safe_dict(payload.get("drift_summary_lines"))
    print(f"fleet_drift_digest_line={payload.get('fleet_drift_digest_line') or '-'}")
    fleet_drift_digest = _safe_dict(payload.get('fleet_drift_digest'))
    for group_name in ('main', 'support'):
        group = _safe_dict(fleet_drift_digest.get(group_name))
        print(
            f"fleet_drift_{group_name}_llm_model_counts="
            + ",".join(f"{model}:{count}" for model, count in sorted(_safe_dict(group.get('llm_model_counts')).items()))
        )
        print(
            f"fleet_drift_{group_name}_llm_slot_counts="
            + ",".join(f"{slot}:{count}" for slot, count in sorted(_safe_dict(group.get('llm_slot_counts')).items()))
        )
        print(f"fleet_drift_{group_name}_llm_total_tokens={group.get('llm_total_tokens')}")
        print(f"fleet_drift_{group_name}_llm_usage_bundle_count={group.get('llm_usage_bundle_count')}")
        print(f"fleet_drift_{group_name}_llm_uncosted_bundle_count={group.get('llm_uncosted_bundle_count')}")
        print(f"fleet_drift_{group_name}_llm_priced_bundle_count={group.get('priced_bundle_count')}")
        print(f"fleet_drift_{group_name}_llm_budget_posture={group.get('budget_posture')}")
        print(f"fleet_drift_{group_name}_llm_budget_attention={group.get('budget_attention')}")
        print(f"fleet_drift_{group_name}_llm_budget_summary_line={group.get('budget_summary_line')}")
        print(f"fleet_drift_{group_name}_llm_estimated_cost_usd={group.get('llm_estimated_cost_usd')}")
    print(f"main_drift_summary_line={drift_lines.get('main') or '-'}")
    for domain in sorted(_VALID_DOMAINS):
        key = f"support:{domain}"
        print(f"{key.replace(':', '_')}_drift_summary_line={drift_lines.get(key) or '-'}")
    print(f"fleet_board_posture={board_aggregate.get('overall_posture')}")
    print(
        "fleet_source_health_status_counts="
        + ",".join(
            f"{state}:{count}" for state, count in sorted(_safe_dict(board_aggregate.get('source_health_status_counts')).items())
        )
    )
    print(f"fleet_source_health_attention_subjects={','.join(board_aggregate.get('source_health_attention_subjects') or [])}")
    print(f"fleet_source_health_blocked_subjects={','.join(board_aggregate.get('source_health_blocked_subjects') or [])}")
    print(f"fleet_source_health_degraded_subjects={','.join(board_aggregate.get('source_health_degraded_subjects') or [])}")
    print(
        "fleet_canonical_lifecycle_state_counts="
        + ",".join(
            f"{state}:{count}" for state, count in sorted(_safe_dict(board_aggregate.get('canonical_lifecycle_state_counts')).items())
        )
    )
    print(
        "fleet_board_status_counts="
        + ",".join(
            f"{state}:{count}" for state, count in sorted(_safe_dict(board_rows_aggregate.get('status_semantic_counts')).items())
        )
    )
    print(
        "fleet_board_dispatch_state_counts="
        + ",".join(
            f"{state}:{count}" for state, count in sorted(_safe_dict(board_rows_aggregate.get('dispatch_state_counts')).items())
        )
    )
    print(
        "fleet_board_strongest_slot_counts="
        + ",".join(
            f"{state}:{count}" for state, count in sorted(_safe_dict(board_rows_aggregate.get('strongest_slot_counts')).items())
        )
    )
    print(
        "fleet_board_failure_taxonomy_counts="
        + ",".join(
            f"{state}:{count}" for state, count in sorted(_safe_dict(board_rows_aggregate.get('failure_taxonomy_counts')).items())
        )
    )
    print(f"fleet_board_next_action_subjects={','.join(board_rows_aggregate.get('subjects_with_next_action') or [])}")
    print(f"fleet_board_blocking_reason_subjects={','.join(board_rows_aggregate.get('subjects_with_blocking_reason') or [])}")
    print(f"fleet_board_selected_mismatch_subjects={','.join(board_rows_aggregate.get('selected_mismatch_subjects') or [])}")
    print(f"fleet_board_missing_bundle_subjects={','.join(board_rows_aggregate.get('subjects_with_missing_bundles') or [])}")
    for taxonomy_class, subjects in sorted(_safe_dict(board_rows_aggregate.get('failure_taxonomy_subjects')).items()):
        print(f"fleet_board_failure_taxonomy_subjects_{taxonomy_class}={','.join(subjects or [])}")
    print(
        "fleet_board_state_source_counts="
        + ",".join(
            f"{state}:{count}" for state, count in sorted(_safe_dict(board_state_sources_aggregate.get('state_source_counts')).items())
        )
    )
    print(f"fleet_board_next_action_source_subjects={','.join(board_state_sources_aggregate.get('subjects_with_next_action_source') or [])}")
    print(f"fleet_board_blocking_reason_source_subjects={','.join(board_state_sources_aggregate.get('subjects_with_blocking_reason_source') or [])}")
    print(f"fleet_qa_axes_posture={qa_axes_aggregate.get('overall_posture')}")
    print(f"fleet_budget_posture={lineage_aggregate.get('budget_posture')}")
    print(f"fleet_budget_attention={lineage_aggregate.get('budget_attention')}")
    print(f"fleet_budget_summary_line={lineage_aggregate.get('budget_summary_line')}")
    print(f"fleet_qa_axes_attention_subjects={','.join(qa_axes_aggregate.get('subjects_with_attention') or [])}")
    print(f"fleet_qa_axes_not_ready_subjects={','.join(qa_axes_aggregate.get('not_ready_subjects') or [])}")
    print(f"fleet_qa_axes_axes={','.join(sorted((_safe_dict(qa_axes_aggregate.get('axes'))).keys()))}")
    print(f"db_candidate_fleet_verdict={db_candidate_fleet.get('verdict')}")
    print(f"db_candidate_fleet_reason={db_candidate_fleet.get('reason_code')}")
    print(f"db_candidate_fleet_summary={db_candidate_fleet.get('summary_line')}")
    print(f"db_candidate_current_artifact_id={db_candidate_fleet.get('current_artifact_id')}")
    print(f"db_candidate_selected_artifact_id={db_candidate_fleet.get('selected_artifact_id')}")
    print(f"db_candidate_best_artifact_id={db_candidate_fleet.get('best_candidate_artifact_id')}")
    print(f"db_candidate_selected_matches_best={db_candidate_fleet.get('selected_matches_best')}")
    print(f"db_candidate_current_matches_best={db_candidate_fleet.get('current_matches_best')}")
    print(f"db_candidate_history_count={len(db_candidate_history)}")
    board_history_rows = [
        _safe_dict(item)
        for item in (board_rows.get('history') or [])
        if isinstance(item, dict)
    ]
    if board_history_rows:
        first_board_history = board_history_rows[0]
        print(f"board_history_1_subject={first_board_history.get('subject')}")
        print(f"board_history_1_status={first_board_history.get('status_semantic')}")
        print(f"board_history_1_blocking_reason={first_board_history.get('blocking_reason')}")
        print(f"board_history_1_next_action={first_board_history.get('next_action')}")
        print(f"board_history_1_selected_artifact_id={first_board_history.get('selected_artifact_id')}")
        print(f"board_history_1_selected_is_current={first_board_history.get('selected_is_current')}")
        print(f"board_history_1_strongest_slot={first_board_history.get('strongest_slot')}")
        print(f"board_history_1_generated_at_utc={first_board_history.get('generated_at_utc')}")
        print(f"board_history_1_dispatch_state={first_board_history.get('dispatch_state')}")
        print(f"board_history_1_bundle_count={first_board_history.get('bundle_count')}")
        print(f"board_history_1_missing_bundle_count={first_board_history.get('missing_bundle_count')}")
        print(f"board_history_1_lineage_sla_summary={first_board_history.get('lineage_sla_summary')}")
        print(f"board_history_1_failure_taxonomy_class={first_board_history.get('failure_taxonomy_class')}")
        print(f"board_history_1_failure_taxonomy_reason={first_board_history.get('failure_taxonomy_reason')}")
        print(f"board_history_1_failure_taxonomy_summary={first_board_history.get('failure_taxonomy_summary')}")
        print(f"board_history_1_summary={first_board_history.get('summary_line')}")
    if db_candidate_history:
        first_history = db_candidate_history[0]
        print(f"db_candidate_history_1_subject={first_history.get('subject')}")
        print(f"db_candidate_history_1_verdict={first_history.get('verdict')}")
        print(f"db_candidate_history_1_reason={first_history.get('reason_code')}")
        print(f"db_candidate_history_1_summary={first_history.get('summary_line')}")
        print(f"db_candidate_history_1_current_artifact_id={first_history.get('current_artifact_id')}")
        print(f"db_candidate_history_1_best_artifact_id={first_history.get('best_candidate_artifact_id')}")
        print(f"db_candidate_history_1_canonical_lifecycle_state={first_history.get('canonical_lifecycle_state')}")
        print(f"db_candidate_history_1_canonical_lifecycle_reason={first_history.get('canonical_lifecycle_reason')}")
        print(f"db_candidate_history_1_dispatch_state={first_history.get('dispatch_state')}")
        print(f"db_candidate_history_1_dispatch_receipt_state={first_history.get('dispatch_receipt_state')}")
        print(f"db_candidate_history_1_dispatch_receipt_channel={first_history.get('dispatch_receipt_channel')}")
        print(f"db_candidate_history_1_dispatch_receipt_error={first_history.get('dispatch_receipt_error')}")
    print(f"fleet_ready_subjects={','.join(board_aggregate.get('ready_subjects') or [])}")
    print(f"fleet_review_subjects={','.join(board_aggregate.get('review_required_subjects') or [])}")
    print(f"fleet_governance_action_required_subjects={','.join(board_aggregate.get('governance_action_required_subjects') or [])}")
    print(f"fleet_blocked_subjects={','.join(board_aggregate.get('blocked_subjects') or [])}")
    print(f"fleet_attention_subjects={','.join(board_aggregate.get('attention_subjects') or [])}")
    print(f"main_history_count={len(payload.get('history') or [])}")
    print(f"candidate_count={len(payload.get('db_candidates') or [])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified operator board for FSJ delivery state across MAIN and support domains.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--business-date")
    target.add_argument("--latest", action="store_true", help="Resolve the latest active MAIN business date and render the board")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.latest:
        business_date = None
    else:
        business_date = args.business_date

    payload = build_board_payload(business_date=business_date, history_limit=args.history_limit)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
