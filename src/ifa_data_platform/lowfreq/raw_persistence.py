"""Raw source mirror persistence for low-frequency ingestion."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _json_serial(obj: any) -> str:
    """Custom JSON serializer for dates and other non-serializable types."""
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class RawFetchPersistence:
    """Persists raw fetch results for replay and audit."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def store(
        self,
        run_id: str,
        source_name: str,
        dataset_name: str,
        request_params: Optional[dict],
        raw_payload: list[dict],
        watermark: Optional[str],
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> str:
        """Store a raw fetch result.

        Args:
            run_id: The run ID that triggered this fetch.
            source_name: Name of the data source (e.g., 'tushare').
            dataset_name: Name of the dataset (e.g., 'trade_cal').
            request_params: Parameters used for the API request.
            raw_payload: Raw records returned from the source.
            watermark: Watermark value from this fetch.
            status: Status of the fetch ('success' or 'failed').
            error_message: Optional error message if failed.

        Returns:
            ID of the inserted record.
        """
        fetch_id = str(uuid.uuid4())
        fetched_at = now_utc()

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.lowfreq_raw_fetch (
                        id, run_id, source_name, dataset_name, request_params_json,
                        fetched_at_utc, raw_payload_json, record_count, watermark,
                        status, error_message, created_at
                    )
                    VALUES (
                        :id, :run_id, :source_name, :dataset_name, :request_params_json,
                        :fetched_at_utc, :raw_payload_json, :record_count, :watermark,
                        :status, :error_message, now()
                    )
                    """
                ),
                {
                    "id": fetch_id,
                    "run_id": run_id,
                    "source_name": source_name,
                    "dataset_name": dataset_name,
                    "request_params_json": json.dumps(request_params)
                    if request_params
                    else None,
                    "fetched_at_utc": fetched_at,
                    "raw_payload_json": json.dumps(raw_payload, default=_json_serial),
                    "record_count": len(raw_payload),
                    "watermark": watermark,
                    "status": status,
                    "error_message": error_message,
                },
            )

        return fetch_id

    def get_latest_for_dataset(self, dataset_name: str, limit: int = 1) -> list[dict]:
        """Get the latest raw fetch records for a dataset.

        Args:
            dataset_name: Name of the dataset.
            limit: Maximum number of records to return.

        Returns:
            List of raw fetch records.
        """
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, run_id, source_name, dataset_name, request_params_json,
                           fetched_at_utc, raw_payload_json, record_count, watermark,
                           status, error_message, created_at
                    FROM ifa2.lowfreq_raw_fetch
                    WHERE dataset_name = :dataset_name
                    ORDER BY fetched_at_utc DESC
                    LIMIT :limit
                    """
                ),
                {"dataset_name": dataset_name, "limit": limit},
            ).fetchall()

            return [
                {
                    "id": row.id,
                    "run_id": row.run_id,
                    "source_name": row.source_name,
                    "dataset_name": row.dataset_name,
                    "request_params_json": row.request_params_json,
                    "fetched_at_utc": row.fetched_at_utc,
                    "raw_payload_json": row.raw_payload_json,
                    "record_count": row.record_count,
                    "watermark": row.watermark,
                    "status": row.status,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def get_by_run_id(self, run_id: str) -> Optional[dict]:
        """Get raw fetch record by run ID.

        Args:
            run_id: The run ID.

        Returns:
            Raw fetch record if found, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, run_id, source_name, dataset_name, request_params_json,
                           fetched_at_utc, raw_payload_json, record_count, watermark,
                           status, error_message, created_at
                    FROM ifa2.lowfreq_raw_fetch
                    WHERE run_id = :run_id
                    ORDER BY fetched_at_utc DESC
                    LIMIT 1
                    """
                ),
                {"run_id": run_id},
            ).fetchone()

            if not row:
                return None

            return {
                "id": row.id,
                "run_id": row.run_id,
                "source_name": row.source_name,
                "dataset_name": row.dataset_name,
                "request_params_json": row.request_params_json,
                "fetched_at_utc": row.fetched_at_utc,
                "raw_payload_json": row.raw_payload_json,
                "record_count": row.record_count,
                "watermark": row.watermark,
                "status": row.status,
                "error_message": row.error_message,
                "created_at": row.created_at,
            }
