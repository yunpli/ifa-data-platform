#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone

from ifa_data_platform.fsj import LateMainFSJProducer
from ifa_data_platform.fsj.main_publish_cli import (
    MainPublishFlowConfig,
    parse_generated_at,
    resolve_canonical_publish_surface,
    run_main_publish_flow,
)
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError, enforce_non_live_test_roots

_FLOW = MainPublishFlowConfig(
    slot="late",
    producer_label="LateMainFSJProducer",
    summary_name="main_late_publish_summary.json",
    artifact_type="fsj_main_late_publish_summary",
    report_run_id_prefix_default="fsj-main-late",
    flow_name="fsj_main_late_publish",
)


def _parse_generated_at(value: str | None) -> datetime | None:
    return parse_generated_at(value)


def _resolve_canonical_publish_surface(*, business_date: str):
    return resolve_canonical_publish_surface(business_date=business_date)


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist + publish A-share FSJ late MAIN report through one canonical operator command.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--generated-at", help="ISO8601 timestamp; defaults to current UTC time")
    parser.add_argument("--report-run-id-prefix", default=_FLOW.report_run_id_prefix_default)
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--output-profile", choices=["internal", "review", "customer"], default="internal")
    args = parser.parse_args()

    generated_at = _parse_generated_at(args.generated_at) or datetime.now(timezone.utc)
    enforce_non_live_test_roots(flow_name=_FLOW.flow_name, output_path=args.output_root)
    payload = run_main_publish_flow(
        config=_FLOW,
        business_date=args.business_date,
        output_root=args.output_root,
        generated_at=generated_at,
        report_run_id_prefix=args.report_run_id_prefix,
        include_empty=args.include_empty,
        output_profile=getattr(args, "output_profile", "internal"),
        producer_factory=LateMainFSJProducer,
        resolve_canonical_surface=_resolve_canonical_publish_surface,
        subprocess_run=subprocess.run,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    if payload["status"] != "ready":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
