"""Stock daily archiver for D2 Stock Historical Archive Layer."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.tushare.client import get_tushare_client

logger = logging.getLogger(__name__)


class StockDailyArchiver:
    """Archiver for stock daily historical data.

    Fetches daily OHLCV data from Tushare and persists to stock_daily_history.
    Supports checkpoint-based backfill and resume.
    """

    def __init__(self) -> None:
        self.engine = make_engine()
        self._tushare_client: Optional[object] = None

    @property
    def tushare_client(self):
        """Lazy-initialize Tushare client."""
        if self._tushare_client is None:
            self._tushare_client = get_tushare_client()
        return self._tushare_client

    def fetch_stock_universe(self, limit: int = 30) -> list[tuple[str, str]]:
        """Fetch active stock universe from symbol_universe or stock_basic.

        Returns list of (ts_code, symbol) tuples.
        Default: top 30 active stocks from A-share universe.
        """
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
                return [(r.symbol, r.symbol) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to fetch universe from DB: {e}")
            return self._fetch_from_stock_basic(limit)

    def _fetch_from_stock_basic(self, limit: int = 30) -> list[tuple[str, str]]:
        """Fallback: fetch from stock_basic."""
        records = self.tushare_client.query(
            "stock_basic",
            {"list_status": "L", "market": "SSE"},
        )
        result = []
        for rec in records[:limit]:
            ts_code = rec.get("ts_code", "")
            symbol = rec.get("symbol", "")
            if ts_code:
                result.append((ts_code, symbol))
        return result

    def fetch_stock_daily(
        self,
        ts_code: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch daily data for a single stock between dates."""
        records = self.tushare_client.query(
            "daily",
            {
                "ts_code": ts_code,
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d"),
            },
            timeout_sec=120,
            max_retries=3,
        )

        parsed = []
        for rec in records:
            trade_date_str = rec.get("trade_date", "")
            try:
                trade_date = datetime.strptime(trade_date_str, "%Y%m%d").date()
            except (ValueError, TypeError):
                continue

            parsed.append(
                {
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "open": rec.get("open"),
                    "high": rec.get("high"),
                    "low": rec.get("low"),
                    "close": rec.get("close"),
                    "pre_close": rec.get("pre_close"),
                    "change": rec.get("change"),
                    "pct_chg": rec.get("pct_chg"),
                    "vol": rec.get("vol"),
                    "amount": rec.get("amount"),
                    "adjusted": False,
                    "source": "tushare",
                }
            )

        return parsed

    def persist_daily_records(self, records: list[dict]) -> int:
        """Persist stock daily records to the archive table.

        Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
        """
        if not records:
            return 0

        with self.engine.begin() as conn:
            for rec in records:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.stock_daily_history (
                            id, ts_code, trade_date, open, high, low, close,
                            pre_close, change, pct_chg, vol, amount, adjusted, source
                        ) VALUES (
                            gen_random_uuid(), :ts_code, :trade_date, :open, :high,
                            :low, :close, :pre_close, :change, :pct_chg, :vol,
                            :amount, :adjusted, :source
                        )
                        ON CONFLICT (ts_code, trade_date) DO NOTHING
                        """
                    ),
                    {
                        "ts_code": rec["ts_code"],
                        "trade_date": rec["trade_date"],
                        "open": rec.get("open"),
                        "high": rec.get("high"),
                        "low": rec.get("low"),
                        "close": rec.get("close"),
                        "pre_close": rec.get("pre_close"),
                        "change": rec.get("change"),
                        "pct_chg": rec.get("pct_chg"),
                        "vol": rec.get("vol"),
                        "amount": rec.get("amount"),
                        "adjusted": False,
                        "source": "tushare",
                    },
                )

        return len(records)

    def get_last_recorded_date(self, ts_code: str) -> Optional[date]:
        """Get the last recorded trade date for a stock."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT MAX(trade_date) as last_date
                    FROM ifa2.stock_daily_history
                    WHERE ts_code = :ts_code
                    """
                ),
                {"ts_code": ts_code},
            ).fetchone()
            if result and result.last_date:
                return result.last_date
        return None

    def get_checkpoint(self, dataset_name: str) -> Optional[dict]:
        """Get checkpoint from stock_history_checkpoint table."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT dataset_name, last_completed_date, last_ts_code, batch_no, status
                    FROM ifa2.stock_history_checkpoint
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()
            if result:
                return {
                    "dataset_name": result.dataset_name,
                    "last_completed_date": result.last_completed_date,
                    "last_ts_code": result.last_ts_code,
                    "batch_no": result.batch_no,
                    "status": result.status,
                }
        return None

    def sync_to_archive_checkpoints(
        self,
        dataset_name: str,
        asset_type: str,
        last_completed_date: Optional[date] = None,
        batch_no: int = 0,
        status: str = "in_progress",
    ) -> None:
        """Sync checkpoint to archive_checkpoints for unified tracking."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_checkpoints (
                        id, dataset_name, asset_type, last_completed_date, batch_no, status, updated_at, created_at
                    )
                    SELECT gen_random_uuid(), :dataset_name, :asset_type, :last_completed_date,
                           :batch_no, :status, NOW(), NOW()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM ifa2.archive_checkpoints
                        WHERE dataset_name = :dataset_name AND asset_type = :asset_type
                    )
                    """
                ),
                {
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "last_completed_date": last_completed_date,
                    "batch_no": batch_no,
                    "status": status,
                },
            )
            conn.execute(
                text(
                    """
                    UPDATE ifa2.archive_checkpoints
                    SET last_completed_date = :last_completed_date,
                        batch_no = :batch_no,
                        status = :status,
                        updated_at = NOW()
                    WHERE dataset_name = :dataset_name AND asset_type = :asset_type
                    """
                ),
                {
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "last_completed_date": last_completed_date,
                    "batch_no": batch_no,
                    "status": status,
                },
            )

    def upsert_checkpoint(
        self,
        dataset_name: str,
        last_completed_date: Optional[date] = None,
        last_ts_code: Optional[str] = None,
        batch_no: int = 0,
        status: str = "in_progress",
    ) -> None:
        """Upsert checkpoint to both stock_history_checkpoint and archive_checkpoints."""
        asset_type = "stock"
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.stock_history_checkpoint (
                        id, dataset_name, last_completed_date, last_ts_code, batch_no, status
                    ) VALUES (
                        gen_random_uuid(), :dataset_name, :last_completed_date,
                        :last_ts_code, :batch_no, :status
                    )
                    ON CONFLICT (dataset_name) DO UPDATE SET
                        last_completed_date = EXCLUDED.last_completed_date,
                        last_ts_code = EXCLUDED.last_ts_code,
                        batch_no = EXCLUDED.batch_no,
                        status = EXCLUDED.status,
                        updated_at = now()
                    """
                ),
                {
                    "dataset_name": dataset_name,
                    "last_completed_date": last_completed_date,
                    "last_ts_code": last_ts_code,
                    "batch_no": batch_no,
                    "status": status,
                },
            )
        self.sync_to_archive_checkpoints(
            dataset_name=dataset_name,
            asset_type=asset_type,
            last_completed_date=last_completed_date,
            batch_no=batch_no,
            status=status,
        )

    def run_archive(
        self,
        dataset_name: str = "stock_daily",
        end_date: Optional[date] = None,
        limit_per_stock: int = 30,
    ) -> int:
        """Run stock daily archive for the given date range.

        Uses checkpoint to support resume.
        Fetches daily data for up to 30 active stocks.
        """
        if end_date is None:
            end_date = date.today()

        checkpoint = self.get_checkpoint(dataset_name)
        start_date = (
            checkpoint.get("last_completed_date")
            if checkpoint
            else date.today() - timedelta(days=365)
        )

        stocks = self.fetch_stock_universe(limit=limit_per_stock)

        total_records = 0
        batch_no = 0

        for ts_code, symbol in stocks:
            batch_no += 1

            if start_date and checkpoint:
                last_recorded = self.get_last_recorded_date(ts_code)
                if last_recorded and last_recorded >= start_date:
                    continue

            try:
                records = self.fetch_stock_daily(ts_code, start_date, end_date)
                if records:
                    persisted = self.persist_daily_records(records)
                    total_records += persisted
                    logger.info(f"Archived {persisted} records for {ts_code}")

                    if records:
                        self.upsert_checkpoint(
                            dataset_name=dataset_name,
                            last_completed_date=records[-1]["trade_date"],
                            last_ts_code=ts_code,
                            batch_no=batch_no,
                            status="in_progress",
                        )

            except Exception as e:
                logger.warning(f"Failed to archive {ts_code}: {e}")
                continue

        if total_records > 0:
            self.upsert_checkpoint(
                dataset_name=dataset_name,
                last_completed_date=end_date,
                last_ts_code=stocks[-1][0] if stocks else None,
                batch_no=batch_no,
                status="completed",
            )

        return total_records
