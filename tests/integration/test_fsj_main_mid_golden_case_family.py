from __future__ import annotations

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine

from tests.integration.fsj_main_slot_golden_cases import (
    DB_URL,
    MID_MAIN_GOLDEN_CASES,
    assert_main_slot_golden_case,
    describe_slot_golden_case,
)


@pytest.fixture(autouse=True)
def _explicit_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    make_engine.cache_clear()
    get_settings.cache_clear()


@pytest.mark.parametrize("case", MID_MAIN_GOLDEN_CASES, ids=[case.name for case in MID_MAIN_GOLDEN_CASES])
def test_mid_main_golden_case_family_pins_second_p3_3_benchmark_slice(case) -> None:
    descriptor = describe_slot_golden_case(case)

    assert descriptor["family"] == "mid_main"
    assert descriptor["slot"] == "mid"
    assert descriptor["section_key"] == "midday_main"
    assert "slot_replay:runtime" in descriptor["required_evidence_roles"]
    assert "source_observed:highfreq" in descriptor["required_evidence_roles"]
    assert "prior_slot_reference:fsj" in descriptor["required_evidence_roles"]
    assert descriptor["minimum_counts"]["object_cnt"] >= 6

    assert_main_slot_golden_case(case)
