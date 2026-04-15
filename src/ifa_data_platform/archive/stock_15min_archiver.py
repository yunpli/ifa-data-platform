"""Stock 15min archiver for production-grade intraday archive ingestion."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.archive.archive_checkpoint import ArchiveCheckpointStore
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.tushare.client import get_tushare_client

logger = logging.getLogger(__name__)


class Stock15MinArchiver:
    """Archiver for stock 15min historical bars.

    Uses Tushare `stk_mins` as the source of truth and persists bars into
    `ifa2.stock_15min_history` with idempotent upserts. Progress is stored in
    `ifa2.archive_checkpoints` using both a date watermark and an intraday
    datetime watermark (`last_completed_at`) for stable resume semantics.
    """

    def __init__(self) -> None:
        self.engine = make_engine()
        self.checkpoint_store = ArchiveCheckpointStore()
        self._tushare_client: Optional[object] = None

    @property
    def tushare_client(self):
        if self._tushare_client is None:
            self._tushare_client = get_tushare_client()
        return self._tushare_client

    def fetch_stock_universe(self, limit: int = 10) -> list[str]:
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(
                    text(
                        """
                        SELECT symbol
                        FROM ifa2.symbol_universe
                        WHERE universe_type = 'C' AND is_active = true
                        ORDER BY symbol
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()
                return [r.symbol for r in rows]
        except Exception as e:
            logger.warning(f"Failed to fetch stock universe from DB: {e}")
            return ["000001.SZ"]

    def get_checkpoint(self, dataset_name: str) -> Optional[dict]:
        return self.checkpoint_store.get_checkpoint(dataset_name, "stock")

    def fetch_stock_15min(
        self,
        ts_code: str,
        start_time: datetime,
        end_time: datetime,
        freq: str = "15min",
    ) -> list[dict]:
        rows = self.tushare_client.query(
            "stk_mins",
            {
                "ts_code": ts_code,
                "freq": freq,
                "start_date": start_time.strftime("%Y%m%d %H:%M:%S"),
                "end_date": end_time.strftime("%Y%m%d %H:%M:%S"),
            },
            timeout_sec=120,
            max_retries=3,
        )

        parsed: list[dict] = []
        for row in rows:
            trade_time_str = row.get("trade_time")
            if not trade_time_str:
                continue
            try:
                trade_time = datetime.strptime(trade_time_str, "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                continue
            parsed.append(
                {
                    "ts_code": ts_code,
                    "trade_time": trade_time,
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                    "vol": row.get("vol"),
                    "amount": row.get("amount"),
                    "freq": freq,
                    "source": "tushare",
                }
            )

        parsed.sort(key=lambda r: r["trade_time"])
        return parsed

    def persist_records(self, records: list[dict]) -> int:
        if not records:
            return 0

        inserted = 0
        with self.engine.begin() as conn:
            for rec in records:
                result = conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.stock_15min_history (
                            id, ts_code, trade_time, open, high, low, close,
                            vol, amount, freq, source, created_at
                        ) VALUES (
                            gen_random_uuid(), :ts_code, :trade_time, :open, :high, :low,
                            :close, :vol, :amount, :freq, :source, NOW()
                        )
                        ON CONFLICT (ts_code, trade_time) DO NOTHING
                        """
                    ),
                    rec,
                )
                inserted += result.rowcount or 0
        return inserted

    def _default_window(self, end_time: Optional[datetime]) -> tuple[datetime, datetime]:
        if end_time is None:
            yesterday = date.today() - timedelta(days=1)
            end_time = datetime.combine(yesterday, time(15, 0, 0))
        start_time = datetime.combine(end_time.date(), time(9, 30, 0))
        return start_time, end_time

    def run_archive(
        self,
        dataset_name: str = "stock_15min_history",
        end_time: Optional[datetime] = None,
        limit_stocks: int = 5,
    ) -> int:
        checkpoint = self.get_checkpoint(dataset_name)
        default_start, resolved_end = self._default_window(end_time)

        if checkpoint and checkpoint.get("last_completed_at"):
            resolved_start = checkpoint["last_completed_at"] + timedelta(minutes=15)
        else:
            resolved_start = default_start

        stocks = self.fetch_stock_universe(limit=limit_stocks)
        total_inserted = 0
        batch_no = 0
        watermark: Optional[datetime] = None
        last_symbol: Optional[str] = None

        for ts_code in stocks:
            batch_no += 1
            last_symbol = ts_code
            try:
                records = self.fetch_stock_15min(ts_code, resolved_start, resolved_end)
                inserted = self.persist_records(records)
                total_inserted += inserted
                if records:
                    watermark = records[-1]["trade_time"]
                    self.checkpoint_store.upsert_checkpoint(
                        dataset_name=dataset_name,
                        asset_type="stock",
                        last_completed_date=watermark.date(),
                        last_completed_at=watermark,
                        shard_id=ts_code,
                        batch_no=batch_no,
                        status="in_progress",
                    )
                    logger.info(
                        "Archived %s 15min rows for %s (%s -> %s)",
                        inserted,
                        ts_code,
                        resolved_start,
                        resolved_end,
                    )
            except Exception as e:
                logger.warning(f"Failed to archive stock 15min for {ts_code}: {e}")
                continue

        if watermark is not None:
            self.checkpoint_store.upsert_checkpoint(
                dataset_name=dataset_name,
                asset_type="stock",
                last_completed_date=watermark.date(),
                last_completed_at=watermark,
                shard_id=last_symbol,
                batch_no=batch_no,
                status="completed",
            )
        elif checkpoint is None:
            self.checkpoint_store.upsert_checkpoint(
                dataset_name=dataset_name,
                asset_type="stock",
                last_completed_date=resolved_start.date(),
                last_completed_at=None,
                shard_id=last_symbol,
                batch_no=batch_no,
                status="pending",
            )

        return total_inserted
