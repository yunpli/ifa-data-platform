from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
engine = create_engine(DB_URL)
OUT = Path('artifacts/futures_source_truth_2026-04-16_1805.json')
ROOTS = ['IF', 'IH', 'IC', 'IM', 'TS', 'TF', 'T', 'TL']

QUERIES = {
    'tables_like_futures': "select table_name from information_schema.tables where table_schema='ifa2' and table_name ilike '%futures%' order by table_name",
    'futures_history_symbols': "select distinct ts_code from ifa2.futures_history order by ts_code limit 200",
    'futures_15min_symbols': "select distinct ts_code from ifa2.futures_15min_history order by ts_code limit 200",
    'futures_minute_symbols': "select distinct ts_code from ifa2.futures_minute_history order by ts_code limit 200",
    'futures_60min_symbols': "select distinct ts_code from ifa2.futures_60min_history order by ts_code limit 200",
    'archive_focus_items_futures': "select distinct symbol from ifa2.focus_list_items where asset_category='futures' order by symbol limit 200",
    'archive_runs_futures_datasets': "select distinct dataset_name from ifa2.archive_runs where asset_type='futures' order by dataset_name",
}

payload = {'roots': ROOTS, 'queries': {}, 'root_hits': {}}
with engine.begin() as conn:
    for name, sql in QUERIES.items():
        rows = conn.execute(text(sql)).fetchall()
        payload['queries'][name] = [r[0] for r in rows]

    for root in ROOTS:
        payload['root_hits'][root] = {}
        for name, values in payload['queries'].items():
            hits = [v for v in values if isinstance(v, str) and v.startswith(root)]
            payload['root_hits'][root][name] = hits

    payload['futures_history_sample'] = [dict(r) for r in conn.execute(text('select * from ifa2.futures_history order by trade_date desc limit 5')).mappings().all()]
    payload['futures_15min_sample'] = [dict(r) for r in conn.execute(text('select * from ifa2.futures_15min_history order by trade_time desc limit 5')).mappings().all()]
    payload['futures_minute_sample'] = [dict(r) for r in conn.execute(text('select * from ifa2.futures_minute_history order by trade_time desc limit 5')).mappings().all()]
    payload['futures_60min_sample'] = [dict(r) for r in conn.execute(text('select * from ifa2.futures_60min_history order by trade_time desc limit 5')).mappings().all()]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
print(OUT)
