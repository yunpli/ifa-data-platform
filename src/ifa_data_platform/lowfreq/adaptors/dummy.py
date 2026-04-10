"""Dummy adaptor for testing and placeholder low-frequency data."""

from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult


class DummyAdaptor(BaseAdaptor):
    """Dummy adaptor that returns mock data for testing and placeholder jobs."""

    def __init__(self, mock_records: Optional[list[dict]] = None) -> None:
        self._mock_records = mock_records or [
            {
                "symbol": "000001",
                "name": "平安银行",
                "price": 12.34,
                "date": "2024-01-15",
            },
            {
                "symbol": "600000",
                "name": "浦发银行",
                "price": 8.56,
                "date": "2024-01-15",
            },
        ]

    def fetch(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
        run_id: Optional[str] = None,
        source_name: str = "generic",
        version_id: Optional[str] = None,
    ) -> FetchResult:
        records = self._mock_records.copy()
        if limit:
            records = records[:limit]

        new_watermark = datetime.now(timezone.utc).isoformat()

        return FetchResult(
            records=records,
            watermark=new_watermark,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

    def test_connection(self) -> bool:
        return True
