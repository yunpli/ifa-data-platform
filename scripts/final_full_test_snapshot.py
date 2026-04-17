from __future__ import annotations

import json
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
OUT_DIR = Path('artifacts/final_full_test')
OUT_DIR.mkdir(parents=True, exist_ok=True)
label = sys.argv[1]
TABLES = [
    'unified_runtime_runs', 'job_runs', 'lowfreq_runs', 'midfreq_execution_summary', 'highfreq_execution_summary', 'highfreq_runs', 'archive_runs', 'archive_checkpoints', 'archive_target_catchup', 'archive_summary_daily', 'daily_structured_output_archive',
    'trade_cal_history', 'stock_basic_history', 'index_basic_history', 'fund_basic_etf_history', 'announcements_history', 'news_history', 'research_reports_history', 'investor_qa_history',
    'equity_daily_bar_history', 'index_daily_bar_history', 'etf_daily_bar_history', 'northbound_flow_history', 'limit_up_down_status_history', 'margin_financing_history', 'southbound_flow_history', 'turnover_rate_history', 'main_force_flow_history', 'sector_performance_history', 'dragon_tiger_list_history', 'limit_up_detail_history',
    'highfreq_stock_1m_working', 'highfreq_index_1m_working', 'highfreq_proxy_1m_working', 'highfreq_futures_minute_working', 'highfreq_open_auction_working', 'highfreq_close_auction_working', 'highfreq_event_stream_working', 'highfreq_sector_breadth_working', 'highfreq_sector_heat_working', 'highfreq_leader_candidate_working', 'highfreq_limit_event_stream_working', 'highfreq_intraday_signal_state_working',
    'stock_60min_history', 'futures_60min_history', 'commodity_60min_history', 'precious_metal_60min_history', 'stock_15min_history', 'stock_minute_history', 'futures_15min_history', 'futures_minute_history', 'commodity_15min_history', 'commodity_minute_history', 'precious_metal_15min_history', 'precious_metal_minute_history'
]
payload = {'label': label, 'tables': {}}
with engine.begin() as conn:
    for t in TABLES:
        payload['tables'][t] = conn.execute(text(f'select count(*) from ifa2."{t}"')).scalar_one()
    payload['recent_archive_jobs'] = [dict(r) for r in conn.execute(text("select job_name, dataset_name, asset_type, status, records_processed, started_at, completed_at from ifa2.archive_runs order by started_at desc limit 30")).mappings().all()]
OUT = OUT_DIR / f'{label}.json'
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
print(OUT)
