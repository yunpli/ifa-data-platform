from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable
import subprocess

import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.fsj import FSJStore
from ifa_data_platform.fsj.early_main_producer import EarlyMainFSJAssembler, EarlyMainFSJProducer, EarlyMainProducerInput
from ifa_data_platform.fsj.late_main_producer import LateMainFSJProducer, LateMainProducerInput
from ifa_data_platform.fsj.llm_assist import (
    FSJEarlyLLMAssistant,
    FSJEarlyLLMRequest,
    FSJEarlyLLMResult,
    ResilientEarlyLLMClient,
)
from ifa_data_platform.fsj.mid_main_producer import MidMainFSJProducer, MidMainProducerInput

DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"


class FakeEarlyMainInputReader:
    def __init__(self, payload: EarlyMainProducerInput) -> None:
        self.payload = payload

    def read(self, *, business_date: str, slot: str = "early", section_key: str = "pre_open_main") -> EarlyMainProducerInput:
        assert business_date == self.payload.business_date
        assert slot == self.payload.slot
        assert section_key == self.payload.section_key
        return self.payload


class FakeMidMainInputReader:
    def __init__(self, payload: MidMainProducerInput) -> None:
        self.payload = payload

    def read(self, *, business_date: str, slot: str = "mid", section_key: str = "midday_main") -> MidMainProducerInput:
        assert business_date == self.payload.business_date
        assert slot == self.payload.slot
        assert section_key == self.payload.section_key
        return self.payload


class PrimaryTimeoutEarlyLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        raise subprocess.TimeoutExpired(cmd=["ifa_llm_cli.py"], timeout=120)


class FallbackSuccessEarlyLLMClient:
    model_alias = "gemini31_pro_jmr"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        return FSJEarlyLLMResult(
            summary="A股盘前主线预案：机器人链条在竞价、事件流与 focus seed 之间形成优先候选，primary 超时后由 fallback 模型完成候选表达补强，但仍待开盘验证。",
            candidate_signal_statement="盘前竞价、事件流与 focus seed 已共同支持机器人链条进入主线候选，当前由 fallback 模型在 primary 超时后完成表达补强，但这仍只是待开盘验证的 candidate state。",
            judgment_statement="将机器人链条列为开盘首要验证候选：本次由 fallback 模型在 primary 超时后完成补强；若竞价承接、事件延续与 focus 对齐不能继续兑现，立即降回观察项，不把盘前候选写成已确认主线。",
            invalidators=[
                "09:27后竞价承接快速回落且高频覆盖未继续刷新",
                "事件流与候选龙头无法在 focus 池中形成一致验证",
                "若把隔夜文本催化直接写成 same-day 开盘确认，则当前判断无效",
            ],
            reasoning_trace=[
                "preopen auction packet present",
                "event and leader packet present",
                "primary timeout then fallback success",
            ],
            provider="eval-stub",
            model_alias=self.model_alias,
            model_id="gemini-3.1-pro",
            prompt_version=self.prompt_version,
            usage={"total_tokens": 341},
            raw_response={"stub": True, "fallback": True},
        )


class AllFailEarlyLLMClient(PrimaryTimeoutEarlyLLMClient):
    model_alias = "gemini31_pro_jmr"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        raise RuntimeError("business repo llm cli failed: synthetic provider failure")


class FakeLateMainInputReader:
    def __init__(self, payload: LateMainProducerInput) -> None:
        self.payload = payload

    def read(self, *, business_date: str, slot: str = "late", section_key: str = "post_close_main") -> LateMainProducerInput:
        assert business_date == self.payload.business_date
        assert slot == self.payload.slot
        assert section_key == self.payload.section_key
        return self.payload


@dataclass(frozen=True)
class SlotGoldenCase:
    name: str
    slot: str
    section_key: str
    producer_factory: Callable[[FSJStore], Any]
    expected_judgment_action: str
    expected_object_type: str
    expected_contract_mode: str | None
    required_evidence_roles: set[tuple[str, str]]
    minimum_counts: dict[str, int]
    expected_llm_outcome: str | None = None
    expected_llm_applied: bool | None = None
    expected_llm_model_alias: str | None = None
    expected_operator_tag: str | None = None
    expected_attempted_model_chain: list[str] | None = None
    required_attempt_failure_classifications: set[str] | None = None


def engine() -> sa.Engine:
    return sa.create_engine(DB_URL, future=True)


def cleanup_bundle(bundle_id: str) -> None:
    with engine().begin() as conn:
        conn.execute(text("DELETE FROM ifa2.ifa_fsj_report_links WHERE bundle_id = :bundle_id"), {"bundle_id": bundle_id})
        conn.execute(text("DELETE FROM ifa2.ifa_fsj_observed_records WHERE bundle_id = :bundle_id"), {"bundle_id": bundle_id})
        conn.execute(text("DELETE FROM ifa2.ifa_fsj_evidence_links WHERE bundle_id = :bundle_id"), {"bundle_id": bundle_id})
        conn.execute(text("DELETE FROM ifa2.ifa_fsj_edges WHERE bundle_id = :bundle_id"), {"bundle_id": bundle_id})
        conn.execute(text("DELETE FROM ifa2.ifa_fsj_objects WHERE bundle_id = :bundle_id"), {"bundle_id": bundle_id})
        conn.execute(text("DELETE FROM ifa2.ifa_fsj_bundles WHERE bundle_id = :bundle_id"), {"bundle_id": bundle_id})


def persisted_bundle_counts(bundle_id: str) -> dict[str, int]:
    with engine().begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM ifa2.ifa_fsj_objects WHERE bundle_id=:bundle_id) AS object_cnt,
                  (SELECT count(*) FROM ifa2.ifa_fsj_edges WHERE bundle_id=:bundle_id) AS edge_cnt,
                  (SELECT count(*) FROM ifa2.ifa_fsj_evidence_links WHERE bundle_id=:bundle_id) AS evidence_cnt,
                  (SELECT count(*) FROM ifa2.ifa_fsj_observed_records WHERE bundle_id=:bundle_id) AS observed_cnt
                """
            ),
            {"bundle_id": bundle_id},
        ).mappings().one()
    return {str(key): int(value) for key, value in row.items()}


def assert_main_slot_golden_case(case: SlotGoldenCase) -> None:
    producer = case.producer_factory(FSJStore(database_url=DB_URL))
    payload = producer.produce(business_date="2099-04-22")
    bundle_id = payload["bundle"]["bundle_id"]
    try:
        persisted = producer.produce_and_persist(business_date="2099-04-22")
        assert persisted["bundle"]["bundle_id"] == bundle_id
        assert persisted["bundle"]["slot"] == case.slot
        assert persisted["bundle"]["section_key"] == case.section_key

        judgments = [obj for obj in persisted["objects"] if obj["fsj_kind"] == "judgment"]
        assert len(judgments) == 1
        assert judgments[0]["judgment_action"] == case.expected_judgment_action
        assert judgments[0]["object_type"] == case.expected_object_type
        if case.expected_contract_mode is not None:
            assert judgments[0]["attributes_json"]["contract_mode"] == case.expected_contract_mode

        evidence_roles = {(row["evidence_role"], row["ref_system"]) for row in persisted["evidence_links"]}
        assert case.required_evidence_roles.issubset(evidence_roles)

        llm_audit = persisted["bundle"]["payload_json"].get("llm_assist", {})
        llm_policy = llm_audit.get("policy") or {}
        if case.expected_llm_outcome is not None:
            assert llm_policy.get("outcome") == case.expected_llm_outcome
        if case.expected_llm_applied is not None:
            assert llm_audit.get("applied") is case.expected_llm_applied
        if case.expected_llm_model_alias is not None:
            assert llm_audit.get("model_alias") == case.expected_llm_model_alias
        if case.expected_operator_tag is not None:
            assert llm_policy.get("operator_tag") == case.expected_operator_tag
        if case.expected_attempted_model_chain is not None:
            assert llm_policy.get("attempted_model_chain") == case.expected_attempted_model_chain
        if case.required_attempt_failure_classifications is not None:
            observed_classifications = {
                row.get("classification") for row in (llm_audit.get("attempt_failures") or llm_policy.get("prior_failures") or [])
            }
            assert case.required_attempt_failure_classifications.issubset(observed_classifications)

        counts = persisted_bundle_counts(bundle_id)
        for key, minimum in case.minimum_counts.items():
            assert counts[key] >= minimum
    finally:
        cleanup_bundle(bundle_id)


def _build_early_case(store: FSJStore) -> EarlyMainFSJProducer:
    sample = EarlyMainProducerInput(
        business_date="2099-04-22",
        slot="early",
        section_key="pre_open_main",
        section_type="thesis",
        bundle_topic_key=f"mainline_candidate:{uuid.uuid4()}",
        summary_topic="A股盘前主线预案",
        trading_day_open=True,
        trading_day_label="open",
        focus_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        focus_list_types=["focus", "key_focus"],
        auction_count=12,
        auction_snapshot_time="2099-04-22T09:27:00+08:00",
        event_count=5,
        event_latest_time="2099-04-22T09:24:00+08:00",
        event_titles=["机器人链条隔夜催化", "AI 应用催化"],
        leader_count=3,
        leader_symbols=["300024.SZ", "002031.SZ"],
        signal_scope_count=1,
        latest_signal_state="candidate_confirming",
        text_catalyst_count=2,
        text_catalyst_titles=["机器人政策催化", "AI 应用发布"],
        previous_archive_summary="昨日机器人主线维持高位扩散",
        replay_id=f"replay:{uuid.uuid4()}",
        slot_run_id=f"slot-run:{uuid.uuid4()}",
        report_run_id=None,
    )
    return EarlyMainFSJProducer(reader=FakeEarlyMainInputReader(sample), store=store)


def _build_early_llm_fallback_case(store: FSJStore) -> EarlyMainFSJProducer:
    sample = EarlyMainProducerInput(
        business_date="2099-04-22",
        slot="early",
        section_key="pre_open_main",
        section_type="thesis",
        bundle_topic_key=f"mainline_candidate_fallback:{uuid.uuid4()}",
        summary_topic="A股盘前主线预案",
        trading_day_open=True,
        trading_day_label="open",
        focus_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        focus_list_types=["focus", "key_focus"],
        auction_count=18,
        auction_snapshot_time="2099-04-22T09:27:00+08:00",
        event_count=6,
        event_latest_time="2099-04-22T09:25:00+08:00",
        event_titles=["机器人链条隔夜催化", "算力链订单更新"],
        leader_count=4,
        leader_symbols=["300024.SZ", "002031.SZ"],
        signal_scope_count=1,
        latest_signal_state="candidate_confirming",
        text_catalyst_count=3,
        text_catalyst_titles=["机器人政策催化", "AI 应用发布", "龙头预告更新"],
        previous_archive_summary="昨日机器人主线维持高位扩散",
        replay_id=f"replay:{uuid.uuid4()}",
        slot_run_id=f"slot-run:{uuid.uuid4()}",
        report_run_id=None,
    )
    return EarlyMainFSJProducer(
        reader=FakeEarlyMainInputReader(sample),
        store=store,
        assembler=EarlyMainFSJAssembler(
            llm_assistant=FSJEarlyLLMAssistant(
                ResilientEarlyLLMClient(clients=[PrimaryTimeoutEarlyLLMClient(), FallbackSuccessEarlyLLMClient()])
            )
        ),
    )


def _build_early_llm_deterministic_degrade_case(store: FSJStore) -> EarlyMainFSJProducer:
    sample = EarlyMainProducerInput(
        business_date="2099-04-22",
        slot="early",
        section_key="pre_open_main",
        section_type="thesis",
        bundle_topic_key=f"mainline_candidate_degrade:{uuid.uuid4()}",
        summary_topic="A股盘前主线预案",
        trading_day_open=True,
        trading_day_label="open",
        focus_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        focus_list_types=["focus", "key_focus"],
        auction_count=18,
        auction_snapshot_time="2099-04-22T09:27:00+08:00",
        event_count=6,
        event_latest_time="2099-04-22T09:25:00+08:00",
        event_titles=["机器人链条隔夜催化", "算力链订单更新"],
        leader_count=4,
        leader_symbols=["300024.SZ", "002031.SZ"],
        signal_scope_count=1,
        latest_signal_state="candidate_confirming",
        text_catalyst_count=3,
        text_catalyst_titles=["机器人政策催化", "AI 应用发布", "龙头预告更新"],
        previous_archive_summary="昨日机器人主线维持高位扩散",
        replay_id=f"replay:{uuid.uuid4()}",
        slot_run_id=f"slot-run:{uuid.uuid4()}",
        report_run_id=None,
    )
    return EarlyMainFSJProducer(
        reader=FakeEarlyMainInputReader(sample),
        store=store,
        assembler=EarlyMainFSJAssembler(
            llm_assistant=FSJEarlyLLMAssistant(
                ResilientEarlyLLMClient(clients=[PrimaryTimeoutEarlyLLMClient(), AllFailEarlyLLMClient()])
            )
        ),
    )


def _build_mid_case(store: FSJStore) -> MidMainFSJProducer:
    sample = MidMainProducerInput(
        business_date="2099-04-22",
        slot="mid",
        section_key="midday_main",
        section_type="thesis",
        bundle_topic_key=f"mainline_mid_update:{uuid.uuid4()}",
        summary_topic="A股盘中主线更新",
        stock_1m_count=128,
        stock_1m_latest_time="2099-04-22T11:18:00+08:00",
        breadth_count=24,
        breadth_latest_time="2099-04-22T11:16:00+08:00",
        breadth_sector_code="BK0421",
        breadth_spread_ratio=0.72,
        heat_count=20,
        heat_latest_time="2099-04-22T11:17:00+08:00",
        heat_sector_code="BK0421",
        heat_score=8.4,
        leader_count=5,
        leader_latest_time="2099-04-22T11:19:00+08:00",
        leader_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        leader_confirmation_states=["confirmed", "candidate_confirming"],
        signal_scope_count=2,
        signal_latest_time="2099-04-22T11:20:00+08:00",
        latest_validation_state="confirmed",
        latest_emotion_stage="expanding",
        latest_risk_state="balanced",
        event_count=4,
        event_latest_time="2099-04-22T11:21:00+08:00",
        event_titles=["机器人链条盘中继续扩散", "算力方向再获催化"],
        latest_text_count=3,
        latest_text_titles=["机器人政策催化", "AI 应用发布", "龙头预告更新"],
        early_plan_summary="盘前预案聚焦机器人链条强度延续",
        previous_late_summary="T-1 晚报维持机器人主线高位扩散",
        replay_id=f"replay:{uuid.uuid4()}",
        slot_run_id=f"slot-run:{uuid.uuid4()}",
        report_run_id=None,
    )
    return MidMainFSJProducer(reader=FakeMidMainInputReader(sample), store=store)


def _build_late_case(store: FSJStore) -> LateMainFSJProducer:
    sample = LateMainProducerInput(
        business_date="2099-04-22",
        slot="late",
        section_key="post_close_main",
        section_type="thesis",
        bundle_topic_key=f"mainline_close:{uuid.uuid4()}",
        summary_topic="A股收盘主线复盘",
        equity_daily_count=420,
        equity_daily_latest_trade_date="2099-04-22",
        equity_daily_sample_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        northbound_flow_count=0,
        northbound_latest_trade_date=None,
        northbound_net_amount=None,
        limit_up_detail_count=0,
        limit_up_detail_latest_trade_date=None,
        limit_up_detail_sample_symbols=[],
        limit_up_down_status_count=0,
        limit_up_down_latest_trade_date=None,
        limit_up_count=None,
        limit_down_count=None,
        dragon_tiger_count=0,
        dragon_tiger_latest_trade_date=None,
        dragon_tiger_sample_symbols=[],
        sector_performance_count=0,
        sector_performance_latest_trade_date=None,
        sector_performance_top_sector=None,
        sector_performance_top_pct_chg=None,
        latest_text_count=0,
        latest_text_titles=[],
        latest_text_source_times=[],
        intraday_event_count=4,
        intraday_event_latest_time="2099-04-22T14:55:00+08:00",
        intraday_event_titles=["机器人午后回流", "AI 应用分支走强"],
        intraday_leader_count=3,
        intraday_leader_latest_time="2099-04-22T14:57:00+08:00",
        intraday_leader_symbols=["300024.SZ", "002031.SZ"],
        intraday_signal_scope_count=2,
        intraday_signal_latest_time="2099-04-22T14:58:00+08:00",
        intraday_validation_state="confirmed",
        previous_late_summary="T-1 晚报维持机器人主线高位扩散",
        same_day_mid_summary="盘中机器人链条继续扩散并保持 validation=confirmed",
        replay_id=f"replay:{uuid.uuid4()}",
        slot_run_id=f"slot-run:{uuid.uuid4()}",
        report_run_id=None,
    )
    return LateMainFSJProducer(reader=FakeLateMainInputReader(sample), store=store)


MAIN_SLOT_GOLDEN_CASES: tuple[SlotGoldenCase, ...] = (
    SlotGoldenCase(
        name="early_candidate_validation",
        slot="early",
        section_key="pre_open_main",
        producer_factory=_build_early_case,
        expected_judgment_action="validate",
        expected_object_type="thesis",
        expected_contract_mode=None,
        required_evidence_roles={
            ("slot_replay", "runtime"),
            ("source_observed", "highfreq"),
            ("source_observed", "business_seed"),
        },
        minimum_counts={"object_cnt": 4, "edge_cnt": 2, "evidence_cnt": 4, "observed_cnt": 3},
    ),
    SlotGoldenCase(
        name="early_llm_fallback_applied",
        slot="early",
        section_key="pre_open_main",
        producer_factory=_build_early_llm_fallback_case,
        expected_judgment_action="validate",
        expected_object_type="thesis",
        expected_contract_mode="candidate_with_open_validation",
        required_evidence_roles={
            ("slot_replay", "runtime"),
            ("source_observed", "highfreq"),
            ("source_observed", "business_seed"),
            ("historical_reference", "archive_v2"),
        },
        minimum_counts={"object_cnt": 5, "edge_cnt": 3, "evidence_cnt": 5, "observed_cnt": 4},
        expected_llm_outcome="fallback_applied",
        expected_llm_applied=True,
        expected_llm_model_alias="gemini31_pro_jmr",
        expected_attempted_model_chain=["grok41_thinking", "gemini31_pro_jmr"],
        required_attempt_failure_classifications={"timeout"},
    ),
    SlotGoldenCase(
        name="early_llm_deterministic_degrade",
        slot="early",
        section_key="pre_open_main",
        producer_factory=_build_early_llm_deterministic_degrade_case,
        expected_judgment_action="validate",
        expected_object_type="thesis",
        expected_contract_mode="candidate_with_open_validation",
        required_evidence_roles={
            ("slot_replay", "runtime"),
            ("source_observed", "highfreq"),
            ("source_observed", "business_seed"),
            ("historical_reference", "archive_v2"),
        },
        minimum_counts={"object_cnt": 5, "edge_cnt": 3, "evidence_cnt": 5, "observed_cnt": 4},
        expected_llm_outcome="deterministic_degrade",
        expected_llm_applied=False,
        expected_llm_model_alias="grok41_thinking",
        expected_operator_tag="llm_provider_failure",
        expected_attempted_model_chain=["grok41_thinking", "gemini31_pro_jmr"],
        required_attempt_failure_classifications={"timeout", "provider_failure"},
    ),
    SlotGoldenCase(
        name="mid_intraday_adjustment",
        slot="mid",
        section_key="midday_main",
        producer_factory=_build_mid_case,
        expected_judgment_action="adjust",
        expected_object_type="thesis",
        expected_contract_mode=None,
        required_evidence_roles={
            ("slot_replay", "runtime"),
            ("source_observed", "highfreq"),
            ("prior_slot_reference", "fsj"),
            ("historical_reference", "archive_v2"),
        },
        minimum_counts={"object_cnt": 6, "edge_cnt": 4, "evidence_cnt": 8, "observed_cnt": 6},
    ),
    SlotGoldenCase(
        name="late_provisional_close_monitor",
        slot="late",
        section_key="post_close_main",
        producer_factory=_build_late_case,
        expected_judgment_action="monitor",
        expected_object_type="watch_item",
        expected_contract_mode="provisional_close_only",
        required_evidence_roles={
            ("slot_replay", "runtime"),
            ("source_observed", "midfreq"),
            ("source_observed", "highfreq"),
            ("prior_slot_reference", "fsj"),
            ("historical_reference", "archive_v2"),
        },
        minimum_counts={"object_cnt": 5, "edge_cnt": 4, "evidence_cnt": 8, "observed_cnt": 4},
    ),
)
