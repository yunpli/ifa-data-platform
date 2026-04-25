from __future__ import annotations

from ifa_data_platform.fsj.early_main_producer import EarlyMainFSJAssembler, EarlyMainProducerInput
import subprocess

from ifa_data_platform.fsj.llm_assist import (
    FSJ_ASSIST_POLICY_VERSION,
    FSJ_ASSIST_STRATEGY_NAME,
    FSJEarlyLLMAssistant,
    FSJEarlyLLMRequest,
    FSJEarlyLLMResult,
    LLMInvocationFailure,
    ResilientEarlyLLMClient,
    _classify_llm_exception,
    build_fsj_early_evidence_packet,
    build_fsj_early_prompt,
    parse_fsj_early_result,
    parse_fsj_late_result,
)


class FakeEarlyLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        return FSJEarlyLLMResult(
            summary="A股盘前主线预案：机器人链条具备盘前候选强度，但仍需开盘验证后才可升级。",
            candidate_signal_statement="盘前竞价、事件流与 focus seed 共同支持机器人方向进入主线候选，开盘后仍需继续验证，不能视为已确认。",
            judgment_statement="将机器人方向列为开盘首要验证候选；若竞价承接与事件强化无法延续，立即降回观察项，不把盘前候选写成已确认主线。",
            invalidators=[
                "09:27后竞价强度快速回落且高频覆盖未继续强化",
                "事件流与 focus 池无法形成同向验证",
                "近期文本催化在开盘前后得不到市场侧呼应",
            ],
            reasoning_trace=[
                "preopen auction packet present",
                "event and leader context present",
                "candidate boundary preserved",
            ],
            provider="stub",
            model_alias=self.model_alias,
            model_id="grok-4.1-thinking",
            prompt_version=self.prompt_version,
            usage={"total_tokens": 222},
            raw_response={"stub": True, "request_contract_mode": request.contract_mode},
        )


class FailingEarlyLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        raise RuntimeError("synthetic early llm failure")


class TimeoutEarlyLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        raise subprocess.TimeoutExpired(cmd=["ifa_llm_cli.py"], timeout=120)


class FallbackSuccessEarlyLLMClient(FakeEarlyLLMClient):
    model_alias = "gemini31_pro_jmr"


class BoundaryFailEarlyLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        raise RuntimeError("invalid llm field: early candidate boundary violated")


def _sample_input(*, has_high: bool = True, has_low: bool = True) -> EarlyMainProducerInput:
    return EarlyMainProducerInput(
        business_date="2099-04-22",
        slot="early",
        section_key="pre_open_main",
        section_type="thesis",
        bundle_topic_key="mainline_candidate:2099-04-22",
        summary_topic="A股盘前主线预案",
        trading_day_open=True,
        trading_day_label="open",
        focus_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        focus_list_types=["focus", "key_focus"],
        auction_count=18 if has_high else 0,
        auction_snapshot_time="2099-04-22T09:27:00+08:00" if has_high else None,
        event_count=6 if has_high else 0,
        event_latest_time="2099-04-22T09:25:00+08:00" if has_high else None,
        event_titles=["机器人链条隔夜催化", "算力链订单更新"] if has_high else [],
        leader_count=4 if has_high else 0,
        leader_symbols=["300024.SZ", "002031.SZ"] if has_high else [],
        signal_scope_count=1 if has_high else 0,
        latest_signal_state="candidate_confirming" if has_high else None,
        text_catalyst_count=3 if has_low else 0,
        text_catalyst_titles=["机器人政策催化", "AI 应用发布", "龙头预告更新"] if has_low else [],
        previous_archive_summary="昨日机器人主线维持高位扩散" if has_low else None,
        replay_id="replay-early-2099-04-22",
        slot_run_id="slot-run-early-2099-04-22",
        report_run_id=None,
    )


def test_build_fsj_early_prompt_and_parser_contract() -> None:
    data = _sample_input()
    packet = build_fsj_early_evidence_packet(
        data,
        contract_mode="candidate_with_open_validation",
        completeness_label="complete",
        degrade_reason=None,
    )
    prompt = build_fsj_early_prompt(
        FSJEarlyLLMRequest(
            business_date=data.business_date,
            section_key=data.section_key,
            contract_mode="candidate_with_open_validation",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet=packet,
        )
    )
    assert prompt["request"]["evidence_packet"]["reference_scope"]["focus_symbol_count"] == 3

    result = parse_fsj_early_result(
        parsed={
            "summary": "盘前候选已收敛，仍待开盘验证。",
            "candidate_signal_statement": "当前方向属于候选状态，开盘后仍需验证，不可视为已确认。",
            "judgment_statement": "先按候选跟踪，若开盘验证不成立则回退观察。",
            "invalidators": ["a", "b"],
            "reasoning_trace": ["x", "y"],
        },
        envelope={"provider": "stub", "model_alias": "grok41_thinking", "model_id": "grok-4.1-thinking", "usage": {"total_tokens": 9}},
        prompt_version="fsj_early_main_v1",
        model_alias="grok41_thinking",
    )
    assert result.model_alias == "grok41_thinking"
    assert result.invalidators == ["a", "b"]
    audit = result.audit_payload(input_digest="abc")
    assert audit["prompt_version"] == "fsj_early_main_v1"
    assert audit["adopted_output_fields"] == [
        "bundle.summary",
        "signal.statement",
        "judgment.statement",
        "judgment.invalidators",
        "judgment.attributes.llm_reasoning_trace",
    ]
    assert audit["discarded_output_fields"] == []
    assert audit["field_replay_ready"] is True


def test_early_assembler_applies_llm_text_without_changing_deterministic_shape() -> None:
    assembler = EarlyMainFSJAssembler(llm_assistant=FSJEarlyLLMAssistant(FakeEarlyLLMClient()))
    payload = assembler.build_bundle_graph(_sample_input())

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    signal = next(obj for obj in payload["objects"] if obj["object_key"] == "signal:early:mainline_candidate_state")

    assert payload["bundle"]["summary"].startswith("A股盘前主线预案：机器人链条")
    assert judgment["judgment_action"] == "validate"
    assert judgment["object_type"] == "thesis"
    assert "机器人方向" in judgment["statement"]
    assert "候选" in signal["statement"] and "验证" in signal["statement"]
    assert payload["bundle"]["payload_json"]["llm_assist"]["applied"] is True
    assert payload["bundle"]["payload_json"]["llm_assist"]["model_alias"] == "grok41_thinking"
    assert payload["bundle"]["payload_json"]["llm_role_policy"]["policy_version"] == "fsj_llm_role_policy_v1"
    assert payload["bundle"]["payload_json"]["llm_role_policy"]["boundary_mode"] == "candidate_only"
    assert "promote_candidate_to_same_day_confirmed_theme" in payload["bundle"]["payload_json"]["llm_role_policy"]["forbidden_decisions"]
    assert judgment["attributes_json"]["llm_assist_applied"] is True
    assert judgment["attributes_json"]["llm_reasoning_trace"]


def test_early_assembler_falls_back_when_llm_fails() -> None:
    assembler = EarlyMainFSJAssembler(llm_assistant=FSJEarlyLLMAssistant(FailingEarlyLLMClient()))
    payload = assembler.build_bundle_graph(_sample_input())

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    assert "开盘首要验证对象" in judgment["statement"]
    assert payload["bundle"]["payload_json"]["llm_assist"]["applied"] is False
    assert "synthetic early llm failure" in payload["bundle"]["payload_json"]["llm_assist"]["error"]


def test_late_parser_rejects_underfilled_invalidators_for_hardening() -> None:
    try:
        parse_fsj_late_result(
            parsed={
                "summary": "ok",
                "close_signal_statement": "ok",
                "context_signal_statement": "ok",
                "judgment_statement": "ok",
                "invalidators": ["only one"],
                "reasoning_trace": ["x", "y"],
            },
            envelope={"provider": "stub", "model_alias": "grok41_thinking"},
            prompt_version="fsj_late_main_v1",
            model_alias="grok41_thinking",
        )
    except RuntimeError as exc:
        assert "invalid llm field: invalidators" in str(exc)
    else:
        raise AssertionError("expected parser hardening failure")


def test_resilient_early_client_uses_fallback_model_after_primary_failure() -> None:
    client = ResilientEarlyLLMClient(clients=[FailingEarlyLLMClient(), FallbackSuccessEarlyLLMClient()])
    result = client.synthesize(
        FSJEarlyLLMRequest(
            business_date="2099-04-22",
            section_key="pre_open_main",
            contract_mode="candidate_with_open_validation",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert result.model_alias == "gemini31_pro_jmr"
    assert result.raw_response["_fsj_resilience"]["attempted_model_chain"] == ["grok41_thinking", "gemini31_pro_jmr"]
    assert result.raw_response["_fsj_resilience"]["failures"][0]["classification"] == "invoke_error"


def test_early_assistant_tags_timeout_deterministic_degrade() -> None:
    _, audit = FSJEarlyLLMAssistant(TimeoutEarlyLLMClient()).maybe_synthesize(
        FSJEarlyLLMRequest(
            business_date="2099-04-22",
            section_key="pre_open_main",
            contract_mode="candidate_with_open_validation",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert audit["applied"] is False
    assert audit["failure_classification"] == "timeout"
    assert audit["policy"]["operator_tag"] == "llm_timeout"
    assert audit["policy"]["outcome"] == "deterministic_degrade"
    assert audit["policy"]["policy_version"] == FSJ_ASSIST_POLICY_VERSION
    assert audit["policy"]["strategy_name"] == FSJ_ASSIST_STRATEGY_NAME
    assert audit["adopted_output_fields"] == []
    assert audit["discarded_output_field_count"] == 5
    assert audit["discard_reason"] == "timeout"
    assert audit["field_replay_ready"] is False


def test_early_assistant_surfaces_boundary_violation_classification() -> None:
    _, audit = FSJEarlyLLMAssistant(BoundaryFailEarlyLLMClient()).maybe_synthesize(
        FSJEarlyLLMRequest(
            business_date="2099-04-22",
            section_key="pre_open_main",
            contract_mode="candidate_with_open_validation",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert audit["failure_classification"] == "boundary_violation"
    assert audit["policy"]["operator_tag"] == "llm_boundary_violation"


def test_role_policy_exposes_time_window_schema_and_evidence_guards() -> None:
    assembler = EarlyMainFSJAssembler(llm_assistant=FSJEarlyLLMAssistant(FakeEarlyLLMClient()))
    payload = assembler.build_bundle_graph(_sample_input())
    role_policy = payload["bundle"]["payload_json"]["llm_role_policy"]
    assert role_policy["time_window_guard"] == "candidate_only"
    assert role_policy["schema_enforcement"] == "slot_specific_required_json_schema_plus_parser_validation"
    assert role_policy["evidence_binding"] == "input_digest_and_evidence_packet_only"


def test_llm_failure_classifier_covers_timeout_and_malformed() -> None:
    assert _classify_llm_exception(subprocess.TimeoutExpired(cmd=["x"], timeout=3)) == "timeout"
    assert _classify_llm_exception(LLMInvocationFailure("malformed_output", "bad json", "grok41_thinking")) == "malformed_output"
