"""Archive run persistence module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ArchiveRunStore:
    """Manages archive run state in DB."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def create_run(
        self,
        job_name: str,
        dataset_name: str,
        asset_type: str,
        window_name: str,
    ) -> str:
        """Create a new archive run record."""
        run_id = str(uuid.uuid4())

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_runs (
                        id, run_id, job_name, dataset_name, asset_type, window_name,
                        status, started_at, created_at
                    )
                    VALUES (:id, :run_id, :job_name, :dataset_name, :asset_type, :window_name,
                            'running', :now, :now)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "run_id": run_id,
                    "job_name": job_name,
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "window_name": window_name,
                    "now": now_utc(),
                },
            )

        return run_id

    def update_status(
        self,
        run_id: str,
        status: str,
        records_processed: Optional[int] = None,
        error_summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update run status."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ifa2.archive_runs
                    SET status = :status,
                        records_processed = COALESCE(:records_processed, records_processed),
                        error_summary = :error_summary,
                        error_message = :error_message,
                        completed_at = CASE WHEN :status IN ('succeeded', 'failed', 'timed_out')
                                           THEN :now ELSE completed_at END
                    WHERE run_id = :run_id
                    """
                ),
                {
                    "run_id": run_id,
                    "status": status,
                    "records_processed": records_processed,
                    "error_summary": error_summary,
                    "error_message": error_message,
                    "now": now_utc(),
                },
            )

    def get_run(self, run_id: str) -> Optional[dict]:
        """Get run by ID."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, run_id, job_name, dataset_name, asset_type, window_name,
                           started_at, completed_at, status, records_processed,
                           error_summary, error_message, created_at
                    FROM ifa2.archive_runs
                    WHERE run_id = :run_id
                    """
                ),
                {"run_id": run_id},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "run_id": row.run_id,
                "job_name": row.job_name,
                "dataset_name": row.dataset_name,
                "asset_type": row.asset_type,
                "window_name": row.window_name,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "status": row.status,
                "records_processed": row.records_processed or 0,
                "error_summary": row.error_summary,
                "error_message": row.error_message,
                "created_at": row.created_at,
            }

    def get_latest_for_job(self, job_name: str) -> Optional[dict]:
        """Get the most recent run for a job."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, run_id, job_name, dataset_name, asset_type, window_name,
                           started_at, completed_at, status, records_processed,
                           error_summary, error_message, created_at
                    FROM ifa2.archive_runs
                    WHERE job_name = :job_name
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                ),
                {"job_name": job_name},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "run_id": row.run_id,
                "job_name": row.job_name,
                "dataset_name": row.dataset_name,
                "asset_type": row.asset_type,
                "window_name": row.window_name,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "status": row.status,
                "records_processed": row.records_processed or 0,
                "error_summary": row.error_summary,
                "error_message": row.error_message,
                "created_at": row.created_at,
            }

    def list_recent(self, limit: int = 10) -> list[dict]:
        """List recent runs."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, run_id, job_name, dataset_name, asset_type, window_name,
                           started_at, completed_at, status, records_processed,
                           error_summary, error_message, created_at
                    FROM ifa2.archive_runs
                    ORDER BY started_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()

            return [
                {
                    "id": row.id,
                    "run_id": row.run_id,
                    "job_name": row.job_name,
                    "dataset_name": row.dataset_name,
                    "asset_type": row.asset_type,
                    "window_name": row.window_name,
                    "started_at": row.started_at,
                    "completed_at": row.completed_at,
                    "status": row.status,
                    "records_processed": row.records_processed or 0,
                    "error_summary": row.error_summary,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
