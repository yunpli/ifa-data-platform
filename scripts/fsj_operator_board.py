#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ifa_data_platform.fsj.store import FSJStore
from scripts.fsj_drift_monitor import build_drift_payload, format_drift_summary_line

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
    payload = store.build_operator_board_surface(business_date=business_date, history_limit=history_limit)
    if payload.get("support"):
        drift_payloads = {
            "main": build_drift_payload(scope="main", days=7, store=store),
        }
        for domain in sorted(_VALID_DOMAINS):
            drift_payloads[f"support:{domain}"] = build_drift_payload(scope=f"support:{domain}", days=7, store=store)
        payload["drift_summary_lines"] = {
            key: format_drift_summary_line(drift_payload)
            for key, drift_payload in drift_payloads.items()
        }
    else:
        payload["drift_summary_lines"] = {
            "main": format_drift_summary_line(build_drift_payload(scope="main", days=7, store=store)),
        }
    return payload


def _print_text(payload: dict[str, Any]) -> None:
    resolution = _safe_dict(payload.get("resolution"))
    lineage = _safe_dict(payload.get("llm_lineage_summary"))
    lineage_aggregate = _safe_dict(lineage.get("aggregate"))
    role_policy = _safe_dict(payload.get("llm_role_policy_review"))
    role_policy_aggregate = _safe_dict(role_policy.get("aggregate"))
    board_readiness = _safe_dict(payload.get("board_readiness_summary"))
    board_aggregate = _safe_dict(board_readiness.get("aggregate"))
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
    if main:
        print(f"main_artifact_id={_safe_dict(main.get('artifact')).get('artifact_id')}")
        print(f"main_recommended_action={_safe_dict(main.get('state')).get('recommended_action')}")
        print(f"main_workflow_state={_safe_dict(main.get('state')).get('workflow_state')}")
        print(f"main_package_state={_safe_dict(main.get('state')).get('package_state')}")
        print(f"main_llm_lineage_status={main_lineage.get('status')}")
        print(f"main_llm_lineage_summary={main_lineage.get('summary_line')}")
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
        print(f"support_{domain}_artifact_id={_safe_dict(item.get('artifact')).get('artifact_id')}")
        print(f"support_{domain}_recommended_action={state.get('recommended_action')}")
        print(f"support_{domain}_workflow_state={state.get('workflow_state')}")
        print(f"support_{domain}_package_state={state.get('package_state')}")
        print(f"support_{domain}_llm_lineage_status={item_lineage.get('status')}")
        print(f"support_{domain}_llm_lineage_summary={item_lineage.get('summary_line')}")
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
    print(f"fleet_llm_lineage_status={lineage_aggregate.get('overall_status')}")
    print(f"fleet_llm_attention_subjects={','.join(lineage_aggregate.get('attention_subjects') or [])}")
    print(f"fleet_llm_reported_subject_count={lineage_aggregate.get('reported_subject_count')}")
    print(f"fleet_llm_policy_versions={','.join(role_policy_aggregate.get('policy_versions') or [])}")
    print(f"fleet_llm_override_precedence={'>'.join(role_policy_aggregate.get('override_precedence') or [])}")
    print(f"fleet_llm_attention_policy_subjects={','.join(role_policy_aggregate.get('attention_subjects') or [])}")
    drift_lines = _safe_dict(payload.get("drift_summary_lines"))
    print(f"main_drift_summary_line={drift_lines.get('main') or '-'}")
    for domain in sorted(_VALID_DOMAINS):
        key = f"support:{domain}"
        print(f"{key.replace(':', '_')}_drift_summary_line={drift_lines.get(key) or '-'}")
    print(f"fleet_board_posture={board_aggregate.get('overall_posture')}")
    print(f"fleet_qa_axes_posture={qa_axes_aggregate.get('overall_posture')}")
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
    if db_candidate_history:
        first_history = db_candidate_history[0]
        print(f"db_candidate_history_1_subject={first_history.get('subject')}")
        print(f"db_candidate_history_1_verdict={first_history.get('verdict')}")
        print(f"db_candidate_history_1_reason={first_history.get('reason_code')}")
        print(f"db_candidate_history_1_summary={first_history.get('summary_line')}")
        print(f"db_candidate_history_1_current_artifact_id={first_history.get('current_artifact_id')}")
        print(f"db_candidate_history_1_best_artifact_id={first_history.get('best_candidate_artifact_id')}")
    print(f"fleet_ready_subjects={','.join(board_aggregate.get('ready_subjects') or [])}")
    print(f"fleet_review_subjects={','.join(board_aggregate.get('review_required_subjects') or [])}")
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
