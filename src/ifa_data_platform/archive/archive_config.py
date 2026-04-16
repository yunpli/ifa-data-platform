"""Archive daemon configuration module."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Optional

import yaml
from zoneinfo import ZoneInfo


@dataclass
class ArchiveWindow:
    """A single archive schedule window.

    Window defines a time range when archive jobs are allowed to run.
    Business time standard: Asia/Shanghai
    """

    window_name: str
    start_time: str
    end_time: str
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Shanghai"))
    max_duration_minutes: int = 60
    is_enabled: bool = True

    def contains(self, check_time: datetime) -> bool:
        """Check if the given time is within this window."""
        window_start = time.fromisoformat(self.start_time)
        window_end = time.fromisoformat(self.end_time)
        check_t = check_time.time()

        if window_start <= window_end:
            return window_start <= check_t < window_end
        else:
            return check_t >= window_start or check_t < window_end

    def is_available_now(self) -> bool:
        """Check if window is currently available."""
        now_sh = datetime.now(ZoneInfo("Asia/Shanghai"))
        return self.is_enabled and self.contains(now_sh)


@dataclass
class ArchiveJobConfig:
    """Configuration for a single archive job."""

    job_name: str
    dataset_name: str
    asset_type: str
    pool_name: str = ""
    scope_name: str = ""
    is_enabled: bool = True
    description: str = ""


@dataclass
class ArchiveConfig:
    """Main archive daemon configuration."""

    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Shanghai"))
    loop_interval_sec: int = 60
    windows: list[ArchiveWindow] = field(default_factory=list)
    jobs: list[ArchiveJobConfig] = field(default_factory=list)

    def get_matching_window(self, current_time: datetime) -> Optional[ArchiveWindow]:
        """Get the window that matches the current time."""
        for window in self.windows:
            if window.contains(current_time):
                return window
        return None

    def get_active_window(self) -> Optional[ArchiveWindow]:
        """Get the currently active window based on Asia/Shanghai time."""
        now_sh = datetime.now(ZoneInfo("Asia/Shanghai"))
        return self.get_matching_window(now_sh)

    def get_job(self, job_name: str) -> Optional[ArchiveJobConfig]:
        """Get job config by name."""
        for job in self.jobs:
            if job.job_name == job_name:
                return job
        return None

    def get_enabled_jobs(self) -> list[ArchiveJobConfig]:
        """Get all enabled jobs."""
        return [j for j in self.jobs if j.is_enabled]


def _get_default_config() -> ArchiveConfig:
    """Get default archive configuration.

    Default windows (Asia/Shanghai):
    - window_1: 21:30-22:30 (Shanghai night)
    - window_2: 02:00-03:00 (Shanghai early morning)

    Max 1 hour each, 2 hours total budget per day.
    """
    return ArchiveConfig(
        timezone=ZoneInfo("Asia/Shanghai"),
        loop_interval_sec=60,
        windows=[
            ArchiveWindow(
                window_name="night_window_1",
                start_time="21:30",
                end_time="22:30",
                timezone=ZoneInfo("Asia/Shanghai"),
                max_duration_minutes=60,
                is_enabled=True,
            ),
            ArchiveWindow(
                window_name="night_window_2",
                start_time="02:00",
                end_time="03:00",
                timezone=ZoneInfo("Asia/Shanghai"),
                max_duration_minutes=60,
                is_enabled=True,
            ),
        ],
        jobs=[
            ArchiveJobConfig(
                job_name="stock_daily_archive",
                dataset_name="stock_daily",
                asset_type="stock",
                pool_name="default",
                scope_name="all",
                is_enabled=True,
                description="Stock daily historical data archive",
            ),
            ArchiveJobConfig(
                job_name="macro_archive",
                dataset_name="macro_history",
                asset_type="macro",
                pool_name="default",
                scope_name="cn_macro",
                is_enabled=True,
                description="Macro economic indicators historical archive",
            ),
            ArchiveJobConfig(
                job_name="futures_archive",
                dataset_name="futures_history",
                asset_type="futures",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Futures historical archive",
            ),
            ArchiveJobConfig(
                job_name="commodity_archive",
                dataset_name="commodity_history",
                asset_type="commodity",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Commodity historical archive",
            ),
            ArchiveJobConfig(
                job_name="precious_metal_archive",
                dataset_name="precious_metal_history",
                asset_type="precious_metal",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Precious metal historical archive",
            ),
            ArchiveJobConfig(
                job_name="stock_15min_archive",
                dataset_name="stock_15min_history",
                asset_type="stock",
                pool_name="default",
                scope_name="all",
                is_enabled=True,
                description="Stock 15min archive",
            ),
            ArchiveJobConfig(
                job_name="macro_15min_archive",
                dataset_name="macro_15min_history",
                asset_type="macro",
                pool_name="default",
                scope_name="cn_macro",
                is_enabled=True,
                description="Macro 15min archive",
            ),
            ArchiveJobConfig(
                job_name="futures_15min_archive",
                dataset_name="futures_15min_history",
                asset_type="futures",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Futures 15min archive",
            ),
            ArchiveJobConfig(
                job_name="commodity_15min_archive",
                dataset_name="commodity_15min_history",
                asset_type="commodity",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Commodity 15min archive",
            ),
            ArchiveJobConfig(
                job_name="precious_metal_15min_archive",
                dataset_name="precious_metal_15min_history",
                asset_type="precious_metal",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Precious metal 15min archive",
            ),
            ArchiveJobConfig(
                job_name="stock_minute_archive",
                dataset_name="stock_minute_history",
                asset_type="stock",
                pool_name="default",
                scope_name="all",
                is_enabled=True,
                description="Stock minute archive",
            ),
            ArchiveJobConfig(
                job_name="futures_minute_archive",
                dataset_name="futures_minute_history",
                asset_type="futures",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Futures minute archive",
            ),
            ArchiveJobConfig(
                job_name="commodity_minute_archive",
                dataset_name="commodity_minute_history",
                asset_type="commodity",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Commodity minute archive",
            ),
            ArchiveJobConfig(
                job_name="precious_metal_minute_archive",
                dataset_name="precious_metal_minute_history",
                asset_type="precious_metal",
                pool_name="default",
                scope_name="commodity_pool",
                is_enabled=True,
                description="Precious metal minute archive",
            ),
        ],
    )


def _load_config_from_file(config_path: Optional[str]) -> Optional[ArchiveConfig]:
    """Load configuration from a YAML file."""
    if config_path is None:
        config_path = os.environ.get("ARCHIVE_DAEMON_CONFIG")

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
    for w in data.get("windows", []):
        windows.append(
            ArchiveWindow(
                window_name=w["window_name"],
                start_time=w["start_time"],
                end_time=w["end_time"],
                timezone=timezone,
                max_duration_minutes=w.get("max_duration_minutes", 60),
                is_enabled=w.get("is_enabled", True),
            )
        )

    jobs = []
    for j in data.get("jobs", []):
        jobs.append(
            ArchiveJobConfig(
                job_name=j["job_name"],
                dataset_name=j["dataset_name"],
                asset_type=j["asset_type"],
                pool_name=j.get("pool_name", ""),
                scope_name=j.get("scope_name", ""),
                is_enabled=j.get("is_enabled", True),
                description=j.get("description", ""),
            )
        )

    return ArchiveConfig(
        timezone=timezone,
        loop_interval_sec=loop_interval,
        windows=windows,
        jobs=jobs,
    )


def get_archive_config(config_path: Optional[str] = None) -> ArchiveConfig:
    """Get archive configuration, loading from file if provided, else defaults."""
    file_config = _load_config_from_file(config_path)
    if file_config is not None:
        return file_config

    return _get_default_config()
