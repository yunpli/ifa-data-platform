"""Tushare adaptor for China-market low-frequency data."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Optional

from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult
from ifa_data_platform.lowfreq.canonical_persistence import (
    FundBasicEtfCurrent,
    IndexBasicCurrent,
    StockBasicCurrent,
    SwIndustryMappingCurrent,
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
        self._index_basic = IndexBasicCurrent()
        self._fund_basic_etf = FundBasicEtfCurrent()
        self._sw_industry_mapping = SwIndustryMappingCurrent()

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
        version_id: Optional[str] = None,
    ) -> FetchResult:
        """Fetch data from Tushare for a specific dataset.

        Args:
            dataset_name: Name of the dataset to fetch (trade_cal, stock_basic).
            watermark: Optional watermark (start_date for trade_cal).
            limit: Optional record limit.
            run_id: Optional run_id for raw persistence linkage.
            source_name: Source name for raw persistence.
            version_id: Optional version ID for version tracking.

        Returns:
            FetchResult with records, watermark, and fetch timestamp.
        """
        logger.info(
            f"Fetching {dataset_name} from Tushare (watermark={watermark}, version_id={version_id})"
        )

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

            elif dataset_name == "index_basic":
                raw_records, new_watermark = self._fetch_index_basic()
                request_params = {"market": None}

            elif dataset_name == "fund_basic_etf":
                raw_records, new_watermark = self._fetch_fund_basic_etf()
                request_params = {"market": None}

            elif dataset_name == "sw_industry_mapping":
                raw_records, new_watermark = self._fetch_sw_industry_mapping()
                request_params = {}

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

            self._persist_canonical(dataset_name, raw_records, version_id=version_id)

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

    def _fetch_index_basic(
        self,
    ) -> tuple[list[dict], str]:
        """Fetch index basic from Tushare."""
        records = self.client.query(
            "index_basic",
            {"market": None},
        )

        parsed_records = []
        for rec in records:
            base_date_str = rec.get("base_date", "")
            if base_date_str:
                try:
                    base_date = datetime.strptime(base_date_str, "%Y%m%d").date()
                except ValueError:
                    base_date = None
            else:
                base_date = None

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
                    "name": rec.get("name", ""),
                    "market": rec.get("market", ""),
                    "publisher": rec.get("publisher", ""),
                    "category": rec.get("category", ""),
                    "base_date": base_date,
                    "base_point": rec.get("base_point"),
                    "list_date": list_date,
                    "weight_rule": rec.get("weight_rule", ""),
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_fund_basic_etf(
        self,
    ) -> tuple[list[dict], str]:
        """Fetch fund basic (ETF subset) from Tushare."""
        records = self.client.query(
            "fund_basic",
            {"market": None},
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

            due_date_str = rec.get("due_date", "")
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y%m%d").date()
                except ValueError:
                    due_date = None
            else:
                due_date = None

            issue_date_str = rec.get("issue_date", "")
            if issue_date_str:
                try:
                    issue_date = datetime.strptime(issue_date_str, "%Y%m%d").date()
                except ValueError:
                    issue_date = None
            else:
                issue_date = None

            delist_date_str = rec.get("delist_date", "")
            if delist_date_str:
                try:
                    delist_date = datetime.strptime(delist_date_str, "%Y%m%d").date()
                except ValueError:
                    delist_date = None
            else:
                delist_date = None

            fund_type = rec.get("fund_type", "")
            is_etf = fund_type and "ETF" in fund_type.upper()

            if is_etf or not fund_type:
                parsed_records.append(
                    {
                        "ts_code": rec.get("ts_code", ""),
                        "name": rec.get("name", ""),
                        "market": rec.get("market", ""),
                        "fund_type": fund_type,
                        "management": rec.get("management", ""),
                        "custodian": rec.get("custodian", ""),
                        "list_date": list_date,
                        "due_date": due_date,
                        "issue_date": issue_date,
                        "delist_date": delist_date,
                        "invest_type": rec.get("invest_type", ""),
                        "benchmark": rec.get("benchmark", ""),
                        "status": rec.get("status", ""),
                    }
                )

        return parsed_records, "full_snapshot"

    def _fetch_sw_industry_mapping(
        self,
    ) -> tuple[list[dict], str]:
        """Fetch Shenwan industry mapping from Tushare."""
        records = self.client.query(
            "index_member",
            {},
        )

        parsed_records = []
        for rec in records:
            in_date_str = rec.get("in_date", "")
            if in_date_str:
                try:
                    in_date = datetime.strptime(in_date_str, "%Y%m%d").date()
                except ValueError:
                    in_date = None
            else:
                in_date = None

            out_date_str = rec.get("out_date", "")
            if out_date_str:
                try:
                    out_date = datetime.strptime(out_date_str, "%Y%m%d").date()
                except ValueError:
                    out_date = None
            else:
                out_date = None

            parsed_records.append(
                {
                    "index_code": rec.get("index_code", ""),
                    "industry_name": rec.get("industry_name", ""),
                    "level": None,
                    "parent_code": None,
                    "src": "sw",
                    "member_ts_code": rec.get("con_code", ""),
                    "member_name": rec.get("name", ""),
                    "in_date": in_date,
                    "out_date": out_date,
                    "is_active": out_date is None,
                }
            )

        return parsed_records, "full_snapshot"

    def _persist_canonical(
        self,
        dataset_name: str,
        records: list[dict],
        version_id: Optional[str] = None,
    ) -> None:
        """Persist records to canonical current tables.

        Args:
            dataset_name: Name of the dataset.
            records: Raw records to persist.
            version_id: Optional version ID for version tracking.
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
            self._trade_cal.bulk_upsert(trade_cal_records, version_id=version_id)
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
            self._stock_basic.bulk_upsert(stock_basic_records, version_id=version_id)
            logger.info(
                f"Persisted {len(stock_basic_records)} stock_basic records to canonical"
            )

        elif dataset_name == "index_basic":
            index_basic_records = [
                {
                    "ts_code": rec["ts_code"],
                    "name": rec.get("name"),
                    "market": rec.get("market"),
                    "publisher": rec.get("publisher"),
                    "category": rec.get("category"),
                    "base_date": rec.get("base_date"),
                    "base_point": rec.get("base_point"),
                    "list_date": rec.get("list_date"),
                    "weight_rule": rec.get("weight_rule"),
                }
                for rec in records
            ]
            self._index_basic.bulk_upsert(index_basic_records, version_id=version_id)
            logger.info(
                f"Persisted {len(index_basic_records)} index_basic records to canonical"
            )

        elif dataset_name == "fund_basic_etf":
            fund_basic_etf_records = [
                {
                    "ts_code": rec["ts_code"],
                    "name": rec.get("name"),
                    "market": rec.get("market"),
                    "fund_type": rec.get("fund_type"),
                    "management": rec.get("management"),
                    "custodian": rec.get("custodian"),
                    "list_date": rec.get("list_date"),
                    "due_date": rec.get("due_date"),
                    "issue_date": rec.get("issue_date"),
                    "delist_date": rec.get("delist_date"),
                    "invest_type": rec.get("invest_type"),
                    "benchmark": rec.get("benchmark"),
                    "status": rec.get("status"),
                }
                for rec in records
            ]
            self._fund_basic_etf.bulk_upsert(
                fund_basic_etf_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(fund_basic_etf_records)} fund_basic_etf records to canonical"
            )

        elif dataset_name == "sw_industry_mapping":
            sw_industry_mapping_records = [
                {
                    "index_code": rec["index_code"],
                    "industry_name": rec.get("industry_name"),
                    "level": rec.get("level"),
                    "parent_code": rec.get("parent_code"),
                    "src": rec.get("src"),
                    "member_ts_code": rec.get("member_ts_code"),
                    "member_name": rec.get("member_name"),
                    "in_date": rec.get("in_date"),
                    "out_date": rec.get("out_date"),
                    "is_active": rec.get("is_active", True),
                }
                for rec in records
            ]
            self._sw_industry_mapping.bulk_upsert(
                sw_industry_mapping_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(sw_industry_mapping_records)} sw_industry_mapping records to canonical"
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
