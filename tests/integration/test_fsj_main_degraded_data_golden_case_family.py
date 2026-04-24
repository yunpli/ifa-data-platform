from __future__ import annotations

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine

from tests.integration.fsj_main_slot_golden_cases import (
    DB_URL,
    DEGRADED_DATA_GOLDEN_CASES,
    assert_main_slot_golden_case,
    describe_slot_golden_case,
)


@pytest.fixture(autouse=True)
def _explicit_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    make_engine.cache_clear()
    get_settings.cache_clear()


@pytest.mark.parametrize("case", DEGRADED_DATA_GOLDEN_CASES, ids=[case.name for case in DEGRADED_DATA_GOLDEN_CASES])
def test_degraded_data_golden_case_family_pins_non_false_ready_contracts(case) -> None:
    descriptor = describe_slot_golden_case(case)

    assert descriptor["family"] in {"early_main", "late_main"}
    assert descriptor["expected_contract_mode"] in {"candidate_with_open_validation", "provisional_close_only"}
    if descriptor["expected_llm_outcome"] == "deterministic_degrade":
        assert descriptor["expected_llm_applied"] is False
        assert descriptor["expected_operator_tag"] == "llm_provider_failure"
    else:
        assert descriptor["expected_judgment_action"] == "monitor"
        assert "source_observed:midfreq" in descriptor["required_evidence_roles"]
        assert "source_observed:lowfreq" not in descriptor["required_evidence_roles"]

    assert_main_slot_golden_case(case)
