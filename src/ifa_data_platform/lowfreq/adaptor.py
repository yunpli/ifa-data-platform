"""Adaptor interface boundary - provider-agnostic."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator, Optional


@dataclass
class FetchResult:
    records: list[dict[str, Any]]
    watermark: Optional[str]
    fetched_at: str


class BaseAdaptor(ABC):
    """Abstract base class for low-frequency data source adaptors.

    This interface is provider-agnostic. Implementations (e.g., Tushare, Dummy, etc.)
    must provide fetch() and test_connection() methods.
    """

    @abstractmethod
    def fetch(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> FetchResult:
        """Fetch data from the source.

        Args:
            dataset_name: Name of the dataset to fetch.
            watermark: Optional watermark from previous run.
            limit: Optional record limit.

        Returns:
            FetchResult with records, watermark, and fetch timestamp.
        """
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Test the connection to the data source.

        Returns:
            True if connection is successful.
        """
        ...

    def close(self) -> None:
        """Optional cleanup method."""
        pass
