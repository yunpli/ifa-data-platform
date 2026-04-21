"""Highfreq runner for milestone 2 raw-layer landing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.highfreq.adaptor_tushare import HighfreqTushareAdaptor
from ifa_data_platform.highfreq.derived_signals import DerivedSignalBuilder
from ifa_data_platform.highfreq.persistence import HighfreqRunStore
from ifa_data_platform.highfreq.registry import HighfreqDatasetRegistry


@dataclass
class RunnerResult:
    dataset_name: str
    status: str
    records_processed: int
    watermark: Optional[str] = None
    error_message: Optional[str] = None


class HighfreqRunner:
    def __init__(self) -> None:
        self.registry = HighfreqDatasetRegistry()
        self.adaptor = HighfreqTushareAdaptor()
        self.derived_builder = DerivedSignalBuilder()
        self.run_store = HighfreqRunStore()

    def run(self, dataset_name: str, dry_run: bool = False, run_id: Optional[str] = None) -> RunnerResult:
        now = datetime.now(timezone.utc).isoformat()
        enabled = {d.dataset_name for d in self.registry.list_enabled()}
        if dataset_name not in enabled:
            result = RunnerResult(
                dataset_name=dataset_name,
                status="unsupported",
                records_processed=0,
                watermark=now,
                error_message="dataset_not_enabled_or_not_verified",
            )
            if run_id:
                self.run_store.record(run_id, dataset_name, result.status, result.records_processed, result.watermark, result.error_message)
            return result

        if dry_run:
            result = RunnerResult(dataset_name=dataset_name, status="dry_run", records_processed=0, watermark=now)
            if run_id:
                self.run_store.record(run_id, dataset_name, result.status, result.records_processed, result.watermark, result.error_message)
            return result

        if dataset_name == "stock_1m_ohlcv":
            records = self.adaptor.fetch_stock_1m()
            count = self.adaptor.persist_stock_1m(run_id or "highfreq-local", records, now)
            result = RunnerResult(dataset_name=dataset_name, status="succeeded", records_processed=count, watermark=now)
        elif dataset_name == "open_auction_snapshot":
            records = self.adaptor.fetch_open_auction()
            count = self.adaptor.persist_open_auction(run_id or "highfreq-local", records, now)
            result = RunnerResult(dataset_name=dataset_name, status="succeeded", records_processed=count, watermark=now)
        elif dataset_name == "close_auction_snapshot":
            records = self.adaptor.fetch_close_auction()
            count = self.adaptor.persist_close_auction(run_id or "highfreq-local", records, now)
            result = RunnerResult(dataset_name=dataset_name, status="succeeded", records_processed=count, watermark=now)
        elif dataset_name == "event_time_stream":
            records = self.adaptor.fetch_event_stream()
            count = self.adaptor.persist_event_stream(run_id or "highfreq-local", records, now)
            result = RunnerResult(dataset_name=dataset_name, status="succeeded", records_processed=count, watermark=now)
        elif dataset_name == "index_1m_ohlcv":
            records = self.adaptor.fetch_index_1m()
            count = self.adaptor.persist_index_1m(run_id or "highfreq-local", records, now)
            result = RunnerResult(dataset_name=dataset_name, status="succeeded", records_processed=count, watermark=now)
        elif dataset_name == "etf_sector_style_1m_ohlcv":
            records = self.adaptor.fetch_proxy_1m()
            count = self.adaptor.persist_proxy_1m(run_id or "highfreq-local", records, now)
            result = RunnerResult(dataset_name=dataset_name, status="succeeded", records_processed=count, watermark=now)
        elif dataset_name == "futures_commodity_pm_1m_ohlcv":
            records = self.adaptor.fetch_futures_family_1m()
            count = self.adaptor.persist_futures_family_1m(run_id or "highfreq-local", records, now)
            result = RunnerResult(dataset_name=dataset_name, status="succeeded", records_processed=count, watermark=now)
        else:
            result = RunnerResult(
                dataset_name=dataset_name,
                status="deferred",
                records_processed=0,
                watermark=now,
                error_message="source_not_verified_or_storage_not_landed_in_milestone2_batch4",
            )

        if run_id:
            self.run_store.record(run_id, dataset_name, result.status, result.records_processed, result.watermark, result.error_message)
        return result

    def build_derived_state(self, dry_run: bool = False, run_id: Optional[str] = None) -> RunnerResult:
        now = datetime.now(timezone.utc).isoformat()
        dataset_name = "derived_signal_state"
        if dry_run:
            result = RunnerResult(dataset_name=dataset_name, status="dry_run", records_processed=0, watermark=now)
            if run_id:
                self.run_store.record(run_id, dataset_name, result.status, result.records_processed, result.watermark, result.error_message)
            return result

        summary = self.derived_builder.build()
        records_processed = int(
            1
            + int(summary.get("leader_candidate_count", 0) or 0)
            + int(summary.get("limit_event_count", 0) or 0)
            + 2
        )
        result = RunnerResult(dataset_name=dataset_name, status="succeeded", records_processed=records_processed, watermark=now)
        if run_id:
            self.run_store.record(run_id, dataset_name, result.status, result.records_processed, result.watermark, result.error_message)
        return result
