#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ifa_data_platform.fsj.store import FSJStore

_BEIJING = timezone(timedelta(hours=8))


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value or {})


def _resolve_business_date(*, store: FSJStore, agent_domain: str, artifact_family: str, strongest_slot: str | None) -> str | None:
    lineage = store.get_latest_active_report_artifact_lineage(
        agent_domain=agent_domain,
        artifact_family=artifact_family,
        strongest_slot=strongest_slot,
        max_business_date=datetime.now(_BEIJING).date(),
    )
    return _safe_dict(lineage.get("artifact") if lineage else {}).get("business_date")


def build_payload(
    *,
    business_date: str | None,
    agent_domain: str,
    artifact_family: str,
    strongest_slot: str | None,
    history_limit: int,
    store: FSJStore | None = None,
) -> dict[str, Any]:
    store = store or FSJStore()
    resolved_business_date = business_date or _resolve_business_date(
        store=store,
        agent_domain=agent_domain,
        artifact_family=artifact_family,
        strongest_slot=strongest_slot,
    )
    active = None
    history: list[dict[str, Any]] = []
    if resolved_business_date:
        active = store.get_active_report_artifact_lineage(
            business_date=resolved_business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
        )
        history = store.list_report_artifact_lineages(
            business_date=resolved_business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
            statuses=["active", "superseded"],
            limit=history_limit,
        )
    return {
        "business_date": resolved_business_date,
        "agent_domain": agent_domain,
        "artifact_family": artifact_family,
        "strongest_slot": strongest_slot,
        "active": active,
        "history": history,
    }


def _print_text(payload: dict[str, Any]) -> None:
    print(f"business_date={payload.get('business_date') or '-'}")
    print(f"agent_domain={payload.get('agent_domain')}")
    print(f"artifact_family={payload.get('artifact_family')}")
    active = _safe_dict(payload.get("active"))
    artifact = _safe_dict(active.get("artifact"))
    lifecycle = _safe_dict(active.get("canonical_lifecycle"))
    selection = _safe_dict(active.get("selection"))
    received = _safe_dict(active.get("what_user_received"))
    package = _safe_dict(active.get("package"))
    review = _safe_dict(active.get("review"))
    bundle_summary = _safe_dict(active.get("bundle_lineage_summary"))
    llm_summary = _safe_dict(active.get("llm_lineage_summary"))
    if not artifact:
        print("active_artifact=NONE")
        print(f"history_count={len(payload.get('history') or [])}")
        return
    print(f"artifact_id={artifact.get('artifact_id')}")
    print(f"artifact_status={artifact.get('status')}")
    print(f"report_run_id={artifact.get('report_run_id')}")
    print(f"supersedes_artifact_id={artifact.get('supersedes_artifact_id')}")
    print(f"canonical_lifecycle_state={lifecycle.get('state')}")
    print(f"canonical_lifecycle_reason={lifecycle.get('reason')}")
    print(f"selected_artifact_id={selection.get('selected_artifact_id')}")
    print(f"selected_is_current={selection.get('selected_is_current')}")
    print(f"delivery_manifest_path={_safe_dict(package.get('paths')).get('delivery_manifest_path')}")
    print(f"send_manifest_path={_safe_dict(package.get('paths')).get('send_manifest_path')}")
    print(f"review_manifest_path={_safe_dict(package.get('paths')).get('review_manifest_path')}")
    print(f"workflow_manifest_path={_safe_dict(package.get('paths')).get('workflow_manifest_path')}")
    print(f"dispatch_state={received.get('dispatch_state')}")
    print(f"dispatch_channel={received.get('channel')}")
    print(f"provider_message_id={received.get('provider_message_id')}")
    print(f"sent_at={received.get('sent_at')}")
    print(f"dispatch_error={received.get('error')}")
    print(f"review_decision={_safe_dict(review.get('operator_go_no_go')).get('decision')}")
    print(f"candidate_count={_safe_dict(review.get('candidate_comparison')).get('candidate_count')}")
    print(f"bundle_count={bundle_summary.get('bundle_count')}")
    print(f"missing_bundle_count={bundle_summary.get('missing_bundle_count')}")
    print(f"bundle_slots={','.join(bundle_summary.get('slots') or [])}")
    print(f"bundle_section_keys={','.join(bundle_summary.get('section_keys') or [])}")
    print(f"llm_lineage_status={llm_summary.get('status')}")
    print(f"llm_lineage_summary={llm_summary.get('summary_line')}")
    print(f"history_count={len(payload.get('history') or [])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Query canonical FSJ artifact lineage across package/review/send seams.")
    parser.add_argument("--business-date")
    parser.add_argument("--agent-domain", default="main")
    parser.add_argument("--artifact-family", default="main_final_report")
    parser.add_argument("--strongest-slot")
    parser.add_argument("--history-limit", type=int, default=5)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    payload = build_payload(
        business_date=args.business_date,
        agent_domain=args.agent_domain,
        artifact_family=args.artifact_family,
        strongest_slot=args.strongest_slot,
        history_limit=args.history_limit,
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    _print_text(payload)


if __name__ == "__main__":
    main()
