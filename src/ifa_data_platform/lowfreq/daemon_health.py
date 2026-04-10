"""Daemon health, status, and freshness reporting."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.lowfreq.daemon_config import DaemonConfig
from ifa_data_platform.lowfreq.run_state import RunStateManager


@dataclass
class GroupStatus:
    """Status for a single group."""

    group_name: str
    last_success_time: Optional[datetime]
    last_failure_time: Optional[datetime]
    last_status: str


@dataclass
class DaemonHealth:
    """Overall daemon health status."""

    status: str
    last_loop_time: Optional[datetime]
    config_loaded: bool
    group_statuses: dict[str, GroupStatus]
    dataset_freshness: dict[str, str]


def _get_memory_last_loop() -> Optional[datetime]:
    """Get last loop time from memory file."""
    memory_path = os.environ.get("LOWFREQ_DAEMON_MEMORY", "/tmp/ifa_daemon_memory.json")
    path = Path(memory_path)
    if not path.exists():
        return None

    try:
        import json

        with open(path) as f:
            data = json.load(f)
        loop_times = []
        for state in data.values():
            if state.get("last_success_time"):
                loop_times.append(datetime.fromisoformat(state["last_success_time"]))
        if loop_times:
            return max(loop_times)
    except Exception:
        pass

    return None


def get_group_status(config: DaemonConfig) -> dict[str, GroupStatus]:
    """Get status for each group based on run history."""
    run_manager = RunStateManager()
    statuses: dict[str, GroupStatus] = {}

    for group in config.groups:
        group_datasets = group.datasets
        latest_success = None
        latest_failure = None

        for ds in group_datasets:
            latest = run_manager.get_latest_for_dataset(ds)
            if latest:
                if latest.status == "succeeded":
                    if latest.completed_at and (
                        latest_success is None or latest.completed_at > latest_success
                    ):
                        latest_success = latest.completed_at
                elif latest.status == "failed":
                    if latest.completed_at and (
                        latest_failure is None or latest.completed_at > latest_failure
                    ):
                        latest_failure = latest.completed_at

        last_status = "unknown"
        if latest_success and latest_failure:
            last_status = "succeeded" if latest_success > latest_failure else "failed"
        elif latest_success:
            last_status = "succeeded"
        elif latest_failure:
            last_status = "failed"

        statuses[group.group_name] = GroupStatus(
            group_name=group.group_name,
            last_success_time=latest_success,
            last_failure_time=latest_failure,
            last_status=last_status,
        )

    return statuses


def _get_dataset_freshness(config: DaemonConfig) -> dict[str, str]:
    """Get freshness information for tracked datasets."""
    run_manager = RunStateManager()
    freshness: dict[str, str] = {}

    all_datasets = set()
    for group in config.groups:
        all_datasets.update(group.datasets)

    for ds in all_datasets:
        latest = run_manager.get_latest_for_dataset(ds)
        if latest and latest.completed_at:
            now = datetime.now(timezone.utc)
            completed_at = latest.completed_at
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            age = now - completed_at

            if age.total_seconds() < 3600:
                freshness[ds] = f"fresh (<1h, {latest.status})"
            elif age.total_seconds() < 86400:
                freshness[ds] = (
                    f"recent ({int(age.total_seconds() / 3600)}h, {latest.status})"
                )
            elif age.total_seconds() < 604800:
                freshness[ds] = (
                    f"stale ({int(age.total_seconds() / 86400)}d, {latest.status})"
                )
            else:
                freshness[ds] = (
                    f"very stale ({int(age.total_seconds() / 86400)}d, {latest.status})"
                )
        else:
            freshness[ds] = "no run recorded"

    return freshness


def get_daemon_health(config: DaemonConfig) -> DaemonHealth:
    """Get overall daemon health."""
    last_loop = _get_memory_last_loop()

    group_statuses = get_group_status(config)
    dataset_freshness = _get_dataset_freshness(config)

    status = "ok"
    if last_loop:
        now = datetime.now(timezone.utc)
        if (now - last_loop).total_seconds() > 3600:
            status = "stale"
    else:
        status = "no_runs"

    return DaemonHealth(
        status=status,
        last_loop_time=last_loop,
        config_loaded=True,
        group_statuses=group_statuses,
        dataset_freshness=dataset_freshness,
    )
