#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj.report_assembly import FSJReportAssemblyStore, MainReportAssemblyService
from ifa_data_platform.fsj.report_rendering import MainReportArtifactPublishingService, MainReportRenderingService
from ifa_data_platform.fsj.store import FSJStore
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError, enforce_non_live_test_roots


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish A-share FSJ MAIN HTML artifact and delivery package.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-run-id")
    parser.add_argument("--generated-at", help="ISO8601 timestamp; defaults to current UTC time")
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--package-only", action="store_true", help="Alias for delivery packaging; output remains package-first JSON")
    args = parser.parse_args()

    enforce_non_live_test_roots(flow_name="fsj_main_report_publish", output_path=args.output_dir)

    store = FSJStore()
    assembly_store = FSJReportAssemblyStore()
    rendering_service = MainReportRenderingService(
        assembly_service=MainReportAssemblyService(store=assembly_store),
    )
    publisher = MainReportArtifactPublishingService(
        rendering_service=rendering_service,
        store=store,
        artifact_root=Path(args.output_dir),
    )
    published = publisher.publish_delivery_package(
        business_date=args.business_date,
        output_dir=Path(args.output_dir),
        include_empty=args.include_empty,
        report_run_id=args.report_run_id,
        generated_at=_parse_generated_at(args.generated_at),
    )
    print(json.dumps({
        "artifact": published["artifact"],
        "html_path": published["html_path"],
        "qa_path": published["qa_path"],
        "manifest_path": published["manifest_path"],
        "delivery_package_dir": published["delivery_package_dir"],
        "delivery_manifest_path": published["delivery_manifest_path"],
        "telegram_caption_path": published["telegram_caption_path"],
        "delivery_zip_path": published["delivery_zip_path"],
        "delivery_manifest": published["delivery_manifest"],
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
