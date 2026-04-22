from __future__ import annotations

from ifa_data_platform.fsj.mid_main_producer import MidMainFSJAssembler, MidMainProducerInput


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
