from __future__ import annotations

from dataclasses import replace

import subprocess

from ifa_data_platform.fsj.llm_assist import (
    FSJMidLLMAssistant,
    FSJMidLLMRequest,
    FSJMidLLMResult,
    LLMInvocationFailure,
    ResilientMidLLMClient,
    _classify_llm_exception,
    build_fsj_mid_evidence_packet,
    build_fsj_mid_prompt,
    parse_fsj_mid_result,
)
from ifa_data_platform.fsj.mid_main_producer import MidMainFSJAssembler, MidMainProducerInput


class FakeMidLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_mid_main_v1"

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        return FSJMidLLMResult(
            summary="A股盘中主线更新：机器人链条盘中 working 结构延续，当前可做 intraday adjust，但午后仍需继续验证。",
            validation_signal_statement="盘中 working 结构、leader/event 与 validation_state=confirmed 共同支持机器人链条继续作为 intraday adjust 输入，但这仍是盘中验证，不是收盘最终确认。",
            afternoon_signal_statement="午后继续验证点：跟踪机器人链条是否继续向 breadth/heat 扩散，并观察 validation_state 是否维持 confirmed 或转弱。",
            judgment_statement="将机器人链条作为盘中主线修正输入：允许做 intraday thesis/adjust，但必须保留午后继续验证与失效边界，不把盘中 working 证据写成收盘结论。",
            invalidators=[
                "盘中 structure high layer 未继续刷新或关键表再次断档",
                "leader/breadth/heat 之间无法形成一致强化",
                "盘前预案锚点与盘中 working 证据出现明显背离",
            ],
            reasoning_trace=[
                "intraday structure packet present",
                "leader event packet present",
                "intraday-only boundary preserved",
            ],
            provider="stub",
            model_alias=self.model_alias,
            model_id="grok-4.1-thinking",
            prompt_version=self.prompt_version,
            usage={"total_tokens": 287},
            raw_response={"stub": True, "request_contract_mode": request.contract_mode},
        )


class FailingMidLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_mid_main_v1"

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        raise RuntimeError("synthetic mid llm failure")


class TimeoutMidLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_mid_main_v1"

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        raise subprocess.TimeoutExpired(cmd=["ifa_llm_cli.py"], timeout=120)


class FallbackSuccessMidLLMClient(FakeMidLLMClient):
    model_alias = "gemini31_pro_jmr"


class BoundaryFailMidLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_mid_main_v1"

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        raise RuntimeError("invalid llm field: validation_signal_statement")


def _sample_input(*, has_sufficient_high: bool = True, has_any_high: bool = True, has_background: bool = True) -> MidMainProducerInput:
    if has_sufficient_high:
        stock_1m_count = 128
        breadth_count = 24
        heat_count = 20
        leader_count = 5
        signal_scope_count = 2
        event_count = 4
        stock_1m_latest_time = "2099-04-22T11:18:00+08:00"
        breadth_latest_time = "2099-04-22T11:16:00+08:00"
        heat_latest_time = "2099-04-22T11:17:00+08:00"
        leader_latest_time = "2099-04-22T11:19:00+08:00"
        signal_latest_time = "2099-04-22T11:20:00+08:00"
        event_latest_time = "2099-04-22T11:21:00+08:00"
    elif has_any_high:
        stock_1m_count = 36
        breadth_count = 0
        heat_count = 0
        leader_count = 0
        signal_scope_count = 0
        event_count = 0
        stock_1m_latest_time = "2099-04-22T10:05:00+08:00"
        breadth_latest_time = None
        heat_latest_time = None
        leader_latest_time = None
        signal_latest_time = None
        event_latest_time = None
    else:
        stock_1m_count = 0
        breadth_count = 0
        heat_count = 0
        leader_count = 0
        signal_scope_count = 0
        event_count = 0
        stock_1m_latest_time = None
        breadth_latest_time = None
        heat_latest_time = None
        leader_latest_time = None
        signal_latest_time = None
        event_latest_time = None

    return MidMainProducerInput(
        business_date="2099-04-22",
        slot="mid",
        section_key="midday_main",
        section_type="thesis",
        bundle_topic_key="mainline_mid_update:2099-04-22",
        summary_topic="A股盘中主线更新",
        stock_1m_count=stock_1m_count,
        stock_1m_latest_time=stock_1m_latest_time,
        breadth_count=breadth_count,
        breadth_latest_time=breadth_latest_time,
        breadth_sector_code="BK0421" if breadth_count else None,
        breadth_spread_ratio=0.72 if breadth_count else None,
        heat_count=heat_count,
        heat_latest_time=heat_latest_time,
        heat_sector_code="BK0421" if heat_count else None,
        heat_score=8.4 if heat_count else None,
        leader_count=leader_count,
        leader_latest_time=leader_latest_time,
        leader_symbols=["300024.SZ", "002031.SZ", "601127.SH"] if leader_count else [],
        leader_confirmation_states=["confirmed", "candidate_confirming"] if leader_count else [],
        signal_scope_count=signal_scope_count,
        signal_latest_time=signal_latest_time,
        latest_validation_state="confirmed" if signal_scope_count else None,
        latest_emotion_stage="expanding" if signal_scope_count else None,
        latest_risk_state="balanced" if signal_scope_count else None,
        event_count=event_count,
        event_latest_time=event_latest_time,
        event_titles=["机器人链条盘中继续扩散", "算力方向再获催化"] if event_count else [],
        latest_text_count=3 if has_background else 0,
        latest_text_titles=["机器人政策催化", "AI 应用发布", "龙头预告更新"] if has_background else [],
        early_plan_summary="盘前预案聚焦机器人链条强度延续" if has_background else None,
        previous_late_summary="T-1 晚报维持机器人主线高位扩散" if has_background else None,
        replay_id="replay-mid-2099-04-22",
        slot_run_id="slot-run-mid-2099-04-22",
        report_run_id=None,
    )


def test_build_fsj_mid_prompt_and_parser_contract() -> None:
    data = _sample_input()
    packet = build_fsj_mid_evidence_packet(
        data,
        contract_mode="intraday_structure",
        completeness_label="complete",
        degrade_reason=None,
        freshness="fresh",
    )
    prompt = build_fsj_mid_prompt(
        FSJMidLLMRequest(
            business_date=data.business_date,
            section_key=data.section_key,
            contract_mode="intraday_structure",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet=packet,
        )
    )
    assert prompt["request"]["evidence_packet"]["intraday_structure"]["breadth_sector_code"] == "BK0421"

    result = parse_fsj_mid_result(
        parsed={
            "summary": "盘中结构延续，可做 intraday adjust，但午后仍需验证。",
            "validation_signal_statement": "盘中 working 结构已支持当前验证状态，但仍属于盘中验证而非最终确认。",
            "afternoon_signal_statement": "午后继续验证点：跟踪 breadth/heat 是否继续扩散。",
            "judgment_statement": "允许做 intraday thesis/adjust，但要保留午后继续验证边界。",
            "invalidators": ["a", "b"],
            "reasoning_trace": ["x", "y"],
        },
        envelope={"provider": "stub", "model_alias": "grok41_thinking", "model_id": "grok-4.1-thinking", "usage": {"total_tokens": 11}},
        prompt_version="fsj_mid_main_v1",
        model_alias="grok41_thinking",
    )
    assert result.model_alias == "grok41_thinking"
    assert result.invalidators == ["a", "b"]
    assert result.audit_payload(input_digest="abc")["prompt_version"] == "fsj_mid_main_v1"


def test_assembler_builds_mid_main_graph_with_fresh_intraday_structure() -> None:
    assembler = MidMainFSJAssembler()
    payload = assembler.build_bundle_graph(_sample_input(has_sufficient_high=True, has_any_high=True, has_background=True))

    bundle = payload["bundle"]
    assert bundle["slot"] == "mid"
    assert bundle["agent_domain"] == "main"
    assert bundle["section_key"] == "midday_main"
    assert bundle["assembly_mode"] == "contract_driven_first_slice"

    objects = payload["objects"]
    facts = [obj for obj in objects if obj["fsj_kind"] == "fact"]
    signals = [obj for obj in objects if obj["fsj_kind"] == "signal"]
    judgments = [obj for obj in objects if obj["fsj_kind"] == "judgment"]

    assert len(facts) >= 4
    assert len(signals) == 2
    assert len(judgments) == 1
    assert judgments[0]["object_type"] == "thesis"
    assert judgments[0]["judgment_action"] == "adjust"
    assert judgments[0]["direction"] == "conditional"
    assert "intraday thesis/adjust" in judgments[0]["statement"]

    validation_signal = next(obj for obj in signals if obj["object_key"] == "signal:mid:plan_validation_state")
    assert validation_signal["object_type"] == "confirmation"
    assert validation_signal["signal_strength"] == "medium"
    assert "validation_state=confirmed" in validation_signal["statement"]

    edges = payload["edges"]
    assert any(edge["edge_type"] == "fact_to_signal" for edge in edges)
    assert any(edge["edge_type"] == "signal_to_judgment" for edge in edges)

    evidence_links = payload["evidence_links"]
    assert any(link["evidence_role"] == "slot_replay" for link in evidence_links)
    assert any(link["ref_system"] == "highfreq" for link in evidence_links)
    assert any(link["ref_system"] == "archive_v2" for link in evidence_links)

    observed_records = payload["observed_records"]
    assert any(record["source_layer"] == "highfreq" for record in observed_records)
    assert any(record["source_layer"] == "lowfreq" for record in observed_records)


def test_mid_assembler_applies_llm_text_without_changing_deterministic_shape() -> None:
    assembler = MidMainFSJAssembler(llm_assistant=FSJMidLLMAssistant(FakeMidLLMClient()))
    payload = assembler.build_bundle_graph(_sample_input())

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    validation_signal = next(obj for obj in payload["objects"] if obj["object_key"] == "signal:mid:plan_validation_state")
    afternoon_signal = next(obj for obj in payload["objects"] if obj["object_key"] == "signal:mid:afternoon_tracking_state")

    assert payload["bundle"]["summary"].startswith("A股盘中主线更新：机器人链条盘中 working 结构延续")
    assert judgment["judgment_action"] == "adjust"
    assert judgment["object_type"] == "thesis"
    assert "intraday thesis/adjust" in judgment["statement"]
    assert "盘中 working" in validation_signal["statement"]
    assert "午后继续验证点" in afternoon_signal["statement"]
    assert payload["bundle"]["payload_json"]["llm_assist"]["applied"] is True
    assert payload["bundle"]["payload_json"]["llm_assist"]["model_alias"] == "grok41_thinking"
    assert judgment["attributes_json"]["llm_assist_applied"] is True
    assert judgment["attributes_json"]["llm_reasoning_trace"]


def test_mid_assembler_falls_back_when_llm_fails() -> None:
    assembler = MidMainFSJAssembler(llm_assistant=FSJMidLLMAssistant(FailingMidLLMClient()))
    payload = assembler.build_bundle_graph(_sample_input())

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    assert "intraday thesis/adjust" in judgment["statement"]
    assert payload["bundle"]["payload_json"]["llm_assist"]["applied"] is False
    assert "synthetic mid llm failure" in payload["bundle"]["payload_json"]["llm_assist"]["error"]


def test_resilient_mid_client_uses_fallback_model_after_primary_failure() -> None:
    client = ResilientMidLLMClient(clients=[FailingMidLLMClient(), FallbackSuccessMidLLMClient()])
    result = client.synthesize(
        FSJMidLLMRequest(
            business_date="2099-04-22",
            section_key="midday_main",
            contract_mode="intraday_structure",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert result.model_alias == "gemini31_pro_jmr"
    assert result.raw_response["_fsj_resilience"]["attempted_model_chain"] == ["grok41_thinking", "gemini31_pro_jmr"]
    assert result.raw_response["_fsj_resilience"]["failures"][0]["classification"] == "invoke_error"



def test_mid_assistant_surfaces_fallback_policy_envelope() -> None:
    _, audit = FSJMidLLMAssistant(ResilientMidLLMClient(clients=[TimeoutMidLLMClient(), FallbackSuccessMidLLMClient()])).maybe_synthesize(
        FSJMidLLMRequest(
            business_date="2099-04-22",
            section_key="midday_main",
            contract_mode="intraday_structure",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert audit["applied"] is True
    assert audit["model_alias"] == "gemini31_pro_jmr"
    assert audit["policy"]["outcome"] == "fallback_applied"
    assert audit["policy"]["attempted_model_chain"] == ["grok41_thinking", "gemini31_pro_jmr"]
    assert audit["policy"]["prior_failures"][0]["classification"] == "timeout"



def test_mid_assistant_tags_timeout_deterministic_degrade() -> None:
    _, audit = FSJMidLLMAssistant(TimeoutMidLLMClient()).maybe_synthesize(
        FSJMidLLMRequest(
            business_date="2099-04-22",
            section_key="midday_main",
            contract_mode="intraday_structure",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert audit["applied"] is False
    assert audit["failure_classification"] == "timeout"
    assert audit["policy"]["operator_tag"] == "llm_timeout"
    assert audit["policy"]["outcome"] == "deterministic_degrade"



def test_mid_assistant_surfaces_malformed_output_classification() -> None:
    _, audit = FSJMidLLMAssistant(BoundaryFailMidLLMClient()).maybe_synthesize(
        FSJMidLLMRequest(
            business_date="2099-04-22",
            section_key="midday_main",
            contract_mode="intraday_structure",
            completeness_label="complete",
            degrade_reason=None,
            evidence_packet={"k": "v"},
        )
    )
    assert audit["failure_classification"] == "malformed_output"
    assert audit["policy"]["operator_tag"] == "llm_malformed_output"



def test_mid_failure_classifier_covers_timeout_and_malformed() -> None:
    assert _classify_llm_exception(subprocess.TimeoutExpired(cmd=["x"], timeout=3)) == "timeout"
    assert _classify_llm_exception(LLMInvocationFailure("malformed_output", "bad json", "grok41_thinking")) == "malformed_output"


def test_assembler_degrades_to_monitoring_only_when_intraday_structure_missing() -> None:
    assembler = MidMainFSJAssembler()
    payload = assembler.build_bundle_graph(_sample_input(has_sufficient_high=False, has_any_high=False, has_background=True))

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    validation_signal = next(obj for obj in payload["objects"] if obj["object_key"] == "signal:mid:plan_validation_state")
    structure_fact = next(obj for obj in payload["objects"] if obj["object_key"] == "fact:mid:intraday_structure")

    assert judgment["object_type"] == "watch_item"
    assert judgment["judgment_action"] == "watch"
    assert "不形成正式盘中主结论" in judgment["statement"]
    assert validation_signal["object_type"] == "risk"
    assert validation_signal["signal_strength"] == "low"
    assert structure_fact["attributes_json"]["is_finalized_equivalent"] is False
    assert structure_fact["attributes_json"]["degrade_reason"] == "missing_intraday_structure"
    assert payload["bundle"]["payload_json"]["degrade"]["monitoring_only"] is True


def test_mid_assembler_backfills_runtime_lineage_ids_when_reader_inputs_are_missing() -> None:
    assembler = MidMainFSJAssembler()
    payload = assembler.build_bundle_graph(replace(_sample_input(), replay_id=None, slot_run_id=None))

    bundle = payload["bundle"]
    assert bundle["slot_run_id"].startswith("fsj-runtime:slot_run:2099-04-22:mid:")
    assert bundle["replay_id"].startswith("fsj-runtime:replay:2099-04-22:mid:")
    assert any(
        link["evidence_role"] == "slot_replay" and link["ref_key"] == bundle["replay_id"]
        for link in payload["evidence_links"]
    )
