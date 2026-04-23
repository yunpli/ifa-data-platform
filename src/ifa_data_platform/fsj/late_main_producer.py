from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.llm_assist import (
    FSJLateLLMAssistant,
    FSJLateLLMRequest,
    build_fsj_late_evidence_packet,
)
from ifa_data_platform.fsj.store import FSJStore

LATE_MAIN_PRODUCER = "ifa_data_platform.fsj.late_main_producer"
LATE_MAIN_PRODUCER_VERSION = "phase1-main-late-v1"


@dataclass(frozen=True)
class LateEvidenceRecord:
    source_layer: str
    source_family: str
    source_table: str
    source_record_key: str
    observed_label: str
    observed_payload: dict[str, Any]


@dataclass(frozen=True)
class LateMainProducerInput:
    business_date: str
    slot: str
    section_key: str
    section_type: str
    bundle_topic_key: str
    summary_topic: str
    equity_daily_count: int
    equity_daily_latest_trade_date: str | None
    equity_daily_sample_symbols: list[str]
    northbound_flow_count: int
    northbound_latest_trade_date: str | None
    northbound_net_amount: float | None
    limit_up_detail_count: int
    limit_up_detail_latest_trade_date: str | None
    limit_up_detail_sample_symbols: list[str]
    limit_up_down_status_count: int
    limit_up_down_latest_trade_date: str | None
    limit_up_count: int | None
    limit_down_count: int | None
    dragon_tiger_count: int
    dragon_tiger_latest_trade_date: str | None
    dragon_tiger_sample_symbols: list[str]
    sector_performance_count: int
    sector_performance_latest_trade_date: str | None
    sector_performance_top_sector: str | None
    sector_performance_top_pct_chg: float | None
    latest_text_count: int
    latest_text_titles: list[str]
    latest_text_source_times: list[str]
    intraday_event_count: int
    intraday_event_latest_time: str | None
    intraday_event_titles: list[str]
    intraday_leader_count: int
    intraday_leader_latest_time: str | None
    intraday_leader_symbols: list[str]
    intraday_signal_scope_count: int
    intraday_signal_latest_time: str | None
    intraday_validation_state: str | None
    previous_late_summary: str | None
    same_day_mid_summary: str | None
    replay_id: str | None = None
    slot_run_id: str | None = None
    report_run_id: str | None = None

    @property
    def has_same_day_final_structure(self) -> bool:
        return self.equity_daily_count > 0

    @property
    def has_same_day_stable_market_support(self) -> bool:
        return any(
            count > 0
            for count in (
                self.northbound_flow_count,
                self.limit_up_detail_count,
                self.limit_up_down_status_count,
                self.dragon_tiger_count,
                self.sector_performance_count,
            )
        )

    @property
    def has_same_day_low_text(self) -> bool:
        return self.latest_text_count > 0 and any(self.latest_text_source_times)

    @property
    def has_intraday_context(self) -> bool:
        return self.intraday_event_count > 0 or self.intraday_leader_count > 0 or self.intraday_signal_scope_count > 0

    @property
    def full_close_ready(self) -> bool:
        return self.has_same_day_final_structure and self.has_same_day_stable_market_support and self.has_same_day_low_text

    @property
    def provisional_close_only(self) -> bool:
        return self.has_same_day_final_structure and not self.full_close_ready


class LateMainInputReader(Protocol):
    def read(
        self,
        *,
        business_date: str,
        slot: str = "late",
        section_key: str = "post_close_main",
    ) -> LateMainProducerInput: ...


class SqlLateMainInputReader:
    def __init__(self) -> None:
        self.engine = make_engine()

    def read(
        self,
        *,
        business_date: str,
        slot: str = "late",
        section_key: str = "post_close_main",
    ) -> LateMainProducerInput:
        with self.engine.begin() as conn:
            equity_row = conn.execute(
                text(
                    """
                    with ranked as (
                        select ts_code, trade_date,
                               row_number() over (order by ts_code) as rn
                        from ifa2.equity_daily_bar_history
                        where trade_date = cast(:business_date as date)
                    )
                    select
                      (select count(*) from ifa2.equity_daily_bar_history where trade_date = cast(:business_date as date)) as cnt,
                      max(trade_date)::text as latest_trade_date,
                      array_remove(array_agg(case when rn <= 5 then ts_code end), null) as sample_symbols
                    from ranked
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            northbound_row = conn.execute(
                text(
                    """
                    select count(*) as cnt,
                           max(trade_date)::text as latest_trade_date,
                           max(north_money) as north_money
                    from ifa2.northbound_flow_history
                    where trade_date = cast(:business_date as date)
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            limit_detail_row = conn.execute(
                text(
                    """
                    with ranked as (
                        select ts_code, trade_date,
                               row_number() over (order by ts_code) as rn
                        from ifa2.limit_up_detail_history
                        where trade_date = cast(:business_date as date)
                    )
                    select
                      (select count(*) from ifa2.limit_up_detail_history where trade_date = cast(:business_date as date)) as cnt,
                      max(trade_date)::text as latest_trade_date,
                      array_remove(array_agg(case when rn <= 5 then ts_code end), null) as sample_symbols
                    from ranked
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            limit_status_row = conn.execute(
                text(
                    """
                    select count(*) as cnt,
                           max(trade_date)::text as latest_trade_date,
                           max(limit_up_count) as limit_up_count,
                           max(limit_down_count) as limit_down_count
                    from ifa2.limit_up_down_status_history
                    where trade_date = cast(:business_date as date)
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            dragon_row = conn.execute(
                text(
                    """
                    with ranked as (
                        select ts_code, trade_date,
                               row_number() over (order by ts_code) as rn
                        from ifa2.dragon_tiger_list_history
                        where trade_date = cast(:business_date as date)
                    )
                    select
                      (select count(*) from ifa2.dragon_tiger_list_history where trade_date = cast(:business_date as date)) as cnt,
                      max(trade_date)::text as latest_trade_date,
                      array_remove(array_agg(case when rn <= 5 then ts_code end), null) as sample_symbols
                    from ranked
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            sector_row = conn.execute(
                text(
                    """
                    with ranked as (
                        select trade_date, sector_name, pct_chg,
                               row_number() over (order by pct_chg desc nulls last, sector_name) as rn
                        from ifa2.sector_performance_history
                        where trade_date = cast(:business_date as date)
                    )
                    select
                      (select count(*) from ifa2.sector_performance_history where trade_date = cast(:business_date as date)) as cnt,
                      max(trade_date)::text as latest_trade_date,
                      max(case when rn = 1 then sector_name end) as top_sector,
                      max(case when rn = 1 then pct_chg end) as top_pct_chg
                    from ranked
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            text_rows = conn.execute(
                text(
                    """
                    with latest_text as (
                        select title, datetime as published_at from ifa2.news_history
                        where datetime::date = cast(:business_date as date)
                        union all
                        select title, rec_time as published_at from ifa2.announcements_history
                        where ann_date = cast(:business_date as date)
                        union all
                        select title, trade_date::timestamp as published_at from ifa2.research_reports_history
                        where trade_date = cast(:business_date as date)
                        union all
                        select left(coalesce(q, 'investor_qa'), 80) as title, pub_time as published_at from ifa2.investor_qa_history
                        where trade_date = cast(:business_date as date)
                    )
                    select title, published_at
                    from latest_text
                    where published_at is not null
                    order by published_at desc nulls last
                    limit 8
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

            leader_rows = conn.execute(
                text(
                    """
                    select symbol, trade_time
                    from ifa2.highfreq_leader_candidate_working
                    where trade_time::date = cast(:business_date as date)
                    order by trade_time desc, candidate_score desc, symbol
                    limit 8
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            signal_rows = conn.execute(
                text(
                    """
                    select scope_key, trade_time, validation_state
                    from ifa2.highfreq_intraday_signal_state_working
                    where trade_time::date = cast(:business_date as date)
                    order by trade_time desc, scope_key
                    limit 5
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

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

            same_day_mid_row = conn.execute(
                text(
                    """
                    select summary
                    from ifa2.ifa_fsj_bundles
                    where market='a_share'
                      and slot='mid'
                      and agent_domain='main'
                      and status='active'
                      and business_date = cast(:business_date as date)
                    order by updated_at desc, created_at desc
                    limit 1
                    """
                ),
                {"business_date": business_date},
            ).mappings().first()

        latest_signal = signal_rows[0] if signal_rows else None
        return LateMainProducerInput(
            business_date=business_date,
            slot=slot,
            section_key=section_key,
            section_type="thesis",
            bundle_topic_key=f"mainline_close:{business_date}",
            summary_topic="A股收盘主线复盘",
            equity_daily_count=int(equity_row["cnt"] or 0),
            equity_daily_latest_trade_date=equity_row["latest_trade_date"],
            equity_daily_sample_symbols=list(equity_row["sample_symbols"] or []),
            northbound_flow_count=int(northbound_row["cnt"] or 0),
            northbound_latest_trade_date=northbound_row["latest_trade_date"],
            northbound_net_amount=float(northbound_row["north_money"]) if northbound_row.get("north_money") is not None else None,
            limit_up_detail_count=int(limit_detail_row["cnt"] or 0),
            limit_up_detail_latest_trade_date=limit_detail_row["latest_trade_date"],
            limit_up_detail_sample_symbols=list(limit_detail_row["sample_symbols"] or []),
            limit_up_down_status_count=int(limit_status_row["cnt"] or 0),
            limit_up_down_latest_trade_date=limit_status_row["latest_trade_date"],
            limit_up_count=int(limit_status_row["limit_up_count"]) if limit_status_row.get("limit_up_count") is not None else None,
            limit_down_count=int(limit_status_row["limit_down_count"]) if limit_status_row.get("limit_down_count") is not None else None,
            dragon_tiger_count=int(dragon_row["cnt"] or 0),
            dragon_tiger_latest_trade_date=dragon_row["latest_trade_date"],
            dragon_tiger_sample_symbols=list(dragon_row["sample_symbols"] or []),
            sector_performance_count=int(sector_row["cnt"] or 0),
            sector_performance_latest_trade_date=sector_row["latest_trade_date"],
            sector_performance_top_sector=sector_row.get("top_sector"),
            sector_performance_top_pct_chg=float(sector_row["top_pct_chg"]) if sector_row.get("top_pct_chg") is not None else None,
            latest_text_count=len(text_rows),
            latest_text_titles=[row["title"] for row in text_rows if row.get("title")],
            latest_text_source_times=[row["published_at"].isoformat() for row in text_rows if row.get("published_at")],
            intraday_event_count=len(event_rows),
            intraday_event_latest_time=event_rows[0]["event_time"].isoformat() if event_rows else None,
            intraday_event_titles=[row["title"] for row in event_rows if row.get("title")],
            intraday_leader_count=len(leader_rows),
            intraday_leader_latest_time=leader_rows[0]["trade_time"].isoformat() if leader_rows else None,
            intraday_leader_symbols=[row["symbol"] for row in leader_rows if row.get("symbol")],
            intraday_signal_scope_count=len(signal_rows),
            intraday_signal_latest_time=latest_signal["trade_time"].isoformat() if latest_signal else None,
            intraday_validation_state=latest_signal["validation_state"] if latest_signal else None,
            previous_late_summary=previous_late_row["summary"] if previous_late_row else None,
            same_day_mid_summary=same_day_mid_row["summary"] if same_day_mid_row else None,
            replay_id=None,
            slot_run_id=None,
            report_run_id=None,
        )


class LateMainFSJAssembler:
    def __init__(self, *, llm_assistant: FSJLateLLMAssistant | None = None) -> None:
        self.llm_assistant = llm_assistant or FSJLateLLMAssistant()

    def build_bundle_graph(self, data: LateMainProducerInput) -> dict[str, Any]:
        objects: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        evidence_links: list[dict[str, Any]] = []
        observed_records: list[dict[str, Any]] = []

        bundle_id = self._bundle_id(data)
        completeness_label = self._completeness_label(data)
        degrade_reason = self._degrade_reason(data)
        contract_mode = self._contract_mode(data)
        llm_result = None
        llm_audit: dict[str, Any] = {"applied": False, "reason": "late_llm_assist_not_attempted"}
        if data.full_close_ready or data.provisional_close_only:
            llm_result, llm_audit = self.llm_assistant.maybe_synthesize(
                FSJLateLLMRequest(
                    business_date=data.business_date,
                    section_key=data.section_key,
                    contract_mode=contract_mode,
                    completeness_label=completeness_label,
                    degrade_reason=degrade_reason,
                    evidence_packet=build_fsj_late_evidence_packet(
                        data,
                        contract_mode=contract_mode,
                        completeness_label=completeness_label,
                        degrade_reason=degrade_reason,
                    ),
                )
            )

        primary_fact_keys: list[str] = []
        context_fact_keys: list[str] = []

        fact_final_market = self._append_fact(
            objects,
            object_key="fact:late:same_day_final_market",
            statement=self._final_market_statement(data),
            object_type="market",
            confidence="high" if data.has_same_day_final_structure else "low",
            evidence_level="E2" if data.has_same_day_final_structure else "E3",
            metric_refs=["equity_daily_count", "northbound_flow_count", "limit_up_detail_count", "limit_up_down_status_count", "dragon_tiger_count", "sector_performance_count"],
            entity_refs=(data.equity_daily_sample_symbols[:3] + data.limit_up_detail_sample_symbols[:3] + data.dragon_tiger_sample_symbols[:3])[:8],
            attributes_json={
                "source_layer": "mid",
                "freshness_label": "fresh" if data.has_same_day_final_structure else "unknown",
                "completeness_label": completeness_label,
                "is_finalized_equivalent": data.has_same_day_final_structure,
                "degrade_reason": degrade_reason,
                "same_day_final_structure_ready": data.has_same_day_final_structure,
                "same_day_stable_support_ready": data.has_same_day_stable_market_support,
            },
        )
        primary_fact_keys.append(fact_final_market["object_key"])
        observed_records.extend(
            self._build_observed_records(
                fact_final_market,
                [
                    LateEvidenceRecord(
                        source_layer="midfreq",
                        source_family="equity_daily_bar",
                        source_table="ifa2.equity_daily_bar_history",
                        source_record_key=f"{data.business_date}:equity_daily_bar",
                        observed_label="same-day 日线 final 覆盖",
                        observed_payload={"count": data.equity_daily_count, "trade_date": data.equity_daily_latest_trade_date, "sample_symbols": data.equity_daily_sample_symbols[:5]},
                    ),
                    LateEvidenceRecord(
                        source_layer="midfreq",
                        source_family="northbound_flow",
                        source_table="ifa2.northbound_flow_history",
                        source_record_key=f"{data.business_date}:northbound_flow",
                        observed_label="same-day 北向资金盘后稳定表",
                        observed_payload={"count": data.northbound_flow_count, "trade_date": data.northbound_latest_trade_date, "net_amount": data.northbound_net_amount},
                    ),
                    LateEvidenceRecord(
                        source_layer="midfreq",
                        source_family="limit_up_detail",
                        source_table="ifa2.limit_up_detail_history",
                        source_record_key=f"{data.business_date}:limit_up_detail",
                        observed_label="same-day 涨停明细稳定表",
                        observed_payload={"count": data.limit_up_detail_count, "trade_date": data.limit_up_detail_latest_trade_date, "sample_symbols": data.limit_up_detail_sample_symbols[:5]},
                    ),
                    LateEvidenceRecord(
                        source_layer="midfreq",
                        source_family="limit_up_down_status",
                        source_table="ifa2.limit_up_down_status_history",
                        source_record_key=f"{data.business_date}:limit_up_down_status",
                        observed_label="same-day 涨跌停状态稳定表",
                        observed_payload={"count": data.limit_up_down_status_count, "trade_date": data.limit_up_down_latest_trade_date, "up_count": data.limit_up_count, "down_count": data.limit_down_count},
                    ),
                    LateEvidenceRecord(
                        source_layer="midfreq",
                        source_family="dragon_tiger_list",
                        source_table="ifa2.dragon_tiger_list_history",
                        source_record_key=f"{data.business_date}:dragon_tiger_list",
                        observed_label="same-day 龙虎榜稳定表",
                        observed_payload={"count": data.dragon_tiger_count, "trade_date": data.dragon_tiger_latest_trade_date, "sample_symbols": data.dragon_tiger_sample_symbols[:5]},
                    ),
                    LateEvidenceRecord(
                        source_layer="midfreq",
                        source_family="sector_performance",
                        source_table="ifa2.sector_performance_history",
                        source_record_key=f"{data.business_date}:sector_performance",
                        observed_label="same-day 板块表现稳定表",
                        observed_payload={"count": data.sector_performance_count, "trade_date": data.sector_performance_latest_trade_date, "top_sector": data.sector_performance_top_sector, "top_pct_chg": data.sector_performance_top_pct_chg},
                    ),
                ],
            )
        )
        evidence_links.extend(
            self._build_evidence_links(
                fact_final_market,
                [
                    ("source_observed", "midfreq", "equity_daily_bar", "ifa2.equity_daily_bar_history", f"{data.business_date}:equity_daily_bar", {"trade_date": data.equity_daily_latest_trade_date}),
                    ("source_observed", "midfreq", "northbound_flow", "ifa2.northbound_flow_history", f"{data.business_date}:northbound_flow", {"trade_date": data.northbound_latest_trade_date}),
                    ("source_observed", "midfreq", "limit_up_detail", "ifa2.limit_up_detail_history", f"{data.business_date}:limit_up_detail", {"trade_date": data.limit_up_detail_latest_trade_date}),
                    ("source_observed", "midfreq", "limit_up_down_status", "ifa2.limit_up_down_status_history", f"{data.business_date}:limit_up_down_status", {"trade_date": data.limit_up_down_latest_trade_date}),
                    ("source_observed", "midfreq", "dragon_tiger_list", "ifa2.dragon_tiger_list_history", f"{data.business_date}:dragon_tiger_list", {"trade_date": data.dragon_tiger_latest_trade_date}),
                    ("source_observed", "midfreq", "sector_performance", "ifa2.sector_performance_history", f"{data.business_date}:sector_performance", {"trade_date": data.sector_performance_latest_trade_date}),
                ],
            )
        )

        if data.has_same_day_low_text:
            fact_text = self._append_fact(
                objects,
                object_key="fact:late:same_day_text_evidence",
                statement=self._text_statement(data),
                object_type="news",
                confidence="medium",
                evidence_level="E2",
                attributes_json={
                    "source_layer": "low",
                    "freshness_label": "fresh",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": False,
                    "source_time_known": True,
                },
            )
            primary_fact_keys.append(fact_text["object_key"])
            observed_records.extend(
                self._build_observed_records(
                    fact_text,
                    [
                        LateEvidenceRecord(
                            source_layer="lowfreq",
                            source_family="same_day_latest_text",
                            source_table="ifa2.news_history+ifa2.announcements_history+ifa2.research_reports_history+ifa2.investor_qa_history",
                            source_record_key=f"{data.business_date}:same_day_text",
                            observed_label="same-day 文本/事件事实",
                            observed_payload={"count": data.latest_text_count, "titles": data.latest_text_titles[:6], "source_times": data.latest_text_source_times[:6]},
                        )
                    ],
                )
            )
            evidence_links.extend(
                self._build_evidence_links(
                    fact_text,
                    [("source_observed", "lowfreq", "same_day_latest_text", "ifa2.news_history", f"{data.business_date}:same_day_text", {"count": data.latest_text_count})],
                )
            )

        if data.same_day_mid_summary:
            fact_mid_anchor = self._append_fact(
                objects,
                object_key="fact:late:same_day_mid_anchor",
                statement=f"盘中锚点：{data.same_day_mid_summary}",
                object_type="reference",
                confidence="medium",
                evidence_level="E2",
                attributes_json={
                    "source_layer": "replay",
                    "freshness_label": "same_day_prior_slot",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": False,
                },
            )
            context_fact_keys.append(fact_mid_anchor["object_key"])
            evidence_links.extend(
                self._build_evidence_links(
                    fact_mid_anchor,
                    [("prior_slot_reference", "fsj", "bundle_summary", "ifa2.ifa_fsj_bundles", f"mid:{data.business_date}", {"slot": "mid", "business_date": data.business_date})],
                )
            )

        if data.has_intraday_context:
            fact_intraday = self._append_fact(
                objects,
                object_key="fact:late:retained_intraday_context",
                statement=self._intraday_context_statement(data),
                object_type="context",
                confidence="medium",
                evidence_level="E2",
                entity_refs=data.intraday_leader_symbols[:6],
                attributes_json={
                    "source_layer": "high",
                    "freshness_label": "historical-same-day-working",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": False,
                    "background_only": True,
                    "not_for_final_confirmation": True,
                },
            )
            context_fact_keys.append(fact_intraday["object_key"])
            observed_records.extend(
                self._build_observed_records(
                    fact_intraday,
                    [
                        LateEvidenceRecord(
                            source_layer="highfreq",
                            source_family="event_time_stream",
                            source_table="ifa2.highfreq_event_stream_working",
                            source_record_key=f"{data.business_date}:intraday_events",
                            observed_label="same-day retained intraday event context",
                            observed_payload={"count": data.intraday_event_count, "latest_time": data.intraday_event_latest_time, "titles": data.intraday_event_titles[:5]},
                        ),
                        LateEvidenceRecord(
                            source_layer="highfreq",
                            source_family="leader_candidate",
                            source_table="ifa2.highfreq_leader_candidate_working",
                            source_record_key=f"{data.business_date}:intraday_leaders",
                            observed_label="same-day retained intraday leader context",
                            observed_payload={"count": data.intraday_leader_count, "latest_time": data.intraday_leader_latest_time, "symbols": data.intraday_leader_symbols[:5]},
                        ),
                        LateEvidenceRecord(
                            source_layer="highfreq",
                            source_family="intraday_signal_state",
                            source_table="ifa2.highfreq_intraday_signal_state_working",
                            source_record_key=f"{data.business_date}:intraday_signal_state",
                            observed_label="same-day retained intraday signal context",
                            observed_payload={"count": data.intraday_signal_scope_count, "latest_time": data.intraday_signal_latest_time, "validation_state": data.intraday_validation_state},
                        ),
                    ],
                )
            )
            evidence_links.extend(
                self._build_evidence_links(
                    fact_intraday,
                    [
                        ("source_observed", "highfreq", "event_time_stream", "ifa2.highfreq_event_stream_working", f"{data.business_date}:intraday_events", {"latest_time": data.intraday_event_latest_time}),
                        ("source_observed", "highfreq", "leader_candidate", "ifa2.highfreq_leader_candidate_working", f"{data.business_date}:intraday_leaders", {"latest_time": data.intraday_leader_latest_time}),
                        ("source_observed", "highfreq", "intraday_signal_state", "ifa2.highfreq_intraday_signal_state_working", f"{data.business_date}:intraday_signal_state", {"latest_time": data.intraday_signal_latest_time}),
                    ],
                )
            )

        if data.previous_late_summary:
            fact_background = self._append_fact(
                objects,
                object_key="fact:late:t_minus_1_background",
                statement=f"T-1 历史对照：{data.previous_late_summary}",
                object_type="background",
                confidence="medium",
                evidence_level="E1",
                attributes_json={
                    "source_layer": "archive",
                    "freshness_label": "historical-reference",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": True,
                    "background_only": True,
                    "not_for_same_day_confirmation": True,
                },
            )
            context_fact_keys.append(fact_background["object_key"])
            evidence_links.extend(
                self._build_evidence_links(
                    fact_background,
                    [("historical_reference", "archive_v2", "fsj_bundle", "ifa2.ifa_fsj_bundles", f"late:<{data.business_date}", {"summary": data.previous_late_summary})],
                )
            )

        signal_close_state = self._append_signal(
            objects,
            object_key="signal:late:close_package_state",
            statement=llm_result.close_signal_statement if llm_result else self._close_signal_statement(data),
            object_type="confirmation" if data.full_close_ready else "risk",
            signal_strength="medium" if data.full_close_ready else "low",
            confidence="medium" if data.has_same_day_final_structure else "low",
            attributes_json={
                "based_on_fact_keys": [*primary_fact_keys, *context_fact_keys],
                "contract_mode": contract_mode,
                "degrade_reason": degrade_reason,
                "provisional_close_only": data.provisional_close_only,
            },
        )
        for fact_key in [*primary_fact_keys, *context_fact_keys]:
            edges.append(
                {
                    "edge_type": "fact_to_signal",
                    "from_fsj_kind": "fact",
                    "from_object_key": fact_key,
                    "to_fsj_kind": "signal",
                    "to_object_key": signal_close_state["object_key"],
                    "role": "support" if fact_key in primary_fact_keys else "context",
                }
            )

        signal_context = self._append_signal(
            objects,
            object_key="signal:late:intraday_to_close_context",
            statement=llm_result.context_signal_statement if llm_result else self._context_signal_statement(data),
            object_type="confirmation" if data.has_intraday_context else "risk",
            signal_strength="low" if not data.has_intraday_context else "medium",
            confidence="low" if not data.has_intraday_context else "medium",
            attributes_json={
                "based_on_fact_keys": context_fact_keys,
                "context_only": True,
                "not_for_same_day_final_confirmation": True,
            },
        )
        for fact_key in context_fact_keys:
            edges.append(
                {
                    "edge_type": "fact_to_signal",
                    "from_fsj_kind": "fact",
                    "from_object_key": fact_key,
                    "to_fsj_kind": "signal",
                    "to_object_key": signal_context["object_key"],
                    "role": "context",
                }
            )

        judgment = self._append_judgment(
            objects,
            object_key="judgment:late:mainline_close",
            statement=llm_result.judgment_statement if llm_result else self._judgment_statement(data),
            object_type="thesis" if data.full_close_ready else "watch_item",
            judgment_action="confirm" if data.full_close_ready else ("monitor" if data.provisional_close_only else "watch"),
            direction="conditional" if data.full_close_ready else "mixed",
            priority="p0",
            confidence="high" if data.full_close_ready else ("medium" if data.provisional_close_only else "low"),
            invalidators=llm_result.invalidators if llm_result else self._invalidators(data),
            attributes_json={
                "contract_mode": contract_mode,
                "provisional_close_only": data.provisional_close_only,
                "degrade_reason": degrade_reason,
                "same_day_final_structure_ready": data.has_same_day_final_structure,
                "same_day_stable_support_ready": data.has_same_day_stable_market_support,
                "same_day_low_text_ready": data.has_same_day_low_text,
                "deferred": [
                    "support-agent merge not yet implemented",
                    "report artifact linking deferred",
                    "supersede/orchestration policy deferred",
                ],
                "llm_assist_applied": bool(llm_result),
                "llm_reasoning_trace": llm_result.reasoning_trace if llm_result else [],
            },
        )
        for signal_key in [signal_close_state["object_key"], signal_context["object_key"]]:
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

        if data.replay_id:
            evidence_links.append(
                {
                    "object_key": None,
                    "fsj_kind": None,
                    "evidence_role": "slot_replay",
                    "ref_system": "runtime",
                    "ref_family": "slot_replay",
                    "ref_table": "ifa2.slot_replay_evidence",
                    "ref_key": data.replay_id,
                    "ref_locator_json": {"replay_id": data.replay_id},
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
            "producer": LATE_MAIN_PRODUCER,
            "producer_version": LATE_MAIN_PRODUCER_VERSION,
            "assembly_mode": "contract_driven_first_slice",
            "status": "active",
            "supersedes_bundle_id": None,
            "slot_run_id": data.slot_run_id,
            "replay_id": data.replay_id,
            "report_run_id": data.report_run_id,
            "summary": llm_result.summary if llm_result else self._bundle_summary(data),
            "payload_json": self._payload_meta(data, completeness_label, degrade_reason, contract_mode, llm_audit),
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
            "horizon": "same_day_close",
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

    def _build_observed_records(self, obj: dict[str, Any], evidence: Sequence[LateEvidenceRecord]) -> list[dict[str, Any]]:
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

    def _bundle_id(self, data: LateMainProducerInput) -> str:
        seed = f"a_share|{data.business_date}|{data.slot}|main|{data.section_key}|{data.bundle_topic_key}|{LATE_MAIN_PRODUCER_VERSION}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
        return f"fsj:a_share:{data.business_date}:{data.slot}:main:{data.section_key}:{digest}"

    def _completeness_label(self, data: LateMainProducerInput) -> str:
        if data.full_close_ready:
            return "complete"
        if data.provisional_close_only:
            return "partial"
        if data.has_intraday_context or data.has_same_day_low_text:
            return "sparse"
        return "missing"

    def _degrade_reason(self, data: LateMainProducerInput) -> str | None:
        if data.full_close_ready:
            return None
        if data.provisional_close_only:
            missing: list[str] = []
            if not data.has_same_day_stable_market_support:
                missing.append("same_day_stable_market_support_missing")
            if not data.has_same_day_low_text:
                missing.append("same_day_low_text_missing_or_untimed")
            return "+".join(missing) if missing else "provisional_close_only"
        if data.has_intraday_context or data.has_same_day_low_text:
            return "same_day_final_structure_missing"
        return "historical_only"

    def _contract_mode(self, data: LateMainProducerInput) -> str:
        if data.full_close_ready:
            return "full_close_package"
        if data.provisional_close_only:
            return "provisional_close_only"
        if data.has_intraday_context or data.has_same_day_low_text:
            return "post_close_observation_only"
        return "historical_reference_only"

    def _payload_meta(self, data: LateMainProducerInput, completeness_label: str, degrade_reason: str | None, contract_mode: str, llm_audit: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": LATE_MAIN_PRODUCER_VERSION,
            "contract_source": "A_SHARE_EARLY_MID_LATE_DATA_CONSUMPTION_CONTRACT_V1",
            "implemented_scope": {
                "slot": "late",
                "agent_domain": "main",
                "section": data.section_key,
                "included_primary_inputs": [
                    "equity_daily_bar_history",
                    "northbound_flow_history",
                    "limit_up_detail_history",
                    "limit_up_down_status_history",
                    "dragon_tiger_list_history",
                    "sector_performance_history",
                    "same-day lowfreq text with source_time",
                ],
                "included_context_inputs": [
                    "same-day mid FSJ summary",
                    "retained intraday highfreq context",
                    "optional T-1 late FSJ background",
                ],
                "deferred_inputs": [
                    "support-agent merge",
                    "report artifact linking",
                    "automatic supersede orchestration",
                ],
            },
            "degrade": {
                "contract_mode": contract_mode,
                "completeness_label": completeness_label,
                "degrade_reason": degrade_reason,
                "full_close_ready": data.full_close_ready,
                "provisional_close_only": data.provisional_close_only,
                "has_same_day_final_structure": data.has_same_day_final_structure,
                "has_same_day_stable_market_support": data.has_same_day_stable_market_support,
                "has_same_day_low_text": data.has_same_day_low_text,
            },
            "llm_assist": llm_audit,
        }

    def _bundle_summary(self, data: LateMainProducerInput) -> str:
        if data.full_close_ready:
            return f"{data.summary_topic}：已基于 same-day stable/final 市场表与 same-day 文本事实形成收盘结论。"
        if data.provisional_close_only:
            return f"{data.summary_topic}：same-day final 结构已到位，但稳定支撑或文本证据未齐，只输出 provisional close。"
        if data.has_intraday_context or data.has_same_day_low_text:
            return f"{data.summary_topic}：缺少 same-day stable/final 主表，只保留盘后观察与日内演变上下文。"
        return f"{data.summary_topic}：仅保留历史对照，不能形成 same-day 收盘判断。"

    def _final_market_statement(self, data: LateMainProducerInput) -> str:
        return (
            f"same-day 收盘稳定市场层覆盖：日线 {data.equity_daily_count} 条，北向资金 {data.northbound_flow_count} 条，"
            f"涨停明细 {data.limit_up_detail_count} 条，涨跌停状态 {data.limit_up_down_status_count} 条，"
            f"龙虎榜 {data.dragon_tiger_count} 条，板块表现 {data.sector_performance_count} 条。"
        )

    def _text_statement(self, data: LateMainProducerInput) -> str:
        preview = "；".join(data.latest_text_titles[:3])
        return f"same-day 可追溯文本/事件事实 {data.latest_text_count} 条，最近样本包括：{preview or '暂无标题样本'}。"

    def _intraday_context_statement(self, data: LateMainProducerInput) -> str:
        return (
            f"same-day retained intraday context：事件流 {data.intraday_event_count} 条，"
            f"leader {data.intraday_leader_count} 个，signal-state {data.intraday_signal_scope_count} 条；"
            f"仅用于解释日内演变，不作为收盘 final 确认证据。"
        )

    def _close_signal_statement(self, data: LateMainProducerInput) -> str:
        if data.full_close_ready:
            return "same-day stable/final 市场表与同日文本事实已足以形成收盘 close package，可以做晚报主线结论。"
        if data.provisional_close_only:
            return "same-day final 结构已出现，但稳定支撑表或同日带时间文本事实尚未齐备，只能输出 provisional close。"
        if data.has_intraday_context or data.has_same_day_low_text:
            return "当前仅有盘后观察材料或 retained intraday context，不能把它们升级成 same-day close confirmation。"
        return "当前缺少可用 same-day late 证据，只能保留历史对照。"

    def _context_signal_statement(self, data: LateMainProducerInput) -> str:
        if data.has_intraday_context:
            return "日内 retained highfreq 证据可用于解释从盘中到收盘的演化，但不能替代 same-day stable/final close 证据。"
        return "当前缺少可用日内 retained context，收盘解释链条只能依赖 stable/final 与历史背景。"

    def _judgment_statement(self, data: LateMainProducerInput) -> str:
        if data.full_close_ready:
            return "将当前 same-day stable/final 事实作为晚报主线收盘结论依据；intraday retained 仅做演化解释，T-1 仅做历史对照。"
        if data.provisional_close_only:
            return "当前只输出 provisional close：允许描述收盘初步结构，但不得宣称 full confident close package 或完整最终确认。"
        if data.has_intraday_context or data.has_same_day_low_text:
            return "当前只输出盘后观察/待补全项，不形成正式收盘主结论。"
        return "本时段仅保留历史参考，不形成 same-day 收盘判断。"

    def _invalidators(self, data: LateMainProducerInput) -> list[str]:
        invalidators = [
            "same-day stable/final 主表后续确认缺失或发现并未真正到齐",
            "将 retained intraday 或 T-1 背景误当成 same-day close confirmation",
        ]
        if data.provisional_close_only:
            invalidators.append("盘后稳定支撑表或同日带时间文本事实补齐前，不得升级为 full close package")
        if not data.has_same_day_final_structure:
            invalidators.append("在 same-day final 结构主表缺失时，不得输出 final daily structure judgment")
        return invalidators


class LateMainFSJProducer:
    def __init__(
        self,
        *,
        reader: LateMainInputReader | None = None,
        assembler: LateMainFSJAssembler | None = None,
        store: FSJStore | None = None,
    ) -> None:
        self.reader = reader or SqlLateMainInputReader()
        self.assembler = assembler or LateMainFSJAssembler()
        self.store = store or FSJStore()

    def produce(
        self,
        *,
        business_date: str,
        slot: str = "late",
        section_key: str = "post_close_main",
    ) -> dict[str, Any]:
        data = self.reader.read(business_date=business_date, slot=slot, section_key=section_key)
        return self.assembler.build_bundle_graph(data)

    def produce_and_persist(
        self,
        *,
        business_date: str,
        slot: str = "late",
        section_key: str = "post_close_main",
    ) -> dict[str, Any]:
        payload = self.produce(business_date=business_date, slot=slot, section_key=section_key)
        self.store.upsert_bundle_graph(payload)
        bundle_id = payload["bundle"]["bundle_id"]
        graph = self.store.get_bundle_graph(bundle_id)
        if graph is None:
            raise RuntimeError(f"persisted FSJ bundle not found: {bundle_id}")
        return graph
