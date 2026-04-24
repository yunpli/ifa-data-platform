from __future__ import annotations

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine

from tests.integration.fsj_main_slot_golden_cases import DB_URL, MAIN_SLOT_GOLDEN_CASES, assert_main_slot_golden_case


@pytest.fixture(autouse=True)
def _explicit_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    make_engine.cache_clear()
    get_settings.cache_clear()


@pytest.mark.parametrize("case", MAIN_SLOT_GOLDEN_CASES, ids=[case.name for case in MAIN_SLOT_GOLDEN_CASES])
def test_main_slot_golden_cases_cover_canonical_fsj_behaviors(case) -> None:
    assert_main_slot_golden_case(case)
