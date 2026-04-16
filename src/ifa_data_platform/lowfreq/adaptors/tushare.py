"""Tushare adaptor for China-market low-frequency data."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult
from ifa_data_platform.lowfreq.canonical_persistence import (
    AnnouncementsCurrent,
    CompanyBasicCurrent,
    EtfDailyBasicCurrent,
    ForecastCurrent,
    FundBasicEtfCurrent,
    IndexBasicCurrent,
    IndexWeightCurrent,
    InvestorQaCurrent,
    MarginCurrent,
    NameChangeCurrent,
    NewShareCurrent,
    NewsCurrent,
    NorthSouthFlowCurrent,
    ResearchReportsCurrent,
    ShareFloatCurrent,
    StkHoldernumberCurrent,
    StkManagersCurrent,
    StockBasicCurrent,
    StockFundForecastCurrent,
    SwIndustryMappingCurrent,
    Top10FloatholdersCurrent,
    Top10HoldersCurrent,
    PledgeStatCurrent,
    TradeCalCurrent,
)
from ifa_data_platform.lowfreq.models import DatasetConfig
from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
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
        self._index_weight = IndexWeightCurrent()
        self._etf_daily_basic = EtfDailyBasicCurrent()
        self._share_float = ShareFloatCurrent()
        self._company_basic = CompanyBasicCurrent()
        self._stk_holdernumber = StkHoldernumberCurrent()
        self._name_change = NameChangeCurrent()
        self._new_share = NewShareCurrent()
        self._stk_managers = StkManagersCurrent()
        # Use existing classes for new datasets
        self._news_basic = NewsCurrent()  # news_basic uses news table
        self._stock_repurchase = AnnouncementsCurrent()  # reuse announcements table
        self._stock_dividend = AnnouncementsCurrent()  # reuse announcements table
        self._management = CompanyBasicCurrent()  # reuse company_basic table
        self._stock_equity_change = AnnouncementsCurrent()  # reuse announcements table
        self._top10_holders = Top10HoldersCurrent()
        self._top10_floatholders = Top10FloatholdersCurrent()
        self._pledge_stat = PledgeStatCurrent()
        self._forecast = ForecastCurrent()
        self._stock_fund_forecast = StockFundForecastCurrent()
        self._margin = MarginCurrent()
        self._north_south_flow = NorthSouthFlowCurrent()
        self.engine = make_engine()

    @property
    def client(self) -> TushareClient:
        """Lazy-initialize Tushare client."""
        if self._client is None:
            self._client = get_tushare_client()
        return self._client

    def _get_universe_symbols(self, universe_type: str = "C") -> list[str]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT symbol
                    FROM ifa2.symbol_universe
                    WHERE universe_type = :u AND is_active = true
                    ORDER BY symbol
                    """
                ),
                {"u": universe_type},
            ).fetchall()
            return [r.symbol for r in rows]

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

            elif dataset_name == "index_weight":
                raw_records, new_watermark = self._fetch_index_weight(watermark)
                request_params = {"trade_date": watermark}

            elif dataset_name == "etf_daily_basic":
                raw_records, new_watermark = self._fetch_etf_daily_basic(watermark)
                request_params = {"trade_date": watermark}

            elif dataset_name == "share_float":
                raw_records, new_watermark = self._fetch_share_float(watermark)
                request_params = {"trade_date": watermark}

            elif dataset_name == "company_basic":
                raw_records, new_watermark = self._fetch_company_basic()
                request_params = {}

            elif dataset_name == "stk_managers":
                raw_records, new_watermark = self._fetch_stk_managers(watermark)
                request_params = {"ts_code": watermark}

            elif dataset_name == "new_share":
                raw_records, new_watermark = self._fetch_new_share()
                request_params = {}

            elif dataset_name == "stk_holdernumber":
                raw_records, new_watermark = self._fetch_stk_holdernumber(watermark)
                request_params = {"end_date": watermark}

            elif dataset_name == "name_change":
                raw_records, new_watermark = self._fetch_name_change()
                request_params = {}

            elif dataset_name == "news_basic":
                raw_records, new_watermark = self._fetch_news_basic()
                request_params = {}

            elif dataset_name == "stock_repurchase":
                raw_records, new_watermark = self._fetch_stock_repurchase(watermark)
                request_params = {
                    "ann_date": watermark
                    or datetime.now(timezone.utc).strftime("%Y%m%d")
                }

            elif dataset_name == "stock_dividend":
                raw_records, new_watermark = self._fetch_stock_dividend(watermark)
                request_params = {
                    "ann_date": watermark
                    or datetime.now(timezone.utc).strftime("%Y%m%d")
                }

            elif dataset_name == "management":
                raw_records, new_watermark = self._fetch_management()
                request_params = {}

            elif dataset_name == "stock_equity_change":
                raw_records, new_watermark = self._fetch_stock_equity_change(watermark)
                request_params = {
                    "ann_date": watermark
                    or datetime.now(timezone.utc).strftime("%Y%m%d")
                }

            elif dataset_name == "top10_holders":
                raw_records, new_watermark = self._fetch_top10_holders()
                request_params = {"api_name": "top10_holders"}

            elif dataset_name == "top10_floatholders":
                raw_records, new_watermark = self._fetch_top10_floatholders()
                request_params = {"api_name": "top10_floatholders"}

            elif dataset_name == "pledge_stat":
                raw_records, new_watermark = self._fetch_pledge_stat()
                request_params = {"api_name": "pledge_stat"}

            elif dataset_name == "forecast":
                raw_records, new_watermark = self._fetch_forecast(watermark)
                request_params = {"api_name": "forecast"}

            elif dataset_name == "stock_fund_forecast":
                raw_records, new_watermark = self._fetch_stock_fund_forecast(watermark)
                request_params = {"api_name": "stock_fund_forecast"}

            elif dataset_name == "margin":
                raw_records, new_watermark = self._fetch_margin(watermark)
                request_params = {"api_name": "margin"}

            elif dataset_name == "north_south_flow":
                raw_records, new_watermark = self._fetch_north_south_flow(watermark)
                request_params = {"api_name": "moneyflow_hsgt"}

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
            news_datetime = None
            news_time_str = rec.get("datetime", "")
            if news_time_str:
                try:
                    news_datetime = datetime.strptime(
                        news_time_str, "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    try:
                        news_datetime = datetime.strptime(
                            news_time_str, "%Y-%m-%d %H:%M"
                        )
                    except ValueError:
                        news_datetime = datetime.now(timezone.utc)

            title = rec.get("title")
            if title is None:
                content = rec.get("content", "")
                title = content[:80] + "..." if len(content) > 80 else content

            parsed_records.append(
                {
                    "datetime": news_datetime,
                    "classify": rec.get("classify", ""),
                    "title": title,
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
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            trade_date = yesterday.strftime("%Y%m%d")

        records = self.client.query(
            "research_report",
            {"trade_date": trade_date},
        )

        parsed_records = []
        for rec in records:
            if not rec.get("ts_code"):
                continue

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
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            trade_date = yesterday.strftime("%Y%m%d")

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

    def _get_last_trading_day(self) -> Optional[str]:
        """Get the last trading day from the database."""
        try:
            from sqlalchemy import text

            with self._trade_cal.engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT cal_date FROM ifa2.trade_cal_current "
                        "WHERE is_open = 1 AND cal_date <= CURRENT_DATE "
                        "ORDER BY cal_date DESC LIMIT 1"
                    )
                )
                row = result.fetchone()
                if row:
                    return row[0].strftime("%Y%m%d")
        except Exception as e:
            logger.warning(f"Failed to get last trading day: {e}")
        return None

    def _fetch_index_weight(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        if not trade_date:
            trade_date = self._get_last_trading_day()
            if not trade_date:
                trade_date = "20240116"

        records = self.client.query(
            "index_weight",
            {"trade_date": trade_date},
        )

        parsed_records = []
        for rec in records:
            trade_date_val = None
            td_str = rec.get("trade_date", "")
            if td_str:
                try:
                    trade_date_val = datetime.strptime(td_str, "%Y%m%d").date()
                except ValueError:
                    trade_date_val = None

            parsed_records.append(
                {
                    "index_code": rec.get("index_code", ""),
                    "trade_date": trade_date_val,
                    "con_code": rec.get("con_code", ""),
                    "weight": rec.get("weight"),
                }
            )

        return parsed_records, trade_date

    def _fetch_etf_daily_basic(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        if not trade_date:
            trade_date = self._get_last_trading_day()
            if not trade_date:
                trade_date = "20250410"

        nav_records = self.client.query(
            "fund_nav",
            {"nav_date": trade_date},
        )
        adj_records = self.client.query(
            "fund_adj",
            {"trade_date": trade_date},
        )
        share_records = self.client.query(
            "fund_share",
            {"trade_date": trade_date},
        )

        adj_by_code = {
            rec.get("ts_code", ""): rec for rec in adj_records if rec.get("ts_code")
        }
        share_by_code = {
            rec.get("ts_code", ""): rec for rec in share_records if rec.get("ts_code")
        }

        parsed_records = []
        for rec in nav_records:
            ts_code = rec.get("ts_code", "")
            if not ts_code:
                continue

            trade_date_val = None
            td_str = rec.get("nav_date", "") or trade_date
            if td_str:
                try:
                    trade_date_val = datetime.strptime(td_str, "%Y%m%d").date()
                except ValueError:
                    trade_date_val = None

            share_rec = share_by_code.get(ts_code, {})
            adj_rec = adj_by_code.get(ts_code, {})
            share = share_rec.get("fd_share")
            unit_nav = rec.get("unit_nav")
            total_netasset = rec.get("total_netasset")

            parsed_records.append(
                {
                    "ts_code": ts_code,
                    "trade_date": trade_date_val,
                    "unit_nav": unit_nav,
                    "unit_total": rec.get("accum_nav"),
                    "total_mv": total_netasset,
                    "nav_mv": total_netasset,
                    "share": share,
                    "adj_factor": adj_rec.get("adj_factor"),
                }
            )

        return parsed_records, trade_date

    def _fetch_share_float(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        if not trade_date:
            trade_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        records = self.client.query(
            "share_float",
            {"trade_date": trade_date},
        )

        parsed_records = []
        for rec in records:
            float_date_val = None
            fd_str = rec.get("float_date", "")
            if fd_str:
                try:
                    float_date_val = datetime.strptime(fd_str, "%Y%m%d").date()
                except ValueError:
                    float_date_val = None

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "float_date": float_date_val,
                    "float_share": rec.get("float_share"),
                    "total_share": rec.get("total_share"),
                    "free_share": rec.get("free_share"),
                    "float_mv": rec.get("float_mv"),
                    "total_mv": rec.get("total_mv"),
                }
            )

        return parsed_records, trade_date

    def _fetch_company_basic(self) -> tuple[list[dict], str]:
        records = self.client.query("stock_company", {})

        parsed_records = []
        for rec in records:
            setup_date_val = None
            sd_str = rec.get("setup_date", "")
            if sd_str:
                try:
                    setup_date_val = datetime.strptime(sd_str, "%Y%m%d").date()
                except ValueError:
                    setup_date_val = None

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "exchange": rec.get("exchange"),
                    "chairman": rec.get("chairman"),
                    "manager": rec.get("manager"),
                    "secretary": rec.get("secretary"),
                    "registered_capital": rec.get("reg_capital"),
                    "paid_in_capital": None,
                    "setup_date": setup_date_val,
                    "province": rec.get("province"),
                    "city": rec.get("city"),
                    "introduction": rec.get("introduction"),
                    "website": rec.get("website"),
                    "email": rec.get("email"),
                    "office": rec.get("office"),
                    "employees": rec.get("employees"),
                    "main_business": rec.get("main_business"),
                    "business_scope": rec.get("business_scope"),
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_stk_managers(
        self, ts_code: Optional[str] = None
    ) -> tuple[list[dict], str]:
        params = {}
        if ts_code:
            params["ts_code"] = ts_code

        records = self.client.query("stk_managers", params)

        parsed_records = []
        for rec in records:
            begin_date_val = None
            bd_str = rec.get("begin_date", "")
            if bd_str:
                try:
                    begin_date_val = datetime.strptime(bd_str, "%Y%m%d").date()
                except ValueError:
                    begin_date_val = None

            end_date_val = None
            ed_str = rec.get("end_date", "")
            if ed_str:
                try:
                    end_date_val = datetime.strptime(ed_str, "%Y%m%d").date()
                except ValueError:
                    end_date_val = None

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "name": rec.get("name", ""),
                    "title": rec.get("title", ""),
                    "gender": rec.get("gender"),
                    "edu": rec.get("edu"),
                    "nationality": rec.get("nationality"),
                    "birthday": rec.get("birthday"),
                    "begin_date": begin_date_val,
                    "end_date": end_date_val,
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_new_share(self) -> tuple[list[dict], str]:
        records = self.client.query("new_share", {})

        parsed_records = []
        for rec in records:
            ipo_date_val = None
            ipo_str = rec.get("ipo_date", "")
            if ipo_str:
                try:
                    ipo_date_val = datetime.strptime(ipo_str, "%Y%m%d").date()
                except ValueError:
                    ipo_date_val = None

            issue_date_val = None
            issue_str = rec.get("issue_date", "")
            if issue_str:
                try:
                    issue_date_val = datetime.strptime(issue_str, "%Y%m%d").date()
                except ValueError:
                    issue_date_val = None

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "name": rec.get("name", ""),
                    "ipo_date": ipo_date_val,
                    "issue_date": issue_date_val,
                    "issue_price": rec.get("price"),
                    "amount": rec.get("amount"),
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_news_basic(self) -> tuple[list[dict], str]:
        records = self.client.query("news", {})

        parsed_records = []
        for rec in records:
            datetime_val = None
            dt_str = rec.get("datetime", "")
            if dt_str:
                try:
                    datetime_val = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

            # Skip records without datetime
            if not datetime_val:
                continue

            parsed_records.append(
                {
                    "datetime": datetime_val,
                    "classify": rec.get("classify"),
                    "title": rec.get("title"),
                    "source": rec.get("source"),
                    "url": rec.get("url"),
                    "content": rec.get("content"),
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_stock_repurchase(
        self, watermark: Optional[str] = None
    ) -> tuple[list[dict], str]:
        # Fetch recent repurchase data without date filter
        records = self.client.query("repurchase", {})

        parsed_records = []
        for rec in records:
            ann_date_val = None
            ad_str = rec.get("ann_date", "")
            if ad_str:
                try:
                    ann_date_val = datetime.strptime(ad_str, "%Y%m%d").date()
                except ValueError:
                    pass

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "ann_date": ann_date_val,
                    "holder_name": rec.get("holder_name"),
                    "hold_amount": rec.get("hold_amount"),
                    "hold_ratio": rec.get("hold_ratio"),
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_stock_dividend(
        self, watermark: Optional[str] = None
    ) -> tuple[list[dict], str]:
        # Fetch dividend data with a date range (last 1 year)
        end_date = datetime.now(timezone.utc).strftime("%Y%m%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime(
            "%Y%m%d"
        )
        records = self.client.query(
            "dividend", {"start_date": start_date, "end_date": end_date}
        )

        parsed_records = []
        for rec in records:
            ann_date_val = None
            ad_str = rec.get("ann_date", "")
            if ad_str:
                try:
                    ann_date_val = datetime.strptime(ad_str, "%Y%m%d").date()
                except ValueError:
                    pass

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "ann_date": ann_date_val,
                    "name": rec.get("name"),
                    "divi": rec.get("divi"),
                    "divi_ratio": rec.get("divi_ratio"),
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_management(self) -> tuple[list[dict], str]:
        records = self.client.query("stock_company", {})

        parsed_records = []
        for rec in records:
            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "exchange": rec.get("exchange"),
                    "chairman": rec.get("chairman"),
                    "manager": rec.get("manager"),
                    "secretary": rec.get("secretary"),
                    "registered_capital": rec.get("reg_capital"),
                    "setup_date": rec.get("setup_date"),
                    "province": rec.get("province"),
                    "city": rec.get("city"),
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_stock_equity_change(
        self, watermark: Optional[str] = None
    ) -> tuple[list[dict], str]:
        # Use stk_holdertrade for equity changes (股东增减持)
        records = self.client.query("stk_holdertrade", {})

        parsed_records = []
        for rec in records:
            ann_date_val = None
            ad_str = rec.get("ann_date", "")
            if ad_str:
                try:
                    ann_date_val = datetime.strptime(ad_str, "%Y%m%d").date()
                except ValueError:
                    pass

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "ann_date": ann_date_val,
                    "holder_name": rec.get("holder_name"),
                    "change_vol": rec.get("change_vol"),
                    "change_ratio": rec.get("change_ratio"),
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_name_change(self) -> tuple[list[dict], str]:
        records = self.client.query("namechange", {})

        parsed_records = []
        for rec in records:
            start_date_val = None
            sd_str = rec.get("start_date", "")
            if sd_str:
                try:
                    start_date_val = datetime.strptime(sd_str, "%Y%m%d").date()
                except ValueError:
                    start_date_val = None

            end_date_val = None
            ed_str = rec.get("end_date", "")
            if ed_str:
                try:
                    end_date_val = datetime.strptime(ed_str, "%Y%m%d").date()
                except ValueError:
                    end_date_val = None

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "name": rec.get("name", ""),
                    "start_date": start_date_val,
                    "end_date": end_date_val,
                }
            )

        return parsed_records, "full_snapshot"

    def _fetch_top10_holders(self) -> tuple[list[dict], str]:
        codes = self._get_universe_symbols("C")
        parsed_records = []
        failures = []
        for ts_code in codes:
            try:
                records = self.client.query("top10_holders", {"ts_code": ts_code}, timeout_sec=60, max_retries=3)
            except Exception as e:
                failures.append((ts_code, str(e)))
                logger.warning(f"top10_holders failed for {ts_code}: {e}")
                continue
            for rec in records:
                ann_date_val = None
                if rec.get("ann_date"):
                    ann_date_val = datetime.strptime(rec["ann_date"], "%Y%m%d").date()
                end_date_val = None
                if rec.get("end_date"):
                    end_date_val = datetime.strptime(rec["end_date"], "%Y%m%d").date()
                if end_date_val and rec.get("holder_name"):
                    parsed_records.append(
                        {
                            "ts_code": rec.get("ts_code", ts_code),
                            "ann_date": ann_date_val,
                            "end_date": end_date_val,
                            "holder_name": rec.get("holder_name"),
                            "hold_amount": rec.get("hold_amount"),
                            "hold_ratio": rec.get("hold_ratio"),
                            "hold_float_ratio": rec.get("hold_float_ratio"),
                            "hold_change": rec.get("hold_change"),
                            "holder_type": rec.get("holder_type"),
                        }
                    )
        if failures:
            logger.warning(f"top10_holders partial failures: {len(failures)} symbols")
        return parsed_records, datetime.now(timezone.utc).strftime("%Y%m%d")

    def _fetch_top10_floatholders(self) -> tuple[list[dict], str]:
        codes = self._get_universe_symbols("C")
        parsed_records = []
        failures = []
        for ts_code in codes:
            try:
                records = self.client.query("top10_floatholders", {"ts_code": ts_code}, timeout_sec=60, max_retries=3)
            except Exception as e:
                failures.append((ts_code, str(e)))
                logger.warning(f"top10_floatholders failed for {ts_code}: {e}")
                continue
            for rec in records:
                ann_date_val = None
                if rec.get("ann_date"):
                    ann_date_val = datetime.strptime(rec["ann_date"], "%Y%m%d").date()
                end_date_val = None
                if rec.get("end_date"):
                    end_date_val = datetime.strptime(rec["end_date"], "%Y%m%d").date()
                if end_date_val and rec.get("holder_name"):
                    parsed_records.append(
                        {
                            "ts_code": rec.get("ts_code", ts_code),
                            "ann_date": ann_date_val,
                            "end_date": end_date_val,
                            "holder_name": rec.get("holder_name"),
                            "hold_amount": rec.get("hold_amount"),
                            "hold_ratio": rec.get("hold_ratio"),
                            "hold_float_ratio": rec.get("hold_float_ratio"),
                            "hold_change": rec.get("hold_change"),
                            "holder_type": rec.get("holder_type"),
                        }
                    )
        if failures:
            logger.warning(f"top10_floatholders partial failures: {len(failures)} symbols")
        return parsed_records, datetime.now(timezone.utc).strftime("%Y%m%d")

    def _fetch_pledge_stat(self) -> tuple[list[dict], str]:
        codes = self._get_universe_symbols("C")
        parsed_records = []
        failures = []
        for ts_code in codes:
            try:
                records = self.client.query("pledge_stat", {"ts_code": ts_code}, timeout_sec=60, max_retries=3)
            except Exception as e:
                failures.append((ts_code, str(e)))
                logger.warning(f"pledge_stat failed for {ts_code}: {e}")
                continue
            for rec in records:
                end_date_val = None
                if rec.get("end_date"):
                    end_date_val = datetime.strptime(rec["end_date"], "%Y%m%d").date()
                if end_date_val:
                    parsed_records.append(
                        {
                            "ts_code": rec.get("ts_code", ts_code),
                            "end_date": end_date_val,
                            "pledge_count": rec.get("pledge_count"),
                            "unrest_pledge": rec.get("unrest_pledge"),
                            "rest_pledge": rec.get("rest_pledge"),
                            "total_share": rec.get("total_share"),
                            "pledge_ratio": rec.get("pledge_ratio"),
                        }
                    )
        if failures:
            logger.warning(f"pledge_stat partial failures: {len(failures)} symbols")
        return parsed_records, datetime.now(timezone.utc).strftime("%Y%m%d")

    def _fetch_stk_holdernumber(
        self, end_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        if not end_date:
            end_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        records = self.client.query("stk_holdernumber", {"end_date": end_date})

        parsed_records = []
        for rec in records:
            end_date_val = None
            ed_str = rec.get("end_date", "")
            if ed_str:
                try:
                    end_date_val = datetime.strptime(ed_str, "%Y%m%d").date()
                except ValueError:
                    end_date_val = None

            parsed_records.append(
                {
                    "ts_code": rec.get("ts_code", ""),
                    "end_date": end_date_val,
                    "holder_num": rec.get("holder_num"),
                }
            )

        return parsed_records, end_date

    def _fetch_forecast(
        self, start_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        if not start_date:
            start_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        codes = self._get_universe_symbols("C")
        parsed_records = []
        for ts_code in codes:
            records = self.client.query(
                "forecast", {"ts_code": ts_code, "ann_date": start_date}
            )
            for rec in records:
                ann_date_val = None
                ad_str = rec.get("ann_date", "")
                if ad_str:
                    try:
                        ann_date_val = datetime.strptime(ad_str, "%Y%m%d").date()
                    except ValueError:
                        ann_date_val = None
                end_date_val = None
                ed_str = rec.get("end_date", "")
                if ed_str:
                    try:
                        end_date_val = datetime.strptime(ed_str, "%Y%m%d").date()
                    except ValueError:
                        end_date_val = None
                if ann_date_val and end_date_val:
                    parsed_records.append(
                        {
                            "ts_code": rec.get("ts_code", ts_code),
                            "ann_date": ann_date_val,
                            "end_date": end_date_val,
                            "type": rec.get("type"),
                            "p_change_min": rec.get("p_change_min"),
                            "p_change_max": rec.get("p_change_max"),
                            "net_profit_min": rec.get("net_profit_min"),
                            "net_profit_max": rec.get("net_profit_max"),
                            "eps_min": rec.get("eps_min"),
                            "eps_max": rec.get("eps_max"),
                            "roe_min": rec.get("roe_min"),
                            "roe_max": rec.get("roe_max"),
                            "net_profit_ratio_min": rec.get("net_profit_ratio_min"),
                            "net_profit_ratio_max": rec.get("net_profit_ratio_max"),
                            "op_income_min": rec.get("op_income_min"),
                            "op_income_max": rec.get("op_income_max"),
                        }
                    )
        return parsed_records, datetime.now(timezone.utc).strftime("%Y%m%d")

    def _fetch_stock_fund_forecast(
        self, end_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        if not end_date:
            end_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        codes = self._get_universe_symbols("C")
        parsed_records = []
        for ts_code in codes:
            records = self.client.query(
                "stock_fund_forecast", {"ts_code": ts_code, "end_date": end_date}
            )
            for rec in records:
                end_date_val = None
                ed_str = rec.get("end_date", "")
                if ed_str:
                    try:
                        end_date_val = datetime.strptime(ed_str, "%Y%m%d").date()
                    except ValueError:
                        end_date_val = None

                if end_date_val:
                    parsed_records.append(
                        {
                            "ts_code": rec.get("ts_code", ts_code),
                            "end_date": end_date_val,
                            "type": rec.get("type"),
                            "eps": rec.get("eps"),
                            "eps_yoy": rec.get("eps_yoy"),
                            "net_profit": rec.get("net_profit"),
                            "net_profit_yoy": rec.get("net_profit_yoy"),
                            "gross_profit_margin": rec.get("gross_profit_margin"),
                            "net_profit_margin": rec.get("net_profit_margin"),
                            "roe": rec.get("roe"),
                            "earnings_weight": rec.get("earnings_weight"),
                            "conference_type": rec.get("conference_type"),
                            "org_type": rec.get("org_type"),
                            "org_sname": rec.get("org_sname"),
                            "analyst_name": rec.get("analyst_name"),
                        }
                    )
        return parsed_records, end_date

    def _fetch_margin(self, trade_date: Optional[str] = None) -> tuple[list[dict], str]:
        if not trade_date:
            trade_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        records = self.client.query("margin", {"trade_date": trade_date})

        parsed_records = []
        for rec in records:
            trade_date_val = None
            td_str = rec.get("trade_date", "")
            if td_str:
                try:
                    trade_date_val = datetime.strptime(td_str, "%Y%m%d").date()
                except ValueError:
                    trade_date_val = None

            if trade_date_val:
                parsed_records.append(
                    {
                        "trade_date": trade_date_val,
                        "ts_code": rec.get("ts_code"),
                        "rzye": rec.get("rzye"),
                        "rzmre": rec.get("rzmre"),
                        "rzche": rec.get("rzche"),
                        "rzche_ratio": rec.get("rzche_ratio"),
                        "rqye": rec.get("rqye"),
                        "rqmcl": rec.get("rqmcl"),
                        "rqchl": rec.get("rqchl"),
                        "rqchl_ratio": rec.get("rqchl_ratio"),
                        "total_market": rec.get("total_market"),
                        "total_margin": rec.get("total_margin"),
                    }
                )

        return parsed_records, trade_date

    def _fetch_north_south_flow(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        if not trade_date:
            trade_date = datetime.now(timezone.utc).strftime("%Y%m%d")

        records = self.client.query("moneyflow_hsgt", {"trade_date": trade_date})

        parsed_records = []
        for rec in records:
            trade_date_val = None
            td_str = rec.get("trade_date", "")
            if td_str:
                try:
                    trade_date_val = datetime.strptime(td_str, "%Y%m%d").date()
                except ValueError:
                    trade_date_val = None

            if trade_date_val:
                parsed_records.append(
                    {
                        "trade_date": trade_date_val,
                        "ts_code": rec.get("ts_code"),
                        "north_money": rec.get("north_money"),
                        "south_money": rec.get("south_money"),
                    }
                )

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

        elif dataset_name == "index_weight":
            index_weight_records = [
                {
                    "index_code": rec["index_code"],
                    "trade_date": rec["trade_date"],
                    "con_code": rec["con_code"],
                    "weight": rec["weight"],
                }
                for rec in records
            ]
            self._index_weight.bulk_upsert(index_weight_records, version_id=version_id)
            logger.info(
                f"Persisted {len(index_weight_records)} index_weight records to canonical"
            )

        elif dataset_name == "etf_daily_basic":
            etf_daily_basic_records = [
                {
                    "ts_code": rec["ts_code"],
                    "trade_date": rec["trade_date"],
                    "unit_nav": rec.get("unit_nav"),
                    "unit_total": rec.get("unit_total"),
                    "total_mv": rec.get("total_mv"),
                    "nav_mv": rec.get("nav_mv"),
                    "share": rec.get("share"),
                    "adj_factor": rec.get("adj_factor"),
                }
                for rec in records
            ]
            self._etf_daily_basic.bulk_upsert(
                etf_daily_basic_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(etf_daily_basic_records)} etf_daily_basic records to canonical"
            )

        elif dataset_name == "share_float":
            share_float_records = [
                {
                    "ts_code": rec["ts_code"],
                    "float_date": rec["float_date"],
                    "float_share": rec.get("float_share"),
                    "total_share": rec.get("total_share"),
                    "free_share": rec.get("free_share"),
                    "float_mv": rec.get("float_mv"),
                    "total_mv": rec.get("total_mv"),
                }
                for rec in records
            ]
            self._share_float.bulk_upsert(share_float_records, version_id=version_id)
            logger.info(
                f"Persisted {len(share_float_records)} share_float records to canonical"
            )

        elif dataset_name == "company_basic":
            company_basic_records = [
                {
                    "ts_code": rec["ts_code"],
                    "exchange": rec.get("exchange"),
                    "chairman": rec.get("chairman"),
                    "manager": rec.get("manager"),
                    "secretary": rec.get("secretary"),
                    "registered_capital": rec.get("registered_capital"),
                    "paid_in_capital": rec.get("paid_in_capital"),
                    "setup_date": rec.get("setup_date"),
                    "province": rec.get("province"),
                    "city": rec.get("city"),
                    "introduction": rec.get("introduction"),
                    "website": rec.get("website"),
                    "email": rec.get("email"),
                    "office": rec.get("office"),
                    "employees": rec.get("employees"),
                    "main_business": rec.get("main_business"),
                    "business_scope": rec.get("business_scope"),
                }
                for rec in records
            ]
            self._company_basic.bulk_upsert(
                company_basic_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(company_basic_records)} company_basic records to canonical"
            )

        elif dataset_name == "stk_managers":
            stk_managers_records = [
                {
                    "ts_code": rec["ts_code"],
                    "name": rec["name"],
                    "title": rec.get("title"),
                    "gender": rec.get("gender"),
                    "edu": rec.get("edu"),
                    "nationality": rec.get("nationality"),
                    "birthday": rec.get("birthday"),
                    "begin_date": rec.get("begin_date"),
                    "end_date": rec.get("end_date"),
                }
                for rec in records
            ]
            self._stk_managers.bulk_upsert(stk_managers_records, version_id=version_id)
            logger.info(
                f"Persisted {len(stk_managers_records)} stk_managers records to canonical"
            )

        elif dataset_name == "new_share":
            new_share_records = [
                {
                    "ts_code": rec["ts_code"],
                    "name": rec["name"],
                    "ipo_date": rec.get("ipo_date"),
                    "issue_date": rec.get("issue_date"),
                    "issue_price": rec.get("issue_price"),
                    "amount": rec.get("amount"),
                }
                for rec in records
            ]
            self._new_share.bulk_upsert(new_share_records, version_id=version_id)
            logger.info(
                f"Persisted {len(new_share_records)} new_share records to canonical"
            )

        elif dataset_name == "stk_holdernumber":
            stk_holdernumber_records = [
                {
                    "ts_code": rec["ts_code"],
                    "end_date": rec["end_date"],
                    "holder_num": rec.get("holder_num"),
                }
                for rec in records
            ]
            self._stk_holdernumber.bulk_upsert(
                stk_holdernumber_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(stk_holdernumber_records)} stk_holdernumber records to canonical"
            )

        elif dataset_name == "name_change":
            name_change_records = [
                {
                    "ts_code": rec["ts_code"],
                    "name": rec["name"],
                    "start_date": rec["start_date"],
                    "end_date": rec.get("end_date"),
                }
                for rec in records
            ]
            self._name_change.bulk_upsert(name_change_records, version_id=version_id)
            logger.info(
                f"Persisted {len(name_change_records)} name_change records to canonical"
            )

        elif dataset_name == "news_basic":
            news_basic_records = [
                {
                    "datetime": rec.get("datetime"),
                    "classify": rec.get("classify"),
                    "title": rec.get("title"),
                    "source": rec.get("source"),
                    "url": rec.get("url"),
                    "content": rec.get("content"),
                }
                for rec in records
            ]
            self._news.bulk_upsert(news_basic_records, version_id=version_id)
            logger.info(
                f"Persisted {len(news_basic_records)} news_basic records to canonical"
            )

        elif dataset_name == "stock_repurchase":
            stock_repurchase_records = [
                {
                    "ts_code": rec["ts_code"],
                    "ann_date": rec.get("ann_date"),
                    "holder_name": rec.get("holder_name"),
                    "hold_amount": rec.get("hold_amount"),
                    "hold_ratio": rec.get("hold_ratio"),
                }
                for rec in records
            ]
            self._stock_repurchase.bulk_upsert(
                stock_repurchase_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(stock_repurchase_records)} stock_repurchase records to canonical"
            )

        elif dataset_name == "stock_dividend":
            stock_dividend_records = [
                {
                    "ts_code": rec["ts_code"],
                    "ann_date": rec.get("ann_date"),
                    "name": rec.get("name"),
                    "divi": rec.get("divi"),
                    "divi_ratio": rec.get("divi_ratio"),
                }
                for rec in records
            ]
            self._stock_dividend.bulk_upsert(
                stock_dividend_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(stock_dividend_records)} stock_dividend records to canonical"
            )

        elif dataset_name == "management":
            management_records = [
                {
                    "ts_code": rec["ts_code"],
                    "exchange": rec.get("exchange"),
                    "chairman": rec.get("chairman"),
                    "manager": rec.get("manager"),
                    "secretary": rec.get("secretary"),
                    "registered_capital": rec.get("registered_capital"),
                    "setup_date": rec.get("setup_date"),
                    "province": rec.get("province"),
                    "city": rec.get("city"),
                }
                for rec in records
            ]
            self._management.bulk_upsert(management_records, version_id=version_id)
            logger.info(
                f"Persisted {len(management_records)} management records to canonical"
            )

        elif dataset_name == "stock_equity_change":
            stock_equity_change_records = [
                {
                    "ts_code": rec["ts_code"],
                    "ann_date": rec.get("ann_date"),
                    "change_type": rec.get("change_type"),
                    "change_vol": rec.get("change_vol"),
                    "after_share": rec.get("after_share"),
                }
                for rec in records
            ]
            self._stock_equity_change.bulk_upsert(
                stock_equity_change_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(stock_equity_change_records)} stock_equity_change records to canonical"
            )

        elif dataset_name == "top10_holders":
            top10_holders_records = [
                {
                    "ts_code": rec["ts_code"],
                    "ann_date": rec.get("ann_date"),
                    "end_date": rec["end_date"],
                    "holder_name": rec["holder_name"],
                    "hold_amount": rec.get("hold_amount"),
                    "hold_ratio": rec.get("hold_ratio"),
                    "hold_float_ratio": rec.get("hold_float_ratio"),
                    "hold_change": rec.get("hold_change"),
                    "holder_type": rec.get("holder_type"),
                }
                for rec in records
            ]
            self._top10_holders.bulk_upsert(
                top10_holders_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(top10_holders_records)} top10_holders records to canonical"
            )

        elif dataset_name == "top10_floatholders":
            top10_floatholders_records = [
                {
                    "ts_code": rec["ts_code"],
                    "ann_date": rec.get("ann_date"),
                    "end_date": rec["end_date"],
                    "holder_name": rec["holder_name"],
                    "hold_amount": rec.get("hold_amount"),
                    "hold_ratio": rec.get("hold_ratio"),
                    "hold_float_ratio": rec.get("hold_float_ratio"),
                    "hold_change": rec.get("hold_change"),
                    "holder_type": rec.get("holder_type"),
                }
                for rec in records
            ]
            self._top10_floatholders.bulk_upsert(
                top10_floatholders_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(top10_floatholders_records)} top10_floatholders records to canonical"
            )

        elif dataset_name == "pledge_stat":
            pledge_stat_records = [
                {
                    "ts_code": rec["ts_code"],
                    "end_date": rec["end_date"],
                    "pledge_count": rec.get("pledge_count"),
                    "unrest_pledge": rec.get("unrest_pledge"),
                    "rest_pledge": rec.get("rest_pledge"),
                    "total_share": rec.get("total_share"),
                    "pledge_ratio": rec.get("pledge_ratio"),
                }
                for rec in records
            ]
            self._pledge_stat.bulk_upsert(pledge_stat_records, version_id=version_id)
            logger.info(
                f"Persisted {len(pledge_stat_records)} pledge_stat records to canonical"
            )

        elif dataset_name == "forecast":
            forecast_records = [
                {
                    "ts_code": rec["ts_code"],
                    "ann_date": rec["ann_date"],
                    "end_date": rec["end_date"],
                    "type": rec.get("type"),
                    "p_change_min": rec.get("p_change_min"),
                    "p_change_max": rec.get("p_change_max"),
                    "net_profit_min": rec.get("net_profit_min"),
                    "net_profit_max": rec.get("net_profit_max"),
                    "eps_min": rec.get("eps_min"),
                    "eps_max": rec.get("eps_max"),
                    "roe_min": rec.get("roe_min"),
                    "roe_max": rec.get("roe_max"),
                    "net_profit_ratio_min": rec.get("net_profit_ratio_min"),
                    "net_profit_ratio_max": rec.get("net_profit_ratio_max"),
                    "op_income_min": rec.get("op_income_min"),
                    "op_income_max": rec.get("op_income_max"),
                }
                for rec in records
            ]
            self._forecast.bulk_upsert(forecast_records, version_id=version_id)
            logger.info(
                f"Persisted {len(forecast_records)} forecast records to canonical"
            )

        elif dataset_name == "stock_fund_forecast":
            stock_fund_forecast_records = [
                {
                    "ts_code": rec["ts_code"],
                    "end_date": rec["end_date"],
                    "type": rec.get("type"),
                    "eps": rec.get("eps"),
                    "eps_yoy": rec.get("eps_yoy"),
                    "net_profit": rec.get("net_profit"),
                    "net_profit_yoy": rec.get("net_profit_yoy"),
                    "gross_profit_margin": rec.get("gross_profit_margin"),
                    "net_profit_margin": rec.get("net_profit_margin"),
                    "roe": rec.get("roe"),
                    "earnings_weight": rec.get("earnings_weight"),
                    "conference_type": rec.get("conference_type"),
                    "org_type": rec.get("org_type"),
                    "org_sname": rec.get("org_sname"),
                    "analyst_name": rec.get("analyst_name"),
                }
                for rec in records
            ]
            self._stock_fund_forecast.bulk_upsert(
                stock_fund_forecast_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(stock_fund_forecast_records)} stock_fund_forecast records to canonical"
            )

        elif dataset_name == "margin":
            margin_records = [
                {
                    "trade_date": rec["trade_date"],
                    "ts_code": rec["ts_code"],
                    "rzye": rec.get("rzye"),
                    "rzmre": rec.get("rzmre"),
                    "rzche": rec.get("rzche"),
                    "rzche_ratio": rec.get("rzche_ratio"),
                    "rqye": rec.get("rqye"),
                    "rqmcl": rec.get("rqmcl"),
                    "rqchl": rec.get("rqchl"),
                    "rqchl_ratio": rec.get("rqchl_ratio"),
                    "total_market": rec.get("total_market"),
                    "total_margin": rec.get("total_margin"),
                }
                for rec in records
            ]
            self._margin.bulk_upsert(margin_records, version_id=version_id)
            logger.info(f"Persisted {len(margin_records)} margin records to canonical")

        elif dataset_name == "north_south_flow":
            north_south_flow_records = [
                {
                    "trade_date": rec["trade_date"],
                    "ts_code": rec["ts_code"],
                    "north_money": rec.get("north_money"),
                    "south_money": rec.get("south_money"),
                }
                for rec in records
            ]
            self._north_south_flow.bulk_upsert(
                north_south_flow_records, version_id=version_id
            )
            logger.info(
                f"Persisted {len(north_south_flow_records)} north_south_flow records to canonical"
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
