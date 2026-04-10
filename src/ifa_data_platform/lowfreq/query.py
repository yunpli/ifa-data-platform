"""Query layer for low-frequency datasets.

Supports:
- Fast current query (default path)
- Version-aware query
- As-of query for historical lookups
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.version_persistence import (
    DatasetVersionRegistry,
    StockBasicHistory,
    TradeCalHistory,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CurrentQuery:
    """Fast current query for low-frequency datasets.

    Default path for current/latest data.
    """

    def __init__(self) -> None:
        self.engine = make_engine()
        self._version_registry = DatasetVersionRegistry()
        self._trade_cal_history = TradeCalHistory()
        self._stock_basic_history = StockBasicHistory()

    def get_trade_cal(
        self,
        cal_date: date,
        exchange: str = "SSE",
    ) -> Optional[dict]:
        """Get trade calendar record by date.

        Args:
            cal_date: Calendar date.
            exchange: Exchange code.

        Returns:
            Record dict if found, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, cal_date, exchange, is_open, pretrade_date,
                           version_id, created_at, updated_at
                    FROM ifa2.trade_cal_current
                    WHERE cal_date = :cal_date AND exchange = :exchange
                    """
                ),
                {"cal_date": cal_date, "exchange": exchange},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "cal_date": row.cal_date,
                "exchange": row.exchange,
                "is_open": bool(row.is_open),
                "pretrade_date": row.pretrade_date,
                "version_id": row.version_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def list_trade_cal(
        self,
        start_date: date,
        end_date: date,
        exchange: Optional[str] = None,
    ) -> list[dict]:
        """List trade calendar records in a date range.

        Args:
            start_date: Start date (inclusive).
            end_date: End date (inclusive).
            exchange: Optional exchange filter.

        Returns:
            List of records.
        """
        with self.engine.begin() as conn:
            if exchange:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, cal_date, exchange, is_open, pretrade_date,
                               version_id, created_at, updated_at
                        FROM ifa2.trade_cal_current
                        WHERE cal_date BETWEEN :start_date AND :end_date
                          AND exchange = :exchange
                        ORDER BY cal_date
                        """
                    ),
                    {
                        "start_date": start_date,
                        "end_date": end_date,
                        "exchange": exchange,
                    },
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, cal_date, exchange, is_open, pretrade_date,
                               version_id, created_at, updated_at
                        FROM ifa2.trade_cal_current
                        WHERE cal_date BETWEEN :start_date AND :end_date
                        ORDER BY exchange, cal_date
                        """
                    ),
                    {"start_date": start_date, "end_date": end_date},
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "cal_date": row.cal_date,
                    "exchange": row.exchange,
                    "is_open": bool(row.is_open),
                    "pretrade_date": row.pretrade_date,
                    "version_id": row.version_id,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]

    def get_stock_basic(
        self,
        ts_code: str,
    ) -> Optional[dict]:
        """Get stock basic record by ts_code.

        Args:
            ts_code: Tushare stock code.

        Returns:
            Record dict if found, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, ts_code, symbol, name, area, industry, market,
                           list_status, list_date, delist_date, is_hs,
                           version_id, created_at, updated_at
                    FROM ifa2.stock_basic_current
                    WHERE ts_code = :ts_code
                    """
                ),
                {"ts_code": ts_code},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
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
                "version_id": row.version_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def list_stock_basic(
        self,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """List stock basic records.

        Args:
            limit: Optional record limit.

        Returns:
            List of records.
        """
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, symbol, name, area, industry, market,
                               list_status, list_date, delist_date, is_hs,
                               version_id, created_at, updated_at
                        FROM ifa2.stock_basic_current
                        ORDER BY ts_code
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, symbol, name, area, industry, market,
                               list_status, list_date, delist_date, is_hs,
                               version_id, created_at, updated_at
                        FROM ifa2.stock_basic_current
                        ORDER BY ts_code
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
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
                    "version_id": row.version_id,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class VersionQuery:
    """Version-aware and as-of query for low-frequency datasets."""

    def __init__(self) -> None:
        self.engine = make_engine()
        self._version_registry = DatasetVersionRegistry()
        self._trade_cal_history = TradeCalHistory()
        self._stock_basic_history = StockBasicHistory()

    def get_active_version(self, dataset_name: str) -> Optional[dict]:
        """Get the active version for a dataset.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Version dict if found, None otherwise.
        """
        return self._version_registry.get_active_version(dataset_name)

    def get_version_by_id(self, version_id: str) -> Optional[dict]:
        """Get a version by ID.

        Args:
            version_id: Version ID.

        Returns:
            Version dict if found, None otherwise.
        """
        return self._version_registry.get_version_by_id(version_id)

    def get_version_at(self, dataset_name: str, as_of: datetime) -> Optional[dict]:
        """Get the version that was active at a given time.

        Args:
            dataset_name: Name of the dataset.
            as_of: Date/time to query at.

        Returns:
            Version dict if found, None otherwise.
        """
        return self._version_registry.get_version_at_promoted_time(dataset_name, as_of)

    def query_trade_cal_at_version(
        self,
        version_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict]:
        """Query trade calendar from a specific version.

        Args:
            version_id: The version ID.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            List of historical records.
        """
        return self._trade_cal_history.query_by_version(
            version_id, start_date, end_date
        )

    def query_stock_basic_at_version(
        self,
        version_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query stock basic from a specific version.

        Args:
            version_id: The version ID.
            limit: Optional record limit.

        Returns:
            List of historical records.
        """
        return self._stock_basic_history.query_by_version(version_id, limit)

    def query_trade_cal_as_of(
        self,
        as_of: datetime,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        exchange: str = "SSE",
    ) -> list[dict]:
        """Query trade calendar as-of a specific time.

        Args:
            as_of: Date/time to query at.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            exchange: Exchange code.

        Returns:
            List of historical records at that version.
        """
        version = self._version_registry.get_version_at_promoted_time(
            "trade_cal", as_of
        )
        if not version:
            return []

        return self._trade_cal_history.query_by_version(
            version["id"], start_date, end_date
        )

    def query_stock_basic_as_of(
        self,
        as_of: datetime,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Query stock basic as-of a specific time.

        Args:
            as_of: Date/time to query at.
            limit: Optional record limit.

        Returns:
            List of historical records at that version.
        """
        version = self._version_registry.get_version_at_promoted_time(
            "stock_basic", as_of
        )
        if not version:
            return []

        return self._stock_basic_history.query_by_version(version["id"], limit)
