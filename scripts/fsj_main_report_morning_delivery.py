#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj.report_assembly import FSJReportAssemblyStore, MainReportAssemblyService
from ifa_data_platform.fsj.report_dispatch import MainReportDeliveryDispatchHelper
from ifa_data_platform.fsj.report_orchestration import MainReportMorningDeliveryOrchestrator
from ifa_data_platform.fsj.report_rendering import MainReportArtifactPublishingService, MainReportRenderingService
from ifa_data_platform.fsj.store import FSJStore


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_comparison_candidates(
    *,
    helper: MainReportDeliveryDispatchHelper,
    store: FSJStore,
    compare_under_output_dir: str | None,
    comparison_package_dir: list[str],
    comparison_manifest: list[str],
    business_date: str,
    compare_limit: int,
) -> list[dict]:
    candidates: list[dict] = []
    seen_manifest_paths: set[str] = set()

    def _append(candidate: dict) -> None:
        manifest_path = str(candidate.get("delivery_manifest_path") or "")
        if manifest_path and manifest_path not in seen_manifest_paths:
            candidates.append(candidate)
            seen_manifest_paths.add(manifest_path)

    db_active = helper.load_active_published_candidate(business_date=business_date, store=store)
    if db_active:
        _append(db_active)

    if compare_under_output_dir:
        for candidate in helper.discover_published_candidates(compare_under_output_dir, business_date=business_date, limit=compare_limit):
            _append(candidate)
    for package_dir in comparison_package_dir:
        _append(helper.load_published_candidate(package_dir))
    for manifest_path in comparison_manifest:
        _append(helper.load_published_candidate(manifest_path))
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MAIN morning delivery workflow: package + eval + dispatch + review/send manifests.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-run-id")
    parser.add_argument("--generated-at", help="ISO8601 timestamp; defaults to current UTC time")
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--compare-under-output-dir", help="Discover prior delivery packages under this output root and include same-day candidates in dispatch selection")
    parser.add_argument("--compare-limit", type=int, default=8, help="Max discovered candidates when --compare-under-output-dir is used")
    parser.add_argument("--comparison-package-dir", action="append", default=[], help="Existing delivery package dir to compare against; repeatable")
    parser.add_argument("--comparison-manifest", action="append", default=[], help="Path to an existing delivery_manifest.json to compare against; repeatable")
    args = parser.parse_args()

    helper = MainReportDeliveryDispatchHelper()
    store = FSJStore()
    comparison_candidates = _load_comparison_candidates(
        helper=helper,
        store=store,
        compare_under_output_dir=args.compare_under_output_dir,
        comparison_package_dir=args.comparison_package_dir,
        comparison_manifest=args.comparison_manifest,
        business_date=args.business_date,
        compare_limit=args.compare_limit,
    )

    assembly_store = FSJReportAssemblyStore()
    rendering_service = MainReportRenderingService(
        assembly_service=MainReportAssemblyService(store=assembly_store),
    )
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store)
    orchestrator = MainReportMorningDeliveryOrchestrator(publisher=publisher, dispatch_helper=helper)
    result = orchestrator.run_workflow(
        business_date=args.business_date,
        output_dir=Path(args.output_dir),
        include_empty=args.include_empty,
        report_run_id=args.report_run_id,
        generated_at=_parse_generated_at(args.generated_at),
        comparison_candidates=comparison_candidates,
    )
    print(json.dumps({
        "artifact": result["artifact"],
        "delivery_manifest": result["delivery_manifest"],
        "dispatch_decision": result["dispatch_decision"],
        "workflow_manifest": result["workflow_manifest"],
        "comparison_candidate_count": len(comparison_candidates),
        "delivery_package_dir": result["delivery_package_dir"],
        "delivery_manifest_path": result["delivery_manifest_path"],
        "send_manifest_path": result["send_manifest_path"],
        "review_manifest_path": result["review_manifest_path"],
        "operator_summary_path": result["operator_summary_path"],
        "workflow_manifest_path": result["workflow_manifest_path"],
        "delivery_zip_path": result["delivery_zip_path"],
        "telegram_caption_path": result["telegram_caption_path"],
        "selected_handoff": result["selected_handoff"],
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
