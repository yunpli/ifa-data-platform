#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from ifa_data_platform.fsj.store import FSJStore


_DRIFT_MONITOR_PATH = Path(__file__).resolve().parent / "fsj_drift_monitor.py"
_DRIFT_MONITOR_SPEC = importlib.util.spec_from_file_location("fsj_drift_monitor_script", _DRIFT_MONITOR_PATH)
if _DRIFT_MONITOR_SPEC is None or _DRIFT_MONITOR_SPEC.loader is None:
    raise RuntimeError(f"failed to load drift monitor module from {_DRIFT_MONITOR_PATH}")
_DRIFT_MONITOR_MODULE = importlib.util.module_from_spec(_DRIFT_MONITOR_SPEC)
_DRIFT_MONITOR_SPEC.loader.exec_module(_DRIFT_MONITOR_MODULE)
build_drift_payload = _DRIFT_MONITOR_MODULE.build_drift_payload

_SCOPES = ("main", "support:macro", "support:commodities", "support:ai_tech")


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def build_fallback_status_payload(*, days: int = 3, include_clean: bool = False, store: FSJStore | None = None) -> dict[str, Any]:
    scopes: list[dict[str, Any]] = []
    fleet_attention = {
        "scope_count": 0,
        "attention_scope_count": 0,
        "fallback_scope_count": 0,
        "degraded_scope_count": 0,
        "missing_scope_count": 0,
        "attention_scopes": [],
        "fallback_scopes": [],
        "degraded_scopes": [],
        "missing_scopes": [],
    }

    for scope in _SCOPES:
        drift = build_drift_payload(scope=scope, days=days, store=store)
        aggregate = _safe_dict(drift.get("aggregate"))
        reported_day_count = int(drift.get("reported_day_count") or 0)
        entry = {
            "scope": scope,
            "reported_day_count": reported_day_count,
            "business_dates": list(drift.get("business_dates") or []),
            "attention_dates": list(aggregate.get("attention_dates") or []),
            "qa_attention_dates": list(aggregate.get("qa_attention_dates") or []),
            "qa_blocked_dates": list(aggregate.get("qa_blocked_dates") or []),
            "llm_fallback_dates": list(aggregate.get("llm_fallback_dates") or []),
            "llm_degraded_dates": list(aggregate.get("llm_degraded_dates") or []),
            "llm_missing_bundle_dates": list(aggregate.get("llm_missing_bundle_dates") or []),
            "llm_operator_tags": list(aggregate.get("llm_operator_tags") or []),
            "llm_model_counts": dict(aggregate.get("llm_model_counts") or {}),
            "llm_slot_counts": dict(aggregate.get("llm_slot_counts") or {}),
            "llm_fallback_rate": aggregate.get("llm_fallback_rate"),
            "llm_degraded_rate": aggregate.get("llm_degraded_rate"),
            "llm_missing_bundle_rate": aggregate.get("llm_missing_bundle_rate"),
            "selection_mismatch_dates": list(aggregate.get("selection_mismatch_dates") or []),
            "posture_counts": dict(aggregate.get("posture_counts") or {}),
            "lineage_status_counts": dict(aggregate.get("lineage_status_counts") or {}),
        }
        needs_attention = bool(
            entry["llm_fallback_dates"]
            or entry["llm_degraded_dates"]
            or entry["llm_missing_bundle_dates"]
            or entry["qa_blocked_dates"]
            or entry["selection_mismatch_dates"]
        )
        entry["needs_attention"] = needs_attention
        entry["summary_line"] = _summary_line(entry)

        fleet_attention["scope_count"] += 1
        if needs_attention:
            fleet_attention["attention_scope_count"] += 1
            fleet_attention["attention_scopes"].append(scope)
        if entry["llm_fallback_dates"]:
            fleet_attention["fallback_scope_count"] += 1
            fleet_attention["fallback_scopes"].append(scope)
        if entry["llm_degraded_dates"]:
            fleet_attention["degraded_scope_count"] += 1
            fleet_attention["degraded_scopes"].append(scope)
        if entry["llm_missing_bundle_dates"]:
            fleet_attention["missing_scope_count"] += 1
            fleet_attention["missing_scopes"].append(scope)

        if include_clean or needs_attention:
            scopes.append(entry)

    fleet_attention["summary_line"] = (
        f"llm-fallback fleet: attention {fleet_attention['attention_scope_count']}/{fleet_attention['scope_count']}"
        f" | fallback_scopes={fleet_attention['fallback_scope_count']}"
        f" | degraded_scopes={fleet_attention['degraded_scope_count']}"
        f" | missing_scopes={fleet_attention['missing_scope_count']}"
    )
    return {
        "window_days": days,
        "include_clean": include_clean,
        "fleet_attention": fleet_attention,
        "scopes": scopes,
    }


def _summary_line(entry: dict[str, Any]) -> str:
    parts = [f"{entry['scope']}: {entry['reported_day_count']}d"]
    if entry.get("llm_fallback_dates"):
        parts.append(f"fallback={','.join(entry['llm_fallback_dates'])}")
    if entry.get("llm_degraded_dates"):
        parts.append(f"degraded={','.join(entry['llm_degraded_dates'])}")
    if entry.get("llm_missing_bundle_dates"):
        parts.append(f"missing={','.join(entry['llm_missing_bundle_dates'])}")
    if entry.get("qa_blocked_dates"):
        parts.append(f"qa_blocked={','.join(entry['qa_blocked_dates'])}")
    if entry.get("selection_mismatch_dates"):
        parts.append(f"mismatch={','.join(entry['selection_mismatch_dates'])}")
    if entry.get("llm_operator_tags"):
        parts.append(f"tags={','.join(entry['llm_operator_tags'])}")
    if len(parts) == 1:
        parts.append("clean")
    return " | ".join(parts)


def _print_text(payload: dict[str, Any]) -> None:
    fleet = _safe_dict(payload.get("fleet_attention"))
    print(f"window_days={payload.get('window_days')}")
    print(f"include_clean={payload.get('include_clean')}")
    print(f"fleet_summary={fleet.get('summary_line')}")
    print(f"attention_scopes={','.join(fleet.get('attention_scopes') or [])}")
    print(f"fallback_scopes={','.join(fleet.get('fallback_scopes') or [])}")
    print(f"degraded_scopes={','.join(fleet.get('degraded_scopes') or [])}")
    print(f"missing_scopes={','.join(fleet.get('missing_scopes') or [])}")
    for idx, entry in enumerate(payload.get("scopes") or [], start=1):
        print(f"scope_{idx}={entry.get('summary_line')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Operator-visible FSJ LLM fallback attention summary across main/support scopes.")
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--include-clean", action="store_true", help="Include scopes without current fallback/degrade/missing attention")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    payload = build_fallback_status_payload(days=args.days, include_clean=args.include_clean)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
