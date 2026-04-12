"""Dummy adaptor for mid-frequency datasets (testing only)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from ifa_data_platform.midfreq.adaptor import BaseAdaptor, FetchResult


class DummyMidfreqAdaptor(BaseAdaptor):
    """Dummy adaptor that returns mock data for testing."""

    def fetch(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
        run_id: Optional[str] = None,
        source_name: str = "dummy",
        version_id: Optional[str] = None,
    ) -> FetchResult:
        """Return mock data for testing."""
        mock_records = []

        if dataset_name == "equity_daily_bar":
            mock_records = [
                {
                    "ts_code": "000001.SZ",
                    "trade_date": date(2025, 4, 10),
                    "open": 10.5,
                    "high": 11.2,
                    "low": 10.3,
                    "close": 11.0,
                    "vol": 1000000,
                    "amount": 11000000,
                    "pre_close": 10.5,
                    "change": 0.5,
                    "pct_chg": 4.76,
                },
                {
                    "ts_code": "000002.SZ",
                    "trade_date": date(2025, 4, 10),
                    "open": 20.0,
                    "high": 20.5,
                    "low": 19.8,
                    "close": 20.2,
                    "vol": 500000,
                    "amount": 10100000,
                    "pre_close": 20.0,
                    "change": 0.2,
                    "pct_chg": 1.0,
                },
            ]
        elif dataset_name == "index_daily_bar":
            mock_records = [
                {
                    "ts_code": "000001.SH",
                    "trade_date": date(2025, 4, 10),
                    "open": 3000.0,
                    "high": 3050.0,
                    "low": 2980.0,
                    "close": 3030.0,
                    "vol": 350000000,
                    "amount": 105000000000,
                    "pre_close": 3000.0,
                    "change": 30.0,
                    "pct_chg": 1.0,
                },
            ]
        elif dataset_name == "etf_daily_bar":
            mock_records = [
                {
                    "ts_code": "510300.SH",
                    "trade_date": date(2025, 4, 10),
                    "open": 3.5,
                    "high": 3.6,
                    "low": 3.45,
                    "close": 3.55,
                    "vol": 50000000,
                    "amount": 177500000,
                    "pre_close": 3.5,
                    "change": 0.05,
                    "pct_chg": 1.43,
                },
            ]
        elif dataset_name == "northbound_flow":
            mock_records = [
                {
                    "trade_date": date(2025, 4, 10),
                    "north_money": 1500000000,
                    "north_bal": 25000000000,
                    "north_buy": 18000000000,
                    "north_sell": 16500000000,
                },
            ]
        elif dataset_name == "limit_up_down_status":
            mock_records = [
                {
                    "trade_date": date(2025, 4, 10),
                    "limit_up_count": 45,
                    "limit_down_count": 12,
                    "limit_up_streak_high": 7,
                    "limit_down_streak_high": 3,
                },
            ]

        return FetchResult(
            records=mock_records,
            watermark=watermark or "mock_watermark",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
