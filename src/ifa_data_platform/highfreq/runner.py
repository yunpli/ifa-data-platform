"""Highfreq runner skeleton for milestone 1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

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

    def run(self, dataset_name: str, dry_run: bool = False) -> RunnerResult:
        now = datetime.now(timezone.utc).isoformat()
        enabled = {d.dataset_name for d in self.registry.list_enabled()}
        if dataset_name not in enabled:
            return RunnerResult(
                dataset_name=dataset_name,
                status="unsupported",
                records_processed=0,
                watermark=now,
                error_message="dataset_not_enabled_or_not_verified",
            )
        return RunnerResult(
            dataset_name=dataset_name,
            status="skeleton_ready" if dry_run else "skeleton_ready",
            records_processed=0,
            watermark=now,
        )
