"""Dataset version registry and history persistence for Job 4.

Provides version tracking for low-frequency datasets with:
- Dataset version registry (dataset_version_id, dataset_name, source_name, run_id,
  created_at_utc, promoted_at_utc, status, is_active, supersedes_version_id,
  watermark, notes/metadata)
- Promote/active semantics (candidate -> active current)
- History tables for trade_cal and stock_basic versions
- As-of query support
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class VersionStatus:
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class DatasetVersionRegistry:
    """Registry for tracking dataset versions.

    Manages version lifecycle: candidate -> active (via promote).
    """

    def __init__(self) -> None:
        self.engine = make_engine()

    def create_version(
        self,
        dataset_name: str,
        source_name: str,
        run_id: str,
        watermark: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Create a new candidate version for a dataset.

        Args:
            dataset_name: Name of the dataset.
            source_name: Name of the source (e.g., 'tushare').
            run_id: The run ID that created this version.
            watermark: Optional watermark value.
            metadata: Optional metadata dict.

        Returns:
            Dataset version ID (UUID string).
        """
        version_id = str(uuid.uuid4())
        created_at = now_utc()

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.dataset_versions (
                        id, dataset_name, source_name, run_id, 
                        created_at_utc, promoted_at_utc, status, is_active,
                        supersedes_version_id, watermark, metadata,
                        created_at
                    )
                    VALUES (
                        :id, :dataset_name, :source_name, :run_id,
                        :created_at_utc, NULL, :status, 0,
                        :supersedes_version_id, :watermark, :metadata,
                        now()
                    )
                    """
                ),
                {
                    "id": version_id,
                    "dataset_name": dataset_name,
                    "source_name": source_name,
                    "run_id": run_id,
                    "created_at_utc": created_at,
                    "status": VersionStatus.CANDIDATE,
                    "supersedes_version_id": self._get_active_version_id(dataset_name),
                    "watermark": watermark,
                    "metadata": str(metadata) if metadata else None,
                },
            )

        return version_id

    def _get_active_version_id(self, dataset_name: str) -> Optional[str]:
        """Get the active version ID for a dataset."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id FROM ifa2.dataset_versions
                    WHERE dataset_name = :dataset_name AND is_active = 1
                    LIMIT 1
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()
            return row.id if row else None

    def promote(
        self,
        dataset_name: str,
        version_id: str,
    ) -> bool:
        """Promote a candidate version to active (current).

        Args:
            dataset_name: Name of the dataset.
            version_id: ID of the version to promote.

        Returns:
            True if successful.
        """
        with self.engine.begin() as conn:
            current_active = conn.execute(
                text(
                    """
                    SELECT id FROM ifa2.dataset_versions
                    WHERE dataset_name = :dataset_name AND is_active = 1
                    LIMIT 1
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()

            if current_active:
                conn.execute(
                    text(
                        """
                        UPDATE ifa2.dataset_versions
                        SET is_active = 0, status = :new_status
                        WHERE id = :old_id
                        """
                    ),
                    {
                        "new_status": VersionStatus.SUPERSEDED,
                        "old_id": current_active.id,
                    },
                )

            promoted_at = now_utc()
            conn.execute(
                text(
                    """
                    UPDATE ifa2.dataset_versions
                    SET is_active = 1, status = :new_status, promoted_at_utc = :promoted_at
                    WHERE id = :new_id
                    """
                ),
                {
                    "new_status": VersionStatus.ACTIVE,
                    "promoted_at": promoted_at,
                    "new_id": version_id,
                },
            )

        return True

    def get_active_version(self, dataset_name: str) -> Optional[dict]:
        """Get the active version for a dataset.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Version dict if found, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, source_name, run_id, 
                           created_at_utc, promoted_at_utc, status, is_active,
                           supersedes_version_id, watermark, metadata,
                           created_at
                    FROM ifa2.dataset_versions
                    WHERE dataset_name = :dataset_name AND is_active = 1
                    LIMIT 1
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "dataset_name": row.dataset_name,
                "source_name": row.source_name,
                "run_id": row.run_id,
                "created_at_utc": row.created_at_utc,
                "promoted_at_utc": row.promoted_at_utc,
                "status": row.status,
                "is_active": bool(row.is_active),
                "supersedes_version_id": row.supersedes_version_id,
                "watermark": row.watermark,
                "metadata": row.metadata,
                "created_at": row.created_at,
            }

    def get_version_by_id(self, version_id: str) -> Optional[dict]:
        """Get a version by ID.

        Args:
            version_id: Version ID.

        Returns:
            Version dict if found, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, source_name, run_id, 
                           created_at_utc, promoted_at_utc, status, is_active,
                           supersedes_version_id, watermark, metadata,
                           created_at
                    FROM ifa2.dataset_versions
                    WHERE id = :id
                    """
                ),
                {"id": version_id},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "dataset_name": row.dataset_name,
                "source_name": row.source_name,
                "run_id": row.run_id,
                "created_at_utc": row.created_at_utc,
                "promoted_at_utc": row.promoted_at_utc,
                "status": row.status,
                "is_active": bool(row.is_active),
                "supersedes_version_id": row.supersedes_version_id,
                "watermark": row.watermark,
                "metadata": row.metadata,
                "created_at": row.created_at,
            }

    def get_version_at_promoted_time(
        self,
        dataset_name: str,
        promoted_at_or_before: datetime,
    ) -> Optional[dict]:
        """Get the version that was active at a given time.

        Args:
            dataset_name: Name of the dataset.
            promoted_at_or_before: Date/time to query at.

        Returns:
            Version dict if found, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, source_name, run_id, 
                           created_at_utc, promoted_at_utc, status, is_active,
                           supersedes_version_id, watermark, metadata,
                           created_at
                    FROM ifa2.dataset_versions
                    WHERE dataset_name = :dataset_name 
                      AND promoted_at_utc <= :promoted_at_or_before
                    ORDER BY promoted_at_utc DESC
                    LIMIT 1
                    """
                ),
                {
                    "dataset_name": dataset_name,
                    "promoted_at_or_before": promoted_at_or_before,
                },
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "dataset_name": row.dataset_name,
                "source_name": row.source_name,
                "run_id": row.run_id,
                "created_at_utc": row.created_at_utc,
                "promoted_at_utc": row.promoted_at_utc,
                "status": row.status,
                "is_active": bool(row.is_active),
                "supersedes_version_id": row.supersedes_version_id,
                "watermark": row.watermark,
                "metadata": row.metadata,
                "created_at": row.created_at,
            }

    def list_versions(self, dataset_name: str, limit: int = 10) -> list[dict]:
        """List versions for a dataset.

        Args:
            dataset_name: Name of the dataset.
            limit: Maximum number of versions to return.

        Returns:
            List of version dicts.
        """
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, source_name, run_id, 
                           created_at_utc, promoted_at_utc, status, is_active,
                           supersedes_version_id, watermark, metadata,
                           created_at
                    FROM ifa2.dataset_versions
                    WHERE dataset_name = :dataset_name
                    ORDER BY created_at_utc DESC
                    LIMIT :limit
                    """
                ),
                {"dataset_name": dataset_name, "limit": limit},
            ).fetchall()

            return [
                {
                    "id": row.id,
                    "dataset_name": row.dataset_name,
                    "source_name": row.source_name,
                    "run_id": row.run_id,
                    "created_at_utc": row.created_at_utc,
                    "promoted_at_utc": row.promoted_at_utc,
                    "status": row.status,
                    "is_active": bool(row.is_active),
                    "supersedes_version_id": row.supersedes_version_id,
                    "watermark": row.watermark,
                    "metadata": row.metadata,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class TradeCalHistory:
    """Historical trade calendar records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version.

        Args:
            version_id: The dataset version ID.
            records: List of trade calendar records.

        Returns:
            Number of records stored.
        """
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.trade_cal_history (
                            id, version_id, cal_date, exchange, is_open, pretrade_date,
                            created_at
                        )
                        VALUES (
                            :id, :version_id, :cal_date, :exchange, :is_open, :pretrade_date,
                            now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "cal_date": rec["cal_date"],
                        "exchange": rec["exchange"],
                        "is_open": 1 if rec["is_open"] else 0,
                        "pretrade_date": rec.get("pretrade_date"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Query historical records by version.

        Args:
            version_id: The dataset version ID.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            List of historical records.
        """
        with self.engine.begin() as conn:
            if start_date and end_date:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, cal_date, exchange, is_open,
                               pretrade_date, created_at
                        FROM ifa2.trade_cal_history
                        WHERE version_id = :version_id
                          AND cal_date BETWEEN :start_date AND :end_date
                        ORDER BY cal_date
                        """
                    ),
                    {
                        "version_id": version_id,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                ).fetchall()
            elif start_date:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, cal_date, exchange, is_open,
                               pretrade_date, created_at
                        FROM ifa2.trade_cal_history
                        WHERE version_id = :version_id
                          AND cal_date >= :start_date
                        ORDER BY cal_date
                        """
                    ),
                    {"version_id": version_id, "start_date": start_date},
                ).fetchall()
            elif end_date:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, cal_date, exchange, is_open,
                               pretrade_date, created_at
                        FROM ifa2.trade_cal_history
                        WHERE version_id = :version_id
                          AND cal_date <= :end_date
                        ORDER BY cal_date
                        """
                    ),
                    {"version_id": version_id, "end_date": end_date},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, cal_date, exchange, is_open,
                               pretrade_date, created_at
                        FROM ifa2.trade_cal_history
                        WHERE version_id = :version_id
                        ORDER BY cal_date
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "cal_date": row.cal_date,
                    "exchange": row.exchange,
                    "is_open": bool(row.is_open),
                    "pretrade_date": row.pretrade_date,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class StockBasicHistory:
    """Historical stock basic records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version.

        Args:
            version_id: The dataset version ID.
            records: List of stock basic records.

        Returns:
            Number of records stored.
        """
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.stock_basic_history (
                            id, version_id, ts_code, symbol, name, area, industry,
                            market, list_status, list_date, delist_date, is_hs,
                            created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :symbol, :name, :area, :industry,
                            :market, :list_status, :list_date, :delist_date, :is_hs,
                            now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "symbol": rec.get("symbol"),
                        "name": rec.get("name"),
                        "area": rec.get("area"),
                        "industry": rec.get("industry"),
                        "market": rec.get("market"),
                        "list_status": rec.get("list_status"),
                        "list_date": rec.get("list_date"),
                        "delist_date": rec.get("delist_date"),
                        "is_hs": rec.get("is_hs"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query historical records by version.

        Args:
            version_id: The dataset version ID.
            limit: Optional record limit.

        Returns:
            List of historical records.
        """
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, symbol, name, area, industry,
                               market, list_status, list_date, delist_date, is_hs,
                               created_at
                        FROM ifa2.stock_basic_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, symbol, name, area, industry,
                               market, list_status, list_date, delist_date, is_hs,
                               created_at
                        FROM ifa2.stock_basic_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "ts_code": row.ts_code,
                    "symbol": row.symbol,
                    "name": row.name,
                    "area": row.area,
                    "industry": row.industry,
                    "market": row.market,
                    "list_status": row.list_status,
                    "list_date": row.list_date,
                    "delist_date": row.delist_date,
                    "is_hs": row.is_hs,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
