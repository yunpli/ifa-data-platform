#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj.report_assembly import FSJReportAssemblyStore, MainReportAssemblyService
from ifa_data_platform.fsj.report_orchestration import build_main_report_delivery_publisher
from ifa_data_platform.fsj.store import FSJStore
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError, enforce_non_live_test_roots


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_canonical_publish_surface(*, business_date: str, store: FSJStore | None = None) -> dict | None:
    store = store or FSJStore()
    surface = store.get_active_report_delivery_surface(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
    )
    if not surface:
        return None
    return {
        "delivery_surface": surface,
        "workflow_handoff": store.report_workflow_handoff_from_surface(surface),
        "operator_review_surface": store.report_operator_review_surface_from_surface(surface),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish A-share FSJ MAIN HTML artifact and delivery package.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-run-id")
    parser.add_argument("--generated-at", help="ISO8601 timestamp; defaults to current UTC time")
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--output-profile", choices=["internal", "review", "customer"], default="internal")
    parser.add_argument("--package-only", action="store_true", help="Alias for delivery packaging; output remains package-first JSON")
    args = parser.parse_args()

    enforce_non_live_test_roots(flow_name="fsj_main_report_publish", output_path=args.output_dir)

    store = FSJStore()
    assembly_store = FSJReportAssemblyStore()
    publisher = build_main_report_delivery_publisher(
        assembly_service=MainReportAssemblyService(store=assembly_store),
        store=store,
        artifact_root=Path(args.output_dir),
    )
    published = publisher.publish_delivery_package(
        business_date=args.business_date,
        output_dir=Path(args.output_dir),
        include_empty=args.include_empty,
        report_run_id=args.report_run_id,
        generated_at=_parse_generated_at(args.generated_at),
        output_profile=args.output_profile,
    )
    payload = {
        "artifact": published["artifact"],
        "html_path": published["html_path"],
        "qa_path": published["qa_path"],
        "manifest_path": published["manifest_path"],
        "delivery_package_dir": published["delivery_package_dir"],
        "delivery_manifest_path": published["delivery_manifest_path"],
        "telegram_caption_path": published["telegram_caption_path"],
        "delivery_zip_path": published["delivery_zip_path"],
        "judgment_review_surface_path": dict(published.get("delivery_manifest") or {}).get("judgment_review_surface", {}).get("path"),
        "judgment_mapping_ledger_path": dict(published.get("delivery_manifest") or {}).get("judgment_mapping_ledger", {}).get("path"),
        "delivery_manifest": published["delivery_manifest"],
        "output_profile": args.output_profile,
    }
    canonical_surface = _resolve_canonical_publish_surface(business_date=args.business_date, store=store)
    if canonical_surface:
        payload.update(canonical_surface)
        workflow_handoff = dict(canonical_surface.get("workflow_handoff") or {})
        operator_review_surface = dict(canonical_surface.get("operator_review_surface") or {})
        manifest_pointers = dict(workflow_handoff.get("manifest_pointers") or {})
        selected_handoff = dict(workflow_handoff.get("selected_handoff") or {})
        package_paths = dict(operator_review_surface.get("package_paths") or {})
        payload["delivery_package_dir"] = selected_handoff.get("selected_delivery_package_dir") or payload["delivery_package_dir"]
        payload["delivery_manifest_path"] = manifest_pointers.get("delivery_manifest_path") or payload["delivery_manifest_path"]
        payload["telegram_caption_path"] = manifest_pointers.get("telegram_caption_path") or payload["telegram_caption_path"]
        payload["delivery_zip_path"] = manifest_pointers.get("delivery_zip_path") or payload["delivery_zip_path"]
        payload["operator_summary_path"] = package_paths.get("operator_review_readme_path") or payload.get("operator_summary_path")
        payload["package_index_path"] = package_paths.get("package_index_path") or payload.get("package_index_path")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
