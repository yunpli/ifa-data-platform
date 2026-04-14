"""Archive health monitoring module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.archive.archive_config import ArchiveConfig
from ifa_data_platform.archive.archive_daemon_state import ArchiveDaemonStateStore
from ifa_data_platform.archive.archive_checkpoint import ArchiveCheckpointStore
from ifa_data_platform.archive.archive_summary import ArchiveSummaryStore


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ArchiveHealth:
    """Archive health status."""

    status: str
    is_running: bool
    last_run_time: Optional[datetime]
    latest_run_status: Optional[str]
    checkpoint_advanced: bool
    message: str


def get_archive_health(config: ArchiveConfig) -> ArchiveHealth:
    """Get archive health status from DB (primary source)."""
    daemon_store = ArchiveDaemonStateStore()
    checkpoint_store = ArchiveCheckpointStore()
    summary_store = ArchiveSummaryStore()

    daemon_state = daemon_store.get_state()
    last_loop = daemon_state.get("last_loop_at_utc")
    is_running = daemon_state.get("is_running", False)
    last_status = daemon_state.get("last_run_status")

    latest_summary = summary_store.get_recent_summary()
    if latest_summary:
        latest_run_status = latest_summary.get("status")
    else:
        latest_run_status = None

    checkpoints = checkpoint_store.list_checkpoints()
    checkpoint_advanced = False
    for cp in checkpoints:
        if cp.get("last_completed_date"):
            checkpoint_advanced = True
            break

    if is_running:
        status = "running"
        message = "Archive daemon is currently running"
    elif last_loop is None and not checkpoints:
        status = "no_runs"
        message = "No archive runs recorded"
    elif last_loop:
        now = now_utc()
        if last_loop.tzinfo is None:
            last_loop = last_loop.replace(tzinfo=timezone.utc)
        if (now - last_loop).total_seconds() > 7200:
            status = "stale"
            message = f"No runs in {(now - last_loop).total_seconds() / 3600:.1f} hours"
        else:
            status = "ok"
            message = "Archive is healthy"
    else:
        status = "unknown"
        message = "Cannot determine status"

    return ArchiveHealth(
        status=status,
        is_running=is_running,
        last_run_time=last_loop,
        latest_run_status=latest_run_status,
        checkpoint_advanced=checkpoint_advanced,
        message=message,
    )


@dataclass
class ArchiveWatchdog:
    """Archive watchdog to check if archiver is running/stale."""

    is_alive: bool
    is_stale: bool
    last_run_time: Optional[datetime]
    message: str


def check_archive_watchdog(config: ArchiveConfig) -> ArchiveWatchdog:
    """Check if archive daemon is alive and responsive."""
    daemon_store = ArchiveDaemonStateStore()

    state = daemon_store.get_state()
    last_loop = state.get("last_loop_at_utc")

    if last_loop is None:
        return ArchiveWatchdog(
            is_alive=False,
            is_stale=True,
            last_run_time=None,
            message="No archive runs recorded",
        )

    now = now_utc()
    if last_loop.tzinfo is None:
        last_loop = last_loop.replace(tzinfo=timezone.utc)
    elapsed = (now - last_loop).total_seconds()

    is_alive = elapsed < 7200
    is_stale = elapsed > 7200

    if is_alive:
        message = f"Archive is alive, last run {elapsed / 60:.0f}m ago"
    else:
        message = f"Archive is stale, no run in {elapsed / 3600:.1f} hours"

    return ArchiveWatchdog(
        is_alive=is_alive,
        is_stale=is_stale,
        last_run_time=last_loop,
        message=message,
    )
