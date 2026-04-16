from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine

BJ_TZ = ZoneInfo("Asia/Shanghai")


@dataclass
class TradingDayStatus:
    as_of_date: date
    exchange: str
    is_trading_day: bool
    pretrade_date: Optional[date]
    source: str


class TradingCalendarService:
    def __init__(self) -> None:
        self.engine = make_engine()

    def get_day_status(self, target_date: date, exchange: str = "SSE") -> TradingDayStatus:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT cal_date, exchange, is_open, pretrade_date
                    FROM ifa2.trade_cal_current
                    WHERE cal_date = :cal_date AND exchange = :exchange
                    """
                ),
                {"cal_date": target_date, "exchange": exchange},
            ).mappings().first()
        if row:
            return TradingDayStatus(
                as_of_date=row["cal_date"],
                exchange=row["exchange"],
                is_trading_day=bool(row["is_open"]),
                pretrade_date=row["pretrade_date"],
                source="ifa2.trade_cal_current",
            )
        weekday = target_date.weekday()
        return TradingDayStatus(
            as_of_date=target_date,
            exchange=exchange,
            is_trading_day=weekday < 5,
            pretrade_date=None,
            source="fallback_weekday_only",
        )

    def get_runtime_day_type(self, current_time_utc: Optional[datetime] = None, exchange: str = "SSE") -> str:
        now = current_time_utc or datetime.now(timezone.utc)
        bj_now = now.astimezone(BJ_TZ)
        d = bj_now.date()
        weekday = d.weekday()
        status = self.get_day_status(d, exchange=exchange)
        if weekday == 5:
            return "saturday"
        if weekday == 6:
            return "sunday"
        if status.is_trading_day:
            return "trading_day"
        return "non_trading_weekday"

    def next_trading_day(self, target_date: date, exchange: str = "SSE", max_days: int = 14) -> Optional[date]:
        for offset in range(1, max_days + 1):
            cand = target_date + timedelta(days=offset)
            status = self.get_day_status(cand, exchange=exchange)
            if status.is_trading_day:
                return cand
        return None
