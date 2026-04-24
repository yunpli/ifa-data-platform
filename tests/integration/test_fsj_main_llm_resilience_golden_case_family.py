from __future__ import annotations

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine

from tests.integration.fsj_main_slot_golden_cases import (
    DB_URL,
    LLM_RESILIENCE_GOLDEN_CASES,
    assert_main_slot_golden_case,
    describe_slot_golden_case,
)


@pytest.fixture(autouse=True)
def _explicit_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    make_engine.cache_clear()
    get_settings.cache_clear()


@pytest.mark.parametrize("case", LLM_RESILIENCE_GOLDEN_CASES, ids=[case.name for case in LLM_RESILIENCE_GOLDEN_CASES])
def test_llm_resilience_golden_case_family_pins_cross_slot_timeout_and_fallback_contracts(case) -> None:
    descriptor = describe_slot_golden_case(case)

    assert descriptor["family"] in {"early_main", "mid_main", "late_main"}
    assert descriptor["expected_llm_outcome"] in {"fallback_applied", "deterministic_degrade"}
    assert descriptor["expected_attempted_model_chain"] == ["grok41_thinking", "gemini31_pro_jmr"]
    assert "timeout" in descriptor["required_attempt_failure_classifications"]
    if descriptor["expected_llm_outcome"] == "deterministic_degrade":
        assert descriptor["expected_operator_tag"] == "llm_provider_failure"

    assert_main_slot_golden_case(case)
