"""Summary persistence for midfreq daemon execution."""

from __future__ import annotations

import uuid
import json
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


class ExecutionSummaryStore:
    """Store midfreq execution summaries to database."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store(self, summary_json: str, group_name: str, window_type: str) -> str:
        """Store execution summary to database.

        Args:
            summary_json: JSON string from GroupExecutionSummary.to_json()
            group_name: Group name
            window_type: Window type

        Returns:
            Record ID
        """
        record_id = str(uuid.uuid4())
        summary_data = json.loads(summary_json)
        started_at = datetime.fromisoformat(summary_data["started_at"])
        completed_at = datetime.fromisoformat(summary_data["completed_at"])

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.midfreq_execution_summary (
                        id, group_name, window_type, started_at, completed_at,
                        total_datasets, succeeded_datasets, failed_datasets,
                        summary_json, created_at
                    )
                    VALUES (
                        :id, :group_name, :window_type, :started_at, :completed_at,
                        :total, :succeeded, :failed,
                        :json, now()
                    )
                    """
                ),
                {
                    "id": record_id,
                    "group_name": group_name,
                    "window_type": window_type,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "total": summary_data["total_datasets"],
                    "succeeded": summary_data["succeeded_datasets"],
                    "failed": summary_data["failed_datasets"],
                    "json": summary_json,
                },
            )

        return record_id

    def query_latest(self, limit: int = 10) -> list[dict]:
        """Query latest execution summaries."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, group_name, window_type, started_at, completed_at,
                           total_datasets, succeeded_datasets, failed_datasets,
                           created_at
                    FROM ifa2.midfreq_execution_summary
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()

            return [
                {
                    "id": row.id,
                    "group_name": row.group_name,
                    "window_type": row.window_type,
                    "started_at": row.started_at,
                    "completed_at": row.completed_at,
                    "total_datasets": row.total_datasets,
                    "succeeded_datasets": row.succeeded_datasets,
                    "failed_datasets": row.failed_datasets,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def query_by_date(self, run_date: date) -> list[dict]:
        """Query summaries by date."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, group_name, window_type, started_at, completed_at,
                           total_datasets, succeeded_datasets, failed_datasets,
                           created_at
                    FROM ifa2.midfreq_execution_summary
                    WHERE DATE(started_at) = :run_date
                    ORDER BY started_at DESC
                    """
                ),
                {"run_date": run_date},
            ).fetchall()

            return [
                {
                    "id": row.id,
                    "group_name": row.group_name,
                    "window_type": row.window_type,
                    "started_at": row.started_at,
                    "completed_at": row.completed_at,
                    "total_datasets": row.total_datasets,
                    "succeeded_datasets": row.succeeded_datasets,
                    "failed_datasets": row.failed_datasets,
                }
                for row in rows
            ]


class DaemonWatchdog:
    """Simple watchdog for midfreq daemon."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def check_health(self) -> dict:
        """Check daemon health / freshness."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT latest_loop_at, latest_status
                    FROM ifa2.midfreq_daemon_state
                    WHERE daemon_name = 'midfreq_daemon'
                    """
                ),
            ).fetchone()

            if not row or not row.latest_loop_at:
                return {
                    "status": "unknown",
                    "message": "Daemon never run",
                    "last_heartbeat": None,
                }

            now = datetime.now(timezone.utc)
            elapsed = (now - row.latest_loop_at).total_seconds()
            elapsed_min = elapsed / 60

            # Freshness threshold: 10 minutes
            if elapsed_min > 10:
                status = "stale"
            else:
                status = "healthy"

            return {
                "status": status,
                "message": f"Last run {elapsed_min:.1f} minutes ago",
                "last_heartbeat": row.latest_loop_at,
                "last_status": row.latest_status,
            }

    def needs_restart(self) -> bool:
        """Check if daemon needs restart."""
        health = self.check_health()
        return health["status"] in ["unknown", "stale", "failed"]

    def record_heartbeat(self) -> None:
        """Record daemon heartbeat."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.midfreq_daemon_state (
                        daemon_name, latest_loop_at, latest_status, created_at
                    )
                    VALUES (:name, now(), 'running', now())
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        latest_loop_at = now(),
                        latest_status = 'running'
                    """
                ),
                {"name": "midfreq_daemon"},
            )
