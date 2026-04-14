"""Archive daemon for iFA Archive Layer.

A separate line for long-term asset accumulation and backfill.
NOT for same-day report production.

Runs in night windows that do not compete with lowfreq/midfreq production.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timedelta, timezone

from ifa_data_platform.archive.archive_config import (
    ArchiveConfig,
    get_archive_config,
)
from ifa_data_platform.archive.archive_daemon_state import ArchiveDaemonStateStore
from ifa_data_platform.archive.archive_health import (
    get_archive_health,
    check_archive_watchdog,
)
from ifa_data_platform.archive.archive_orchestrator import (
    ArchiveOrchestrator,
    ArchiveExecutionSummary,
)
from ifa_data_platform.archive.archive_summary import ArchiveSummaryStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] archive: %(message)s",
)
logger = logging.getLogger(__name__)


def _business_date(config: ArchiveConfig, now: datetime) -> datetime.date:
    """Return the business date in archive timezone."""
    return now.astimezone(config.timezone).date()


def _seconds_until_next_window(config: ArchiveConfig, now: datetime) -> int:
    """Compute seconds until the next enabled window start in archive timezone."""
    current_local = now.astimezone(config.timezone)
    candidates: list[datetime] = []

    for window in config.windows:
        if not window.is_enabled:
            continue
        start_time = datetime.strptime(window.start_time, "%H:%M").time()
        candidate = datetime.combine(
            current_local.date(),
            start_time,
            tzinfo=config.timezone,
        )
        if candidate <= current_local:
            candidate = candidate + timedelta(days=1)
        candidates.append(candidate)

    if not candidates:
        return max(config.loop_interval_sec, 300)

    next_start = min(candidates)
    wait_seconds = int((next_start - current_local).total_seconds())
    return max(wait_seconds, config.loop_interval_sec)


def _signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received signal %d, initiating shutdown...", signum)
    daemon_store = ArchiveDaemonStateStore()
    daemon_store.mark_running(False)
    sys.exit(0)


def run_once(
    config: ArchiveConfig, current_time_override: datetime = None
) -> ArchiveExecutionSummary:
    """Execute one iteration of the daemon (--once mode)."""
    orchestrator = ArchiveOrchestrator(config)
    daemon_store = ArchiveDaemonStateStore()
    summary_store = ArchiveSummaryStore()

    now = current_time_override or datetime.now(timezone.utc)
    current_time = now.astimezone(config.timezone)
    business_date = _business_date(config, now)

    logger.info(f"Running archive daemon in --once mode at {current_time.isoformat()}")

    window = config.get_matching_window(current_time)
    if window is None:
        logger.info("No matching schedule window for current time, exiting.")
        return None

    logger.info(f"Matched window: {window.window_name}")

    existing = summary_store.get_summary(business_date, window.window_name)
    if existing and existing.get("status") in {"completed", "partial"}:
        logger.info(
            "Window %s already executed for %s, skipping duplicate run.",
            window.window_name,
            business_date,
        )
        return None

    daemon_store.mark_running(True)
    try:
        summary = orchestrator.run_window(window.window_name, dry_run=False)
    finally:
        daemon_store.mark_running(False)

    if summary and summary.succeeded_jobs > 0:
        daemon_store.mark_success(f"window_{summary.window_name}")
    elif summary and summary.failed_jobs > 0:
        daemon_store.mark_failed(f"window_{summary.window_name}")

    return summary


def run_loop(config: ArchiveConfig) -> None:
    """Run daemon in continuous loop mode."""
    orchestrator = ArchiveOrchestrator(config)
    daemon_store = ArchiveDaemonStateStore()
    summary_store = ArchiveSummaryStore()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    active_poll_sec = min(config.loop_interval_sec, 60)
    logger.info(
        "Starting archive daemon loop with base interval=%ss; active-window poll=%ss",
        config.loop_interval_sec,
        active_poll_sec,
    )

    while True:
        now = datetime.now(timezone.utc)
        current_time = now.astimezone(config.timezone)
        business_date = _business_date(config, now)

        logger.debug(f"Daemon loop iteration at {current_time.isoformat()}")

        sleep_seconds = active_poll_sec
        window = config.get_matching_window(current_time)
        if window is not None:
            existing = summary_store.get_summary(business_date, window.window_name)
            if existing and existing.get("status") in {"completed", "partial"}:
                logger.info(
                    "Window %s already executed for %s, waiting for next window/day.",
                    window.window_name,
                    business_date,
                )
                sleep_seconds = _seconds_until_next_window(config, now)
            else:
                logger.info(f"Matched window: {window.window_name}")

                daemon_store.mark_running(True)
                try:
                    summary = orchestrator.run_window(window.window_name, dry_run=False)
                finally:
                    daemon_store.mark_running(False)

                if summary and summary.succeeded_jobs > 0:
                    daemon_store.mark_success(f"window_{summary.window_name}")
                elif summary and summary.failed_jobs > 0:
                    daemon_store.mark_failed(f"window_{summary.window_name}")

                logger.info(
                    f"Window {window.window_name}: {summary.succeeded_jobs}/{summary.total_jobs} succeeded"
                )
                sleep_seconds = _seconds_until_next_window(config, now)
        else:
            sleep_seconds = _seconds_until_next_window(config, now)
            logger.debug(
                "No matching schedule window; sleeping %ss until next window",
                sleep_seconds,
            )

        time.sleep(sleep_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive daemon for iFA Archive Layer")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one iteration and exit",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run in continuous loop mode (default when neither --once nor --loop specified)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to daemon config file (YAML). If not provided, uses default config.",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Show daemon health/status information and exit",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = get_archive_config(args.config)

    if args.health:
        health = get_archive_health(config)
        print("=== Archive Health ===")
        print(f"Status: {health.status}")
        print(f"Is Running: {health.is_running}")
        print(f"Last Run: {health.last_run_time}")
        print(f"Latest Run Status: {health.latest_run_status}")
        print(f"Checkpoint Advanced: {health.checkpoint_advanced}")
        print(f"Message: {health.message}")
        print()

        watchdog = check_archive_watchdog(config)
        print("=== Archive Watchdog ===")
        print(f"Is Alive: {watchdog.is_alive}")
        print(f"Is Stale: {watchdog.is_stale}")
        print(f"Last Run: {watchdog.last_run_time}")
        print(f"Message: {watchdog.message}")
        return 0

    if args.once:
        summary = run_once(config)
        if summary is None:
            print("No matching window")
            return 0
        print(
            f"Window {summary.window_name}: {summary.succeeded_jobs}/{summary.total_jobs} succeeded"
        )
        if summary.failed_jobs > 0:
            print(f"Failed: {summary.failed_jobs}")
        return 0 if summary.succeeded_jobs > 0 else 1
    else:
        run_loop(config)
        return 0


if __name__ == "__main__":
    sys.exit(main())
