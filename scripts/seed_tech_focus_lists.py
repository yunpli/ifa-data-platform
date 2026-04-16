from __future__ import annotations

import json
from pathlib import Path
from sqlalchemy import create_engine, text
from uuid import uuid4

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
engine = create_engine(DB_URL)
OUT = Path('artifacts/tech_focus_seed_2026-04-16_0922.json')

KEY_NAMES = [
    '寒武纪', '海光信息', '中际旭创', '新易盛', '天孚通信', '润泽科技', '中科曙光', '浪潮信息', '工业富联', '沪电股份',
    '生益科技', '兆易创新', '中微公司', '北方华创', '拓荆科技', '澜起科技', '芯原股份', '佰维存储', '三花智控', '奥比中光-UW'
]
FOCUS_NAMES = KEY_NAMES + [
    '源杰科技', '东山精密', '胜宏科技', '协创数据', '宏景科技', '光环新网', '数据港', '网宿科技', '芯源微', '安集科技',
    '江丰电子', '雅克科技', '鼎龙股份', '伟测科技', '联动科技', '金海通', '怡合达', '埃斯顿', '汇川技术', '绿的谐波',
    '中大力德', '柯力传感', '鸣志电器', '机器人', '博众精工', '思源电气', '海兴电力', '三星医疗', '中国动力', '东方电气',
    '应流股份', '万泽股份', '固德威', '阳光电源', '中科江南', '深信服', '用友网络', '金山办公', '中科星图', '中国软件',
    '拓尔思', '科大讯飞', '虹软科技', '万兴科技', '德明利', '芯朋微', '圣邦股份'
]

LIST_SPECS = [
    ('default_tech_key_focus', 'tech_key_focus', 20, KEY_NAMES),
    ('default_tech_focus', 'tech_focus', 80, FOCUS_NAMES),
]

def resolve_name(conn, name: str):
    rows = conn.execute(text(
        "select symbol, name from ifa2.stock_basic_current where name = :name order by symbol"
    ), {'name': name}).mappings().all()
    return [dict(r) for r in rows]

with engine.begin() as conn:
    payload = {'lists': [], 'unresolved': []}
    for list_name, list_type, target_size, names in LIST_SPECS:
        existing = conn.execute(text(
            "select id from ifa2.focus_lists where name=:name"
        ), {'name': list_name}).scalar_one_or_none()
        if existing:
            list_id = str(existing)
            conn.execute(text("delete from ifa2.focus_list_rules where list_id = cast(:id as uuid)"), {'id': list_id})
            conn.execute(text("delete from ifa2.focus_list_items where list_id = cast(:id as uuid)"), {'id': list_id})
            conn.execute(text(
                "update ifa2.focus_lists set list_type=:lt, asset_type='multi_asset', frequency_type='none', description=:d, is_active=true, updated_at=now() where id=cast(:id as uuid)"
            ), {'id': list_id, 'lt': list_type, 'd': f'{list_name} seeded 2026-04-16'})
        else:
            list_id = str(uuid4())
            conn.execute(text(
                "insert into ifa2.focus_lists (id, owner_type, owner_id, list_type, name, asset_type, frequency_type, description, is_active, created_at, updated_at) "
                "values (cast(:id as uuid), 'default', 'default', :lt, :name, 'multi_asset', 'none', :d, true, now(), now())"
            ), {'id': list_id, 'lt': list_type, 'name': list_name, 'd': f'{list_name} seeded 2026-04-16'})
        conn.execute(text(
            "insert into ifa2.focus_list_rules (id, list_id, rule_key, rule_value, created_at, updated_at) values "
            "(cast(:id1 as uuid), cast(:list_id as uuid), 'owner_scope', 'default', now(), now()), "
            "(cast(:id2 as uuid), cast(:list_id as uuid), 'target_size', :target_size, now(), now())"
        ), {'id1': str(uuid4()), 'id2': str(uuid4()), 'list_id': list_id, 'target_size': str(target_size)})

        inserted = []
        unresolved = []
        seen = set()
        priority = 1
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            matches = resolve_name(conn, name)
            if len(matches) != 1:
                unresolved.append({'name': name, 'matches': matches})
                continue
            row = matches[0]
            conn.execute(text(
                "insert into ifa2.focus_list_items (id, list_id, symbol, name, asset_category, priority, source, notes, is_active, created_at, updated_at) "
                "values (cast(:id as uuid), cast(:list_id as uuid), :symbol, :name, 'stock', :priority, 'seed_tech_2026-04-16', '', true, now(), now())"
            ), {'id': str(uuid4()), 'list_id': list_id, 'symbol': row['symbol'], 'name': row['name'], 'priority': priority})
            inserted.append({'name': row['name'], 'symbol': row['symbol'], 'priority': priority})
            priority += 1
        payload['lists'].append({'list_name': list_name, 'list_type': list_type, 'inserted_count': len(inserted), 'inserted': inserted, 'unresolved_count': len(unresolved), 'unresolved': unresolved})
        payload['unresolved'].extend([{'list_name': list_name, **u} for u in unresolved])
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
print(OUT)
