"""Tushare adaptor for mid-frequency datasets."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from ifa_data_platform.midfreq.adaptor import BaseAdaptor, FetchResult
from ifa_data_platform.midfreq.canonical_persistence import (
    EquityDailyBarCurrent,
    EtfDailyBarCurrent,
    IndexDailyBarCurrent,
    LimitUpDownStatusCurrent,
    NorthboundFlowCurrent,
)
from ifa_data_platform.tushare.client import TushareClient, get_tushare_client
from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine

logger = logging.getLogger(__name__)


class MidfreqTushareAdaptor(BaseAdaptor):
    """Tushare adaptor for mid-frequency datasets.

    Implements data fetch for:
    - equity_daily_bar: A-share daily OHLCV
    - index_daily_bar: Index daily OHLCV
    - etf_daily_bar: ETF daily OHLCV
    - northbound_flow: Northbound (HK->CN) flow
    - limit_up_down_status: Limit up/down counts

    Persists canonical data to current tables.
    """

    def __init__(self) -> None:
        self._client: Optional[TushareClient] = None
        self._equity_daily_bar = EquityDailyBarCurrent()
        self._index_daily_bar = IndexDailyBarCurrent()
        self._etf_daily_bar = EtfDailyBarCurrent()
        self._northbound_flow = NorthboundFlowCurrent()
        self._limit_up_down_status = LimitUpDownStatusCurrent()
        self.engine = make_engine()

    @property
    def client(self) -> TushareClient:
        """Lazy-initialize Tushare client."""
        if self._client is None:
            self._client = get_tushare_client()
        return self._client

    def _get_universe_symbols(self, universe_type: str = "B") -> list[str]:
        """Get symbols from symbol_universe table for given Universe type."""
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

    def _get_last_trading_day(self) -> Optional[str]:
        """Get the last trading day from the database."""
        try:
            with self.engine.begin() as conn:
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

    def fetch(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
        run_id: Optional[str] = None,
        source_name: str = "tushare",
        version_id: Optional[str] = None,
    ) -> FetchResult:
        """Fetch data from Tushare for a specific midfreq dataset.

        Args:
            dataset_name: Name of the dataset to fetch.
            watermark: Optional watermark (trade_date).
            limit: Optional record limit.
            run_id: Optional run_id for raw persistence.
            source_name: Source name.
            version_id: Optional version ID.

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
            if dataset_name == "equity_daily_bar":
                raw_records, new_watermark = self._fetch_equity_daily_bar(watermark)
                request_params = {
                    "api_name": "daily",
                    "trade_date": watermark,
                }

            elif dataset_name == "index_daily_bar":
                raw_records, new_watermark = self._fetch_index_daily_bar(watermark)
                request_params = {
                    "api_name": "index_daily",
                    "trade_date": watermark,
                }

            elif dataset_name == "etf_daily_bar":
                raw_records, new_watermark = self._fetch_etf_daily_bar(watermark)
                request_params = {
                    "api_name": "etf_daily",
                    "trade_date": watermark,
                }

            elif dataset_name == "northbound_flow":
                raw_records, new_watermark = self._fetch_northbound_flow(watermark)
                request_params = {
                    "api_name": "moneyflow_hsgt",
                    "trade_date": watermark,
                }

            elif dataset_name == "limit_up_down_status":
                raw_records, new_watermark = self._fetch_limit_up_down_status(watermark)
                request_params = {
                    "api_name": "stk_limit",
                    "trade_date": watermark,
                }

            else:
                raise ValueError(f"Unsupported midfreq dataset: {dataset_name}")

        except Exception as e:
            logger.error(f"Failed to fetch {dataset_name}: {e}")
            raise

        fetched_at = datetime.now(timezone.utc).isoformat()

        if raw_records:
            self._persist_canonical(dataset_name, raw_records, version_id=version_id)

        if limit:
            raw_records = raw_records[:limit]

        return FetchResult(
            records=raw_records,
            watermark=new_watermark,
            fetched_at=fetched_at,
        )

    def _persist_canonical(
        self,
        dataset_name: str,
        records: list[dict],
        version_id: Optional[str] = None,
    ) -> int:
        """Persist records to canonical current table."""
        if not records:
            return 0

        if dataset_name == "equity_daily_bar":
            return self._equity_daily_bar.bulk_upsert(records, version_id)
        elif dataset_name == "index_daily_bar":
            return self._index_daily_bar.bulk_upsert(records, version_id)
        elif dataset_name == "etf_daily_bar":
            return self._etf_daily_bar.bulk_upsert(records, version_id)
        elif dataset_name == "northbound_flow":
            return self._northbound_flow.bulk_upsert(records, version_id)
        elif dataset_name == "limit_up_down_status":
            return self._limit_up_down_status.bulk_upsert(records, version_id)

        return 0

    def _fetch_equity_daily_bar(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch equity daily bar ( OHLCV) from Tushare."""
        if not trade_date:
            trade_date = self._get_last_trading_day()
            if not trade_date:
                trade_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                    "%Y%m%d"
                )

        symbols = self._get_universe_symbols("B")
        parsed_records = []
        failures = []

        for ts_code in symbols:
            full_code = (
                f"{ts_code}.SZ"
                if ts_code.startswith("0") or ts_code.startswith("3")
                else f"{ts_code}.SH"
            )
            try:
                records = self.client.query(
                    "daily",
                    {"ts_code": full_code, "trade_date": trade_date},
                    timeout_sec=30,
                    max_retries=2,
                )
                for rec in records:
                    trade_date_val = None
                    td_str = rec.get("trade_date", "")
                    if td_str:
                        try:
                            trade_date_val = datetime.strptime(td_str, "%Y%m%d").date()
                        except ValueError:
                            continue
                    if trade_date_val:
                        parsed_records.append(
                            {
                                "ts_code": rec.get("ts_code", full_code),
                                "trade_date": trade_date_val,
                                "open": rec.get("open"),
                                "high": rec.get("high"),
                                "low": rec.get("low"),
                                "close": rec.get("close"),
                                "vol": rec.get("vol"),
                                "amount": rec.get("amount"),
                                "pre_close": rec.get("pre_close"),
                                "change": rec.get("change"),
                                "pct_chg": rec.get("pct_chg"),
                            }
                        )
            except Exception as e:
                failures.append((ts_code, str(e)))
                logger.warning(f"equity_daily_bar failed for {ts_code}: {e}")
                continue

        if failures:
            logger.warning(
                f"equity_daily_bar partial failures: {len(failures)} symbols"
            )
        return parsed_records, trade_date

    def _fetch_index_daily_bar(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch index daily bar from Tushare."""
        if not trade_date:
            trade_date = self._get_last_trading_day()
            if not trade_date:
                trade_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                    "%Y%m%d"
                )

        index_codes = [
            "000001.SH",
            "399001.SZ",
            "399006.SZ",
            "000300.SH",
            "000905.SH",
            "000016.SH",
            "000688.SH",
            "399300.SZ",
        ]
        parsed_records = []

        for ts_code in index_codes:
            try:
                records = self.client.query(
                    "index_daily",
                    {"ts_code": ts_code, "trade_date": trade_date},
                    timeout_sec=30,
                    max_retries=2,
                )
                for rec in records:
                    trade_date_val = None
                    td_str = rec.get("trade_date", "")
                    if td_str:
                        try:
                            trade_date_val = datetime.strptime(td_str, "%Y%m%d").date()
                        except ValueError:
                            continue
                    if trade_date_val:
                        parsed_records.append(
                            {
                                "ts_code": rec.get("ts_code", ts_code),
                                "trade_date": trade_date_val,
                                "open": rec.get("open"),
                                "high": rec.get("high"),
                                "low": rec.get("low"),
                                "close": rec.get("close"),
                                "vol": rec.get("vol"),
                                "amount": rec.get("amount"),
                                "pre_close": rec.get("pre_close"),
                                "change": rec.get("change"),
                                "pct_chg": rec.get("pct_chg"),
                            }
                        )
            except Exception as e:
                logger.warning(f"index_daily_bar failed for {ts_code}: {e}")
                continue

        return parsed_records, trade_date

    def _fetch_etf_daily_bar(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch ETF daily bar from Tushare."""
        if not trade_date:
            trade_date = self._get_last_trading_day()
            if not trade_date:
                trade_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                    "%Y%m%d"
                )

        etf_codes = [
            "510300.SH",
            "510500.SH",
            "512880.SH",
            "159915.SZ",
            "159938.SZ",
            "510050.SH",
            "159920.SZ",
            "159928.SZ",
            "159985.SZ",
            "510010.SH",
            "159901.SZ",
            "159991.SZ",
        ]
        parsed_records = []

        for ts_code in etf_codes:
            try:
                records = self.client.query(
                    "etf_daily",
                    {"ts_code": ts_code, "trade_date": trade_date},
                    timeout_sec=30,
                    max_retries=2,
                )
                for rec in records:
                    trade_date_val = None
                    td_str = rec.get("trade_date", "")
                    if td_str:
                        try:
                            trade_date_val = datetime.strptime(td_str, "%Y%m%d").date()
                        except ValueError:
                            continue
                    if trade_date_val:
                        parsed_records.append(
                            {
                                "ts_code": rec.get("ts_code", ts_code),
                                "trade_date": trade_date_val,
                                "open": rec.get("open"),
                                "high": rec.get("high"),
                                "low": rec.get("low"),
                                "close": rec.get("close"),
                                "vol": rec.get("vol"),
                                "amount": rec.get("amount"),
                                "pre_close": rec.get("pre_close"),
                                "change": rec.get("change"),
                                "pct_chg": rec.get("pct_chg"),
                            }
                        )
            except Exception as e:
                logger.warning(f"etf_daily_bar failed for {ts_code}: {e}")
                continue

        return parsed_records, trade_date

    def _fetch_northbound_flow(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch northbound (HK->CN) flow from Tushare."""
        if not trade_date:
            trade_date = self._get_last_trading_day()
            if not trade_date:
                trade_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                    "%Y%m%d"
                )

        try:
            records = self.client.query(
                "moneyflow_hsgt",
                {"trade_date": trade_date},
                timeout_sec=30,
                max_retries=2,
            )
        except Exception as e:
            logger.warning(f"northbound_flow query failed: {e}")
            return [], trade_date

        parsed_records = []
        for rec in records:
            trade_date_val = None
            td_str = rec.get("trade_date", "")
            if td_str:
                try:
                    trade_date_val = datetime.strptime(td_str, "%Y%m%d").date()
                except ValueError:
                    continue
            if trade_date_val:
                parsed_records.append(
                    {
                        "trade_date": trade_date_val,
                        "north_money": rec.get("north_money"),
                        "north_bal": rec.get("north_bal"),
                        "north_buy": rec.get("north_buy"),
                        "north_sell": rec.get("north_sell"),
                    }
                )

        return parsed_records, trade_date

    def _fetch_limit_up_down_status(
        self, trade_date: Optional[str] = None
    ) -> tuple[list[dict], str]:
        """Fetch limit up/down status from Tushare."""
        if not trade_date:
            trade_date = self._get_last_trading_day()
            if not trade_date:
                trade_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                    "%Y%m%d"
                )

        try:
            records = self.client.query(
                "stk_limit",
                {"trade_date": trade_date},
                timeout_sec=30,
                max_retries=2,
            )
        except Exception as e:
            logger.warning(f"limit_up_down_status query failed: {e}")
            return [], trade_date

        parsed_records = []
        total_up = 0
        total_down = 0

        for rec in records:
            limit = rec.get("limit", "")
            if limit == "U":
                total_up += 1
            elif limit == "D":
                total_down += 1

        trade_date_val = None
        if trade_date:
            try:
                trade_date_val = datetime.strptime(trade_date, "%Y%m%d").date()
            except ValueError:
                pass

        if trade_date_val:
            parsed_records.append(
                {
                    "trade_date": trade_date_val,
                    "limit_up_count": total_up,
                    "limit_down_count": total_down,
                    "limit_up_streak_high": None,
                    "limit_down_streak_high": None,
                }
            )

        return parsed_records, trade_date
