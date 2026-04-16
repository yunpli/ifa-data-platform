from __future__ import annotations

import json
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
engine = create_engine(DB_URL)
OUT_DIR = Path('artifacts/archive_real_run')
OUT_DIR.mkdir(parents=True, exist_ok=True)
TABLES = [
    'archive_runs', 'archive_checkpoints', 'archive_target_catchup', 'archive_summary_daily',
    'stock_60min_history', 'futures_60min_history', 'commodity_60min_history', 'precious_metal_60min_history',
    'stock_15min_history', 'stock_minute_history',
    'futures_15min_history', 'futures_minute_history',
    'commodity_15min_history', 'commodity_minute_history',
    'precious_metal_15min_history', 'precious_metal_minute_history',
    'dragon_tiger_list_history', 'limit_up_detail_history', 'limit_up_down_status_history', 'daily_structured_output_archive',
    'unified_runtime_runs', 'job_runs'
]

label = sys.argv[1]
payload = {'label': label, 'tables': {}, 'archive_jobs': []}
with engine.begin() as conn:
    for t in TABLES:
        payload['tables'][t] = conn.execute(text(f'select count(*) from ifa2."{t}"')).scalar_one()
    rows = conn.execute(text(
        "select job_name, dataset_name, asset_type, window_name, status, records_processed, started_at, completed_at "
        "from ifa2.archive_runs order by started_at desc limit 20"
    )).mappings().all()
    payload['archive_jobs'] = [dict(r) for r in rows]
(OUT_DIR / f'{label}.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
print(OUT_DIR / f'{label}.json')
