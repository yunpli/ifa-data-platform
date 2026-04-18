#!/usr/bin/env python3
from __future__ import annotations

import argparse

from ifa_data_platform.archive_v2.operator import (
    summary, gaps, repair_backlog, recent_runs, family_health, date_health,
    actionable_backlog, non_actionable_backlog, select_repair_targets,
    build_repair_batch_notes, to_json, claim_repair_targets, load_claimed_targets,
    claimed_backlog, suppressed_backlog, repair_history, acknowledge_backlog,
    unsuppress_backlog, release_claims,
)
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner

REPAIR_EXECUTOR_PROFILE = 'profiles/archive_v2_milestone7_repair_executor.json'


def _common_scope_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--business-date')
    parser.add_argument('--start-date')
    parser.add_argument('--end-date')
    parser.add_argument('--family', action='append')
    parser.add_argument('--status', action='append')
    parser.add_argument('--urgency', action='append')
    parser.add_argument('--min-priority', type=int)
    parser.add_argument('--retry-due-only', action='store_true')
    parser.add_argument('--include-nonactionable', action='store_true')
    parser.add_argument('--include-suppressed', action='store_true')


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
    p3.add_argument('--include-suppressed', action='store_true')

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
    _common_scope_args(p9)
    p9.add_argument('--claim-only', action='store_true')
    p9.add_argument('--claim-id')
    p9.add_argument('--claimed-by', default='operator_cli')
    p9.add_argument('--lease-minutes', type=int, default=15)
    p9.add_argument('--dry-run', action='store_true')

    p10 = sub.add_parser('claimed-backlog')
    p10.add_argument('--limit', type=int, default=20)
    p10.add_argument('--active-only', action='store_true')

    p11 = sub.add_parser('repair-history')
    p11.add_argument('--limit', type=int, default=20)

    p12 = sub.add_parser('suppressed-backlog')
    p12.add_argument('--limit', type=int, default=20)

    p13 = sub.add_parser('acknowledge-backlog')
    p13.add_argument('--business-date')
    p13.add_argument('--family', action='append')
    p13.add_argument('--reason', required=True)
    p13.add_argument('--acknowledged-by', default='operator_cli')
    p13.add_argument('--suppress-hours', type=int)
    p13.add_argument('--include-actionable', action='store_true')

    p14 = sub.add_parser('unsuppress-backlog')
    p14.add_argument('--business-date')
    p14.add_argument('--family', action='append')

    p15 = sub.add_parser('release-claims')
    p15.add_argument('--claim-id', required=True)
    p15.add_argument('--released-by', default='operator_cli')
    p15.add_argument('--reason', default='manual release')

    args = parser.parse_args()
    if args.cmd == 'summary':
        print(to_json(summary(days=args.days, limit=args.limit)))
    elif args.cmd == 'gaps':
        print(to_json(gaps(days=args.days)))
    elif args.cmd == 'repair-backlog':
        print(to_json(repair_backlog(limit=args.limit, actionable_only=args.actionable_only, include_non_actionable=not args.exclude_nonactionable, include_suppressed=args.include_suppressed)))
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
    elif args.cmd == 'claimed-backlog':
        print(to_json(claimed_backlog(limit=args.limit, include_expired=not args.active_only)))
    elif args.cmd == 'repair-history':
        print(to_json(repair_history(limit=args.limit)))
    elif args.cmd == 'suppressed-backlog':
        print(to_json(suppressed_backlog(limit=args.limit)))
    elif args.cmd == 'acknowledge-backlog':
        print(to_json(acknowledge_backlog(
            acknowledged_by=args.acknowledged_by,
            reason=args.reason,
            business_date=args.business_date,
            family_names=args.family,
            non_actionable_only=not args.include_actionable,
            suppress_hours=args.suppress_hours,
        )))
    elif args.cmd == 'unsuppress-backlog':
        print(to_json(unsuppress_backlog(business_date=args.business_date, family_names=args.family)))
    elif args.cmd == 'release-claims':
        print(to_json(release_claims(args.claim_id, args.released_by, args.reason)))
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
            'include_suppressed': args.include_suppressed,
            'lease_minutes': args.lease_minutes,
            'claimed_by': args.claimed_by,
        }
        if args.claim_id:
            targets = load_claimed_targets(args.claim_id, claimed_by=args.claimed_by, include_expired=True)
            if args.dry_run:
                print(to_json({'ok': True, 'dry_run': True, 'claim_id': args.claim_id, 'selected_count': len(targets), 'filters': filters, 'targets': targets}))
                return
            runner = ArchiveV2Runner(REPAIR_EXECUTOR_PROFILE)
            notes = build_repair_batch_notes(targets, filters, claim_id=args.claim_id)
            result = runner.run_selected_targets(targets, trigger_source='operator_repair_batch', notes=notes)
            payload = {'claim_id': args.claim_id, 'filters': filters, 'selected_count': len(targets), 'targets': targets, **result}
            print(to_json(payload))
            return

        if args.dry_run:
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
                include_suppressed=args.include_suppressed,
                include_claimed=False,
            )
            print(to_json({'ok': True, 'dry_run': True, 'selected_count': len(targets), 'filters': filters, 'targets': targets}))
            return

        claim_payload = claim_repair_targets(
            claimed_by=args.claimed_by,
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
            include_suppressed=args.include_suppressed,
            lease_minutes=args.lease_minutes,
        )
        if args.claim_only:
            print(to_json({'ok': True, 'claim_only': True, **claim_payload, 'selected_count': len(claim_payload['targets']), 'filters': filters}))
            return
        targets = claim_payload['targets']
        runner = ArchiveV2Runner(REPAIR_EXECUTOR_PROFILE)
        notes = build_repair_batch_notes(targets, filters, claim_id=claim_payload['claim_id'])
        result = runner.run_selected_targets(targets, trigger_source='operator_repair_batch', notes=notes)
        payload = {**claim_payload, 'filters': filters, 'selected_count': len(targets), **result}
        print(to_json(payload))


if __name__ == '__main__':
    main()
