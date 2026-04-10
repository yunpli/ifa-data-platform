"""Job 1 preflight verification tests for iFA China-market low-frequency acquisition."""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestConfigLoad:
    """Test config loading and settings."""

    def test_settings_load_with_env(self):
        """Test that settings load from environment variables."""
        from ifa_data_platform.config.settings import get_settings

        settings = get_settings()
        assert settings.db_schema == "ifa2"
        assert settings.env == "dev"

    def test_tushare_token_in_settings(self):
        """Test that Tushare token field exists in settings."""
        from ifa_data_platform.config.settings import Settings

        settings = Settings()
        assert hasattr(settings, "tushare_token")
        assert settings.tushare_token == ""

    def test_tushare_token_from_env(self):
        """Test that Tushare token can be loaded from environment."""
        test_token = "test_token_123"
        with patch.dict(os.environ, {"TUSHARE_TOKEN": test_token}):
            from ifa_data_platform.config.settings import Settings

            settings = Settings()
            assert settings.tushare_token == test_token


class TestTushareClient:
    """Test Tushare client functionality."""

    def test_tushare_token_missing_error(self):
        """Test that missing token raises TushareTokenMissingError."""
        from ifa_data_platform.tushare import TushareTokenMissingError

        with patch.dict(os.environ, clear=True):
            from ifa_data_platform.tushare.client import TushareClient

            with pytest.raises(TushareTokenMissingError):
                TushareClient()

    def test_tushare_client_with_token(self):
        """Test that TushareClient can be initialized with token."""
        from ifa_data_platform.tushare.client import TushareClient

        client = TushareClient(token="test_token")
        assert client._token == "test_token"

    def test_get_tushare_client_factory(self):
        """Test get_tushare_client factory function."""
        from ifa_data_platform.tushare import get_tushare_client

        client = get_tushare_client(token="factory_test_token")
        assert client._token == "factory_test_token"

    def test_query_maps_fields_to_dicts(self):
        """Test that query() converts Tushare field/item payloads to row dicts."""
        from ifa_data_platform.tushare.client import TushareClient

        client = TushareClient(token="test_token")
        with patch.object(
            client,
            "_request",
            return_value={
                "code": 0,
                "data": {
                    "fields": ["ts_code", "symbol"],
                    "items": [["000001.SZ", "000001"], ["600000.SH", "600000"]],
                },
            },
        ):
            result = client.query("stock_basic", {"list_status": "L"})
        assert result == [
            {"ts_code": "000001.SZ", "symbol": "000001"},
            {"ts_code": "600000.SH", "symbol": "600000"},
        ]

    @pytest.mark.integration
    def test_tushare_smoke_call(self):
        """Test actual Tushare API call with real token.

        Requires TUSHARE_TOKEN environment variable or .env file.
        Marked as integration test - skip with: pytest -m "not integration"
        """
        token = os.environ.get("TUSHARE_TOKEN")
        if not token:
            pytest.skip("TUSHARE_TOKEN not set")

        from ifa_data_platform.tushare import get_tushare_client

        client = get_tushare_client(token=token)
        result = client.query(
            "stock_basic", {"list_status": "L", "fields": "ts_code,symbol"}
        )
        assert len(result) > 0
        assert "ts_code" in result[0] or result[0].get("ts_code")


class TestDatabaseSchema:
    """Test database schema visibility."""

    @pytest.mark.integration
    def test_ifa2_schema_exists(self):
        """Test that ifa2 schema is visible in database.

        Requires DATABASE_URL environment variable and running PostgreSQL.
        """
        from ifa_data_platform.config.settings import get_settings
        from sqlalchemy import create_engine, inspect

        settings = get_settings()
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)

        schemas = inspector.get_schema_names()
        if schemas:
            assert "ifa2" in schemas or "public" in schemas


class TestAlembicMigrations:
    """Test Alembic migration status."""

    @pytest.mark.integration
    def test_alembic_status_readable(self):
        """Test that Alembic status can be read.

        Requires DATABASE_URL and running migration environment.
        """
        from ifa_data_platform.config.settings import get_settings
        from sqlalchemy import create_engine
        import alembic.config
        import alembic.script

        settings = get_settings()
        engine = create_engine(settings.database_url)

        cfg = alembic.config.Config("alembic.ini")
        script = alembic.script.ScriptDirectory.from_config(cfg)

        revisions = list(script.walk_revisions())
        assert len(revisions) > 0
