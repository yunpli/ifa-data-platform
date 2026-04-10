"""Low-frequency daemon for iFA China-market / A-share."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.lowfreq.daemon_config import (
    DaemonConfig,
    GroupConfig,
    get_daemon_config,
)
from ifa_data_platform.lowfreq.daemon_health import (
    DaemonHealth,
    GroupStatus,
    get_daemon_health,
    get_group_status,
)
from ifa_data_platform.lowfreq.daemon_orchestrator import (
    DaemonOrchestrator,
    GroupExecutionSummary,
)
from ifa_data_platform.lowfreq.run_state import RunStateManager
from ifa_data_platform.lowfreq.schedule_memory import (
    ScheduleMemory,
    WindowState,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class DaemonState:
    """Runtime state for the daemon."""

    config: DaemonConfig
    orchestrator: DaemonOrchestrator
    schedule_memory: ScheduleMemory
    shutdown_requested: bool = False
    last_loop_time: Optional[datetime] = None


def _signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received signal %d, initiating shutdown...", signum)
    sys.exit(0)


def run_once(config: DaemonConfig) -> GroupExecutionSummary:
    """Execute one iteration of the daemon (--once mode)."""
    orchestrator = DaemonOrchestrator(config)
    schedule_memory = ScheduleMemory()

    now = datetime.now(timezone.utc)
    current_time = now.astimezone(config.timezone)

    logger.info(f"Running daemon in --once mode at {current_time.isoformat()}")

    window = config.get_matching_window(current_time)
    if window is None:
        logger.info("No matching schedule window for current time, exiting.")
        return GroupExecutionSummary(
            group_name="none",
            started_at=now,
            completed_at=datetime.now(timezone.utc),
            total_datasets=0,
            succeeded_datasets=0,
            failed_datasets=0,
            dataset_results=[],
            window_type="none",
            skipped=True,
        )

    logger.info(f"Matched window: {window.window_type} (group: {window.group_name})")

    memory_state = schedule_memory.get_window_state(window.window_type)
    if memory_state and memory_state.already_succeeded_today:
        logger.info(f"Window {window.window_type} already succeeded today, skipping.")
        return GroupExecutionSummary(
            group_name=window.group_name,
            started_at=now,
            completed_at=datetime.now(timezone.utc),
            total_datasets=0,
            succeeded_datasets=0,
            failed_datasets=0,
            dataset_results=[],
            window_type=window.window_type,
            skipped=True,
        )

    retry_count = memory_state.retry_count_in_window if memory_state else 0
    max_retries = window.max_retries if window else 0

    if retry_count >= max_retries and max_retries > 0:
        logger.warning(
            f"Window {window.window_type} exhausted retries ({retry_count}/{max_retries}), marking degraded."
        )
        schedule_memory.mark_window_degraded(window.window_type)
        return GroupExecutionSummary(
            group_name=window.group_name,
            started_at=now,
            completed_at=datetime.now(timezone.utc),
            total_datasets=0,
            succeeded_datasets=0,
            failed_datasets=0,
            dataset_results=[],
            window_type=window.window_type,
            skipped=True,
            degraded=True,
        )

    summary = orchestrator.run_group(window.group_name)

    if summary.all_succeeded:
        schedule_memory.mark_window_succeeded(window.window_type, window.group_name)
    else:
        schedule_memory.increment_retry(window.window_type)

    return summary


def run_loop(config: DaemonConfig) -> None:
    """Run daemon in continuous loop mode."""
    orchestrator = DaemonOrchestrator(config)
    schedule_memory = ScheduleMemory()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info(f"Starting daemon loop with {config.loop_interval_sec}s interval")

    while True:
        now = datetime.now(timezone.utc)
        current_time = now.astimezone(config.timezone)

        logger.debug(f"Daemon loop iteration at {current_time.isoformat()}")

        window = config.get_matching_window(current_time)
        if window is not None:
            logger.info(
                f"Matched window: {window.window_type} (group: {window.group_name})"
            )

            memory_state = schedule_memory.get_window_state(window.window_type)
            retry_count = memory_state.retry_count_in_window if memory_state else 0
            max_retries = window.max_retries if window else 0

            if memory_state and memory_state.already_succeeded_today:
                logger.info(
                    f"Window {window.window_type} already succeeded today, skipping."
                )
            elif retry_count >= max_retries and max_retries > 0:
                logger.warning(
                    f"Window {window.window_type} exhausted retries, marking degraded."
                )
                schedule_memory.mark_window_degraded(window.window_type)
            else:
                summary = orchestrator.run_group(window.group_name)

                if summary.all_succeeded:
                    schedule_memory.mark_window_succeeded(
                        window.window_type, window.group_name
                    )
                else:
                    schedule_memory.increment_retry(window.window_type)

                logger.info(
                    f"Group {window.group_name}: {summary.succeeded_datasets}/{summary.total_datasets} succeeded"
                )
        else:
            logger.debug("No matching schedule window")

        time.sleep(config.loop_interval_sec)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Low-frequency daemon for iFA China-market / A-share"
    )
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

    config = get_daemon_config(args.config)

    if args.health:
        health = get_daemon_health(config)
        print("=== Daemon Health ===")
        print(f"Status: {health.status}")
        print(f"Last Loop: {health.last_loop_time}")
        print(f"Config Loaded: {health.config_loaded}")
        print()
        print("=== Group Status ===")
        for group_name, status in health.group_statuses.items():
            print(f"Group: {group_name}")
            print(f"  Last Success: {status.last_success_time}")
            print(f"  Last Failure: {status.last_failure_time}")
            print(f"  Last Status: {status.last_status}")
        print()
        print("=== Dataset Freshness ===")
        for ds, freshness in health.dataset_freshness.items():
            print(f"{ds}: {freshness}")
        return 0

    if args.once:
        summary = run_once(config)
        if summary.skipped:
            print(f"Skipped: {summary.reason or 'no matching window'}")
            return 0
        print(
            f"Group {summary.group_name}: {summary.succeeded_datasets}/{summary.total_datasets} succeeded"
        )
        return 0 if summary.all_succeeded else 1
    else:
        run_loop(config)
        return 0


if __name__ == "__main__":
    sys.exit(main())
