"""Validation script for daemon --once mode and schedule simulation.

This script demonstrates:
1. Running --once mode with real data
2. Simulating a matching time window via injected time

Usage:
    # Basic --once run (will likely skip if not in a scheduled window)
    python scripts/validate_daemon.py --once

    # Simulate a specific time window (e.g., daily_light at 22:45)
    python scripts/validate_daemon.py --once --simulate-time "2024-01-15T22:45:00+08:00"

    # Run health check
    python scripts/validate_daemon.py --health

    # Show current daemon configuration
    python scripts/validate_daemon.py --show-config
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from unittest.mock import patch

from ifa_data_platform.lowfreq.daemon import main as daemon_main
from ifa_data_platform.lowfreq.daemon_config import get_daemon_config
from ifa_data_platform.lowfreq.daemon_health import get_daemon_health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def show_config():
    """Show current daemon configuration."""
    config = get_daemon_config()

    print("=== Daemon Configuration ===")
    print(f"Timezone: {config.timezone}")
    print(f"Loop Interval: {config.loop_interval_sec}s")
    print()

    print("=== Schedule Windows ===")
    for window in config.schedule_windows:
        print(f"  {window.window_type}:")
        print(f"    Group: {window.group_name}")
        print(f"    Time: {window.time_str}")
        print(f"    Day of Week: {window.day_of_week or 'any'}")
        print(f"    Max Retries: {window.max_retries}")
        print()

    print("=== Groups ===")
    for group in config.groups:
        print(f"  {group.group_name}: {group.datasets}")
        if group.description:
            print(f"    Description: {group.description}")


def run_with_simulated_time(simulated_time_str: str):
    """Run daemon with a simulated time to force window matching."""
    config = get_daemon_config()

    simulated_time = datetime.fromisoformat(simulated_time_str)
    current_time = simulated_time.astimezone(config.timezone)

    print(f"=== Simulating time: {simulated_time} ===")
    print(f"Local time in {config.timezone}: {current_time}")
    print()

    window = config.get_matching_window(current_time)
    if window:
        print(f"MATCHED WINDOW: {window.window_type} (group: {window.group_name})")
        print()

        from ifa_data_platform.lowfreq import daemon

        simulated_utc = simulated_time.astimezone(timezone.utc)
        result = daemon.run_once(config, current_time_override=simulated_utc)
        print(f"Result: {result}")
        return 0 if result.all_succeeded else 1
    else:
        print("No matching window for simulated time.")
        print("Try: --simulate-time '2024-01-15T22:45:00+08:00' (daily_light)")
        print("Try: --simulate-time '2024-01-20T10:00:00+08:00' (weekly_deep Saturday)")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Validate low-frequency daemon")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run daemon in --once mode",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Show daemon health/status",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show current daemon configuration",
    )
    parser.add_argument(
        "--simulate-time",
        type=str,
        default=None,
        help="Simulate a specific time for window matching (ISO format, e.g., '2024-01-15T22:45:00+08:00')",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.show_config:
        show_config()
        return 0

    if args.health:
        config = get_daemon_config()
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
            print(f"  {ds}: {freshness}")
        return 0

    if args.once:
        if args.simulate_time:
            return run_with_simulated_time(args.simulate_time)
        else:
            sys.argv = ["validate_daemon.py", "--once"]
            return daemon_main()

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
