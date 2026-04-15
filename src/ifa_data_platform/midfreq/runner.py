"""Runner module for mid-frequency dataset ingestion."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.midfreq.adaptor_factory import get_midfreq_adaptor
from ifa_data_platform.midfreq.models import RunState
from ifa_data_platform.midfreq.registry import MidfreqDatasetRegistry
from ifa_data_platform.midfreq.version_persistence import DatasetVersionRegistry

logger = logging.getLogger(__name__)


class RunnerResult:
    """Result of a runner execution."""

    def __init__(
        self,
        run_id: str,
        dataset_name: str,
        status: str,
        records_processed: int,
        watermark: Optional[str] = None,
        error_message: Optional[str] = None,
        version_id: Optional[str] = None,
    ) -> None:
        self.run_id = run_id
        self.dataset_name = dataset_name
        self.status = status
        self.records_processed = records_processed
        self.watermark = watermark
        self.error_message = error_message
        self.version_id = version_id


class MidfreqRunner:
    """Runner for mid-frequency datasets."""

    def __init__(
        self,
        source_name: str = "tushare",
    ) -> None:
        self.source_name = source_name
        self.adaptor = get_midfreq_adaptor(source_name)
        self.dataset_registry = MidfreqDatasetRegistry()
        self.version_registry = DatasetVersionRegistry()

    def run(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
    ) -> RunnerResult:
        """Run ingestion for a single dataset.

        Args:
            dataset_name: Name of the dataset to run.
            watermark: Optional watermark (trade_date).
            limit: Optional record limit.
            dry_run: If True, don't persist to database.

        Returns:
            RunnerResult with execution details.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        logger.info(f"Starting midfreq run {run_id} for {dataset_name}")

        version_id: Optional[str] = None
        if not dry_run:
            version_id = self.version_registry.create_version(
                dataset_name=dataset_name,
                source_name=self.source_name,
                run_id=run_id,
                watermark=watermark,
            )

        try:
            fetch_result = self.adaptor.fetch(
                dataset_name=dataset_name,
                watermark=watermark,
                limit=limit,
                run_id=run_id,
                source_name=self.source_name,
                version_id=version_id,
            )

            records_processed = len(fetch_result.records)
            watermark = fetch_result.watermark

            if dry_run:
                logger.info(
                    f"[DRY RUN] {dataset_name}: {records_processed} records fetched"
                )
                return RunnerResult(
                    run_id=run_id,
                    dataset_name=dataset_name,
                    status="dry_run",
                    records_processed=records_processed,
                    watermark=watermark,
                )

            logger.info(f"{dataset_name}: {records_processed} records processed")

            if records_processed > 0 and version_id:
                self.version_registry.promote(dataset_name, version_id)
                self._persist_current_to_history(dataset_name, version_id)

            return RunnerResult(
                run_id=run_id,
                dataset_name=dataset_name,
                status="succeeded",
                records_processed=records_processed,
                watermark=watermark,
                version_id=version_id,
            )

        except Exception as e:
            logger.error(f"Failed to run {dataset_name}: {e}")
            return RunnerResult(
                run_id=run_id,
                dataset_name=dataset_name,
                status="failed",
                records_processed=0,
                error_message=str(e),
                version_id=version_id,
            )

    def register_datasets(self) -> None:
        """Register midfreq datasets if not already registered."""
        datasets = [
            {
                "dataset_name": "equity_daily_bar",
                "description": "A-share equity daily OHLCV for B Universe",
            },
            {
                "dataset_name": "index_daily_bar",
                "description": "Index daily OHLCV",
            },
            {
                "dataset_name": "etf_daily_bar",
                "description": "ETF daily OHLCV",
            },
            {
                "dataset_name": "northbound_flow",
                "description": "Northbound (HK->CN) capital flow",
            },
            {
                "dataset_name": "limit_up_down_status",
                "description": "Limit up/down market status",
            },
        ]

        for ds in datasets:
            from ifa_data_platform.midfreq.models import (
                DatasetConfig,
                JobType,
                Market,
                RunnerType,
                TimezoneSemantics,
                WatermarkStrategy,
            )

            config = DatasetConfig(
                dataset_name=ds["dataset_name"],
                market=Market.CHINA_A_SHARE,
                source_name=self.source_name,
                job_type=JobType.INCREMENTAL,
                enabled=True,
                timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
                runner_type=RunnerType.TUSHARE,
                watermark_strategy=WatermarkStrategy.DATE_BASED,
                metadata={
                    "source_of_truth": self.source_name,
                    "registered_by": "MidfreqRunner.register_datasets",
                },
                description=ds["description"],
            )

            self.dataset_registry.register(config)
            logger.info(f"Registered midfreq dataset: {ds['dataset_name']}")

    def _persist_current_to_history(self, dataset_name: str, version_id: str) -> int:
        """Copy current records to history table for versioning."""
        from sqlalchemy import text
        from ifa_data_platform.db.engine import make_engine

        engine = make_engine()
        table_map = {
            "equity_daily_bar": (
                "equity_daily_bar_current",
                "equity_daily_bar_history",
            ),
            "index_daily_bar": ("index_daily_bar_current", "index_daily_bar_history"),
            "etf_daily_bar": ("etf_daily_bar_current", "etf_daily_bar_history"),
            "northbound_flow": ("northbound_flow_current", "northbound_flow_history"),
            "limit_up_down_status": (
                "limit_up_down_status_current",
                "limit_up_down_status_history",
            ),
            "margin_financing": (
                "margin_financing_current",
                "margin_financing_history",
            ),
            "turnover_rate": ("turnover_rate_current", "turnover_rate_history"),
            "limit_up_detail": ("limit_up_detail_current", "limit_up_detail_history"),
            "southbound_flow": ("southbound_flow_current", "southbound_flow_history"),
            "main_force_flow": ("main_force_flow_current", "main_force_flow_history"),
            "sector_performance": (
                "sector_performance_current",
                "sector_performance_history",
            ),
            "dragon_tiger_list": (
                "dragon_tiger_list_current",
                "dragon_tiger_list_history",
            ),
        }

        if dataset_name not in table_map:
            logger.warning(f"No history mapping for {dataset_name}")
            return 0

        current_table, history_table = table_map[dataset_name]

        with engine.begin() as conn:
            result = conn.execute(
                text(f"""
                    INSERT INTO ifa2.{history_table} (id, version_id, 
                        {self._get_columns_for_history(dataset_name)})
                    SELECT gen_random_uuid(), :version_id,
                        {self._get_columns_for_insert(dataset_name)}
                    FROM ifa2.{current_table}
                    WHERE version_id = :version_id
                """),
                {"version_id": version_id},
            )
            return result.rowcount

    def _get_columns_for_history(self, dataset_name: str) -> str:
        """Get column list for history insert."""
        column_maps = {
            "equity_daily_bar": "ts_code, trade_date, open, high, low, close, vol, amount, pre_close, change, pct_chg",
            "index_daily_bar": "ts_code, trade_date, open, high, low, close, vol, amount, pre_close, change, pct_chg",
            "etf_daily_bar": "ts_code, trade_date, open, high, low, close, vol, amount, pre_close, change, pct_chg",
            "northbound_flow": "trade_date, north_money, north_bal, north_buy, north_sell",
            "limit_up_down_status": "trade_date, limit_up_count, limit_down_count, limit_up_streak_high, limit_down_streak_high",
            "margin_financing": "ts_code, trade_date, rzye, rzmre, rzche, rzrqye, rqryl",
            "turnover_rate": "ts_code, trade_date, turnover_rate, turnover_rate_f",
            "limit_up_detail": "ts_code, trade_date, limit, pre_limit",
            "southbound_flow": "trade_date, south_money, south_bal, south_buy, south_sell",
            "main_force_flow": "ts_code, trade_date, main_force, main_force_pct",
            "sector_performance": "sector_code, trade_date, sector_name, close, pct_chg, turnover_rate",
            "dragon_tiger_list": "ts_code, trade_date, buy_amount, sell_amount, net_amount",
        }
        return column_maps.get(dataset_name, "*")

    def _get_columns_for_insert(self, dataset_name: str) -> str:
        """Get column list for history insert."""
        return self._get_columns_for_history(dataset_name)
