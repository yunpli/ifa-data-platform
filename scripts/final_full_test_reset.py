from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
OUT = Path('artifacts/final_full_test_reset_2026-04-16_2336.json')

TABLES = [
    'unified_runtime_runs', 'job_runs', 'lowfreq_runs', 'highfreq_runs', 'midfreq_execution_summary', 'highfreq_execution_summary', 'target_manifest_snapshots', 'lowfreq_raw_fetch',
    'highfreq_close_auction_working', 'highfreq_event_stream_working', 'highfreq_futures_minute_working', 'highfreq_index_1m_working', 'highfreq_intraday_signal_state_working', 'highfreq_leader_candidate_working', 'highfreq_limit_event_stream_working', 'highfreq_open_auction_working', 'highfreq_proxy_1m_working', 'highfreq_sector_breadth_working', 'highfreq_sector_heat_working', 'highfreq_stock_1m_working', 'highfreq_active_scope', 'highfreq_dynamic_candidate'
]
RECENT = [
    ('archive_runs', "delete from ifa2.archive_runs where started_at >= now() - interval '5 day'"),
    ('archive_summary_daily', "delete from ifa2.archive_summary_daily where created_at >= now() - interval '5 day'"),
    ('daily_structured_output_archive', "delete from ifa2.daily_structured_output_archive where created_at >= now() - interval '5 day'"),
]
payload = {'deleted': {}, 'recent_archive_deleted': {}}
with engine.begin() as conn:
    for table in TABLES:
        before = conn.execute(text(f'select count(*) from ifa2."{table}"')).scalar_one()
        conn.execute(text(f'delete from ifa2."{table}"'))
        after = conn.execute(text(f'select count(*) from ifa2."{table}"')).scalar_one()
        payload['deleted'][table] = {'before': before, 'after': after}
    for table, sql in RECENT:
        before = conn.execute(text(f'select count(*) from ifa2."{table}"')).scalar_one()
        conn.execute(text(sql))
        after = conn.execute(text(f'select count(*) from ifa2."{table}"')).scalar_one()
        payload['recent_archive_deleted'][table] = {'before': before, 'after': after}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
print(OUT)
