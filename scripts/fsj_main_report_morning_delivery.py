#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj.report_assembly import FSJReportAssemblyStore, MainReportAssemblyService
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MAIN morning delivery workflow: package + eval + dispatch + review/send manifests.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-run-id")
    parser.add_argument("--generated-at", help="ISO8601 timestamp; defaults to current UTC time")
    parser.add_argument("--include-empty", action="store_true")
    args = parser.parse_args()

    store = FSJStore()
    assembly_store = FSJReportAssemblyStore()
    rendering_service = MainReportRenderingService(
        assembly_service=MainReportAssemblyService(store=assembly_store),
    )
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store)
    orchestrator = MainReportMorningDeliveryOrchestrator(publisher=publisher)
    result = orchestrator.run_workflow(
        business_date=args.business_date,
        output_dir=Path(args.output_dir),
        include_empty=args.include_empty,
        report_run_id=args.report_run_id,
        generated_at=_parse_generated_at(args.generated_at),
    )
    print(json.dumps({
        "artifact": result["artifact"],
        "delivery_manifest": result["delivery_manifest"],
        "dispatch_decision": result["dispatch_decision"],
        "workflow_manifest": result["workflow_manifest"],
        "delivery_package_dir": result["delivery_package_dir"],
        "delivery_manifest_path": result["delivery_manifest_path"],
        "send_manifest_path": result["send_manifest_path"],
        "review_manifest_path": result["review_manifest_path"],
        "operator_summary_path": result["operator_summary_path"],
        "workflow_manifest_path": result["workflow_manifest_path"],
        "delivery_zip_path": result["delivery_zip_path"],
        "telegram_caption_path": result["telegram_caption_path"],
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
