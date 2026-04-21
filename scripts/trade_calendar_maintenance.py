#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date, datetime

from ifa_data_platform.lowfreq.trade_calendar_maintenance import TradeCalendarMaintenanceService


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Trade calendar maintenance / health-check CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="Manual exact-range refresh/backfill")
    p_sync.add_argument("--start-date", required=True, type=_parse_date)
    p_sync.add_argument("--end-date", required=True, type=_parse_date)
    p_sync.add_argument("--exchange", default="SSE")
    p_sync.add_argument("--no-promote", action="store_true")

    p_monthly = sub.add_parser("monthly-sync", help="Bounded monthly maintenance refresh")
    p_monthly.add_argument("--anchor-date", type=_parse_date)
    p_monthly.add_argument("--exchange", default="SSE")
    p_monthly.add_argument("--lookback-days", type=int, default=45)
    p_monthly.add_argument("--forward-days", type=int, default=400)
    p_monthly.add_argument("--no-promote", action="store_true")

    p_health = sub.add_parser("health-check", help="Calendar validity check without syncing")
    p_health.add_argument("--anchor-date", type=_parse_date)
    p_health.add_argument("--exchange", default="SSE")
    p_health.add_argument("--past-days-required", type=int, default=30)
    p_health.add_argument("--future-days-required", type=int, default=180)
    p_health.add_argument("--max-active-version-age-days", type=int, default=45)

    args = parser.parse_args()
    svc = TradeCalendarMaintenanceService()

    if args.cmd == "sync":
        result = svc.sync_range(
            start_date=args.start_date,
            end_date=args.end_date,
            exchange=args.exchange,
            promote=not args.no_promote,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
        return

    if args.cmd == "monthly-sync":
        result = svc.monthly_sync(
            anchor_date=args.anchor_date,
            exchange=args.exchange,
            lookback_days=args.lookback_days,
            forward_days=args.forward_days,
            promote=not args.no_promote,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
        return

    report = svc.health_check(
        anchor_date=args.anchor_date,
        exchange=args.exchange,
        past_days_required=args.past_days_required,
        future_days_required=args.future_days_required,
        max_active_version_age_days=args.max_active_version_age_days,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
