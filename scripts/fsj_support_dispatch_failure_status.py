#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from ifa_data_platform.fsj.store import FSJStore
from scripts.fsj_send_dispatch_failure_status import (
    _classify_dispatch_failure,
    _print_text,
)
from scripts.fsj_support_delivery_status import (
    _surface_summary,
    build_status_payload as build_support_status_payload,
)

_VALID_SLOTS = ("early", "late")
_VALID_DOMAINS = ("macro", "commodities", "ai_tech")


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _history_row(surface: dict[str, Any] | None) -> dict[str, Any]:
    summary = _safe_dict(surface)
    artifact = _safe_dict(summary.get("artifact"))
    state = _safe_dict(summary.get("state"))
    lifecycle = _safe_dict(summary.get("canonical_lifecycle"))
    review_summary = _safe_dict(summary.get("review_summary"))
    artifact_lineage = _safe_dict(summary.get("artifact_lineage"))
    bundle_summary = _safe_dict(artifact_lineage.get("bundle_lineage_summary"))
    received = _safe_dict(artifact_lineage.get("what_user_received"))
    dispatch_receipt = _safe_dict(summary.get("dispatch_receipt") or review_summary.get("dispatch_receipt"))
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
        "review_blocking_item_count": review_summary.get("review_blocking_item_count"),
        "review_warning_item_count": review_summary.get("review_warning_item_count"),
        "send_blocker_count": review_summary.get("send_blocker_count"),
        "governance_blocking_reasons": list(review_summary.get("governance_blocking_reasons") or []),
        "bundle_count": bundle_summary.get("bundle_count"),
        "missing_bundle_count": bundle_summary.get("missing_bundle_count"),
        "dispatch_state": summary.get("dispatch_state") or received.get("dispatch_state") or review_summary.get("dispatch_state"),
        "provider_message_id": received.get("provider_message_id"),
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


def build_dispatch_failure_payload(
    *,
    business_date: str,
    agent_domain: str,
    history_limit: int = 5,
    resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status_payload = build_support_status_payload(
        business_date=business_date,
        agent_domain=agent_domain,
        history_limit=history_limit,
        resolution=resolution,
    )
    active_surface = _surface_summary(status_payload.get("active_surface")) if status_payload.get("active_surface") else None
    history = [_surface_summary(item) for item in (status_payload.get("history") or [])]
    return {
        "business_date": business_date,
        "agent_domain": agent_domain,
        "resolution": dict(status_payload.get("resolution") or resolution or {}),
        "active_surface": active_surface,
        "history": history,
        "history_rows": [_history_row(item) for item in history],
        "dispatch_failure": _classify_dispatch_failure(active_surface),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Operator helper for support-domain send/dispatch failure posture. "
            "This reads DB/operator truth only; downstream channel delivery receipts are not modeled here."
        )
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--business-date")
    target.add_argument("--latest", action="store_true", help="Resolve latest active support delivery surface from DB truth")
    parser.add_argument("--agent-domain", required=True, choices=_VALID_DOMAINS)
    parser.add_argument("--slot", choices=_VALID_SLOTS, help="Optional strongest-slot filter when resolving --latest")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.business_date:
        business_date = args.business_date
        resolution = {
            "mode": "explicit_business_date",
            "business_date": business_date,
            "agent_domain": args.agent_domain,
        }
    else:
        store = FSJStore()
        active_surface = store.get_latest_active_report_operator_review_surface(
            agent_domain=args.agent_domain,
            artifact_family="support_domain_report",
            strongest_slot=args.slot,
        )
        active_surface = _surface_summary(active_surface, store=store) if active_surface else None
        artifact = _safe_dict(_safe_dict(active_surface).get("artifact"))
        if not artifact.get("business_date"):
            payload = {
                "business_date": None,
                "agent_domain": args.agent_domain,
                "resolution": {
                    "mode": "latest_active_lookup",
                    "requested_slot": args.slot,
                    "business_date": None,
                    "agent_domain": args.agent_domain,
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
            "agent_domain": args.agent_domain,
            "resolved_artifact_id": artifact.get("artifact_id"),
            "resolved_report_run_id": artifact.get("report_run_id"),
            "resolved_slot": slot_evaluation.get("strongest_slot"),
            "status": "resolved",
        }

    payload = build_dispatch_failure_payload(
        business_date=business_date,
        agent_domain=args.agent_domain,
        history_limit=args.history_limit,
        resolution=resolution,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
