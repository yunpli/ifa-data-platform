"""Mid-frequency daemon for iFA China-market / A-share."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.midfreq.daemon_config import (
    DaemonConfig,
    get_daemon_config,
)
from ifa_data_platform.midfreq.daemon_health import (
    DaemonHealth,
    GroupStatus,
    get_daemon_health,
)
from ifa_data_platform.midfreq.daemon_orchestrator import (
    DaemonOrchestrator,
    GroupExecutionSummary,
)
from ifa_data_platform.midfreq.schedule_memory import (
    ScheduleMemory,
    WindowState,
)
from ifa_data_platform.midfreq.summary_persistence import (
    ExecutionSummaryStore,
    DaemonWatchdog,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class DaemonState:
    """Runtime state for the midfreq daemon."""

    config: DaemonConfig
    orchestrator: DaemonOrchestrator
    schedule_memory: ScheduleMemory
    shutdown_requested: bool = False
    last_loop_time: Optional[datetime] = None


def _signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received signal %d, initiating shutdown...", signum)
    sys.exit(0)


def run_once(
    config: DaemonConfig, current_time_override: Optional[datetime] = None
) -> GroupExecutionSummary:
    """Execute one iteration of the daemon (--once mode)."""
    orchestrator = DaemonOrchestrator(config)
    schedule_memory = ScheduleMemory()

    now = current_time_override or datetime.now(timezone.utc)
    current_time = now.astimezone(config.timezone)

    logger.info(f"Running midfreq daemon in --once mode at {current_time.isoformat()}")

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

    schedule_memory.update_daemon_loop(
        window.group_name, "succeeded" if summary.all_succeeded else "failed"
    )

    if summary.all_succeeded:
        schedule_memory.mark_window_succeeded(window.window_type, window.group_name)
    else:
        schedule_memory.increment_retry(window.window_type)

    return summary


def run_loop(config: DaemonConfig) -> None:
    """Run daemon in continuous loop mode."""
    orchestrator = DaemonOrchestrator(config)
    schedule_memory = ScheduleMemory()
    summary_store = ExecutionSummaryStore()
    watchdog = DaemonWatchdog()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Record initial heartbeat
    watchdog = DaemonWatchdog()
    watchdog.record_heartbeat()

    logger.info(
        f"Starting midfreq daemon loop with {config.loop_interval_sec}s interval"
    )

    while True:
        now = datetime.now(timezone.utc)
        current_time = now.astimezone(config.timezone)

        window = config.get_matching_window(current_time)
        if window:
            memory_state = schedule_memory.get_window_state(window.window_type)
            can_run = not (memory_state and memory_state.already_succeeded_today)

            if can_run:
                retry_count = memory_state.retry_count_in_window if memory_state else 0
                max_retries = window.max_retries if window else 0
                can_run = retry_count < max_retries

            if can_run:
                logger.info(
                    f"Matched window: {window.window_type} (group: {window.group_name})"
                )
                summary = orchestrator.run_group(window.group_name)

                # Store summary to database
                summary_store = ExecutionSummaryStore()
                summary_store.store(
                    summary.to_json(), window.group_name, window.window_type
                )

                schedule_memory.update_daemon_loop(
                    window.group_name,
                    "succeeded" if summary.all_succeeded else "failed",
                )

                if summary.all_succeeded:
                    schedule_memory.mark_window_succeeded(
                        window.window_type, window.group_name
                    )
                else:
                    schedule_memory.increment_retry(window.window_type)
            else:
                logger.info(f"Window {window.window_type} already handled this cycle")
        else:
            logger.debug(
                f"No matching window at {current_time.isoformat()}, sleeping..."
            )

        time.sleep(config.loop_interval_sec)


def main() -> None:
    """Main entry point for midfreq daemon."""
    parser = argparse.ArgumentParser(description="iFA Midfreq Daemon")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run in continuous loop (default)",
    )
    parser.add_argument(
        "--group",
        type=str,
        help="Run a specific group directly",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to daemon config file (YAML)",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Show daemon health and exit",
    )
    parser.add_argument(
        "--watchdog",
        action="store_true",
        help="Show watchdog status and check if daemon needs restart",
    )
    args = parser.parse_args()

    config = get_daemon_config(args.config)

    if args.health:
        health = get_daemon_health()
        print(health.to_json())
        return

    if args.watchdog:
        from ifa_data_platform.midfreq.summary_persistence import DaemonWatchdog

        watchdog = DaemonWatchdog()
        health = watchdog.check_health()
        import json

        print(json.dumps(health, indent=2, default=str))
        return

if args.group:
        logger.info(f"Running midfreq group: {args.group}")
        orchestrator = DaemonOrchestrator(config)
        summary = orchestrator.run_group(args.group)
        
        # Store summary with window_type = group_name
        from ifa_data_platform.midfreq.summary_persistence import ExecutionSummaryStore
        summary_store = ExecutionSummaryStore()
        summary_store.store(summary.to_json(), args.group, args.group)
        
        print(summary.to_json())
        return

    if args.once:
        summary = run_once(config)
        print(summary.to_json())
    else:
        run_loop(config)


if __name__ == "__main__":
    main()
