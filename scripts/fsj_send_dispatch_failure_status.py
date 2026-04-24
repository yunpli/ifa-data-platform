#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ifa_data_platform.fsj.store import FSJStore
from scripts.fsj_main_delivery_status import (
    _artifact_row as _main_artifact_row,
    _surface_summary,
    build_status_payload as build_main_status_payload,
)


_REQUIRED_ARTIFACT_KEYS = (
    "delivery_manifest_path",
    "send_manifest_path",
    "review_manifest_path",
    "workflow_manifest_path",
    "delivery_zip_path",
)
_OPTIONAL_ARTIFACT_KEYS = (
    "telegram_caption_path",
    "operator_review_bundle_path",
    "operator_review_readme_path",
    "package_index_path",
)


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _path_exists(value: Any) -> bool:
    path = str(value or "").strip()
    return bool(path) and Path(path).exists()


def _artifact_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    package_paths = _safe_dict(surface.get("package_paths") or surface.get("manifest_pointers"))
    checks: list[dict[str, Any]] = []
    for key in [*_REQUIRED_ARTIFACT_KEYS, *_OPTIONAL_ARTIFACT_KEYS]:
        path = package_paths.get(key)
        exists = _path_exists(path)
        checks.append(
            {
                "artifact": key,
                "required": key in _REQUIRED_ARTIFACT_KEYS,
                "path": path,
                "exists": exists,
                "status": "pass" if exists or key in _OPTIONAL_ARTIFACT_KEYS else "fail",
            }
        )
    return checks


def _classify_dispatch_failure(surface: dict[str, Any] | None) -> dict[str, Any]:
    if not surface:
        return {
            "dispatch_posture": "no_active_artifact",
            "failure_reasons": ["no_active_artifact"],
            "missing_required_artifacts": [],
            "action_summary": "no active MAIN delivery surface is available; resolve the correct business date or rerun publishing",
            "channel_delivery_truth": "unknown_not_modeled",
        }

    artifact = _safe_dict(surface.get("artifact"))
    state = _safe_dict(surface.get("state"))
    selected_handoff = _safe_dict(surface.get("selected_handoff"))
    operator_go_no_go = _safe_dict(surface.get("operator_go_no_go"))
    send_manifest = _safe_dict(surface.get("send_manifest"))
    review_manifest = _safe_dict(surface.get("review_manifest"))
    review_summary = _safe_dict(surface.get("review_summary"))

    checks = _artifact_checks(surface)
    missing_required = [item["artifact"] for item in checks if item.get("required") and not item.get("exists")]
    send_blockers = [str(item) for item in (state.get("send_blockers") or send_manifest.get("send_blockers") or []) if str(item).strip()]
    blocking_items = list(review_manifest.get("blocking_items") or [])

    failure_reasons: list[str] = []
    if not artifact.get("artifact_id"):
        failure_reasons.append("missing_artifact_id")
    if selected_handoff.get("selected_is_current") is False:
        failure_reasons.append("current_package_not_selected")
    if state.get("recommended_action") == "send_review" or state.get("review_required"):
        failure_reasons.append("manual_review_required")
    if state.get("recommended_action") == "hold":
        failure_reasons.append("recommended_action_hold")
    if send_blockers:
        failure_reasons.extend(send_blockers)
    if blocking_items:
        failure_reasons.append("review_manifest_blocking_items")
    if operator_go_no_go.get("decision") == "NO_GO":
        failure_reasons.append("operator_go_no_go_no_go")
    if operator_go_no_go.get("decision") == "REVIEW":
        failure_reasons.append("operator_go_no_go_review")
    if missing_required:
        failure_reasons.append("required_delivery_artifacts_missing")

    deduped_failure_reasons: list[str] = []
    for item in failure_reasons:
        if item not in deduped_failure_reasons:
            deduped_failure_reasons.append(item)

    if not deduped_failure_reasons:
        dispatch_posture = "ready_to_dispatch"
        action_summary = "package is operator-green for dispatch; if channel delivery still failed, that failure is outside current DB truth"
    elif "required_delivery_artifacts_missing" in deduped_failure_reasons:
        dispatch_posture = "artifact_integrity_failed"
        action_summary = "required delivery artifacts are missing; rebuild or recover the selected package before any resend attempt"
    elif "current_package_not_selected" in deduped_failure_reasons:
        dispatch_posture = "switch_package"
        action_summary = "current package is not the selected dispatch candidate; switch to the selected package and do not send the current one"
    elif "manual_review_required" in deduped_failure_reasons or "operator_go_no_go_review" in deduped_failure_reasons:
        dispatch_posture = "review_required"
        action_summary = "operator review is required before dispatch; inspect review manifest and operator review bundle"
    else:
        dispatch_posture = "hold"
        action_summary = "dispatch is held by package/QA workflow truth; inspect send blockers and review manifest before retrying"

    return {
        "dispatch_posture": dispatch_posture,
        "failure_reasons": deduped_failure_reasons,
        "missing_required_artifacts": missing_required,
        "action_summary": action_summary,
        "channel_delivery_truth": "unknown_not_modeled",
        "artifact_checks": checks,
        "selected_is_current": selected_handoff.get("selected_is_current"),
        "recommended_action": state.get("recommended_action"),
        "workflow_state": state.get("workflow_state"),
        "send_ready": state.get("send_ready"),
        "review_required": state.get("review_required"),
        "next_step": state.get("next_step") or send_manifest.get("next_step"),
        "go_no_go_decision": operator_go_no_go.get("decision") or review_summary.get("go_no_go_decision"),
        "dispatch_selected_artifact_id": state.get("dispatch_selected_artifact_id") or review_summary.get("selected_artifact_id"),
        "current_artifact_id": artifact.get("artifact_id"),
    }


def _history_row(surface: dict[str, Any] | None) -> dict[str, Any]:
    summary = _safe_dict(surface)
    row = dict(_main_artifact_row(summary))
    review_summary = _safe_dict(summary.get("review_summary"))
    dispatch_receipt = _safe_dict(summary.get("dispatch_receipt") or review_summary.get("dispatch_receipt"))
    row.update(
        {
            "dispatch_state": summary.get("dispatch_state") or review_summary.get("dispatch_state"),
            "dispatch_attempted": review_summary.get("dispatch_attempted"),
            "dispatch_succeeded": review_summary.get("dispatch_succeeded"),
            "dispatch_failed": review_summary.get("dispatch_failed"),
            "dispatch_receipt_state": dispatch_receipt.get("dispatch_state") or dispatch_receipt.get("status"),
            "dispatch_receipt_attempted_at": dispatch_receipt.get("attempted_at"),
            "dispatch_receipt_failed_at": dispatch_receipt.get("failed_at"),
            "dispatch_receipt_succeeded_at": dispatch_receipt.get("succeeded_at"),
            "dispatch_receipt_channel": dispatch_receipt.get("channel"),
            "dispatch_receipt_error": dispatch_receipt.get("error"),
        }
    )
    return row


def build_dispatch_failure_payload(*, business_date: str, history_limit: int = 5, resolution: dict[str, Any] | None = None) -> dict[str, Any]:
    status_payload = build_main_status_payload(
        business_date=business_date,
        history_limit=history_limit,
        resolution=resolution,
    )
    active_surface = _surface_summary(status_payload.get("active_surface")) if status_payload.get("active_surface") else None
    history = [_surface_summary(item) for item in (status_payload.get("history") or [])]
    return {
        "business_date": business_date,
        "resolution": dict(status_payload.get("resolution") or resolution or {}),
        "active_surface": active_surface,
        "history": history,
        "history_rows": [_history_row(item) for item in history],
        "dispatch_failure": _classify_dispatch_failure(active_surface),
    }


def _print_text(payload: dict[str, Any]) -> None:
    resolution = _safe_dict(payload.get("resolution"))
    dispatch_failure = _safe_dict(payload.get("dispatch_failure"))
    active = _safe_dict(payload.get("active_surface"))
    package_paths = _safe_dict(active.get("package_paths") or active.get("manifest_pointers"))
    active_review_summary = _safe_dict(active.get("review_summary"))
    active_canonical_lifecycle = _safe_dict(active.get("canonical_lifecycle"))
    active_dispatch_receipt = _safe_dict(active.get("dispatch_receipt") or active_review_summary.get("dispatch_receipt"))
    history_rows = [_safe_dict(item) for item in (payload.get("history_rows") or [])]
    print(f"business_date={payload.get('business_date')}")
    print(f"resolution_mode={resolution.get('mode')}")
    if resolution.get("requested_slot"):
        print(f"requested_slot={resolution.get('requested_slot')}")
    if resolution.get("resolved_artifact_id"):
        print(f"resolved_artifact_id={resolution.get('resolved_artifact_id')}")
    print(f"dispatch_posture={dispatch_failure.get('dispatch_posture')}")
    print(f"failure_reasons={','.join(dispatch_failure.get('failure_reasons') or [])}")
    print(f"missing_required_artifacts={','.join(dispatch_failure.get('missing_required_artifacts') or [])}")
    print(f"action_summary={dispatch_failure.get('action_summary')}")
    print(f"channel_delivery_truth={dispatch_failure.get('channel_delivery_truth')}")
    print(f"current_artifact_id={dispatch_failure.get('current_artifact_id')}")
    print(f"dispatch_selected_artifact_id={dispatch_failure.get('dispatch_selected_artifact_id')}")
    print(f"selected_is_current={dispatch_failure.get('selected_is_current')}")
    print(f"recommended_action={dispatch_failure.get('recommended_action')}")
    print(f"workflow_state={dispatch_failure.get('workflow_state')}")
    print(f"send_ready={dispatch_failure.get('send_ready')}")
    print(f"review_required={dispatch_failure.get('review_required')}")
    print(f"go_no_go_decision={dispatch_failure.get('go_no_go_decision')}")
    print(f"next_step={dispatch_failure.get('next_step')}")
    print(f"canonical_lifecycle_state={active_canonical_lifecycle.get('state') or active_review_summary.get('canonical_lifecycle_state')}")
    print(f"canonical_lifecycle_reason={active_canonical_lifecycle.get('reason') or active_review_summary.get('canonical_lifecycle_reason')}")
    print(f"dispatch_state={active.get('dispatch_state') or active_review_summary.get('dispatch_state')}")
    print(f"dispatch_receipt_state={active_dispatch_receipt.get('dispatch_state') or active_dispatch_receipt.get('status')}")
    print(f"dispatch_receipt_attempted_at={active_dispatch_receipt.get('attempted_at')}")
    print(f"dispatch_receipt_succeeded_at={active_dispatch_receipt.get('succeeded_at')}")
    print(f"dispatch_receipt_failed_at={active_dispatch_receipt.get('failed_at')}")
    print(f"dispatch_receipt_channel={active_dispatch_receipt.get('channel')}")
    print(f"dispatch_receipt_error={active_dispatch_receipt.get('error')}")
    print(f"delivery_manifest_path={package_paths.get('delivery_manifest_path')}")
    print(f"send_manifest_path={package_paths.get('send_manifest_path')}")
    print(f"review_manifest_path={package_paths.get('review_manifest_path')}")
    print(f"workflow_manifest_path={package_paths.get('workflow_manifest_path')}")
    print(f"operator_review_bundle_path={package_paths.get('operator_review_bundle_path')}")
    print(f"operator_review_readme_path={package_paths.get('operator_review_readme_path')}")
    print(f"delivery_zip_path={package_paths.get('delivery_zip_path')}")
    for index, item in enumerate(dispatch_failure.get("artifact_checks") or [], start=1):
        print(
            f"artifact_check_{index}="
            f"{item.get('artifact')}|required={item.get('required')}|exists={item.get('exists')}|path={item.get('path') or '-'}"
        )
    print(f"history_count={len(history_rows)}")
    for index, row in enumerate(history_rows, start=1):
        print(f"history_{index}_artifact_id={row.get('artifact_id')}")
        print(f"history_{index}_status={row.get('status')}")
        print(f"history_{index}_workflow_state={row.get('workflow_state')}")
        print(f"history_{index}_recommended_action={row.get('recommended_action')}")
        print(f"history_{index}_canonical_lifecycle_state={row.get('canonical_lifecycle_state')}")
        print(f"history_{index}_canonical_lifecycle_reason={row.get('canonical_lifecycle_reason')}")
        print(f"history_{index}_dispatch_state={row.get('dispatch_state')}")
        print(f"history_{index}_dispatch_attempted={row.get('dispatch_attempted')}")
        print(f"history_{index}_dispatch_succeeded={row.get('dispatch_succeeded')}")
        print(f"history_{index}_dispatch_failed={row.get('dispatch_failed')}")
        print(f"history_{index}_dispatch_receipt_state={row.get('dispatch_receipt_state')}")
        print(f"history_{index}_dispatch_receipt_attempted_at={row.get('dispatch_receipt_attempted_at')}")
        print(f"history_{index}_dispatch_receipt_succeeded_at={row.get('dispatch_receipt_succeeded_at')}")
        print(f"history_{index}_dispatch_receipt_failed_at={row.get('dispatch_receipt_failed_at')}")
        print(f"history_{index}_dispatch_receipt_channel={row.get('dispatch_receipt_channel')}")
        print(f"history_{index}_dispatch_receipt_error={row.get('dispatch_receipt_error')}")
        print(f"history_{index}_selected_is_current={row.get('selected_is_current')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Operator helper for MAIN send/dispatch failure posture. "
            "This reads DB/operator truth only; downstream channel delivery receipts are not modeled here."
        )
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--business-date")
    target.add_argument("--latest", action="store_true", help="Resolve latest active MAIN delivery surface from DB truth")
    parser.add_argument("--slot", choices=["early", "mid", "late"], help="Optional strongest-slot filter when resolving --latest")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.business_date:
        business_date = args.business_date
        resolution = {
            "mode": "explicit_business_date",
            "business_date": business_date,
        }
    else:
        store = FSJStore()
        active_surface = store.get_latest_active_report_operator_review_surface(
            agent_domain="main",
            artifact_family="main_final_report",
            strongest_slot=args.slot,
        )
        active_surface = _surface_summary(active_surface, store=store) if active_surface else None
        artifact = _safe_dict(_safe_dict(active_surface).get("artifact"))
        if not artifact.get("business_date"):
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
                "dispatch_failure": _classify_dispatch_failure(None),
            }
            if args.format == "json":
                print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
            else:
                _print_text(payload)
            return
        business_date = str(artifact.get("business_date"))
        package_state = _safe_dict(active_surface.get("package_state"))
        slot_evaluation = _safe_dict(package_state.get("slot_evaluation"))
        resolution = {
            "mode": "latest_active_lookup",
            "requested_slot": args.slot,
            "business_date": business_date,
            "resolved_artifact_id": artifact.get("artifact_id"),
            "resolved_report_run_id": artifact.get("report_run_id"),
            "resolved_strongest_slot": slot_evaluation.get("strongest_slot"),
            "status": "resolved",
        }

    payload = build_dispatch_failure_payload(
        business_date=business_date,
        history_limit=args.history_limit,
        resolution=resolution,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
