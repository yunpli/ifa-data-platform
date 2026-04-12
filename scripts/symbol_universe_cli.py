#!/usr/bin/env python3
"""CLI for managing A/B/C symbol universe in ifa2.symbol_universe."""

from __future__ import annotations

import argparse
import random
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import text

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp&options=-csearch_path%3Difa2%2Cpublic'

A_NAMES = [
    '测绘股份','金禄电子','震裕科技','致尚科技','复旦微电','全新好','智微智能'
]

C_NAMES = [
    '震裕科技','航天软件','卓易信息','江苏北人','索辰科技','国创高新','友阿股份','浪潮信息','深桑达A','农尚环境','龙芯中科','软通动力','上海瀚讯','柘中股份','航天长峰','神开股份','飞马国际','富时中国A50指数','剑桥科技','胜宏科技','ST复华','天岳先进','集智股份','迈信林','新易盛','中际旭创','复旦微电','ST波导','喜悦智行','朗科科技','浪潮软件','张家港行','长江传媒','江苏国信','东芯股份','国轩高科','青云科技-U','摩尔线程-U','测绘股份','赛微电子','华凯易佰','云天励飞-U','江南新材','光华科技','中国船舶','菲菱科思','晨丰科技','上海机电','超讯通信','天孚通信',
    '全新好','智微智能','致尚科技','金禄电子'
]

SPECIAL_MAP = {
    '深桑达A': ('000032.SZ', '深桑达Ａ'),
    'ST波导': ('600130.SH', '*ST波导'),
    '富时中国A50指数': ('830009.XI', '富时中国A50'),
}


def engine():
    return sa.create_engine(DB_URL)


def resolve_name_map(conn):
    stock_rows = conn.execute(text('select ts_code, name from ifa2.stock_basic_current')).fetchall()
    index_rows = conn.execute(text('select ts_code, name from ifa2.index_basic_current')).fetchall()
    m = {r.name: (r.ts_code, r.name) for r in stock_rows}
    m.update({r.name: (r.ts_code, r.name) for r in index_rows})
    m.update(SPECIAL_MAP)
    return m


def generate_b(c_records):
    non_index = [r for r in c_records if '指数' not in r['name'] and not r['symbol'].endswith(('.XI', '.CSI', '.MI'))]
    a_names = set(A_NAMES)
    a_in_c = [r for r in non_index if r['name'] in a_names]
    pool = [r for r in non_index if r['name'] not in a_names]
    random.seed(20260411)
    target = 20
    extra = max(0, min(len(pool), target - len(a_in_c)))
    chosen = random.sample(pool, extra) if extra else []
    b = a_in_c + chosen
    uniq = []
    seen = set()
    for r in b:
        k = r['symbol']
        if k not in seen:
            uniq.append(r)
            seen.add(k)
    return uniq


def upsert(conn, symbol, name, universe_type):
    conn.execute(text("""
        INSERT INTO ifa2.symbol_universe (
            id, symbol, name, universe_type, source, is_active, created_at, updated_at
        ) VALUES (
            :id, :symbol, :name, :universe_type, 'manual', true, now(), now()
        )
        ON CONFLICT (symbol, universe_type) DO UPDATE SET
            name = EXCLUDED.name,
            source = 'manual',
            is_active = true,
            updated_at = now()
    """), {
        'id': str(uuid.uuid4()),
        'symbol': symbol,
        'name': name,
        'universe_type': universe_type,
    })


def seed():
    with engine().begin() as conn:
        name_map = resolve_name_map(conn)
        a_records = []
        c_records = []
        for name in A_NAMES:
            if name in name_map:
                symbol, resolved_name = name_map[name]
                a_records.append({'symbol': symbol, 'name': name, 'resolved_name': resolved_name})
        for name in C_NAMES:
            if name in name_map:
                symbol, resolved_name = name_map[name]
                c_records.append({'symbol': symbol, 'name': name, 'resolved_name': resolved_name})
        b_records = generate_b(c_records)

        for universe_type in ['A', 'B', 'C']:
            conn.execute(text('update ifa2.symbol_universe set is_active=false, updated_at=now() where universe_type=:u'), {'u': universe_type})

        for r in a_records:
            upsert(conn, r['symbol'], r['name'], 'A')
        for r in b_records:
            upsert(conn, r['symbol'], r['name'], 'B')
        for r in c_records:
            upsert(conn, r['symbol'], r['name'], 'C')

        print(f'A_count={len({r["symbol"] for r in a_records})}')
        print(f'B_count={len({r["symbol"] for r in b_records})}')
        print(f'C_count={len({r["symbol"] for r in c_records})}')
        print('B_method=random.sample from non-index C pool with fixed seed 20260411, then forced include A∩C')
        missing_from_c = sorted(set(A_NAMES) - set(C_NAMES))
        if missing_from_c:
            print('INPUT_BLOCKER_A_not_subset_C=' + ','.join(missing_from_c))


def list_universe(universe_type):
    with engine().connect() as conn:
        rows = conn.execute(text("""
            select symbol, name, universe_type, source, is_active
            from ifa2.symbol_universe
            where universe_type=:u and is_active=true
            order by name
        """), {'u': universe_type}).fetchall()
        for r in rows:
            print(f'{r.universe_type}\t{r.symbol}\t{r.name}\t{r.source}\tactive={r.is_active}')


def add_symbol(symbol, name, universe_type):
    with engine().begin() as conn:
        upsert(conn, symbol, name, universe_type)
    print('ok')


def remove_symbol(symbol, universe_type):
    with engine().begin() as conn:
        conn.execute(text("""
            update ifa2.symbol_universe
            set is_active=false, updated_at=now()
            where symbol=:symbol and universe_type=:u
        """), {'symbol': symbol, 'u': universe_type})
    print('ok')


def move_symbol(symbol, from_type, to_type):
    with engine().begin() as conn:
        row = conn.execute(text("""
            select name from ifa2.symbol_universe
            where symbol=:symbol and universe_type=:u
            order by updated_at desc limit 1
        """), {'symbol': symbol, 'u': from_type}).fetchone()
        if not row:
            raise SystemExit('symbol not found in source universe')
        conn.execute(text("""
            update ifa2.symbol_universe
            set is_active=false, updated_at=now()
            where symbol=:symbol and universe_type=:u
        """), {'symbol': symbol, 'u': from_type})
        upsert(conn, symbol, row.name, to_type)
    print('ok')


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('seed')
    p_list = sub.add_parser('list')
    p_list.add_argument('--type', required=True, choices=['A','B','C'])

    p_add = sub.add_parser('add')
    p_add.add_argument('--symbol', required=True)
    p_add.add_argument('--name', required=True)
    p_add.add_argument('--type', required=True, choices=['A','B','C'])

    p_rm = sub.add_parser('remove')
    p_rm.add_argument('--symbol', required=True)
    p_rm.add_argument('--type', required=True, choices=['A','B','C'])

    p_mv = sub.add_parser('move')
    p_mv.add_argument('--symbol', required=True)
    p_mv.add_argument('--from-type', required=True, choices=['A','B','C'])
    p_mv.add_argument('--to-type', required=True, choices=['A','B','C'])

    args = p.parse_args()
    if args.cmd == 'seed':
        seed()
    elif args.cmd == 'list':
        list_universe(args.type)
    elif args.cmd == 'add':
        add_symbol(args.symbol, args.name, args.type)
    elif args.cmd == 'remove':
        remove_symbol(args.symbol, args.type)
    elif args.cmd == 'move':
        move_symbol(args.symbol, args.from_type, args.to_type)


if __name__ == '__main__':
    main()
