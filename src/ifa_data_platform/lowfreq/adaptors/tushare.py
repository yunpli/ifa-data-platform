"""Tushare adaptor for China-market low-frequency data."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Optional

from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult
from ifa_data_platform.lowfreq.canonical_persistence import (
    AnnouncementsCurrent,
    FundBasicEtfCurrent,
    IndexBasicCurrent,
    InvestorQaCurrent,
    NewsCurrent,
    ResearchReportsCurrent,
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
        self._announcements = AnnouncementsCurrent()
        self._news = NewsCurrent()
        self._research_reports = ResearchReportsCurrent()
        self._investor_qa = InvestorQaCurrent()

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

            elif dataset_name == "announcements":
                raw_records, new_watermark = self._fetch_announcements(watermark)
                request_params = {
                    "ann_date": watermark
                    or datetime.now(timezone.utc).strftime("%Y%m%d"),
                }

            elif dataset_name == "news":
                raw_records, new_watermark = self._fetch_news(watermark)
                request_params = {}

            elif dataset_name == "research_reports":
                raw_records, new_watermark = self._fetch_research_reports(watermark)
                request_params = {
                    "trade_date": watermark
                    or datetime.now(timezone.utc).strftime("%Y%m%d"),
                }

            elif dataset_name == "investor_qa":
                raw_records, new_watermark = self._fetch_investor_qa(watermark)
                request_params = {
                    "trade_date": watermark
                    or datetime.now(timezone.utc).strftime("%Y%m%d"),
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

            if fund_type:
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

    def _fetch_announcements(
        self, ann_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch announcements from Tushare anns_d API."""
        if not ann_date:
            ann_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        records = self.client.query(
            "anns_d",
            {"ann_date": ann_date},
        )

        parsed_records = []
        for rec in records:
            rec_time = None
            rec_time_str = rec.get("rec_time", "")
            if rec_time_str:
                try:
                    rec_time = datetime.strptime(rec_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    rec_time = None

            ann_date_val = None
            ann_date_str = rec.get("ann_date", "")
            if ann_date_str:
                try:
                    ann_date_val = datetime.strptime(ann_date_str, "%Y%m%d").date()
                except ValueError:
                    ann_date_val = None

            parsed_records.append(
                {
                    "ann_date": ann_date_val,
                    "ts_code": rec.get("ts_code", ""),
                    "name": rec.get("name", ""),
                    "title": rec.get("title", ""),
                    "url": rec.get("url", ""),
                    "rec_time": rec_time,
                }
            )

        return parsed_records, ann_date

    def _fetch_news(self, watermark: Optional[str] = None) -> tuple[list[dict], str]:
        """Fetch news from Tushare news API."""
        records = self.client.query(
            "news",
            {},
        )

        parsed_records = []
        for rec in records:
            news_time_str = rec.get("time", "")
            news_datetime = None
            if news_time_str:
                try:
                    news_datetime = datetime.strptime(news_time_str, "%m-%d %H:%M")
                    current_year = datetime.now().year
                    news_datetime = news_datetime.replace(year=current_year)
                except ValueError:
                    news_datetime = datetime.now(timezone.utc)

            parsed_records.append(
                {
                    "datetime": news_datetime,
                    "classify": rec.get("classify", ""),
                    "title": rec.get("title", ""),
                    "source": rec.get("source", ""),
                    "url": rec.get("url", ""),
                    "content": rec.get("content", "")[:2000]
                    if rec.get("content")
                    else None,
                }
            )

        return parsed_records, datetime.now(timezone.utc).strftime("%Y%m%d")

    def _fetch_research_reports(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch research reports from Tushare research_report API."""
        if not trade_date:
            trade_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        records = self.client.query(
            "research_report",
            {"trade_date": trade_date},
        )

        parsed_records = []
        for rec in records:
            report_date_val = None
            report_date_str = rec.get("trade_date", "")
            if report_date_str:
                try:
                    report_date_val = datetime.strptime(
                        report_date_str, "%Y%m%d"
                    ).date()
                except ValueError:
                    report_date_val = None

            parsed_records.append(
                {
                    "trade_date": report_date_val,
                    "ts_code": rec.get("ts_code", ""),
                    "name": rec.get("name", ""),
                    "title": rec.get("title", ""),
                    "report_type": rec.get("report_type", ""),
                    "author": rec.get("author", ""),
                    "inst_csname": rec.get("inst_csname", ""),
                    "ind_name": rec.get("ind_name", ""),
                    "url": rec.get("url", ""),
                }
            )

        return parsed_records, trade_date

    def _fetch_investor_qa(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch investor Q&A from Tushare irm_qa_sz and irm_qa_sh APIs."""
        if not trade_date:
            trade_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        parsed_records = []

        for api_name in ["irm_qa_sz", "irm_qa_sh"]:
            try:
                records = self.client.query(
                    api_name,
                    {"trade_date": trade_date},
                )

                for rec in records:
                    pub_time_val = None
                    pub_time_str = rec.get("pub_time", "")
                    if pub_time_str:
                        try:
                            pub_time_val = datetime.strptime(
                                pub_time_str, "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            pub_time_val = None

                    qa_date_val = None
                    qa_date_str = rec.get("trade_date", "")
                    if qa_date_str:
                        try:
                            qa_date_val = datetime.strptime(
                                qa_date_str, "%Y%m%d"
                            ).date()
                        except ValueError:
                            qa_date_val = None

                    answer_text = rec.get("a", "")
                    if answer_text and len(answer_text) > 5000:
                        answer_text = answer_text[:5000]

                    parsed_records.append(
                        {
                            "ts_code": rec.get("ts_code", ""),
                            "trade_date": qa_date_val,
                            "q": rec.get("q", ""),
                            "name": rec.get("name", ""),
                            "a": answer_text,
                            "pub_time": pub_time_val,
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch {api_name}: {e}")

        return parsed_records, trade_date

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

        elif dataset_name == "announcements":
            announcements_records = [
                {
                    "ann_date": rec["ann_date"],
                    "ts_code": rec["ts_code"],
                    "name": rec.get("name"),
                    "title": rec.get("title"),
                    "url": rec.get("url"),
                    "rec_time": rec.get("rec_time"),
                }
                for rec in records
            ]
            self._announcements.bulk_upsert(
                announcements_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(announcements_records)} announcements records to canonical"
            )

        elif dataset_name == "news":
            news_records = [
                {
                    "datetime": rec["datetime"],
                    "classify": rec.get("classify"),
                    "title": rec.get("title"),
                    "source": rec.get("source"),
                    "url": rec.get("url"),
                    "content": rec.get("content"),
                }
                for rec in records
            ]
            self._news.bulk_upsert(news_records, version_id=version_id)
            logger.info(f"Persisted {len(news_records)} news records to canonical")

        elif dataset_name == "research_reports":
            research_reports_records = [
                {
                    "trade_date": rec["trade_date"],
                    "ts_code": rec["ts_code"],
                    "name": rec.get("name"),
                    "title": rec.get("title"),
                    "report_type": rec.get("report_type"),
                    "author": rec.get("author"),
                    "inst_csname": rec.get("inst_csname"),
                    "ind_name": rec.get("ind_name"),
                    "url": rec.get("url"),
                }
                for rec in records
            ]
            self._research_reports.bulk_upsert(
                research_reports_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(research_reports_records)} research_reports records to canonical"
            )

        elif dataset_name == "investor_qa":
            investor_qa_records = [
                {
                    "ts_code": rec["ts_code"],
                    "trade_date": rec["trade_date"],
                    "q": rec["q"],
                    "name": rec.get("name"),
                    "a": rec.get("a"),
                    "pub_time": rec.get("pub_time"),
                }
                for rec in records
            ]
            self._investor_qa.bulk_upsert(investor_qa_records, version_id=version_id)
            logger.info(
                f"Persisted {len(investor_qa_records)} investor_qa records to canonical"
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
