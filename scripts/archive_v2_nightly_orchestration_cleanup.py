from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text

ENGINE = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dates', nargs='+', required=True)
    ap.add_argument('--families', nargs='+', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    date_values = [date.fromisoformat(d) for d in args.dates]
    out = {'dates': args.dates, 'families': args.families, 'deleted': {}}
    with ENGINE.begin() as conn:
        # explicit table map to keep command auditable and deterministic
        table_map = {
            'equity_daily': 'ifa_archive_equity_daily',
            'index_daily': 'ifa_archive_index_daily',
            'etf_daily': 'ifa_archive_etf_daily',
            'non_equity_daily': 'ifa_archive_non_equity_daily',
            'macro_daily': 'ifa_archive_macro_daily',
            'announcements_daily': 'ifa_archive_announcements_daily',
            'news_daily': 'ifa_archive_news_daily',
            'research_reports_daily': 'ifa_archive_research_reports_daily',
            'investor_qa_daily': 'ifa_archive_investor_qa_daily',
            'dragon_tiger_daily': 'ifa_archive_dragon_tiger_daily',
            'limit_up_detail_daily': 'ifa_archive_limit_up_detail_daily',
            'limit_up_down_status_daily': 'ifa_archive_limit_up_down_status_daily',
            'sector_performance_daily': 'ifa_archive_sector_performance_daily',
            'highfreq_event_stream_daily': 'ifa_archive_highfreq_event_stream_daily',
            'highfreq_limit_event_stream_daily': 'ifa_archive_highfreq_limit_event_stream_daily',
            'highfreq_sector_breadth_daily': 'ifa_archive_highfreq_sector_breadth_daily',
            'highfreq_sector_heat_daily': 'ifa_archive_highfreq_sector_heat_daily',
            'highfreq_leader_candidate_daily': 'ifa_archive_highfreq_leader_candidate_daily',
            'highfreq_intraday_signal_state_daily': 'ifa_archive_highfreq_intraday_signal_state_daily',
        }
        for family in args.families:
            table = table_map.get(family)
            if table:
                out['deleted'][table] = int(conn.execute(text(f"delete from ifa2.{table} where business_date = any(:dates)"), {'dates': date_values}).rowcount or 0)
        out['deleted']['ifa_archive_completeness'] = int(conn.execute(text("delete from ifa2.ifa_archive_completeness where business_date = any(:dates) and family_name = any(:families)"), {'dates': date_values, 'families': args.families}).rowcount or 0)
        out['deleted']['ifa_archive_repair_queue'] = int(conn.execute(text("delete from ifa2.ifa_archive_repair_queue where business_date = any(:dates) and family_name = any(:families)"), {'dates': date_values, 'families': args.families}).rowcount or 0)
        out['deleted']['ifa_archive_run_items'] = int(conn.execute(text("delete from ifa2.ifa_archive_run_items where business_date = any(:dates) and family_name = any(:families) and run_id in (select run_id from ifa2.ifa_archive_runs where trigger_source in ('production_nightly_archive_v2','runtime_archive_v2_nightly'))"), {'dates': date_values, 'families': args.families}).rowcount or 0)
        out['deleted']['ifa_archive_runs'] = int(conn.execute(text("delete from ifa2.ifa_archive_runs r where r.trigger_source in ('production_nightly_archive_v2','runtime_archive_v2_nightly') and not exists (select 1 from ifa2.ifa_archive_run_items i where i.run_id=r.run_id)" )).rowcount or 0)
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(args.output)


if __name__ == '__main__':
    main()
