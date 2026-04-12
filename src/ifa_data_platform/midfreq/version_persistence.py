"""Dataset version registry and history persistence for midfreq datasets."""

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
    """Registry for tracking dataset versions for midfreq."""

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
        """Create a new candidate version for a dataset."""
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
        """Promote a candidate version to active (current)."""
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
        """Get the active version for a dataset."""
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
        """Get a version by ID."""
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

    def list_versions(self, dataset_name: str, limit: int = 10) -> list[dict]:
        """List versions for a dataset."""
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


class EquityDailyBarHistory:
    """Historical equity daily bar records per version."""

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
                        INSERT INTO ifa2.equity_daily_bar_history (
                            id, version_id, ts_code, trade_date, open, high, low, close,
                            vol, amount, pre_close, change, pct_chg, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :trade_date, :open, :high, :low, :close,
                            :vol, :amount, :pre_close, :change, :pct_chg, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "trade_date": rec["trade_date"],
                        "open": rec.get("open"),
                        "high": rec.get("high"),
                        "low": rec.get("low"),
                        "close": rec.get("close"),
                        "vol": rec.get("vol"),
                        "amount": rec.get("amount"),
                        "pre_close": rec.get("pre_close"),
                        "change": rec.get("change"),
                        "pct_chg": rec.get("pct_chg"),
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
                        SELECT id, version_id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg, created_at
                        FROM ifa2.equity_daily_bar_history
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
                        SELECT id, version_id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg, created_at
                        FROM ifa2.equity_daily_bar_history
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
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "vol": row.vol,
                    "amount": row.amount,
                    "pre_close": row.pre_close,
                    "change": row.change,
                    "pct_chg": row.pct_chg,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class IndexDailyBarHistory:
    """Historical index daily bar records per version."""

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
                        INSERT INTO ifa2.index_daily_bar_history (
                            id, version_id, ts_code, trade_date, open, high, low, close,
                            vol, amount, pre_close, change, pct_chg, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :trade_date, :open, :high, :low, :close,
                            :vol, :amount, :pre_close, :change, :pct_chg, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "trade_date": rec["trade_date"],
                        "open": rec.get("open"),
                        "high": rec.get("high"),
                        "low": rec.get("low"),
                        "close": rec.get("close"),
                        "vol": rec.get("vol"),
                        "amount": rec.get("amount"),
                        "pre_close": rec.get("pre_close"),
                        "change": rec.get("change"),
                        "pct_chg": rec.get("pct_chg"),
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
                        SELECT id, version_id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg, created_at
                        FROM ifa2.index_daily_bar_history
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
                        SELECT id, version_id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg, created_at
                        FROM ifa2.index_daily_bar_history
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
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "vol": row.vol,
                    "amount": row.amount,
                    "pre_close": row.pre_close,
                    "change": row.change,
                    "pct_chg": row.pct_chg,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class EtfDailyBarHistory:
    """Historical ETF daily bar records per version."""

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
                        INSERT INTO ifa2.etf_daily_bar_history (
                            id, version_id, ts_code, trade_date, open, high, low, close,
                            vol, amount, pre_close, change, pct_chg, created_at
                        )
                        VALUES (
                            :id, :version_id, :ts_code, :trade_date, :open, :high, :low, :close,
                            :vol, :amount, :pre_close, :change, :pct_chg, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "ts_code": rec["ts_code"],
                        "trade_date": rec["trade_date"],
                        "open": rec.get("open"),
                        "high": rec.get("high"),
                        "low": rec.get("low"),
                        "close": rec.get("close"),
                        "vol": rec.get("vol"),
                        "amount": rec.get("amount"),
                        "pre_close": rec.get("pre_close"),
                        "change": rec.get("change"),
                        "pct_chg": rec.get("pct_chg"),
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
                        SELECT id, version_id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg, created_at
                        FROM ifa2.etf_daily_bar_history
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
                        SELECT id, version_id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg, created_at
                        FROM ifa2.etf_daily_bar_history
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
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "vol": row.vol,
                    "amount": row.amount,
                    "pre_close": row.pre_close,
                    "change": row.change,
                    "pct_chg": row.pct_chg,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class NorthboundFlowHistory:
    """Historical northbound flow records per version."""

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
                        INSERT INTO ifa2.northbound_flow_history (
                            id, version_id, trade_date, north_money, north_bal,
                            north_buy, north_sell, created_at
                        )
                        VALUES (
                            :id, :version_id, :trade_date, :north_money, :north_bal,
                            :north_buy, :north_sell, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "trade_date": rec["trade_date"],
                        "north_money": rec.get("north_money"),
                        "north_bal": rec.get("north_bal"),
                        "north_buy": rec.get("north_buy"),
                        "north_sell": rec.get("north_sell"),
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
                        SELECT id, version_id, trade_date, north_money, north_bal,
                               north_buy, north_sell, created_at
                        FROM ifa2.northbound_flow_history
                        WHERE version_id = :version_id
                        ORDER BY trade_date
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, trade_date, north_money, north_bal,
                               north_buy, north_sell, created_at
                        FROM ifa2.northbound_flow_history
                        WHERE version_id = :version_id
                        ORDER BY trade_date
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "trade_date": row.trade_date,
                    "north_money": row.north_money,
                    "north_bal": row.north_bal,
                    "north_buy": row.north_buy,
                    "north_sell": row.north_sell,
                    "created_at": row.created_at,
                }
                for row in rows
            ]


class LimitUpDownStatusHistory:
    """Historical limit up/down status records per version."""

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
                        INSERT INTO ifa2.limit_up_down_status_history (
                            id, version_id, trade_date, limit_up_count, limit_down_count,
                            limit_up_streak_high, limit_down_streak_high, created_at
                        )
                        VALUES (
                            :id, :version_id, :trade_date, :limit_up_count, :limit_down_count,
                            :limit_up_streak_high, :limit_down_streak_high, now()
                        )
                        """
                    ),
                    {
                        "id": record_id,
                        "version_id": version_id,
                        "trade_date": rec["trade_date"],
                        "limit_up_count": rec.get("limit_up_count"),
                        "limit_down_count": rec.get("limit_down_count"),
                        "limit_up_streak_high": rec.get("limit_up_streak_high"),
                        "limit_down_streak_high": rec.get("limit_down_streak_high"),
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
                        SELECT id, version_id, trade_date, limit_up_count, limit_down_count,
                               limit_up_streak_high, limit_down_streak_high, created_at
                        FROM ifa2.limit_up_down_status_history
                        WHERE version_id = :version_id
                        ORDER BY trade_date
                        LIMIT :limit
                        """
                    ),
                    {"version_id": version_id, "limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, version_id, trade_date, limit_up_count, limit_down_count,
                               limit_up_streak_high, limit_down_streak_high, created_at
                        FROM ifa2.limit_up_down_status_history
                        WHERE version_id = :version_id
                        ORDER BY trade_date
                        """
                    ),
                    {"version_id": version_id},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "version_id": row.version_id,
                    "trade_date": row.trade_date,
                    "limit_up_count": row.limit_up_count,
                    "limit_down_count": row.limit_down_count,
                    "limit_up_streak_high": row.limit_up_streak_high,
                    "limit_down_streak_high": row.limit_down_streak_high,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
