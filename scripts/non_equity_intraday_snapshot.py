from __future__ import annotations

import json
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
OUT_DIR = Path('artifacts/non_equity_intraday')
OUT_DIR.mkdir(parents=True, exist_ok=True)
label = sys.argv[1]

def rows(conn, sql):
    return [dict(r) for r in conn.execute(text(sql)).mappings().all()]

payload = {'label': label}
with engine.begin() as conn:
    payload['tables'] = {
        'futures_15min_history': conn.execute(text('select count(*) from ifa2.futures_15min_history')).scalar_one(),
        'futures_minute_history': conn.execute(text('select count(*) from ifa2.futures_minute_history')).scalar_one(),
        'commodity_15min_history': conn.execute(text('select count(*) from ifa2.commodity_15min_history')).scalar_one(),
        'commodity_minute_history': conn.execute(text('select count(*) from ifa2.commodity_minute_history')).scalar_one(),
        'precious_metal_15min_history': conn.execute(text('select count(*) from ifa2.precious_metal_15min_history')).scalar_one(),
        'precious_metal_minute_history': conn.execute(text('select count(*) from ifa2.precious_metal_minute_history')).scalar_one(),
        'archive_runs': conn.execute(text('select count(*) from ifa2.archive_runs')).scalar_one(),
    }
    payload['recent_intraday_jobs'] = rows(conn, "select job_name, dataset_name, asset_type, status, records_processed, started_at, completed_at from ifa2.archive_runs where dataset_name in ('futures_15min_history','futures_minute_history','commodity_15min_history','commodity_minute_history','precious_metal_15min_history','precious_metal_minute_history') order by started_at desc limit 20")
    payload['checkpoints'] = rows(conn, "select dataset_name, asset_type, last_completed_date, status from ifa2.archive_checkpoints where dataset_name in ('futures_15min_history','futures_minute_history','commodity_15min_history','commodity_minute_history','precious_metal_15min_history','precious_metal_minute_history') order by dataset_name")
(OUT_DIR / f'{label}.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
print(OUT_DIR / f'{label}.json')
