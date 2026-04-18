#!/usr/bin/env python3
from __future__ import annotations

import argparse

from ifa_data_platform.archive_v2.operator import summary, gaps, repair_backlog, recent_runs, family_health, date_health, to_json


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('summary')
    p1.add_argument('--days', type=int, default=14)
    p1.add_argument('--limit', type=int, default=10)

    p2 = sub.add_parser('gaps')
    p2.add_argument('--days', type=int, default=14)

    p3 = sub.add_parser('repair-backlog')
    p3.add_argument('--limit', type=int, default=20)

    p4 = sub.add_parser('recent-runs')
    p4.add_argument('--limit', type=int, default=10)

    p5 = sub.add_parser('family-health')
    p5.add_argument('--limit', type=int, default=30)

    p6 = sub.add_parser('date-health')
    p6.add_argument('--days', type=int, default=14)

    args = parser.parse_args()
    if args.cmd == 'summary':
        print(to_json(summary(days=args.days, limit=args.limit)))
    elif args.cmd == 'gaps':
        print(to_json(gaps(days=args.days)))
    elif args.cmd == 'repair-backlog':
        print(to_json(repair_backlog(limit=args.limit)))
    elif args.cmd == 'recent-runs':
        print(to_json(recent_runs(limit=args.limit)))
    elif args.cmd == 'family-health':
        print(to_json(family_health(limit=args.limit)))
    elif args.cmd == 'date-health':
        print(to_json(date_health(days=args.days)))


if __name__ == '__main__':
    main()
