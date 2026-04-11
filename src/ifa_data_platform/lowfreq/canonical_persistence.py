"""Canonical current persistence for trade_cal and stock_basic datasets."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


CURRENT_VERSION_ID_SENTINEL = "__current__"


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
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        """Upsert a trading calendar record.

        Args:
            cal_date: Calendar date.
            exchange: Exchange code (e.g., 'SSE', 'SZSE').
            is_open: Whether the market is open on this date.
            pretrade_date: Previous trading day.
            version_id: Version ID (None or sentinel for current).

        Returns:
            ID of the upserted record.
        """
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.trade_cal_current (
                        id, cal_date, exchange, is_open, pretrade_date,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :cal_date, :exchange, :is_open, :pretrade_date,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (exchange, cal_date) DO UPDATE SET
                        is_open = EXCLUDED.is_open,
                        pretrade_date = EXCLUDED.pretrade_date,
                        version_id = EXCLUDED.version_id,
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
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        """Bulk upsert trading calendar records.

        Args:
            records: List of records with keys: cal_date, exchange, is_open, pretrade_date.
            version_id: Version ID (None or sentinel for current).

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
                version_id=version_id,
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
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
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
            version_id: Version ID (None or sentinel for current).

        Returns:
            ID of the upserted record.
        """
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.stock_basic_current (
                        id, ts_code, symbol, name, area, industry, market,
                        list_status, list_date, delist_date, is_hs,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :symbol, :name, :area, :industry, :market,
                        :list_status, :list_date, :delist_date, :is_hs,
                        :version_id, now(), now()
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
                        version_id = EXCLUDED.version_id,
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
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        """Bulk upsert stock basic records.

        Args:
            records: List of records with ts_code and optional other fields.
            version_id: Version ID (None or sentinel for current).

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
                version_id=version_id,
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


class IndexBasicCurrent:
    """Canonical current table for China-market index master data."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        name: Optional[str] = None,
        market: Optional[str] = None,
        publisher: Optional[str] = None,
        category: Optional[str] = None,
        base_date: Optional[date] = None,
        base_point: Optional[float] = None,
        list_date: Optional[date] = None,
        weight_rule: Optional[str] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        """Upsert an index basic record."""
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.index_basic_current (
                        id, ts_code, name, market, publisher, category,
                        base_date, base_point, list_date, weight_rule,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :name, :market, :publisher, :category,
                        :base_date, :base_point, :list_date, :weight_rule,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (ts_code) DO UPDATE SET
                        name = EXCLUDED.name,
                        market = EXCLUDED.market,
                        publisher = EXCLUDED.publisher,
                        category = EXCLUDED.category,
                        base_date = EXCLUDED.base_date,
                        base_point = EXCLUDED.base_point,
                        list_date = EXCLUDED.list_date,
                        weight_rule = EXCLUDED.weight_rule,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "name": name,
                    "market": market,
                    "publisher": publisher,
                    "category": category,
                    "base_date": base_date,
                    "base_point": base_point,
                    "list_date": list_date,
                    "weight_rule": weight_rule,
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        """Bulk upsert index basic records."""
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                name=rec.get("name"),
                market=rec.get("market"),
                publisher=rec.get("publisher"),
                category=rec.get("category"),
                base_date=rec.get("base_date"),
                base_point=rec.get("base_point"),
                list_date=rec.get("list_date"),
                weight_rule=rec.get("weight_rule"),
                version_id=version_id,
            )
            count += 1

        return count

    def get_by_ts_code(self, ts_code: str) -> Optional[dict]:
        """Get an index basic record by ts_code."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, ts_code, name, market, publisher, category,
                           base_date, base_point, list_date, weight_rule,
                           created_at, updated_at
                    FROM ifa2.index_basic_current
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
                "name": row.name,
                "market": row.market,
                "publisher": row.publisher,
                "category": row.category,
                "base_date": row.base_date,
                "base_point": row.base_point,
                "list_date": row.list_date,
                "weight_rule": row.weight_rule,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        """List all index basic records."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, name, market, publisher, category,
                               base_date, base_point, list_date, weight_rule,
                               created_at, updated_at
                        FROM ifa2.index_basic_current
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
                        SELECT id, ts_code, name, market, publisher, category,
                               base_date, base_point, list_date, weight_rule,
                               created_at, updated_at
                        FROM ifa2.index_basic_current
                        ORDER BY ts_code
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
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
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class FundBasicEtfCurrent:
    """Canonical current table for ETF/fund master data (ETF-first subset)."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        ts_code: str,
        name: Optional[str] = None,
        market: Optional[str] = None,
        fund_type: Optional[str] = None,
        management: Optional[str] = None,
        custodian: Optional[str] = None,
        list_date: Optional[date] = None,
        due_date: Optional[date] = None,
        issue_date: Optional[date] = None,
        delist_date: Optional[date] = None,
        invest_type: Optional[str] = None,
        benchmark: Optional[str] = None,
        status: Optional[str] = None,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        """Upsert a fund basic ETF record."""
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.fund_basic_etf_current (
                        id, ts_code, name, market, fund_type, management,
                        custodian, list_date, due_date, issue_date, delist_date,
                        invest_type, benchmark, status,
                        version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :ts_code, :name, :market, :fund_type, :management,
                        :custodian, :list_date, :due_date, :issue_date, :delist_date,
                        :invest_type, :benchmark, :status,
                        :version_id, now(), now()
                    )
                    ON CONFLICT (ts_code) DO UPDATE SET
                        name = EXCLUDED.name,
                        market = EXCLUDED.market,
                        fund_type = EXCLUDED.fund_type,
                        management = EXCLUDED.management,
                        custodian = EXCLUDED.custodian,
                        list_date = EXCLUDED.list_date,
                        due_date = EXCLUDED.due_date,
                        issue_date = EXCLUDED.issue_date,
                        delist_date = EXCLUDED.delist_date,
                        invest_type = EXCLUDED.invest_type,
                        benchmark = EXCLUDED.benchmark,
                        status = EXCLUDED.status,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "ts_code": ts_code,
                    "name": name,
                    "market": market,
                    "fund_type": fund_type,
                    "management": management,
                    "custodian": custodian,
                    "list_date": list_date,
                    "due_date": due_date,
                    "issue_date": issue_date,
                    "delist_date": delist_date,
                    "invest_type": invest_type,
                    "benchmark": benchmark,
                    "status": status,
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        """Bulk upsert fund basic ETF records."""
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                ts_code=rec["ts_code"],
                name=rec.get("name"),
                market=rec.get("market"),
                fund_type=rec.get("fund_type"),
                management=rec.get("management"),
                custodian=rec.get("custodian"),
                list_date=rec.get("list_date"),
                due_date=rec.get("due_date"),
                issue_date=rec.get("issue_date"),
                delist_date=rec.get("delist_date"),
                invest_type=rec.get("invest_type"),
                benchmark=rec.get("benchmark"),
                status=rec.get("status"),
                version_id=version_id,
            )
            count += 1

        return count

    def get_by_ts_code(self, ts_code: str) -> Optional[dict]:
        """Get a fund basic ETF record by ts_code."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, ts_code, name, market, fund_type, management,
                           custodian, list_date, due_date, issue_date, delist_date,
                           invest_type, benchmark, status,
                           created_at, updated_at
                    FROM ifa2.fund_basic_etf_current
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
                "updated_at": row.updated_at,
            }

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        """List all fund basic ETF records."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, ts_code, name, market, fund_type, management,
                               custodian, list_date, due_date, issue_date, delist_date,
                               invest_type, benchmark, status,
                               created_at, updated_at
                        FROM ifa2.fund_basic_etf_current
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
                        SELECT id, ts_code, name, market, fund_type, management,
                               custodian, list_date, due_date, issue_date, delist_date,
                               invest_type, benchmark, status,
                               created_at, updated_at
                        FROM ifa2.fund_basic_etf_current
                        ORDER BY ts_code
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
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
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]


class SwIndustryMappingCurrent:
    """Canonical current table for Shenwan industry hierarchy mapping."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def upsert(
        self,
        index_code: str,
        industry_name: Optional[str] = None,
        level: Optional[int] = None,
        parent_code: Optional[str] = None,
        src: Optional[str] = None,
        member_ts_code: Optional[str] = None,
        member_name: Optional[str] = None,
        in_date: Optional[date] = None,
        out_date: Optional[date] = None,
        is_active: bool = True,
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> str:
        """Upsert a SW industry mapping record."""
        record_id = str(uuid.uuid4())
        version_id_value = (
            None if version_id == CURRENT_VERSION_ID_SENTINEL else version_id
        )

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.sw_industry_mapping_current (
                        id, index_code, industry_name, level, parent_code,
                        src, member_ts_code, member_name, in_date, out_date,
                        is_active, version_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :index_code, :industry_name, :level, :parent_code,
                        :src, :member_ts_code, :member_name, :in_date, :out_date,
                        :is_active, :version_id, now(), now()
                    )
                    ON CONFLICT (index_code, member_ts_code, in_date) DO UPDATE SET
                        industry_name = EXCLUDED.industry_name,
                        level = EXCLUDED.level,
                        parent_code = EXCLUDED.parent_code,
                        src = EXCLUDED.src,
                        member_name = EXCLUDED.member_name,
                        out_date = EXCLUDED.out_date,
                        is_active = EXCLUDED.is_active,
                        version_id = EXCLUDED.version_id,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": record_id,
                    "index_code": index_code,
                    "industry_name": industry_name,
                    "level": level,
                    "parent_code": parent_code,
                    "src": src,
                    "member_ts_code": member_ts_code,
                    "member_name": member_name,
                    "in_date": in_date,
                    "out_date": out_date,
                    "is_active": 1 if is_active else 0,
                    "version_id": version_id_value,
                },
            )

        return record_id

    def bulk_upsert(
        self,
        records: list[dict],
        version_id: Optional[str] = CURRENT_VERSION_ID_SENTINEL,
    ) -> int:
        """Bulk upsert SW industry mapping records."""
        if not records:
            return 0

        count = 0
        for rec in records:
            self.upsert(
                index_code=rec["index_code"],
                industry_name=rec.get("industry_name"),
                level=rec.get("level"),
                parent_code=rec.get("parent_code"),
                src=rec.get("src"),
                member_ts_code=rec.get("member_ts_code"),
                member_name=rec.get("member_name"),
                in_date=rec.get("in_date"),
                out_date=rec.get("out_date"),
                is_active=rec.get("is_active", True),
                version_id=version_id,
            )
            count += 1

        return count

    def get_by_member(self, member_ts_code: str) -> list[dict]:
        """Get all SW industry mappings for a member."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, index_code, industry_name, level, parent_code,
                           src, member_ts_code, member_name, in_date, out_date,
                           is_active, created_at, updated_at
                    FROM ifa2.sw_industry_mapping_current
                    WHERE member_ts_code = :member_ts_code
                    ORDER BY in_date DESC
                    """
                ),
                {"member_ts_code": member_ts_code},
            ).fetchall()

            return [
                {
                    "id": row.id,
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
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]

    def list_all(self, limit: Optional[int] = None) -> list[dict]:
        """List all SW industry mapping records."""
        with self.engine.begin() as conn:
            if limit:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, index_code, industry_name, level, parent_code,
                               src, member_ts_code, member_name, in_date, out_date,
                               is_active, created_at, updated_at
                        FROM ifa2.sw_industry_mapping_current
                        ORDER BY index_code, level
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, index_code, industry_name, level, parent_code,
                               src, member_ts_code, member_name, in_date, out_date,
                               is_active, created_at, updated_at
                        FROM ifa2.sw_industry_mapping_current
                        ORDER BY index_code, level
                        """
                    ),
                ).fetchall()

            return [
                {
                    "id": row.id,
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
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]
