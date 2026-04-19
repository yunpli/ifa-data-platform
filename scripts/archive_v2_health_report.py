from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from ifa_data_platform.archive_v2.db import engine


def fetch(sql: str, params: dict | None = None):
    with engine.begin() as conn:
        return [dict(r) for r in conn.execute(text(sql), params or {}).mappings().all()]


def build_report(days: int = 30, limit: int = 50) -> dict:
    family_windows = fetch(
        """
        select family_name,
               frequency,
               min(business_date)::text as earliest_seen_date,
               max(business_date)::text as latest_seen_date,
               min(case when status='completed' then business_date end)::text as earliest_completed_date,
               max(case when status='completed' then business_date end)::text as latest_completed_date,
               count(*) as total_rows,
               count(*) filter (where status='completed') as completed_rows,
               count(*) filter (where status<>'completed') as non_completed_rows
        from ifa2.ifa_archive_completeness
        group by family_name, frequency
        order by frequency, family_name
        """
    )
    recent_dates = fetch(
        """
        select business_date::text as business_date,
               count(*) as total_families,
               count(*) filter (where status='completed') as completed_families,
               count(*) filter (where status<>'completed') as non_completed_families
        from ifa2.ifa_archive_completeness
        where business_date >= current_date - :days
        group by business_date
        order by business_date desc
        limit :limit
        """,
        {'days': days, 'limit': limit},
    )
    latest_gaps = fetch(
        """
        select business_date::text as business_date,
               family_name,
               frequency,
               status,
               row_count,
               last_error,
               updated_at::text as updated_at
        from ifa2.ifa_archive_completeness
        where status <> 'completed'
        order by business_date desc, frequency, family_name
        limit :limit
        """,
        {'limit': limit},
    )
    repair_backlog = fetch(
        """
        select business_date::text as business_date,
               family_name,
               frequency,
               status,
               reason_code,
               actionability,
               priority,
               urgency,
               retry_count,
               suppression_state,
               claimed_by,
               retry_after::text as retry_after
        from ifa2.ifa_archive_repair_queue
        order by priority desc, business_date desc, family_name
        limit :limit
        """,
        {'limit': limit},
    )
    recent_runs = fetch(
        """
        select run_id::text as run_id,
               trigger_source,
               profile_name,
               mode,
               start_time::text as start_time,
               end_time::text as end_time,
               status,
               notes
        from ifa2.ifa_archive_runs
        order by start_time desc
        limit :limit
        """,
        {'limit': limit},
    )
    return {
        'family_windows': family_windows,
        'recent_dates': recent_dates,
        'latest_gaps': latest_gaps,
        'repair_backlog': repair_backlog,
        'recent_runs': recent_runs,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--limit', type=int, default=50)
    ap.add_argument('--output', default=None)
    args = ap.parse_args()
    payload = build_report(days=args.days, limit=args.limit)
    text_out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text_out)
    print(text_out)


if __name__ == '__main__':
    main()
