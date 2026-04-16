"""Daemon health, status, and freshness reporting.

Now DB-backed as primary source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.lowfreq.daemon_config import DaemonConfig
from ifa_data_platform.lowfreq.daemon_state import (
    DaemonStateStore,
    GroupStateStore,
    now_utc,
)
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


def get_group_status(config: DaemonConfig) -> dict[str, GroupStatus]:
    """Get status for each group from DB (primary source)."""
    group_store = GroupStateStore()
    run_manager = RunStateManager()
    statuses: dict[str, GroupStatus] = {}

    for group in config.groups:
        group_name = group.group_name
        db_state = group_store.get_group_state(group_name)

        last_success = db_state.get("last_success_at_utc")
        last_failure = None
        if db_state.get("last_status") == "failed":
            last_failure = db_state.get("last_run_at_utc")

        last_status = db_state.get("last_status", "unknown")

        statuses[group_name] = GroupStatus(
            group_name=group_name,
            last_success_time=last_success,
            last_failure_time=last_failure,
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
            now = now_utc()
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
    """Get overall daemon health from DB (primary source)."""
    daemon_store = DaemonStateStore()
    try:
        daemon_state = daemon_store.get_state()
        last_loop = daemon_state.get("last_loop_at_utc")
    except Exception:
        daemon_state = {}
        last_loop = None

    group_statuses = get_group_status(config)
    dataset_freshness = _get_dataset_freshness(config)

    any_group_activity = any(
        s.last_success_time is not None or s.last_failure_time is not None or s.last_status not in (None, "unknown")
        for s in group_statuses.values()
    )

    if last_loop is None and any_group_activity:
        candidate_times = [
            ts
            for s in group_statuses.values()
            for ts in (s.last_success_time, s.last_failure_time)
            if ts is not None
        ]
        if candidate_times:
            last_loop = max(candidate_times)

    status = "ok"
    now = now_utc()
    if last_loop:
        if last_loop.tzinfo is None:
            last_loop = last_loop.replace(tzinfo=timezone.utc)
        elapsed_seconds = (now - last_loop).total_seconds()
        any_degraded = any(s.last_status in {"failed", "degraded", "retrying"} for s in group_statuses.values())
        if any_degraded:
            status = "degraded"
        elif elapsed_seconds > 3600 * 24:
            status = "stale"
        else:
            status = "ok"
    elif daemon_state.get("last_success_at_utc") or any_group_activity:
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
