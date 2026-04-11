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


class IndexBasicHistory:
    """Historical index basic records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version."""
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.index_basic_history (
                            id, version_id, ts_code, name, market, publisher,
                            category, base_date, base_point, list_date, weight_rule,
                            created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :name, :market, :publisher,
                            :category, :base_date, :base_point, :list_date, :weight_rule,
                            now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "name": rec.get("name"),
                        "market": rec.get("market"),
                        "publisher": rec.get("publisher"),
                        "category": rec.get("category"),
                        "base_date": rec.get("base_date"),
                        "base_point": rec.get("base_point"),
                        "list_date": rec.get("list_date"),
                        "weight_rule": rec.get("weight_rule"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query historical records by version."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, name, market, publisher,
                               category, base_date, base_point, list_date, weight_rule,
                               created_at
                        FROM ifa2.index_basic_history
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
                        SELECT id, version_id, ts_code, name, market, publisher,
                               category, base_date, base_point, list_date, weight_rule,
                               created_at
                        FROM ifa2.index_basic_history
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
                    "name": row.name,
                    "market": row.market,
                    "publisher": row.publisher,
                    "category": row.category,
                    "base_date": row.base_date,
                    "base_point": row.base_point,
                    "list_date": row.list_date,
                    "weight_rule": row.weight_rule,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class FundBasicEtfHistory:
    """Historical fund basic ETF records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version."""
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.fund_basic_etf_history (
                            id, version_id, ts_code, name, market, fund_type,
                            management, custodian, list_date, due_date, issue_date,
                            delist_date, invest_type, benchmark, status, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :name, :market, :fund_type,
                            :management, :custodian, :list_date, :due_date, :issue_date,
                            :delist_date, :invest_type, :benchmark, :status, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "name": rec.get("name"),
                        "market": rec.get("market"),
                        "fund_type": rec.get("fund_type"),
                        "management": rec.get("management"),
                        "custodian": rec.get("custodian"),
                        "list_date": rec.get("list_date"),
                        "due_date": rec.get("due_date"),
                        "issue_date": rec.get("issue_date"),
                        "delist_date": rec.get("delist_date"),
                        "invest_type": rec.get("invest_type"),
                        "benchmark": rec.get("benchmark"),
                        "status": rec.get("status"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query historical records by version."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, name, market, fund_type,
                               management, custodian, list_date, due_date, issue_date,
                               delist_date, invest_type, benchmark, status, created_at
                        FROM ifa2.fund_basic_etf_history
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
                        SELECT id, version_id, ts_code, name, market, fund_type,
                               management, custodian, list_date, due_date, issue_date,
                               delist_date, invest_type, benchmark, status, created_at
                        FROM ifa2.fund_basic_etf_history
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
                    "name": row.name,
                    "market": row.market,
                    "fund_type": row.fund_type,
                    "management": row.management,
                    "custodian": row.custodian,
                    "list_date": row.list_date,
                    "due_date": row.due_date,
                    "issue_date": row.issue_date,
                    "delist_date": row.delist_date,
                    "invest_type": row.invest_type,
                    "benchmark": row.benchmark,
                    "status": row.status,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class SwIndustryMappingHistory:
    """Historical SW industry mapping records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version."""
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.sw_industry_mapping_history (
                            id, version_id, index_code, industry_name, level,
                            parent_code, src, member_ts_code, member_name,
                            in_date, out_date, is_active, created_at
                        )
                        VALUES (
                            :id, :version_id, :index_code, :industry_name, :level,
                            :parent_code, :src, :member_ts_code, :member_name,
                            :in_date, :out_date, :is_active, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "index_code": rec["index_code"],
                        "industry_name": rec.get("industry_name"),
                        "level": rec.get("level"),
                        "parent_code": rec.get("parent_code"),
                        "src": rec.get("src"),
                        "member_ts_code": rec.get("member_ts_code"),
                        "member_name": rec.get("member_name"),
                        "in_date": rec.get("in_date"),
                        "out_date": rec.get("out_date"),
                        "is_active": 1 if rec.get("is_active", True) else 0,
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query historical records by version."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, index_code, industry_name, level,
                               parent_code, src, member_ts_code, member_name,
                               in_date, out_date, is_active, created_at
                        FROM ifa2.sw_industry_mapping_history
                        WHERE version_id = :version_id
                        ORDER BY index_code, level
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, index_code, industry_name, level,
                               parent_code, src, member_ts_code, member_name,
                               in_date, out_date, is_active, created_at
                        FROM ifa2.sw_industry_mapping_history
                        WHERE version_id = :version_id
                        ORDER BY index_code, level
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "index_code": row.index_code,
                    "industry_name": row.industry_name,
                    "level": row.level,
                    "parent_code": row.parent_code,
                    "src": row.src,
                    "member_ts_code": row.member_ts_code,
                    "member_name": row.member_name,
                    "in_date": row.in_date,
                    "out_date": row.out_date,
                    "is_active": bool(row.is_active),
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class AnnouncementsHistory:
    """Historical announcement records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version."""
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.announcements_history (
                            id, version_id, ann_date, ts_code, name, title,
                            url, rec_time, created_at
                        )
                        VALUES (
                            :id, :version_id, :ann_date, :ts_code, :name, :title,
                            :url, :rec_time, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ann_date": rec["ann_date"],
                        "ts_code": rec["ts_code"],
                        "name": rec.get("name"),
                        "title": rec.get("title"),
                        "url": rec.get("url"),
                        "rec_time": rec.get("rec_time"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query historical records by version."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ann_date, ts_code, name, title,
                               url, rec_time, created_at
                        FROM ifa2.announcements_history
                        WHERE version_id = :version_id
                        ORDER BY ann_date DESC, ts_code
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ann_date, ts_code, name, title,
                               url, rec_time, created_at
                        FROM ifa2.announcements_history
                        WHERE version_id = :version_id
                        ORDER BY ann_date DESC, ts_code
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "ann_date": row.ann_date,
                    "ts_code": row.ts_code,
                    "name": row.name,
                    "title": row.title,
                    "url": row.url,
                    "rec_time": row.rec_time,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class NewsHistory:
    """Historical news records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version."""
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.news_history (
                            id, version_id, datetime, classify, title, source,
                            url, content, created_at
                        )
                        VALUES (
                            :id, :version_id, :datetime, :classify, :title, :source,
                            :url, :content, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "datetime": rec["datetime"],
                        "classify": rec.get("classify"),
                        "title": rec.get("title"),
                        "source": rec.get("source"),
                        "url": rec.get("url"),
                        "content": rec.get("content"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query historical records by version."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, datetime, classify, title, source,
                               url, content, created_at
                        FROM ifa2.news_history
                        WHERE version_id = :version_id
                        ORDER BY datetime DESC
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, datetime, classify, title, source,
                               url, content, created_at
                        FROM ifa2.news_history
                        WHERE version_id = :version_id
                        ORDER BY datetime DESC
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "datetime": row.datetime,
                    "classify": row.classify,
                    "title": row.title,
                    "source": row.source,
                    "url": row.url,
                    "content": row.content,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class ResearchReportsHistory:
    """Historical research report records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version."""
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.research_reports_history (
                            id, version_id, trade_date, ts_code, name, title,
                            report_type, author, inst_csname, ind_name, url,
                            created_at
                        )
                        VALUES (
                            :id, :version_id, :trade_date, :ts_code, :name, :title,
                            :report_type, :author, :inst_csname, :ind_name, :url,
                            now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "trade_date": rec["trade_date"],
                        "ts_code": rec["ts_code"],
                        "name": rec.get("name"),
                        "title": rec.get("title"),
                        "report_type": rec.get("report_type"),
                        "author": rec.get("author"),
                        "inst_csname": rec.get("inst_csname"),
                        "ind_name": rec.get("ind_name"),
                        "url": rec.get("url"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query historical records by version."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, trade_date, ts_code, name, title,
                               report_type, author, inst_csname, ind_name, url,
                               created_at
                        FROM ifa2.research_reports_history
                        WHERE version_id = :version_id
                        ORDER BY trade_date DESC, ts_code
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, trade_date, ts_code, name, title,
                               report_type, author, inst_csname, ind_name, url,
                               created_at
                        FROM ifa2.research_reports_history
                        WHERE version_id = :version_id
                        ORDER BY trade_date DESC, ts_code
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "trade_date": row.trade_date,
                    "ts_code": row.ts_code,
                    "name": row.name,
                    "title": row.title,
                    "report_type": row.report_type,
                    "author": row.author,
                    "inst_csname": row.inst_csname,
                    "ind_name": row.ind_name,
                    "url": row.url,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class InvestorQaHistory:
    """Historical investor Q&A records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(
        self,
        version_id: str,
        records: list[dict],
    ) -> int:
        """Store historical records for a version."""
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.investor_qa_history (
                            id, version_id, ts_code, trade_date, q, name, a,
                            pub_time, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :trade_date, :q, :name,
                            :a, :pub_time, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "trade_date": rec["trade_date"],
                        "q": rec["q"],
                        "name": rec.get("name"),
                        "a": rec.get("a"),
                        "pub_time": rec.get("pub_time"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query historical records by version."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, trade_date, q, name, a,
                               pub_time, created_at
                        FROM ifa2.investor_qa_history
                        WHERE version_id = :version_id
                        ORDER BY trade_date DESC, ts_code
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, trade_date, q, name, a,
                               pub_time, created_at
                        FROM ifa2.investor_qa_history
                        WHERE version_id = :version_id
                        ORDER BY trade_date DESC, ts_code
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "ts_code": row.ts_code,
                    "trade_date": row.trade_date,
                    "q": row.q,
                    "name": row.name,
                    "a": row.a,
                    "pub_time": row.pub_time,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class IndexWeightHistory:
    """Historical index weight records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(self, version_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.index_weight_history (
                            id, version_id, index_code, trade_date, con_code, weight,
                            created_at
                        )
                        VALUES (
                            :id, :version_id, :index_code, :trade_date, :con_code, :weight,
                            now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "index_code": rec["index_code"],
                        "trade_date": rec["trade_date"],
                        "con_code": rec["con_code"],
                        "weight": rec["weight"],
                    },
                )
                count += 1

        return count

    def query_by_version(
        self, version_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, index_code, trade_date, con_code, weight,
                               created_at
                        FROM ifa2.index_weight_history
                        WHERE version_id = :version_id
                        ORDER BY index_code, trade_date, con_code
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, index_code, trade_date, con_code, weight,
                               created_at
                        FROM ifa2.index_weight_history
                        WHERE version_id = :version_id
                        ORDER BY index_code, trade_date, con_code
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "index_code": row.index_code,
                    "trade_date": row.trade_date,
                    "con_code": row.con_code,
                    "weight": row.weight,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class EtfDailyBasicHistory:
    """Historical ETF daily basic records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(self, version_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.etf_daily_basic_history (
                            id, version_id, ts_code, trade_date, unit_nav, unit_total,
                            total_mv, nav_mv, share, adj_factor, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :trade_date, :unit_nav, :unit_total,
                            :total_mv, :nav_mv, :share, :adj_factor, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "trade_date": rec["trade_date"],
                        "unit_nav": rec.get("unit_nav"),
                        "unit_total": rec.get("unit_total"),
                        "total_mv": rec.get("total_mv"),
                        "nav_mv": rec.get("nav_mv"),
                        "share": rec.get("share"),
                        "adj_factor": rec.get("adj_factor"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self, version_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, trade_date, unit_nav, unit_total,
                               total_mv, nav_mv, share, adj_factor, created_at
                        FROM ifa2.etf_daily_basic_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, trade_date
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, trade_date, unit_nav, unit_total,
                               total_mv, nav_mv, share, adj_factor, created_at
                        FROM ifa2.etf_daily_basic_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, trade_date
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "ts_code": row.ts_code,
                    "trade_date": row.trade_date,
                    "unit_nav": row.unit_nav,
                    "unit_total": row.unit_total,
                    "total_mv": row.total_mv,
                    "nav_mv": row.nav_mv,
                    "share": row.share,
                    "adj_factor": row.adj_factor,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class ShareFloatHistory:
    """Historical share float records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(self, version_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.share_float_history (
                            id, version_id, ts_code, float_date, float_share, total_share,
                            free_share, float_mv, total_mv, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :float_date, :float_share, :total_share,
                            :free_share, :float_mv, :total_mv, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "float_date": rec["float_date"],
                        "float_share": rec.get("float_share"),
                        "total_share": rec.get("total_share"),
                        "free_share": rec.get("free_share"),
                        "float_mv": rec.get("float_mv"),
                        "total_mv": rec.get("total_mv"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self, version_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, float_date, float_share, total_share,
                               free_share, float_mv, total_mv, created_at
                        FROM ifa2.share_float_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, float_date
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, float_date, float_share, total_share,
                               free_share, float_mv, total_mv, created_at
                        FROM ifa2.share_float_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, float_date
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "ts_code": row.ts_code,
                    "float_date": row.float_date,
                    "float_share": row.float_share,
                    "total_share": row.total_share,
                    "free_share": row.free_share,
                    "float_mv": row.float_mv,
                    "total_mv": row.total_mv,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class CompanyBasicHistory:
    """Historical company basic records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(self, version_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.company_basic_history (
                            id, version_id, ts_code, exchange, chairman, manager, secretary,
                            registered_capital, paid_in_capital, setup_date,
                            province, city, introduction, website, email, office,
                            employees, main_business, business_scope, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :exchange, :chairman, :manager, :secretary,
                            :registered_capital, :paid_in_capital, :setup_date,
                            :province, :city, :introduction, :website, :email, :office,
                            :employees, :main_business, :business_scope, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "exchange": rec.get("exchange"),
                        "chairman": rec.get("chairman"),
                        "manager": rec.get("manager"),
                        "secretary": rec.get("secretary"),
                        "registered_capital": rec.get("registered_capital"),
                        "paid_in_capital": rec.get("paid_in_capital"),
                        "setup_date": rec.get("setup_date"),
                        "province": rec.get("province"),
                        "city": rec.get("city"),
                        "introduction": rec.get("introduction"),
                        "website": rec.get("website"),
                        "email": rec.get("email"),
                        "office": rec.get("office"),
                        "employees": rec.get("employees"),
                        "main_business": rec.get("main_business"),
                        "business_scope": rec.get("business_scope"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self, version_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, exchange, chairman, manager, secretary,
                               registered_capital, paid_in_capital, setup_date,
                               province, city, introduction, website, email, office,
                               employees, main_business, business_scope, created_at
                        FROM ifa2.company_basic_history
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
                        SELECT id, version_id, ts_code, exchange, chairman, manager, secretary,
                               registered_capital, paid_in_capital, setup_date,
                               province, city, introduction, website, email, office,
                               employees, main_business, business_scope, created_at
                        FROM ifa2.company_basic_history
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
                    "exchange": row.exchange,
                    "chairman": row.chairman,
                    "manager": row.manager,
                    "secretary": row.secretary,
                    "registered_capital": row.registered_capital,
                    "paid_in_capital": row.paid_in_capital,
                    "setup_date": row.setup_date,
                    "province": row.province,
                    "city": row.city,
                    "introduction": row.introduction,
                    "website": row.website,
                    "email": row.email,
                    "office": row.office,
                    "employees": row.employees,
                    "main_business": row.main_business,
                    "business_scope": row.business_scope,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class StkManagersHistory:
    """Historical stk managers records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(self, version_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.stk_managers_history (
                            id, version_id, ts_code, name, title, gender,
                            edu, nationality, birthday, begin_date, end_date,
                            created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :name, :title, :gender,
                            :edu, :nationality, :birthday, :begin_date, :end_date,
                            now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "name": rec["name"],
                        "title": rec.get("title"),
                        "gender": rec.get("gender"),
                        "edu": rec.get("edu"),
                        "nationality": rec.get("nationality"),
                        "birthday": rec.get("birthday"),
                        "begin_date": rec.get("begin_date"),
                        "end_date": rec.get("end_date"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self, version_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, name, title, gender,
                               edu, nationality, birthday, begin_date, end_date,
                               created_at
                        FROM ifa2.stk_managers_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, begin_date
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, name, title, gender,
                               edu, nationality, birthday, begin_date, end_date,
                               created_at
                        FROM ifa2.stk_managers_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, begin_date
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "ts_code": row.ts_code,
                    "name": row.name,
                    "title": row.title,
                    "gender": row.gender,
                    "edu": row.edu,
                    "nationality": row.nationality,
                    "birthday": row.birthday,
                    "begin_date": row.begin_date,
                    "end_date": row.end_date,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class NewShareHistory:
    """Historical new share records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(self, version_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.new_share_history (
                            id, version_id, ts_code, name, ipo_date, issue_date,
                            issue_price, amount, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :name, :ipo_date, :issue_date,
                            :issue_price, :amount, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "name": rec["name"],
                        "ipo_date": rec.get("ipo_date"),
                        "issue_date": rec.get("issue_date"),
                        "issue_price": rec.get("issue_price"),
                        "amount": rec.get("amount"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self, version_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, name, ipo_date, issue_date,
                               issue_price, amount, created_at
                        FROM ifa2.new_share_history
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
                        SELECT id, version_id, ts_code, name, ipo_date, issue_date,
                               issue_price, amount, created_at
                        FROM ifa2.new_share_history
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
                    "name": row.name,
                    "ipo_date": row.ipo_date,
                    "issue_date": row.issue_date,
                    "issue_price": row.issue_price,
                    "amount": row.amount,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class NameChangeHistory:
    """Historical name change records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(self, version_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.name_change_history (
                            id, version_id, ts_code, name, start_date,
                            end_date, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :name, :start_date,
                            :end_date, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "name": rec["name"],
                        "start_date": rec["start_date"],
                        "end_date": rec.get("end_date"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self, version_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, name, start_date,
                               end_date, created_at
                        FROM ifa2.name_change_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, start_date
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, name, start_date,
                               end_date, created_at
                        FROM ifa2.name_change_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, start_date
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "ts_code": row.ts_code,
                    "name": row.name,
                    "start_date": row.start_date,
                    "end_date": row.end_date,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class StkHoldernumberHistory:
    """Historical stk holdernumber records per version."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store_version(self, version_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            record_id = str(uuid.uuid4())
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.stk_holdernumber_history (
                            id, version_id, ts_code, end_date, holder_num, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :end_date, :holder_num, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "end_date": rec["end_date"],
                        "holder_num": rec.get("holder_num"),
                    },
                )
                count += 1

        return count

    def query_by_version(
        self, version_id: str, limit: Optional[int] = None
    ) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, end_date, holder_num, created_at
                        FROM ifa2.stk_holdernumber_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, end_date
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, ts_code, end_date, holder_num, created_at
                        FROM ifa2.stk_holdernumber_history
                        WHERE version_id = :version_id
                        ORDER BY ts_code, end_date
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "ts_code": row.ts_code,
                    "end_date": row.end_date,
                    "holder_num": row.holder_num,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
