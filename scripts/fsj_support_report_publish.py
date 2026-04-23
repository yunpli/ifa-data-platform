#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ifa_data_platform.fsj.report_assembly import FSJReportAssemblyStore, SupportReportAssemblyService
from ifa_data_platform.fsj.report_rendering import SupportReportArtifactPublishingService, SupportReportRenderingService
from ifa_data_platform.fsj.store import FSJStore


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_canonical_publish_surface(*, business_date: str, agent_domain: str, store: FSJStore | None = None) -> dict[str, Any] | None:
    store = store or FSJStore()
    surface = store.get_active_report_delivery_surface(
        business_date=business_date,
        agent_domain=agent_domain,
        artifact_family="support_domain_report",
    )
    if not surface:
        return None
    return {
        "delivery_surface": surface,
        "workflow_handoff": store.report_workflow_handoff_from_surface(surface),
    }



def main() -> None:
    parser = argparse.ArgumentParser(description="Publish A-share FSJ support HTML artifact and delivery package.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--agent-domain", required=True, choices=["macro", "commodities", "ai_tech"])
    parser.add_argument("--slot", required=True, choices=["early", "late"])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-run-id")
    parser.add_argument("--generated-at", help="ISO8601 timestamp; defaults to current UTC time")
    parser.add_argument("--html-only", action="store_true", help="Only publish standalone HTML + manifest; skip QA/package surfaces")
    parser.add_argument("--require-ready", action="store_true", help="Fail fast when the persisted support bundle is missing/non-ready instead of publishing a blocked placeholder package")
    args = parser.parse_args()

    store = FSJStore()
    assembly_store = FSJReportAssemblyStore()
    assembly_service = SupportReportAssemblyService(store=assembly_store)
    rendering_service = SupportReportRenderingService(
        assembly_service=assembly_service,
    )
    publisher = SupportReportArtifactPublishingService(rendering_service=rendering_service, store=store)
    assembled = assembly_service.assemble_support_section(
        business_date=args.business_date,
        agent_domain=args.agent_domain,
        slot=args.slot,
    )
    if args.require_ready and assembled.get("status") != "ready":
        print(json.dumps({
            "business_date": args.business_date,
            "agent_domain": args.agent_domain,
            "slot": args.slot,
            "status": assembled.get("status") or "missing",
            "section_render_key": assembled.get("section_render_key"),
            "bundle": assembled.get("bundle"),
            "reason": "persisted_support_bundle_not_ready",
        }, ensure_ascii=False, indent=2, default=str))
        raise SystemExit(2)
    if args.html_only:
        published = publisher.publish_support_report_html(
            business_date=args.business_date,
            agent_domain=args.agent_domain,
            slot=args.slot,
            output_dir=Path(args.output_dir),
            report_run_id=args.report_run_id,
            generated_at=_parse_generated_at(args.generated_at),
        )
        payload = {
            "artifact": published["artifact"],
            "html_path": published["html_path"],
            "manifest_path": published["manifest_path"],
        }
    else:
        published = publisher.publish_delivery_package(
            business_date=args.business_date,
            agent_domain=args.agent_domain,
            slot=args.slot,
            output_dir=Path(args.output_dir),
            report_run_id=args.report_run_id,
            generated_at=_parse_generated_at(args.generated_at),
        )
        payload = {
            "artifact": published["artifact"],
            "html_path": published["html_path"],
            "qa_path": published["qa_path"],
            "manifest_path": published["manifest_path"],
            "delivery_package_dir": published["delivery_package_dir"],
            "delivery_manifest_path": published["delivery_manifest_path"],
            "delivery_zip_path": published["delivery_zip_path"],
            "operator_summary_path": published["operator_summary_path"],
            "package_index_path": published["package_index_path"],
            "delivery_manifest": published["delivery_manifest"],
        }
        canonical_surface = _resolve_canonical_publish_surface(
            business_date=args.business_date,
            agent_domain=args.agent_domain,
            store=store,
        )
        if canonical_surface:
            payload.update(canonical_surface)
            workflow_handoff = dict(canonical_surface.get("workflow_handoff") or {})
            manifest_pointers = dict(workflow_handoff.get("manifest_pointers") or {})
            selected_handoff = dict(workflow_handoff.get("selected_handoff") or {})
            payload["delivery_package_dir"] = selected_handoff.get("selected_delivery_package_dir") or payload["delivery_package_dir"]
            payload["delivery_manifest_path"] = manifest_pointers.get("delivery_manifest_path") or payload["delivery_manifest_path"]
            payload["delivery_zip_path"] = manifest_pointers.get("delivery_zip_path") or payload["delivery_zip_path"]
            payload["operator_summary_path"] = manifest_pointers.get("operator_review_readme_path") or payload["operator_summary_path"]
            payload["package_index_path"] = manifest_pointers.get("package_index_path") or payload["package_index_path"]
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
