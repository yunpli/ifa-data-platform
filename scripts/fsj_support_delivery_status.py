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
    if surface.get("review_summary"):
        return surface
    return (store or FSJStore()).report_operator_review_surface_from_surface(surface)


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
    return {
        "business_date": business_date,
        "agent_domain": agent_domain,
        "resolution": dict(resolution or {"mode": "explicit_business_date", "business_date": business_date, "agent_domain": agent_domain}),
        "active_surface": _surface_summary(active_surface) if active_surface else None,
        "history": [_surface_summary(surface) for surface in history_surfaces],
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
    print(f"llm_bundle_count={llm_summary.get('bundle_count')}")
    print(f"llm_applied_count={llm_summary.get('applied_count')}")
    print(f"llm_degraded_count={llm_summary.get('degraded_count')}")
    print(f"llm_fallback_count={llm_summary.get('fallback_applied_count')}")
    print(f"llm_operator_tags={','.join(llm_summary.get('operator_tags') or [])}")
    print(f"llm_lineage_status={llm_lineage_summary.get('status')}")
    print(f"llm_lineage_summary={llm_lineage_summary.get('summary_line')}")
    print(f"llm_policy_versions={','.join(llm_role_policy.get('policy_versions') or [])}")
    print(f"llm_boundary_modes={','.join(llm_role_policy.get('boundary_modes') or [])}")
    print(f"llm_forbidden_decision_count={len(llm_role_policy.get('forbidden_decisions') or [])}")
    print(f"history_count={len(payload.get('history') or [])}")


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
