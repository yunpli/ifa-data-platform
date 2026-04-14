"""Archive data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ArchiveJob:
    """Archive job definition."""

    job_name: str
    dataset_name: str
    asset_type: str
    pool_name: str
    scope_name: str
    is_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


@dataclass
class ArchiveRun:
    """Archive run execution state."""

    run_id: str
    dataset_name: str
    asset_type: str
    window_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "pending"
    records_processed: int = 0
    error_summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class ArchiveCheckpoint:
    """Archive checkpoint for resume capability."""

    dataset_name: str
    asset_type: str
    backfill_start: Optional[datetime] = None
    backfill_end: Optional[datetime] = None
    last_completed_date: Optional[datetime] = None
    shard_id: Optional[str] = None
    batch_no: Optional[int] = None
    status: str = "pending"
    updated_at: Optional[datetime] = None


@dataclass
class ArchiveSummary:
    """Archive summary for reporting."""

    date: str
    window_name: str
    total_jobs: int
    succeeded_jobs: int
    failed_jobs: int
    total_records: int
    status: str
    created_at: datetime


@dataclass
class ArchiveHealth:
    """Archive health status."""

    status: str
    is_running: bool
    last_run_time: Optional[datetime]
    latest_run_status: Optional[str]
    checkpoint_advanced: bool
    message: str
