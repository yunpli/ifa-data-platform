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

EARLY_COMMODITIES_SUPPORT_PRODUCER = "ifa_data_platform.fsj.commodities_support_producer"
EARLY_COMMODITIES_SUPPORT_PRODUCER_VERSION = "phase1-support-commodities-early-v1"
LATE_COMMODITIES_SUPPORT_PRODUCER = "ifa_data_platform.fsj.commodities_support_producer"
LATE_COMMODITIES_SUPPORT_PRODUCER_VERSION = "phase1-support-commodities-late-v1"

COMMODITY_NEWS_KEYWORD_SQL = """
(
    title ilike '%黄金%' or title ilike '%白银%' or title ilike '%铜%' or title ilike '%铝%'
    or title ilike '%原油%' or title ilike '%黑色%' or title ilike '%钢铁%' or title ilike '%焦煤%'
    or title ilike '%焦炭%' or title ilike '%有色%' or title ilike '%化工%' or title ilike '%煤炭%'
)
"""


@dataclass(frozen=True, kw_only=True)
class CommoditiesSupportProducerInput(SupportBundleBase):
    commodity_snapshots: list[SupportSnapshot]
    latest_text_items: list[SupportTextItem]
    futures_daily_count: int
    futures_latest_trade_date: str | None
    intraday_snapshot_latest_time: str | None
    prior_main_summary: str | None = None
    previous_support_summary: str | None = None

    @property
    def fresh_snapshot_count(self) -> int:
        return sum(1 for item in self.commodity_snapshots if item.freshness_label in {"fresh", "same_slot"})

    @property
    def background_snapshot_count(self) -> int:
        return sum(1 for item in self.commodity_snapshots if item.freshness_label == "t_minus_1")

    @property
    def has_background_support(self) -> bool:
        return self.futures_daily_count > 0 or bool(self.commodity_snapshots)

    @property
    def has_fresh_change_signal(self) -> bool:
        return self.fresh_snapshot_count > 0 or bool(self.latest_text_items)


class CommoditiesSupportInputReader(Protocol):
    def read(self, *, business_date: str, slot: str) -> CommoditiesSupportProducerInput: ...


class SqlCommoditiesSupportInputReader:
    def __init__(self) -> None:
        self.engine = make_engine()

    def read(self, *, business_date: str, slot: str) -> CommoditiesSupportProducerInput:
        if slot not in {"early", "late"}:
            raise ValueError(f"unsupported commodities support slot: {slot}")
        section_key = "support_commodities"
        ensure_support_contract(agent_domain="commodities", slot=slot, section_key=section_key)
        business_dt = date.fromisoformat(business_date)
        previous_date = (business_dt - timedelta(days=1)).isoformat()

        with self.engine.begin() as conn:
            commodity_rows = conn.execute(
                text(
                    """
                    with latest_commodity as (
                        select ts_code, trade_time, close, vol, oi,
                               row_number() over (partition by ts_code order by trade_time desc) as rn
                        from ifa2.commodity_15min_history
                    ),
                    latest_precious as (
                        select ts_code, trade_time, close, vol, oi,
                               row_number() over (partition by ts_code order by trade_time desc) as rn
                        from ifa2.precious_metal_15min_history
                    ),
                    unioned as (
                        select 'commodity' as family, ts_code, trade_time, close, vol, oi from latest_commodity where rn = 1
                        union all
                        select 'precious_metal' as family, ts_code, trade_time, close, vol, oi from latest_precious where rn = 1
                    )
                    select family, ts_code, trade_time::text as trade_time, close, vol, oi
                    from unioned
                    order by coalesce(vol, 0) desc, ts_code
                    limit 6
                    """
                )
            ).mappings().all()

            futures_row = conn.execute(
                text(
                    """
                    select count(*) as cnt, max(trade_date)::text as latest_trade_date
                    from ifa2.futures_history
                    where trade_date <= cast(:business_date as date)
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            intraday_row = conn.execute(
                text(
                    """
                    select max(trade_time)::text as latest_time
                    from ifa2.highfreq_futures_minute_working
                    where trade_time::date = cast(:business_date as date)
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            news_rows = conn.execute(
                text(
                    f"""
                    select title, datetime::text as published_at, 'news_history' as source_table
                    from ifa2.news_history
                    where datetime::date in (cast(:business_date as date), cast(:previous_date as date))
                      and {COMMODITY_NEWS_KEYWORD_SQL}
                    order by datetime desc
                    limit 6
                    """
                ),
                {"business_date": business_date, "previous_date": previous_date},
            ).mappings().all()

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
                      and agent_domain = 'commodities'
                      and section_key = 'support_commodities'
                      and status = 'active'
                    order by business_date desc, updated_at desc, created_at desc
                    limit 1
                    """
                ),
                {"business_date": business_date, "slot": slot},
            ).mappings().first()

        snapshots = [self._snapshot_from_row(business_date=business_date, row=row) for row in commodity_rows]
        text_items = [SupportTextItem(title=row["title"], published_at=row.get("published_at"), source_table=row.get("source_table")) for row in news_rows]
        return CommoditiesSupportProducerInput(
            business_date=business_date,
            slot=slot,
            agent_domain="commodities",
            section_key=section_key,
            section_type="support",
            bundle_topic_key=f"commodities_{slot}_support:{business_date}",
            summary_topic="A股 commodities support",
            commodity_snapshots=snapshots,
            latest_text_items=text_items[:5],
            futures_daily_count=int(futures_row["cnt"] or 0),
            futures_latest_trade_date=futures_row.get("latest_trade_date"),
            intraday_snapshot_latest_time=intraday_row.get("latest_time"),
            prior_main_summary=None if prior_main_row is None else prior_main_row.get("summary"),
            previous_support_summary=None if prior_support_row is None else prior_support_row.get("summary"),
        )

    def _snapshot_from_row(self, *, business_date: str, row: Any) -> SupportSnapshot:
        trade_time = row.get("trade_time")
        trade_date = trade_time[:10] if trade_time else None
        previous_date = (date.fromisoformat(business_date) - timedelta(days=1)).isoformat()
        if trade_date == business_date:
            freshness = "fresh"
        elif trade_date == previous_date:
            freshness = "t_minus_1"
        else:
            freshness = "stale"
        family = row.get("family") or "commodity"
        ts_code = row.get("ts_code") or "unknown"
        label = ts_code
        return SupportSnapshot(
            object_key=f"commodity:{family}:{ts_code}",
            label=label,
            source_layer="midfreq",
            source_family=f"{family}_15min_history",
            source_table=f"ifa2.{family if family != 'precious_metal' else 'precious_metal'}_15min_history",
            source_record_key=f"{ts_code}@{trade_time}",
            freshness_label=freshness,
            confidence="high" if freshness == "fresh" else "medium",
            value_text=f"{ts_code} 最新价 {row.get('close')} vol={row.get('vol')} oi={row.get('oi')}",
            observed_at=trade_time,
            attributes={
                "trade_time": trade_time,
                "close": None if row.get("close") is None else float(row.get("close")),
                "vol": None if row.get("vol") is None else float(row.get("vol")),
                "oi": None if row.get("oi") is None else float(row.get("oi")),
                "family": family,
            },
        )


class CommoditiesSupportAssembler:
    def build_bundle_graph(self, data: CommoditiesSupportProducerInput) -> dict[str, Any]:
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

        bundle = {
            "bundle_id": bundle_id,
            "market": "a_share",
            "business_date": data.business_date,
            "slot": data.slot,
            "agent_domain": data.agent_domain,
            "section_key": data.section_key,
            "section_type": data.section_type,
            "bundle_topic_key": data.bundle_topic_key,
            "producer": EARLY_COMMODITIES_SUPPORT_PRODUCER if data.slot == "early" else LATE_COMMODITIES_SUPPORT_PRODUCER,
            "producer_version": EARLY_COMMODITIES_SUPPORT_PRODUCER_VERSION if data.slot == "early" else LATE_COMMODITIES_SUPPORT_PRODUCER_VERSION,
            "assembly_mode": "rule_assembled",
            "status": "active",
            "slot_run_id": slot_run_id,
            "replay_id": replay_id,
            "report_run_id": data.report_run_id,
            "summary": plan.summary,
            "payload_json": {
                "primary_relation": plan.primary_relation,
                "secondary_relations": plan.secondary_relations,
                "implemented_scope": {"domain": "commodities", "slots": [data.slot], "scaffold_ready_for": ["macro", "ai_tech"]},
                "degrade": {
                    "reason": plan.degrade_reason,
                    "has_background_support": data.has_background_support,
                    "has_fresh_change_signal": data.has_fresh_change_signal,
                    "fresh_snapshot_count": data.fresh_snapshot_count,
                    "background_snapshot_count": data.background_snapshot_count,
                    "text_item_count": len(data.latest_text_items),
                    "archive_support": "not_available_for_phase1",
                },
                "input_context": {
                    "futures_daily_count": data.futures_daily_count,
                    "futures_latest_trade_date": data.futures_latest_trade_date,
                    "intraday_snapshot_latest_time": data.intraday_snapshot_latest_time,
                    "prior_main_summary": data.prior_main_summary,
                    "previous_support_summary": data.previous_support_summary,
                },
            },
        }

        facts=[]; evidence_links=[]; observed_records=[]; fact_keys=[]
        if data.commodity_snapshots:
            for snapshot in data.commodity_snapshots[:3]:
                fact_key = f"fact:{data.slot}:{snapshot.object_key}"
                fact_keys.append(fact_key)
                facts.append(make_fact_object(bundle_id=bundle_id, object_key=fact_key, object_type="commodity", statement=f"{snapshot.label}：{snapshot.value_text}（freshness={snapshot.freshness_label}）。", confidence=snapshot.confidence, entity_refs=[snapshot.label], metric_refs=[snapshot.object_key], attributes={"source_layer": snapshot.source_layer, "source_family": snapshot.source_family, "freshness_label": snapshot.freshness_label, **(snapshot.attributes or {})}))
                evidence_links.append({"bundle_id": bundle_id, "object_key": fact_key, "fsj_kind": "fact", "evidence_role": "source_observed", "ref_system": snapshot.source_layer, "ref_family": snapshot.source_family, "ref_table": snapshot.source_table, "ref_key": snapshot.source_record_key, "ref_locator_json": {"observed_at": snapshot.observed_at, "freshness_label": snapshot.freshness_label}})
                observed_records.append({"bundle_id": bundle_id, "object_key": fact_key, "fsj_kind": "fact", "source_layer": snapshot.source_layer, "source_family": snapshot.source_family, "source_table": snapshot.source_table, "source_record_key": snapshot.source_record_key, "observed_label": snapshot.label, "observed_payload_json": {"value_text": snapshot.value_text, "freshness_label": snapshot.freshness_label}})
        else:
            fact_key = f"fact:{data.slot}:commodities:background_gap"
            fact_keys.append(fact_key)
            facts.append(make_fact_object(bundle_id=bundle_id, object_key=fact_key, object_type="commodity", statement="当前可消费的商品快照不足，只能保留链条观察，不直接写成A股映射结论。", confidence="low", entity_refs=["commodity_background"], metric_refs=[], attributes={"degrade_reason": "missing_background_support"}))

        daily_fact_key = f"fact:{data.slot}:commodities:futures_background"
        fact_keys.append(daily_fact_key)
        facts.append(make_fact_object(bundle_id=bundle_id, object_key=daily_fact_key, object_type="commodity", statement=(f"期货日线背景可用，latest trade_date={data.futures_latest_trade_date}，rows={data.futures_daily_count}。" if data.futures_daily_count > 0 else "期货日线背景不足，不能把商品链历史波动直接当作今日映射结论。"), confidence="high" if data.futures_daily_count > 0 else "low", entity_refs=["futures_background"], metric_refs=["futures_history"], attributes={"futures_daily_count": data.futures_daily_count, "futures_latest_trade_date": data.futures_latest_trade_date}))
        evidence_links.append({"bundle_id": bundle_id, "object_key": daily_fact_key, "fsj_kind": "fact", "evidence_role": "historical_reference", "ref_system": "midfreq", "ref_family": "futures_history", "ref_table": "ifa2.futures_history", "ref_key": data.futures_latest_trade_date, "ref_locator_json": {"row_count": data.futures_daily_count}})

        if data.latest_text_items:
            titles = [item.title for item in data.latest_text_items[:3]]
            text_fact_key = f"fact:{data.slot}:commodities:latest_text"
            fact_keys.append(text_fact_key)
            facts.append(make_fact_object(bundle_id=bundle_id, object_key=text_fact_key, object_type="news", statement=f"最近商品/资源文本：{'；'.join(titles)}。", confidence="medium", entity_refs=titles, metric_refs=["commodity:industrial_metals"], attributes={"text_item_count": len(data.latest_text_items)}))
            for idx, item in enumerate(data.latest_text_items[:3], start=1):
                evidence_links.append({"bundle_id": bundle_id, "object_key": text_fact_key, "fsj_kind": "fact", "evidence_role": "source_observed", "ref_system": "lowfreq", "ref_family": item.source_table or "commodity_text", "ref_table": f"ifa2.{item.source_table}" if item.source_table else None, "ref_key": f"text:{idx}:{item.title}", "ref_locator_json": {"published_at": item.published_at}})
            observed_records.append({"bundle_id": bundle_id, "object_key": text_fact_key, "fsj_kind": "fact", "source_layer": "lowfreq", "source_family": "commodity_text", "source_table": "ifa2.news_history", "source_record_key": "commodity_text_recent", "observed_label": "recent_commodity_text", "observed_payload_json": {"titles": titles}})

        signal = make_signal_object(bundle_id=bundle_id, object_key=plan.signal_key, object_type=plan.signal_type, statement=plan.signal_statement, signal_strength=plan.signal_strength, horizon=plan.horizon, confidence=plan.confidence, attributes={"primary_relation": plan.primary_relation, "secondary_relations": plan.secondary_relations, "based_on_fact_ids": fact_keys})
        judgment = make_judgment_object(bundle_id=bundle_id, object_key=plan.object_key, object_type=plan.judgment_type, statement=plan.judgment_statement, judgment_action=plan.judgment_action, direction=plan.direction, priority=plan.priority, confidence=plan.confidence, invalidators=plan.invalidators, attributes={"primary_relation": plan.primary_relation, "secondary_relations": plan.secondary_relations, "based_on_signal_ids": [plan.signal_key], "degrade_reason": plan.degrade_reason})
        edges = [*[edge(bundle_id, "fact_to_signal", "fact", fact_key, "signal", plan.signal_key) for fact_key in fact_keys], edge(bundle_id, "signal_to_judgment", "signal", plan.signal_key, "judgment", plan.object_key), support_relation_edge(bundle_id, plan.object_key, f"judgment:{data.slot}:main:reference", relation=plan.primary_relation, strength="primary")]
        for relation in plan.secondary_relations:
            edges.append(support_relation_edge(bundle_id, plan.object_key, f"judgment:{data.slot}:main:reference", relation=relation, strength="secondary"))
        return {"bundle": bundle, "objects": [*facts, signal, judgment], "edges": edges, "evidence_links": evidence_links, "observed_records": observed_records, "report_links": []}

    def _bundle_id(self, data: CommoditiesSupportProducerInput) -> str:
        digest = hashlib.sha1(f"a_share:{data.business_date}:{data.slot}:commodities:{data.section_key}".encode("utf-8")).hexdigest()[:12]
        return f"a_share:{data.business_date}:{data.slot}:commodities:{data.section_key}:{digest}"

    def _plan(self, data: CommoditiesSupportProducerInput) -> SupportJudgmentPlan:
        return self._plan_early(data) if data.slot == "early" else self._plan_late(data)

    def _plan_early(self, data: CommoditiesSupportProducerInput) -> SupportJudgmentPlan:
        if not data.has_background_support:
            return SupportJudgmentPlan(primary_relation="adjust", secondary_relations=[], judgment_type="watch_item", judgment_action="observe", direction="neutral", priority="p1", signal_type="risk", signal_strength="low", horizon="same_day", confidence="low", object_key="judgment:early:commodities:chain_watch", signal_key="signal:early:commodities:mapping_quality", summary="盘前商品背景不足，只能保留资源链观察。", signal_statement="盘前商品/资源链缺少足够快照，不能直接上升为A股映射判断。", judgment_statement="盘前主 Agent 仅将商品链作为 observe 输入，等待盘中验证链条映射是否成立。", invalidators=["缺少商品快照", "缺少资源链文本锚点"], degrade_reason="missing_background_support")
        if data.has_fresh_change_signal:
            return SupportJudgmentPlan(primary_relation="adjust", secondary_relations=["support"], judgment_type="support", judgment_action="adjust", direction="conditional", priority="p0", signal_type="confirmation", signal_strength="medium", horizon="same_day", confidence="medium", object_key="judgment:early:commodities:chain_watch", signal_key="signal:early:commodities:mapping_quality", summary="盘前商品链有新变化，应作为主判断的 adjust 输入。", signal_statement="商品/资源链出现新的价格或事件变化，适合修正主 Agent 对资源映射方向的排序。", judgment_statement="盘前将商品链作为 adjust 输入：提高黄金/有色/黑色链的监控优先级，但不把商品波动直接写成A股已验证主线。", invalidators=["商品波动缺少A股承接", "把外盘或期货脉冲误写成股票主线"])
        return SupportJudgmentPlan(primary_relation="support", secondary_relations=[], judgment_type="support", judgment_action="support", direction="neutral", priority="p1", signal_type="confirmation", signal_strength="medium", horizon="same_day", confidence="medium", object_key="judgment:early:commodities:chain_watch", signal_key="signal:early:commodities:mapping_quality", summary="盘前商品链更多是稳定背景，可支持资源映射边界。", signal_statement="商品链背景稳定，可为主 Agent 提供资源品映射的观察边界。", judgment_statement="盘前保留商品链 support 作为背景支撑，不让商品波动替代开盘后的股票结构验证。", invalidators=["盘前出现新的资源价格冲击未纳入", "把链条背景误写成同日已验证驱动"])

    def _plan_late(self, data: CommoditiesSupportProducerInput) -> SupportJudgmentPlan:
        if not data.has_background_support:
            return SupportJudgmentPlan(primary_relation="adjust", secondary_relations=[], judgment_type="risk", judgment_action="observe", direction="neutral", priority="p1", signal_type="risk", signal_strength="low", horizon="t_plus_1", confidence="low", object_key="judgment:late:commodities:next_day_watch", signal_key="signal:late:commodities:chain_validation", summary="收盘后商品背景不足，只能保留为次日观察项。", signal_statement="晚报阶段商品链证据不足，不能判断映射是否真实成立。", judgment_statement="晚报不要把商品链写成全天驱动，仅保留 next-day watch。", invalidators=["缺少商品快照", "缺少映射验证"], degrade_reason="missing_background_support")
        if data.has_fresh_change_signal:
            return SupportJudgmentPlan(primary_relation="support", secondary_relations=["adjust"], judgment_type="next_step", judgment_action="prepare", direction="conditional", priority="p0", signal_type="rotation", signal_strength="medium", horizon="t_plus_1", confidence="medium", object_key="judgment:late:commodities:next_day_watch", signal_key="signal:late:commodities:chain_validation", summary="晚报商品链形成可追溯变化，应沉淀为次日优先验证链条。", signal_statement="同日商品/资源链出现可追溯变化，更适合作为次日重点验证的映射链条。", judgment_statement="晚报将商品链沉淀为 next-day watch：保留黄金/有色/黑色链中更值得继续验证的方向，不把弱相关同步夸大为强驱动。", invalidators=["价格变化未被A股承接", "相关性只是表面同步"])
        return SupportJudgmentPlan(primary_relation="adjust", secondary_relations=[], judgment_type="support", judgment_action="confirm", direction="neutral", priority="p1", signal_type="confirmation", signal_strength="low", horizon="t_plus_1", confidence="medium", object_key="judgment:late:commodities:next_day_watch", signal_key="signal:late:commodities:chain_validation", summary="晚报商品链更像稳定背景，不足以单独抬升次日主线优先级。", signal_statement="同日没有新的商品链变化，更多是资源背景与次日观察边界。", judgment_statement="晚报将商品链作为 adjust/confirm 输入：保留跟踪，但不把它写成次日必然主线。", invalidators=["收盘后出现新的商品冲击未纳入", "把稳定背景误写成强驱动"])


class EarlyCommoditiesSupportProducer:
    def __init__(self, reader: CommoditiesSupportInputReader | None = None, store: FSJStore | None = None) -> None:
        self.reader = reader or SqlCommoditiesSupportInputReader()
        self.store = store or FSJStore()
        self.assembler = CommoditiesSupportAssembler()

    def produce(self, *, business_date: str) -> dict[str, Any]:
        return self.assembler.build_bundle_graph(self.reader.read(business_date=business_date, slot="early"))

    def produce_and_persist(self, *, business_date: str) -> dict[str, Any]:
        return self.store.upsert_bundle_graph(self.produce(business_date=business_date))


class LateCommoditiesSupportProducer:
    def __init__(self, reader: CommoditiesSupportInputReader | None = None, store: FSJStore | None = None) -> None:
        self.reader = reader or SqlCommoditiesSupportInputReader()
        self.store = store or FSJStore()
        self.assembler = CommoditiesSupportAssembler()

    def produce(self, *, business_date: str) -> dict[str, Any]:
        return self.assembler.build_bundle_graph(self.reader.read(business_date=business_date, slot="late"))

    def produce_and_persist(self, *, business_date: str) -> dict[str, Any]:
        return self.store.upsert_bundle_graph(self.produce(business_date=business_date))
