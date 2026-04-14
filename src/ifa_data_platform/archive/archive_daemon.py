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
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ifa_data_platform.archive.archive_config import (
    ArchiveConfig,
    get_archive_config,
)
from ifa_data_platform.archive.archive_daemon_state import ArchiveDaemonStateStore
from ifa_data_platform.archive.archive_health import (
    ArchiveHealth,
    get_archive_health,
    check_archive_watchdog,
)
from ifa_data_platform.archive.archive_orchestrator import (
    ArchiveOrchestrator,
    ArchiveExecutionSummary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] archive: %(message)s",
)
logger = logging.getLogger(__name__)


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

    now = current_time_override or datetime.now(timezone.utc)
    current_time = now.astimezone(config.timezone)

    logger.info(f"Running archive daemon in --once mode at {current_time.isoformat()}")

    window = config.get_matching_window(current_time)
    if window is None:
        logger.info("No matching schedule window for current time, exiting.")
        return None

    logger.info(f"Matched window: {window.window_name}")

    daemon_store.mark_running(True)

    summary = orchestrator.run_window(window.window_name, dry_run=False)

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

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info(
        f"Starting archive daemon loop with {config.loop_interval_sec}s interval"
    )

    while True:
        now = datetime.now(timezone.utc)
        current_time = now.astimezone(config.timezone)

        logger.debug(f"Daemon loop iteration at {current_time.isoformat()}")

        window = config.get_matching_window(current_time)
        if window is not None:
            logger.info(f"Matched window: {window.window_name}")

            daemon_store.mark_running(True)

            summary = orchestrator.run_window(window.window_name, dry_run=False)

            daemon_store.mark_running(False)

            if summary and summary.succeeded_jobs > 0:
                daemon_store.mark_success(f"window_{summary.window_name}")
            elif summary and summary.failed_jobs > 0:
                daemon_store.mark_failed(f"window_{summary.window_name}")

            logger.info(
                f"Window {window.window_name}: {summary.succeeded_jobs}/{summary.total_jobs} succeeded"
            )
        else:
            logger.debug("No matching schedule window")

        time.sleep(config.loop_interval_sec)


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
