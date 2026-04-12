"""Canonical current persistence for mid-frequency datasets."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


CURRENT_VERSION_ID_SENTINEL = "__current__"


class EquityDailyBarCurrent:
    """Canonical current table for equity daily bar (OHLCV)."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        trade_date: date,
        open: Optional[float] = None,
        high: Optional[float] = None,
        low: Optional[float] = None,
        close: Optional[float] = None,
        vol: Optional[float] = None,
        amount: Optional[float] = None,
        pre_close: Optional[float] = None,
        change: Optional[float] = None,
        pct_chg: Optional[float] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.equity_daily_bar_current (
                        id, ts_code, trade_date, open, high, low, close,
                        vol, amount, pre_close, change, pct_chg,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :trade_date, :open, :high, :low, :close,
                        :vol, :amount, :pre_close, :change, :pct_chg,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        vol = EXCLUDED.vol,
                        amount = EXCLUDED.amount,
                        pre_close = EXCLUDED.pre_close,
                        change = EXCLUDED.change,
                        pct_chg = EXCLUDED.pct_chg,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "open": open,
                    "high": high,
                    "low": low,
                    "close": close,
                    "vol": vol,
                    "amount": amount,
                    "pre_close": pre_close,
                    "change": change,
                    "pct_chg": pct_chg,
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                trade_date=rec["trade_date"],
                open=rec.get("open"),
                high=rec.get("high"),
                low=rec.get("low"),
                close=rec.get("close"),
                vol=rec.get("vol"),
                amount=rec.get("amount"),
                pre_close=rec.get("pre_close"),
                change=rec.get("change"),
                pct_chg=rec.get("pct_chg"),
                version_id=version_id,
            )
            count += 1

        return count

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg,
                               created_at, updated_at
                        FROM ifa2.equity_daily_bar_current
                        ORDER BY ts_code, trade_date
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg,
                               created_at, updated_at
                        FROM ifa2.equity_daily_bar_current
                        ORDER BY ts_code, trade_date
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
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
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class IndexDailyBarCurrent:
    """Canonical current table for index daily bar."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        trade_date: date,
        open: Optional[float] = None,
        high: Optional[float] = None,
        low: Optional[float] = None,
        close: Optional[float] = None,
        vol: Optional[float] = None,
        amount: Optional[float] = None,
        pre_close: Optional[float] = None,
        change: Optional[float] = None,
        pct_chg: Optional[float] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.index_daily_bar_current (
                        id, ts_code, trade_date, open, high, low, close,
                        vol, amount, pre_close, change, pct_chg,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :trade_date, :open, :high, :low, :close,
                        :vol, :amount, :pre_close, :change, :pct_chg,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        vol = EXCLUDED.vol,
                        amount = EXCLUDED.amount,
                        pre_close = EXCLUDED.pre_close,
                        change = EXCLUDED.change,
                        pct_chg = EXCLUDED.pct_chg,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "open": open,
                    "high": high,
                    "low": low,
                    "close": close,
                    "vol": vol,
                    "amount": amount,
                    "pre_close": pre_close,
                    "change": change,
                    "pct_chg": pct_chg,
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                trade_date=rec["trade_date"],
                open=rec.get("open"),
                high=rec.get("high"),
                low=rec.get("low"),
                close=rec.get("close"),
                vol=rec.get("vol"),
                amount=rec.get("amount"),
                pre_close=rec.get("pre_close"),
                change=rec.get("change"),
                pct_chg=rec.get("pct_chg"),
                version_id=version_id,
            )
            count += 1

        return count

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg,
                               created_at, updated_at
                        FROM ifa2.index_daily_bar_current
                        ORDER BY ts_code, trade_date
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg,
                               created_at, updated_at
                        FROM ifa2.index_daily_bar_current
                        ORDER BY ts_code, trade_date
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
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
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class EtfDailyBarCurrent:
    """Canonical current table for ETF daily bar."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        trade_date: date,
        open: Optional[float] = None,
        high: Optional[float] = None,
        low: Optional[float] = None,
        close: Optional[float] = None,
        vol: Optional[float] = None,
        amount: Optional[float] = None,
        pre_close: Optional[float] = None,
        change: Optional[float] = None,
        pct_chg: Optional[float] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.etf_daily_bar_current (
                        id, ts_code, trade_date, open, high, low, close,
                        vol, amount, pre_close, change, pct_chg,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :trade_date, :open, :high, :low, :close,
                        :vol, :amount, :pre_close, :change, :pct_chg,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        vol = EXCLUDED.vol,
                        amount = EXCLUDED.amount,
                        pre_close = EXCLUDED.pre_close,
                        change = EXCLUDED.change,
                        pct_chg = EXCLUDED.pct_chg,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "open": open,
                    "high": high,
                    "low": low,
                    "close": close,
                    "vol": vol,
                    "amount": amount,
                    "pre_close": pre_close,
                    "change": change,
                    "pct_chg": pct_chg,
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                trade_date=rec["trade_date"],
                open=rec.get("open"),
                high=rec.get("high"),
                low=rec.get("low"),
                close=rec.get("close"),
                vol=rec.get("vol"),
                amount=rec.get("amount"),
                pre_close=rec.get("pre_close"),
                change=rec.get("change"),
                pct_chg=rec.get("pct_chg"),
                version_id=version_id,
            )
            count += 1

        return count

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg,
                               created_at, updated_at
                        FROM ifa2.etf_daily_bar_current
                        ORDER BY ts_code, trade_date
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, trade_date, open, high, low, close,
                               vol, amount, pre_close, change, pct_chg,
                               created_at, updated_at
                        FROM ifa2.etf_daily_bar_current
                        ORDER BY ts_code, trade_date
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
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
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class NorthboundFlowCurrent:
    """Canonical current table for northbound (HK->CN) flow."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        trade_date: date,
        north_money: Optional[float] = None,
        north_bal: Optional[float] = None,
        north_buy: Optional[float] = None,
        north_sell: Optional[float] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.northbound_flow_current (
                        id, trade_date, north_money, north_bal, north_buy, north_sell,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :trade_date, :north_money, :north_bal, :north_buy, :north_sell,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (trade_date) DO UPDATE SET
                        north_money = EXCLUDED.north_money,
                        north_bal = EXCLUDED.north_bal,
                        north_buy = EXCLUDED.north_buy,
                        north_sell = EXCLUDED.north_sell,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "trade_date": trade_date,
                    "north_money": north_money,
                    "north_bal": north_bal,
                    "north_buy": north_buy,
                    "north_sell": north_sell,
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                trade_date=rec["trade_date"],
                north_money=rec.get("north_money"),
                north_bal=rec.get("north_bal"),
                north_buy=rec.get("north_buy"),
                north_sell=rec.get("north_sell"),
                version_id=version_id,
            )
            count += 1

        return count

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, trade_date, north_money, north_bal, north_buy, north_sell,
                               created_at, updated_at
                        FROM ifa2.northbound_flow_current
                        ORDER BY trade_date
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, trade_date, north_money, north_bal, north_buy, north_sell,
                               created_at, updated_at
                        FROM ifa2.northbound_flow_current
                        ORDER BY trade_date
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "trade_date": row.trade_date,
                    "north_money": row.north_money,
                    "north_bal": row.north_bal,
                    "north_buy": row.north_buy,
                    "north_sell": row.north_sell,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class LimitUpDownStatusCurrent:
    """Canonical current table for limit up/down status."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        trade_date: date,
        limit_up_count: Optional[int] = None,
        limit_down_count: Optional[int] = None,
        limit_up_streak_high: Optional[int] = None,
        limit_down_streak_high: Optional[int] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.limit_up_down_status_current (
                        id, trade_date, limit_up_count, limit_down_count,
                        limit_up_streak_high, limit_down_streak_high,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :trade_date, :limit_up_count, :limit_down_count,
                        :limit_up_streak_high, :limit_down_streak_high,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (trade_date) DO UPDATE SET
                        limit_up_count = EXCLUDED.limit_up_count,
                        limit_down_count = EXCLUDED.limit_down_count,
                        limit_up_streak_high = EXCLUDED.limit_up_streak_high,
                        limit_down_streak_high = EXCLUDED.limit_down_streak_high,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "trade_date": trade_date,
                    "limit_up_count": limit_up_count,
                    "limit_down_count": limit_down_count,
                    "limit_up_streak_high": limit_up_streak_high,
                    "limit_down_streak_high": limit_down_streak_high,
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                trade_date=rec["trade_date"],
                limit_up_count=rec.get("limit_up_count"),
                limit_down_count=rec.get("limit_down_count"),
                limit_up_streak_high=rec.get("limit_up_streak_high"),
                limit_down_streak_high=rec.get("limit_down_streak_high"),
                version_id=version_id,
            )
            count += 1

        return count

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, trade_date, limit_up_count, limit_down_count,
                               limit_up_streak_high, limit_down_streak_high,
                               created_at, updated_at
                        FROM ifa2.limit_up_down_status_current
                        ORDER BY trade_date
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, trade_date, limit_up_count, limit_down_count,
                               limit_up_streak_high, limit_down_streak_high,
                               created_at, updated_at
                        FROM ifa2.limit_up_down_status_current
                        ORDER BY trade_date
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
                    "trade_date": row.trade_date,
                    "limit_up_count": row.limit_up_count,
                    "limit_down_count": row.limit_down_count,
                    "limit_up_streak_high": row.limit_up_streak_high,
                    "limit_down_streak_high": row.limit_down_streak_high,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class MarginFinancingCurrent:
    """Canonical current for margin financing balance."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        trade_date: date,
        rzye: Optional[float] = None,
        rzmre: Optional[float] = None,
        rzche: Optional[float] = None,
        rzrqye: Optional[float] = None,
        rqryl: Optional[float] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.margin_financing_current (
                        id, ts_code, trade_date, rzye, rzmre, rzche, rzrqye, rqryl,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :trade_date, :rzye, :rzmre, :rzche, :rzrqye, :rqryl,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        rzye = EXCLUDED.rzye,
                        rzmre = EXCLUDED.rzmre,
                        rzche = EXCLUDED.rzche,
                        rzrqye = EXCLUDED.rzrqye,
                        rqryl = EXCLUDED.rqryl,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "rzye": rzye,
                    "rzmre": rzmre,
                    "rzche": rzche,
                    "rzrqye": rzrqye,
                    "rqryl": rqryl,
                    "version_id": version_id_value,
                },
            )
        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        if not records:
            return 0
        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                trade_date=rec["trade_date"],
                rzye=rec.get("rzye"),
                rzmre=rec.get("rzmre"),
                rzche=rec.get("rzche"),
                rzrqye=rec.get("rzrqye"),
                rqryl=rec.get("rqryl"),
                version_id=version_id,
            )
            count += 1
        return count

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """SELECT id, ts_code, trade_date, rzye, rzmre, rzche, rzrqye, rqryl
                        FROM ifa2.margin_financing_current ORDER BY ts_code, trade_date LIMIT :limit"""
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """SELECT id, ts_code, trade_date, rzye, rzmre, rzche, rzrqye, rqryl
                        FROM ifa2.margin_financing_current ORDER BY ts_code, trade_date"""
                    ),
                ).fetchall()
            return [
                {
                    "id": row.id,
                    "ts_code": row.ts_code,
                    "trade_date": row.trade_date,
                    "rzye": row.rzye,
                    "rzmre": row.rzmre,
                    "rzche": row.rzche,
                    "rzrqye": row.rzrqye,
                    "rqryl": row.rqryl,
                }
                for row in rows
            ]


class LimitUpDetailCurrent:
    """Canonical current for limit up/down details."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        trade_date: date,
        limit: Optional[str] = None,
        pre_limit: Optional[str] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.limit_up_detail_current (
                        id, ts_code, trade_date, limit, pre_limit,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :trade_date, :limit, :pre_limit,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        limit = EXCLUDED.limit,
                        pre_limit = EXCLUDED.pre_limit,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "limit": limit,
                    "pre_limit": pre_limit,
                    "version_id": version_id_value,
                },
            )
        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        if not records:
            return 0
        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                trade_date=rec["trade_date"],
                limit=rec.get("limit"),
                pre_limit=rec.get("pre_limit"),
                version_id=version_id,
            )
            count += 1
        return count

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """SELECT id, ts_code, trade_date, limit, pre_limit
                        FROM ifa2.limit_up_detail_current ORDER BY ts_code, trade_date LIMIT :limit"""
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """SELECT id, ts_code, trade_date, limit, pre_limit
                        FROM ifa2.limit_up_detail_current ORDER BY ts_code, trade_date"""
                    ),
                ).fetchall()
            return [
                {
                    "id": row.id,
                    "ts_code": row.ts_code,
                    "trade_date": row.trade_date,
                    "limit": row.limit,
                    "pre_limit": row.pre_limit,
                }
                for row in rows
            ]


class TurnoverRateCurrent:
    """Canonical current for stock turnover rates."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        trade_date: date,
        turnover_rate: Optional[float] = None,
        turnover_rate_f: Optional[float] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.turnover_rate_current (
                        id, ts_code, trade_date, turnover_rate, turnover_rate_f,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :trade_date, :turnover_rate, :turnover_rate_f,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        turnover_rate = EXCLUDED.turnover_rate,
                        turnover_rate_f = EXCLUDED.turnover_rate_f,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "turnover_rate": turnover_rate,
                    "turnover_rate_f": turnover_rate_f,
                    "version_id": version_id_value,
                },
            )
        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        if not records:
            return 0
        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                trade_date=rec["trade_date"],
                turnover_rate=rec.get("turnover_rate"),
                turnover_rate_f=rec.get("turnover_rate_f"),
                version_id=version_id,
            )
            count += 1
        return count

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """SELECT id, ts_code, trade_date, turnover_rate, turnover_rate_f
                        FROM ifa2.turnover_rate_current ORDER BY ts_code, trade_date LIMIT :limit"""
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """SELECT id, ts_code, trade_date, turnover_rate, turnover_rate_f
                        FROM ifa2.turnover_rate_current ORDER BY ts_code, trade_date"""
                    ),
                ).fetchall()
            return [
                {
                    "id": row.id,
                    "ts_code": row.ts_code,
                    "trade_date": row.trade_date,
                    "turnover_rate": row.turnover_rate,
                    "turnover_rate_f": row.turnover_rate_f,
                }
                for row in rows
            ]
