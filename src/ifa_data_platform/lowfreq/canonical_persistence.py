"""Canonical current persistence for trade_cal and stock_basic datasets."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TradeCalCurrent:
    """Canonical current table for China-market trading calendar."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        cal_date: date,
        exchange: str,
        is_open: bool,
        pretrade_date: Optional[date] = None,
    ) -> str:
        """Upsert a trading calendar record.

        Args:
            cal_date: Calendar date.
            exchange: Exchange code (e.g., 'SSE', 'SZSE').
            is_open: Whether the market is open on this date.
            pretrade_date: Previous trading day.

        Returns:
            ID of the upserted record.
        """
        record_id = str(uuid.uuid4())

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.trade_cal_current (
                        id, cal_date, exchange, is_open, pretrade_date,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :cal_date, :exchange, :is_open, :pretrade_date,
                        now(), now()
                    )
                    ON CONFLICT (exchange, cal_date) DO UPDATE SET
                        is_open = EXCLUDED.is_open,
                        pretrade_date = EXCLUDED.pretrade_date,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "cal_date": cal_date,
                    "exchange": exchange,
                    "is_open": 1 if is_open else 0,
                    "pretrade_date": pretrade_date,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
    ) -> int:
        """Bulk upsert trading calendar records.

        Args:
            records: List of records with keys: cal_date, exchange, is_open, pretrade_date.

        Returns:
            Number of records processed.
        """
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                cal_date=rec["cal_date"],
                exchange=rec["exchange"],
                is_open=rec["is_open"],
                pretrade_date=rec.get("pretrade_date"),
            )
            count += 1

        return count

    def get_by_date(self, cal_date: date, exchange: str) -> Optional[dict]:
        """Get a trading calendar record by date and exchange.

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
                           created_at, updated_at
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
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def list_range(
        self,
        start_date: date,
        end_date: date,
        exchange: Optional[str] = None,
    ) -> list[dict]:
        """List trading calendar records in a date range.

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
                               created_at, updated_at
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
                               created_at, updated_at
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
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class StockBasicCurrent:
    """Canonical current table for A-share instruments."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        symbol: Optional[str] = None,
        name: Optional[str] = None,
        area: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        list_status: Optional[str] = None,
        list_date: Optional[date] = None,
        delist_date: Optional[date] = None,
        is_hs: Optional[bool] = None,
    ) -> str:
        """Upsert a stock basic record.

        Args:
            ts_code: Tushare stock code (e.g., '000001.SZ').
            symbol: Stock symbol (e.g., '000001').
            name: Company name.
            area: Region.
            industry: Industry.
            market: Market (Main, SME, ChiNext, etc.).
            list_status: Listing status (L, D, P).
            list_date: Listing date.
            delist_date: Delisting date.
            is_hs: Whether in HS (0, 1, 2).

        Returns:
            ID of the upserted record.
        """
        record_id = str(uuid.uuid4())

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.stock_basic_current (
                        id, ts_code, symbol, name, area, industry, market,
                        list_status, list_date, delist_date, is_hs,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :symbol, :name, :area, :industry, :market,
                        :list_status, :list_date, :delist_date, :is_hs,
                        now(), now()
                    )
                    ON CONFLICT (ts_code) DO UPDATE SET
                        symbol = EXCLUDED.symbol,
                        name = EXCLUDED.name,
                        area = EXCLUDED.area,
                        industry = EXCLUDED.industry,
                        market = EXCLUDED.market,
                        list_status = EXCLUDED.list_status,
                        list_date = EXCLUDED.list_date,
                        delist_date = EXCLUDED.delist_date,
                        is_hs = EXCLUDED.is_hs,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "symbol": symbol,
                    "name": name,
                    "area": area,
                    "industry": industry,
                    "market": market,
                    "list_status": list_status,
                    "list_date": list_date,
                    "delist_date": delist_date,
                    "is_hs": 1 if is_hs else (0 if is_hs is not None else None),
                },
            )

        return record_id

    def bulk_upsert(self, records: list[dict]) -> int:
        """Bulk upsert stock basic records.

        Args:
            records: List of records with ts_code and optional other fields.

        Returns:
            Number of records processed.
        """
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                symbol=rec.get("symbol"),
                name=rec.get("name"),
                area=rec.get("area"),
                industry=rec.get("industry"),
                market=rec.get("market"),
                list_status=rec.get("list_status"),
                list_date=rec.get("list_date"),
                delist_date=rec.get("delist_date"),
                is_hs=rec.get("is_hs"),
            )
            count += 1

        return count

    def get_by_ts_code(self, ts_code: str) -> Optional[dict]:
        """Get a stock basic record by ts_code.

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
                           created_at, updated_at
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
                "is_hs": bool(row.is_hs) if row.is_hs is not None else None,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        """List all stock basic records.

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
                               created_at, updated_at
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
                               created_at, updated_at
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
                    "is_hs": bool(row.is_hs) if row.is_hs is not None else None,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]
