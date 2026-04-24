#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj import (
    EarlyAITechSupportProducer,
    EarlyCommoditiesSupportProducer,
    EarlyMacroSupportProducer,
    LateAITechSupportProducer,
    LateCommoditiesSupportProducer,
    LateMacroSupportProducer,
)
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError, enforce_non_live_test_roots

VALID_DOMAINS = ["macro", "commodities", "ai_tech"]
PRODUCER_REGISTRY = {
    ("early", "macro"): EarlyMacroSupportProducer,
    ("early", "commodities"): EarlyCommoditiesSupportProducer,
    ("early", "ai_tech"): EarlyAITechSupportProducer,
    ("late", "macro"): LateMacroSupportProducer,
    ("late", "commodities"): LateCommoditiesSupportProducer,
    ("late", "ai_tech"): LateAITechSupportProducer,
}


def _build_operator_summary(*, business_date: str, slot: str, generated_at: datetime, results: list[dict]) -> str:
    persisted = [item for item in results if item["status"] == "persisted"]
    blocked = [item for item in results if item["status"] != "persisted"]
    lines = [
        f"FSJ support bundle persist｜{business_date}｜{slot}",
        f"generated_at_utc={generated_at.isoformat()}",
        f"persisted={len(persisted)}｜blocked={len(blocked)}｜domains={len(results)}",
        "",
    ]
    for item in results:
        lines.append(
            f"- {item['agent_domain']}: status={item['status']} bundle_id={item.get('bundle_id') or '-'} "
            f"object_count={item.get('object_count') or 0} evidence_link_count={item.get('evidence_link_count') or 0}"
        )
        if item.get("reason"):
            lines.append(f"  reason={item['reason']}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist A-share FSJ support bundle graphs for one slot/date.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--slot", required=True, choices=["early", "late"])
    parser.add_argument("--agent-domain", action="append", dest="agent_domains", choices=VALID_DOMAINS, help="Repeat to limit domains; defaults to all three support domains")
    parser.add_argument("--output-root", help="Optional output root for summary artifacts")
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc)
    domains = args.agent_domains or list(VALID_DOMAINS)
    enforce_non_live_test_roots(flow_name="fsj_support_bundle_persist", output_path=args.output_root)
    results: list[dict] = []

    for domain in domains:
        item = {
            "business_date": args.business_date,
            "slot": args.slot,
            "agent_domain": domain,
        }
        try:
            producer_cls = PRODUCER_REGISTRY[(args.slot, domain)]
            persisted = producer_cls().produce_and_persist(business_date=args.business_date)
            bundle = dict(persisted.get("bundle") or {})
            item.update(
                {
                    "status": "persisted",
                    "bundle_id": bundle.get("bundle_id"),
                    "bundle_status": bundle.get("status"),
                    "section_key": bundle.get("section_key"),
                    "object_count": len(persisted.get("objects") or []),
                    "edge_count": len(persisted.get("edges") or []),
                    "evidence_link_count": len(persisted.get("evidence_links") or []),
                    "observed_record_count": len(persisted.get("observed_records") or []),
                }
            )
        except Exception as exc:  # pragma: no cover - exercised via script tests
            item.update({
                "status": "blocked",
                "reason": f"{type(exc).__name__}: {exc}",
            })
        results.append(item)

    summary = {
        "artifact_type": "fsj_support_bundle_persist_summary",
        "artifact_version": "v1",
        "business_date": args.business_date,
        "slot": args.slot,
        "generated_at_utc": generated_at.isoformat(),
        "domains": domains,
        "persisted_count": sum(1 for item in results if item["status"] == "persisted"),
        "blocked_count": sum(1 for item in results if item["status"] != "persisted"),
        "results": results,
    }

    if args.output_root:
        root = Path(args.output_root)
        root.mkdir(parents=True, exist_ok=True)
        summary_path = root / "persist_summary.json"
        operator_summary_path = root / "operator_summary.txt"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        operator_summary_path.write_text(
            _build_operator_summary(
                business_date=args.business_date,
                slot=args.slot,
                generated_at=generated_at,
                results=results,
            ),
            encoding="utf-8",
        )
        summary["summary_path"] = str(summary_path.resolve())
        summary["operator_summary_path"] = str(operator_summary_path.resolve())

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    if summary["blocked_count"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
