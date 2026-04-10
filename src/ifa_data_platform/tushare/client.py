"""Minimal Tushare client wrapper for China-market low-frequency acquisition."""

from typing import Any, Optional

import requests

from ifa_data_platform.config.settings import get_settings


class TushareError(Exception):
    """Base exception for Tushare client errors."""

    pass


class TushareTokenMissingError(TushareError):
    """Raised when Tushare token is not configured."""

    pass


class TushareAPIError(TushareError):
    """Raised when Tushare API returns an error."""

    pass


class TushareClient:
    """Minimal Tushare API client for low-frequency China-market data acquisition."""

    BASE_URL = "https://api.tushare.pro"

    def __init__(self, token: Optional[str] = None):
        """Initialize client with optional token override.

        Args:
            token: Tushare API token. If not provided, loads from settings.
        """
        if token:
            self._token = token
        else:
            settings = get_settings()
            self._token = settings.tushare_token
            if not self._token:
                raise TushareTokenMissingError(
                    "TUSHARE_TOKEN not configured. Set TUSHARE_TOKEN in .env file."
                )

    def _request(
        self, api_name: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Make a request to the Tushare API.

        Args:
            api_name: Name of the Tushare API endpoint.
            params: Optional parameters for the API call.

        Returns:
            JSON response from the API.

        Raises:
            TushareTokenMissingError: If token is not configured.
            TushareAPIError: If API returns an error.
        """
        if not self._token:
            raise TushareTokenMissingError(
                "TUSHARE_TOKEN not configured. Set TUSHARE_TOKEN in .env file."
            )

        payload: dict[str, Any] = {
            "api_name": api_name,
            "token": self._token,
        }
        if params:
            payload["params"] = params

        response = requests.post(self.BASE_URL, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        if data.get("code") != 0:
            raise TushareAPIError(
                f"Tushare API error [{data.get('code', '?')}]: {data.get('msg', 'Unknown error')}"
            )
        return data

    def query(
        self, api_name: str, params: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Query data from a Tushare API endpoint.

        Args:
            api_name: Name of the Tushare API endpoint.
            params: Optional parameters for the API call.

        Returns:
            List of records returned by the API.
        """
        data = self._request(api_name, params)
        return data.get("data", [])

    def test_connection(self) -> bool:
        """Test the Tushare API connection and token validity.

        Returns:
            True if connection is successful.

        Raises:
            TushareTokenMissingError: If token is not configured.
            TushareAPIError: If API returns an error.
        """
        if not self._token:
            raise TushareTokenMissingError(
                "TUSHARE_TOKEN not configured. Set TUSHARE_TOKEN in .env file."
            )

        data = self._request("get_token", {})
        if data.get("data", [{}])[0].get("token") == self._token:
            return True
        raise TushareAPIError("Token validation failed")


def get_tushare_client(token: Optional[str] = None) -> TushareClient:
    """Factory function to get a TushareClient instance.

    Args:
        token: Optional token override.

    Returns:
        Configured TushareClient instance.
    """
    return TushareClient(token=token)
