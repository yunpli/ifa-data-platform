#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ifa_data_platform.fsj.report_dispatch import MainReportDeliveryDispatchHelper
from ifa_data_platform.fsj.store import FSJStore

_VALID_SLOT_KEYS = {"early", "mid", "late"}
_VALID_DOMAINS = {"macro", "commodities", "ai_tech"}
_BEIJING = timezone(timedelta(hours=8))


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _surface_summary(surface: dict[str, Any] | None, *, store: FSJStore | None = None) -> dict[str, Any] | None:
    if not surface:
        return None
    return (store or FSJStore()).report_workflow_handoff_from_surface(surface)


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
    helper = MainReportDeliveryDispatchHelper()
    if business_date is None:
        main_latest = _resolve_main_latest(store=store)
        business_date = str((main_latest or {}).get("business_date") or "") or None
        resolution = {"mode": "latest_active_lookup", "business_date": business_date, "status": "resolved" if business_date else "not_found"}
    else:
        resolution = {"mode": "explicit_business_date", "business_date": business_date}
    main_active = store.get_active_report_delivery_surface(business_date=business_date, agent_domain="main", artifact_family="main_final_report") if business_date else None
    support_surfaces: dict[str, dict[str, Any] | None] = {
        domain: store.get_active_report_delivery_surface(business_date=business_date, agent_domain=domain, artifact_family="support_domain_report") if business_date else None
        for domain in sorted(_VALID_DOMAINS)
    }
    history = store.list_report_delivery_surfaces(business_date=business_date, agent_domain="main", artifact_family="main_final_report", statuses=["active", "superseded"], limit=history_limit) if business_date else []
    db_candidates = helper.list_db_delivery_candidates(business_date=business_date, store=store, limit=history_limit) if business_date else []
    return {
        "business_date": business_date,
        "resolution": resolution,
        "main": _surface_summary(main_active, store=store),
        "support": {domain: _surface_summary(surface, store=store) for domain, surface in support_surfaces.items()},
        "history": [_surface_summary(surface, store=store) for surface in history],
        "db_candidates": [helper.summarize_candidate(candidate) for candidate in db_candidates],
    }


def _print_text(payload: dict[str, Any]) -> None:
    resolution = _safe_dict(payload.get("resolution"))
    print(f"business_date={payload.get('business_date') or '-'}")
    print(f"resolution_mode={resolution.get('mode') or '-'}")
    main = _safe_dict(payload.get("main"))
    if main:
        print(f"main_artifact_id={_safe_dict(main.get('artifact')).get('artifact_id')}")
        print(f"main_recommended_action={_safe_dict(main.get('state')).get('recommended_action')}")
        print(f"main_workflow_state={_safe_dict(main.get('state')).get('workflow_state')}")
        print(f"main_package_state={_safe_dict(main.get('state')).get('package_state')}")
    else:
        print("main_artifact=NONE")
    for domain in sorted(_VALID_DOMAINS):
        item = _safe_dict((payload.get("support") or {}).get(domain))
        if not item:
            print(f"support_{domain}=NONE")
            continue
        state = _safe_dict(item.get("state"))
        print(f"support_{domain}_artifact_id={_safe_dict(item.get('artifact')).get('artifact_id')}")
        print(f"support_{domain}_recommended_action={state.get('recommended_action')}")
        print(f"support_{domain}_workflow_state={state.get('workflow_state')}")
        print(f"support_{domain}_package_state={state.get('package_state')}")
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
