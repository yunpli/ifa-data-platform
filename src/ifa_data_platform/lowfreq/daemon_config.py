"""Daemon configuration module."""

from __future__ import annotations

import os
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
    """Main daemon configuration."""

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
    """Get default daemon configuration."""
    return DaemonConfig(
        timezone=ZoneInfo("Asia/Shanghai"),
        loop_interval_sec=60,
        schedule_windows=[
            ScheduleWindow(
                window_type="daily_light",
                group_name="daily_light",
                time_str="22:45",
                timezone=ZoneInfo("Asia/Shanghai"),
                max_retries=3,
            ),
            ScheduleWindow(
                window_type="daily_light_fallback",
                group_name="daily_light",
                time_str="01:30",
                timezone=ZoneInfo("Asia/Shanghai"),
                max_retries=2,
            ),
            ScheduleWindow(
                window_type="weekly_deep",
                group_name="weekly_deep",
                time_str="10:00",
                timezone=ZoneInfo("Asia/Shanghai"),
                day_of_week=5,
                max_retries=2,
            ),
        ],
        groups=[
            GroupConfig(
                group_name="daily_light",
                datasets=[
                    "trade_cal",
                    "stock_basic",
                    "index_basic",
                    "fund_basic_etf",
                    "sw_industry_mapping",
                    "announcements",
                    "news",
                    "research_reports",
                    "investor_qa",
                    "index_weight",
                    "etf_daily_basic",
                    "share_float",
                    "company_basic",
                    "stk_managers",
                    "new_share",
                    "stk_holdernumber",
                    "name_change",
                ],
                description="Daily light ingestion for trade calendar and stock basic",
            ),
            GroupConfig(
                group_name="weekly_deep",
                datasets=[
                    "trade_cal",
                    "stock_basic",
                    "index_basic",
                    "fund_basic_etf",
                    "sw_industry_mapping",
                    "announcements",
                    "news",
                    "research_reports",
                    "investor_qa",
                    "index_weight",
                    "etf_daily_basic",
                    "share_float",
                    "company_basic",
                    "stk_managers",
                    "new_share",
                    "stk_holdernumber",
                    "name_change",
                    "top10_holders",
                    "top10_floatholders",
                    "pledge_stat",
                    "forecast",
                    "margin",
                    "north_south_flow",
                    "etf_basic",
                    "management",
                    "stock_equity_change",
                ],
                description="Weekly deep ingestion",
            ),
        ],
    )


def _load_config_from_file(config_path: Optional[str]) -> Optional[DaemonConfig]:
    """Load configuration from a YAML file."""
    if config_path is None:
        config_path = os.environ.get("LOWFREQ_DAEMON_CONFIG")

    if config_path is None:
        return None

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    timezone = ZoneInfo(data.get("timezone", "Asia/Shanghai"))
    loop_interval = data.get("loop_interval_sec", 60)

    windows = []
    for w in data.get("schedule_windows", []):
        windows.append(
            ScheduleWindow(
                window_type=w["window_type"],
                group_name=w["group_name"],
                time_str=w["time_str"],
                timezone=timezone,
                day_of_week=w.get("day_of_week"),
                max_retries=w.get("max_retries", 3),
                retry_interval_minutes=w.get("retry_interval_minutes", 30),
            )
        )

    groups = []
    for g in data.get("groups", []):
        groups.append(
            GroupConfig(
                group_name=g["group_name"],
                datasets=g["datasets"],
                description=g.get("description", ""),
            )
        )

    return DaemonConfig(
        timezone=timezone,
        loop_interval_sec=loop_interval,
        schedule_windows=windows,
        groups=groups,
    )


def get_daemon_config(config_path: Optional[str] = None) -> DaemonConfig:
    """Get daemon configuration, loading from file if provided, else defaults."""
    file_config = _load_config_from_file(config_path)
    if file_config is not None:
        return file_config

    return _get_default_config()
