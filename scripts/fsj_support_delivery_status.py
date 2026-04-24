#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ifa_data_platform.fsj.store import FSJStore

_VALID_SLOT_KEYS = {"early", "late"}
_VALID_DOMAINS = {"macro", "commodities", "ai_tech"}
_BEIJING = timezone(timedelta(hours=8))


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _surface_summary(surface: dict[str, Any], *, store: FSJStore | None = None) -> dict[str, Any]:
    if surface.get("review_summary") and store is None:
        return dict(surface or {})
    resolver = store or FSJStore()
    summary = surface if surface.get("review_summary") else resolver.report_operator_review_surface_from_surface(surface)
    summary = dict(summary or {})
    projector = getattr(resolver, "report_artifact_lineage_from_surface", None)
    if summary and not summary.get("artifact_lineage") and callable(projector):
        summary["artifact_lineage"] = projector(summary)
    return summary


def resolve_latest_support_business_date(*, agent_domain: str, slot: str | None = None, store: FSJStore | None = None) -> dict[str, Any] | None:
    if agent_domain not in _VALID_DOMAINS:
        raise ValueError(f"unsupported agent_domain: {agent_domain}")
    if slot is not None and slot not in _VALID_SLOT_KEYS:
        raise ValueError(f"unsupported slot: {slot}")

    store = store or FSJStore()
    surface = store.get_latest_active_report_operator_review_surface(
        agent_domain=agent_domain,
        artifact_family="support_domain_report",
        strongest_slot=slot,
        max_business_date=datetime.now(_BEIJING).date(),
    )
    if not surface:
        return None
    artifact = _safe_dict(surface.get("artifact"))
    package_state = _safe_dict(surface.get("package_state"))
    slot_evaluation = _safe_dict(package_state.get("slot_evaluation"))
    return {
        "business_date": artifact.get("business_date"),
        "artifact_id": artifact.get("artifact_id"),
        "report_run_id": artifact.get("report_run_id"),
        "status": artifact.get("status"),
        "updated_at": artifact.get("updated_at"),
        "slot": slot_evaluation.get("strongest_slot"),
    }


def build_status_payload(*, business_date: str, agent_domain: str, history_limit: int = 5, resolution: dict[str, Any] | None = None) -> dict[str, Any]:
    store = FSJStore()
    active_surface = store.get_active_report_operator_review_surface(
        business_date=business_date,
        agent_domain=agent_domain,
        artifact_family="support_domain_report",
    )
    history_surfaces = store.list_report_operator_review_surfaces(
        business_date=business_date,
        agent_domain=agent_domain,
        artifact_family="support_domain_report",
        statuses=["active", "superseded"],
        limit=history_limit,
    )
    active_summary = _surface_summary(active_surface) if active_surface else None
    history_summaries = [_surface_summary(surface) for surface in history_surfaces]
    ranked_candidates = _safe_dict(active_summary.get("candidate_comparison")).get("ranked_candidates") if active_summary else []
    db_candidates = [
        _safe_dict(item)
        for item in (ranked_candidates or [])
        if isinstance(item, dict)
    ]
    rerun_compare_summary = store.summarize_rerun_compare_surface(active_summary, db_candidates, subject=f"support:{agent_domain}") if active_summary else None
    return {
        "business_date": business_date,
        "agent_domain": agent_domain,
        "resolution": dict(resolution or {"mode": "explicit_business_date", "business_date": business_date, "agent_domain": agent_domain}),
        "active_surface": active_summary,
        "history": history_summaries,
        "db_candidates": db_candidates,
        "db_candidate_alignment_summary": rerun_compare_summary,
        "rerun_compare_summary": rerun_compare_summary,
        "db_candidate_history_summary": store.summarize_db_candidate_history(history_summaries, db_candidates),
    }


def _artifact_row(surface: dict[str, Any] | None) -> dict[str, Any]:
    summary = _safe_dict(surface)
    artifact = _safe_dict(summary.get("artifact"))
    state = _safe_dict(summary.get("state"))
    lifecycle = _safe_dict(summary.get("canonical_lifecycle"))
    review_summary = _safe_dict(summary.get("review_summary"))
    artifact_lineage = _safe_dict(summary.get("artifact_lineage"))
    bundle_summary = _safe_dict(artifact_lineage.get("bundle_lineage_summary"))
    received = _safe_dict(artifact_lineage.get("what_user_received"))
    return {
        "artifact_id": artifact.get("artifact_id"),
        "report_run_id": artifact.get("report_run_id"),
        "status": artifact.get("status"),
        "workflow_state": state.get("workflow_state"),
        "recommended_action": state.get("recommended_action"),
        "package_state": state.get("package_state"),
        "ready_for_delivery": state.get("ready_for_delivery"),
        "send_ready": state.get("send_ready"),
        "review_required": state.get("review_required"),
        "canonical_lifecycle_state": lifecycle.get("state") or review_summary.get("canonical_lifecycle_state"),
        "canonical_lifecycle_reason": lifecycle.get("reason") or review_summary.get("canonical_lifecycle_reason"),
        "selected_is_current": _safe_dict(summary.get("selected_handoff")).get("selected_is_current"),
        "qa_score": review_summary.get("qa_score", state.get("qa_score")),
        "blocker_count": review_summary.get("blocker_count", state.get("blocker_count")),
        "warning_count": review_summary.get("warning_count", state.get("warning_count")),
        "go_no_go_decision": review_summary.get("go_no_go_decision"),
        "operator_decision_rationale": review_summary.get("operator_decision_rationale"),
        "operator_next_step": review_summary.get("operator_next_step"),
        "operator_action_required": review_summary.get("operator_action_required"),
        "promotion_authority_status": review_summary.get("promotion_authority_status"),
        "promotion_authority_approved": review_summary.get("promotion_authority_approved"),
        "promotion_authority_required_action": review_summary.get("promotion_authority_required_action"),
        "promotion_authority_rationale": review_summary.get("promotion_authority_rationale"),
        "promotion_authority_summary": review_summary.get("promotion_authority_summary"),
        "review_blocking_item_count": review_summary.get("review_blocking_item_count"),
        "review_warning_item_count": review_summary.get("review_warning_item_count"),
        "send_blocker_count": review_summary.get("send_blocker_count"),
        "governance_blocking_reasons": list(review_summary.get("governance_blocking_reasons") or []),
        "bundle_count": bundle_summary.get("bundle_count"),
        "missing_bundle_count": bundle_summary.get("missing_bundle_count"),
        "dispatch_state": received.get("dispatch_state"),
        "provider_message_id": received.get("provider_message_id"),
    }


def _print_text(payload: dict[str, Any]) -> None:
    active = payload.get("active_surface") or {}
    artifact = _safe_dict(active.get("artifact"))
    selected = _safe_dict(active.get("selected_handoff"))
    state = _safe_dict(active.get("state"))
    pointers = _safe_dict(active.get("package_paths") or active.get("manifest_pointers"))
    llm_lineage = _safe_dict(active.get("llm_lineage"))
    llm_summary = _safe_dict(llm_lineage.get("summary"))
    llm_lineage_summary = _safe_dict(active.get("llm_lineage_summary"))
    llm_role_policy = _safe_dict(active.get("llm_role_policy"))
    canonical_lifecycle = _safe_dict(active.get("canonical_lifecycle"))
    artifact_lineage = _safe_dict(active.get("artifact_lineage"))
    bundle_summary = _safe_dict(artifact_lineage.get("bundle_lineage_summary"))
    received = _safe_dict(artifact_lineage.get("what_user_received"))
    history_rows = [_artifact_row(item) for item in (payload.get("history") or [])]
    db_candidate_alignment = _safe_dict(payload.get("db_candidate_alignment_summary"))
    rerun_compare = _safe_dict(payload.get("rerun_compare_summary"))
    db_candidate_history = [_safe_dict(item) for item in (payload.get("db_candidate_history_summary") or []) if isinstance(item, dict)]
    resolution = _safe_dict(payload.get("resolution"))
    print(f"business_date={payload.get('business_date')}")
    print(f"agent_domain={payload.get('agent_domain')}")
    print(f"resolution_mode={resolution.get('mode')}")
    if resolution.get("requested_slot"):
        print(f"requested_slot={resolution.get('requested_slot')}")
    if resolution.get("resolved_artifact_id"):
        print(f"resolved_artifact_id={resolution.get('resolved_artifact_id')}")
    if resolution.get("resolved_slot"):
        print(f"resolved_slot={resolution.get('resolved_slot')}")
    if not active:
        print("active_artifact=NONE")
        return
    print(f"active_artifact_id={artifact.get('artifact_id')}")
    print(f"active_report_run_id={artifact.get('report_run_id')}")
    print(f"active_status={artifact.get('status')}")
    print(f"selected_artifact_id={selected.get('selected_artifact_id')}")
    print(f"selected_is_current={selected.get('selected_is_current')}")
    print(f"recommended_action={state.get('recommended_action')}")
    print(f"dispatch_recommended_action={state.get('dispatch_recommended_action')}")
    print(f"workflow_state={state.get('workflow_state')}")
    print(f"canonical_lifecycle_state={canonical_lifecycle.get('state')}")
    print(f"canonical_lifecycle_reason={canonical_lifecycle.get('reason')}")
    print(f"transition_integrity_valid={_safe_dict(active.get('transition_integrity')).get('valid')}")
    print(f"transition_integrity_reason={_safe_dict(active.get('transition_integrity')).get('reason_code')}")
    print(f"go_no_go_decision={_safe_dict(active.get('review_summary')).get('go_no_go_decision')}")
    print(f"operator_decision_rationale={_safe_dict(active.get('review_summary')).get('operator_decision_rationale')}")
    print(f"operator_action_required={_safe_dict(active.get('review_summary')).get('operator_action_required')}")
    print(f"promotion_authority_status={_safe_dict(active.get('review_summary')).get('promotion_authority_status')}")
    print(f"promotion_authority_approved={_safe_dict(active.get('review_summary')).get('promotion_authority_approved')}")
    print(f"promotion_authority_required_action={_safe_dict(active.get('review_summary')).get('promotion_authority_required_action')}")
    print(f"promotion_authority_rationale={_safe_dict(active.get('review_summary')).get('promotion_authority_rationale')}")
    print(f"promotion_authority_summary={_safe_dict(active.get('review_summary')).get('promotion_authority_summary')}")
    print(f"review_blocking_item_count={_safe_dict(active.get('review_summary')).get('review_blocking_item_count')}")
    print(f"review_warning_item_count={_safe_dict(active.get('review_summary')).get('review_warning_item_count')}")
    print(f"send_blocker_count={_safe_dict(active.get('review_summary')).get('send_blocker_count')}")
    print(f"governance_blocking_reasons={','.join(_safe_dict(active.get('review_summary')).get('governance_blocking_reasons') or [])}")
    print(f"send_ready={state.get('send_ready')}")
    print(f"review_required={state.get('review_required')}")
    print(f"next_step={state.get('next_step')}")
    print(f"selection_reason={state.get('selection_reason')}")
    print(f"dispatch_selected_artifact_id={state.get('dispatch_selected_artifact_id')}")
    print(f"package_state={state.get('package_state')}")
    print(f"ready_for_delivery={state.get('ready_for_delivery')}")
    print(f"qa_score={state.get('qa_score')}")
    print(f"blocker_count={state.get('blocker_count')}")
    print(f"warning_count={state.get('warning_count')}")
    print(f"delivery_manifest_path={pointers.get('delivery_manifest_path')}")
    print(f"send_manifest_path={pointers.get('send_manifest_path')}")
    print(f"review_manifest_path={pointers.get('review_manifest_path')}")
    print(f"workflow_manifest_path={pointers.get('workflow_manifest_path')}")
    print(f"package_index_path={pointers.get('package_index_path')}")
    print(f"delivery_zip_path={pointers.get('delivery_zip_path')}")
    print(f"lineage_bundle_count={bundle_summary.get('bundle_count')}")
    print(f"lineage_missing_bundle_count={bundle_summary.get('missing_bundle_count')}")
    print(f"lineage_bundle_slots={','.join(bundle_summary.get('slots') or [])}")
    print(f"lineage_bundle_section_keys={','.join(bundle_summary.get('section_keys') or [])}")
    print(f"lineage_dispatch_state={received.get('dispatch_state')}")
    print(f"lineage_dispatch_channel={received.get('channel')}")
    print(f"lineage_provider_message_id={received.get('provider_message_id')}")
    print(f"lineage_sent_at={received.get('sent_at')}")
    print(f"lineage_dispatch_error={received.get('error')}")
    print(f"llm_bundle_count={llm_summary.get('bundle_count')}")
    print(f"llm_applied_count={llm_summary.get('applied_count')}")
    print(f"llm_degraded_count={llm_summary.get('degraded_count')}")
    print(f"llm_fallback_count={llm_summary.get('fallback_applied_count')}")
    print(f"llm_operator_tags={','.join(llm_summary.get('operator_tags') or [])}")
    print(f"llm_models={','.join(llm_lineage_summary.get('models') or [])}")
    print(f"llm_usage_bundle_count={llm_lineage_summary.get('usage_bundle_count')}")
    print(f"llm_total_tokens={_safe_dict(llm_lineage_summary.get('token_totals')).get('total_tokens')}")
    print(f"llm_estimated_cost_usd={llm_lineage_summary.get('estimated_cost_usd')}")
    print(f"llm_uncosted_bundle_count={llm_lineage_summary.get('uncosted_bundle_count')}")
    print(f"llm_lineage_status={llm_lineage_summary.get('status')}")
    print(f"llm_lineage_summary={llm_lineage_summary.get('summary_line')}")
    print(f"llm_policy_versions={','.join(llm_role_policy.get('policy_versions') or [])}")
    print(f"llm_boundary_modes={','.join(llm_role_policy.get('boundary_modes') or [])}")
    print(f"llm_forbidden_decision_count={len(llm_role_policy.get('forbidden_decisions') or [])}")
    print(f"llm_deterministic_owner_fields={','.join(llm_role_policy.get('deterministic_owner_fields') or [])}")
    print(f"llm_override_precedence={'>'.join(llm_role_policy.get('override_precedence') or [])}")
    slot_boundary_modes = llm_role_policy.get('slot_boundary_modes') or {}
    slot_boundary_mode_line = ','.join(f"{slot}:{slot_boundary_modes[slot]}" for slot in sorted(slot_boundary_modes))
    print(f"llm_slot_boundary_modes={slot_boundary_mode_line}")
    print(f"db_candidate_verdict={db_candidate_alignment.get('verdict')}")
    print(f"db_candidate_reason={db_candidate_alignment.get('reason_code')}")
    print(f"db_candidate_summary={db_candidate_alignment.get('summary_line')}")
    print(f"db_candidate_current_artifact_id={db_candidate_alignment.get('current_artifact_id')}")
    print(f"db_candidate_selected_artifact_id={db_candidate_alignment.get('selected_artifact_id')}")
    print(f"db_candidate_best_artifact_id={db_candidate_alignment.get('best_candidate_artifact_id')}")
    print(f"db_candidate_candidate_count={db_candidate_alignment.get('candidate_count')}")
    print(f"db_candidate_ready_candidate_count={db_candidate_alignment.get('ready_candidate_count')}")
    print(f"db_candidate_selected_matches_best={db_candidate_alignment.get('selected_matches_best')}")
    print(f"db_candidate_current_matches_best={db_candidate_alignment.get('current_matches_best')}")
    print(f"rerun_compare_outcome={rerun_compare.get('compare_outcome')}")
    print(f"rerun_compare_rerun_outcome={rerun_compare.get('rerun_outcome')}")
    print(f"rerun_compare_rerun_outcome_summary={rerun_compare.get('rerun_outcome_summary')}")
    print(f"rerun_compare_operator_action={rerun_compare.get('operator_action')}")
    print(f"rerun_compare_candidate_present={rerun_compare.get('rerun_candidate_present')}")
    print(f"rerun_compare_candidate_differs_from_current={rerun_compare.get('rerun_candidate_differs_from_current')}")
    print(f"rerun_compare_selected_differs_from_current={rerun_compare.get('selected_candidate_differs_from_current')}")
    print(f"rerun_compare_summary={rerun_compare.get('operator_summary')}")
    print(f"db_candidate_history_count={len(db_candidate_history)}")
    if db_candidate_history:
        first_db_history = db_candidate_history[0]
        print(f"db_candidate_history_1_subject={first_db_history.get('subject')}")
        print(f"db_candidate_history_1_verdict={first_db_history.get('verdict')}")
        print(f"db_candidate_history_1_reason={first_db_history.get('reason_code')}")
        print(f"db_candidate_history_1_summary={first_db_history.get('summary_line')}")
        print(f"db_candidate_history_1_current_artifact_id={first_db_history.get('current_artifact_id')}")
        print(f"db_candidate_history_1_selected_artifact_id={first_db_history.get('selected_artifact_id')}")
        print(f"db_candidate_history_1_best_artifact_id={first_db_history.get('best_candidate_artifact_id')}")
    print(f"history_count={len(history_rows)}")
    for index, row in enumerate(history_rows, start=1):
        print(f"history_{index}_artifact_id={row.get('artifact_id')}")
        print(f"history_{index}_status={row.get('status')}")
        print(f"history_{index}_workflow_state={row.get('workflow_state')}")
        print(f"history_{index}_recommended_action={row.get('recommended_action')}")
        print(f"history_{index}_canonical_lifecycle_state={row.get('canonical_lifecycle_state')}")
        print(f"history_{index}_canonical_lifecycle_reason={row.get('canonical_lifecycle_reason')}")
        print(f"history_{index}_selected_is_current={row.get('selected_is_current')}")
        print(f"history_{index}_go_no_go_decision={row.get('go_no_go_decision')}")
        print(f"history_{index}_operator_decision_rationale={row.get('operator_decision_rationale')}")
        print(f"history_{index}_operator_next_step={row.get('operator_next_step')}")
        print(f"history_{index}_operator_action_required={row.get('operator_action_required')}")
        print(f"history_{index}_promotion_authority_status={row.get('promotion_authority_status')}")
        print(f"history_{index}_promotion_authority_approved={row.get('promotion_authority_approved')}")
        print(f"history_{index}_promotion_authority_required_action={row.get('promotion_authority_required_action')}")
        print(f"history_{index}_promotion_authority_rationale={row.get('promotion_authority_rationale')}")
        print(f"history_{index}_promotion_authority_summary={row.get('promotion_authority_summary')}")
        print(f"history_{index}_review_blocking_item_count={row.get('review_blocking_item_count')}")
        print(f"history_{index}_review_warning_item_count={row.get('review_warning_item_count')}")
        print(f"history_{index}_send_blocker_count={row.get('send_blocker_count')}")
        print(f"history_{index}_governance_blocking_reasons={','.join(row.get('governance_blocking_reasons') or [])}")
        print(f"history_{index}_bundle_count={row.get('bundle_count')}")
        print(f"history_{index}_missing_bundle_count={row.get('missing_bundle_count')}")
        print(f"history_{index}_dispatch_state={row.get('dispatch_state')}")
        print(f"history_{index}_provider_message_id={row.get('provider_message_id')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Operator read surface for support delivery state from DB-backed report artifacts.")
    parser.add_argument("--agent-domain", required=True, choices=sorted(_VALID_DOMAINS))
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--business-date")
    target.add_argument("--latest", action="store_true", help="Resolve the latest active support delivery surface from DB truth")
    parser.add_argument("--slot", choices=sorted(_VALID_SLOT_KEYS), help="Optional support slot filter when resolving --latest")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.business_date:
        resolution = {
            "mode": "explicit_business_date",
            "business_date": args.business_date,
            "agent_domain": args.agent_domain,
        }
        business_date = args.business_date
    else:
        resolved = resolve_latest_support_business_date(agent_domain=args.agent_domain, slot=args.slot)
        if not resolved:
            payload = {
                "business_date": None,
                "agent_domain": args.agent_domain,
                "resolution": {
                    "mode": "latest_active_lookup",
                    "requested_slot": args.slot,
                    "agent_domain": args.agent_domain,
                    "business_date": None,
                    "status": "not_found",
                },
                "active_surface": None,
                "history": [],
            }
            if args.format == "json":
                print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
                return
            _print_text(payload)
            return
        business_date = str(resolved["business_date"])
        resolution = {
            "mode": "latest_active_lookup",
            "requested_slot": args.slot,
            "agent_domain": args.agent_domain,
            "business_date": business_date,
            "resolved_artifact_id": resolved.get("artifact_id"),
            "resolved_report_run_id": resolved.get("report_run_id"),
            "resolved_slot": resolved.get("slot"),
            "status": "resolved",
        }

    payload = build_status_payload(business_date=business_date, agent_domain=args.agent_domain, history_limit=args.history_limit, resolution=resolution)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
