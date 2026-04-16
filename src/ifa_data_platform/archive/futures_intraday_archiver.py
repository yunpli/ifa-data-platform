"""Futures-family intraday archiver for 15min/minute archive closure."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.archive.archive_checkpoint import ArchiveCheckpointStore
from ifa_data_platform.archive.commodity_archiver import CommodityArchiver
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.tushare.client import get_tushare_client

logger = logging.getLogger(__name__)


class FuturesIntradayArchiver:
    def __init__(self) -> None:
        self.engine = make_engine()
        self.checkpoint_store = ArchiveCheckpointStore()
        self.contract_archiver = CommodityArchiver()
        self._tushare_client: Optional[object] = None

    @property
    def tushare_client(self):
        if self._tushare_client is None:
            self._tushare_client = get_tushare_client()
        return self._tushare_client

    def _target_contracts(self, category_filter: set[str], symbols: Optional[list[str]] = None) -> list[dict]:
        contracts = [
            c
            for c in self.contract_archiver.get_active_contracts()
            if c.get("category") in category_filter
        ]
        if not symbols:
            return contracts
        symbol_set = set(symbols)
        return [c for c in contracts if c.get('symbol') in symbol_set or c.get('ts_code') in symbol_set]

    def _default_window(self, end_time: Optional[datetime]) -> tuple[datetime, datetime]:
        if end_time is None:
            yesterday = date.today() - timedelta(days=1)
            end_time = datetime.combine(yesterday, time(15, 0, 0))
        start_time = datetime.combine(end_time.date(), time(9, 0, 0))
        return start_time, end_time

    def fetch_intraday(
        self, ts_code: str, start_time: datetime, end_time: datetime, freq: str
    ) -> list[dict]:
        rows = self.tushare_client.query(
            "ft_mins",
            {
                "ts_code": ts_code,
                "freq": freq,
                "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            timeout_sec=120,
            max_retries=3,
        )
        parsed = []
        for row in rows:
            tt = row.get("trade_time")
            if not tt:
                continue
            try:
                trade_time = datetime.strptime(tt, "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                continue
            parsed.append(
                {
                    "ts_code": row.get("ts_code", ts_code),
                    "trade_time": trade_time,
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                    "vol": row.get("vol"),
                    "amount": row.get("amount"),
                    "oi": row.get("oi"),
                    "freq": freq,
                    "source": "tushare",
                }
            )
        parsed.sort(key=lambda r: r["trade_time"])
        return parsed

    def persist_records(self, table_name: str, records: list[dict]) -> int:
        if not records:
            return 0
        inserted = 0
        with self.engine.begin() as conn:
            for rec in records:
                result = conn.execute(
                    text(
                        f"""
                        INSERT INTO ifa2.{table_name} (
                            id, ts_code, trade_time, open, high, low, close,
                            vol, amount, oi, freq, source, created_at
                        ) VALUES (
                            gen_random_uuid(), :ts_code, :trade_time, :open, :high, :low, :close,
                            :vol, :amount, :oi, :freq, :source, NOW()
                        )
                        ON CONFLICT (ts_code, trade_time) DO NOTHING
                        """
                    ),
                    rec,
                )
                inserted += result.rowcount or 0
        return inserted

    def run_archive(
        self,
        *,
        dataset_name: str,
        asset_type: str,
        category_filter: set[str],
        freq: str,
        end_time: Optional[datetime] = None,
        max_contracts: int = 8,
        symbols: Optional[list[str]] = None,
    ) -> int:
        checkpoint = self.checkpoint_store.get_checkpoint(dataset_name, asset_type)
        default_start, resolved_end = self._default_window(end_time)
        if checkpoint and checkpoint.get("last_completed_at"):
            resolved_start = checkpoint["last_completed_at"] + timedelta(
                minutes=1 if freq == "1min" else 15
            )
        else:
            resolved_start = default_start

        # Intraday archive is forward-only by business policy.
        resolved_start = max(resolved_start, default_start)

        contracts = self._target_contracts(category_filter, symbols=symbols)[:max_contracts]
        total_inserted = 0
        batch_no = 0
        watermark = None
        last_symbol = None
        for contract in contracts:
            batch_no += 1
            ts_code = contract["ts_code"]
            last_symbol = ts_code
            records = self.fetch_intraday(ts_code, resolved_start, resolved_end, freq)
            inserted = self.persist_records(dataset_name, records)
            total_inserted += inserted
            if records:
                watermark = records[-1]["trade_time"]
                self.checkpoint_store.upsert_checkpoint(
                    dataset_name=dataset_name,
                    asset_type=asset_type,
                    last_completed_date=watermark.date(),
                    last_completed_at=watermark,
                    shard_id=ts_code,
                    batch_no=batch_no,
                    status="in_progress",
                )
        if watermark is not None:
            self.checkpoint_store.upsert_checkpoint(
                dataset_name=dataset_name,
                asset_type=asset_type,
                last_completed_date=watermark.date(),
                last_completed_at=watermark,
                shard_id=last_symbol,
                batch_no=batch_no,
                status="completed",
            )
        return total_inserted
