"""Daemon orchestrator for highfreq lane."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.highfreq.daemon_config import DaemonConfig
from ifa_data_platform.highfreq.runner import HighfreqRunner


@dataclass
class DatasetResult:
    dataset_name: str
    status: str
    records_processed: int = 0
    error_message: Optional[str] = None


@dataclass
class GroupExecutionSummary:
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
    duration_ms: int = 0
    sla_status: str = "ok"

    @property
    def all_succeeded(self) -> bool:
        return self.failed_datasets == 0 and not self.skipped

    def to_json(self) -> str:
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
                "reason": self.reason,
                "dataset_results": [r.__dict__ for r in self.dataset_results],
            }
        )


class DaemonOrchestrator:
    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.runner = HighfreqRunner()

    def run_group(self, group_name: str) -> GroupExecutionSummary:
        group = self.config.get_group(group_name)
        started_at = datetime.now(timezone.utc)
        started_monotonic = time.perf_counter()
        if not group:
            return GroupExecutionSummary(
                group_name=group_name,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                total_datasets=0,
                succeeded_datasets=0,
                failed_datasets=0,
                reason=f"group_not_found:{group_name}",
                duration_ms=0,
                sla_status="partial",
            )
        results = []
        ok = 0
        failed = 0
        run_id = str(uuid.uuid4())
        for dataset_name in group.datasets:
            result = self.runner.run(dataset_name, run_id=run_id)
            status = result.status
            results.append(DatasetResult(dataset_name, status, result.records_processed, result.error_message))
            if status in {"skeleton_ready", "succeeded", "dry_run"}:
                ok += 1
            else:
                failed += 1
        duration_ms = int((time.perf_counter() - started_monotonic) * 1000)
        sla_status = "ok"
        if failed > 0:
            sla_status = "partial"
        elif duration_ms > 120000:
            sla_status = "delayed"
        elif duration_ms > 60000:
            sla_status = "degraded"
        return GroupExecutionSummary(
            group_name=group_name,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            total_datasets=len(group.datasets),
            succeeded_datasets=ok,
            failed_datasets=failed,
            dataset_results=results,
            window_type=group_name,
            duration_ms=duration_ms,
            sla_status=sla_status,
            degraded=sla_status in {"degraded", "delayed", "partial"},
        )
