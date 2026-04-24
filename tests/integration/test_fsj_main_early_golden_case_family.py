from __future__ import annotations

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine

from tests.integration.fsj_main_slot_golden_cases import (
    DB_URL,
    EARLY_MAIN_GOLDEN_CASES,
    describe_slot_golden_case,
    assert_main_slot_golden_case,
)


@pytest.fixture(autouse=True)
def _explicit_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    make_engine.cache_clear()
    get_settings.cache_clear()


@pytest.mark.parametrize("case", EARLY_MAIN_GOLDEN_CASES, ids=[case.name for case in EARLY_MAIN_GOLDEN_CASES])
def test_early_main_golden_case_family_pins_first_p3_3_benchmark_slice(case) -> None:
    descriptor = describe_slot_golden_case(case)

    assert descriptor["family"] == "early_main"
    assert descriptor["slot"] == "early"
    assert descriptor["section_key"] == "pre_open_main"
    assert "slot_replay:runtime" in descriptor["required_evidence_roles"]
    assert "source_observed:highfreq" in descriptor["required_evidence_roles"]
    assert descriptor["minimum_counts"]["object_cnt"] >= 4

    assert_main_slot_golden_case(case)
