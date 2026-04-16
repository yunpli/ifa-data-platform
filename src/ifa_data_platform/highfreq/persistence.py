"""Working-table persistence for highfreq milestone 2."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


class HighfreqRunStore:
    def __init__(self) -> None:
        self.engine = make_engine()

    def record(self, run_id: str, dataset_name: str, status: str, records_processed: int, watermark: Optional[str], error_message: Optional[str] = None) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.highfreq_runs (id, run_id, dataset_name, status, records_processed, watermark, error_message)
                    VALUES (:id, :run_id, :dataset_name, :status, :records_processed, :watermark, :error_message)
                    """
                ),
                {
                    'id': str(uuid.uuid4()),
                    'run_id': run_id,
                    'dataset_name': dataset_name,
                    'status': status,
                    'records_processed': records_processed,
                    'watermark': watermark,
                    'error_message': error_message,
                },
            )


class HighfreqStock1mWorking:
    def __init__(self) -> None:
        self.engine = make_engine()

    def bulk_replace(self, records: list[dict], version_id: str) -> int:
        if not records:
            return 0
        with self.engine.begin() as conn:
            for rec in records:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.highfreq_stock_1m_working (
                            id, version_id, ts_code, trade_time, open, high, low, close, vol, amount, vwap, amplitude
                        ) VALUES (
                            :id, :version_id, :ts_code, :trade_time, :open, :high, :low, :close, :vol, :amount, :vwap, :amplitude
                        )
                        ON CONFLICT (ts_code, trade_time) DO UPDATE SET
                            version_id = EXCLUDED.version_id,
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            vol = EXCLUDED.vol,
                            amount = EXCLUDED.amount,
                            vwap = EXCLUDED.vwap,
                            amplitude = EXCLUDED.amplitude
                        """
                    ),
                    {
                        'id': str(uuid.uuid4()),
                        'version_id': version_id,
                        'ts_code': rec['ts_code'],
                        'trade_time': rec['trade_time'],
                        'open': rec.get('open'),
                        'high': rec.get('high'),
                        'low': rec.get('low'),
                        'close': rec.get('close'),
                        'vol': rec.get('vol'),
                        'amount': rec.get('amount'),
                        'vwap': rec.get('vwap'),
                        'amplitude': rec.get('amplitude'),
                    },
                )
        return len(records)


class HighfreqAuctionWorking:
    def __init__(self, table_name: str) -> None:
        self.engine = make_engine()
        self.table_name = table_name

    def bulk_replace(self, records: list[dict], version_id: str) -> int:
        if not records:
            return 0
        with self.engine.begin() as conn:
            for rec in records:
                conn.execute(
                    text(
                        f"""
                        INSERT INTO ifa2.{self.table_name} (
                            id, version_id, ts_code, trade_date, open, high, low, close, vol, amount, vwap
                        ) VALUES (
                            :id, :version_id, :ts_code, :trade_date, :open, :high, :low, :close, :vol, :amount, :vwap
                        )
                        ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                            version_id = EXCLUDED.version_id,
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            vol = EXCLUDED.vol,
                            amount = EXCLUDED.amount,
                            vwap = EXCLUDED.vwap
                        """
                    ),
                    {
                        'id': str(uuid.uuid4()),
                        'version_id': version_id,
                        'ts_code': rec['ts_code'],
                        'trade_date': rec['trade_date'],
                        'open': rec.get('open'),
                        'high': rec.get('high'),
                        'low': rec.get('low'),
                        'close': rec.get('close'),
                        'vol': rec.get('vol'),
                        'amount': rec.get('amount'),
                        'vwap': rec.get('vwap'),
                    },
                )
        return len(records)


class HighfreqEventStreamWorking:
    def __init__(self) -> None:
        self.engine = make_engine()

    def bulk_insert(self, records: list[dict], version_id: str) -> int:
        if not records:
            return 0
        with self.engine.begin() as conn:
            for rec in records:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.highfreq_event_stream_working (
                            id, version_id, event_type, symbol, event_time, title, source, url, payload
                        ) VALUES (
                            :id, :version_id, :event_type, :symbol, :event_time, :title, :source, :url, :payload
                        )
                        """
                    ),
                    {
                        'id': str(uuid.uuid4()),
                        'version_id': version_id,
                        'event_type': rec['event_type'],
                        'symbol': rec.get('symbol'),
                        'event_time': rec['event_time'],
                        'title': rec.get('title'),
                        'source': rec.get('source', 'tushare'),
                        'url': rec.get('url'),
                        'payload': rec.get('payload'),
                    },
                )
        return len(records)
