"""Daemon configuration module for midfreq."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Optional

import yaml
from zoneinfo import ZoneInfo


@dataclass
class ScheduleWindow:
    """A single schedule window configuration."""

    window_type: str
    group_name: str
    time_str: str
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Shanghai"))
    day_of_week: Optional[int] = None
    max_retries: int = 3
    retry_interval_minutes: int = 30

    def matches(self, check_time: datetime) -> bool:
        """Check if the given time matches this window."""
        window_time = time.fromisoformat(self.time_str)
        if self.day_of_week is not None:
            if check_time.weekday() != self.day_of_week:
                return False
        return check_time.time() == window_time


@dataclass
class GroupConfig:
    """Group configuration defining which datasets belong to a group."""

    group_name: str
    datasets: list[str]
    description: str = ""


@dataclass
class DaemonConfig:
    """Main daemon configuration for midfreq."""

    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Shanghai"))
    loop_interval_sec: int = 60
    schedule_windows: list[ScheduleWindow] = field(default_factory=list)
    groups: list[GroupConfig] = field(default_factory=list)

    def get_matching_window(self, current_time: datetime) -> Optional[ScheduleWindow]:
        """Get the schedule window that matches the current time."""
        for window in self.schedule_windows:
            if window.matches(current_time):
                return window
        return None

    def get_group(self, group_name: str) -> Optional[GroupConfig]:
        """Get group config by name."""
        for group in self.groups:
            if group.group_name == group_name:
                return group
        return None


def _get_default_config() -> DaemonConfig:
    """Get default midfreq daemon configuration."""
    return DaemonConfig(
        timezone=ZoneInfo("Asia/shanghai"),
        loop_interval_sec=60,
        schedule_windows=[
            ScheduleWindow(
                window_type="prewarm_early",
                group_name="prewarm_early",
                time_str="07:20",
                max_retries=2,
            ),
            ScheduleWindow(
                window_type="pre_open_final",
                group_name="pre_open_final",
                time_str="08:35",
                max_retries=2,
            ),
            ScheduleWindow(
                window_type="midday_prewarm",
                group_name="midday_prewarm",
                time_str="11:20",
                max_retries=2,
            ),
            ScheduleWindow(
                window_type="midday_final",
                group_name="midday_final",
                time_str="11:45",
                max_retries=2,
            ),
            ScheduleWindow(
                window_type="post_close_prewarm",
                group_name="post_close_prewarm",
                time_str="15:05",
                max_retries=2,
            ),
            ScheduleWindow(
                window_type="post_close_final",
                group_name="post_close_final",
                time_str="15:20",
                max_retries=3,
            ),
            ScheduleWindow(
                window_type="night_settlement",
                group_name="night_settlement",
                time_str="20:30",
                max_retries=2,
            ),
        ],
        groups=[
            GroupConfig(
                group_name="prewarm_early",
                datasets=[],
                description="Early morning warmup",
            ),
            GroupConfig(
                group_name="pre_open_final",
                datasets=[],
                description="Pre-open final window",
            ),
            GroupConfig(
                group_name="midday_prewarm",
                datasets=[],
                description="Midday prewarm",
            ),
            GroupConfig(
                group_name="midday_final",
                datasets=[],
                description="Midday final window",
            ),
            GroupConfig(
                group_name="post_close_prewarm",
                datasets=[],
                description="Post-close prewarm",
            ),
            GroupConfig(
                group_name="post_close_final",
                datasets=[
                    "equity_daily_bar",
                    "index_daily_bar",
                    "etf_daily_bar",
                    "northbound_flow",
                    "limit_up_down_status",
                ],
                description="Post-close final - main data window for B4",
            ),
            GroupConfig(
                group_name="night_settlement",
                datasets=[],
                description="Night settlement / late data",
            ),
        ],
    )


def get_daemon_config(config_path: Optional[str] = None) -> DaemonConfig:
    """Get daemon configuration.

    Args:
        config_path: Optional path to config file.

    Returns:
        DaemonConfig instance.
    """
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                data = yaml.safe_load(f)
                return _parse_config(data)

    return _get_default_config()


def _parse_config(data: dict) -> DaemonConfig:
    """Parse config from dict."""
    return _get_default_config()
