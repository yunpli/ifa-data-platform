"""Tushare adaptor for China-market low-frequency data."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Optional

from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult
from ifa_data_platform.lowfreq.canonical_persistence import (
    StockBasicCurrent,
    TradeCalCurrent,
)
from ifa_data_platform.lowfreq.models import DatasetConfig
from ifa_data_platform.lowfreq.raw_persistence import RawFetchPersistence
from ifa_data_platform.tushare.client import TushareClient, get_tushare_client

logger = logging.getLogger(__name__)


class TushareAdaptor(BaseAdaptor):
    """Tushare adaptor for China-market low-frequency data.

    Implements real Tushare API calls for:
    - trade_cal: China-market trading calendar
    - stock_basic: A-share instrument master data

    Persists raw fetch results to lowfreq_raw_fetch for audit/replay.
    Persists canonical data to current tables for trade_cal and stock_basic.
    """

    def __init__(self) -> None:
        self._client: Optional[TushareClient] = None
        self._raw_persistence = RawFetchPersistence()
        self._trade_cal = TradeCalCurrent()
        self._stock_basic = StockBasicCurrent()

    @property
    def client(self) -> TushareClient:
        """Lazy-initialize Tushare client."""
        if self._client is None:
            self._client = get_tushare_client()
        return self._client

    def fetch(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
        run_id: Optional[str] = None,
        source_name: str = "tushare",
    ) -> FetchResult:
        """Fetch data from Tushare for a specific dataset.

        Args:
            dataset_name: Name of the dataset to fetch (trade_cal, stock_basic).
            watermark: Optional watermark (start_date for trade_cal).
            limit: Optional record limit.
            run_id: Optional run_id for raw persistence linkage.
            source_name: Source name for raw persistence.

        Returns:
            FetchResult with records, watermark, and fetch timestamp.
        """
        logger.info(f"Fetching {dataset_name} from Tushare (watermark={watermark})")

        request_params: dict = {}
        raw_records: list[dict] = []
        new_watermark: Optional[str] = None

        try:
            if dataset_name == "trade_cal":
                raw_records, new_watermark = self._fetch_trade_cal(watermark)
                request_params = {
                    "exchange": "SSE",
                    "start_date": watermark or "20200101",
                    "end_date": datetime.now(timezone.utc).strftime("%Y%m%d"),
                }

            elif dataset_name == "stock_basic":
                raw_records, new_watermark = self._fetch_stock_basic(watermark)
                request_params = {
                    "list_status": "L",
                    "market": None,
                }

            else:
                raise ValueError(f"Unsupported dataset: {dataset_name}")

        except Exception as e:
            logger.error(f"Failed to fetch {dataset_name}: {e}")
            if run_id:
                self._raw_persistence.store(
                    run_id=run_id,
                    source_name=source_name,
                    dataset_name=dataset_name,
                    request_params=request_params,
                    raw_payload=[],
                    watermark=None,
                    status="failed",
                    error_message=str(e),
                )
            raise

        fetched_at = datetime.now(timezone.utc).isoformat()

        if run_id:
            self._raw_persistence.store(
                run_id=run_id,
                source_name=source_name,
                dataset_name=dataset_name,
                request_params=request_params,
                raw_payload=raw_records,
                watermark=new_watermark,
                status="success",
            )

            self._persist_canonical(dataset_name, raw_records)

        if limit:
            raw_records = raw_records[:limit]

        return FetchResult(
            records=raw_records,
            watermark=new_watermark,
            fetched_at=fetched_at,
        )

    def _fetch_trade_cal(
        self, start_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch trading calendar from Tushare.

        Args:
            start_date: Start date in YYYYMMDD format.

        Returns:
            Tuple of (records, end_date watermark).
        """
        if start_date:
            start_str = start_date[:8] if len(start_date) > 8 else start_date
        else:
            start_str = "20200101"

        end_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        records = self.client.query(
            "trade_cal",
            {
                "exchange": "SSE",
                "start_date": start_str,
                "end_date": end_str,
            },
        )

        parsed_records = []
        for rec in records:
            cal_date_str = rec.get("cal_date", "")
            try:
                cal_date = datetime.strptime(cal_date_str, "%Y%m%d").date()
            except (ValueError, TypeError):
                continue

            parsed_records.append(
                {
                    "cal_date": cal_date,
                    "exchange": rec.get("exchange", "SSE"),
                    "is_open": rec.get("is_open") == "1",
                    "pretrade_date": None,
                }
            )

        return parsed_records, end_str

    def _fetch_stock_basic(
        self, watermark: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch stock basic from Tushare.

        Args:
            watermark: Currently unused (stock_basic is a full snapshot).

        Returns:
            Tuple of (records, watermark string).
        """
        records = self.client.query(
            "stock_basic",
            {
                "list_status": "L",
            },
        )

        parsed_records = []
        for rec in records:
            list_date_str = rec.get("list_date", "")
            if list_date_str:
                try:
                    list_date = datetime.strptime(list_date_str, "%Y%m%d").date()
                except ValueError:
                    list_date = None
            else:
                list_date = None

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "symbol": rec.get("symbol", ""),
                    "name": rec.get("name", ""),
                    "area": rec.get("area", ""),
                    "industry": rec.get("industry", ""),
                    "market": rec.get("market", ""),
                    "list_status": rec.get("list_status", ""),
                    "list_date": list_date,
                    "delist_date": None,
                    "is_hs": int(rec["is_hs"]) if rec.get("is_hs") else None,
                }
            )

        return parsed_records, "full_snapshot"

    def _persist_canonical(self, dataset_name: str, records: list[dict]) -> None:
        """Persist records to canonical current tables.

        Args:
            dataset_name: Name of the dataset.
            records: Raw records to persist.
        """
        if dataset_name == "trade_cal":
            trade_cal_records = [
                {
                    "cal_date": rec["cal_date"],
                    "exchange": rec["exchange"],
                    "is_open": rec["is_open"],
                    "pretrade_date": rec.get("pretrade_date"),
                }
                for rec in records
            ]
            self._trade_cal.bulk_upsert(trade_cal_records)
            logger.info(
                f"Persisted {len(trade_cal_records)} trade_cal records to canonical"
            )

        elif dataset_name == "stock_basic":
            stock_basic_records = [
                {
                    "ts_code": rec["ts_code"],
                    "symbol": rec.get("symbol"),
                    "name": rec.get("name"),
                    "area": rec.get("area"),
                    "industry": rec.get("industry"),
                    "market": rec.get("market"),
                    "list_status": rec.get("list_status"),
                    "list_date": rec.get("list_date"),
                    "delist_date": rec.get("delist_date"),
                    "is_hs": rec.get("is_hs"),
                }
                for rec in records
            ]
            self._stock_basic.bulk_upsert(stock_basic_records)
            logger.info(
                f"Persisted {len(stock_basic_records)} stock_basic records to canonical"
            )

    def test_connection(self) -> bool:
        """Test the Tushare API connection.

        Returns:
            True if connection is successful.
        """
        return self.client.test_connection()

    def close(self) -> None:
        """Optional cleanup method."""
        self._client = None
