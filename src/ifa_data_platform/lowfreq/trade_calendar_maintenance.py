from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.canonical_persistence import TradeCalCurrent
from ifa_data_platform.lowfreq.version_persistence import DatasetVersionRegistry, TradeCalHistory
from ifa_data_platform.tushare.client import get_tushare_client


@dataclass
class TradeCalendarSyncResult:
    run_id: str
    version_id: str
    exchange: str
    start_date: date
    end_date: date
    records_fetched: int
    promoted: bool
    watermark: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TradeCalendarHealthReport:
    exchange: str
    checked_at_utc: str
    status: str
    coverage_start: str
    coverage_end: str
    active_version_id: Optional[str]
    active_version_promoted_at_utc: Optional[str]
    findings: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TradeCalendarMaintenanceService:
    def __init__(self) -> None:
        self.engine = make_engine()
        self.current = TradeCalCurrent()
        self.history = TradeCalHistory()
        self.version_registry = DatasetVersionRegistry()
        self.client = get_tushare_client()

    def sync_range(
        self,
        start_date: date,
        end_date: date,
        exchange: str = "SSE",
        *,
        promote: bool = True,
        source_name: str = "tushare",
        run_id: Optional[str] = None,
    ) -> TradeCalendarSyncResult:
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")

        run_id = run_id or str(uuid.uuid4())
        watermark = end_date.strftime("%Y%m%d")
        version_id = self.version_registry.create_version(
            dataset_name="trade_cal",
            source_name=source_name,
            run_id=run_id,
            watermark=watermark,
            metadata={
                "maintenance": True,
                "exchange": exchange,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        records = self._fetch_range(start_date=start_date, end_date=end_date, exchange=exchange)
        self.current.bulk_upsert(records, version_id=version_id)
        self.history.store_version(version_id, records)
        if promote:
            self.version_registry.promote("trade_cal", version_id)

        return TradeCalendarSyncResult(
            run_id=run_id,
            version_id=version_id,
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
            records_fetched=len(records),
            promoted=promote,
            watermark=watermark,
        )

    def monthly_sync(
        self,
        anchor_date: Optional[date] = None,
        exchange: str = "SSE",
        lookback_days: int = 45,
        forward_days: int = 400,
        *,
        promote: bool = True,
    ) -> TradeCalendarSyncResult:
        anchor = anchor_date or datetime.now(timezone.utc).date()
        start_date = anchor - timedelta(days=lookback_days)
        end_date = anchor + timedelta(days=forward_days)
        return self.sync_range(start_date, end_date, exchange=exchange, promote=promote)

    def health_check(
        self,
        exchange: str = "SSE",
        *,
        anchor_date: Optional[date] = None,
        past_days_required: int = 30,
        future_days_required: int = 180,
        max_active_version_age_days: int = 45,
    ) -> TradeCalendarHealthReport:
        today = anchor_date or datetime.now(timezone.utc).date()
        coverage_start = today - timedelta(days=past_days_required)
        coverage_end = today + timedelta(days=future_days_required)
        findings: list[dict[str, Any]] = []

        with self.engine.begin() as conn:
            span = conn.execute(
                text(
                    """
                    SELECT min(cal_date) AS min_date, max(cal_date) AS max_date, count(*) AS row_count
                    FROM ifa2.trade_cal_current
                    WHERE exchange = :exchange
                    """
                ),
                {"exchange": exchange},
            ).mappings().first()
            missing = conn.execute(
                text(
                    """
                    SELECT d::date AS missing_date
                    FROM generate_series(cast(:start_date as date), cast(:end_date as date), interval '1 day') AS d
                    LEFT JOIN ifa2.trade_cal_current tc
                      ON tc.exchange = :exchange
                     AND tc.cal_date = d::date
                    WHERE tc.cal_date IS NULL
                    ORDER BY d
                    """
                ),
                {
                    "start_date": coverage_start,
                    "end_date": coverage_end,
                    "exchange": exchange,
                },
            ).mappings().all()

        active_version = self.version_registry.get_active_version("trade_cal")
        active_promoted_at = active_version.get("promoted_at_utc") if active_version else None
        if active_promoted_at is not None:
            promoted_at_utc = active_promoted_at.replace(tzinfo=timezone.utc) if active_promoted_at.tzinfo is None else active_promoted_at.astimezone(timezone.utc)
            promoted_age_days = (datetime.now(timezone.utc) - promoted_at_utc).total_seconds() / 86400.0
            if promoted_age_days > max_active_version_age_days:
                findings.append(
                    {
                        "severity": "warning",
                        "code": "active_version_stale",
                        "detail": {
                            "active_version_id": str(active_version["id"]),
                            "promoted_at_utc": promoted_at_utc.isoformat(),
                            "age_days": round(promoted_age_days, 1),
                            "max_allowed_days": max_active_version_age_days,
                        },
                    }
                )
        else:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_active_version",
                    "detail": {"dataset_name": "trade_cal"},
                }
            )

        min_date = span.get("min_date") if span else None
        max_date = span.get("max_date") if span else None
        if min_date is None or min_date > coverage_start:
            findings.append(
                {
                    "severity": "error",
                    "code": "coverage_start_too_recent",
                    "detail": {
                        "required_start": coverage_start.isoformat(),
                        "observed_start": min_date.isoformat() if min_date else None,
                    },
                }
            )
        if max_date is None or max_date < coverage_end:
            findings.append(
                {
                    "severity": "error",
                    "code": "coverage_end_too_early",
                    "detail": {
                        "required_end": coverage_end.isoformat(),
                        "observed_end": max_date.isoformat() if max_date else None,
                    },
                }
            )
        if missing:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_dates_in_required_window",
                    "detail": {
                        "missing_count": len(missing),
                        "sample_missing_dates": [row["missing_date"].isoformat() for row in missing[:20]],
                    },
                }
            )

        status = "ok" if not any(f["severity"] == "error" for f in findings) else "error"
        return TradeCalendarHealthReport(
            exchange=exchange,
            checked_at_utc=datetime.now(timezone.utc).isoformat(),
            status=status,
            coverage_start=coverage_start.isoformat(),
            coverage_end=coverage_end.isoformat(),
            active_version_id=str(active_version["id"]) if active_version else None,
            active_version_promoted_at_utc=(active_promoted_at.replace(tzinfo=timezone.utc) if active_promoted_at and active_promoted_at.tzinfo is None else active_promoted_at.astimezone(timezone.utc)).isoformat() if active_promoted_at else None,
            findings=findings,
        )

    def _fetch_range(self, start_date: date, end_date: date, exchange: str) -> list[dict[str, Any]]:
        records = self.client.query(
            "trade_cal",
            {
                "exchange": exchange,
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d"),
            },
        )
        parsed: list[dict[str, Any]] = []
        for rec in records:
            cal_date_raw = rec.get("cal_date")
            if not cal_date_raw:
                continue
            cal_date = datetime.strptime(str(cal_date_raw), "%Y%m%d").date()
            pretrade_raw = rec.get("pretrade_date")
            pretrade_date = None
            if pretrade_raw:
                try:
                    pretrade_date = datetime.strptime(str(pretrade_raw), "%Y%m%d").date()
                except ValueError:
                    pretrade_date = None
            parsed.append(
                {
                    "cal_date": cal_date,
                    "exchange": rec.get("exchange", exchange),
                    "is_open": str(rec.get("is_open", "0")) == "1",
                    "pretrade_date": pretrade_date,
                }
            )
        parsed.sort(key=lambda row: (row["exchange"], row["cal_date"]))
        return parsed
