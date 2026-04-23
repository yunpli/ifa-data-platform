from __future__ import annotations

from dataclasses import replace

from ifa_data_platform.fsj.late_main_producer import LateMainFSJAssembler, LateMainProducerInput


def _sample_input(*, full_close: bool = True, provisional: bool = False) -> LateMainProducerInput:
    if full_close:
        equity_daily_count = 420
        northbound_flow_count = 1
        limit_up_detail_count = 78
        limit_up_down_status_count = 1
        dragon_tiger_count = 12
        sector_performance_count = 42
        latest_text_count = 4
        latest_text_source_times = [
            "2099-04-22T16:03:00+08:00",
            "2099-04-22T15:41:00+08:00",
            "2099-04-22T15:10:00+08:00",
        ]
    elif provisional:
        equity_daily_count = 420
        northbound_flow_count = 0
        limit_up_detail_count = 0
        limit_up_down_status_count = 0
        dragon_tiger_count = 0
        sector_performance_count = 0
        latest_text_count = 0
        latest_text_source_times = []
    else:
        equity_daily_count = 0
        northbound_flow_count = 0
        limit_up_detail_count = 0
        limit_up_down_status_count = 0
        dragon_tiger_count = 0
        sector_performance_count = 0
        latest_text_count = 2
        latest_text_source_times = ["2099-04-22T15:05:00+08:00"]

    return LateMainProducerInput(
        business_date="2099-04-22",
        slot="late",
        section_key="post_close_main",
        section_type="thesis",
        bundle_topic_key="mainline_close:2099-04-22",
        summary_topic="A股收盘主线复盘",
        equity_daily_count=equity_daily_count,
        equity_daily_latest_trade_date="2099-04-22" if equity_daily_count else None,
        equity_daily_sample_symbols=["300024.SZ", "002031.SZ", "601127.SH"] if equity_daily_count else [],
        northbound_flow_count=northbound_flow_count,
        northbound_latest_trade_date="2099-04-22" if northbound_flow_count else None,
        northbound_net_amount=38.5 if northbound_flow_count else None,
        limit_up_detail_count=limit_up_detail_count,
        limit_up_detail_latest_trade_date="2099-04-22" if limit_up_detail_count else None,
        limit_up_detail_sample_symbols=["300024.SZ", "002031.SZ"] if limit_up_detail_count else [],
        limit_up_down_status_count=limit_up_down_status_count,
        limit_up_down_latest_trade_date="2099-04-22" if limit_up_down_status_count else None,
        limit_up_count=56 if limit_up_down_status_count else None,
        limit_down_count=3 if limit_up_down_status_count else None,
        dragon_tiger_count=dragon_tiger_count,
        dragon_tiger_latest_trade_date="2099-04-22" if dragon_tiger_count else None,
        dragon_tiger_sample_symbols=["300024.SZ", "002031.SZ"] if dragon_tiger_count else [],
        sector_performance_count=sector_performance_count,
        sector_performance_latest_trade_date="2099-04-22" if sector_performance_count else None,
        sector_performance_top_sector="机器人" if sector_performance_count else None,
        sector_performance_top_pct_chg=4.8 if sector_performance_count else None,
        latest_text_count=latest_text_count,
        latest_text_titles=["盘后业绩快报", "政策催化", "龙头澄清", "机构点评"][:latest_text_count],
        latest_text_source_times=latest_text_source_times,
        intraday_event_count=5,
        intraday_event_latest_time="2099-04-22T14:56:00+08:00",
        intraday_event_titles=["机器人午后回流", "AI 应用分支走强"],
        intraday_leader_count=3,
        intraday_leader_latest_time="2099-04-22T14:57:00+08:00",
        intraday_leader_symbols=["300024.SZ", "002031.SZ"],
        intraday_signal_scope_count=2,
        intraday_signal_latest_time="2099-04-22T14:58:00+08:00",
        intraday_validation_state="confirmed",
        previous_late_summary="T-1 晚报维持机器人主线高位扩散",
        same_day_mid_summary="盘中机器人链条继续扩散并保持 validation=confirmed",
        replay_id="replay-late-2099-04-22",
        slot_run_id="slot-run-late-2099-04-22",
        report_run_id=None,
    )


def test_assembler_builds_full_close_graph_when_same_day_final_and_text_are_ready() -> None:
    assembler = LateMainFSJAssembler()
    payload = assembler.build_bundle_graph(_sample_input(full_close=True, provisional=False))

    bundle = payload["bundle"]
    assert bundle["slot"] == "late"
    assert bundle["agent_domain"] == "main"
    assert bundle["section_key"] == "post_close_main"
    assert bundle["assembly_mode"] == "contract_driven_first_slice"

    judgments = [obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment"]
    signals = [obj for obj in payload["objects"] if obj["fsj_kind"] == "signal"]
    facts = [obj for obj in payload["objects"] if obj["fsj_kind"] == "fact"]

    assert len(judgments) == 1
    assert len(signals) == 2
    assert len(facts) >= 4
    assert judgments[0]["object_type"] == "thesis"
    assert judgments[0]["judgment_action"] == "confirm"
    assert "晚报主线收盘结论依据" in judgments[0]["statement"]

    close_signal = next(obj for obj in signals if obj["object_key"] == "signal:late:close_package_state")
    assert close_signal["object_type"] == "confirmation"
    assert close_signal["attributes_json"]["contract_mode"] == "full_close_package"

    market_fact = next(obj for obj in facts if obj["object_key"] == "fact:late:same_day_final_market")
    assert market_fact["attributes_json"]["is_finalized_equivalent"] is True
    assert market_fact["attributes_json"]["completeness_label"] == "complete"

    evidence_links = payload["evidence_links"]
    assert any(link["ref_system"] == "midfreq" for link in evidence_links)
    assert any(link["ref_system"] == "highfreq" for link in evidence_links)
    assert any(link["evidence_role"] == "slot_replay" for link in evidence_links)


def test_assembler_degrades_to_provisional_close_when_final_support_is_incomplete() -> None:
    assembler = LateMainFSJAssembler()
    payload = assembler.build_bundle_graph(_sample_input(full_close=False, provisional=True))

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    close_signal = next(obj for obj in payload["objects"] if obj["object_key"] == "signal:late:close_package_state")
    market_fact = next(obj for obj in payload["objects"] if obj["object_key"] == "fact:late:same_day_final_market")

    assert judgment["object_type"] == "watch_item"
    assert judgment["judgment_action"] == "monitor"
    assert "provisional close" in judgment["statement"]
    assert close_signal["object_type"] == "risk"
    assert close_signal["attributes_json"]["provisional_close_only"] is True
    assert market_fact["attributes_json"]["is_finalized_equivalent"] is True
    assert market_fact["attributes_json"]["completeness_label"] == "partial"
    assert payload["bundle"]["payload_json"]["degrade"]["contract_mode"] == "provisional_close_only"
    assert payload["bundle"]["payload_json"]["degrade"]["provisional_close_only"] is True


def test_assembler_refuses_full_close_when_only_intraday_context_exists() -> None:
    assembler = LateMainFSJAssembler()
    payload = assembler.build_bundle_graph(_sample_input(full_close=False, provisional=False))

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    market_fact = next(obj for obj in payload["objects"] if obj["object_key"] == "fact:late:same_day_final_market")

    assert judgment["object_type"] == "watch_item"
    assert judgment["judgment_action"] == "watch"
    assert "不形成正式收盘主结论" in judgment["statement"]
    assert market_fact["attributes_json"]["is_finalized_equivalent"] is False
    assert market_fact["attributes_json"]["degrade_reason"] == "same_day_final_structure_missing"
    assert payload["bundle"]["payload_json"]["degrade"]["contract_mode"] == "post_close_observation_only"
    assert payload["bundle"]["payload_json"]["degrade"]["full_close_ready"] is False
    assert any(obj["object_key"] == "fact:late:retained_intraday_context" for obj in payload["objects"])
    assert any(obj["object_key"] == "fact:late:t_minus_1_background" for obj in payload["objects"])
    assert any(obj["object_key"] == "fact:late:same_day_mid_anchor" for obj in payload["objects"])
    assert any(link["ref_system"] == "archive_v2" for link in payload["evidence_links"])
    assert any(link["ref_system"] == "fsj" for link in payload["evidence_links"])
    assert any(link["ref_system"] == "highfreq" for link in payload["evidence_links"])
    assert any(obj["object_key"] == "fact:late:same_day_text_evidence" for obj in payload["objects"])
    assert any(record["source_layer"] == "highfreq" for record in payload["observed_records"])
    assert any(record["source_layer"] == "lowfreq" for record in payload["observed_records"])
    assert all(record["source_layer"] != "archive" for record in payload["observed_records"])
    assert all(record["source_layer"] != "replay" for record in payload["observed_records"])
    assert all(record["source_layer"] != "midfreq" for record in payload["observed_records"] if record["object_key"] != "fact:late:same_day_final_market")
    assert payload["bundle"]["payload_json"]["degrade"]["degrade_reason"] == "same_day_final_structure_missing"
    assert payload["bundle"]["summary"].startswith("A股收盘主线复盘：缺少 same-day stable/final 主表")
    assert market_fact["attributes_json"]["same_day_final_structure_ready"] is False
    assert market_fact["attributes_json"]["same_day_stable_support_ready"] is False
    assert market_fact["attributes_json"]["completeness_label"] == "sparse"
    assert judgment["attributes_json"]["same_day_final_structure_ready"] is False
    assert judgment["attributes_json"]["same_day_low_text_ready"] is True
    assert judgment["attributes_json"]["same_day_stable_support_ready"] is False
    assert judgment["attributes_json"]["contract_mode"] == "post_close_observation_only"
    assert judgment["attributes_json"]["provisional_close_only"] is False
    close_signal = next(obj for obj in payload["objects"] if obj["object_key"] == "signal:late:close_package_state")
    assert close_signal["attributes_json"]["degrade_reason"] == "same_day_final_structure_missing"
    assert close_signal["attributes_json"]["contract_mode"] == "post_close_observation_only"
    assert close_signal["object_type"] == "risk"
    assert close_signal["signal_strength"] == "low"
    assert any(edge["edge_type"] == "signal_to_judgment" for edge in payload["edges"])
    assert any(edge["edge_type"] == "fact_to_signal" for edge in payload["edges"])
    assert payload["bundle"]["payload_json"]["degrade"]["has_same_day_low_text"] is True
    assert payload["bundle"]["payload_json"]["degrade"]["has_same_day_final_structure"] is False
    assert payload["bundle"]["payload_json"]["degrade"]["has_same_day_stable_market_support"] is False
    assert payload["bundle"]["payload_json"]["degrade"]["provisional_close_only"] is False
    assert payload["bundle"]["payload_json"]["implemented_scope"]["slot"] == "late"
    assert "same-day lowfreq text with source_time" in payload["bundle"]["payload_json"]["implemented_scope"]["included_primary_inputs"]
    assert "retained intraday highfreq context" in payload["bundle"]["payload_json"]["implemented_scope"]["included_context_inputs"]
    assert "support-agent merge" in payload["bundle"]["payload_json"]["implemented_scope"]["deferred_inputs"]
    assert any("不得输出 final daily structure judgment" in invalidator for invalidator in judgment["invalidators"])
    assert any("误当成 same-day close confirmation" in invalidator for invalidator in judgment["invalidators"])
    assert any(record["source_family"] == "event_time_stream" for record in payload["observed_records"])
    assert any(record["source_family"] == "leader_candidate" for record in payload["observed_records"])
    assert any(record["source_family"] == "intraday_signal_state" for record in payload["observed_records"])
    assert any(record["source_family"] == "equity_daily_bar" for record in payload["observed_records"])
    assert any(record["source_family"] == "same_day_latest_text" for record in payload["observed_records"])
    assert payload["bundle"]["slot"] == "late"
    assert payload["bundle"]["agent_domain"] == "main"
    assert payload["bundle"]["section_key"] == "post_close_main"
    assert payload["bundle"]["assembly_mode"] == "contract_driven_first_slice"
    assert payload["bundle"]["producer_version"] == "phase1-main-late-v1"
    assert payload["bundle"]["producer"] == "ifa_data_platform.fsj.late_main_producer"
    assert payload["bundle"]["status"] == "active"
    assert payload["bundle"]["report_run_id"] is None
    assert payload["bundle"]["slot_run_id"] == "slot-run-late-2099-04-22"
    assert payload["bundle"]["replay_id"] == "replay-late-2099-04-22"
    assert payload["bundle"]["bundle_topic_key"] == "mainline_close:2099-04-22"
    assert payload["bundle"]["section_type"] == "thesis"
    assert payload["bundle"]["market"] == "a_share"
    assert payload["bundle"]["business_date"] == "2099-04-22"
    assert payload["bundle"]["payload_json"]["schema_version"] == "phase1-main-late-v1"
    assert payload["bundle"]["payload_json"]["contract_source"] == "A_SHARE_EARLY_MID_LATE_DATA_CONSUMPTION_CONTRACT_V1"
    assert payload["bundle"]["payload_json"]["degrade"]["completeness_label"] == "sparse"
    assert market_fact["statement"].startswith("same-day 收盘稳定市场层覆盖")
    assert any(obj["statement"].startswith("日内 retained highfreq") for obj in payload["objects"] if obj["fsj_kind"] == "signal")
    assert any(obj["statement"].startswith("same-day retained intraday context") for obj in payload["objects"] if obj["object_key"] == "fact:late:retained_intraday_context")
    assert all(obj["attributes_json"].get("not_for_same_day_confirmation", False) for obj in payload["objects"] if obj["object_key"] == "fact:late:t_minus_1_background")
    assert all(obj["attributes_json"].get("background_only", False) for obj in payload["objects"] if obj["object_key"] == "fact:late:t_minus_1_background")
    assert all(obj["attributes_json"].get("not_for_final_confirmation", False) for obj in payload["objects"] if obj["object_key"] == "fact:late:retained_intraday_context")
    assert any(link["evidence_role"] == "historical_reference" for link in payload["evidence_links"])
    assert any(link["evidence_role"] == "prior_slot_reference" for link in payload["evidence_links"])
    assert any(link["evidence_role"] == "slot_replay" for link in payload["evidence_links"])
    assert any(link["evidence_role"] == "source_observed" and link["ref_system"] == "midfreq" for link in payload["evidence_links"])
    assert any(link["evidence_role"] == "source_observed" and link["ref_system"] == "highfreq" for link in payload["evidence_links"])
    assert len([obj for obj in payload["objects"] if obj["fsj_kind"] == "signal"]) == 2
    assert len([obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment"]) == 1
    assert len([obj for obj in payload["objects"] if obj["fsj_kind"] == "fact"]) >= 4
    assert len(payload["edges"]) >= 4
    assert len(payload["evidence_links"]) >= 8
    assert len(payload["observed_records"]) >= 4
    assert judgment["confidence"] == "low"
    assert judgment["direction"] == "mixed"
    assert judgment["priority"] == "p0"
    assert judgment["attributes_json"]["degrade_reason"] == "same_day_final_structure_missing"
    assert judgment["attributes_json"]["deferred"]
    assert "support-agent merge not yet implemented" in judgment["attributes_json"]["deferred"]
    assert close_signal["confidence"] == "low"
    assert close_signal["horizon"] == "same_day_close"
    assert any(obj["horizon"] == "same_day_close" for obj in payload["objects"] if obj["fsj_kind"] == "signal")
    assert any(obj["evidence_level"] == "E1" for obj in payload["objects"] if obj["fsj_kind"] == "fact")
    assert any(obj["evidence_level"] == "E2" for obj in payload["objects"] if obj["fsj_kind"] == "fact")
    assert market_fact["confidence"] == "low"
    assert market_fact["attributes_json"]["source_layer"] == "mid"
    assert any(obj["attributes_json"].get("source_layer") == "archive" for obj in payload["objects"] if obj["fsj_kind"] == "fact")
    assert any(obj["attributes_json"].get("source_layer") == "high" for obj in payload["objects"] if obj["fsj_kind"] == "fact")
    assert any(obj["attributes_json"].get("source_layer") == "replay" for obj in payload["objects"] if obj["fsj_kind"] == "fact")
    assert payload["report_links"] == []
    assert payload["bundle"]["supersedes_bundle_id"] is None


def test_late_assembler_backfills_runtime_lineage_ids_when_reader_inputs_are_missing() -> None:
    assembler = LateMainFSJAssembler()
    payload = assembler.build_bundle_graph(replace(_sample_input(full_close=True, provisional=False), replay_id=None, slot_run_id=None))

    bundle = payload["bundle"]
    assert bundle["slot_run_id"].startswith("fsj-runtime:slot_run:2099-04-22:late:")
    assert bundle["replay_id"].startswith("fsj-runtime:replay:2099-04-22:late:")
    assert any(
        link["evidence_role"] == "slot_replay" and link["ref_key"] == bundle["replay_id"]
        for link in payload["evidence_links"]
    )
