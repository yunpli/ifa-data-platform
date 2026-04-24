from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Protocol, Sequence

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.llm_assist import (
    FSJMidLLMAssistant,
    FSJMidLLMRequest,
    build_fsj_mid_evidence_packet,
    build_fsj_role_policy,
)
from ifa_data_platform.fsj.store import FSJStore

MID_MAIN_PRODUCER = "ifa_data_platform.fsj.mid_main_producer"
MID_MAIN_PRODUCER_VERSION = "phase1-main-mid-v1"


@dataclass(frozen=True)
class MidEvidenceRecord:
    source_layer: str
    source_family: str
    source_table: str
    source_record_key: str
    observed_label: str
    observed_payload: dict[str, Any]


@dataclass(frozen=True)
class MidMainProducerInput:
    business_date: str
    slot: str
    section_key: str
    section_type: str
    bundle_topic_key: str
    summary_topic: str
    stock_1m_count: int
    stock_1m_latest_time: str | None
    breadth_count: int
    breadth_latest_time: str | None
    breadth_sector_code: str | None
    breadth_spread_ratio: float | None
    heat_count: int
    heat_latest_time: str | None
    heat_sector_code: str | None
    heat_score: float | None
    leader_count: int
    leader_latest_time: str | None
    leader_symbols: list[str]
    leader_confirmation_states: list[str]
    signal_scope_count: int
    signal_latest_time: str | None
    latest_validation_state: str | None
    latest_emotion_stage: str | None
    latest_risk_state: str | None
    event_count: int
    event_latest_time: str | None
    event_titles: list[str]
    latest_text_count: int
    latest_text_titles: list[str]
    early_plan_summary: str | None
    previous_late_summary: str | None
    replay_id: str | None = None
    slot_run_id: str | None = None
    report_run_id: str | None = None

    @property
    def structural_high_fact_count(self) -> int:
        count = 0
        if self.stock_1m_count > 0:
            count += 1
        if self.breadth_count > 0:
            count += 1
        if self.heat_count > 0:
            count += 1
        if self.leader_count > 0:
            count += 1
        if self.signal_scope_count > 0:
            count += 1
        if self.event_count > 0:
            count += 1
        return count

    @property
    def has_sufficient_high_evidence(self) -> bool:
        return self.structural_high_fact_count >= 2

    @property
    def has_any_high_evidence(self) -> bool:
        return self.structural_high_fact_count >= 1


class MidMainInputReader(Protocol):
    def read(
        self,
        *,
        business_date: str,
        slot: str = "mid",
        section_key: str = "midday_main",
    ) -> MidMainProducerInput: ...


class SqlMidMainInputReader:
    def __init__(self) -> None:
        self.engine = make_engine()

    def read(
        self,
        *,
        business_date: str,
        slot: str = "mid",
        section_key: str = "midday_main",
    ) -> MidMainProducerInput:
        with self.engine.begin() as conn:
            stock_row = conn.execute(
                text(
                    """
                    select count(*) as cnt, max(trade_time)::text as latest_time
                    from ifa2.highfreq_stock_1m_working
                    where trade_time::date = cast(:business_date as date)
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            breadth_row = conn.execute(
                text(
                    """
                    with ranked as (
                        select trade_time, sector_code, spread_ratio,
                               row_number() over (order by trade_time desc, spread_ratio desc nulls last, sector_code) as rn
                        from ifa2.highfreq_sector_breadth_working
                        where trade_time::date = cast(:business_date as date)
                    )
                    select
                      (select count(*) from ifa2.highfreq_sector_breadth_working where trade_time::date = cast(:business_date as date)) as cnt,
                      trade_time::text as latest_time,
                      sector_code,
                      spread_ratio
                    from ranked
                    where rn = 1
                    """
                ),
                {"business_date": business_date},
            ).mappings().first() or {"cnt": 0, "latest_time": None, "sector_code": None, "spread_ratio": None}

            heat_row = conn.execute(
                text(
                    """
                    with ranked as (
                        select trade_time, sector_code, heat_score,
                               row_number() over (order by trade_time desc, heat_score desc nulls last, sector_code) as rn
                        from ifa2.highfreq_sector_heat_working
                        where trade_time::date = cast(:business_date as date)
                    )
                    select
                      (select count(*) from ifa2.highfreq_sector_heat_working where trade_time::date = cast(:business_date as date)) as cnt,
                      trade_time::text as latest_time,
                      sector_code,
                      heat_score
                    from ranked
                    where rn = 1
                    """
                ),
                {"business_date": business_date},
            ).mappings().first() or {"cnt": 0, "latest_time": None, "sector_code": None, "heat_score": None}

            leader_rows = conn.execute(
                text(
                    """
                    select symbol, confirmation_state, trade_time
                    from ifa2.highfreq_leader_candidate_working
                    where trade_time::date = cast(:business_date as date)
                    order by trade_time desc, candidate_score desc, symbol
                    limit 10
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            signal_rows = conn.execute(
                text(
                    """
                    select scope_key, trade_time, emotion_stage, validation_state, risk_opportunity_state
                    from ifa2.highfreq_intraday_signal_state_working
                    where trade_time::date = cast(:business_date as date)
                    order by trade_time desc, scope_key
                    limit 5
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            event_rows = conn.execute(
                text(
                    """
                    select title, event_time
                    from ifa2.highfreq_event_stream_working
                    where event_time::date = cast(:business_date as date)
                    order by event_time desc
                    limit 8
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            text_rows = conn.execute(
                text(
                    """
                    with latest_text as (
                        select title, datetime as published_at from ifa2.news_history
                        where datetime::date in (cast(:business_date as date), (cast(:business_date as date) - interval '1 day'))
                        union all
                        select title, rec_time as published_at from ifa2.announcements_history
                        where ann_date in (cast(:business_date as date), (cast(:business_date as date) - interval '1 day'))
                        union all
                        select title, trade_date::timestamp as published_at from ifa2.research_reports_history
                        where trade_date in (cast(:business_date as date), (cast(:business_date as date) - interval '1 day'))
                        union all
                        select left(coalesce(q, 'investor_qa'), 80) as title, pub_time as published_at from ifa2.investor_qa_history
                        where trade_date in (cast(:business_date as date), (cast(:business_date as date) - interval '1 day'))
                    )
                    select title, published_at
                    from latest_text
                    order by published_at desc nulls last
                    limit 8
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            early_bundle_row = conn.execute(
                text(
                    """
                    select summary
                    from ifa2.ifa_fsj_bundles
                    where market='a_share'
                      and business_date = cast(:business_date as date)
                      and slot='early'
                      and agent_domain='main'
                      and status='active'
                    order by updated_at desc, created_at desc
                    limit 1
                    """
                ),
                {"business_date": business_date},
            ).mappings().first()

            previous_late_row = conn.execute(
                text(
                    """
                    select summary
                    from ifa2.ifa_fsj_bundles
                    where market='a_share'
                      and slot='late'
                      and agent_domain='main'
                      and status='active'
                      and business_date < cast(:business_date as date)
                    order by business_date desc, created_at desc
                    limit 1
                    """
                ),
                {"business_date": business_date},
            ).mappings().first()

        leader_latest_time = leader_rows[0]["trade_time"].isoformat() if leader_rows else None
        signal_latest_time = signal_rows[0]["trade_time"].isoformat() if signal_rows else None
        event_latest_time = event_rows[0]["event_time"].isoformat() if event_rows else None
        latest_signal = signal_rows[0] if signal_rows else None
        return MidMainProducerInput(
            business_date=business_date,
            slot=slot,
            section_key=section_key,
            section_type="thesis",
            bundle_topic_key=f"mainline_mid_update:{business_date}",
            summary_topic="A股盘中主线更新",
            stock_1m_count=int(stock_row["cnt"] or 0),
            stock_1m_latest_time=stock_row["latest_time"],
            breadth_count=int(breadth_row["cnt"] or 0),
            breadth_latest_time=breadth_row["latest_time"],
            breadth_sector_code=breadth_row.get("sector_code"),
            breadth_spread_ratio=float(breadth_row["spread_ratio"]) if breadth_row.get("spread_ratio") is not None else None,
            heat_count=int(heat_row["cnt"] or 0),
            heat_latest_time=heat_row["latest_time"],
            heat_sector_code=heat_row.get("sector_code"),
            heat_score=float(heat_row["heat_score"]) if heat_row.get("heat_score") is not None else None,
            leader_count=len(leader_rows),
            leader_latest_time=leader_latest_time,
            leader_symbols=[row["symbol"] for row in leader_rows if row.get("symbol")],
            leader_confirmation_states=[row["confirmation_state"] for row in leader_rows if row.get("confirmation_state")],
            signal_scope_count=len(signal_rows),
            signal_latest_time=signal_latest_time,
            latest_validation_state=latest_signal["validation_state"] if latest_signal else None,
            latest_emotion_stage=latest_signal["emotion_stage"] if latest_signal else None,
            latest_risk_state=latest_signal["risk_opportunity_state"] if latest_signal else None,
            event_count=len(event_rows),
            event_latest_time=event_latest_time,
            event_titles=[row["title"] for row in event_rows if row.get("title")],
            latest_text_count=len(text_rows),
            latest_text_titles=[row["title"] for row in text_rows if row.get("title")],
            early_plan_summary=early_bundle_row["summary"] if early_bundle_row else None,
            previous_late_summary=previous_late_row["summary"] if previous_late_row else None,
            replay_id=None,
            slot_run_id=None,
            report_run_id=None,
        )


class MidMainFSJAssembler:
    def __init__(self, *, llm_assistant: FSJMidLLMAssistant | None = None) -> None:
        self.llm_assistant = llm_assistant or FSJMidLLMAssistant()

    def build_bundle_graph(self, data: MidMainProducerInput) -> dict[str, Any]:
        objects: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        evidence_links: list[dict[str, Any]] = []
        observed_records: list[dict[str, Any]] = []

        freshness = self._freshness_label(data)
        completeness_label = self._completeness_label(data, freshness)
        degrade_reason = self._degrade_reason(data, freshness)
        contract_mode = self._contract_mode(data, freshness)
        bundle_id = self._bundle_id(data)
        llm_result = None
        llm_audit: dict[str, Any] = {"applied": False, "reason": "mid_llm_assist_not_attempted"}
        if data.has_any_high_evidence:
            llm_result, llm_audit = self.llm_assistant.maybe_synthesize(
                FSJMidLLMRequest(
                    business_date=data.business_date,
                    section_key=data.section_key,
                    contract_mode=contract_mode,
                    completeness_label=completeness_label,
                    degrade_reason=degrade_reason,
                    evidence_packet=build_fsj_mid_evidence_packet(
                        data,
                        contract_mode=contract_mode,
                        completeness_label=completeness_label,
                        degrade_reason=degrade_reason,
                        freshness=freshness,
                    ),
                )
            )

        high_fact_keys: list[str] = []

        fact_structure = self._append_fact(
            objects,
            object_key="fact:mid:intraday_structure",
            statement=self._structure_fact_statement(data),
            object_type="market",
            confidence="medium" if data.has_sufficient_high_evidence else "low",
            evidence_level="E2",
            metric_refs=["stock_1m_count", "breadth_count", "heat_count", "signal_scope_count"],
            attributes_json={
                "freshness_label": freshness,
                "completeness_label": "complete" if data.has_sufficient_high_evidence else ("partial" if data.has_any_high_evidence else "missing"),
                "is_finalized_equivalent": False,
                "degrade_reason": degrade_reason,
                "breadth_sector_code": data.breadth_sector_code,
                "heat_sector_code": data.heat_sector_code,
            },
        )
        high_fact_keys.append(fact_structure["object_key"])
        observed_records.extend(
            self._build_observed_records(
                fact_structure,
                [
                    MidEvidenceRecord(
                        source_layer="highfreq",
                        source_family="stock_1m_ohlcv",
                        source_table="ifa2.highfreq_stock_1m_working",
                        source_record_key=f"{data.business_date}:stock_1m",
                        observed_label="盘中 1m working 覆盖",
                        observed_payload={"count": data.stock_1m_count, "latest_time": data.stock_1m_latest_time},
                    ),
                    MidEvidenceRecord(
                        source_layer="highfreq",
                        source_family="sector_breadth",
                        source_table="ifa2.highfreq_sector_breadth_working",
                        source_record_key=f"{data.business_date}:sector_breadth",
                        observed_label="盘中广度状态",
                        observed_payload={"count": data.breadth_count, "latest_time": data.breadth_latest_time, "sector_code": data.breadth_sector_code, "spread_ratio": data.breadth_spread_ratio},
                    ),
                    MidEvidenceRecord(
                        source_layer="highfreq",
                        source_family="sector_heat",
                        source_table="ifa2.highfreq_sector_heat_working",
                        source_record_key=f"{data.business_date}:sector_heat",
                        observed_label="盘中热度状态",
                        observed_payload={"count": data.heat_count, "latest_time": data.heat_latest_time, "sector_code": data.heat_sector_code, "heat_score": data.heat_score},
                    ),
                    MidEvidenceRecord(
                        source_layer="highfreq",
                        source_family="intraday_signal_state",
                        source_table="ifa2.highfreq_intraday_signal_state_working",
                        source_record_key=f"{data.business_date}:signal_state",
                        observed_label="盘中结构派生状态",
                        observed_payload={"count": data.signal_scope_count, "latest_time": data.signal_latest_time, "validation_state": data.latest_validation_state, "emotion_stage": data.latest_emotion_stage, "risk_state": data.latest_risk_state},
                    ),
                ],
            )
        )
        evidence_links.extend(
            self._build_evidence_links(
                fact_structure,
                [
                    ("source_observed", "highfreq", "stock_1m_ohlcv", "ifa2.highfreq_stock_1m_working", f"{data.business_date}:stock_1m", {"latest_time": data.stock_1m_latest_time}),
                    ("source_observed", "highfreq", "sector_breadth", "ifa2.highfreq_sector_breadth_working", f"{data.business_date}:sector_breadth", {"latest_time": data.breadth_latest_time}),
                    ("source_observed", "highfreq", "sector_heat", "ifa2.highfreq_sector_heat_working", f"{data.business_date}:sector_heat", {"latest_time": data.heat_latest_time}),
                    ("source_observed", "highfreq", "intraday_signal_state", "ifa2.highfreq_intraday_signal_state_working", f"{data.business_date}:signal_state", {"latest_time": data.signal_latest_time}),
                ],
            )
        )

        fact_leaders = self._append_fact(
            objects,
            object_key="fact:mid:leader_and_event_state",
            statement=self._leader_event_fact_statement(data),
            object_type="theme",
            confidence="medium" if (data.leader_count > 0 or data.event_count > 0) else "low",
            evidence_level="E2",
            entity_refs=data.leader_symbols[:6],
            attributes_json={
                "freshness_label": freshness if (data.leader_count > 0 or data.event_count > 0) else "stale-hard",
                "completeness_label": "partial" if (data.leader_count > 0 or data.event_count > 0) else "missing",
                "is_finalized_equivalent": False,
                "degrade_reason": degrade_reason if not (data.leader_count > 0 or data.event_count > 0) else None,
                "leader_confirmation_states": data.leader_confirmation_states[:6],
            },
        )
        high_fact_keys.append(fact_leaders["object_key"])
        observed_records.extend(
            self._build_observed_records(
                fact_leaders,
                [
                    MidEvidenceRecord(
                        source_layer="highfreq",
                        source_family="leader_candidate",
                        source_table="ifa2.highfreq_leader_candidate_working",
                        source_record_key=f"{data.business_date}:leaders",
                        observed_label="盘中龙头候选覆盖",
                        observed_payload={"count": data.leader_count, "latest_time": data.leader_latest_time, "symbols": data.leader_symbols[:6], "states": data.leader_confirmation_states[:6]},
                    ),
                    MidEvidenceRecord(
                        source_layer="highfreq",
                        source_family="event_time_stream",
                        source_table="ifa2.highfreq_event_stream_working",
                        source_record_key=f"{data.business_date}:events",
                        observed_label="盘中事件流覆盖",
                        observed_payload={"count": data.event_count, "latest_time": data.event_latest_time, "titles": data.event_titles[:5]},
                    ),
                ],
            )
        )
        evidence_links.extend(
            self._build_evidence_links(
                fact_leaders,
                [
                    ("source_observed", "highfreq", "leader_candidate", "ifa2.highfreq_leader_candidate_working", f"{data.business_date}:leaders", {"latest_time": data.leader_latest_time}),
                    ("source_observed", "highfreq", "event_time_stream", "ifa2.highfreq_event_stream_working", f"{data.business_date}:events", {"latest_time": data.event_latest_time}),
                ],
            )
        )

        background_fact_keys: list[str] = []
        if data.early_plan_summary:
            fact_early_anchor = self._append_fact(
                objects,
                object_key="fact:mid:early_plan_anchor",
                statement=f"盘前预案锚点：{data.early_plan_summary}",
                object_type="reference",
                confidence="medium",
                evidence_level="E2",
                attributes_json={
                    "freshness_label": "same_day_prior_slot",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": False,
                },
            )
            background_fact_keys.append(fact_early_anchor["object_key"])
            evidence_links.extend(
                self._build_evidence_links(
                    fact_early_anchor,
                    [
                        ("prior_slot_reference", "fsj", "bundle_summary", "ifa2.ifa_fsj_bundles", f"early:{data.business_date}", {"slot": "early", "business_date": data.business_date}),
                    ],
                )
            )

        if data.previous_late_summary:
            fact_background = self._append_fact(
                objects,
                object_key="fact:mid:t_minus_1_background",
                statement=f"T-1 背景锚点：{data.previous_late_summary}",
                object_type="background",
                confidence="medium",
                evidence_level="E1",
                attributes_json={
                    "freshness_label": "historical-reference",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": True,
                },
            )
            background_fact_keys.append(fact_background["object_key"])
            evidence_links.extend(
                self._build_evidence_links(
                    fact_background,
                    [
                        ("historical_reference", "archive_v2", "fsj_bundle", "ifa2.ifa_fsj_bundles", f"late:<{data.business_date}", {"summary": data.previous_late_summary}),
                    ],
                )
            )

        if data.latest_text_count > 0:
            fact_text = self._append_fact(
                objects,
                object_key="fact:mid:latest_text_context",
                statement=self._text_context_statement(data),
                object_type="news",
                confidence="low" if not data.has_sufficient_high_evidence else "medium",
                evidence_level="E2",
                attributes_json={
                    "freshness_label": "fresh-reference",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": False,
                    "background_only": True,
                },
            )
            background_fact_keys.append(fact_text["object_key"])
            observed_records.extend(
                self._build_observed_records(
                    fact_text,
                    [
                        MidEvidenceRecord(
                            source_layer="lowfreq",
                            source_family="latest_text",
                            source_table="ifa2.news_history+ifa2.announcements_history+ifa2.research_reports_history+ifa2.investor_qa_history",
                            source_record_key=f"{data.business_date}:latest_text",
                            observed_label="盘中解释性文本上下文",
                            observed_payload={"count": data.latest_text_count, "titles": data.latest_text_titles[:5]},
                        )
                    ],
                )
            )
            evidence_links.extend(
                self._build_evidence_links(
                    fact_text,
                    [("source_observed", "lowfreq", "latest_text", "ifa2.news_history", f"{data.business_date}:latest_text", {"count": data.latest_text_count})],
                )
            )

        signal_validation = self._append_signal(
            objects,
            object_key="signal:mid:plan_validation_state",
            statement=llm_result.validation_signal_statement if llm_result else self._validation_signal_statement(data, freshness),
            object_type=self._validation_signal_type(data, freshness),
            signal_strength=self._signal_strength(data, freshness),
            confidence="medium" if data.has_sufficient_high_evidence and freshness == "fresh" else "low",
            attributes_json={
                "based_on_fact_keys": [*high_fact_keys, *background_fact_keys],
                "freshness_label": freshness,
                "degrade_reason": degrade_reason,
            },
        )
        for fact_key in [*high_fact_keys, *background_fact_keys]:
            edges.append(
                {
                    "edge_type": "fact_to_signal",
                    "from_fsj_kind": "fact",
                    "from_object_key": fact_key,
                    "to_fsj_kind": "signal",
                    "to_object_key": signal_validation["object_key"],
                    "role": "support" if fact_key in high_fact_keys else "context",
                }
            )

        signal_afternoon = self._append_signal(
            objects,
            object_key="signal:mid:afternoon_tracking_state",
            statement=llm_result.afternoon_signal_statement if llm_result else self._afternoon_signal_statement(data, freshness),
            object_type="risk" if degrade_reason else "confirmation",
            signal_strength="low" if degrade_reason else "medium",
            confidence="low" if degrade_reason else "medium",
            attributes_json={
                "based_on_fact_keys": high_fact_keys,
                "requires_followup": True,
                "freshness_label": freshness,
            },
        )
        for fact_key in high_fact_keys:
            edges.append(
                {
                    "edge_type": "fact_to_signal",
                    "from_fsj_kind": "fact",
                    "from_object_key": fact_key,
                    "to_fsj_kind": "signal",
                    "to_object_key": signal_afternoon["object_key"],
                    "role": "support",
                }
            )

        judgment = self._append_judgment(
            objects,
            object_key="judgment:mid:mainline_update",
            statement=llm_result.judgment_statement if llm_result else self._judgment_statement(data, freshness),
            object_type="thesis" if data.has_sufficient_high_evidence and freshness == "fresh" else "watch_item",
            judgment_action="adjust" if data.has_sufficient_high_evidence and freshness == "fresh" else "watch",
            direction=self._judgment_direction(data),
            priority="p0",
            confidence="medium" if data.has_sufficient_high_evidence and freshness == "fresh" else "low",
            invalidators=llm_result.invalidators if llm_result else self._invalidators(data, freshness),
            attributes_json={
                "contract_mode": "intraday_structure" if data.has_sufficient_high_evidence and freshness == "fresh" else "monitoring_only",
                "freshness_label": freshness,
                "degrade_reason": degrade_reason,
                "requires_afternoon_validation": True,
                "llm_assist_applied": bool(llm_result),
                "llm_reasoning_trace": llm_result.reasoning_trace if llm_result else [],
                "deferred": [
                    "support-agent merge not yet implemented",
                    "theme-chain explicit graph deferred",
                    "report artifact linking deferred",
                ],
            },
        )
        for signal_key in [signal_validation["object_key"], signal_afternoon["object_key"]]:
            edges.append(
                {
                    "edge_type": "signal_to_judgment",
                    "from_fsj_kind": "signal",
                    "from_object_key": signal_key,
                    "to_fsj_kind": "judgment",
                    "to_object_key": judgment["object_key"],
                    "role": "support",
                }
            )

        replay_id = data.replay_id or self._default_runtime_id(data, kind="replay")
        slot_run_id = data.slot_run_id or self._default_runtime_id(data, kind="slot_run")

        if replay_id:
            evidence_links.append(
                {
                    "object_key": None,
                    "fsj_kind": None,
                    "evidence_role": "slot_replay",
                    "ref_system": "runtime",
                    "ref_family": "slot_replay",
                    "ref_table": "ifa2.slot_replay_evidence",
                    "ref_key": replay_id,
                    "ref_locator_json": {"replay_id": replay_id},
                }
            )

        bundle = {
            "bundle_id": bundle_id,
            "market": "a_share",
            "business_date": data.business_date,
            "slot": data.slot,
            "agent_domain": "main",
            "section_key": data.section_key,
            "section_type": data.section_type,
            "bundle_topic_key": data.bundle_topic_key,
            "producer": MID_MAIN_PRODUCER,
            "producer_version": MID_MAIN_PRODUCER_VERSION,
            "assembly_mode": "contract_driven_first_slice",
            "status": "active",
            "supersedes_bundle_id": None,
            "slot_run_id": slot_run_id,
            "replay_id": replay_id,
            "report_run_id": data.report_run_id,
            "summary": llm_result.summary if llm_result else self._bundle_summary(data, freshness),
            "payload_json": self._payload_meta(data, freshness, completeness_label, degrade_reason, contract_mode, llm_audit),
        }
        return {
            "bundle": bundle,
            "objects": objects,
            "edges": edges,
            "evidence_links": evidence_links,
            "observed_records": observed_records,
            "report_links": [],
        }

    def _append_fact(self, objects: list[dict[str, Any]], *, object_key: str, statement: str, object_type: str, confidence: str, evidence_level: str, entity_refs: Sequence[str] | None = None, metric_refs: Sequence[str] | None = None, attributes_json: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "object_id": object_key,
            "fsj_kind": "fact",
            "object_key": object_key,
            "statement": statement,
            "object_type": object_type,
            "confidence": confidence,
            "evidence_level": evidence_level,
            "entity_refs": list(entity_refs or []),
            "metric_refs": list(metric_refs or []),
            "attributes_json": attributes_json or {},
        }
        objects.append(record)
        return record

    def _append_signal(self, objects: list[dict[str, Any]], *, object_key: str, statement: str, object_type: str, signal_strength: str, confidence: str, attributes_json: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "object_id": object_key,
            "fsj_kind": "signal",
            "object_key": object_key,
            "statement": statement,
            "object_type": object_type,
            "signal_strength": signal_strength,
            "horizon": "intraday",
            "confidence": confidence,
            "attributes_json": attributes_json or {},
        }
        objects.append(record)
        return record

    def _append_judgment(self, objects: list[dict[str, Any]], *, object_key: str, statement: str, object_type: str, judgment_action: str, direction: str, priority: str, confidence: str, invalidators: Sequence[str], attributes_json: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "object_id": object_key,
            "fsj_kind": "judgment",
            "object_key": object_key,
            "statement": statement,
            "object_type": object_type,
            "judgment_action": judgment_action,
            "direction": direction,
            "priority": priority,
            "confidence": confidence,
            "invalidators": list(invalidators),
            "attributes_json": attributes_json or {},
        }
        objects.append(record)
        return record

    def _build_observed_records(self, obj: dict[str, Any], evidence: Sequence[MidEvidenceRecord]) -> list[dict[str, Any]]:
        return [
            {
                "object_key": obj["object_key"],
                "fsj_kind": obj["fsj_kind"],
                "source_layer": item.source_layer,
                "source_family": item.source_family,
                "source_table": item.source_table,
                "source_record_key": item.source_record_key,
                "observed_label": item.observed_label,
                "observed_payload_json": item.observed_payload,
            }
            for item in evidence
        ]

    def _build_evidence_links(self, obj: dict[str, Any], refs: Sequence[tuple[str, str, str, str, str, dict[str, Any]]]) -> list[dict[str, Any]]:
        return [
            {
                "object_key": obj["object_key"],
                "fsj_kind": obj["fsj_kind"],
                "evidence_role": evidence_role,
                "ref_system": ref_system,
                "ref_family": ref_family,
                "ref_table": ref_table,
                "ref_key": ref_key,
                "ref_locator_json": ref_locator_json,
            }
            for evidence_role, ref_system, ref_family, ref_table, ref_key, ref_locator_json in refs
        ]

    def _bundle_id(self, data: MidMainProducerInput) -> str:
        seed = f"a_share|{data.business_date}|{data.slot}|main|{data.section_key}|{data.bundle_topic_key}|{MID_MAIN_PRODUCER_VERSION}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
        return f"fsj:a_share:{data.business_date}:{data.slot}:main:{data.section_key}:{digest}"

    def _default_runtime_id(self, data: MidMainProducerInput, *, kind: str) -> str:
        seed = f"a_share|{data.business_date}|{data.slot}|main|{data.section_key}|{data.bundle_topic_key}|{kind}|{MID_MAIN_PRODUCER_VERSION}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
        return f"fsj-runtime:{kind}:{data.business_date}:{data.slot}:{digest}"

    def _freshness_label(self, data: MidMainProducerInput) -> str:
        latest_candidates = [
            data.stock_1m_latest_time,
            data.breadth_latest_time,
            data.heat_latest_time,
            data.leader_latest_time,
            data.signal_latest_time,
            data.event_latest_time,
        ]
        parsed = [self._parse_timestamp(value) for value in latest_candidates if value]
        if not parsed:
            return "stale-hard"
        latest = max(parsed)
        target = datetime.combine(datetime.fromisoformat(data.business_date).date(), time(11, 30, 0), tzinfo=latest.tzinfo)
        lag_seconds = max((target - latest).total_seconds(), 0.0)
        if lag_seconds <= 20 * 60:
            return "fresh"
        if lag_seconds <= 90 * 60:
            return "stale-soft"
        return "stale-hard"

    def _degrade_reason(self, data: MidMainProducerInput, freshness: str) -> str | None:
        if not data.has_any_high_evidence:
            return "missing_intraday_structure"
        if not data.has_sufficient_high_evidence:
            return "insufficient_intraday_structure"
        if freshness == "stale-soft":
            return "intraday_high_layer_stale_soft"
        if freshness == "stale-hard":
            return "intraday_high_layer_stale_hard"
        return None

    def _completeness_label(self, data: MidMainProducerInput, freshness: str) -> str:
        if data.has_sufficient_high_evidence and freshness == "fresh":
            return "complete"
        if data.has_any_high_evidence:
            return "partial"
        return "missing"

    def _contract_mode(self, data: MidMainProducerInput, freshness: str) -> str:
        if data.has_sufficient_high_evidence and freshness == "fresh":
            return "intraday_structure"
        return "monitoring_only"

    def _payload_meta(self, data: MidMainProducerInput, freshness: str, completeness_label: str, degrade_reason: str | None, contract_mode: str, llm_audit: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": MID_MAIN_PRODUCER_VERSION,
            "contract_source": "A_SHARE_EARLY_MID_LATE_DATA_CONSUMPTION_CONTRACT_V1",
            "implemented_scope": {
                "slot": "mid",
                "agent_domain": "main",
                "section": data.section_key,
                "included_inputs": [
                    "highfreq_stock_1m_working",
                    "highfreq_sector_breadth_working",
                    "highfreq_sector_heat_working",
                    "highfreq_leader_candidate_working",
                    "highfreq_intraday_signal_state_working",
                    "highfreq_event_stream_working",
                    "same-day early FSJ summary as prior-slot context",
                    "recent lowfreq text as explanatory context",
                    "optional T-1 late FSJ background",
                ],
                "deferred_inputs": [
                    "support-agent merge",
                    "explicit theme-chain graph",
                    "report artifact linking",
                    "automatic supersede orchestration",
                ],
            },
            "contract_mode": contract_mode,
            "llm_assist": llm_audit,
            "llm_role_policy": build_fsj_role_policy(
                slot="mid",
                contract_mode=contract_mode,
                completeness_label=completeness_label,
                degrade_reason=degrade_reason,
            ),
            "degrade": {
                "freshness_label": freshness,
                "has_any_high_evidence": data.has_any_high_evidence,
                "has_sufficient_high_evidence": data.has_sufficient_high_evidence,
                "monitoring_only": degrade_reason is not None,
                "degrade_reason": degrade_reason,
            },
        }

    def _bundle_summary(self, data: MidMainProducerInput, freshness: str) -> str:
        if data.has_sufficient_high_evidence and freshness == "fresh":
            return f"{data.summary_topic}：已基于盘中 working high layer 输出结构更新与午后验证框架。"
        if data.has_any_high_evidence:
            return f"{data.summary_topic}：盘中 high layer 证据不足或不够新鲜，仅保留跟踪/观察级更新。"
        return f"{data.summary_topic}：缺少可用盘中结构证据，仅保留背景与午后观察项。"

    def _structure_fact_statement(self, data: MidMainProducerInput) -> str:
        return (
            f"盘中结构层覆盖：1m 样本 {data.stock_1m_count} 条，广度 {data.breadth_count} 条，热度 {data.heat_count} 条，"
            f"信号状态 {data.signal_scope_count} 条；最新 validation={data.latest_validation_state or 'unknown'}，"
            f"emotion={data.latest_emotion_stage or 'unknown'}。"
        )

    def _leader_event_fact_statement(self, data: MidMainProducerInput) -> str:
        preview = "、".join(data.leader_symbols[:3]) or "暂无龙头样本"
        return (
            f"盘中领涨/事件层覆盖：龙头候选 {data.leader_count} 个，事件流 {data.event_count} 条；"
            f"当前优先观察对象包括：{preview}。"
        )

    def _text_context_statement(self, data: MidMainProducerInput) -> str:
        preview = "；".join(data.latest_text_titles[:3])
        return f"盘中文本/事件解释线索 {data.latest_text_count} 条，最近样本包括：{preview or '暂无标题样本'}。"

    def _validation_signal_type(self, data: MidMainProducerInput, freshness: str) -> str:
        if not data.has_sufficient_high_evidence or freshness != "fresh":
            return "risk"
        if (data.latest_validation_state or "").lower() in {"confirmed", "candidate_confirming"}:
            return "confirmation"
        if (data.latest_validation_state or "").lower() in {"challenged", "risk_watch"}:
            return "divergence"
        return "confirmation"

    def _signal_strength(self, data: MidMainProducerInput, freshness: str) -> str:
        if not data.has_sufficient_high_evidence or freshness == "stale-hard":
            return "low"
        if freshness == "stale-soft":
            return "low"
        if (data.latest_validation_state or "").lower() in {"confirmed", "candidate_confirming"}:
            return "medium"
        return "low"

    def _validation_signal_statement(self, data: MidMainProducerInput, freshness: str) -> str:
        if not data.has_any_high_evidence:
            return "当前缺少盘中结构型 high evidence，无法判断盘前预案是否已被盘面验证。"
        if not data.has_sufficient_high_evidence or freshness == "stale-hard":
            return "当前盘中结构证据不足或已明显断档，只能保留‘预案跟踪中/等待更新’的中性判断。"
        if freshness == "stale-soft":
            return "当前盘中结构证据存在轻微延迟，可做初步验证判断，但必须保留 freshness 风险提示。"
        state = data.latest_validation_state or "unknown"
        return f"盘中 working high layer 已可回答预案验证状态，当前 validation_state={state}，但仍属于盘中结构判断而非 final truth。"

    def _afternoon_signal_statement(self, data: MidMainProducerInput, freshness: str) -> str:
        if not data.has_sufficient_high_evidence or freshness != "fresh":
            return "午后继续验证点：等待盘中 high layer 刷新后再判断是否出现强化、扩散或分歧。"
        return "午后继续验证点：跟踪领涨候选是否扩散到 breadth/heat，并观察 validation_state 是否继续改善或转弱。"

    def _judgment_statement(self, data: MidMainProducerInput, freshness: str) -> str:
        if data.has_sufficient_high_evidence and freshness == "fresh":
            return "将当前盘中结构视为对盘前预案的实时修正输入：可以做 intraday thesis/adjust，但仍必须保留午后继续验证与失效边界。"
        if data.has_any_high_evidence:
            return "当前仅输出 observe/track-only 的盘中更新，不输出‘强化/分歧/转强已确认’这类强结论。"
        return "本时段仅保留背景锚点与午后观察项，不形成正式盘中主结论。"

    def _judgment_direction(self, data: MidMainProducerInput) -> str:
        state = (data.latest_validation_state or "").lower()
        if state in {"confirmed", "candidate_confirming", "opportunity"}:
            return "conditional"
        if state in {"challenged", "risk_watch"}:
            return "mixed"
        return "neutral"

    def _invalidators(self, data: MidMainProducerInput, freshness: str) -> list[str]:
        invalidators = [
            "盘中 structure high layer 未继续刷新或关键表再次断档",
            "leader/breadth/heat 之间无法形成一致强化",
        ]
        if freshness != "fresh":
            invalidators.append("当前 freshness 不足，任何强盘中结论都必须回退为观察项")
        if data.early_plan_summary:
            invalidators.append("盘前预案锚点与盘中 working 证据出现明显背离")
        return invalidators

    def _parse_timestamp(self, value: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)


class MidMainFSJProducer:
    def __init__(
        self,
        *,
        reader: MidMainInputReader | None = None,
        assembler: MidMainFSJAssembler | None = None,
        store: FSJStore | None = None,
    ) -> None:
        self.reader = reader or SqlMidMainInputReader()
        self.assembler = assembler or MidMainFSJAssembler()
        self.store = store or FSJStore()

    def produce(
        self,
        *,
        business_date: str,
        slot: str = "mid",
        section_key: str = "midday_main",
    ) -> dict[str, Any]:
        data = self.reader.read(business_date=business_date, slot=slot, section_key=section_key)
        return self.assembler.build_bundle_graph(data)

    def produce_and_persist(
        self,
        *,
        business_date: str,
        slot: str = "mid",
        section_key: str = "midday_main",
    ) -> dict[str, Any]:
        payload = self.produce(business_date=business_date, slot=slot, section_key=section_key)
        self.store.upsert_bundle_graph(payload)
        bundle_id = payload["bundle"]["bundle_id"]
        graph = self.store.get_bundle_graph(bundle_id)
        if graph is None:
            raise RuntimeError(f"persisted FSJ bundle not found: {bundle_id}")
        return graph
