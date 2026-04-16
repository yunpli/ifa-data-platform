"""Highfreq daemon skeleton for milestone 1."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ifa_data_platform.highfreq.daemon_config import get_daemon_config
from ifa_data_platform.highfreq.daemon_orchestrator import DaemonOrchestrator, GroupExecutionSummary
from ifa_data_platform.highfreq.registry import HighfreqDatasetRegistry


def _signal_handler(signum, frame):
    sys.exit(0)


def _match_window(config, current_time):
    current_hm = current_time.strftime('%H:%M')
    for window in config.windows:
        if window.is_enabled and window.trigger_time == current_hm:
            return window
    return None


def run_once(config, current_time_override=None) -> GroupExecutionSummary:
    orchestrator = DaemonOrchestrator(config)
    now = current_time_override or datetime.now(timezone.utc)
    current_time = now.astimezone(config.timezone)
    window = _match_window(config, current_time)
    if not window:
        return GroupExecutionSummary(
            group_name='none',
            started_at=now,
            completed_at=datetime.now(timezone.utc),
            total_datasets=0,
            succeeded_datasets=0,
            failed_datasets=0,
            dataset_results=[],
            window_type='none',
            skipped=True,
            reason='no_matching_window',
        )
    summary = orchestrator.run_group(window.group_name)
    summary.window_type = window.window_type
    return summary


def run_loop(config) -> None:
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    while True:
        run_once(config)
        time.sleep(config.loop_interval_sec)


def health_payload(config) -> dict:
    registry = HighfreqDatasetRegistry()
    enabled = [d.dataset_name for d in registry.list_enabled()]
    return {
        'daemon_name': 'highfreq_daemon',
        'status': 'skeleton_ready',
        'timezone': str(config.timezone),
        'loop_interval_sec': config.loop_interval_sec,
        'light_refresh_interval_min': config.light_refresh_interval_min,
        'enabled_windows': [
            {
                'window_type': w.window_type,
                'group_name': w.group_name,
                'trigger_time': w.trigger_time,
                'max_retries': w.max_retries,
            }
            for w in config.windows if w.is_enabled
        ],
        'groups': [
            {
                'group_name': g.group_name,
                'datasets': g.datasets,
                'description': g.description,
            }
            for g in config.groups
        ],
        'enabled_datasets': enabled,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='iFA Highfreq Daemon')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--loop', action='store_true')
    parser.add_argument('--group', type=str)
    parser.add_argument('--config', type=str)
    parser.add_argument('--health', action='store_true')
    args = parser.parse_args()

    config = get_daemon_config(args.config)

    if args.health:
        print(json.dumps(health_payload(config), ensure_ascii=False, indent=2, default=str))
        return

    if args.group:
        orchestrator = DaemonOrchestrator(config)
        print(orchestrator.run_group(args.group).to_json())
        return

    if args.once:
        print(run_once(config).to_json())
        return

    run_loop(config)


if __name__ == '__main__':
    main()
