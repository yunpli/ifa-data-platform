"""Tushare-backed adaptor for real highfreq paths.

Removes the old hardcoded sample symbol/date windows and routes collection through
Business-Layer scope plus durable alias->live-contract resolution.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from ifa_data_platform.highfreq.persistence import (
    HighfreqAuctionWorking,
    HighfreqEventStreamWorking,
    HighfreqFuturesMinuteWorking,
    HighfreqIndex1mWorking,
    HighfreqProxy1mWorking,
    HighfreqStock1mWorking,
)
from ifa_data_platform.lowfreq.version_persistence import DatasetVersionRegistry
from ifa_data_platform.runtime.contract_resolver import ContractResolver
from ifa_data_platform.runtime.target_manifest import KEY_FOCUS_LIST_TYPES, SelectorScope, build_target_manifest
from ifa_data_platform.tushare.client import get_tushare_client

BJ = ZoneInfo("Asia/Shanghai")


class HighfreqTushareAdaptor:
    def __init__(self) -> None:
        self.client = get_tushare_client()
        self.version_registry = DatasetVersionRegistry()
        self.contract_resolver = ContractResolver()
        self.stock_1m = HighfreqStock1mWorking()
        self.index_1m = HighfreqIndex1mWorking()
        self.proxy_1m = HighfreqProxy1mWorking()
        self.futures_1m = HighfreqFuturesMinuteWorking()
        self.open_auction = HighfreqAuctionWorking("highfreq_open_auction_working")
        self.close_auction = HighfreqAuctionWorking("highfreq_close_auction_working")
        self.event_stream = HighfreqEventStreamWorking()

    def _current_beijing_window(self) -> tuple[str, str, str]:
        now_bj = datetime.now(BJ)
        trade_day = now_bj.date()
        start_dt = datetime.combine(trade_day, time(9, 0), tzinfo=BJ)
        floor_minute = max(1, min(240, now_bj.hour * 60 + now_bj.minute - (9 * 60)))
        end_dt = start_dt + timedelta(minutes=floor_minute)
        return trade_day.strftime("%Y%m%d"), start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")

    def _highfreq_manifest_items(self, asset_categories: set[str]) -> list[dict]:
        manifest = build_target_manifest(SelectorScope(list_types=tuple(sorted(KEY_FOCUS_LIST_TYPES))))
        out = []
        seen = set()
        for item in manifest.items:
            if item.resolved_lane != "highfreq":
                continue
            if item.asset_category not in asset_categories:
                continue
            key = (item.asset_category, item.symbol_or_series_id)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "asset_category": item.asset_category,
                "symbol": item.symbol_or_series_id,
                "display_name": item.display_name,
                "priority": item.priority,
            })
        return sorted(out, key=lambda x: (x["priority"], x["symbol"]))

    def fetch_stock_1m(self) -> list[dict]:
        _, start_time, end_time = self._current_beijing_window()
        out: list[dict] = []
        for item in self._highfreq_manifest_items({"stock"}):
            ts_code = self.contract_resolver.resolve(item["symbol"], "stock").ts_code
            rows = self.client.query("stk_mins", {"ts_code": ts_code, "freq": "1min", "start_date": start_time, "end_date": end_time}, timeout_sec=30, max_retries=2)
            for row in rows:
                open_v = row.get("open")
                high_v = row.get("high")
                low_v = row.get("low")
                close_v = row.get("close")
                out.append({
                    "ts_code": row["ts_code"],
                    "trade_time": datetime.fromisoformat(str(row["trade_time"])),
                    "open": open_v,
                    "high": high_v,
                    "low": low_v,
                    "close": close_v,
                    "vol": row.get("vol"),
                    "amount": row.get("amount"),
                    "vwap": (row.get("amount") / row.get("vol")) if row.get("amount") and row.get("vol") else None,
                    "amplitude": ((high_v - low_v) / close_v) if high_v is not None and low_v is not None and close_v not in (None, 0) else None,
                })
        return out

    def fetch_open_auction(self) -> list[dict]:
        trade_date, _, _ = self._current_beijing_window()
        rows_out = []
        for item in self._highfreq_manifest_items({"stock"}):
            ts_code = self.contract_resolver.resolve(item["symbol"], "stock").ts_code
            rows_out.extend(self.client.query("stk_auction_o", {"ts_code": ts_code, "trade_date": trade_date}, timeout_sec=30, max_retries=2))
        return rows_out

    def fetch_close_auction(self) -> list[dict]:
        trade_date, _, _ = self._current_beijing_window()
        rows_out = []
        for item in self._highfreq_manifest_items({"stock"}):
            ts_code = self.contract_resolver.resolve(item["symbol"], "stock").ts_code
            rows_out.extend(self.client.query("stk_auction_c", {"ts_code": ts_code, "trade_date": trade_date}, timeout_sec=30, max_retries=2))
        return rows_out

    def persist_stock_1m(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_stock_1m_working", "tushare", run_id, watermark=watermark)
        count = self.stock_1m.bulk_replace(records, version_id)
        self.version_registry.promote("highfreq_stock_1m_working", version_id)
        return count

    def persist_open_auction(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_open_auction_working", "tushare", run_id, watermark=watermark)
        count = self.open_auction.bulk_replace(records, version_id)
        self.version_registry.promote("highfreq_open_auction_working", version_id)
        return count

    def persist_close_auction(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_close_auction_working", "tushare", run_id, watermark=watermark)
        count = self.close_auction.bulk_replace(records, version_id)
        self.version_registry.promote("highfreq_close_auction_working", version_id)
        return count

    def fetch_event_stream(self) -> list[dict]:
        trade_date, _, _ = self._current_beijing_window()
        next_date = (datetime.strptime(trade_date, "%Y%m%d").date() + timedelta(days=1)).strftime("%Y%m%d")
        records = []
        major_news = self.client.query("major_news", {"start_date": trade_date, "end_date": next_date}, timeout_sec=30, max_retries=2)
        anns = self.client.query("anns_d", {"start_date": trade_date, "end_date": next_date}, timeout_sec=30, max_retries=2)
        for row in major_news[:500]:
            records.append({"event_type": "major_news", "symbol": None, "event_time": datetime.fromisoformat(str(row["pub_time"])), "title": row.get("title"), "source": row.get("src") or "tushare", "url": row.get("url"), "payload": str(row)})
        for row in anns[:500]:
            records.append({"event_type": "announcement", "symbol": row.get("ts_code"), "event_time": datetime.strptime(str(row["ann_date"]), "%Y%m%d"), "title": row.get("title"), "source": "tushare_anns_d", "url": row.get("url"), "payload": str(row)})
        return records

    def persist_event_stream(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_event_stream_working", "tushare_mix", run_id, watermark=watermark)
        count = self.event_stream.bulk_insert(records, version_id)
        self.version_registry.promote("highfreq_event_stream_working", version_id)
        return count

    def fetch_index_1m(self) -> list[dict]:
        _, start_time, end_time = self._current_beijing_window()
        out = []
        for item in self._highfreq_manifest_items({"index"}):
            ts_code = self.contract_resolver.resolve(item["symbol"], "index").ts_code
            rows = self.client.query("idx_mins", {"ts_code": ts_code, "freq": "1min", "start_date": start_time, "end_date": end_time}, timeout_sec=30, max_retries=2)
            out.extend({
                "ts_code": row["ts_code"],
                "trade_time": datetime.fromisoformat(str(row["trade_time"])),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "vol": row.get("vol"),
                "amount": row.get("amount"),
            } for row in rows)
        return out

    def persist_index_1m(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_index_1m_working", "tushare_idx_mins", run_id, watermark=watermark)
        count = self.index_1m.bulk_replace(records, version_id)
        self.version_registry.promote("highfreq_index_1m_working", version_id)
        return count

    def fetch_proxy_1m(self) -> list[dict]:
        _, start_time, end_time = self._current_beijing_window()
        out = []
        for item in self._highfreq_manifest_items({"etf"}):
            ts_code = self.contract_resolver.resolve(item["symbol"], "etf").ts_code
            rows = self.client.query("stk_mins", {"ts_code": ts_code, "freq": "1min", "start_date": start_time, "end_date": end_time}, timeout_sec=30, max_retries=2)
            for row in rows:
                out.append({
                    "proxy_code": row["ts_code"],
                    "proxy_type": "focus_etf_proxy",
                    "trade_time": datetime.fromisoformat(str(row["trade_time"])),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                    "vol": row.get("vol"),
                    "amount": row.get("amount"),
                })
        return out

    def persist_proxy_1m(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_proxy_1m_working", "tushare_stk_mins_proxy", run_id, watermark=watermark)
        count = self.proxy_1m.bulk_replace(records, version_id)
        self.version_registry.promote("highfreq_proxy_1m_working", version_id)
        return count

    def fetch_futures_family_1m(self) -> list[dict]:
        _, start_time, end_time = self._current_beijing_window()
        buckets = {
            "precious_metal": {"precious_metal"},
            "commodity": {"commodity", "metal", "base_metal", "black_chain", "chemical", "agri", "agricultural", "energy"},
            "futures": {"futures"},
        }
        records = []
        for bucket, categories in buckets.items():
            items = self._highfreq_manifest_items(categories)
            for item in items:
                resolved = self.contract_resolver.resolve(item["symbol"], item["asset_category"])
                mins = self.client.query("ft_mins", {"ts_code": resolved.ts_code, "freq": "1min", "start_date": start_time, "end_date": end_time}, timeout_sec=30, max_retries=2)
                for row in mins:
                    records.append({
                        "ts_code": row["ts_code"],
                        "bucket": bucket,
                        "trade_time": datetime.fromisoformat(str(row["trade_time"])),
                        "open": row.get("open"),
                        "high": row.get("high"),
                        "low": row.get("low"),
                        "close": row.get("close"),
                        "vol": row.get("vol"),
                        "amount": row.get("amount"),
                        "oi": row.get("oi"),
                    })
        return records

    def persist_futures_family_1m(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_futures_minute_working", "tushare_ft_mins", run_id, watermark=watermark)
        count = self.futures_1m.bulk_replace(records, version_id)
        self.version_registry.promote("highfreq_futures_minute_working", version_id)
        return count
