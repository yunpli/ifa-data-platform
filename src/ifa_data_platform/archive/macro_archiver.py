"""Macro historical archiver for D3 Macro Historical Archive.

This archiver fetches macro economic indicators from Tushare:
- cn_cpi: Consumer Price Index
- cn_ppi: Producer Price Index
- cn_gdp: GDP
- cn_pmi: PMI

These are the key macro slow variables that support long-term asset analysis.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.tushare.client import get_tushare_client

logger = logging.getLogger(__name__)


MACRO_INDICATORS = [
    {"series": "cn_cpi", "name": "Consumer Price Index (CPI)", "unit": "index"},
    {"series": "cn_ppi", "name": "Producer Price Index (PPI)", "unit": "yoy %"},
    {"series": "cn_gdp", "name": "Gross Domestic Product (GDP)", "unit": "100M RMB"},
    {"series": "cn_pmi", "name": "Purchasing Managers Index (PMI)", "unit": "index"},
]


class MacroArchiver:
    """Archiver for macro economic indicator historical data.

    Fetches macro economic indicators from Tushare and persists to macro_history.
    Supports checkpoint-based backfill and resume.
    """

    def __init__(self) -> None:
        self.engine = make_engine()
        self._tushare_client: Optional[object] = None
        self.dataset_name = "macro_history"

    @property
    def tushare_client(self):
        """Lazy-initialize Tushare client."""
        if self._tushare_client is None:
            self._tushare_client = get_tushare_client()
        return self._tushare_client

    def fetch_macro_data(
        self,
        macro_series: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch macro data for a series between dates."""
        if macro_series == "cn_cpi":
            return self._fetch_cpi(start_date, end_date)
        elif macro_series == "cn_ppi":
            return self._fetch_ppi(start_date, end_date)
        elif macro_series == "cn_gdp":
            return self._fetch_gdp(start_date, end_date)
        elif macro_series == "cn_pmi":
            return self._fetch_pmi(start_date, end_date)
        else:
            logger.warning(f"Unknown macro series: {macro_series}")
            return []

    def _fetch_cpi(self, start_date: date, end_date: date) -> list[dict]:
        """Fetch CPI (Consumer Price Index) data."""
        try:
            records = self.tushare_client.query(
                "cn_cpi",
                {"month": start_date.strftime("%Y%m")},
                timeout_sec=60,
            )
            return self._parse_cpi_records(records)
        except Exception as e:
            logger.warning(f"Failed to fetch CPI: {e}")
            return []

    def _fetch_ppi(self, start_date: date, end_date: date) -> list[dict]:
        """Fetch PPI (Producer Price Index) data."""
        try:
            records = self.tushare_client.query(
                "cn_ppi",
                {"month": start_date.strftime("%Y%m")},
                timeout_sec=60,
            )
            return self._parse_ppi_records(records)
        except Exception as e:
            logger.warning(f"Failed to fetch PPI: {e}")
            return []

    def _fetch_gdp(self, start_date: date, end_date: date) -> list[dict]:
        """Fetch GDP data."""
        try:
            quarter = self._get_quarter(start_date)
            records = self.tushare_client.query(
                "cn_gdp",
                {"quarter": quarter},
                timeout_sec=60,
            )
            return self._parse_gdp_records(records)
        except Exception as e:
            logger.warning(f"Failed to fetch GDP: {e}")
            return []

    def _fetch_pmi(self, start_date: date, end_date: date) -> list[dict]:
        """Fetch PMI (Purchasing Managers Index) data."""
        try:
            records = self.tushare_client.query(
                "cn_pmi",
                {"month": start_date.strftime("%Y%m")},
                timeout_sec=60,
            )
            return self._parse_pmi_records(records)
        except Exception as e:
            logger.warning(f"Failed to fetch PMI: {e}")
            return []

    def _get_quarter(self, d: date) -> str:
        """Get quarter string from date."""
        return f"{d.year}Q{(d.month - 1) // 3 + 1}"

    def _parse_cpi_records(self, records: list[dict]) -> list[dict]:
        """Parse CPI records into standardized format."""
        parsed = []
        for rec in records:
            month_str = rec.get("month", "")
            if not month_str:
                continue

            try:
                report_date = datetime.strptime(month_str + "01", "%Y%m%d").date()
            except (ValueError, TypeError):
                continue

            value = rec.get("nt_val") or rec.get("cnt_val")
            if value is None:
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            parsed.append(
                {
                    "macro_series": "cn_cpi",
                    "indicator_name": "Consumer Price Index (CPI)",
                    "report_date": report_date,
                    "value": value,
                    "unit": "index",
                    "source": "tushare",
                }
            )

        return parsed

    def _parse_ppi_records(self, records: list[dict]) -> list[dict]:
        """Parse PPI records into standardized format."""
        parsed = []
        for rec in records:
            month_str = rec.get("month", "")
            if not month_str:
                continue

            try:
                report_date = datetime.strptime(month_str + "01", "%Y%m%d").date()
            except (ValueError, TypeError):
                continue

            value = rec.get("ppi_yoy")
            if value is None:
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            parsed.append(
                {
                    "macro_series": "cn_ppi",
                    "indicator_name": "Producer Price Index (PPI)",
                    "report_date": report_date,
                    "value": value,
                    "unit": "yoy %",
                    "source": "tushare",
                }
            )

        return parsed

    def _parse_gdp_records(self, records: list[dict]) -> list[dict]:
        """Parse GDP records into standardized format."""
        parsed = []
        for rec in records:
            quarter_str = rec.get("quarter", "")
            if not quarter_str:
                continue

            try:
                year = int(quarter_str[:4])
                q = int(quarter_str[5])
                month = (q - 1) * 3 + 1
                report_date = date(year, month, 1)
            except (ValueError, TypeError):
                continue

            value = rec.get("gdp")
            if value is None:
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            parsed.append(
                {
                    "macro_series": "cn_gdp",
                    "indicator_name": "Gross Domestic Product (GDP)",
                    "report_date": report_date,
                    "value": value,
                    "unit": "100M RMB",
                    "source": "tushare",
                }
            )

        return parsed

    def _parse_pmi_records(self, records: list[dict]) -> list[dict]:
        """Parse PMI records into standardized format."""
        parsed = []
        for rec in records:
            month_str = rec.get("MONTH", "")
            if not month_str:
                continue

            try:
                report_date = datetime.strptime(month_str + "01", "%Y%m%d").date()
            except (ValueError, TypeError):
                continue

            value = rec.get("PMI010100")
            if value is None:
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            parsed.append(
                {
                    "macro_series": "cn_pmi",
                    "indicator_name": "Purchasing Managers Index (PMI)",
                    "report_date": report_date,
                    "value": value,
                    "unit": "index",
                    "source": "tushare",
                }
            )

        return parsed

    def persist_macro_records(self, records: list[dict]) -> int:
        """Persist macro records to the archive table.

        Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
        """
        if not records:
            return 0

        with self.engine.begin() as conn:
            for rec in records:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.macro_history (
                            id, macro_series, indicator_name, report_date, value, unit, source
                        ) VALUES (
                            gen_random_uuid(), :macro_series, :indicator_name, :report_date,
                            :value, :unit, :source
                        )
                        ON CONFLICT (macro_series, report_date) DO NOTHING
                        """
                    ),
                    {
                        "macro_series": rec["macro_series"],
                        "indicator_name": rec["indicator_name"],
                        "report_date": rec["report_date"],
                        "value": rec.get("value"),
                        "unit": rec.get("unit"),
                        "source": rec.get("source", "tushare"),
                    },
                )

        return len(records)

    def get_checkpoint(self, dataset_name: str) -> Optional[dict]:
        """Get checkpoint for a dataset from archive_checkpoints."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT dataset_name, asset_type, last_completed_date, batch_no, status
                    FROM ifa2.archive_checkpoints
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()
            if result:
                return {
                    "dataset_name": result.dataset_name,
                    "asset_type": result.asset_type,
                    "last_completed_date": result.last_completed_date,
                    "batch_no": result.batch_no,
                    "status": result.status,
                }
        return None

    def upsert_checkpoint(
        self,
        dataset_name: str,
        asset_type: str,
        last_completed_date: Optional[date] = None,
        batch_no: int = 0,
        status: str = "in_progress",
    ) -> None:
        """Upsert checkpoint to archive_checkpoints."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.archive_checkpoints (
                        id, dataset_name, asset_type, last_completed_date, batch_no, status, updated_at, created_at
                    )
                    SELECT gen_random_uuid(), :dataset_name, :asset_type, :last_completed_date,
                           :batch_no, :status, NOW(), NOW()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM ifa2.archive_checkpoints
                        WHERE dataset_name = :dataset_name AND asset_type = :asset_type
                    )
                    """
                ),
                {
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "last_completed_date": last_completed_date,
                    "batch_no": batch_no,
                    "status": status,
                },
            )
            conn.execute(
                text(
                    """
                    UPDATE ifa2.archive_checkpoints
                    SET last_completed_date = :last_completed_date,
                        batch_no = :batch_no,
                        status = :status,
                        updated_at = NOW()
                    WHERE dataset_name = :dataset_name AND asset_type = :asset_type
                    """
                ),
                {
                    "dataset_name": dataset_name,
                    "asset_type": asset_type,
                    "last_completed_date": last_completed_date,
                    "batch_no": batch_no,
                    "status": status,
                },
            )

    def run_archive(
        self,
        dataset_name: str = "macro_history",
        end_date: Optional[date] = None,
    ) -> int:
        """Run macro archive for the given date range.

        Uses checkpoint to support resume.
        Fetches data for all configured macro indicators.
        """
        if end_date is None:
            end_date = date.today()

        checkpoint = self.get_checkpoint(dataset_name)
        start_date = (
            checkpoint.get("last_completed_date")
            if checkpoint
            else date.today() - timedelta(days=365)
        )

        total_records = 0
        batch_no = 0

        for indicator in MACRO_INDICATORS:
            batch_no += 1
            series = indicator["series"]

            try:
                records = self.fetch_macro_data(series, start_date, end_date)
                if records:
                    persisted = self.persist_macro_records(records)
                    total_records += persisted
                    logger.info(f"Archived {persisted} records for {series}")
            except Exception as e:
                logger.warning(f"Failed to archive {series}: {e}")
                continue

        if total_records > 0:
            self.upsert_checkpoint(
                dataset_name=dataset_name,
                asset_type="macro",
                last_completed_date=end_date,
                batch_no=batch_no,
                status="completed",
            )
            logger.info(
                f"Macro archive completed: {total_records} records for {batch_no} indicators"
            )
        else:
            self.upsert_checkpoint(
                dataset_name=dataset_name,
                asset_type="macro",
                last_completed_date=end_date,
                batch_no=batch_no,
                status="completed",
            )
            logger.info("Macro archive completed with no new records")

        return total_records
