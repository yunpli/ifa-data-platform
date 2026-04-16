"""Tushare-backed adaptor for the first real highfreq raw paths."""

from __future__ import annotations

from datetime import datetime

from ifa_data_platform.highfreq.persistence import (
    HighfreqAuctionWorking,
    HighfreqEventStreamWorking,
    HighfreqIndex1mWorking,
    HighfreqProxy1mWorking,
    HighfreqStock1mWorking,
)
from ifa_data_platform.lowfreq.version_persistence import DatasetVersionRegistry
from ifa_data_platform.tushare.client import get_tushare_client


class HighfreqTushareAdaptor:
    def __init__(self) -> None:
        self.client = get_tushare_client()
        self.version_registry = DatasetVersionRegistry()
        self.stock_1m = HighfreqStock1mWorking()
        self.index_1m = HighfreqIndex1mWorking()
        self.proxy_1m = HighfreqProxy1mWorking()
        self.open_auction = HighfreqAuctionWorking("highfreq_open_auction_working")
        self.close_auction = HighfreqAuctionWorking("highfreq_close_auction_working")
        self.event_stream = HighfreqEventStreamWorking()

    def fetch_stock_1m(self, ts_code: str, start_time: str, end_time: str) -> list[dict]:
        rows = self.client.query(
            "stk_mins",
            {
                "ts_code": ts_code,
                "freq": "1min",
                "start_date": start_time,
                "end_date": end_time,
            },
            timeout_sec=30,
            max_retries=2,
        )
        out = []
        for row in rows:
            open_v = row.get("open")
            high_v = row.get("high")
            low_v = row.get("low")
            close_v = row.get("close")
            out.append(
                {
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
                }
            )
        return out

    def fetch_open_auction(self, ts_code: str, trade_date: str) -> list[dict]:
        rows = self.client.query("stk_auction_o", {"ts_code": ts_code, "trade_date": trade_date}, timeout_sec=30, max_retries=2)
        return rows

    def fetch_close_auction(self, ts_code: str, trade_date: str) -> list[dict]:
        rows = self.client.query("stk_auction_c", {"ts_code": ts_code, "trade_date": trade_date}, timeout_sec=30, max_retries=2)
        return rows

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

    def fetch_event_stream(self, start_date: str, end_date: str) -> list[dict]:
        records = []
        major_news = self.client.query("major_news", {"start_date": start_date, "end_date": end_date}, timeout_sec=30, max_retries=2)
        anns = self.client.query("anns_d", {"start_date": start_date, "end_date": end_date}, timeout_sec=30, max_retries=2)
        for row in major_news[:200]:
            records.append(
                {
                    'event_type': 'major_news',
                    'symbol': None,
                    'event_time': datetime.fromisoformat(str(row['pub_time'])),
                    'title': row.get('title'),
                    'source': row.get('src') or 'tushare',
                    'url': row.get('url'),
                    'payload': str(row),
                }
            )
        for row in anns[:200]:
            records.append(
                {
                    'event_type': 'announcement',
                    'symbol': row.get('ts_code'),
                    'event_time': datetime.strptime(str(row['ann_date']), '%Y%m%d'),
                    'title': row.get('title'),
                    'source': 'tushare_anns_d',
                    'url': row.get('url'),
                    'payload': str(row),
                }
            )
        return records

    def persist_event_stream(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_event_stream_working", "tushare_mix", run_id, watermark=watermark)
        count = self.event_stream.bulk_insert(records, version_id)
        self.version_registry.promote("highfreq_event_stream_working", version_id)
        return count

    def fetch_index_1m(self, ts_code: str, start_time: str, end_time: str) -> list[dict]:
        rows = self.client.query(
            "stk_mins",
            {
                "ts_code": ts_code,
                "freq": "1min",
                "start_date": start_time,
                "end_date": end_time,
            },
            timeout_sec=30,
            max_retries=2,
        )
        return [
            {
                'ts_code': row['ts_code'],
                'trade_time': datetime.fromisoformat(str(row['trade_time'])),
                'open': row.get('open'),
                'high': row.get('high'),
                'low': row.get('low'),
                'close': row.get('close'),
                'vol': row.get('vol'),
                'amount': row.get('amount'),
            }
            for row in rows
        ]

    def persist_index_1m(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_index_1m_working", "tushare", run_id, watermark=watermark)
        count = self.index_1m.bulk_replace(records, version_id)
        self.version_registry.promote("highfreq_index_1m_working", version_id)
        return count

    def fetch_proxy_1m(self) -> list[dict]:
        rows = self.client.query("ths_daily", {"ts_code": "885728.TI", "trade_date": "20260415"}, timeout_sec=30, max_retries=2)
        out = []
        for row in rows:
            trade_time = datetime.strptime(str(row['trade_date']) + ' 15:00:00', '%Y%m%d %H:%M:%S')
            out.append(
                {
                    'proxy_code': row['ts_code'],
                    'proxy_type': 'ths_sector_proxy',
                    'trade_time': trade_time,
                    'open': row.get('open'),
                    'high': row.get('high'),
                    'low': row.get('low'),
                    'close': row.get('close'),
                    'vol': row.get('vol'),
                    'amount': None,
                }
            )
        return out

    def persist_proxy_1m(self, run_id: str, records: list[dict], watermark: str) -> int:
        version_id = self.version_registry.create_version("highfreq_proxy_1m_working", "ths_proxy", run_id, watermark=watermark)
        count = self.proxy_1m.bulk_replace(records, version_id)
        self.version_registry.promote("highfreq_proxy_1m_working", version_id)
        return count
