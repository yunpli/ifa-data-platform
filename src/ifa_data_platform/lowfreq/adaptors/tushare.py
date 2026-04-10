"""Tushare adaptor for China-market low-frequency data (placeholder)."""

from typing import Optional

from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult


class TushareAdaptor(BaseAdaptor):
    """Tushare adaptor placeholder for China-market data.

    This is a placeholder implementation. In production, it would:
    - Use the existing TushareClient from ifa_data_platform.tushare
    - Map Tushare API responses to FetchResult
    - Handle pagination, retries, and error handling

    Currently returns empty results as a stub.
    """

    def fetch(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> FetchResult:
        return FetchResult(
            records=[],
            watermark=None,
            fetched_at="",
        )

    def test_connection(self) -> bool:
        return True
