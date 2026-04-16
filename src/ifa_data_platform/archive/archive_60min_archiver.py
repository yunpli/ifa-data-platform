from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine

TABLE_BY_CATEGORY = {
    'stock': 'stock_60min_history',
    'futures': 'futures_60min_history',
    'commodity': 'commodity_60min_history',
    'precious_metal': 'precious_metal_60min_history',
}

SOURCE_BY_CATEGORY = {
    'stock': ('stock_15min_history', 'ts_code'),
    'futures': ('futures_15min_history', 'ts_code'),
    'commodity': ('commodity_15min_history', 'ts_code'),
    'precious_metal': ('precious_metal_15min_history', 'ts_code'),
}


class Archive60MinArchiver:
    def __init__(self) -> None:
        self.engine = make_engine()

    def run_archive(self, asset_type: str, symbols: Optional[list[str]] = None) -> int:
        target = TABLE_BY_CATEGORY[asset_type]
        source, code_col = SOURCE_BY_CATEGORY[asset_type]
        with self.engine.begin() as conn:
            rows = conn.execute(text(f'select {code_col}, trade_time, open, high, low, close, vol, amount from ifa2."{source}" order by trade_time desc limit 500')).mappings().all()
            if symbols:
                symbol_set = set(symbols)
                rows = [r for r in rows if r[code_col] in symbol_set]
            inserted = 0
            for r in rows:
                minute = r['trade_time'].minute
                if minute not in {0, 30}:
                    continue
                result = conn.execute(text(
                    f'insert into ifa2."{target}" (id, ts_code, trade_time, open, high, low, close, vol, amount) '
                    f'values (cast(:id as uuid), :ts_code, :trade_time, :open, :high, :low, :close, :vol, :amount) '
                    f'on conflict (ts_code, trade_time) do nothing'
                ), {
                    'id': str(uuid.uuid4()),
                    'ts_code': r[code_col],
                    'trade_time': r['trade_time'],
                    'open': r['open'],
                    'high': r['high'],
                    'low': r['low'],
                    'close': r['close'],
                    'vol': r['vol'],
                    'amount': r['amount'],
                })
                inserted += result.rowcount or 0
            return inserted
