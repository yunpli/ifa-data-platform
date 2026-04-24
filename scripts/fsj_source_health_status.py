#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from ifa_data_platform.fsj.store import FSJStore

_VALID_DOMAINS = ("macro", "commodities", "ai_tech")


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _subject_entry(surface: dict[str, Any] | None, *, subject: str) -> dict[str, Any] | None:
    if not surface:
        return None
    artifact = _safe_dict(surface.get("artifact"))
    state = _safe_dict(surface.get("state"))
    review_summary = _safe_dict(surface.get("review_summary"))
    canonical_lifecycle = _safe_dict(surface.get("canonical_lifecycle"))
    source_health = _safe_dict(review_summary.get("source_health"))
    status = str(source_health.get("overall_status") or "healthy")
    blocking_slot_count = int(source_health.get("blocking_slot_count") or 0)
    degraded_slot_count = int(source_health.get("degraded_slot_count") or 0)
    slots = list(source_health.get("slots") or [])
    slot_bits = []
    for item in slots:
        item_dict = _safe_dict(item)
        slot = str(item_dict.get("slot") or "")
        item_status = str(item_dict.get("status") or "")
        reason = str(item_dict.get("degrade_reason") or "")
        if slot:
            bit = f"{slot}:{item_status or 'unknown'}"
            if reason:
                bit += f":{reason}"
            slot_bits.append(bit)
    reasons = [
        str(item.get("degrade_reason") or "").strip()
        for item in slots
        if str(item.get("degrade_reason") or "").strip()
    ]
    unique_reasons = []
    seen: set[str] = set()
    for reason in reasons:
        if reason not in seen:
            unique_reasons.append(reason)
            seen.add(reason)
    needs_attention = status in {"blocked", "degraded"}
    entry = {
        "subject": subject,
        "artifact_id": artifact.get("artifact_id"),
        "business_date": artifact.get("business_date"),
        "recommended_action": state.get("recommended_action"),
        "workflow_state": state.get("workflow_state"),
        "canonical_lifecycle_state": canonical_lifecycle.get("state"),
        "canonical_lifecycle_reason": canonical_lifecycle.get("reason"),
        "source_health_status": status,
        "source_health_blocking_slot_count": blocking_slot_count,
        "source_health_degraded_slot_count": degraded_slot_count,
        "source_health_slots": slots,
        "source_health_reasons": unique_reasons,
        "source_health_attention": needs_attention,
    }
    parts = [f"{subject}: {status}"]
    if blocking_slot_count:
        parts.append(f"blocking_slots={blocking_slot_count}")
    if degraded_slot_count:
        parts.append(f"degraded_slots={degraded_slot_count}")
    if unique_reasons:
        parts.append(f"reasons={','.join(unique_reasons)}")
    if slot_bits:
        parts.append(f"slots={','.join(slot_bits)}")
    if entry["recommended_action"]:
        parts.append(f"action={entry['recommended_action']}")
    if entry["canonical_lifecycle_state"]:
        parts.append(f"lifecycle={entry['canonical_lifecycle_state']}")
    entry["summary_line"] = " | ".join(parts)
    return entry



def build_source_health_status_payload(*, business_date: str | None = None, history_limit: int = 5, include_healthy: bool = False, store: FSJStore | None = None) -> dict[str, Any]:
    store = store or FSJStore()
    board = store.build_operator_board_surface(business_date=business_date, history_limit=history_limit)
    main_entry = _subject_entry(board.get("main"), subject="main")
    support_entries = []
    for domain in _VALID_DOMAINS:
        support_entry = _subject_entry(_safe_dict(board.get("support")).get(domain), subject=f"support:{domain}")
        if support_entry:
            support_entries.append(support_entry)

    subjects = [entry for entry in [main_entry, *support_entries] if entry]
    visible_subjects = [entry for entry in subjects if include_healthy or entry.get("source_health_attention")]
    blocked_subjects = [entry["subject"] for entry in subjects if entry.get("source_health_status") == "blocked"]
    degraded_subjects = [entry["subject"] for entry in subjects if entry.get("source_health_status") == "degraded"]
    healthy_subjects = [entry["subject"] for entry in subjects if entry.get("source_health_status") == "healthy"]
    status_counts: dict[str, int] = {}
    for entry in subjects:
        status = str(entry.get("source_health_status") or "")
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1

    fleet_status = "healthy"
    if blocked_subjects:
        fleet_status = "blocked"
    elif degraded_subjects:
        fleet_status = "degraded"

    attention_subjects = blocked_subjects + [subject for subject in degraded_subjects if subject not in blocked_subjects]
    fleet_summary = (
        f"source-health fleet: {fleet_status} | attention={len(attention_subjects)}/{len(subjects)}"
        f" | blocked={len(blocked_subjects)}"
        f" | degraded={len(degraded_subjects)}"
    )

    return {
        "business_date": board.get("business_date"),
        "resolution": _safe_dict(board.get("resolution")),
        "history_limit": history_limit,
        "include_healthy": include_healthy,
        "fleet": {
            "overall_status": fleet_status,
            "subject_count": len(subjects),
            "attention_subject_count": len(attention_subjects),
            "blocked_subjects": blocked_subjects,
            "degraded_subjects": degraded_subjects,
            "healthy_subjects": healthy_subjects,
            "attention_subjects": attention_subjects,
            "status_counts": status_counts,
            "summary_line": fleet_summary,
        },
        "subjects": visible_subjects,
    }



def _print_text(payload: dict[str, Any]) -> None:
    resolution = _safe_dict(payload.get("resolution"))
    fleet = _safe_dict(payload.get("fleet"))
    print(f"business_date={payload.get('business_date')}")
    print(f"resolution_mode={resolution.get('mode')}")
    print(f"include_healthy={payload.get('include_healthy')}")
    print(f"fleet_summary={fleet.get('summary_line')}")
    print(f"fleet_status_counts=" + ",".join(f"{key}:{value}" for key, value in sorted(_safe_dict(fleet.get('status_counts')).items())))
    print(f"attention_subjects={','.join(fleet.get('attention_subjects') or [])}")
    print(f"blocked_subjects={','.join(fleet.get('blocked_subjects') or [])}")
    print(f"degraded_subjects={','.join(fleet.get('degraded_subjects') or [])}")
    for idx, entry in enumerate(payload.get("subjects") or [], start=1):
        print(f"subject_{idx}={entry.get('summary_line')}")



def main() -> None:
    parser = argparse.ArgumentParser(description="Operator-visible FSJ data-source health attention summary across main/support subjects.")
    parser.add_argument("--business-date")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--include-healthy", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    payload = build_source_health_status_payload(
        business_date=args.business_date,
        history_limit=args.history_limit,
        include_healthy=args.include_healthy,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
