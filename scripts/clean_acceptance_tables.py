from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
engine = create_engine(DB_URL)
OUT = Path('artifacts/acceptance_cleanup_2026-04-16_0832.json')

DELETE_ORDER = [
    'archive_runs',
    'archive_summary_daily',
    'unified_runtime_runs',
    'job_runs',
    'lowfreq_runs',
    'highfreq_runs',
    'midfreq_execution_summary',
    'highfreq_execution_summary',
    'lowfreq_raw_fetch',
    'highfreq_close_auction_working',
    'highfreq_event_stream_working',
    'highfreq_futures_minute_working',
    'highfreq_index_1m_working',
    'highfreq_intraday_signal_state_working',
    'highfreq_leader_candidate_working',
    'highfreq_limit_event_stream_working',
    'highfreq_open_auction_working',
    'highfreq_proxy_1m_working',
    'highfreq_sector_breadth_working',
    'highfreq_sector_heat_working',
    'highfreq_stock_1m_working',
    'highfreq_active_scope',
    'highfreq_dynamic_candidate',
    'target_manifest_snapshots',
]

KEEP_TABLES = [
    'focus_lists', 'focus_list_items', 'focus_list_rules',
    'symbol_universe', 'trade_cal_current', 'trade_cal_history',
    'runtime_worker_schedules', 'runtime_worker_state',
    'archive_checkpoints', 'archive_target_catchup', 'stock_history_checkpoint',
]


def count(conn, table):
    return conn.execute(text(f'select count(*) from ifa2."{table}"')).scalar_one()

payload = {'cleaned': {}, 'kept': KEEP_TABLES}
with engine.begin() as conn:
    for table in DELETE_ORDER:
        before = count(conn, table)
        conn.execute(text(f'delete from ifa2."{table}"'))
        after = count(conn, table)
        payload['cleaned'][table] = {'before': before, 'after': after}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
print(OUT)
