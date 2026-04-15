"""Commodity/Futures/Precious Metals historical archiver for D4."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.tushare.client import get_tushare_client

logger = logging.getLogger(__name__)


FUTURES_POOL = [
    {"ts_code": "AU2506.SHF", "name": "Gold", "category": "precious_metal"},
    {"ts_code": "AG2506.SHF", "name": "Silver", "category": "precious_metal"},
    {"ts_code": "CU2506.SHF", "name": "Copper", "category": "base_metal"},
    {"ts_code": "AL2506.SHF", "name": "Aluminum", "category": "base_metal"},
    {"ts_code": "ZN2506.SHF", "name": "Zinc", "category": "base_metal"},
    {"ts_code": "PB2506.SHF", "name": "Lead", "category": "base_metal"},
    {"ts_code": "NI2506.SHF", "name": "Nickel", "category": "base_metal"},
    {"ts_code": "SC2506.SHF", "name": "Crude Oil", "category": "energy"},
    {"ts_code": "RB2506.SHF", "name": "Rebar", "category": "energy"},
    {"ts_code": "HC2506.SHF", "name": "Hot Rolled Coil", "category": "energy"},
    {"ts_code": "RU2506.SHF", "name": "Natural Rubber", "category": "commodity"},
    {"ts_code": "TA2506.ZCE", "name": "PTA", "category": "chemical"},
    {"ts_code": "MA2506.ZCE", "name": "Methanol", "category": "chemical"},
    {"ts_code": "SR2506.CZCE", "name": "Sugar", "category": "agricultural"},
    {"ts_code": "CF2506.CZCE", "name": "Cotton", "category": "agricultural"},
    {"ts_code": "RM2506.CZCE", "name": "Soybean Meal", "category": "agricultural"},
    {"ts_code": "M2506.CZCE", "name": "Soybean Oil", "category": "agricultural"},
    {"ts_code": "Y2506.CZCE", "name": "Soybean", "category": "agricultural"},
    {"ts_code": "A2506.DCE", "name": "Soybean", "category": "agricultural"},
    {"ts_code": "B2506.DCE", "name": "Soybean Meal", "category": "agricultural"},
    {"ts_code": "C2506.DCE", "name": "Corn", "category": "agricultural"},
    {"ts_code": "J2506.DCE", "name": "Iron Ore", "category": "metals"},
    {"ts_code": "JM2506.DCE", "name": "Iron Ore", "category": "metals"},
    {"ts_code": "I2506.DCE", "name": "Iron Ore", "category": "metals"},
    {"ts_code": "J2509.DCE", "name": "Iron Ore", "category": "metals"},
    {"ts_code": "IF2506.CFFEX", "name": "CSI 300 Index", "category": "index"},
    {"ts_code": "IH2506.CFFEX", "name": "CSI 500 Index", "category": "index"},
    {"ts_code": "IC2506.CFFEX", "name": "CSI 500 Index", "category": "index"},
    {"ts_code": "T2506.CFFEX", "name": "10Y Treasury", "category": "bond"},
    {"ts_code": "TF2506.CFFEX", "name": "5Y Treasury", "category": "bond"},
]


class CommodityArchiver:
    """Archiver for commodity/futures/precious metals historical data.

    Fetches futures data from Tushare and persists to futures_history.
    Supports checkpoint-based backfill and resume.
    """

    def __init__(self) -> None:
        self.engine = make_engine()
        self._tushare_client: Optional[object] = None
        self.dataset_name = "futures_history"

    @property
    def tushare_client(self):
        """Lazy-initialize Tushare client."""
        if self._tushare_client is None:
            self._tushare_client = get_tushare_client()
        return self._tushare_client

    def get_active_contracts(self, category: Optional[str] = None) -> list[dict]:
        """Get active futures contracts from the pool.

        Args:
            category: Optional category filter (e.g., 'precious_metal', 'base_metal')

        Returns:
            List of contract dicts with ts_code and metadata
        """
        if category:
            return [f for f in FUTURES_POOL if f.get("category") == category]
        return FUTURES_POOL

    def fetch_futures_daily(
        self,
        ts_code: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch daily data for a single futures contract between dates."""
        try:
            records = self.tushare_client.query(
                "fut_daily",
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
                if not trade_date_str:
                    continue

                try:
                    trade_date = datetime.strptime(trade_date_str, "%Y%m%d").date()
                except (ValueError, TypeError):
                    continue

                parsed.append(
                    {
                        "ts_code": ts_code,
                        "trade_date": trade_date,
                        "pre_close": rec.get("pre_close"),
                        "pre_settle": rec.get("pre_settle"),
                        "open": rec.get("open"),
                        "high": rec.get("high"),
                        "low": rec.get("low"),
                        "close": rec.get("close"),
                        "settle": rec.get("settle"),
                        "change1": rec.get("change1"),
                        "change2": rec.get("change2"),
                        "vol": rec.get("vol"),
                        "amount": rec.get("amount"),
                        "oi": rec.get("oi"),
                        "oi_chg": rec.get("oi_chg"),
                        "source": "tushare",
                    }
                )

            return parsed
        except Exception as e:
            logger.warning(f"Failed to fetch futures data for {ts_code}: {e}")
            return []

    def persist_futures_records(self, records: list[dict]) -> int:
        """Persist futures records to the archive table.

        Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
        """
        if not records:
            return 0

        with self.engine.begin() as conn:
            for rec in records:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.futures_history (
                            id, ts_code, trade_date, pre_close, pre_settle, open, high, low,
                            close, settle, change1, change2, vol, amount, oi, oi_chg, source
                        ) VALUES (
                            gen_random_uuid(), :ts_code, :trade_date, :pre_close, :pre_settle,
                            :open, :high, :low, :close, :settle, :change1, :change2, :vol,
                            :amount, :oi, :oi_chg, :source
                        )
                        ON CONFLICT (ts_code, trade_date) DO NOTHING
                        """
                    ),
                    {
                        "ts_code": rec["ts_code"],
                        "trade_date": rec["trade_date"],
                        "pre_close": rec.get("pre_close"),
                        "pre_settle": rec.get("pre_settle"),
                        "open": rec.get("open"),
                        "high": rec.get("high"),
                        "low": rec.get("low"),
                        "close": rec.get("close"),
                        "settle": rec.get("settle"),
                        "change1": rec.get("change1"),
                        "change2": rec.get("change2"),
                        "vol": rec.get("vol"),
                        "amount": rec.get("amount"),
                        "oi": rec.get("oi"),
                        "oi_chg": rec.get("oi_chg"),
                        "source": rec.get("source", "tushare"),
                    },
                )

        return len(records)

    def get_checkpoint(self, dataset_name: str) -> Optional[dict]:
        """Get checkpoint for a dataset from archive_checkpoints."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT dataset_name, asset_type, last_completed_date, batch_no, status
                    FROM ifa2.archive_checkpoints
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()
            if result:
                return {
                    "dataset_name": result.dataset_name,
                    "asset_type": result.asset_type,
                    "last_completed_date": result.last_completed_date,
                    "batch_no": result.batch_no,
                    "status": result.status,
                }
        return None

    def upsert_checkpoint(
        self,
        dataset_name: str,
        asset_type: str,
        last_completed_date: Optional[date] = None,
        batch_no: int = 0,
        status: str = "in_progress",
    ) -> None:
        """Upsert checkpoint to archive_checkpoints."""
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

    def run_archive(
        self,
        dataset_name: str = "futures_history",
        end_date: Optional[date] = None,
        max_contracts: int = 30,
        category_filter: Optional[set[str]] = None,
        asset_type: str = "futures",
    ) -> int:
        """Run futures/commodity/precious-metals archive for the given date range.

        Uses checkpoint to support resume.
        Fetches data for configured futures contracts, optionally filtered by category.
        """
        if end_date is None:
            end_date = date.today()

        checkpoint = self.get_checkpoint(dataset_name)
        start_date = (
            checkpoint.get("last_completed_date")
            if checkpoint
            else date.today() - timedelta(days=365)
        )

        contracts = self.get_active_contracts()
        if category_filter:
            contracts = [c for c in contracts if c.get("category") in category_filter]
        contracts = contracts[:max_contracts]

        total_records = 0
        batch_no = 0

        for contract in contracts:
            batch_no += 1
            ts_code = contract["ts_code"]

            try:
                records = self.fetch_futures_daily(ts_code, start_date, end_date)
                if records:
                    persisted = self.persist_futures_records(records)
                    total_records += persisted
                    logger.info(f"Archived {persisted} records for {ts_code}")
            except Exception as e:
                logger.warning(f"Failed to archive {ts_code}: {e}")
                continue

        self.upsert_checkpoint(
            dataset_name=dataset_name,
            asset_type=asset_type,
            last_completed_date=end_date,
            batch_no=batch_no,
            status="completed",
        )
        if total_records > 0:
            logger.info(
                f"{asset_type} archive completed: {total_records} records for {batch_no} contracts"
            )
        else:
            logger.info(f"{asset_type} archive completed with no new records")

        return total_records
