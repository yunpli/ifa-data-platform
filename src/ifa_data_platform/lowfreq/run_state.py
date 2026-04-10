"""Run state manager for low-frequency dataset jobs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.models import RunState


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class RunStateManager:
    """Manages run-level state for low-frequency dataset jobs.

    Tracks execution state per dataset, including status, records processed,
    watermark, and error messages. Reuses existing job_runs table where possible.
    """

    def __init__(self) -> None:
        self.engine = make_engine()

    def create_run(
        self,
        dataset_name: str,
        dry_run: bool = False,
        run_type: str = "scheduled",
    ) -> RunState:
        """Create a new run record for a dataset.

        Args:
            dataset_name: Name of the dataset being run.
            dry_run: Whether this is a dry run.
            run_type: Type of run (scheduled, manual, etc.).

        Returns:
            RunState with initial state.
        """
        run_id = str(uuid.uuid4())
        started = now_utc()

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.lowfreq_runs (
                        id, dataset_name, status, started_at, records_processed,
                        watermark, run_type, dry_run, created_at
                    )
                    VALUES (:id, :dataset_name, :status, :started_at, 0, NULL, :run_type, :dry_run, now())
                    """
                ),
                {
                    "id": run_id,
                    "dataset_name": dataset_name,
                    "status": "pending",
                    "started_at": started,
                    "run_type": run_type,
                    "dry_run": 1 if dry_run else 0,
                },
            )

        return RunState(
            run_id=run_id,
            dataset_name=dataset_name,
            status="pending",
            started_at=started,
            records_processed=0,
            dry_run=dry_run,
        )

    def update_status(
        self,
        run_id: str,
        status: str,
        records_processed: Optional[int] = None,
        watermark: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update run status.

        Args:
            run_id: Run ID.
            status: New status (pending, running, succeeded, failed).
            records_processed: Optional record count.
            watermark: Optional watermark value.
            error_message: Optional error message.
        """
        completed_at = (
            "now()" if status in ("succeeded", "failed", "timed_out") else "NULL"
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE ifa2.lowfreq_runs
                    SET status = :status,
                        records_processed = COALESCE(:records_processed, records_processed),
                        watermark = COALESCE(:watermark, watermark),
                        error_message = :error_message,
                        completed_at = CASE WHEN :status IN ('succeeded','failed','timed_out') THEN now() ELSE completed_at END
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "status": status,
                    "records_processed": records_processed,
                    "watermark": watermark,
                    "error_message": error_message,
                },
            )

    def get(self, run_id: str) -> Optional[RunState]:
        """Get run state by ID.

        Args:
            run_id: Run ID.

        Returns:
            RunState if found, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, status, started_at, completed_at,
                           records_processed, watermark, error_message, run_type, dry_run
                    FROM ifa2.lowfreq_runs
                    WHERE id = :id
                    """
                ),
                {"id": run_id},
            ).fetchone()

            if not row:
                return None

            return RunState(
                run_id=row.id,
                dataset_name=row.dataset_name,
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                records_processed=row.records_processed or 0,
                watermark=row.watermark,
                error_message=row.error_message,
                run_type=row.run_type or "scheduled",
                dry_run=bool(row.dry_run),
            )

    def get_latest_for_dataset(self, dataset_name: str) -> Optional[RunState]:
        """Get the most recent run for a dataset.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            RunState of latest run if any, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, status, started_at, completed_at,
                           records_processed, watermark, error_message, run_type, dry_run
                    FROM ifa2.lowfreq_runs
                    WHERE dataset_name = :dataset_name
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()

            if not row:
                return None

            return RunState(
                run_id=row.id,
                dataset_name=row.dataset_name,
                status=row.status,
                started_at=row.started_at,
                completed_at=row.completed_at,
                records_processed=row.records_processed or 0,
                watermark=row.watermark,
                error_message=row.error_message,
                run_type=row.run_type or "scheduled",
                dry_run=bool(row.dry_run),
            )

    def list_recent(self, limit: int = 10) -> list[RunState]:
        """List recent runs.

        Args:
            limit: Maximum number of runs to return.

        Returns:
            List of RunState objects.
        """
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, status, started_at, completed_at,
                           records_processed, watermark, error_message, run_type, dry_run
                    FROM ifa2.lowfreq_runs
                    ORDER BY started_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()

            return [
                RunState(
                    run_id=row.id,
                    dataset_name=row.dataset_name,
                    status=row.status,
                    started_at=row.started_at,
                    completed_at=row.completed_at,
                    records_processed=row.records_processed or 0,
                    watermark=row.watermark,
                    error_message=row.error_message,
                    run_type=row.run_type or "scheduled",
                    dry_run=bool(row.dry_run),
                )
                for row in rows
            ]
