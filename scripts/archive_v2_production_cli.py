#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from ifa_data_platform.archive_v2.production import run_nightly_production, run_manual_backfill, resolve_production_business_date, PRODUCTION_NIGHTLY_FAMILIES, PRODUCTION_MANUAL_BACKFILL_FAMILIES, PRODUCTION_REPAIR_PATH, MANUAL_CLI_NIGHTLY_TRIGGER, OFFICIAL_RUNTIME_NIGHTLY_TRIGGER


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('nightly')
    p1.add_argument('--business-date')
    p1.add_argument('--trigger-source', default=MANUAL_CLI_NIGHTLY_TRIGGER)

    p2 = sub.add_parser('backfill')
    p2.add_argument('--start-date')
    p2.add_argument('--end-date')
    p2.add_argument('--backfill-days', type=int)

    p3 = sub.add_parser('plan')
    p3.add_argument('--business-date')

    args = parser.parse_args()
    if args.cmd == 'nightly':
        print(json.dumps(run_nightly_production(business_date=args.business_date, trigger_source=args.trigger_source), ensure_ascii=False, indent=2, default=str))
    elif args.cmd == 'backfill':
        print(json.dumps(run_manual_backfill(start_date=args.start_date, end_date=args.end_date, backfill_days=args.backfill_days), ensure_ascii=False, indent=2, default=str))
    elif args.cmd == 'plan':
        business_date = args.business_date or resolve_production_business_date()
        print(json.dumps({
            'production_business_date': business_date,
            'nightly_profile_name': 'archive_v2_production_nightly_daily_final',
            'family_count': len(PRODUCTION_NIGHTLY_FAMILIES),
            'families': PRODUCTION_NIGHTLY_FAMILIES,
            'manual_backfill_family_count': len(PRODUCTION_MANUAL_BACKFILL_FAMILIES),
            'manual_backfill_families': PRODUCTION_MANUAL_BACKFILL_FAMILIES,
            'manual_repair_path': PRODUCTION_REPAIR_PATH,
            'official_runtime_nightly_trigger': OFFICIAL_RUNTIME_NIGHTLY_TRIGGER,
            'manual_cli_nightly_trigger': MANUAL_CLI_NIGHTLY_TRIGGER,
        }, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
