from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.runtime.job_state import JobStatus


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobRunRecord:
    id: str
    job_name: str
    status: str


class JobStore:
    def __init__(self) -> None:
        self.engine = make_engine()

    def create_run(self, job_name: str) -> JobRunRecord:
        run_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.job_runs (id, job_name, status, started_at, created_at)
                    VALUES (:id, :job_name, :status, now(), now())
                    """
                ),
                {"id": run_id, "job_name": job_name, "status": JobStatus.PENDING.value},
            )
        return JobRunRecord(id=run_id, job_name=job_name, status=JobStatus.PENDING.value)

    def update_status(self, run_id: str, status: JobStatus, error_message: str | None = None) -> None:
        sql = """
        UPDATE ifa2.job_runs
        SET status = :status,
            error_message = :error_message,
            completed_at = CASE WHEN :status IN ('succeeded','failed','timed_out') THEN now() ELSE completed_at END
        WHERE id = :id
        """
        with self.engine.begin() as conn:
            conn.execute(text(sql), {"id": run_id, "status": status.value, "error_message": error_message})

    def recent_runs(self, limit: int = 10) -> list[dict]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT id::text, job_name, status, started_at, completed_at, error_message FROM ifa2.job_runs ORDER BY started_at DESC LIMIT :limit"
                ),
                {"limit": limit},
            )
            return [dict(r._mapping) for r in rows]
