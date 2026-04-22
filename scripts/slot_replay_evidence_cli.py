#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from ifa_data_platform.runtime.replay_evidence import ReplayEvidenceStore, artifact_from_path


def cmd_capture(args: argparse.Namespace) -> None:
    store = ReplayEvidenceStore()
    artifact = artifact_from_path(args.artifact_path, producer=args.artifact_producer) if args.artifact_path else None
    payload = store.capture_slot_evidence(
        trade_date=args.trade_date,
        slot_key=args.slot,
        perspective=args.perspective,
        capture_reason=args.capture_reason,
        artifact=artifact,
        run_ids=args.run_id or [],
        schedule_keys=args.schedule_key or [],
        notes=args.notes,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def cmd_list(args: argparse.Namespace) -> None:
    store = ReplayEvidenceStore()
    payload = store.list_evidence(
        trade_date=args.trade_date,
        slot_key=args.slot,
        perspective=args.perspective,
        limit=args.limit,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def cmd_get(args: argparse.Namespace) -> None:
    store = ReplayEvidenceStore()
    payload = store.get_evidence(args.evidence_id)
    print(json.dumps(payload or {}, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture/query slot replay evidence snapshots")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("capture")
    p1.add_argument("--trade-date", required=True)
    p1.add_argument("--slot", required=True, choices=["early", "mid", "late"])
    p1.add_argument("--perspective", default="observed", choices=["observed", "corrected"])
    p1.add_argument("--capture-reason", default="manual_capture")
    p1.add_argument("--artifact-path")
    p1.add_argument("--artifact-producer", default="manual")
    p1.add_argument("--run-id", action="append")
    p1.add_argument("--schedule-key", action="append")
    p1.add_argument("--notes")
    p1.set_defaults(func=cmd_capture)

    p2 = sub.add_parser("list")
    p2.add_argument("--trade-date")
    p2.add_argument("--slot", choices=["early", "mid", "late"])
    p2.add_argument("--perspective", choices=["observed", "corrected"])
    p2.add_argument("--limit", type=int, default=20)
    p2.set_defaults(func=cmd_list)

    p3 = sub.add_parser("get")
    p3.add_argument("evidence_id")
    p3.set_defaults(func=cmd_get)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
