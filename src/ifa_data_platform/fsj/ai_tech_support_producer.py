from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Protocol

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.store import FSJStore
from ifa_data_platform.fsj.support_common import (
    SupportBundleBase,
    SupportJudgmentPlan,
    SupportSnapshot,
    SupportTextItem,
    edge,
    ensure_support_contract,
    make_fact_object,
    make_judgment_object,
    make_signal_object,
    support_relation_edge,
    coalesce_support_lineage_ids,
)

EARLY_AI_TECH_SUPPORT_PRODUCER = "ifa_data_platform.fsj.ai_tech_support_producer"
EARLY_AI_TECH_SUPPORT_PRODUCER_VERSION = "phase1-support-ai-tech-early-v1"
LATE_AI_TECH_SUPPORT_PRODUCER = "ifa_data_platform.fsj.ai_tech_support_producer"
LATE_AI_TECH_SUPPORT_PRODUCER_VERSION = "phase1-support-ai-tech-late-v1"

AI_TECH_NEWS_KEYWORD_SQL = """
(
    title ilike '%AI%' or title ilike '%算力%' or title ilike '%人工智能%' or title ilike '%机器人%'
    or title ilike '%半导体%' or title ilike '%芯片%' or title ilike '%服务器%' or title ilike '%CPO%'
    or title ilike '%光模块%' or title ilike '%华为昇腾%' or title ilike '%大模型%' or title ilike '%智算%'
)
"""

AI_TECH_ARCHIVE_KEYWORD_SQL = """
(
    payload::text ilike '%人工智能%' or payload::text ilike '%机器人%' or payload::text ilike '%云计算%'
    or payload::text ilike '%算力%' or payload::text ilike '%数据中心%' or payload::text ilike '%半导体%'
    or payload::text ilike '%芯片%' or payload::text ilike '%存储芯片%' or payload::text ilike '%光模块%'
    or payload::text ilike '%服务器%' or payload::text ilike '%华为昇腾%' or payload::text ilike '%先进封装%'
    or payload::text ilike '%AIGC%' or payload::text ilike '%信创%'
)
"""

AI_TECH_SECTOR_HISTORY_KEYWORD_SQL = """
(
    sector_name ilike '%人工智能%' or sector_name ilike '%机器人%' or sector_name ilike '%云计算%'
    or sector_name ilike '%算力%' or sector_name ilike '%数据中心%' or sector_name ilike '%半导体%'
    or sector_name ilike '%芯片%' or sector_name ilike '%存储芯片%' or sector_name ilike '%光模块%'
    or sector_name ilike '%服务器%' or sector_name ilike '%华为昇腾%' or sector_name ilike '%先进封装%'
    or sector_name ilike '%AIGC%' or sector_name ilike '%信创%'
)
"""


@dataclass(frozen=True, kw_only=True)
class AITechSupportProducerInput(SupportBundleBase):
    tech_focus_count: int
    tech_key_focus_count: int
    tech_focus_symbols: list[str]
    ai_tech_sector_snapshots: list[SupportSnapshot]
    latest_text_items: list[SupportTextItem]
    archive_sector_count: int
    archive_sector_latest_business_date: str | None
    current_top_sector: str | None = None
    current_top_sector_pct_chg: float | None = None
    prior_main_summary: str | None = None
    previous_support_summary: str | None = None

    @property
    def fresh_sector_snapshot_count(self) -> int:
        return sum(1 for item in self.ai_tech_sector_snapshots if item.freshness_label in {"fresh", "same_slot"})

    @property
    def background_sector_snapshot_count(self) -> int:
        return sum(1 for item in self.ai_tech_sector_snapshots if item.freshness_label == "t_minus_1")

    @property
    def has_focus_scaffold(self) -> bool:
        return self.tech_focus_count > 0 or self.tech_key_focus_count > 0

    @property
    def has_background_support(self) -> bool:
        return self.has_focus_scaffold or self.archive_sector_count > 0 or bool(self.ai_tech_sector_snapshots)

    @property
    def has_fresh_change_signal(self) -> bool:
        return self.fresh_sector_snapshot_count > 0 or bool(self.latest_text_items)


class AITechSupportInputReader(Protocol):
    def read(self, *, business_date: str, slot: str) -> AITechSupportProducerInput: ...


class SqlAITechSupportInputReader:
    def __init__(self) -> None:
        self.engine = make_engine()

    def read(self, *, business_date: str, slot: str) -> AITechSupportProducerInput:
        if slot not in {"early", "late"}:
            raise ValueError(f"unsupported ai_tech support slot: {slot}")
        section_key = "support_ai_tech"
        ensure_support_contract(agent_domain="ai_tech", slot=slot, section_key=section_key)
        business_dt = date.fromisoformat(business_date)
        previous_date = (business_dt - timedelta(days=1)).isoformat()

        with self.engine.begin() as conn:
            focus_rows = conn.execute(
                text(
                    """
                    select fl.list_type, fi.symbol
                    from ifa2.focus_lists fl
                    join ifa2.focus_list_items fi on fi.list_id = fl.id
                    where fl.owner_type='default' and fl.owner_id='default'
                      and fl.is_active = true
                      and fi.is_active = true
                      and fl.name in ('default_tech_focus', 'default_tech_key_focus')
                      and coalesce(fi.asset_category, 'stock') in ('tech', 'stock')
                      and fi.symbol is not null
                    order by fl.name, fi.priority nulls last, fi.symbol
                    """
                )
            ).mappings().all()

            sector_rows = conn.execute(
                text(
                    f"""
                    select sector_name, trade_date::text as trade_date, pct_chg
                    from ifa2.sector_performance_history
                    where trade_date in (cast(:business_date as date), cast(:previous_date as date))
                      and {AI_TECH_SECTOR_HISTORY_KEYWORD_SQL}
                    order by trade_date desc, pct_chg desc nulls last, sector_name
                    limit 5
                    """
                ),
                {"business_date": business_date, "previous_date": previous_date},
            ).mappings().all()

            news_rows = conn.execute(
                text(
                    f"""
                    select title, datetime::text as published_at, 'news_history' as source_table
                    from ifa2.news_history
                    where datetime::date in (cast(:business_date as date), cast(:previous_date as date))
                      and {AI_TECH_NEWS_KEYWORD_SQL}
                    order by datetime desc
                    limit 6
                    """
                ),
                {"business_date": business_date, "previous_date": previous_date},
            ).mappings().all()

            archive_row = conn.execute(
                text(
                    f"""
                    select count(*) as cnt, max(business_date)::text as latest_business_date
                    from ifa2.ifa_archive_sector_performance_daily
                    where business_date <= cast(:business_date as date)
                      and {AI_TECH_ARCHIVE_KEYWORD_SQL}
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            same_day_sector_row = conn.execute(
                text(
                    f"""
                    select sector_name, pct_chg
                    from ifa2.sector_performance_history
                    where trade_date = cast(:business_date as date)
                      and {AI_TECH_SECTOR_HISTORY_KEYWORD_SQL}
                    order by pct_chg desc nulls last, sector_name
                    limit 1
                    """
                ),
                {"business_date": business_date},
            ).mappings().first()

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
                {"business_date": business_date, "slot": slot},
            ).mappings().first()

            prior_support_row = conn.execute(
                text(
                    """
                    select summary
                    from ifa2.ifa_fsj_bundles
                    where market='a_share'
                      and business_date < cast(:business_date as date)
                      and slot = :slot
                      and agent_domain = 'ai_tech'
                      and section_key = 'support_ai_tech'
                      and status = 'active'
                    order by business_date desc, updated_at desc, created_at desc
                    limit 1
                    """
                ),
                {"business_date": business_date, "slot": slot},
            ).mappings().first()

        tech_focus_symbols = [row["symbol"] for row in focus_rows if row["list_type"] == "focus"]
        tech_key_focus_symbols = [row["symbol"] for row in focus_rows if row["list_type"] == "key_focus"]
        snapshots = [self._snapshot_from_sector_row(business_date=business_date, row=row) for row in sector_rows]
        text_items = [
            SupportTextItem(title=row["title"], published_at=row.get("published_at"), source_table=row.get("source_table"))
            for row in news_rows
        ]

        return AITechSupportProducerInput(
            business_date=business_date,
            slot=slot,
            agent_domain="ai_tech",
            section_key=section_key,
            section_type="support",
            bundle_topic_key=f"ai_tech_{slot}_support:{business_date}",
            summary_topic="A股AI-tech support",
            tech_focus_count=len(tech_focus_symbols),
            tech_key_focus_count=len(tech_key_focus_symbols),
            tech_focus_symbols=sorted(set([*tech_key_focus_symbols, *tech_focus_symbols])),
            ai_tech_sector_snapshots=snapshots,
            latest_text_items=text_items[:5],
            archive_sector_count=int(archive_row["cnt"] or 0),
            archive_sector_latest_business_date=archive_row.get("latest_business_date"),
            current_top_sector=None if same_day_sector_row is None else same_day_sector_row.get("sector_name"),
            current_top_sector_pct_chg=(
                None
                if same_day_sector_row is None or same_day_sector_row.get("pct_chg") is None
                else float(same_day_sector_row["pct_chg"])
            ),
            prior_main_summary=None if prior_main_row is None else prior_main_row.get("summary"),
            previous_support_summary=None if prior_support_row is None else prior_support_row.get("summary"),
        )

    def _snapshot_from_sector_row(self, *, business_date: str, row: Any) -> SupportSnapshot:
        trade_date = row.get("trade_date")
        if trade_date == business_date:
            freshness = "fresh"
        elif trade_date == (date.fromisoformat(business_date) - timedelta(days=1)).isoformat():
            freshness = "t_minus_1"
        else:
            freshness = "stale"
        pct_chg = row.get("pct_chg")
        label = row.get("sector_name") or "AI-tech sector"
        return SupportSnapshot(
            object_key=f"ai_tech:{label}",
            label=label,
            source_layer="midfreq",
            source_family="sector_performance",
            source_table="ifa2.sector_performance_history",
            source_record_key=f"{label}@{trade_date}",
            freshness_label=freshness,
            confidence="high" if freshness in {"fresh", "t_minus_1"} else "medium",
            value_text=(f"{label} 当日涨跌幅 {float(pct_chg):.2f}%" if pct_chg is not None else f"{label} 板块表现可用"),
            observed_at=trade_date,
            attributes={"trade_date": trade_date, "pct_chg": None if pct_chg is None else float(pct_chg)},
        )


class AITechSupportAssembler:
    def build_bundle_graph(self, data: AITechSupportProducerInput) -> dict[str, Any]:
        ensure_support_contract(agent_domain=data.agent_domain, slot=data.slot, section_key=data.section_key)
        bundle_id = self._bundle_id(data)
        plan = self._plan(data)

        slot_run_id, replay_id = coalesce_support_lineage_ids(
            business_date=data.business_date,
            slot=data.slot,
            agent_domain=data.agent_domain,
            slot_run_id=data.slot_run_id,
            replay_id=data.replay_id,
        )

        bundle_payload = {
            "primary_relation": plan.primary_relation,
            "secondary_relations": plan.secondary_relations,
            "implemented_scope": {
                "domain": "ai_tech",
                "slots": [data.slot],
                "scaffold_ready_for": ["macro", "commodities"],
            },
            "degrade": {
                "reason": plan.degrade_reason,
                "has_background_support": data.has_background_support,
                "has_focus_scaffold": data.has_focus_scaffold,
                "has_fresh_change_signal": data.has_fresh_change_signal,
                "fresh_sector_snapshot_count": data.fresh_sector_snapshot_count,
                "background_sector_snapshot_count": data.background_sector_snapshot_count,
                "text_item_count": len(data.latest_text_items),
            },
            "input_context": {
                "tech_focus_count": data.tech_focus_count,
                "tech_key_focus_count": data.tech_key_focus_count,
                "current_top_sector": data.current_top_sector,
                "current_top_sector_pct_chg": data.current_top_sector_pct_chg,
                "archive_sector_count": data.archive_sector_count,
                "archive_sector_latest_business_date": data.archive_sector_latest_business_date,
                "prior_main_summary": data.prior_main_summary,
                "previous_support_summary": data.previous_support_summary,
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
            "producer": EARLY_AI_TECH_SUPPORT_PRODUCER if data.slot == "early" else LATE_AI_TECH_SUPPORT_PRODUCER,
            "producer_version": EARLY_AI_TECH_SUPPORT_PRODUCER_VERSION if data.slot == "early" else LATE_AI_TECH_SUPPORT_PRODUCER_VERSION,
            "assembly_mode": "rule_assembled",
            "status": "active",
            "slot_run_id": slot_run_id,
            "replay_id": replay_id,
            "report_run_id": data.report_run_id,
            "summary": plan.summary,
            "payload_json": bundle_payload,
        }

        facts: list[dict[str, Any]] = []
        evidence_links: list[dict[str, Any]] = []
        observed_records: list[dict[str, Any]] = []
        fact_keys: list[str] = []

        if data.ai_tech_sector_snapshots:
            for snapshot in data.ai_tech_sector_snapshots[:3]:
                fact_key = f"fact:{data.slot}:{snapshot.object_key}"
                fact_keys.append(fact_key)
                facts.append(
                    make_fact_object(
                        bundle_id=bundle_id,
                        object_key=fact_key,
                        object_type="theme",
                        statement=f"{snapshot.label}：{snapshot.value_text}（freshness={snapshot.freshness_label}）。",
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
            fallback_fact_key = f"fact:{data.slot}:ai_tech:background_gap"
            fact_keys.append(fallback_fact_key)
            facts.append(
                make_fact_object(
                    bundle_id=bundle_id,
                    object_key=fallback_fact_key,
                    object_type="theme",
                    statement="当前可追溯 AI-tech 板块快照不足，只能保留为主题观察项，不应直接写成主线结论。",
                    confidence="low",
                    entity_refs=["ai_tech_background"],
                    metric_refs=[],
                    attributes={"degrade_reason": "missing_ai_tech_snapshot"},
                )
            )

        focus_fact_key = f"fact:{data.slot}:ai_tech:focus_scaffold"
        fact_keys.append(focus_fact_key)
        facts.append(
            make_fact_object(
                bundle_id=bundle_id,
                object_key=focus_fact_key,
                object_type="theme",
                statement=(
                    f"AI-tech focus 清单已就绪：key_focus={data.tech_key_focus_count}，focus={data.tech_focus_count}，"
                    f"优先监控 {', '.join(data.tech_focus_symbols[:5]) if data.tech_focus_symbols else '无明确标的'}。"
                ),
                confidence="high" if data.has_focus_scaffold else "low",
                entity_refs=data.tech_focus_symbols[:5],
                metric_refs=["ai_tech:leader_diffusion"],
                attributes={"tech_focus_count": data.tech_focus_count, "tech_key_focus_count": data.tech_key_focus_count},
            )
        )

        if data.latest_text_items:
            titles = [item.title for item in data.latest_text_items[:3]]
            text_fact_key = f"fact:{data.slot}:ai_tech:latest_text"
            fact_keys.append(text_fact_key)
            facts.append(
                make_fact_object(
                    bundle_id=bundle_id,
                    object_key=text_fact_key,
                    object_type="news",
                    statement=f"最近 AI-tech 文本/事件：{'；'.join(titles)}。",
                    confidence="medium",
                    entity_refs=titles,
                    metric_refs=["ai_tech:mainline_status"],
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
                        "ref_family": item.source_table or "ai_tech_text",
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
                    "source_family": "ai_tech_text",
                    "source_table": "ifa2.news_history",
                    "source_record_key": "ai_tech_text_recent",
                    "observed_label": "recent_ai_tech_text",
                    "observed_payload_json": {"titles": titles},
                }
            )

        archive_fact_key = f"fact:{data.slot}:ai_tech:archive_background"
        fact_keys.append(archive_fact_key)
        facts.append(
            make_fact_object(
                bundle_id=bundle_id,
                object_key=archive_fact_key,
                object_type="theme",
                statement=(
                    f"AI-tech 板块 archive 背景可用，latest archive business_date={data.archive_sector_latest_business_date}，archive_rows={data.archive_sector_count}。"
                    if data.archive_sector_count > 0
                    else "AI-tech 板块 archive 背景不足，不能把历史热度直接写成今日主线成立。"
                ),
                confidence="high" if data.archive_sector_count > 0 else "low",
                entity_refs=["ai_tech_archive_background"],
                metric_refs=["archive_v2:sector_performance_daily"],
                attributes={
                    "archive_sector_count": data.archive_sector_count,
                    "archive_sector_latest_business_date": data.archive_sector_latest_business_date,
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
                "ref_family": "sector_performance_daily",
                "ref_table": "ifa2.ifa_archive_sector_performance_daily",
                "ref_key": data.archive_sector_latest_business_date,
                "ref_locator_json": {"row_count": data.archive_sector_count},
            }
        )
        if replay_id:
            evidence_links.append(
                {
                    "bundle_id": bundle_id,
                    "object_key": None,
                    "fsj_kind": None,
                    "evidence_role": "slot_replay",
                    "ref_system": "runtime",
                    "ref_family": data.slot,
                    "ref_table": None,
                    "ref_key": replay_id,
                    "ref_locator_json": {"slot_run_id": slot_run_id},
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
            *[edge(bundle_id, "fact_to_signal", "fact", fact_key, "signal", plan.signal_key) for fact_key in fact_keys],
            edge(bundle_id, "signal_to_judgment", "signal", plan.signal_key, "judgment", plan.object_key),
            support_relation_edge(bundle_id, plan.object_key, f"judgment:{data.slot}:main:reference", relation=plan.primary_relation, strength="primary"),
        ]
        for relation in plan.secondary_relations:
            edges.append(support_relation_edge(bundle_id, plan.object_key, f"judgment:{data.slot}:main:reference", relation=relation, strength="secondary"))

        return {
            "bundle": bundle,
            "objects": [*facts, signal, judgment],
            "edges": edges,
            "evidence_links": evidence_links,
            "observed_records": observed_records,
            "report_links": [],
        }

    def _bundle_id(self, data: AITechSupportProducerInput) -> str:
        digest = hashlib.sha1(f"a_share:{data.business_date}:{data.slot}:ai_tech:{data.section_key}".encode("utf-8")).hexdigest()[:12]
        return f"a_share:{data.business_date}:{data.slot}:ai_tech:{data.section_key}:{digest}"

    def _plan(self, data: AITechSupportProducerInput) -> SupportJudgmentPlan:
        return self._plan_early(data) if data.slot == "early" else self._plan_late(data)

    def _plan_early(self, data: AITechSupportProducerInput) -> SupportJudgmentPlan:
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
                object_key="judgment:early:ai_tech:priority_watch",
                signal_key="signal:early:ai_tech:mainline_candidacy",
                summary="盘前 AI-tech 缺少可追溯主题背景，只能作为观察项，不能直接写成主线候选。",
                signal_statement="AI-tech 板块快照和文本锚点不足，盘前只能保留优先观察，不宜直接提升为主线判断。",
                judgment_statement="盘前主 Agent 对 AI-tech 仅保留 observe/caution，等待开盘后扩散与强度验证。",
                invalidators=["缺少 AI-tech sector snapshot", "缺少可追溯 AI-tech 文本锚点"],
                degrade_reason="missing_background_support",
            )
        if data.has_fresh_change_signal:
            return SupportJudgmentPlan(
                primary_relation="adjust",
                secondary_relations=["support"] if data.has_focus_scaffold else [],
                judgment_type="support",
                judgment_action="adjust",
                direction="conditional",
                priority="p0",
                signal_type="confirmation",
                signal_strength="medium",
                horizon="same_day",
                confidence="medium",
                object_key="judgment:early:ai_tech:priority_watch",
                signal_key="signal:early:ai_tech:mainline_candidacy",
                summary="盘前 AI-tech 有新催化/板块强弱变化，应作为主判断的 adjust 输入。",
                signal_statement="AI-tech 出现新的催化或板块强弱变化，适合提升监控优先级并修正主 Agent 的主线候选排序。",
                judgment_statement="盘前将 AI-tech 作为 adjust 输入：提高主 Agent 对算力/半导体/机器人等子主题的监控优先级，但不把题材预判写成已确认主线。",
                invalidators=[
                    "催化仅停留在新闻标题，缺少板块或标的承接",
                    "盘中扩散失败，热点只停留在单一龙头",
                    "主判断把主题候选误写成全市场已确认主线",
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
            object_key="judgment:early:ai_tech:priority_watch",
            signal_key="signal:early:ai_tech:mainline_candidacy",
            summary="盘前 AI-tech 更像稳定候选池，可支持主 Agent 设定重点盯盘方向。",
            signal_statement="AI-tech 背景与 focus scaffold 稳定，可为主 Agent 提供重点监控子主题与候选龙头清单。",
            judgment_statement="盘前把 AI-tech 作为 support 输入：帮助主 Agent 设定题材盯盘顺序，但不替代开盘后的强度验证。",
            invalidators=["开盘后 AI-tech 板块明显弱于其他主线候选", "主判断把 focus 清单误写成已验证扩散链"],
        )

    def _plan_late(self, data: AITechSupportProducerInput) -> SupportJudgmentPlan:
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
                object_key="judgment:late:ai_tech:next_day_priority",
                signal_key="signal:late:ai_tech:diffusion_quality",
                summary="收盘后 AI-tech 缺少可追溯证据，只能保留为次日观察项。",
                signal_statement="晚报阶段缺少 AI-tech 板块/文本锚点，不能判断其是主线还是噪声，只能留待次日继续验证。",
                judgment_statement="晚报不要把 AI-tech 直接写成全天主线；仅记录为 next-day watch。",
                invalidators=["缺少 AI-tech sector snapshot", "缺少 AI-tech 催化/扩散证据"],
                degrade_reason="missing_background_support",
            )
        if data.has_fresh_change_signal and data.current_top_sector_pct_chg is not None and data.current_top_sector_pct_chg < 0:
            return SupportJudgmentPlan(
                primary_relation="counter",
                secondary_relations=["adjust"] if data.has_focus_scaffold else [],
                judgment_type="risk",
                judgment_action="adjust",
                direction="negative",
                priority="p0",
                signal_type="risk",
                signal_strength="medium",
                horizon="t_plus_1",
                confidence="medium",
                object_key="judgment:late:ai_tech:next_day_priority",
                signal_key="signal:late:ai_tech:diffusion_quality",
                summary="晚报 AI-tech 催化存在但板块承接偏弱，更适合作为次日降权/防伪强信号。",
                signal_statement="AI-tech 有事件催化，但板块承接与扩散不足，需防止把局部强势误判为可持续主线。",
                judgment_statement="晚报将 AI-tech 作为 counter/adjust 输入：提示主 Agent 下调次日优先级，重点防范只剩个股表演而无板块扩散。",
                invalidators=["次日盘前出现新的强催化并带来板块级修复", "晚报错误地把单一子主题疲弱外推到整个科技链"],
            )
        if data.has_fresh_change_signal:
            return SupportJudgmentPlan(
                primary_relation="support",
                secondary_relations=["adjust"] if data.current_top_sector_pct_chg and data.current_top_sector_pct_chg > 0 else [],
                judgment_type="next_step",
                judgment_action="prepare",
                direction="positive",
                priority="p0",
                signal_type="rotation",
                signal_strength="medium",
                horizon="t_plus_1",
                confidence="medium",
                object_key="judgment:late:ai_tech:next_day_priority",
                signal_key="signal:late:ai_tech:diffusion_quality",
                summary="晚报 AI-tech 形成可追溯催化与板块承接，应沉淀为次日优先监控链条。",
                signal_statement="AI-tech 同日存在催化与板块表现承接，适合判断哪些子主题应延续为次日重点观察。",
                judgment_statement="晚报把 AI-tech 沉淀为 next-day priority：保留强子主题与扩散链条，供主 Agent 次日开盘前排序使用。",
                invalidators=["板块上涨仅由单一龙头贡献，未形成扩散", "把短促消息脉冲误写成可持续主线"],
            )
        return SupportJudgmentPlan(
            primary_relation="adjust",
            secondary_relations=[],
            judgment_type="support",
            judgment_action="confirm",
            direction="neutral",
            priority="p1",
            signal_type="confirmation",
            signal_strength="low",
            horizon="t_plus_1",
            confidence="medium",
            object_key="judgment:late:ai_tech:next_day_priority",
            signal_key="signal:late:ai_tech:diffusion_quality",
            summary="晚报 AI-tech 更像稳定背景，不足以单独抬升次日主线优先级。",
            signal_statement="同日 AI-tech 没有新的强催化或扩散证据，更多是稳定背景或支线候选。",
            judgment_statement="晚报将 AI-tech 作为 adjust/confirm 输入：保留跟踪，但不把它写成必须延续的主线。",
            invalidators=["收盘后出现新的重磅产业催化未被纳入", "主报告把稳定背景误写成次日必然主线"],
        )


class EarlyAITechSupportProducer:
    def __init__(self, reader: AITechSupportInputReader | None = None, store: FSJStore | None = None) -> None:
        self.reader = reader or SqlAITechSupportInputReader()
        self.store = store or FSJStore()
        self.assembler = AITechSupportAssembler()

    def produce(self, *, business_date: str) -> dict[str, Any]:
        data = self.reader.read(business_date=business_date, slot="early")
        return self.assembler.build_bundle_graph(data)

    def produce_and_persist(self, *, business_date: str) -> dict[str, Any]:
        return self.store.upsert_bundle_graph(self.produce(business_date=business_date))


class LateAITechSupportProducer:
    def __init__(self, reader: AITechSupportInputReader | None = None, store: FSJStore | None = None) -> None:
        self.reader = reader or SqlAITechSupportInputReader()
        self.store = store or FSJStore()
        self.assembler = AITechSupportAssembler()

    def produce(self, *, business_date: str) -> dict[str, Any]:
        data = self.reader.read(business_date=business_date, slot="late")
        return self.assembler.build_bundle_graph(data)

    def produce_and_persist(self, *, business_date: str) -> dict[str, Any]:
        return self.store.upsert_bundle_graph(self.produce(business_date=business_date))
