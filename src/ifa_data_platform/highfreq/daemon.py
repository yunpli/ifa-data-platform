"""Highfreq daemon with schedule/state/operator surfaces."""

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
from ifa_data_platform.highfreq.schedule_memory import ScheduleMemory
from ifa_data_platform.highfreq.summary_persistence import DaemonWatchdog, ExecutionSummaryStore


def _signal_handler(signum, frame):
    sys.exit(0)


def _match_window(config, current_time):
    current_hm = current_time.strftime('%H:%M')
    current_minute = current_time.minute
    for window in config.windows:
        if window.is_enabled and window.trigger_time == current_hm:
            return window
    if current_time.hour in {9, 10, 11, 13, 14} and current_minute % config.light_refresh_interval_min == 0:
        return type('LightRefreshWindow', (), {
            'window_type': f'light_refresh_{current_hm.replace(":", "")}',
            'group_name': 'intraday_core',
            'trigger_time': current_hm,
            'max_retries': 1,
            'is_enabled': True,
        })()
    return None


def run_once(config, current_time_override=None) -> GroupExecutionSummary:
    orchestrator = DaemonOrchestrator(config)
    memory = ScheduleMemory()
    summary_store = ExecutionSummaryStore()
    now = current_time_override or datetime.now(timezone.utc)
    current_time = now.astimezone(config.timezone)
    window = _match_window(config, current_time)
    if not window:
        memory.update_daemon_loop('idle', None)
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
            sla_status='ok',
        )
    state = memory.get_window_state(window.window_type)
    if state and state.already_succeeded_today and not window.window_type.startswith('light_refresh_'):
        memory.update_daemon_loop('skipped', window.window_type)
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
            reason='already_succeeded_today',
            sla_status='ok',
        )
    summary = orchestrator.run_group(window.group_name)
    summary.window_type = window.window_type
    final_status = 'succeeded' if summary.failed_datasets == 0 else 'failed'
    memory.mark_window_result(window.window_type, window.group_name, final_status, summary.duration_ms, summary.sla_status)
    memory.update_daemon_loop(summary.sla_status, window.window_type)
    summary_store.store(summary.to_json(), window.group_name, window.window_type, summary.sla_status)
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
    watchdog = DaemonWatchdog()
    health = watchdog.check_health()
    return {
        'daemon_name': 'highfreq_daemon',
        'status': health['status'],
        'message': health['message'],
        'last_heartbeat': health.get('last_heartbeat'),
        'last_status': health.get('last_status'),
        'last_window_type': health.get('last_window_type'),
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
    parser.add_argument('--watchdog', action='store_true')
    args = parser.parse_args()

    config = get_daemon_config(args.config)

    if args.health:
        print(json.dumps(health_payload(config), ensure_ascii=False, indent=2, default=str))
        return

    if args.watchdog:
        print(json.dumps(DaemonWatchdog().check_health(), ensure_ascii=False, indent=2, default=str))
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
