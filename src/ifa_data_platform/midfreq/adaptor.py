"""Base adaptor for mid-frequency datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FetchResult:
    """Result from a fetch operation."""

    records: list[dict]
    watermark: Optional[str]
    fetched_at: str


class BaseAdaptor:
    """Base class for mid-frequency dataset adaptors."""

    def fetch(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
        run_id: Optional[str] = None,
        source_name: str = "tushare",
        version_id: Optional[str] = None,
    ) -> FetchResult:
        """Fetch data from source.

        Args:
            dataset_name: Name of the dataset to fetch.
            watermark: Optional watermark (start_date, trade_date, etc.).
            limit: Optional record limit.
            run_id: Optional run_id for persistence linkage.
            source_name: Source name for raw persistence.
            version_id: Optional version ID for version tracking.

        Returns:
            FetchResult with records, watermark, and fetch timestamp.
        """
        raise NotImplementedError("Subclasses must implement fetch()")
