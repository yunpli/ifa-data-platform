"""Archive job persistence module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ArchiveJobStore:
    """Manages archive job definitions in DB."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def create_job(
        self,
        job_name: str,
        dataset_name: str,
        asset_type: str,
        pool_name: str = "",
        scope_name: str = "",
        is_enabled: bool = True,
    ) -> str:
        """Create a new archive job."""
        job_id = str(uuid.uuid4())

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_jobs (
                        id, job_name, dataset_name, asset_type, pool_name, scope_name,
                        is_enabled, created_at, updated_at
                    )
                    VALUES (:id, :job_name, :dataset_name, :asset_type, :pool_name, :scope_name,
                            :is_enabled, :now, :now)
                    ON CONFLICT (job_name) DO UPDATE SET
                        dataset_name = EXCLUDED.dataset_name,
                        asset_type = EXCLUDED.asset_type,
                        pool_name = EXCLUDED.pool_name,
                        scope_name = EXCLUDED.scope_name,
                        is_enabled = EXCLUDED.is_enabled,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "id": job_id,
                    "job_name": job_name,
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "pool_name": pool_name,
                    "scope_name": scope_name,
                    "is_enabled": is_enabled,
                    "now": now_utc(),
                },
            )

        return job_id

    def get_job(self, job_name: str) -> Optional[dict]:
        """Get job by name."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, job_name, dataset_name, asset_type, pool_name,
                           scope_name, is_enabled, created_at, updated_at
                    FROM ifa2.archive_jobs
                    WHERE job_name = :job_name
                    """
                ),
                {"job_name": job_name},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "job_name": row.job_name,
                "dataset_name": row.dataset_name,
                "asset_type": row.asset_type,
                "pool_name": row.pool_name,
                "scope_name": row.scope_name,
                "is_enabled": row.is_enabled,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def list_jobs(self, include_disabled: bool = False) -> list[dict]:
        """List all archive jobs."""
        with self.engine.begin() as conn:
            if include_disabled:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, job_name, dataset_name, asset_type, pool_name,
                               scope_name, is_enabled, created_at, updated_at
                        FROM ifa2.archive_jobs
                        ORDER BY created_at DESC
                        """
                    ),
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, job_name, dataset_name, asset_type, pool_name,
                               scope_name, is_enabled, created_at, updated_at
                        FROM ifa2.archive_jobs
                        WHERE is_enabled = TRUE
                        ORDER BY created_at DESC
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "job_name": row.job_name,
                    "dataset_name": row.dataset_name,
                    "asset_type": row.asset_type,
                    "pool_name": row.pool_name,
                    "scope_name": row.scope_name,
                    "is_enabled": row.is_enabled,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]

    def update_job(
        self,
        job_name: str,
        is_enabled: Optional[bool] = None,
        pool_name: Optional[str] = None,
        scope_name: Optional[str] = None,
    ) -> None:
        """Update job configuration."""
        updates = []
        params = {"job_name": job_name, "now": now_utc()}

        if is_enabled is not None:
            updates.append("is_enabled = :is_enabled")
            params["is_enabled"] = is_enabled
        if pool_name is not None:
            updates.append("pool_name = :pool_name")
            params["pool_name"] = pool_name
        if scope_name is not None:
            updates.append("scope_name = :scope_name")
            params["scope_name"] = scope_name

        if not updates:
            return

        updates.append("updated_at = :now")

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE ifa2.archive_jobs
                    SET {", ".join(updates)}
                    WHERE job_name = :job_name
                    """
                ),
                params,
            )
