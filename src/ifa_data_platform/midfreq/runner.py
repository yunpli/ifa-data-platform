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
                # Note: SQL uses boolean but we pass 1 for INTEGER
                timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
                runner_type=RunnerType.TUSHARE,
                watermark_strategy=WatermarkStrategy.DATE_BASED,
                description=ds["description"],
            )

            self.dataset_registry.register(config)
            logger.info(f"Registered midfreq dataset: {ds['dataset_name']}")
