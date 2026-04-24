from __future__ import annotations

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.store import FSJStore
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError as LiveIsolationError


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"
LIVE_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp"


def _clear_caches() -> None:
    make_engine.cache_clear()
    get_settings.cache_clear()


def test_fsj_store_requires_explicit_database_url_under_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    _clear_caches()

    with pytest.raises(LiveIsolationError, match="DATABASE_URL must be set explicitly"):
        FSJStore()


def test_fsj_store_rejects_canonical_live_database_url_under_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", LIVE_DB_URL)
    _clear_caches()

    with pytest.raises(LiveIsolationError, match="canonical/live DB"):
        FSJStore()


def test_fsj_store_allows_explicit_test_database_url_under_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    _clear_caches()

    store = FSJStore(database_url=TEST_DB_URL)

    assert store.engine.url.database == "ifa_test"
    assert store.engine.url.host in {None, "/tmp"}
    store.engine.dispose()
