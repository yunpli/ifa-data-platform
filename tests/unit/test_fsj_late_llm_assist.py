from __future__ import annotations

from ifa_data_platform.fsj.late_main_producer import LateMainFSJAssembler, LateMainProducerInput
import subprocess

from ifa_data_platform.fsj.llm_assist import (
    FSJLateLLMAssistant,
    FSJLateLLMRequest,
    FSJLateLLMResult,
    LLMInvocationFailure,
    ResilientLateLLMClient,
    _classify_llm_exception,
    build_fsj_late_evidence_packet,
    build_fsj_late_prompt,
    parse_fsj_late_result,
)


class FakeLateLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_late_main_v1"

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        return FSJLateLLMResult(
            summary="A股收盘主线复盘：机器人方向由同日收盘稳定表与盘后文本共同支撑，可形成收盘主线结论。",
            close_signal_statement="same-day stable/final 市场表、北向/涨停结构与盘后文本已同向对齐，收盘 close package 可用。",
            context_signal_statement="盘中机器人回流与 validation=confirmed 只用于解释强化路径，不替代收盘 final confirmation。",
            judgment_statement="晚报主线可落在机器人链条，但结论只建立在同日 stable/final 事实之上，日内与T-1仅作解释和对照，不替代收盘最终确认。",
            invalidators=[
                "若盘后稳定表复核后出现大面积回撤或关键字段失真，则收盘主线结论失效",
                "若同日文本线索无法对应到已给定样本方向，则不得把题材扩写为更大主线",
            ],
            reasoning_trace=[
                "same-day final market packet ready",
                "same-day text packet timed and non-empty",
                "intraday context constrained to explanation only",
            ],
            provider="stub",
            model_alias=self.model_alias,
            model_id="grok-4.1-thinking",
            prompt_version=self.prompt_version,
            usage={"total_tokens": 321},
            raw_response={"stub": True, "request_contract_mode": request.contract_mode},
        )


class FailingLateLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_late_main_v1"

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        raise RuntimeError("synthetic llm failure")


class TimeoutLateLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_late_main_v1"

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        raise subprocess.TimeoutExpired(cmd=["ifa_llm_cli.py"], timeout=120)


class FallbackSuccessLateLLMClient(FakeLateLLMClient):
    model_alias = "gemini31_pro_jmr"


class BoundaryFailLateLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_late_main_v1"

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        raise RuntimeError("invalid llm field: close_signal_statement")


def _sample_input() -> LateMainProducerInput:
    return LateMainProducerInput(
        business_date="2099-04-22",
        slot="late",
        section_key="post_close_main",
        section_type="thesis",
        bundle_topic_key="mainline_close:2099-04-22",
        summary_topic="A股收盘主线复盘",
        equity_daily_count=420,
        equity_daily_latest_trade_date="2099-04-22",
        equity_daily_sample_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        northbound_flow_count=1,
        northbound_latest_trade_date="2099-04-22",
        northbound_net_amount=38.5,
        limit_up_detail_count=78,
        limit_up_detail_latest_trade_date="2099-04-22",
        limit_up_detail_sample_symbols=["300024.SZ", "002031.SZ"],
        limit_up_down_status_count=1,
        limit_up_down_latest_trade_date="2099-04-22",
        limit_up_count=56,
        limit_down_count=3,
        dragon_tiger_count=12,
        dragon_tiger_latest_trade_date="2099-04-22",
        dragon_tiger_sample_symbols=["300024.SZ", "002031.SZ"],
        sector_performance_count=42,
        sector_performance_latest_trade_date="2099-04-22",
        sector_performance_top_sector="机器人",
        sector_performance_top_pct_chg=4.8,
        latest_text_count=4,
        latest_text_titles=["盘后业绩快报", "政策催化", "龙头澄清", "机构点评"],
        latest_text_source_times=[
            "2099-04-22T16:03:00+08:00",
            "2099-04-22T15:41:00+08:00",
        ],
        intraday_event_count=5,
        intraday_event_latest_time="2099-04-22T14:56:00+08:00",
        intraday_event_titles=["机器人午后回流", "AI 应用分支走强"],
        intraday_leader_count=3,
        intraday_leader_latest_time="2099-04-22T14:57:00+08:00",
        intraday_leader_symbols=["300024.SZ", "002031.SZ"],
        intraday_signal_scope_count=2,
        intraday_signal_latest_time="2099-04-22T14:58:00+08:00",
        intraday_validation_state="confirmed",
        previous_late_summary="T-1 晚报维持机器人主线高位扩散",
        same_day_mid_summary="盘中机器人链条继续扩散并保持 validation=confirmed",
        replay_id="replay-late-2099-04-22",
        slot_run_id="slot-run-late-2099-04-22",
        report_run_id=None,
    )


def test_build_fsj_late_prompt_and_parser_contract() -> None:
    data = _sample_input()
    packet = build_fsj_late_evidence_packet(
        data,
        contract_mode="full_close_package",
        completeness_label="complete",
        degrade_reason=None,
    )
    prompt = build_fsj_late_prompt(
        FSJLateLLMRequest(
            business_date=data.business_date,
            section_key=data.section_key,
            contract_mode="full_close_package",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet=packet,
        )
    )
    assert "required_json_schema" in prompt
    assert prompt["request"]["evidence_packet"]["same_day_final_market"]["sector_performance_top_sector"] == "机器人"

    result = parse_fsj_late_result(
        parsed={
            "summary": "收盘主线可确认。",
            "close_signal_statement": "close package ready",
            "context_signal_statement": "intraday only as context",
            "judgment_statement": "form late thesis",
            "invalidators": ["a", "b"],
            "reasoning_trace": ["x", "y"],
        },
        envelope={"provider": "stub", "model_alias": "grok41_thinking", "model_id": "grok-4.1-thinking", "usage": {"total_tokens": 9}},
        prompt_version="fsj_late_main_v1",
        model_alias="grok41_thinking",
    )
    assert result.model_alias == "grok41_thinking"
    assert result.invalidators == ["a", "b"]
    assert result.audit_payload(input_digest="abc")["prompt_version"] == "fsj_late_main_v1"


def test_late_assembler_applies_llm_text_without_changing_deterministic_shape() -> None:
    assembler = LateMainFSJAssembler(llm_assistant=FSJLateLLMAssistant(FakeLateLLMClient()))
    payload = assembler.build_bundle_graph(_sample_input())

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    close_signal = next(obj for obj in payload["objects"] if obj["object_key"] == "signal:late:close_package_state")

    assert payload["bundle"]["summary"].startswith("A股收盘主线复盘：机器人方向")
    assert judgment["judgment_action"] == "confirm"
    assert judgment["object_type"] == "thesis"
    assert "机器人链条" in judgment["statement"]
    assert close_signal["object_type"] == "confirmation"
    assert payload["bundle"]["payload_json"]["llm_assist"]["applied"] is True
    assert payload["bundle"]["payload_json"]["llm_assist"]["model_alias"] == "grok41_thinking"
    assert payload["bundle"]["payload_json"]["llm_role_policy"]["policy_version"] == "fsj_llm_role_policy_v1"
    assert payload["bundle"]["payload_json"]["llm_role_policy"]["boundary_mode"] == "same_day_close"
    assert "upgrade_provisional_close_without_required_same_day_evidence" in payload["bundle"]["payload_json"]["llm_role_policy"]["forbidden_decisions"]
    assert judgment["attributes_json"]["llm_assist_applied"] is True
    assert judgment["attributes_json"]["llm_reasoning_trace"]


def test_late_assembler_falls_back_when_llm_fails() -> None:
    assembler = LateMainFSJAssembler(llm_assistant=FSJLateLLMAssistant(FailingLateLLMClient()))
    payload = assembler.build_bundle_graph(_sample_input())

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    assert "晚报主线收盘结论依据" in judgment["statement"]
    assert payload["bundle"]["payload_json"]["llm_assist"]["applied"] is False
    assert "synthetic llm failure" in payload["bundle"]["payload_json"]["llm_assist"]["error"]


def test_resilient_late_client_uses_fallback_model_after_primary_failure() -> None:
    client = ResilientLateLLMClient(clients=[FailingLateLLMClient(), FallbackSuccessLateLLMClient()])
    result = client.synthesize(
        FSJLateLLMRequest(
            business_date="2099-04-22",
            section_key="post_close_main",
            contract_mode="full_close_package",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert result.model_alias == "gemini31_pro_jmr"
    assert result.raw_response["_fsj_resilience"]["attempted_model_chain"] == ["grok41_thinking", "gemini31_pro_jmr"]
    assert result.raw_response["_fsj_resilience"]["failures"][0]["classification"] == "invoke_error"


def test_late_assistant_tags_timeout_deterministic_degrade() -> None:
    _, audit = FSJLateLLMAssistant(TimeoutLateLLMClient()).maybe_synthesize(
        FSJLateLLMRequest(
            business_date="2099-04-22",
            section_key="post_close_main",
            contract_mode="full_close_package",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert audit["applied"] is False
    assert audit["failure_classification"] == "timeout"
    assert audit["policy"]["operator_tag"] == "llm_timeout"
    assert audit["policy"]["outcome"] == "deterministic_degrade"


def test_late_assistant_surfaces_malformed_output_classification() -> None:
    _, audit = FSJLateLLMAssistant(BoundaryFailLateLLMClient()).maybe_synthesize(
        FSJLateLLMRequest(
            business_date="2099-04-22",
            section_key="post_close_main",
            contract_mode="full_close_package",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert audit["failure_classification"] == "malformed_output"
    assert audit["policy"]["operator_tag"] == "llm_malformed_output"


def test_late_failure_classifier_covers_timeout_and_malformed() -> None:
    assert _classify_llm_exception(subprocess.TimeoutExpired(cmd=["x"], timeout=3)) == "timeout"
    assert _classify_llm_exception(LLMInvocationFailure("malformed_output", "bad json", "grok41_thinking")) == "malformed_output"
