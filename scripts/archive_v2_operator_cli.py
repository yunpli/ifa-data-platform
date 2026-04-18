#!/usr/bin/env python3
from __future__ import annotations

import argparse

from ifa_data_platform.archive_v2.operator import (
    summary, gaps, repair_backlog, recent_runs, family_health, date_health,
    actionable_backlog, non_actionable_backlog, select_repair_targets,
    build_repair_batch_notes, to_json,
)
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner

REPAIR_EXECUTOR_PROFILE = 'profiles/archive_v2_milestone7_repair_executor.json'


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
    p3.add_argument('--actionable-only', action='store_true')
    p3.add_argument('--exclude-nonactionable', action='store_true')

    p4 = sub.add_parser('recent-runs')
    p4.add_argument('--limit', type=int, default=10)

    p5 = sub.add_parser('family-health')
    p5.add_argument('--limit', type=int, default=30)

    p6 = sub.add_parser('date-health')
    p6.add_argument('--days', type=int, default=14)

    p7 = sub.add_parser('actionable-backlog')
    p7.add_argument('--limit', type=int, default=20)

    p8 = sub.add_parser('nonactionable-backlog')
    p8.add_argument('--limit', type=int, default=20)

    p9 = sub.add_parser('repair-batch')
    p9.add_argument('--limit', type=int, default=10)
    p9.add_argument('--business-date')
    p9.add_argument('--start-date')
    p9.add_argument('--end-date')
    p9.add_argument('--family', action='append')
    p9.add_argument('--status', action='append')
    p9.add_argument('--urgency', action='append')
    p9.add_argument('--min-priority', type=int)
    p9.add_argument('--retry-due-only', action='store_true')
    p9.add_argument('--include-nonactionable', action='store_true')
    p9.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'summary':
        print(to_json(summary(days=args.days, limit=args.limit)))
    elif args.cmd == 'gaps':
        print(to_json(gaps(days=args.days)))
    elif args.cmd == 'repair-backlog':
        print(to_json(repair_backlog(limit=args.limit, actionable_only=args.actionable_only, include_non_actionable=not args.exclude_nonactionable)))
    elif args.cmd == 'recent-runs':
        print(to_json(recent_runs(limit=args.limit)))
    elif args.cmd == 'family-health':
        print(to_json(family_health(limit=args.limit)))
    elif args.cmd == 'date-health':
        print(to_json(date_health(days=args.days)))
    elif args.cmd == 'actionable-backlog':
        print(to_json(actionable_backlog(limit=args.limit)))
    elif args.cmd == 'nonactionable-backlog':
        print(to_json(non_actionable_backlog(limit=args.limit)))
    elif args.cmd == 'repair-batch':
        filters = {
            'limit': args.limit,
            'business_date': args.business_date,
            'start_date': args.start_date,
            'end_date': args.end_date,
            'family_names': args.family,
            'statuses': args.status,
            'urgencies': args.urgency,
            'min_priority': args.min_priority,
            'retry_due_only': args.retry_due_only,
            'actionable_only': not args.include_nonactionable,
            'include_non_actionable': args.include_nonactionable,
        }
        targets = select_repair_targets(
            limit=args.limit,
            business_date=args.business_date,
            start_date=args.start_date,
            end_date=args.end_date,
            family_names=args.family,
            statuses=args.status,
            urgencies=args.urgency,
            min_priority=args.min_priority,
            retry_due_only=args.retry_due_only,
            actionable_only=not args.include_nonactionable,
            include_non_actionable=args.include_nonactionable,
        )
        if args.dry_run:
            print(to_json({'ok': True, 'dry_run': True, 'selected_count': len(targets), 'filters': filters, 'targets': targets}))
            return
        runner = ArchiveV2Runner(REPAIR_EXECUTOR_PROFILE)
        notes = build_repair_batch_notes(targets, filters)
        result = runner.run_selected_targets(targets, trigger_source='operator_repair_batch', notes=notes)
        payload = {'filters': filters, 'selected_count': len(targets), 'targets': targets, **result}
        print(to_json(payload))


if __name__ == '__main__':
    main()
