from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
engine = create_engine(DB_URL)
OUT = Path('artifacts/archive_and_commodity_check_2026-04-16_0924.json')

ARCHIVE_NAMES = ['default_archive_targets_15min', 'default_archive_targets_minute']

QUERY_LISTS = """
select fl.name, fl.list_type, fl.asset_type, fl.frequency_type, count(fli.id) as item_count
from ifa2.focus_lists fl
left join ifa2.focus_list_items fli on fl.id = fli.list_id
where fl.name = any(:names)
group by fl.name, fl.list_type, fl.asset_type, fl.frequency_type
order by fl.name
"""

QUERY_ARCHIVE_BREAKDOWN = """
select fl.name, fli.asset_category, count(*) as item_count
from ifa2.focus_lists fl
join ifa2.focus_list_items fli on fl.id = fli.list_id
where fl.name = any(:names)
group by fl.name, fli.asset_category
order by fl.name, fli.asset_category
"""

QUERY_PM_COMMODITY = """
select fl.name, fl.list_type, fl.frequency_type, count(fli.id) as item_count
from ifa2.focus_lists fl
left join ifa2.focus_list_items fli on fl.id = fli.list_id
where fl.name ilike any(:patterns)
group by fl.name, fl.list_type, fl.frequency_type
order by fl.name
"""

COUNT_TABLES = [
    'stock_15min_history', 'stock_minute_history',
    'futures_15min_history', 'futures_minute_history',
    'commodity_15min_history', 'commodity_minute_history',
    'precious_metal_15min_history', 'precious_metal_minute_history',
]

with engine.begin() as conn:
    payload = {}
    payload['archive_lists'] = [dict(r) for r in conn.execute(text(QUERY_LISTS), {'names': ARCHIVE_NAMES}).mappings().all()]
    payload['archive_breakdown'] = [dict(r) for r in conn.execute(text(QUERY_ARCHIVE_BREAKDOWN), {'names': ARCHIVE_NAMES}).mappings().all()]
    payload['archive_checkpoints'] = [dict(r) for r in conn.execute(text(
        "select dataset_name, asset_type, min(last_completed_date) as min_date, max(last_completed_date) as max_date, count(*) as checkpoint_rows "
        "from ifa2.archive_checkpoints group by dataset_name, asset_type order by dataset_name, asset_type"
    )).mappings().all()]
    payload['archive_catchup'] = [dict(r) for r in conn.execute(text(
        "select asset_category, granularity, status, count(*) as rows from ifa2.archive_target_catchup group by asset_category, granularity, status order by asset_category, granularity, status"
    )).mappings().all()]
    payload['history_counts'] = []
    for table_name in COUNT_TABLES:
        rows = conn.execute(text(f'select count(*) from ifa2."{table_name}"')).scalar_one()
        payload['history_counts'].append({'table_name': table_name, 'rows': rows})
    payload['pm_commodity_lists'] = [dict(r) for r in conn.execute(text(QUERY_PM_COMMODITY), {'patterns': ['%commodity%', '%precious%', '%metal%']}).mappings().all()]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
print(OUT)
