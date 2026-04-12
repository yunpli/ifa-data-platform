"""Daemon orchestrator for midfreq."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.midfreq.daemon_config import DaemonConfig, GroupConfig
from ifa_data_platform.midfreq.runner import MidfreqRunner, RunnerResult

logger = logging.getLogger(__name__)


@dataclass
class DatasetResult:
    """Result of a single dataset execution."""

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
    dataset_results: list[DatasetResult]
    window_type: str
    skipped: bool = False
    degraded: bool = False

    @property
    def all_succeeded(self) -> bool:
        return self.failed_datasets == 0 and not self.skipped

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(
            {
                "group_name": self.group_name,
                "started_at": self.started_at.isoformat(),
                "completed_at": self.completed_at.isoformat(),
                "total_datasets": self.total_datasets,
                "succeeded_datasets": self.succeeded_datasets,
                "failed_datasets": self.failed_datasets,
                "window_type": self.window_type,
                "skipped": self.skipped,
                "degraded": self.degraded,
                "dataset_results": [
                    {
                        "dataset_name": r.dataset_name,
                        "status": r.status,
                        "records_processed": r.records_processed,
                        "error_message": r.error_message,
                    }
                    for r in self.dataset_results
                ],
            }
        )


class DaemonOrchestrator:
    """Orchestrates dataset execution for groups."""

    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.runner = MidfreqRunner()

    def run_group(self, group_name: str) -> GroupExecutionSummary:
        """Run all datasets in a group."""
        started_at = datetime.now(timezone.utc)

        group = self.config.get_group(group_name)
        if not group:
            logger.warning(f"Group not found: {group_name}")
            return GroupExecutionSummary(
                group_name=group_name,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                total_datasets=0,
                succeeded_datasets=0,
                failed_datasets=0,
                dataset_results=[],
                window_type=group_name,
            )

        dataset_results = []
        succeeded_count = 0
        failed_count = 0

        for dataset_name in group.datasets:
            try:
                result = self.runner.run(dataset_name)
                dataset_results.append(
                    DatasetResult(
                        dataset_name=dataset_name,
                        status=result.status,
                        records_processed=result.records_processed,
                        error_message=result.error_message,
                    )
                )
                if result.status == "succeeded":
                    succeeded_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to run {dataset_name}: {e}")
                dataset_results.append(
                    DatasetResult(
                        dataset_name=dataset_name,
                        status="failed",
                        records_processed=0,
                        error_message=str(e),
                    )
                )
                failed_count += 1

        return GroupExecutionSummary(
            group_name=group_name,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            total_datasets=len(group.datasets),
            succeeded_datasets=succeeded_count,
            failed_datasets=failed_count,
            dataset_results=dataset_results,
            window_type=group_name,
        )
