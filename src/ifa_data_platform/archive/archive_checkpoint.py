"""Archive checkpoint persistence for resume capability."""

from __future__ import annotations

import uuid
from datetime import datetime, date, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ArchiveCheckpointStore:
    """Manages archive checkpoint in DB for resume capability.

    Tracks:
    - dataset_name, asset_type: Primary key
    - backfill_start, backfill_end: Backfill range
    - last_completed_date: Daily progress watermark
    - last_completed_at: Intraday progress watermark for minute/15min datasets
    - shard_id, batch_no: Shard/batch tracking
    - status: Current checkpoint status
    """

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert_checkpoint(
        self,
        dataset_name: str,
        asset_type: str,
        backfill_start: Optional[date] = None,
        backfill_end: Optional[date] = None,
        last_completed_date: Optional[date] = None,
        last_completed_at: Optional[datetime] = None,
        shard_id: Optional[str] = None,
        batch_no: Optional[int] = None,
        status: str = "pending",
    ) -> None:
        """Create or update a checkpoint."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_checkpoints (
                        id, dataset_name, asset_type, backfill_start, backfill_end,
                        last_completed_date, last_completed_at, shard_id, batch_no, status, updated_at, created_at
                    )
                    VALUES (:id, :dataset_name, :asset_type, :backfill_start, :backfill_end,
                            :last_completed_date, :last_completed_at, :shard_id, :batch_no, :status, :now, :now)
                    ON CONFLICT (dataset_name, asset_type) DO UPDATE SET
                        backfill_start = COALESCE(EXCLUDED.backfill_start, ifa2.archive_checkpoints.backfill_start),
                        backfill_end = COALESCE(EXCLUDED.backfill_end, ifa2.archive_checkpoints.backfill_end),
                        last_completed_date = COALESCE(EXCLUDED.last_completed_date, ifa2.archive_checkpoints.last_completed_date),
                        last_completed_at = COALESCE(EXCLUDED.last_completed_at, ifa2.archive_checkpoints.last_completed_at),
                        shard_id = COALESCE(EXCLUDED.shard_id, ifa2.archive_checkpoints.shard_id),
                        batch_no = COALESCE(EXCLUDED.batch_no, ifa2.archive_checkpoints.batch_no),
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "id": gen_uuid(),
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "backfill_start": backfill_start,
                    "backfill_end": backfill_end,
                    "last_completed_date": last_completed_date,
                    "last_completed_at": last_completed_at,
                    "shard_id": shard_id,
                    "batch_no": batch_no,
                    "status": status,
                    "now": now_utc(),
                },
            )

    def get_checkpoint(self, dataset_name: str, asset_type: str) -> Optional[dict]:
        """Get checkpoint for a dataset/asset_type."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, asset_type, backfill_start, backfill_end,
                           last_completed_date, last_completed_at, shard_id, batch_no, status, updated_at, created_at
                    FROM ifa2.archive_checkpoints
                    WHERE dataset_name = :dataset_name AND asset_type = :asset_type
                    """
                ),
                {"dataset_name": dataset_name, "asset_type": asset_type},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "dataset_name": row.dataset_name,
                "asset_type": row.asset_type,
                "backfill_start": row.backfill_start,
                "backfill_end": row.backfill_end,
                "last_completed_date": row.last_completed_date,
                "last_completed_at": row.last_completed_at,
                "shard_id": row.shard_id,
                "batch_no": row.batch_no,
                "status": row.status,
                "updated_at": row.updated_at,
                "created_at": row.created_at,
            }

    def update_progress(
        self,
        dataset_name: str,
        asset_type: str,
        last_completed_date: date,
        shard_id: Optional[str] = None,
        batch_no: Optional[int] = None,
        status: str = "in_progress",
    ) -> None:
        """Update progress after processing."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ifa2.archive_checkpoints
                    SET last_completed_date = :last_completed_date,
                        shard_id = COALESCE(:shard_id, shard_id),
                        batch_no = COALESCE(:batch_no, batch_no),
                        status = :status,
                        updated_at = :now
                    WHERE dataset_name = :dataset_name AND asset_type = :asset_type
                    """
                ),
                {
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "last_completed_date": last_completed_date,
                    "shard_id": shard_id,
                    "batch_no": batch_no,
                    "status": status,
                    "now": now_utc(),
                },
            )

    def mark_completed(self, dataset_name: str, asset_type: str) -> None:
        """Mark checkpoint as completed."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ifa2.archive_checkpoints
                    SET status = 'completed', updated_at = :now
                    WHERE dataset_name = :dataset_name AND asset_type = :asset_type
                    """
                ),
                {
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "now": now_utc(),
                },
            )

    def list_checkpoints(self) -> list[dict]:
        """List all checkpoints."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, asset_type, backfill_start, backfill_end,
                           last_completed_date, last_completed_at, shard_id, batch_no, status, updated_at, created_at
                    FROM ifa2.archive_checkpoints
                    ORDER BY updated_at DESC
                    """
                ),
            ).fetchall()

            return [
                {
                    "id": row.id,
                    "dataset_name": row.dataset_name,
                    "asset_type": row.asset_type,
                    "backfill_start": row.backfill_start,
                    "backfill_end": row.backfill_end,
                    "last_completed_date": row.last_completed_date,
                    "last_completed_at": row.last_completed_at,
                    "shard_id": row.shard_id,
                    "batch_no": row.batch_no,
                    "status": row.status,
                    "updated_at": row.updated_at,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
