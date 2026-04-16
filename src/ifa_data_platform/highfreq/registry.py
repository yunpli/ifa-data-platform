"""Dataset registry for highfreq lane."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HighfreqDataset:
    dataset_name: str
    category: str
    source_policy: str
    enabled: bool = True
    description: str = ""


class HighfreqDatasetRegistry:
    def __init__(self) -> None:
        self._datasets = [
            HighfreqDataset("stock_1m_ohlcv", "stock", "tushare_or_alt_minute", True, "Stock minute OHLCV"),
            HighfreqDataset("index_1m_ohlcv", "index", "tushare_or_alt_index_minute", True, "Index minute OHLCV"),
            HighfreqDataset("etf_sector_style_1m_ohlcv", "proxy", "tushare_or_alt_proxy_minute", True, "ETF/sector/style minute OHLCV"),
            HighfreqDataset("futures_commodity_pm_1m_ohlcv", "derivatives", "tushare_or_alt_futures_minute", True, "Futures/commodity/precious metal minute OHLCV"),
            HighfreqDataset("open_auction_snapshot", "auction", "source_check_required", True, "Open auction result snapshot"),
            HighfreqDataset("close_auction_snapshot", "auction", "source_check_required", True, "Close auction result snapshot"),
            HighfreqDataset("event_time_stream", "event_stream", "platform_derived_or_source_mix", True, "Key event timestamp stream"),
            HighfreqDataset("l2_snapshot", "l2", "source_check_required", False, "L2 snapshot (not yet verified)"),
            HighfreqDataset("order_queue", "l2", "source_check_required", False, "Order queue (not yet verified)"),
            HighfreqDataset("tick_order", "l2", "source_check_required", False, "Tick-by-tick order (not yet verified)"),
            HighfreqDataset("tick_trade", "l2", "source_check_required", False, "Tick-by-tick trade (not yet verified)"),
        ]

    def list_enabled(self) -> list[HighfreqDataset]:
        return [d for d in self._datasets if d.enabled]

    def list_all(self) -> list[HighfreqDataset]:
        return list(self._datasets)
