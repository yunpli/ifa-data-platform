from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable

import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.fsj import FSJStore
from ifa_data_platform.fsj.early_main_producer import EarlyMainFSJProducer, EarlyMainProducerInput
from ifa_data_platform.fsj.late_main_producer import LateMainFSJProducer, LateMainProducerInput
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
