"""Retention/recycle utilities for highfreq working tables."""

from __future__ import annotations

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


class RetentionManager:
    def __init__(self) -> None:
        self.engine = make_engine()

    def apply(self, keep_days: int = 30) -> dict:
        tables = [
            ('highfreq_stock_1m_working', 'trade_time'),
            ('highfreq_index_1m_working', 'trade_time'),
            ('highfreq_proxy_1m_working', 'trade_time'),
            ('highfreq_futures_minute_working', 'trade_time'),
            ('highfreq_event_stream_working', 'event_time'),
            ('highfreq_sector_breadth_working', 'trade_time'),
            ('highfreq_sector_heat_working', 'trade_time'),
            ('highfreq_leader_candidate_working', 'trade_time'),
            ('highfreq_limit_event_stream_working', 'trade_time'),
            ('highfreq_intraday_signal_state_working', 'trade_time'),
        ]
        deleted = {}
        with self.engine.begin() as conn:
            for table, time_col in tables:
                result = conn.execute(
                    text(
                        f"delete from ifa2.{table} where {time_col} < now() - (:keep_days || ' days')::interval"
                    ),
                    {'keep_days': keep_days},
                )
                deleted[table] = result.rowcount or 0
        return {'keep_days': keep_days, 'deleted_rows': deleted}
