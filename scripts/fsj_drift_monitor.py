#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ifa_data_platform.fsj.store import FSJStore

_VALID_SCOPE = {
    "main": ("main", "main_final_report", {"early", "mid", "late"}),
    "support:macro": ("macro", "support_domain_report", {"early", "late"}),
    "support:commodities": ("commodities", "support_domain_report", {"early", "late"}),
    "support:ai_tech": ("ai_tech", "support_domain_report", {"early", "late"}),
}
_BEIJING = timezone(timedelta(hours=8))


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _scope_config(scope: str) -> tuple[str, str, set[str]]:
    if scope not in _VALID_SCOPE:
        raise ValueError(f"unsupported scope: {scope}")
    return _VALID_SCOPE[scope]


def _surface_slot(surface: dict[str, Any]) -> str | None:
    delivery_package = _safe_dict(surface.get("delivery_package"))
    slot_evaluation = _safe_dict(delivery_package.get("slot_evaluation"))
    return str(slot_evaluation.get("strongest_slot") or delivery_package.get("slot") or "").strip() or None


def _surface_matches_slot(surface: dict[str, Any], *, slot: str | None) -> bool:
    if slot is None:
        return True
    return _surface_slot(surface) == slot


def resolve_latest_business_dates(
    *,
    scope: str,
    days: int,
    slot: str | None = None,
    store: FSJStore | None = None,
) -> list[str]:
    agent_domain, artifact_family, valid_slots = _scope_config(scope)
    if slot is not None and slot not in valid_slots:
        raise ValueError(f"unsupported slot for {scope}: {slot}")
    store = store or FSJStore()
    business_dates = store.list_report_business_dates(
        agent_domain=agent_domain,
        artifact_family=artifact_family,
        statuses=["active"],
        limit=max(days, days * 10) if slot else days,
        max_business_date=datetime.now(_BEIJING).date(),
    )
    if slot is None:
        return business_dates

    matched_dates: list[str] = []
    for business_date in business_dates:
        surface = store.get_active_report_delivery_surface(
            business_date=business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
        )
        if surface and _surface_matches_slot(surface, slot=slot):
            matched_dates.append(business_date)
        if len(matched_dates) >= days:
            break
    return matched_dates


def _lineage_attention(summary: dict[str, Any]) -> bool:
    return str(summary.get("status") or "") in {"degraded", "incomplete", "not_applied"}


def _build_day_summary(surface: dict[str, Any], *, business_date: str) -> dict[str, Any]:
    artifact = _safe_dict(surface.get("artifact"))
    state = _safe_dict(surface.get("state"))
    review_summary = _safe_dict(surface.get("review_summary"))
    candidate_comparison = _safe_dict(surface.get("candidate_comparison"))
    selected_handoff = _safe_dict(surface.get("selected_handoff"))
    llm_lineage = _safe_dict(surface.get("llm_lineage"))
    llm_lineage_summary = _safe_dict(surface.get("llm_lineage_summary"))
    llm_summary = _safe_dict(llm_lineage.get("summary"))
    llm_models = [str(item) for item in (llm_lineage_summary.get("models") or []) if str(item).strip()]
    llm_slots = [str(item) for item in (llm_lineage_summary.get("slots") or []) if str(item).strip()]
    llm_token_totals = _safe_dict(llm_lineage_summary.get("token_totals"))
    llm_total_tokens = _safe_int(llm_token_totals.get("total_tokens"))
    llm_usage_bundle_count = _safe_int(llm_lineage_summary.get("usage_bundle_count"))
    llm_uncosted_bundle_count = _safe_int(llm_lineage_summary.get("uncosted_bundle_count"))
    llm_estimated_cost_usd = _safe_float(llm_lineage_summary.get("estimated_cost_usd"))
    qa_axes = {
        str(axis): _safe_dict(payload)
        for axis, payload in _safe_dict(state.get("qa_axes")).items()
        if str(axis).strip()
    }
    axes_with_attention = sorted(
        axis for axis, payload in qa_axes.items() if _safe_int(payload.get("blocker_count")) > 0 or _safe_int(payload.get("warning_count")) > 0
    )
    not_ready_axes = sorted(axis for axis, payload in qa_axes.items() if payload.get("ready") is False)
    selected_artifact_id = candidate_comparison.get("selected_artifact_id") or selected_handoff.get("selected_artifact_id")
    current_artifact_id = candidate_comparison.get("current_artifact_id") or artifact.get("artifact_id")
    selected_is_current = selected_handoff.get("selected_is_current")
    if selected_is_current is None and current_artifact_id and selected_artifact_id:
        selected_is_current = current_artifact_id == selected_artifact_id
    fallback_count = _safe_int(llm_summary.get("fallback_applied_count"))
    degraded_count = _safe_int(llm_summary.get("degraded_count"))
    missing_bundle_count = _safe_int(llm_summary.get("missing_bundle_count"))
    send_ready = bool(state.get("send_ready"))
    review_required = bool(state.get("review_required")) or state.get("recommended_action") == "send_review"
    blocked = not send_ready and not review_required
    qa_posture = "ready"
    if not_ready_axes:
        qa_posture = "blocked"
    elif axes_with_attention:
        qa_posture = "attention"
    return {
        "business_date": business_date,
        "artifact_id": artifact.get("artifact_id"),
        "report_run_id": artifact.get("report_run_id"),
        "recommended_action": state.get("recommended_action"),
        "workflow_state": state.get("workflow_state"),
        "send_ready": send_ready,
        "review_required": review_required,
        "blocked": blocked,
        "posture": "ready_to_send" if send_ready else ("review_required" if review_required else "blocked"),
        "qa_score": review_summary.get("qa_score"),
        "blocker_count": _safe_int(review_summary.get("blocker_count") or state.get("blocker_count")),
        "warning_count": _safe_int(review_summary.get("warning_count") or state.get("warning_count")),
        "qa_posture": qa_posture,
        "qa_axes": qa_axes,
        "axes_with_attention": axes_with_attention,
        "not_ready_axes": not_ready_axes,
        "llm_lineage_status": llm_lineage_summary.get("status"),
        "llm_lineage_summary": llm_lineage_summary.get("summary_line"),
        "lineage_attention": _lineage_attention(llm_lineage_summary),
        "llm_models": llm_models,
        "llm_slots": llm_slots,
        "llm_usage_bundle_count": llm_usage_bundle_count,
        "llm_total_tokens": llm_total_tokens,
        "llm_estimated_cost_usd": llm_estimated_cost_usd,
        "llm_uncosted_bundle_count": llm_uncosted_bundle_count,
        "llm_bundle_count": _safe_int(llm_summary.get("bundle_count")),
        "llm_applied_count": _safe_int(llm_summary.get("applied_count")),
        "llm_degraded_count": degraded_count,
        "llm_fallback_count": fallback_count,
        "llm_missing_bundle_count": missing_bundle_count,
        "llm_operator_tags": list(llm_summary.get("operator_tags") or []),
        "selected_artifact_id": selected_artifact_id,
        "current_artifact_id": current_artifact_id,
        "selected_is_current": bool(selected_is_current) if selected_is_current is not None else None,
        "selection_mismatch": bool(current_artifact_id and selected_artifact_id and current_artifact_id != selected_artifact_id),
    }


def build_drift_payload(*, scope: str, days: int = 7, slot: str | None = None, store: FSJStore | None = None) -> dict[str, Any]:
    agent_domain, artifact_family, valid_slots = _scope_config(scope)
    if slot is not None and slot not in valid_slots:
        raise ValueError(f"unsupported slot for {scope}: {slot}")
    store = store or FSJStore()
    business_dates = resolve_latest_business_dates(scope=scope, days=days, slot=slot, store=store)
    day_summaries: list[dict[str, Any]] = []
    for business_date in business_dates:
        surface = store.get_active_report_operator_review_surface(
            business_date=business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
        )
        if not surface:
            continue
        day_summaries.append(_build_day_summary(surface, business_date=business_date))

    total = len(day_summaries)
    posture_counts = {
        "ready_to_send": len([item for item in day_summaries if item.get("posture") == "ready_to_send"]),
        "review_required": len([item for item in day_summaries if item.get("posture") == "review_required"]),
        "blocked": len([item for item in day_summaries if item.get("posture") == "blocked"]),
    }
    qa_posture_counts = {
        "ready": len([item for item in day_summaries if item.get("qa_posture") == "ready"]),
        "attention": len([item for item in day_summaries if item.get("qa_posture") == "attention"]),
        "blocked": len([item for item in day_summaries if item.get("qa_posture") == "blocked"]),
    }
    lineage_status_counts: dict[str, int] = {}
    attention_dates: list[str] = []
    qa_attention_dates: list[str] = []
    qa_blocked_dates: list[str] = []
    mismatch_dates: list[str] = []
    fallback_dates: list[str] = []
    degraded_dates: list[str] = []
    missing_lineage_dates: list[str] = []
    operator_tags: set[str] = set()
    model_counts: dict[str, int] = {}
    slot_counts: dict[str, int] = {}
    total_tokens = 0
    usage_bundle_count = 0
    uncosted_bundle_count = 0
    estimated_cost_values: list[float] = []
    for item in day_summaries:
        status = str(item.get("llm_lineage_status") or "not_available")
        lineage_status_counts[status] = lineage_status_counts.get(status, 0) + 1
        if item.get("lineage_attention"):
            attention_dates.append(item["business_date"])
        if item.get("axes_with_attention"):
            qa_attention_dates.append(item["business_date"])
        if item.get("not_ready_axes"):
            qa_blocked_dates.append(item["business_date"])
        if item.get("selection_mismatch"):
            mismatch_dates.append(item["business_date"])
        if _safe_int(item.get("llm_fallback_count")) > 0:
            fallback_dates.append(item["business_date"])
        if _safe_int(item.get("llm_degraded_count")) > 0:
            degraded_dates.append(item["business_date"])
        if _safe_int(item.get("llm_missing_bundle_count")) > 0:
            missing_lineage_dates.append(item["business_date"])
        operator_tags.update(str(tag) for tag in (item.get("llm_operator_tags") or []) if str(tag).strip())
        for model in item.get("llm_models") or []:
            model_counts[str(model)] = model_counts.get(str(model), 0) + 1
        for slot_name in item.get("llm_slots") or []:
            slot_counts[str(slot_name)] = slot_counts.get(str(slot_name), 0) + 1
        total_tokens += _safe_int(item.get("llm_total_tokens"))
        usage_bundle_count += _safe_int(item.get("llm_usage_bundle_count"))
        uncosted_bundle_count += _safe_int(item.get("llm_uncosted_bundle_count"))
        estimated_cost_usd = _safe_float(item.get("llm_estimated_cost_usd"))
        if estimated_cost_usd is not None:
            estimated_cost_values.append(estimated_cost_usd)

    def _rate(count: int) -> float:
        return round((count / total), 4) if total else 0.0

    def _leading_streak(items: list[dict[str, Any]], predicate: Any) -> int:
        streak = 0
        for item in items:
            if predicate(item):
                streak += 1
                continue
            break
        return streak

    recent_streaks = {
        "blocked": _leading_streak(day_summaries, lambda item: item.get("posture") == "blocked"),
        "review_required": _leading_streak(day_summaries, lambda item: item.get("posture") == "review_required"),
        "lineage_attention": _leading_streak(day_summaries, lambda item: bool(item.get("lineage_attention"))),
        "qa_attention": _leading_streak(day_summaries, lambda item: bool(item.get("axes_with_attention"))),
        "qa_blocked": _leading_streak(day_summaries, lambda item: bool(item.get("not_ready_axes"))),
        "selection_mismatch": _leading_streak(day_summaries, lambda item: bool(item.get("selection_mismatch"))),
        "llm_fallback": _leading_streak(day_summaries, lambda item: _safe_int(item.get("llm_fallback_count")) > 0),
        "llm_degraded": _leading_streak(day_summaries, lambda item: _safe_int(item.get("llm_degraded_count")) > 0),
        "llm_missing_bundle": _leading_streak(day_summaries, lambda item: _safe_int(item.get("llm_missing_bundle_count")) > 0),
    }

    return {
        "scope": scope,
        "agent_domain": agent_domain,
        "artifact_family": artifact_family,
        "slot": slot,
        "window_days": days,
        "business_dates": business_dates,
        "reported_day_count": total,
        "days": day_summaries,
        "aggregate": {
            "posture_counts": posture_counts,
            "posture_rates": {key: _rate(value) for key, value in posture_counts.items()},
            "qa_posture_counts": qa_posture_counts,
            "qa_posture_rates": {key: _rate(value) for key, value in qa_posture_counts.items()},
            "lineage_status_counts": lineage_status_counts,
            "lineage_attention_rate": _rate(len(attention_dates)),
            "qa_attention_rate": _rate(len(qa_attention_dates)),
            "qa_blocked_rate": _rate(len(qa_blocked_dates)),
            "selection_mismatch_rate": _rate(len(mismatch_dates)),
            "llm_fallback_rate": _rate(len(fallback_dates)),
            "llm_degraded_rate": _rate(len(degraded_dates)),
            "llm_missing_bundle_rate": _rate(len(missing_lineage_dates)),
            "average_qa_score": round(sum(float(item.get("qa_score") or 0) for item in day_summaries) / total, 2) if total else None,
            "max_blocker_count": max((_safe_int(item.get("blocker_count")) for item in day_summaries), default=0),
            "max_warning_count": max((_safe_int(item.get("warning_count")) for item in day_summaries), default=0),
            "attention_dates": attention_dates,
            "qa_attention_dates": qa_attention_dates,
            "qa_blocked_dates": qa_blocked_dates,
            "selection_mismatch_dates": mismatch_dates,
            "llm_fallback_dates": fallback_dates,
            "llm_degraded_dates": degraded_dates,
            "llm_missing_bundle_dates": missing_lineage_dates,
            "llm_operator_tags": sorted(operator_tags),
            "llm_model_counts": dict(sorted(model_counts.items())),
            "llm_slot_counts": dict(sorted(slot_counts.items())),
            "llm_total_tokens": total_tokens,
            "llm_usage_bundle_count": usage_bundle_count,
            "llm_uncosted_bundle_count": uncosted_bundle_count,
            "llm_estimated_cost_usd": round(sum(estimated_cost_values), 6) if estimated_cost_values else None,
            "recent_streaks": recent_streaks,
        },
    }


def format_drift_summary_line(payload: dict[str, Any]) -> str:
    aggregate = _safe_dict(payload.get("aggregate"))
    total = _safe_int(payload.get("reported_day_count"))
    window_days = _safe_int(payload.get("window_days"))
    label = str(payload.get("scope") or "scope")
    slot = payload.get("slot")
    if slot:
        label = f"{label}:{slot}"
    blocked = _safe_int(_safe_dict(aggregate.get("posture_counts")).get("blocked"))
    fallback = len(aggregate.get("llm_fallback_dates") or [])
    mismatch = len(aggregate.get("selection_mismatch_dates") or [])
    qa_attention = len(aggregate.get("qa_attention_dates") or [])
    recent_streaks = _safe_dict(aggregate.get("recent_streaks"))
    streak_parts: list[str] = []
    for key, short_label in (
        ("blocked", "hold"),
        ("llm_fallback", "fallback"),
        ("selection_mismatch", "mismatch"),
        ("qa_attention", "qa_attn"),
    ):
        streak_value = _safe_int(recent_streaks.get(key))
        if streak_value > 0:
            streak_parts.append(f"{short_label}_streak={streak_value}")
    streak_suffix = f" | recent {'; '.join(streak_parts)}" if streak_parts else ""
    return (
        f"{window_days}d drift {label}: hold {blocked}/{total} | "
        f"fallback {fallback}/{total} | mismatch {mismatch}/{total} | qa_attn {qa_attention}/{total}"
        f"{streak_suffix}"
    )


def build_fleet_drift_digest(
    drift_payloads: dict[str, dict[str, Any]],
    *,
    window_days: int | None = None,
) -> dict[str, Any]:
    main_payload = _safe_dict(drift_payloads.get("main"))
    support_payloads = [
        _safe_dict(payload)
        for scope, payload in sorted(drift_payloads.items())
        if str(scope).startswith("support:") and isinstance(payload, dict)
    ]

    if window_days is None:
        window_days = _safe_int(main_payload.get("window_days")) or 7

    def _group_digest(label: str, payloads: list[dict[str, Any]]) -> dict[str, Any]:
        reported_days = sum(_safe_int(payload.get("reported_day_count")) for payload in payloads)
        hold_days = sum(_safe_int(_safe_dict(_safe_dict(payload.get("aggregate")).get("posture_counts")).get("blocked")) for payload in payloads)
        fallback_days = sum(len(_safe_dict(payload.get("aggregate")).get("llm_fallback_dates") or []) for payload in payloads)
        mismatch_days = sum(len(_safe_dict(payload.get("aggregate")).get("selection_mismatch_dates") or []) for payload in payloads)
        qa_attention_days = sum(len(_safe_dict(payload.get("aggregate")).get("qa_attention_dates") or []) for payload in payloads)
        model_counts: dict[str, int] = {}
        slot_counts: dict[str, int] = {}
        total_tokens = 0
        usage_bundle_count = 0
        uncosted_bundle_count = 0
        estimated_cost_values: list[float] = []
        for payload in payloads:
            aggregate = _safe_dict(payload.get("aggregate"))
            for model, count in _safe_dict(aggregate.get("llm_model_counts")).items():
                model_counts[str(model)] = model_counts.get(str(model), 0) + _safe_int(count)
            for slot_name, count in _safe_dict(aggregate.get("llm_slot_counts")).items():
                slot_counts[str(slot_name)] = slot_counts.get(str(slot_name), 0) + _safe_int(count)
            total_tokens += _safe_int(aggregate.get("llm_total_tokens"))
            usage_bundle_count += _safe_int(aggregate.get("llm_usage_bundle_count"))
            uncosted_bundle_count += _safe_int(aggregate.get("llm_uncosted_bundle_count"))
            estimated_cost_usd = _safe_float(aggregate.get("llm_estimated_cost_usd"))
            if estimated_cost_usd is not None:
                estimated_cost_values.append(estimated_cost_usd)
        scope_count = len(payloads)
        return {
            "label": label,
            "scope_count": scope_count,
            "reported_day_count": reported_days,
            "hold_count": hold_days,
            "fallback_count": fallback_days,
            "mismatch_count": mismatch_days,
            "qa_attention_count": qa_attention_days,
            "llm_model_counts": dict(sorted(model_counts.items())),
            "llm_slot_counts": dict(sorted(slot_counts.items())),
            "llm_total_tokens": total_tokens,
            "llm_usage_bundle_count": usage_bundle_count,
            "llm_uncosted_bundle_count": uncosted_bundle_count,
            "llm_estimated_cost_usd": round(sum(estimated_cost_values), 6) if estimated_cost_values else None,
        }

    main_group = _group_digest("main", [main_payload] if main_payload else [])
    support_group = _group_digest("support", support_payloads)
    return {
        "window_days": window_days,
        "main": main_group,
        "support": support_group,
    }


def format_fleet_drift_digest_line(digest: dict[str, Any]) -> str:
    window_days = _safe_int(digest.get("window_days")) or 7

    def _render(group: dict[str, Any]) -> str:
        return (
            f"{group.get('label') or 'group'} hold {_safe_int(group.get('hold_count'))}/{_safe_int(group.get('reported_day_count'))}"
            f" ({_safe_int(group.get('scope_count'))} scope)"
            f" | fallback {_safe_int(group.get('fallback_count'))}/{_safe_int(group.get('reported_day_count'))}"
            f" | mismatch {_safe_int(group.get('mismatch_count'))}/{_safe_int(group.get('reported_day_count'))}"
            f" | qa_attn {_safe_int(group.get('qa_attention_count'))}/{_safe_int(group.get('reported_day_count'))}"
        )

    return f"{window_days}d fleet drift: {_render(_safe_dict(digest.get('main')))} || {_render(_safe_dict(digest.get('support')))}"


def _print_text(payload: dict[str, Any]) -> None:
    aggregate = _safe_dict(payload.get("aggregate"))
    posture_counts = _safe_dict(aggregate.get("posture_counts"))
    posture_rates = _safe_dict(aggregate.get("posture_rates"))
    qa_posture_counts = _safe_dict(aggregate.get("qa_posture_counts"))
    qa_posture_rates = _safe_dict(aggregate.get("qa_posture_rates"))
    print(f"scope={payload.get('scope')}")
    print(f"agent_domain={payload.get('agent_domain')}")
    print(f"artifact_family={payload.get('artifact_family')}")
    print(f"window_days={payload.get('window_days')}")
    print(f"reported_day_count={payload.get('reported_day_count')}")
    if payload.get("slot"):
        print(f"slot={payload.get('slot')}")
    print(f"business_dates={','.join(payload.get('business_dates') or [])}")
    print(
        "posture_counts="
        + ",".join(f"{key}:{posture_counts.get(key, 0)}" for key in ("ready_to_send", "review_required", "blocked"))
    )
    print(
        "posture_rates="
        + ",".join(f"{key}:{posture_rates.get(key, 0.0):.4f}" for key in ("ready_to_send", "review_required", "blocked"))
    )
    print(
        "qa_posture_counts="
        + ",".join(f"{key}:{qa_posture_counts.get(key, 0)}" for key in ("ready", "attention", "blocked"))
    )
    print(
        "qa_posture_rates="
        + ",".join(f"{key}:{qa_posture_rates.get(key, 0.0):.4f}" for key in ("ready", "attention", "blocked"))
    )
    print(
        "lineage_status_counts="
        + ",".join(f"{key}:{value}" for key, value in sorted(_safe_dict(aggregate.get('lineage_status_counts')).items()))
    )
    print(f"lineage_attention_rate={aggregate.get('lineage_attention_rate', 0.0):.4f}")
    print(f"qa_attention_rate={aggregate.get('qa_attention_rate', 0.0):.4f}")
    print(f"qa_blocked_rate={aggregate.get('qa_blocked_rate', 0.0):.4f}")
    print(f"selection_mismatch_rate={aggregate.get('selection_mismatch_rate', 0.0):.4f}")
    print(f"llm_fallback_rate={aggregate.get('llm_fallback_rate', 0.0):.4f}")
    print(f"llm_degraded_rate={aggregate.get('llm_degraded_rate', 0.0):.4f}")
    print(f"llm_missing_bundle_rate={aggregate.get('llm_missing_bundle_rate', 0.0):.4f}")
    print(f"average_qa_score={aggregate.get('average_qa_score')}")
    print(f"max_blocker_count={aggregate.get('max_blocker_count')}")
    print(f"max_warning_count={aggregate.get('max_warning_count')}")
    print(f"attention_dates={','.join(aggregate.get('attention_dates') or [])}")
    print(f"qa_attention_dates={','.join(aggregate.get('qa_attention_dates') or [])}")
    print(f"qa_blocked_dates={','.join(aggregate.get('qa_blocked_dates') or [])}")
    print(f"selection_mismatch_dates={','.join(aggregate.get('selection_mismatch_dates') or [])}")
    print(f"llm_fallback_dates={','.join(aggregate.get('llm_fallback_dates') or [])}")
    print(f"llm_degraded_dates={','.join(aggregate.get('llm_degraded_dates') or [])}")
    print(f"llm_missing_bundle_dates={','.join(aggregate.get('llm_missing_bundle_dates') or [])}")
    print(f"llm_operator_tags={','.join(aggregate.get('llm_operator_tags') or [])}")
    print(
        "llm_model_counts="
        + ",".join(f"{model}:{count}" for model, count in sorted(_safe_dict(aggregate.get("llm_model_counts")).items()))
    )
    print(
        "llm_slot_counts="
        + ",".join(f"{slot_name}:{count}" for slot_name, count in sorted(_safe_dict(aggregate.get("llm_slot_counts")).items()))
    )
    print(f"llm_total_tokens={aggregate.get('llm_total_tokens')}")
    print(f"llm_usage_bundle_count={aggregate.get('llm_usage_bundle_count')}")
    print(f"llm_uncosted_bundle_count={aggregate.get('llm_uncosted_bundle_count')}")
    print(f"llm_estimated_cost_usd={aggregate.get('llm_estimated_cost_usd')}")
    recent_streaks = _safe_dict(aggregate.get("recent_streaks"))
    print(
        "recent_streaks="
        + ",".join(
            f"{key}:{_safe_int(value)}"
            for key, value in sorted(recent_streaks.items())
        )
    )
    print(f"summary_line={format_drift_summary_line(payload)}")
    for index, item in enumerate(payload.get("days") or [], start=1):
        print(
            "day_{idx}=".format(idx=index)
            + "|".join(
                [
                    f"business_date:{item.get('business_date')}",
                    f"artifact_id:{item.get('artifact_id')}",
                    f"posture:{item.get('posture')}",
                    f"qa_posture:{item.get('qa_posture')}",
                    f"llm_lineage_status:{item.get('llm_lineage_status')}",
                    f"llm_fallback_count:{item.get('llm_fallback_count')}",
                    f"llm_models:{','.join(item.get('llm_models') or [])}",
                    f"llm_slots:{','.join(item.get('llm_slots') or [])}",
                    f"llm_total_tokens:{item.get('llm_total_tokens')}",
                    f"llm_estimated_cost_usd:{item.get('llm_estimated_cost_usd')}",
                    f"llm_uncosted_bundle_count:{item.get('llm_uncosted_bundle_count')}",
                    f"selection_mismatch:{item.get('selection_mismatch')}",
                    f"axes_attention:{','.join(item.get('axes_with_attention') or [])}",
                    f"not_ready_axes:{','.join(item.get('not_ready_axes') or [])}",
                ]
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Historical drift/trend monitor over FSJ operator review surfaces.")
    parser.add_argument("--scope", required=True, choices=sorted(_VALID_SCOPE))
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--slot")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    payload = build_drift_payload(scope=args.scope, days=args.days, slot=args.slot)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
