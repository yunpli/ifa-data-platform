"""Archive orchestrator module."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.archive.archive_config import ArchiveConfig
from ifa_data_platform.archive.archive_checkpoint import ArchiveCheckpointStore
from ifa_data_platform.archive.models import ArchiveJob
from ifa_data_platform.archive.archive_run_store import ArchiveRunStore
from ifa_data_platform.archive.archive_summary import ArchiveSummaryStore
from ifa_data_platform.archive.archive_daemon_state import ArchiveDaemonStateStore

logger = logging.getLogger(__name__)


@dataclass
class ArchiveJobResult:
    """Result of executing a single archive job."""

    job_name: str
    dataset_name: str
    status: str
    records_processed: int = 0
    error_message: Optional[str] = None


@dataclass
class ArchiveExecutionSummary:
    """Summary of archive execution."""

    window_name: str
    started_at: datetime
    completed_at: datetime
    total_jobs: int
    succeeded_jobs: int
    failed_jobs: int
    job_results: list[ArchiveJobResult] = field(default_factory=list)
    skipped: bool = False


class ArchiveOrchestrator:
    """Orchestrates execution of archive jobs."""

    def __init__(self, config: ArchiveConfig) -> None:
        self.config = config
        self.run_store = ArchiveRunStore()
        self.checkpoint_store = ArchiveCheckpointStore()
        self.summary_store = ArchiveSummaryStore()
        self.daemon_store = ArchiveDaemonStateStore()

    def run_window(
        self, window_name: str, dry_run: bool = False
    ) -> ArchiveExecutionSummary:
        """Execute all enabled jobs within a window.

        Args:
            window_name: Name of the window to execute.
            dry_run: If True, simulate execution without actual processing.

        Returns:
            ArchiveExecutionSummary with results.
        """
        logger.info(f"Starting archive window: {window_name}")

        enabled_jobs = self.config.get_enabled_jobs()
        if not enabled_jobs:
            logger.warning(f"No enabled jobs configured")
            return ArchiveExecutionSummary(
                window_name=window_name,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                total_jobs=0,
                succeeded_jobs=0,
                failed_jobs=0,
                skipped=True,
            )

        started_at = datetime.now(timezone.utc)
        results: list[ArchiveJobResult] = []

        for job_config in enabled_jobs:
            result = self._run_job(job_config, window_name, dry_run)
            results.append(result)
            if result.status == "failed":
                logger.error(
                    f"Job {job_config.job_name} failed: {result.error_message}"
                )

        completed_at = datetime.now(timezone.utc)

        succeeded = sum(1 for r in results if r.status == "succeeded")
        failed = sum(1 for r in results if r.status == "failed")
        total_records = sum(r.records_processed for r in results)

        summary = ArchiveExecutionSummary(
            window_name=window_name,
            started_at=started_at,
            completed_at=completed_at,
            total_jobs=len(enabled_jobs),
            succeeded_jobs=succeeded,
            failed_jobs=failed,
            job_results=results,
        )

        self._persist_summary(summary)

        last_job = enabled_jobs[-1].job_name if enabled_jobs else None
        last_status = "succeeded" if failed == 0 else "failed"
        self.daemon_store.update_loop(last_job, last_status)

        logger.info(
            f"Window {window_name} completed: {succeeded}/{len(enabled_jobs)} succeeded, "
            f"{failed} failed, {total_records} records"
        )

        return summary

    def _run_job(self, job_config, window_name: str, dry_run: bool) -> ArchiveJobResult:
        """Run a single archive job, catching exceptions."""
        job_name = job_config.job_name
        dataset_name = job_config.dataset_name
        asset_type = job_config.asset_type

        run_id = self.run_store.create_run(
            job_name=job_name,
            dataset_name=dataset_name,
            asset_type=asset_type,
            window_name=window_name,
        )

        try:
            if dry_run:
                records = 0
            else:
                records = self._process_job(
                    job_name, dataset_name, asset_type, window_name
                )

            self.run_store.update_status(
                run_id=run_id,
                status="succeeded",
                records_processed=records,
            )

            return ArchiveJobResult(
                job_name=job_name,
                dataset_name=dataset_name,
                status="succeeded",
                records_processed=records,
            )

        except Exception as e:
            logger.error(f"Exception running job {job_name}: {e}")
            self.run_store.update_status(
                run_id=run_id,
                status="failed",
                error_message=str(e),
            )
            return ArchiveJobResult(
                job_name=job_name,
                dataset_name=dataset_name,
                status="failed",
                records_processed=0,
                error_message=str(e),
            )

    def _process_job(
        self, job_name: str, dataset_name: str, asset_type: str, window_name: str
    ) -> int:
        """Process a single archive job.

        Routes to asset-specific archiver implementations.
        D2: Stock daily historical archive.
        Milestone A: commodity / precious_metal promoted into explicit runtime jobs.
        """
        if dataset_name == "stock_daily":
            return self._process_stock_job(dataset_name)
        if dataset_name == "stock_15min_history":
            return self._process_stock_15min_job(dataset_name)
        if dataset_name == "stock_minute_history":
            return self._process_stock_minute_job(dataset_name)
        if dataset_name == "futures_history":
            return self._process_commodity_family_job(dataset_name, asset_type={"futures"}, checkpoint_asset_type="futures")
        if dataset_name == "futures_15min_history":
            return self._process_futures_intraday_job(dataset_name, asset_type="futures", category_filter={"metals"}, freq="15min")
        if dataset_name == "futures_minute_history":
            return self._process_futures_intraday_job(dataset_name, asset_type="futures", category_filter={"metals"}, freq="1min")
        if dataset_name == "commodity_history":
            return self._process_commodity_family_job(dataset_name, asset_type={"commodity", "chemical", "agricultural", "energy", "base_metal", "metals"}, checkpoint_asset_type="commodity")
        if dataset_name == "commodity_15min_history":
            return self._process_futures_intraday_job(dataset_name, asset_type="commodity", category_filter={"commodity", "chemical", "agricultural", "energy", "base_metal", "metals"}, freq="15min")
        if dataset_name == "commodity_minute_history":
            return self._process_futures_intraday_job(dataset_name, asset_type="commodity", category_filter={"commodity", "chemical", "agricultural", "energy", "base_metal", "metals"}, freq="1min")
        if dataset_name == "precious_metal_history":
            return self._process_commodity_family_job(dataset_name, asset_type={"precious_metal"}, checkpoint_asset_type="precious_metal")
        if dataset_name == "precious_metal_15min_history":
            return self._process_futures_intraday_job(dataset_name, asset_type="precious_metal", category_filter={"precious_metal"}, freq="15min")
        if dataset_name == "precious_metal_minute_history":
            return self._process_futures_intraday_job(dataset_name, asset_type="precious_metal", category_filter={"precious_metal"}, freq="1min")
        if dataset_name == "macro_15min_history":
            raise NotImplementedError("macro 15min archive has no real source/storage path in current repo")
        if dataset_name == "macro_minute_history":
            raise NotImplementedError("macro minute archive has no real source/storage path in current repo")
        if asset_type == "macro":
            return self._process_generic_job(job_name, dataset_name, asset_type)

        return self._process_generic_job(job_name, dataset_name, asset_type)

    def _process_stock_job(self, dataset_name: str) -> int:
        """Process stock daily archive job using real Tushare data."""
        from ifa_data_platform.archive.stock_daily_archiver import StockDailyArchiver
        from datetime import date, timedelta

        archiver = StockDailyArchiver()

        try:
            records = archiver.run_archive(
                dataset_name=dataset_name,
                end_date=date.today() - timedelta(days=1),
                limit_per_stock=20,
            )
            logger.info(f"Stock archive completed: {records} records")
            return records
        except Exception as e:
            logger.error(f"Stock archive failed: {e}")
            raise

    def _process_stock_15min_job(self, dataset_name: str) -> int:
        """Process stock 15min archive job using real Tushare intraday bars."""
        from datetime import date, datetime, time, timedelta
        from ifa_data_platform.archive.stock_15min_archiver import Stock15MinArchiver

        archiver = Stock15MinArchiver()
        end_time = datetime.combine(date.today() - timedelta(days=1), time(15, 0, 0))

        try:
            records = archiver.run_archive(
                dataset_name=dataset_name,
                end_time=end_time,
                limit_stocks=5,
            )
            logger.info(f"Stock 15min archive completed: {records} records")
            return records
        except Exception as e:
            logger.error(f"Stock 15min archive failed: {e}")
            raise

    def _process_stock_minute_job(self, dataset_name: str) -> int:
        """Process stock minute archive via Tushare stk_mins."""
        from datetime import date, datetime, time, timedelta
        from ifa_data_platform.archive.stock_minute_archiver import StockMinuteArchiver

        archiver = StockMinuteArchiver()
        end_time = datetime.combine(date.today() - timedelta(days=1), time(15, 0, 0))
        records = archiver.run_archive(
            dataset_name=dataset_name,
            end_time=end_time,
            limit_stocks=5,
        )
        logger.info(f"Stock minute archive completed: {records} records")
        return records

    def _process_futures_intraday_job(
        self, dataset_name: str, asset_type: str, category_filter: set[str], freq: str
    ) -> int:
        """Process futures-family intraday archive job using ft_mins."""
        from datetime import date, datetime, time, timedelta
        from ifa_data_platform.archive.futures_intraday_archiver import (
            FuturesIntradayArchiver,
        )

        archiver = FuturesIntradayArchiver()
        end_time = datetime.combine(date.today() - timedelta(days=1), time(15, 0, 0))
        records = archiver.run_archive(
            dataset_name=dataset_name,
            asset_type=asset_type,
            category_filter=category_filter,
            freq=freq,
            end_time=end_time,
            max_contracts=8,
        )
        logger.info(f"{dataset_name} archive completed: {records} records")
        return records

    def _process_commodity_family_job(
        self, dataset_name: str, asset_type: set[str], checkpoint_asset_type: str
    ) -> int:
        """Process commodity-family archive jobs through the commodity archiver with category filters."""
        from datetime import date, timedelta
        from ifa_data_platform.archive.commodity_archiver import CommodityArchiver

        archiver = CommodityArchiver()
        return archiver.run_archive(
            dataset_name=dataset_name,
            end_date=date.today() - timedelta(days=1),
            max_contracts=20,
            category_filter=asset_type,
            asset_type=checkpoint_asset_type,
        )

    def _process_generic_job(
        self, job_name: str, dataset_name: str, asset_type: str
    ) -> int:
        """Generic fallback job processor."""
        from datetime import date, timedelta

        checkpoint = self.checkpoint_store.get_checkpoint(dataset_name, asset_type)

        last_date = None
        if checkpoint and checkpoint.get("last_completed_date"):
            last_date = checkpoint["last_completed_date"]

        is_15min = dataset_name.endswith("15min_history")

        if last_date:
            current_date = last_date + (timedelta(minutes=15) if is_15min else timedelta(days=1))
        else:
            current_date = date.today() - timedelta(days=365)

        records_processed = 0
        batch_no = 0
        while current_date <= date.today():
            batch_no += 1

            self.checkpoint_store.update_progress(
                dataset_name=dataset_name,
                asset_type=asset_type,
                last_completed_date=current_date,
                batch_no=batch_no,
                status="in_progress",
            )

            records_processed += 1
            current_date += timedelta(days=1)

            if batch_no >= (8 if is_15min else 5):
                break

        if records_processed > 0:
            self.checkpoint_store.mark_completed(dataset_name, asset_type)

        return records_processed

    def _persist_summary(self, summary: ArchiveExecutionSummary) -> None:
        """Persist summary to DB."""
        from datetime import date

        summary_date = summary.started_at.date()
        status = "completed"
        if summary.failed_jobs > 0 and summary.succeeded_jobs == 0:
            status = "failed"
        elif summary.failed_jobs > 0:
            status = "partial"

        self.summary_store.upsert_summary(
            summary_date=summary_date,
            window_name=summary.window_name,
            total_jobs=summary.total_jobs,
            succeeded_jobs=summary.succeeded_jobs,
            failed_jobs=summary.failed_jobs,
            total_records=sum(r.records_processed for r in summary.job_results),
            status=status,
        )
