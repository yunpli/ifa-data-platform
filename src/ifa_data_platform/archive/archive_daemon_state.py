"""Archive daemon state persistence (DB-backed)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ArchiveDaemonStateStore:
    """DB-backed archive daemon state as primary source.

    Tracks daemon-level state: last loop time, is_running, last run status, etc.
    """

    def __init__(self, daemon_name: str = "default") -> None:
        self.engine = make_engine()
        self.daemon_name = daemon_name

    def get_state(self) -> dict:
        """Get daemon state from DB."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT daemon_name, last_loop_at_utc, last_run_job,
                           last_run_status, last_success_at_utc, is_running, updated_at_utc
                    FROM ifa2.archive_daemon_state
                    WHERE daemon_name = :daemon_name
                    """
                ),
                {"daemon_name": self.daemon_name},
            ).fetchone()

            if not row:
                return {
                    "daemon_name": self.daemon_name,
                    "last_loop_at_utc": None,
                    "last_run_job": None,
                    "last_run_status": None,
                    "last_success_at_utc": None,
                    "is_running": False,
                    "updated_at_utc": None,
                }

            return {
                "daemon_name": row.daemon_name,
                "last_loop_at_utc": row.last_loop_at_utc,
                "last_run_job": row.last_run_job,
                "last_run_status": row.last_run_status,
                "last_success_at_utc": row.last_success_at_utc,
                "is_running": row.is_running,
                "updated_at_utc": row.updated_at_utc,
            }

    def update_loop(self, job_name: Optional[str], status: Optional[str]) -> None:
        """Update daemon state after a loop iteration."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_daemon_state (id, daemon_name, last_loop_at_utc, last_run_job, last_run_status, updated_at_utc)
                    VALUES (:id, :daemon_name, :now, :job_name, :status, :now)
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        last_loop_at_utc = EXCLUDED.last_loop_at_utc,
                        last_run_job = EXCLUDED.last_run_job,
                        last_run_status = EXCLUDED.last_run_status,
                        updated_at_utc = EXCLUDED.updated_at_utc
                    """
                ),
                {
                    "id": gen_uuid(),
                    "daemon_name": self.daemon_name,
                    "now": now_utc(),
                    "job_name": job_name,
                    "status": status,
                },
            )

    def mark_running(self, is_running: bool) -> None:
        """Mark daemon as running/not running."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_daemon_state (id, daemon_name, is_running, updated_at_utc)
                    VALUES (:id, :daemon_name, :is_running, :now)
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        is_running = EXCLUDED.is_running,
                        updated_at_utc = EXCLUDED.updated_at_utc
                    """
                ),
                {
                    "id": gen_uuid(),
                    "daemon_name": self.daemon_name,
                    "is_running": is_running,
                    "now": now_utc(),
                },
            )

    def mark_success(self, job_name: str) -> None:
        """Mark a job as successful."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_daemon_state (id, daemon_name, last_success_at_utc, last_run_job, last_run_status, updated_at_utc)
                    VALUES (:id, :daemon_name, :now, :job_name, 'succeeded', :now)
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        last_success_at_utc = EXCLUDED.last_success_at_utc,
                        last_run_job = EXCLUDED.last_run_job,
                        last_run_status = 'succeeded',
                        updated_at_utc = EXCLUDED.updated_at_utc
                    """
                ),
                {
                    "id": gen_uuid(),
                    "daemon_name": self.daemon_name,
                    "now": now_utc(),
                    "job_name": job_name,
                },
            )

    def mark_failed(self, job_name: str, error: Optional[str] = None) -> None:
        """Mark a job as failed."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_daemon_state (id, daemon_name, last_success_at_utc, last_run_job, last_run_status, updated_at_utc)
                    VALUES (:id, :daemon_name, NULL, :job_name, 'failed', :now)
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        last_success_at_utc = NULL,
                        last_run_job = EXCLUDED.last_run_job,
                        last_run_status = 'failed',
                        updated_at_utc = EXCLUDED.updated_at_utc
                    """
                ),
                {
                    "id": gen_uuid(),
                    "daemon_name": self.daemon_name,
                    "now": now_utc(),
                    "job_name": job_name,
                },
            )
