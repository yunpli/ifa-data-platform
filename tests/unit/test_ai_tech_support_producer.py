from __future__ import annotations

from ifa_data_platform.fsj.ai_tech_support_producer import AITechSupportAssembler, AITechSupportProducerInput
from ifa_data_platform.fsj.support_common import SupportSnapshot, SupportTextItem


def _sample_input(*, slot: str = "early", with_background: bool = True, with_fresh_change: bool = True, negative_close: bool = False) -> AITechSupportProducerInput:
    snapshots = []
    texts = []
    if with_background:
        snapshots = [
            SupportSnapshot(
                object_key="ai_tech:人工智能",
                label="人工智能",
                source_layer="midfreq",
                source_family="sector_performance",
                source_table="ifa2.sector_performance_history",
                source_record_key="人工智能@2099-04-22" if with_fresh_change else "人工智能@2099-04-21",
                freshness_label="fresh" if with_fresh_change else "t_minus_1",
                confidence="high",
                value_text=("人工智能 当日涨跌幅 -1.20%" if negative_close else "人工智能 当日涨跌幅 3.80%") if with_fresh_change else "人工智能 当日涨跌幅 1.20%",
                observed_at="2099-04-22" if with_fresh_change else "2099-04-21",
                attributes={"trade_date": "2099-04-22" if with_fresh_change else "2099-04-21", "pct_chg": -1.2 if negative_close else (3.8 if with_fresh_change else 1.2)},
            ),
            SupportSnapshot(
                object_key="ai_tech:半导体",
                label="半导体",
                source_layer="midfreq",
                source_family="sector_performance",
                source_table="ifa2.sector_performance_history",
                source_record_key="半导体@2099-04-21",
                freshness_label="t_minus_1",
                confidence="medium",
                value_text="半导体 当日涨跌幅 2.10%",
                observed_at="2099-04-21",
                attributes={"trade_date": "2099-04-21", "pct_chg": 2.1},
            ),
        ]
    if with_fresh_change:
        texts = [
            SupportTextItem(title="算力订单再获验证", published_at="2099-04-22T07:10:00+08:00", source_table="news_history"),
            SupportTextItem(title="国产AI芯片催化升温", published_at="2099-04-22T06:45:00+08:00", source_table="news_history"),
        ]

    return AITechSupportProducerInput(
        business_date="2099-04-22",
        slot=slot,
        agent_domain="ai_tech",
        section_key="support_ai_tech",
        section_type="support",
        bundle_topic_key=f"ai_tech_{slot}_support:2099-04-22",
        summary_topic="A股AI-tech support",
        tech_focus_count=12 if with_background else 0,
        tech_key_focus_count=4 if with_background else 0,
        tech_focus_symbols=["300308.SZ", "688981.SH", "002230.SZ", "603019.SH"] if with_background else [],
        ai_tech_sector_snapshots=snapshots,
        latest_text_items=texts,
        archive_sector_count=6 if with_background else 0,
        archive_sector_latest_business_date="2099-04-21" if with_background else None,
        current_top_sector="人工智能" if with_background else None,
        current_top_sector_pct_chg=(-1.2 if negative_close else 3.8) if with_background and with_fresh_change else (1.2 if with_background else None),
        prior_main_summary="主判断认为科技链有修复机会" if with_background else None,
        previous_support_summary="前一日 AI-tech 处于支线跟踪" if with_background else None,
        replay_id="replay-2099-04-22",
        slot_run_id="slot-run-2099-04-22",
        report_run_id=None,
    )


def test_early_ai_tech_support_prefers_adjust_when_fresh_change_exists() -> None:
    payload = AITechSupportAssembler().build_bundle_graph(_sample_input(slot="early", with_background=True, with_fresh_change=True))

    bundle = payload["bundle"]
    assert bundle["slot"] == "early"
    assert bundle["agent_domain"] == "ai_tech"
    assert bundle["section_key"] == "support_ai_tech"
    assert bundle["payload_json"]["primary_relation"] == "adjust"
    assert bundle["payload_json"]["secondary_relations"] == ["support"]

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    signal = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "signal")
    assert judgment["object_type"] == "support"
    assert judgment["judgment_action"] == "adjust"
    assert signal["object_type"] == "confirmation"
    assert "盘前" in judgment["statement"]


def test_early_ai_tech_support_degrades_to_watch_when_background_missing() -> None:
    payload = AITechSupportAssembler().build_bundle_graph(_sample_input(slot="early", with_background=False, with_fresh_change=False))

    bundle = payload["bundle"]
    assert bundle["payload_json"]["primary_relation"] == "adjust"
    assert bundle["payload_json"]["degrade"]["reason"] == "missing_background_support"

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    signal = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "signal")
    assert judgment["object_type"] == "watch_item"
    assert judgment["judgment_action"] == "observe"
    assert signal["object_type"] == "risk"


def test_late_ai_tech_support_can_emit_counter_when_diffusion_fails() -> None:
    payload = AITechSupportAssembler().build_bundle_graph(
        _sample_input(slot="late", with_background=True, with_fresh_change=True, negative_close=True)
    )

    bundle = payload["bundle"]
    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    relation_edges = [edge for edge in payload["edges"] if edge["edge_type"] == "judgment_to_judgment"]
    assert bundle["payload_json"]["primary_relation"] == "counter"
    assert judgment["object_type"] == "risk"
    assert judgment["judgment_action"] == "adjust"
    assert any(edge["role"] == "counter" for edge in relation_edges)


def test_late_ai_tech_support_prepares_next_day_when_strength_holds() -> None:
    payload = AITechSupportAssembler().build_bundle_graph(_sample_input(slot="late", with_background=True, with_fresh_change=True))

    bundle = payload["bundle"]
    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    assert bundle["payload_json"]["primary_relation"] == "support"
    assert judgment["object_type"] == "next_step"
    assert judgment["judgment_action"] == "prepare"
    assert bundle["payload_json"]["degrade"]["has_focus_scaffold"] is True
