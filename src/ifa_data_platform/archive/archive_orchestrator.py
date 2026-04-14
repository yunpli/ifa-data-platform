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

        try:
            if dry_run:
                records = 0
            else:
                records = self._process_job(
                    job_name, dataset_name, asset_type, window_name
                )

            return ArchiveJobResult(
                job_name=job_name,
                dataset_name=dataset_name,
                status="succeeded",
                records_processed=records,
            )

        except Exception as e:
            logger.error(f"Exception running job {job_name}: {e}")
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

        This is a placeholder implementation that demonstrates the checkpoint/resume chain.
        Real implementation would wire to actual data sources in D2+.
        """
        checkpoint = self.checkpoint_store.get_checkpoint(dataset_name, asset_type)

        last_date = None
        if checkpoint and checkpoint.get("last_completed_date"):
            last_date = checkpoint["last_completed_date"]

        from datetime import date, timedelta

        if last_date:
            current_date = last_date + timedelta(days=1)
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

            if batch_no >= 5:
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
