#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ifa_data_platform.fsj.report_dispatch import MainReportDeliveryDispatchHelper
from ifa_data_platform.fsj.store import FSJStore

_VALID_SLOT_KEYS = {"early", "mid", "late"}
_BEIJING = timezone(timedelta(hours=8))


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _surface_summary(surface: dict[str, Any]) -> dict[str, Any]:
    artifact = _safe_dict(surface.get("artifact"))
    delivery_package = _safe_dict(surface.get("delivery_package"))
    workflow_linkage = _safe_dict(surface.get("workflow_linkage"))
    workflow = _safe_dict(delivery_package.get("workflow"))
    quality_gate = _safe_dict(delivery_package.get("quality_gate"))
    selected_handoff = _safe_dict(workflow_linkage.get("selected_handoff"))
    artifacts = _safe_dict(delivery_package.get("artifacts"))
    dispatch_advice = _safe_dict(delivery_package.get("dispatch_advice"))
    return {
        "artifact": {
            "artifact_id": artifact.get("artifact_id"),
            "report_run_id": artifact.get("report_run_id"),
            "business_date": artifact.get("business_date"),
            "status": artifact.get("status"),
            "supersedes_artifact_id": artifact.get("supersedes_artifact_id"),
            "created_at": artifact.get("created_at"),
            "updated_at": artifact.get("updated_at"),
        },
        "selected_handoff": {
            "selected_artifact_id": selected_handoff.get("selected_artifact_id"),
            "selected_report_run_id": selected_handoff.get("selected_report_run_id"),
            "selected_business_date": selected_handoff.get("selected_business_date"),
            "selected_is_current": selected_handoff.get("selected_is_current"),
            "selected_delivery_package_dir": selected_handoff.get("delivery_package_dir"),
            "selected_delivery_manifest_path": selected_handoff.get("delivery_manifest_path"),
            "selected_delivery_zip_path": selected_handoff.get("delivery_zip_path"),
            "selected_telegram_caption_path": selected_handoff.get("telegram_caption_path"),
        },
        "state": {
            "package_state": delivery_package.get("package_state"),
            "ready_for_delivery": delivery_package.get("ready_for_delivery"),
            "recommended_action": workflow.get("recommended_action") or dispatch_advice.get("recommended_action"),
            "workflow_state": workflow.get("workflow_state"),
            "send_ready": bool(surface.get("send_ready")),
            "review_required": bool(surface.get("review_required")),
            "qa_score": quality_gate.get("score"),
            "blocker_count": quality_gate.get("blocker_count"),
            "warning_count": quality_gate.get("warning_count"),
            "late_contract_mode": quality_gate.get("late_contract_mode"),
        },
        "manifest_pointers": {
            "delivery_manifest_path": delivery_package.get("delivery_manifest_path"),
            "send_manifest_path": workflow_linkage.get("send_manifest_path"),
            "review_manifest_path": workflow_linkage.get("review_manifest_path"),
            "workflow_manifest_path": workflow_linkage.get("workflow_manifest_path"),
            "operator_review_bundle_path": workflow_linkage.get("operator_review_bundle_path"),
            "operator_review_readme_path": workflow_linkage.get("operator_review_readme_path"),
            "package_index_path": delivery_package.get("package_index_path"),
            "package_browse_readme_path": delivery_package.get("package_browse_readme_path"),
            "telegram_caption_path": delivery_package.get("telegram_caption_path"),
            "delivery_zip_path": delivery_package.get("delivery_zip_path"),
        },
        "version_pointers": {
            "artifact_version": artifact.get("artifact_version"),
            "delivery_manifest_version": artifacts.get("delivery_manifest"),
            "send_manifest_version": artifacts.get("send_manifest"),
            "review_manifest_version": artifacts.get("review_manifest"),
            "workflow_manifest_version": artifacts.get("workflow_manifest"),
            "package_index_version": artifacts.get("package_index"),
        },
    }


def resolve_latest_main_business_date(*, store: FSJStore | None = None, slot: str | None = None) -> dict[str, Any] | None:
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


def build_status_payload(*, business_date: str, history_limit: int = 5, resolution: dict[str, Any] | None = None) -> dict[str, Any]:
    store = FSJStore()
    helper = MainReportDeliveryDispatchHelper()
    active_surface = store.get_active_report_delivery_surface(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
    )
    history_surfaces = store.list_report_delivery_surfaces(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
        statuses=["active", "superseded"],
        limit=history_limit,
    )
    db_candidates = helper.list_db_delivery_candidates(
        business_date=business_date,
        store=store,
        limit=history_limit,
    )
    return {
        "business_date": business_date,
        "resolution": dict(resolution or {"mode": "explicit_business_date", "business_date": business_date}),
        "active_surface": _surface_summary(active_surface) if active_surface else None,
        "history": [_surface_summary(surface) for surface in history_surfaces],
        "db_candidates": [helper.summarize_candidate(candidate) for candidate in db_candidates],
    }


def _print_text(payload: dict[str, Any]) -> None:
    active = payload.get("active_surface") or {}
    artifact = _safe_dict(active.get("artifact"))
    selected = _safe_dict(active.get("selected_handoff"))
    state = _safe_dict(active.get("state"))
    pointers = _safe_dict(active.get("manifest_pointers"))
    resolution = _safe_dict(payload.get("resolution"))
    print(f"business_date={payload.get('business_date')}")
    print(f"resolution_mode={resolution.get('mode')}")
    if resolution.get("requested_slot"):
        print(f"requested_slot={resolution.get('requested_slot')}")
    if resolution.get("resolved_artifact_id"):
        print(f"resolved_artifact_id={resolution.get('resolved_artifact_id')}")
    if resolution.get("resolved_strongest_slot"):
        print(f"resolved_strongest_slot={resolution.get('resolved_strongest_slot')}")
    if not active:
        print("active_artifact=NONE")
        return
    print(f"active_artifact_id={artifact.get('artifact_id')}")
    print(f"active_report_run_id={artifact.get('report_run_id')}")
    print(f"active_status={artifact.get('status')}")
    print(f"selected_artifact_id={selected.get('selected_artifact_id')}")
    print(f"selected_is_current={selected.get('selected_is_current')}")
    print(f"recommended_action={state.get('recommended_action')}")
    print(f"workflow_state={state.get('workflow_state')}")
    print(f"send_ready={state.get('send_ready')}")
    print(f"review_required={state.get('review_required')}")
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
    print(f"history_count={len(payload.get('history') or [])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Operator read surface for MAIN delivery state from DB-backed report artifacts.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--business-date")
    target.add_argument("--latest", action="store_true", help="Resolve the latest active MAIN delivery surface from DB truth")
    parser.add_argument("--slot", choices=sorted(_VALID_SLOT_KEYS), help="Optional strongest-slot filter when resolving --latest")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.business_date:
        resolution = {
            "mode": "explicit_business_date",
            "business_date": args.business_date,
        }
        business_date = args.business_date
    else:
        resolved = resolve_latest_main_business_date(slot=args.slot)
        if not resolved:
            payload = {
                "business_date": None,
                "resolution": {
                    "mode": "latest_active_lookup",
                    "requested_slot": args.slot,
                    "business_date": None,
                    "status": "not_found",
                },
                "active_surface": None,
                "history": [],
                "db_candidates": [],
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
            "business_date": business_date,
            "resolved_artifact_id": resolved.get("artifact_id"),
            "resolved_report_run_id": resolved.get("report_run_id"),
            "resolved_strongest_slot": resolved.get("strongest_slot"),
            "status": "resolved",
        }

    payload = build_status_payload(business_date=business_date, history_limit=args.history_limit, resolution=resolution)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
