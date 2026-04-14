"""Archive summary persistence module."""

from __future__ import annotations

import uuid
from datetime import datetime, date, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ArchiveSummaryStore:
    """Manages archive daily summary in DB.

    Tracks daily archive execution summary for reporting.
    """

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert_summary(
        self,
        summary_date: date,
        window_name: str,
        total_jobs: int = 0,
        succeeded_jobs: int = 0,
        failed_jobs: int = 0,
        total_records: int = 0,
        status: str = "pending",
    ) -> None:
        """Create or update a daily summary."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_summary_daily (
                        id, date, window_name, total_jobs, succeeded_jobs, failed_jobs,
                        total_records, status, created_at
                    )
                    VALUES (:id, :date, :window_name, :total_jobs, :succeeded_jobs, :failed_jobs,
                            :total_records, :status, :now)
                    ON CONFLICT (date, window_name) DO UPDATE SET
                        total_jobs = EXCLUDED.total_jobs,
                        succeeded_jobs = EXCLUDED.succeeded_jobs,
                        failed_jobs = EXCLUDED.failed_jobs,
                        total_records = EXCLUDED.total_records,
                        status = EXCLUDED.status
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "date": summary_date,
                    "window_name": window_name,
                    "total_jobs": total_jobs,
                    "succeeded_jobs": succeeded_jobs,
                    "failed_jobs": failed_jobs,
                    "total_records": total_records,
                    "status": status,
                    "now": now_utc(),
                },
            )

    def get_summary(self, summary_date: date, window_name: str) -> Optional[dict]:
        """Get summary for a date/window."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, date, window_name, total_jobs, succeeded_jobs, failed_jobs,
                           total_records, status, created_at
                    FROM ifa2.archive_summary_daily
                    WHERE date = :date AND window_name = :window_name
                    """
                ),
                {"date": summary_date, "window_name": window_name},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "date": row.date,
                "window_name": row.window_name,
                "total_jobs": row.total_jobs,
                "succeeded_jobs": row.succeeded_jobs,
                "failed_jobs": row.failed_jobs,
                "total_records": row.total_records,
                "status": row.status,
                "created_at": row.created_at,
            }

    def list_summaries(self, limit: int = 30) -> list[dict]:
        """List recent summaries."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, date, window_name, total_jobs, succeeded_jobs, failed_jobs,
                           total_records, status, created_at
                    FROM ifa2.archive_summary_daily
                    ORDER BY date DESC, window_name DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()

            return [
                {
                    "id": row.id,
                    "date": row.date,
                    "window_name": row.window_name,
                    "total_jobs": row.total_jobs,
                    "succeeded_jobs": row.succeeded_jobs,
                    "failed_jobs": row.failed_jobs,
                    "total_records": row.total_records,
                    "status": row.status,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def get_recent_summary(self) -> Optional[dict]:
        """Get the most recent summary."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, date, window_name, total_jobs, succeeded_jobs, failed_jobs,
                           total_records, status, created_at
                    FROM ifa2.archive_summary_daily
                    ORDER BY date DESC, created_at DESC
                    LIMIT 1
                    """
                ),
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "date": row.date,
                "window_name": row.window_name,
                "total_jobs": row.total_jobs,
                "succeeded_jobs": row.succeeded_jobs,
                "failed_jobs": row.failed_jobs,
                "total_records": row.total_records,
                "status": row.status,
                "created_at": row.created_at,
            }
