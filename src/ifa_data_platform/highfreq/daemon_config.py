"""Daemon configuration for highfreq lane."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import yaml


@dataclass(frozen=True)
class GroupConfig:
    group_name: str
    datasets: list[str]
    description: str = ""


@dataclass(frozen=True)
class WindowConfig:
    window_type: str
    group_name: str
    trigger_time: str
    timezone: ZoneInfo
    max_retries: int = 1
    is_enabled: bool = True


@dataclass(frozen=True)
class DaemonConfig:
    timezone: ZoneInfo
    loop_interval_sec: int
    groups: list[GroupConfig]
    windows: list[WindowConfig]
    light_refresh_interval_min: int = 10

    def get_group(self, group_name: str) -> Optional[GroupConfig]:
        for group in self.groups:
            if group.group_name == group_name:
                return group
        return None


def _default_config() -> DaemonConfig:
    tz = ZoneInfo("Asia/Shanghai")
    return DaemonConfig(
        timezone=tz,
        loop_interval_sec=60,
        light_refresh_interval_min=10,
        groups=[
            GroupConfig(
                group_name="pre_open_core",
                datasets=[
                    "stock_1m_ohlcv",
                    "index_1m_ohlcv",
                    "etf_sector_style_1m_ohlcv",
                    "futures_commodity_pm_1m_ohlcv",
                    "open_auction_snapshot",
                    "event_time_stream",
                ],
                description="Pre-open and auction-adjacent core highfreq collection",
            ),
            GroupConfig(
                group_name="intraday_core",
                datasets=[
                    "stock_1m_ohlcv",
                    "index_1m_ohlcv",
                    "etf_sector_style_1m_ohlcv",
                    "futures_commodity_pm_1m_ohlcv",
                    "event_time_stream",
                ],
                description="Intraday highfreq light refresh collection",
            ),
            GroupConfig(
                group_name="close_core",
                datasets=[
                    "stock_1m_ohlcv",
                    "index_1m_ohlcv",
                    "etf_sector_style_1m_ohlcv",
                    "futures_commodity_pm_1m_ohlcv",
                    "close_auction_snapshot",
                    "event_time_stream",
                ],
                description="Close and post-close highfreq collection",
            ),
        ],
        windows=[
            WindowConfig("pre_open_0915", "pre_open_core", "09:15", tz),
            WindowConfig("auction_window_0920", "pre_open_core", "09:20", tz),
            WindowConfig("auction_window_0925", "pre_open_core", "09:25", tz),
            WindowConfig("pre_open_finalize_0928", "pre_open_core", "09:28", tz),
            WindowConfig("open_0930", "intraday_core", "09:30", tz),
            WindowConfig("check_0945", "intraday_core", "09:45", tz),
            WindowConfig("check_1015", "intraday_core", "10:15", tz),
            WindowConfig("check_1030", "intraday_core", "10:30", tz),
            WindowConfig("check_1100", "intraday_core", "11:00", tz),
            WindowConfig("check_1125", "intraday_core", "11:25", tz),
            WindowConfig("afternoon_1330", "intraday_core", "13:30", tz),
            WindowConfig("afternoon_1400", "intraday_core", "14:00", tz),
            WindowConfig("afternoon_1430", "intraday_core", "14:30", tz),
            WindowConfig("afternoon_1445", "intraday_core", "14:45", tz),
            WindowConfig("close_auction_1457", "close_core", "14:57", tz),
            WindowConfig("close_1500", "close_core", "15:00", tz),
            WindowConfig("post_close_1505", "close_core", "15:05", tz),
        ],
    )


def get_daemon_config(config_path: Optional[str] = None) -> DaemonConfig:
    path = config_path or os.environ.get("HIGHFREQ_DAEMON_CONFIG")
    if not path:
        return _default_config()
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    data = yaml.safe_load(p.read_text())
    tz = ZoneInfo(data.get("timezone", "Asia/Shanghai"))
    groups = [GroupConfig(**g) for g in data.get("groups", [])]
    windows = [
        WindowConfig(
            window_type=w["window_type"],
            group_name=w["group_name"],
            trigger_time=w["trigger_time"],
            timezone=tz,
            max_retries=w.get("max_retries", 1),
            is_enabled=w.get("is_enabled", True),
        )
        for w in data.get("windows", [])
    ]
    return DaemonConfig(
        timezone=tz,
        loop_interval_sec=data.get("loop_interval_sec", 60),
        groups=groups,
        windows=windows,
        light_refresh_interval_min=data.get("light_refresh_interval_min", 10),
    )
