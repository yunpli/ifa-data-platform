from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
OUT = Path('artifacts/tail_closure_inspect_2026-04-16_2120.json')

SQL = {
    'highfreq_source_counts': {
        'highfreq_stock_1m_working': 'select count(*) from ifa2.highfreq_stock_1m_working',
        'highfreq_index_1m_working': 'select count(*) from ifa2.highfreq_index_1m_working',
        'highfreq_proxy_1m_working': 'select count(*) from ifa2.highfreq_proxy_1m_working',
        'highfreq_futures_minute_working': 'select count(*) from ifa2.highfreq_futures_minute_working',
        'highfreq_event_stream_working': 'select count(*) from ifa2.highfreq_event_stream_working',
        'highfreq_limit_event_stream_working': 'select count(*) from ifa2.highfreq_limit_event_stream_working',
        'highfreq_sector_breadth_working': 'select count(*) from ifa2.highfreq_sector_breadth_working',
        'highfreq_sector_heat_working': 'select count(*) from ifa2.highfreq_sector_heat_working',
        'highfreq_leader_candidate_working': 'select count(*) from ifa2.highfreq_leader_candidate_working',
        'highfreq_intraday_signal_state_working': 'select count(*) from ifa2.highfreq_intraday_signal_state_working',
    },
    'midfreq_source_counts': {
        'equity_daily_bar_history': 'select count(*) from ifa2.equity_daily_bar_history',
        'limit_up_detail_history': 'select count(*) from ifa2.limit_up_detail_history',
        'sector_performance_history': 'select count(*) from ifa2.sector_performance_history',
    },
    'archive_counts': {
        'stock_60min_history': 'select count(*) from ifa2.stock_60min_history',
        'stock_15min_history': 'select count(*) from ifa2.stock_15min_history',
        'stock_minute_history': 'select count(*) from ifa2.stock_minute_history',
        'futures_60min_history': 'select count(*) from ifa2.futures_60min_history',
        'futures_15min_history': 'select count(*) from ifa2.futures_15min_history',
        'futures_minute_history': 'select count(*) from ifa2.futures_minute_history',
        'commodity_60min_history': 'select count(*) from ifa2.commodity_60min_history',
        'commodity_15min_history': 'select count(*) from ifa2.commodity_15min_history',
        'commodity_minute_history': 'select count(*) from ifa2.commodity_minute_history',
        'precious_metal_60min_history': 'select count(*) from ifa2.precious_metal_60min_history',
        'precious_metal_15min_history': 'select count(*) from ifa2.precious_metal_15min_history',
        'precious_metal_minute_history': 'select count(*) from ifa2.precious_metal_minute_history',
        'daily_structured_output_archive': 'select count(*) from ifa2.daily_structured_output_archive',
    },
}

payload = {}
with engine.begin() as conn:
    for group, mapping in SQL.items():
        payload[group] = {k: conn.execute(text(v)).scalar_one() for k, v in mapping.items()}
    payload['recent_archive_jobs'] = [dict(r) for r in conn.execute(text(
        "select job_name, dataset_name, asset_type, status, records_processed, started_at, completed_at from ifa2.archive_runs order by started_at desc limit 25"
    )).mappings().all()]
    payload['archive_checkpoints'] = [dict(r) for r in conn.execute(text(
        "select dataset_name, asset_type, last_completed_date, status from ifa2.archive_checkpoints order by dataset_name, asset_type"
    )).mappings().all()]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
print(OUT)
