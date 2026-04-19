from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text

from ifa_data_platform.archive_v2.runner import ALL_FAMILY_META, DIRECT_DEST_TABLES

ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
TEST_TRIGGER_PREFIXES = (
    'manual_validation_',
    'manual_tail_',
    'manual_business_contract_',
    'manual_retest_',
    'manual_profile',
    'operator_repair_batch',
)
PROD_TRIGGER_SOURCES = {
    'production_nightly_archive_v2',
    'runtime_archive_v2_nightly',
}
DATA_TABLES = [
    'ifa_archive_equity_daily',
    'ifa_archive_index_daily',
    'ifa_archive_etf_daily',
    'ifa_archive_non_equity_daily',
    'ifa_archive_macro_daily',
    'ifa_archive_announcements_daily',
    'ifa_archive_news_daily',
    'ifa_archive_research_reports_daily',
    'ifa_archive_investor_qa_daily',
    'ifa_archive_dragon_tiger_daily',
    'ifa_archive_limit_up_detail_daily',
    'ifa_archive_limit_up_down_status_daily',
    'ifa_archive_sector_performance_daily',
    'ifa_archive_equity_60m',
    'ifa_archive_etf_60m',
    'ifa_archive_index_60m',
    'ifa_archive_futures_60m',
    'ifa_archive_commodity_60m',
    'ifa_archive_precious_metal_60m',
]


def family_dest_table(family: str) -> str | None:
    meta = ALL_FAMILY_META.get(family, {})
    return meta.get('dest_table') or DIRECT_DEST_TABLES.get(family)


def load_scope() -> dict:
    run_sql = text(
        """
        select r.run_id::text as run_id, r.trigger_source, r.profile_name,
               array_agg(distinct i.business_date::text order by i.business_date::text) as business_dates,
               array_agg(distinct i.family_name order by i.family_name) as families
        from ifa2.ifa_archive_runs r
        join ifa2.ifa_archive_run_items i on i.run_id = r.run_id
        where r.start_time >= now() - interval '30 days'
          and r.trigger_source not in ('production_nightly_archive_v2', 'runtime_archive_v2_nightly')
          and (r.trigger_source like 'manual_%' or r.trigger_source = 'operator_repair_batch')
        group by 1,2,3
        order by max(r.start_time) desc
        """
    )
    pair_sql = text(
        """
        select i.business_date::text as business_date, i.family_name, max(r.trigger_source) as trigger_source
        from ifa2.ifa_archive_runs r
        join ifa2.ifa_archive_run_items i on i.run_id = r.run_id
        where r.start_time >= now() - interval '30 days'
          and (r.trigger_source like 'manual_%' or r.trigger_source = 'operator_repair_batch')
        group by 1,2
        order by 1,2
        """
    )
    prod_pair_sql = text(
        """
        select distinct i.business_date::text as business_date, i.family_name
        from ifa2.ifa_archive_runs r
        join ifa2.ifa_archive_run_items i on i.run_id = r.run_id
        where r.start_time >= now() - interval '30 days'
          and r.trigger_source in ('production_nightly_archive_v2', 'runtime_archive_v2_nightly')
        """
    )
    with ENGINE.begin() as conn:
        runs = [dict(r) for r in conn.execute(run_sql).mappings().all()]
        pairs = [dict(r) for r in conn.execute(pair_sql).mappings().all()]
        protected = {(r.business_date, r.family_name) for r in conn.execute(prod_pair_sql).all()}

    for row in pairs:
        row['dest_table'] = family_dest_table(row['family_name'])
        row['protected_by_production'] = (row['business_date'], row['family_name']) in protected
    deletable_pairs = [row for row in pairs if row['dest_table'] and not row['protected_by_production']]
    protected_pairs = [row for row in pairs if row['protected_by_production']]
    dates = sorted({row['business_date'] for row in pairs})
    families = sorted({row['family_name'] for row in pairs})
    return {'runs': runs, 'pairs': pairs, 'deletable_pairs': deletable_pairs, 'protected_pairs': protected_pairs, 'dates': dates, 'families': families}


def count_tables(dates: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    if not dates:
        return out
    date_values = [date.fromisoformat(d) for d in dates]
    with ENGINE.begin() as conn:
        for table in DATA_TABLES:
            out[table] = int(conn.execute(text(f"select count(*) from ifa2.{table} where business_date = any(:dates)"), {'dates': date_values}).scalar_one())
        out['ifa_archive_completeness'] = int(conn.execute(text("select count(*) from ifa2.ifa_archive_completeness where business_date = any(:dates)"), {'dates': date_values}).scalar_one())
        out['ifa_archive_repair_queue'] = int(conn.execute(text("select count(*) from ifa2.ifa_archive_repair_queue where business_date = any(:dates)"), {'dates': date_values}).scalar_one())
        out['ifa_archive_run_items'] = int(conn.execute(text("select count(*) from ifa2.ifa_archive_run_items where business_date = any(:dates)"), {'dates': date_values}).scalar_one())
        out['ifa_archive_runs_manual'] = int(conn.execute(text("select count(*) from ifa2.ifa_archive_runs where trigger_source not in ('production_nightly_archive_v2','runtime_archive_v2_nightly') and (trigger_source like 'manual_%' or trigger_source='operator_repair_batch') and run_id in (select distinct run_id from ifa2.ifa_archive_run_items where business_date = any(:dates))"), {'dates': date_values}).scalar_one())
        out['archive_runs_test_legacy'] = int(conn.execute(text("select count(*) from ifa2.archive_runs where started_at >= now() - interval '30 days' and (job_name ilike '%test%' or job_name ilike '%validation%' or job_name ilike '%retest%')")).scalar_one())
    return out


def cleanup_scope(scope: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    dates = scope['dates']
    if not dates:
        return out
    date_values = [date.fromisoformat(d) for d in dates]
    with ENGINE.begin() as conn:
        for row in scope['deletable_pairs']:
            table = row['dest_table']
            key = f"{table}::{row['business_date']}::{row['family_name']}"
            out[key] = int(conn.execute(text(f"delete from ifa2.{table} where business_date = :business_date"), {'business_date': date.fromisoformat(row['business_date'])}).rowcount or 0)
        out['ifa_archive_completeness_manual_only'] = int(conn.execute(text("delete from ifa2.ifa_archive_completeness c using ifa2.ifa_archive_runs r where c.last_run_id = r.run_id and (r.trigger_source like 'manual_%' or r.trigger_source='operator_repair_batch')" )).rowcount or 0)
        out['ifa_archive_repair_queue_manual_dates'] = int(conn.execute(text("delete from ifa2.ifa_archive_repair_queue where business_date = any(:dates)"), {'dates': date_values}).rowcount or 0)
        out['ifa_archive_run_items_manual'] = int(conn.execute(text("delete from ifa2.ifa_archive_run_items i using ifa2.ifa_archive_runs r where i.run_id = r.run_id and (r.trigger_source like 'manual_%' or r.trigger_source='operator_repair_batch')" )).rowcount or 0)
        out['ifa_archive_runs_manual_orphan'] = int(conn.execute(text("delete from ifa2.ifa_archive_runs r where (r.trigger_source like 'manual_%' or r.trigger_source='operator_repair_batch') and not exists (select 1 from ifa2.ifa_archive_run_items i where i.run_id = r.run_id)" )).rowcount or 0)
        out['archive_runs_test_legacy'] = int(conn.execute(text("delete from ifa2.archive_runs where started_at >= now() - interval '30 days' and (job_name ilike '%test%' or job_name ilike '%validation%' or job_name ilike '%retest%')" )).rowcount or 0)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    scope = load_scope()
    before = count_tables(scope['dates'])
    deleted = cleanup_scope(scope) if args.apply else {}
    after = count_tables(scope['dates']) if args.apply else before
    payload = {
        'scope': scope,
        'before': before,
        'deleted': deleted,
        'after': after,
        'untouched_truth_tables': [
            'Business Layer truth/config tables',
            'trading calendar / trade day truth tables',
            'runtime schedule truth tables',
            'runtime worker state truth tables',
            'canonical retained source truth tables',
        ],
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    print(args.output)


if __name__ == '__main__':
    main()
