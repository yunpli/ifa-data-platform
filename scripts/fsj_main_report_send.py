#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from ifa_data_platform.fsj.report_sender import DispatchTarget, FSJMainReportDispatchService, ReportDispatchSendError


def main() -> None:
    parser = argparse.ArgumentParser(description="Send the selected FSJ MAIN delivery package via OpenClaw and persist truthful dispatch receipts.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--business-date")
    target.add_argument("--latest", action="store_true", help="Resolve the latest active MAIN delivery surface from DB truth")
    parser.add_argument("--slot", choices=["early", "mid", "late"], help="Optional strongest-slot filter when resolving --latest")
    parser.add_argument("--max-business-date", help="Optional latest business date bound when resolving --latest")
    parser.add_argument("--target", required=True, help="Telegram target/chat id")
    parser.add_argument("--account", default="main")
    parser.add_argument("--channel", default="telegram", choices=["telegram"])
    parser.add_argument("--silent", action="store_true")
    parser.add_argument("--format", choices=["json"], default="json")
    args = parser.parse_args()

    service = FSJMainReportDispatchService()
    dispatch_target = DispatchTarget(
        target=args.target,
        account=args.account,
        channel=args.channel,
        silent=args.silent,
    )

    try:
        if args.business_date:
            payload = service.dispatch_business_date_report(
                business_date=args.business_date,
                dispatch_target=dispatch_target,
            )
        else:
            payload = service.dispatch_latest_ready_report(
                dispatch_target=dispatch_target,
                strongest_slot=args.slot,
                max_business_date=args.max_business_date,
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    except ReportDispatchSendError as exc:
        payload = {
            "status": "dispatch_failed",
            "error_class": type(exc).__name__,
            "error_message": str(exc),
            "dispatch_receipt": exc.receipt,
            "return_code": exc.return_code,
            "stdout": exc.stdout,
            "stderr": exc.stderr,
            "command": exc.command,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
