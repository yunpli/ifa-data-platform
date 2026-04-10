"""Low-frequency dataset/job abstractions for iFA China-market / A-share."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Optional


class Market(StrEnum):
    CHINA_A_SHARE = "china_a_share"
    US_EQUITY = "us_equity"
    UNKNOWN = "unknown"


class JobType(StrEnum):
    SNAPSHOT = "snapshot"
    INCREMENTAL = "incremental"
    FULL_REFRESH = "full_refresh"


class RunnerType(StrEnum):
    TUSHARE = "tushare"
    DUMMY = "dummy"
    GENERIC = "generic"


class TimezoneSemantics(StrEnum):
    UTC = "utc"
    CHINA_SHANGHAI = "china_shanghai"
    US_EASTERN = "us_eastern"


class WatermarkStrategy(StrEnum):
    NONE = "none"
    DATE_BASED = "date_based"
    DATETIME_BASED = "datetime_based"
    VERSION_BASED = "version_based"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    RETRYING = "retrying"


@dataclass
class DatasetConfig:
    dataset_name: str
    market: Market
    source_name: str
    job_type: JobType
    enabled: bool = True
    timezone_semantics: TimezoneSemantics = TimezoneSemantics.CHINA_SHANGHAI
    runner_type: RunnerType = RunnerType.GENERIC
    watermark_strategy: WatermarkStrategy = WatermarkStrategy.DATE_BASED
    budget_records_max: Optional[int] = None
    budget_seconds_max: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RunState:
    run_id: str
    dataset_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    watermark: Optional[str] = None
    error_message: Optional[str] = None
    run_type: str = "scheduled"
    dry_run: bool = False
