from __future__ import annotations

from ifa_data_platform.fsj.commodities_support_producer import (
    CommoditiesSupportAssembler,
    CommoditiesSupportProducerInput,
)
from ifa_data_platform.fsj.support_common import SupportSnapshot, SupportTextItem


def _sample_input(*, slot: str = "early", with_background: bool = True, with_fresh_change: bool = True) -> CommoditiesSupportProducerInput:
    snapshots = []
    texts = []
    if with_background:
        snapshots = [
            SupportSnapshot(
                object_key="commodity:precious_metal:AU9999.SGE",
                label="AU9999.SGE",
                source_layer="midfreq",
                source_family="precious_metal_15min_history",
                source_table="ifa2.precious_metal_15min_history",
                source_record_key="AU9999.SGE@2099-04-22T09:15:00" if with_fresh_change else "AU9999.SGE@2099-04-21T14:45:00",
                freshness_label="fresh" if with_fresh_change else "t_minus_1",
                confidence="high",
                value_text="AU9999.SGE 最新价 582.6 vol=1200 oi=3100",
                observed_at="2099-04-22T09:15:00" if with_fresh_change else "2099-04-21T14:45:00",
                attributes={"trade_time": "2099-04-22T09:15:00" if with_fresh_change else "2099-04-21T14:45:00", "close": 582.6, "vol": 1200.0, "oi": 3100.0, "family": "precious_metal"},
            ),
            SupportSnapshot(
                object_key="commodity:commodity:CU.SHF",
                label="CU.SHF",
                source_layer="midfreq",
                source_family="commodity_15min_history",
                source_table="ifa2.commodity_15min_history",
                source_record_key="CU.SHF@2099-04-21T14:45:00",
                freshness_label="t_minus_1",
                confidence="medium",
                value_text="CU.SHF 最新价 72100 vol=850 oi=1800",
                observed_at="2099-04-21T14:45:00",
                attributes={"trade_time": "2099-04-21T14:45:00", "close": 72100.0, "vol": 850.0, "oi": 1800.0, "family": "commodity"},
            ),
        ]
    if with_fresh_change:
        texts = [
            SupportTextItem(title="黄金夜盘走强带动资源链关注升温", published_at="2099-04-22T07:10:00+08:00", source_table="news_history"),
            SupportTextItem(title="铜价波动扩大，有色映射需盘中验证", published_at="2099-04-22T06:45:00+08:00", source_table="news_history"),
        ]

    return CommoditiesSupportProducerInput(
        business_date="2099-04-22",
        slot=slot,
        agent_domain="commodities",
        section_key="support_commodities",
        section_type="support",
        bundle_topic_key=f"commodities_{slot}_support:2099-04-22",
        summary_topic="A股 commodities support",
        commodity_snapshots=snapshots,
        latest_text_items=texts,
        futures_daily_count=5 if with_background else 0,
        futures_latest_trade_date="2099-04-21" if with_background else None,
        intraday_snapshot_latest_time="2099-04-22T09:15:00" if with_background and with_fresh_change else None,
        prior_main_summary="主判断维持资源映射跟踪" if with_background else None,
        previous_support_summary="前一期商品链以背景观察为主" if with_background else None,
        replay_id="replay-2099-04-22",
        slot_run_id="slot-run-2099-04-22",
        report_run_id=None,
    )


def test_early_commodities_support_prefers_adjust_when_fresh_change_exists() -> None:
    payload = CommoditiesSupportAssembler().build_bundle_graph(_sample_input(slot="early", with_background=True, with_fresh_change=True))

    bundle = payload["bundle"]
    assert bundle["slot"] == "early"
    assert bundle["agent_domain"] == "commodities"
    assert bundle["section_key"] == "support_commodities"
    assert bundle["payload_json"]["primary_relation"] == "adjust"
    assert bundle["payload_json"]["secondary_relations"] == ["support"]

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    signal = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "signal")
    assert judgment["object_type"] == "support"
    assert judgment["judgment_action"] == "adjust"
    assert signal["object_type"] == "confirmation"
    assert "盘前" in judgment["statement"]

    relation_edges = [edge for edge in payload["edges"] if edge["edge_type"] == "judgment_to_judgment"]
    assert any(edge["role"] == "adjust" for edge in relation_edges)
    assert any(edge["attributes_json"]["relation_strength"] == "secondary" for edge in relation_edges)


def test_early_commodities_support_degrades_to_watch_when_background_missing() -> None:
    payload = CommoditiesSupportAssembler().build_bundle_graph(_sample_input(slot="early", with_background=False, with_fresh_change=False))

    bundle = payload["bundle"]
    assert bundle["payload_json"]["primary_relation"] == "adjust"
    assert bundle["payload_json"]["degrade"]["reason"] == "missing_background_support"

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    signal = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "signal")
    assert judgment["object_type"] == "watch_item"
    assert judgment["judgment_action"] == "observe"
    assert signal["object_type"] == "risk"


def test_late_commodities_support_prepares_next_day_when_strength_holds() -> None:
    payload = CommoditiesSupportAssembler().build_bundle_graph(_sample_input(slot="late", with_background=True, with_fresh_change=True))

    bundle = payload["bundle"]
    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    assert bundle["payload_json"]["primary_relation"] == "support"
    assert bundle["payload_json"]["secondary_relations"] == ["adjust"]
    assert judgment["object_type"] == "next_step"
    assert judgment["judgment_action"] == "prepare"
    assert "next-day watch" in judgment["statement"]


def test_late_commodities_support_can_confirm_background_mode() -> None:
    payload = CommoditiesSupportAssembler().build_bundle_graph(_sample_input(slot="late", with_background=True, with_fresh_change=False))

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    bundle = payload["bundle"]
    assert bundle["payload_json"]["primary_relation"] == "adjust"
    assert judgment["object_type"] == "support"
    assert judgment["judgment_action"] == "confirm"
    assert bundle["payload_json"]["degrade"]["has_background_support"] is True
