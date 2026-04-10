"""Daemon group orchestration module."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.lowfreq.daemon_config import DaemonConfig, GroupConfig
from ifa_data_platform.lowfreq.models import RunState
from ifa_data_platform.lowfreq.registry import DatasetRegistry
from ifa_data_platform.lowfreq.runner import LowFreqRunner

logger = logging.getLogger(__name__)


@dataclass
class DatasetResult:
    """Result of executing a single dataset within a group."""

    dataset_name: str
    status: str
    records_processed: int = 0
    error_message: Optional[str] = None


@dataclass
class GroupExecutionSummary:
    """Summary of group execution."""

    group_name: str
    started_at: datetime
    completed_at: datetime
    total_datasets: int
    succeeded_datasets: int
    failed_datasets: int
    dataset_results: list[DatasetResult] = field(default_factory=list)
    window_type: str = ""
    skipped: bool = False
    degraded: bool = False
    reason: Optional[str] = None

    @property
    def all_succeeded(self) -> bool:
        return self.succeeded_datasets == self.total_datasets and not self.skipped


class DaemonOrchestrator:
    """Orchestrates execution of dataset groups for the daemon."""

    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.runner = LowFreqRunner()
        self.registry = DatasetRegistry()

    def run_group(self, group_name: str) -> GroupExecutionSummary:
        """Execute all datasets in a group sequentially.

        Args:
            group_name: Name of the group to execute.

        Returns:
            GroupExecutionSummary with results.
        """
        group = self.config.get_group(group_name)
        if group is None:
            logger.warning(f"Group not found: {group_name}")
            return GroupExecutionSummary(
                group_name=group_name,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                total_datasets=0,
                succeeded_datasets=0,
                failed_datasets=0,
                reason=f"Group not found: {group_name}",
            )

        logger.info(
            f"Starting group execution: {group_name} ({len(group.datasets)} datasets)"
        )

        started_at = datetime.now(timezone.utc)
        results: list[DatasetResult] = []

        for dataset_name in group.datasets:
            result = self._run_dataset(dataset_name)
            results.append(result)
            if result.status == "failed":
                logger.error(f"Dataset {dataset_name} failed: {result.error_message}")

        completed_at = datetime.now(timezone.utc)

        succeeded = sum(1 for r in results if r.status == "succeeded")
        failed = sum(1 for r in results if r.status == "failed")

        summary = GroupExecutionSummary(
            group_name=group_name,
            started_at=started_at,
            completed_at=completed_at,
            total_datasets=len(group.datasets),
            succeeded_datasets=succeeded,
            failed_datasets=failed,
            dataset_results=results,
        )

        logger.info(
            f"Group {group_name} completed: {succeeded}/{len(group.datasets)} succeeded, "
            f"{failed} failed"
        )

        return summary

    def _run_dataset(self, dataset_name: str) -> DatasetResult:
        """Run a single dataset, catching exceptions to not crash the daemon.

        Args:
            dataset_name: Name of the dataset to run.

        Returns:
            DatasetResult with execution status.
        """
        try:
            state = self.runner.run(
                dataset_name=dataset_name,
                dry_run=False,
                run_type="daemon",
            )

            return DatasetResult(
                dataset_name=dataset_name,
                status=state.status,
                records_processed=state.records_processed,
                error_message=state.error_message,
            )

        except Exception as e:
            logger.error(f"Exception running dataset {dataset_name}: {e}")
            return DatasetResult(
                dataset_name=dataset_name,
                status="failed",
                records_processed=0,
                error_message=str(e),
            )
