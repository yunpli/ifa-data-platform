from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Protocol, Sequence

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.store import FSJStore
from ifa_data_platform.fsj.support_common import (
    SupportBundleBase,
    SupportEvidenceRecord,
    SupportJudgmentPlan,
    SupportSnapshot,
    SupportTextItem,
    edge,
    ensure_support_contract,
    make_fact_object,
    make_judgment_object,
    make_signal_object,
    support_relation_edge,
)

EARLY_MACRO_SUPPORT_PRODUCER = "ifa_data_platform.fsj.macro_support_producer"
EARLY_MACRO_SUPPORT_PRODUCER_VERSION = "phase1-support-macro-early-v1"
LATE_MACRO_SUPPORT_PRODUCER = "ifa_data_platform.fsj.macro_support_producer"
LATE_MACRO_SUPPORT_PRODUCER_VERSION = "phase1-support-macro-late-v1"

MACRO_KEYWORD_SQL = """
(title ilike '%宏观%' or title ilike '%CPI%' or title ilike '%PPI%' or title ilike '%PMI%'
 or title ilike '%利率%' or title ilike '%汇率%' or title ilike '%流动性%' or title ilike '%美元%'
 or title ilike '%社融%' or title ilike '%M2%' or title ilike '%出口%' or title ilike '%进口%')
"""


@dataclass(frozen=True, kw_only=True)
class MacroSupportProducerInput(SupportBundleBase):
    macro_snapshots: list[SupportSnapshot]
    latest_text_items: list[SupportTextItem]
    archive_macro_count: int
    archive_macro_latest_business_date: str | None
    archive_news_count: int = 0
    northbound_net_flow: float | None = None
    prior_main_summary: str | None = None
    previous_support_summary: str | None = None

    @property
    def fresh_macro_snapshot_count(self) -> int:
        return sum(1 for item in self.macro_snapshots if item.freshness_label in {"fresh", "same_slot"})

    @property
    def t_minus_1_snapshot_count(self) -> int:
        return sum(1 for item in self.macro_snapshots if item.freshness_label == "t_minus_1")

    @property
    def stale_snapshot_count(self) -> int:
        return sum(1 for item in self.macro_snapshots if item.freshness_label in {"stale", "unknown"})

    @property
    def has_background_support(self) -> bool:
        return bool(self.macro_snapshots) or self.archive_macro_count > 0

    @property
    def has_fresh_change_signal(self) -> bool:
        return self.fresh_macro_snapshot_count > 0 or bool(self.latest_text_items)


class MacroSupportInputReader(Protocol):
    def read(self, *, business_date: str, slot: str) -> MacroSupportProducerInput: ...


class SqlMacroSupportInputReader:
    def __init__(self) -> None:
        self.engine = make_engine()

    def read(self, *, business_date: str, slot: str) -> MacroSupportProducerInput:
        if slot not in {"early", "late"}:
            raise ValueError(f"unsupported macro support slot: {slot}")
        section_key = "support_macro"
        ensure_support_contract(agent_domain="macro", slot=slot, section_key=section_key)
        business_dt = date.fromisoformat(business_date)
        previous_date = (business_dt - timedelta(days=1)).isoformat()

        with self.engine.begin() as conn:
            snapshot_rows = conn.execute(
                text(
                    """
                    with ranked as (
                        select
                          macro_series,
                          indicator_name,
                          report_date::text as report_date,
                          value,
                          unit,
                          row_number() over (partition by macro_series order by report_date desc, id desc) as rn
                        from ifa2.macro_history
                        where report_date <= cast(:business_date as date)
                    )
                    select macro_series, indicator_name, report_date, value, unit
                    from ranked
                    where rn = 1
                    order by report_date desc, macro_series
                    limit 8
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            news_rows = conn.execute(
                text(
                    f"""
                    select title, datetime::text as published_at, 'news_history' as source_table
                    from ifa2.news_history
                    where datetime::date in (cast(:business_date as date), cast(:previous_date as date))
                      and {MACRO_KEYWORD_SQL}
                    order by datetime desc
                    limit 5
                    """
                ),
                {"business_date": business_date, "previous_date": previous_date},
            ).mappings().all()

            ann_rows = conn.execute(
                text(
                    f"""
                    select title, ann_date::text as published_at, 'announcements_history' as source_table
                    from ifa2.announcements_history
                    where ann_date in (cast(:business_date as date), cast(:previous_date as date))
                      and {MACRO_KEYWORD_SQL}
                    order by ann_date desc, title
                    limit 5
                    """
                ),
                {"business_date": business_date, "previous_date": previous_date},
            ).mappings().all()

            archive_row = conn.execute(
                text(
                    """
                    select count(*) as cnt, max(business_date)::text as latest_business_date
                    from ifa2.ifa_archive_macro_daily
                    where business_date <= cast(:business_date as date)
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            archive_news_row = conn.execute(
                text(
                    """
                    select count(*) as cnt
                    from ifa2.ifa_archive_news_daily
                    where business_date = cast(:previous_date as date)
                    """
                ),
                {"previous_date": previous_date},
            ).mappings().first() or {"cnt": 0}

            prior_main_row = conn.execute(
                text(
                    """
                    select summary
                    from ifa2.ifa_fsj_bundles
                    where market='a_share'
                      and business_date = cast(:business_date as date)
                      and slot = :slot
                      and agent_domain = 'main'
                      and status = 'active'
                    order by updated_at desc, created_at desc
                    limit 1
                    """
                ),
                {"business_date": business_date, "slot": "early" if slot == "early" else "late"},
            ).mappings().first()

            prior_support_row = conn.execute(
                text(
                    """
                    select summary
                    from ifa2.ifa_fsj_bundles
                    where market='a_share'
                      and business_date < cast(:business_date as date)
                      and slot = :slot
                      and agent_domain = 'macro'
                      and section_key = 'support_macro'
                      and status = 'active'
                    order by business_date desc, updated_at desc, created_at desc
                    limit 1
                    """
                ),
                {"business_date": business_date, "slot": slot},
            ).mappings().first()

            flow_row = None
            if slot == "late":
                flow_row = conn.execute(
                    text(
                        """
                        select net_flow_amount
                        from ifa2.northbound_flow_history
                        where trade_date = cast(:business_date as date)
                        order by trade_date desc
                        limit 1
                        """
                    ),
                    {"business_date": business_date},
                ).mappings().first()

        snapshots = [self._snapshot_from_row(business_date=business_date, row=row) for row in snapshot_rows]
        text_items = [
            SupportTextItem(title=row["title"], published_at=row.get("published_at"), source_table=row.get("source_table"))
            for row in [*news_rows, *ann_rows]
        ]
        text_items = text_items[:5]

        return MacroSupportProducerInput(
            business_date=business_date,
            slot=slot,
            agent_domain="macro",
            section_key=section_key,
            section_type="support",
            bundle_topic_key=f"macro_{slot}_support:{business_date}",
            summary_topic="A股宏观 support",
            macro_snapshots=snapshots,
            latest_text_items=text_items,
            archive_macro_count=int(archive_row["cnt"] or 0),
            archive_macro_latest_business_date=archive_row.get("latest_business_date"),
            archive_news_count=int((archive_news_row or {}).get("cnt") or 0),
            northbound_net_flow=(None if flow_row is None else flow_row.get("net_flow_amount")),
            prior_main_summary=None if prior_main_row is None else prior_main_row.get("summary"),
            previous_support_summary=None if prior_support_row is None else prior_support_row.get("summary"),
        )

    def _snapshot_from_row(self, *, business_date: str, row: Any) -> SupportSnapshot:
        report_date = row.get("report_date")
        if report_date == business_date:
            freshness = "fresh"
        elif report_date == (date.fromisoformat(business_date) - timedelta(days=1)).isoformat():
            freshness = "t_minus_1"
        else:
            freshness = "stale"
        value = row.get("value")
        unit = row.get("unit") or ""
        indicator = row.get("indicator_name") or row.get("macro_series")
        return SupportSnapshot(
            object_key=f"macro:{row['macro_series'].lower()}",
            label=str(indicator),
            source_layer="lowfreq",
            source_family="macro_history",
            source_table="ifa2.macro_history",
            source_record_key=f"{row['macro_series']}@{report_date}",
            freshness_label=freshness,
            confidence="high" if freshness in {"fresh", "t_minus_1"} else "medium",
            value_text=f"{indicator} 最新值 {value}{unit}" if value is not None else f"{indicator} 最新快照可用",
            observed_at=report_date,
            attributes={"report_date": report_date, "value": value, "unit": unit},
        )


class MacroSupportAssembler:
    def build_bundle_graph(self, data: MacroSupportProducerInput) -> dict[str, Any]:
        ensure_support_contract(agent_domain=data.agent_domain, slot=data.slot, section_key=data.section_key)
        bundle_id = self._bundle_id(data)
        plan = self._plan(data)

        bundle_payload = {
            "primary_relation": plan.primary_relation,
            "secondary_relations": plan.secondary_relations,
            "implemented_scope": {
                "domain": "macro",
                "slots": [data.slot],
                "scaffold_ready_for": ["commodities", "ai_tech"],
            },
            "degrade": {
                "reason": plan.degrade_reason,
                "has_background_support": data.has_background_support,
                "has_fresh_change_signal": data.has_fresh_change_signal,
                "fresh_macro_snapshot_count": data.fresh_macro_snapshot_count,
                "t_minus_1_snapshot_count": data.t_minus_1_snapshot_count,
                "text_item_count": len(data.latest_text_items),
            },
            "input_context": {
                "archive_macro_count": data.archive_macro_count,
                "archive_macro_latest_business_date": data.archive_macro_latest_business_date,
                "archive_news_count": data.archive_news_count,
                "prior_main_summary": data.prior_main_summary,
                "previous_support_summary": data.previous_support_summary,
                "northbound_net_flow": data.northbound_net_flow,
            },
        }

        bundle = {
            "bundle_id": bundle_id,
            "market": "a_share",
            "business_date": data.business_date,
            "slot": data.slot,
            "agent_domain": data.agent_domain,
            "section_key": data.section_key,
            "section_type": data.section_type,
            "bundle_topic_key": data.bundle_topic_key,
            "producer": EARLY_MACRO_SUPPORT_PRODUCER if data.slot == "early" else LATE_MACRO_SUPPORT_PRODUCER,
            "producer_version": EARLY_MACRO_SUPPORT_PRODUCER_VERSION if data.slot == "early" else LATE_MACRO_SUPPORT_PRODUCER_VERSION,
            "assembly_mode": "rule_assembled",
            "status": "active",
            "slot_run_id": data.slot_run_id,
            "replay_id": data.replay_id,
            "report_run_id": data.report_run_id,
            "summary": plan.summary,
            "payload_json": bundle_payload,
        }

        facts: list[dict[str, Any]] = []
        evidence_links: list[dict[str, Any]] = []
        observed_records: list[dict[str, Any]] = []
        fact_keys: list[str] = []

        if data.macro_snapshots:
            for snapshot in data.macro_snapshots[:3]:
                fact_key = f"fact:{data.slot}:{snapshot.object_key}"
                fact_keys.append(fact_key)
                facts.append(
                    make_fact_object(
                        bundle_id=bundle_id,
                        object_key=fact_key,
                        object_type="macro",
                        statement=f"{snapshot.label}：{snapshot.value_text}（freshness={snapshot.freshness_label}）",
                        confidence=snapshot.confidence,
                        entity_refs=[snapshot.label],
                        metric_refs=[snapshot.object_key],
                        attributes={
                            "source_layer": snapshot.source_layer,
                            "source_family": snapshot.source_family,
                            "freshness_label": snapshot.freshness_label,
                            **(snapshot.attributes or {}),
                        },
                    )
                )
                evidence_links.append(
                    {
                        "bundle_id": bundle_id,
                        "object_key": fact_key,
                        "fsj_kind": "fact",
                        "evidence_role": "source_observed",
                        "ref_system": snapshot.source_layer,
                        "ref_family": snapshot.source_family,
                        "ref_table": snapshot.source_table,
                        "ref_key": snapshot.source_record_key,
                        "ref_locator_json": {"observed_at": snapshot.observed_at, "freshness_label": snapshot.freshness_label},
                    }
                )
                observed_records.append(
                    {
                        "bundle_id": bundle_id,
                        "object_key": fact_key,
                        "fsj_kind": "fact",
                        "source_layer": snapshot.source_layer,
                        "source_family": snapshot.source_family,
                        "source_table": snapshot.source_table,
                        "source_record_key": snapshot.source_record_key,
                        "observed_label": snapshot.label,
                        "observed_payload_json": {"value_text": snapshot.value_text, "freshness_label": snapshot.freshness_label},
                    }
                )
        else:
            fallback_fact_key = f"fact:{data.slot}:macro:background_gap"
            fact_keys.append(fallback_fact_key)
            facts.append(
                make_fact_object(
                    bundle_id=bundle_id,
                    object_key=fallback_fact_key,
                    object_type="macro",
                    statement="当前可直接消费的宏观快照不足，支持判断只能依赖既有 archive/reference 背景。",
                    confidence="low",
                    entity_refs=["macro_background"],
                    metric_refs=[],
                    attributes={"degrade_reason": "missing_macro_snapshot"},
                )
            )

        if data.latest_text_items:
            titles = [item.title for item in data.latest_text_items[:3]]
            text_fact_key = f"fact:{data.slot}:macro:latest_text"
            fact_keys.append(text_fact_key)
            facts.append(
                make_fact_object(
                    bundle_id=bundle_id,
                    object_key=text_fact_key,
                    object_type="macro",
                    statement=f"最近宏观相关文本/事件：{'；'.join(titles)}。",
                    confidence="medium",
                    entity_refs=titles,
                    metric_refs=["macro:policy_expectation"],
                    attributes={"text_item_count": len(data.latest_text_items)},
                )
            )
            for idx, item in enumerate(data.latest_text_items[:3], start=1):
                evidence_links.append(
                    {
                        "bundle_id": bundle_id,
                        "object_key": text_fact_key,
                        "fsj_kind": "fact",
                        "evidence_role": "source_observed",
                        "ref_system": "lowfreq",
                        "ref_family": item.source_table or "macro_text",
                        "ref_table": f"ifa2.{item.source_table}" if item.source_table else None,
                        "ref_key": f"text:{idx}:{item.title}",
                        "ref_locator_json": {"published_at": item.published_at},
                    }
                )
            observed_records.append(
                {
                    "bundle_id": bundle_id,
                    "object_key": text_fact_key,
                    "fsj_kind": "fact",
                    "source_layer": "lowfreq",
                    "source_family": "macro_text",
                    "source_table": "ifa2.news_history",
                    "source_record_key": "macro_text_recent",
                    "observed_label": "recent_macro_text",
                    "observed_payload_json": {"titles": titles},
                }
            )

        archive_fact_key = f"fact:{data.slot}:macro:archive_background"
        fact_keys.append(archive_fact_key)
        facts.append(
            make_fact_object(
                bundle_id=bundle_id,
                object_key=archive_fact_key,
                object_type="macro",
                statement=(
                    f"T-1 macro archive 背景可用，latest archive business_date={data.archive_macro_latest_business_date}，"
                    f"archive_rows={data.archive_macro_count}。"
                    if data.archive_macro_count > 0
                    else "T-1 macro archive 背景不足，不能把历史背景写成当日已验证结论。"
                ),
                confidence="high" if data.archive_macro_count > 0 else "low",
                entity_refs=["macro_archive_background"],
                metric_refs=["archive_v2:macro_daily"],
                attributes={
                    "archive_macro_count": data.archive_macro_count,
                    "archive_macro_latest_business_date": data.archive_macro_latest_business_date,
                },
            )
        )
        evidence_links.append(
            {
                "bundle_id": bundle_id,
                "object_key": archive_fact_key,
                "fsj_kind": "fact",
                "evidence_role": "historical_reference",
                "ref_system": "archive_v2",
                "ref_family": "macro_daily",
                "ref_table": "ifa2.ifa_archive_macro_daily",
                "ref_key": data.archive_macro_latest_business_date,
                "ref_locator_json": {"row_count": data.archive_macro_count},
            }
        )
        if data.replay_id:
            evidence_links.append(
                {
                    "bundle_id": bundle_id,
                    "object_key": None,
                    "fsj_kind": None,
                    "evidence_role": "slot_replay",
                    "ref_system": "runtime",
                    "ref_family": data.slot,
                    "ref_table": None,
                    "ref_key": data.replay_id,
                    "ref_locator_json": {"slot_run_id": data.slot_run_id},
                }
            )

        signal = make_signal_object(
            bundle_id=bundle_id,
            object_key=plan.signal_key,
            object_type=plan.signal_type,
            statement=plan.signal_statement,
            signal_strength=plan.signal_strength,
            horizon=plan.horizon,
            confidence=plan.confidence,
            attributes={
                "primary_relation": plan.primary_relation,
                "secondary_relations": plan.secondary_relations,
                "based_on_fact_ids": fact_keys,
            },
        )
        judgment = make_judgment_object(
            bundle_id=bundle_id,
            object_key=plan.object_key,
            object_type=plan.judgment_type,
            statement=plan.judgment_statement,
            judgment_action=plan.judgment_action,
            direction=plan.direction,
            priority=plan.priority,
            confidence=plan.confidence,
            invalidators=plan.invalidators,
            attributes={
                "primary_relation": plan.primary_relation,
                "secondary_relations": plan.secondary_relations,
                "based_on_signal_ids": [plan.signal_key],
                "degrade_reason": plan.degrade_reason,
            },
        )

        edges = [
            *[
                edge(bundle_id, "fact_to_signal", "fact", fact_key, "signal", plan.signal_key)
                for fact_key in fact_keys
            ],
            edge(bundle_id, "signal_to_judgment", "signal", plan.signal_key, "judgment", plan.object_key),
            support_relation_edge(bundle_id, plan.object_key, f"judgment:{data.slot}:main:reference", relation=plan.primary_relation, strength="primary"),
        ]
        for relation in plan.secondary_relations:
            edges.append(
                support_relation_edge(
                    bundle_id,
                    plan.object_key,
                    f"judgment:{data.slot}:main:reference",
                    relation=relation,
                    strength="secondary",
                )
            )

        return {
            "bundle": bundle,
            "objects": [*facts, signal, judgment],
            "edges": edges,
            "evidence_links": evidence_links,
            "observed_records": observed_records,
            "report_links": [],
        }

    def _bundle_id(self, data: MacroSupportProducerInput) -> str:
        digest = hashlib.sha1(
            f"a_share:{data.business_date}:{data.slot}:macro:{data.section_key}".encode("utf-8")
        ).hexdigest()[:12]
        return f"a_share:{data.business_date}:{data.slot}:macro:{data.section_key}:{digest}"

    def _plan(self, data: MacroSupportProducerInput) -> SupportJudgmentPlan:
        if data.slot == "early":
            return self._plan_early(data)
        return self._plan_late(data)

    def _plan_early(self, data: MacroSupportProducerInput) -> SupportJudgmentPlan:
        if not data.has_background_support:
            return SupportJudgmentPlan(
                primary_relation="adjust",
                secondary_relations=[],
                judgment_type="watch_item",
                judgment_action="observe",
                direction="neutral",
                priority="p1",
                signal_type="risk",
                signal_strength="low",
                horizon="same_day",
                confidence="low",
                object_key="judgment:early:macro:open_bias",
                signal_key="signal:early:macro:risk_appetite",
                summary="开盘前宏观背景不足，只能作为风险提醒，不形成强 support。",
                signal_statement="宏观背景与文本证据不足，开盘前只能提醒可能的宏观误读风险，不能把历史背景写成今日已验证 support。",
                judgment_statement="盘前主 Agent 应把宏观仅作为 caution/observe 输入，等待更多当日背景确认后再决定是否提高权重。",
                invalidators=["缺少可消费 macro snapshot", "缺少近期宏观文本/事件锚点"],
                degrade_reason="missing_background_support",
            )
        if data.has_fresh_change_signal:
            return SupportJudgmentPlan(
                primary_relation="adjust",
                secondary_relations=["support"] if data.archive_macro_count > 0 else [],
                judgment_type="support",
                judgment_action="adjust",
                direction="conditional",
                priority="p0",
                signal_type="confirmation",
                signal_strength="medium",
                horizon="same_day",
                confidence="medium",
                object_key="judgment:early:macro:open_bias",
                signal_key="signal:early:macro:risk_appetite",
                summary="盘前宏观背景有新变化，应先作为主判断的 adjust 输入，而不是直接当作已验证主线。",
                signal_statement="宏观 snapshot/文本显示盘前背景出现可解释变化，适合修正主 Agent 的开盘语气、优先级与风险边界。",
                judgment_statement="盘前将宏观作为 adjust 输入：提示主 Agent 校准风险偏好与表述力度，但不把宏观背景直接写成 A股开盘结构已成立。",
                invalidators=[
                    "盘前宏观文本仅是泛新闻，缺少与A股相关的明确背景锚点",
                    "新变化未被 snapshot 或 archive 背景承接",
                    "开盘后A股结构与盘前宏观设想明显背离",
                ],
            )
        return SupportJudgmentPlan(
            primary_relation="support",
            secondary_relations=[],
            judgment_type="support",
            judgment_action="support",
            direction="neutral",
            priority="p1",
            signal_type="confirmation",
            signal_strength="medium",
            horizon="same_day",
            confidence="medium",
            object_key="judgment:early:macro:open_bias",
            signal_key="signal:early:macro:risk_appetite",
            summary="盘前宏观更多是稳定背景，可为主判断提供支撑边界，但不单独主导开盘结论。",
            signal_statement="宏观背景稳定且 archive/reference 可追溯，适合作为主 Agent 的 support 边界与风险偏好背景。",
            judgment_statement="盘前保留宏观 support 作为背景支撑：强化主 Agent 的风险边界，但不让宏观背景替代开盘后的市场结构验证。",
            invalidators=[
                "盘前出现新的政策/汇率/流动性变化但未被纳入",
                "主判断把背景 support 误写成同日已验证驱动",
            ],
        )

    def _plan_late(self, data: MacroSupportProducerInput) -> SupportJudgmentPlan:
        if not data.has_background_support:
            return SupportJudgmentPlan(
                primary_relation="adjust",
                secondary_relations=[],
                judgment_type="risk",
                judgment_action="observe",
                direction="neutral",
                priority="p1",
                signal_type="risk",
                signal_strength="low",
                horizon="t_plus_1",
                confidence="low",
                object_key="judgment:late:macro:next_day_watch",
                signal_key="signal:late:macro:driver_strength",
                summary="收盘后缺少足够宏观背景，只能把宏观保留为次日观察项。",
                signal_statement="收盘后缺少可追溯宏观背景与文本锚点，不能判断宏观是 driver 还是背景，只能保留 next-day watch。",
                judgment_statement="晚报阶段不要把宏观写成当日驱动归因；仅保留下一个交易日需要继续核对的宏观变量。",
                invalidators=["缺少 macro snapshot", "缺少可追溯晚间背景"],
                degrade_reason="missing_background_support",
            )
        if data.has_fresh_change_signal:
            return SupportJudgmentPlan(
                primary_relation="adjust",
                secondary_relations=[],
                judgment_type="next_step",
                judgment_action="prepare",
                direction="conditional",
                priority="p0",
                signal_type="rotation",
                signal_strength="medium",
                horizon="t_plus_1",
                confidence="medium",
                object_key="judgment:late:macro:next_day_watch",
                signal_key="signal:late:macro:driver_strength",
                summary="晚报宏观更像放大器/修正项，应沉淀为次日优先监控变量。",
                signal_statement="同日宏观背景有新增变化，但证据更适合解释为放大器或修正项，而不是单独重写全天市场结构。",
                judgment_statement="晚报把宏观沉淀为 next-day watch：说明其可能改变次日风险偏好或叙事权重，但不把它夸大成全天唯一 driver。",
                invalidators=[
                    "同日市场结构主要由非宏观因素驱动",
                    "宏观文本变化缺乏持续性，次日未继续跟踪",
                    "把放大器误写成单一主因",
                ],
            )
        return SupportJudgmentPlan(
            primary_relation="support",
            secondary_relations=[],
            judgment_type="support",
            judgment_action="confirm",
            direction="neutral",
            priority="p1",
            signal_type="confirmation",
            signal_strength="medium",
            horizon="t_plus_1",
            confidence="medium",
            object_key="judgment:late:macro:next_day_watch",
            signal_key="signal:late:macro:driver_strength",
            summary="晚报宏观主要作为稳定背景确认，可帮助判断它更接近背景而非全天主驱动。",
            signal_statement="同日没有明显新的宏观变化，现有 macro background 更像稳定 backdrop，可用于确认主判断边界。",
            judgment_statement="晚报将宏观作为背景确认项：帮助界定宏观更多是 backdrop/support，而非重写全天 A股结构归因。",
            invalidators=[
                "收盘后出现关键政策/汇率/流动性变化未被纳入",
                "主报告把稳定背景误写成强驱动",
            ],
        )


class EarlyMacroSupportProducer:
    def __init__(self, reader: MacroSupportInputReader | None = None, store: FSJStore | None = None) -> None:
        self.reader = reader or SqlMacroSupportInputReader()
        self.store = store or FSJStore()
        self.assembler = MacroSupportAssembler()

    def produce(self, *, business_date: str) -> dict[str, Any]:
        data = self.reader.read(business_date=business_date, slot="early")
        return self.assembler.build_bundle_graph(data)

    def produce_and_persist(self, *, business_date: str) -> dict[str, Any]:
        return self.store.upsert_bundle_graph(self.produce(business_date=business_date))


class LateMacroSupportProducer:
    def __init__(self, reader: MacroSupportInputReader | None = None, store: FSJStore | None = None) -> None:
        self.reader = reader or SqlMacroSupportInputReader()
        self.store = store or FSJStore()
        self.assembler = MacroSupportAssembler()

    def produce(self, *, business_date: str) -> dict[str, Any]:
        data = self.reader.read(business_date=business_date, slot="late")
        return self.assembler.build_bundle_graph(data)

    def produce_and_persist(self, *, business_date: str) -> dict[str, Any]:
        return self.store.upsert_bundle_graph(self.produce(business_date=business_date))
