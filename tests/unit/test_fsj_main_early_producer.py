from __future__ import annotations

from dataclasses import replace

from ifa_data_platform.fsj.early_main_producer import EarlyMainFSJAssembler, EarlyMainProducerInput


def _sample_input(*, has_high: bool = True, has_low: bool = True) -> EarlyMainProducerInput:
    return EarlyMainProducerInput(
        business_date="2099-04-22",
        slot="early",
        section_key="pre_open_main",
        section_type="thesis",
        bundle_topic_key="mainline_candidate:2099-04-22",
        summary_topic="A股盘前主线预案",
        trading_day_open=True,
        trading_day_label="open",
        focus_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        focus_list_types=["focus", "key_focus"],
        auction_count=18 if has_high else 0,
        auction_snapshot_time="2099-04-22T09:27:00+08:00" if has_high else None,
        event_count=6 if has_high else 0,
        event_latest_time="2099-04-22T09:25:00+08:00" if has_high else None,
        event_titles=["机器人链条隔夜催化", "算力链订单更新"] if has_high else [],
        leader_count=4 if has_high else 0,
        leader_symbols=["300024.SZ", "002031.SZ"] if has_high else [],
        signal_scope_count=1 if has_high else 0,
        latest_signal_state="candidate_confirming" if has_high else None,
        text_catalyst_count=3 if has_low else 0,
        text_catalyst_titles=["机器人政策催化", "AI 应用发布", "龙头预告更新"] if has_low else [],
        previous_archive_summary="昨日机器人主线维持高位扩散" if has_low else None,
        replay_id="replay-early-2099-04-22",
        slot_run_id="slot-run-early-2099-04-22",
        report_run_id=None,
    )


def test_assembler_builds_early_main_candidate_graph_with_high_evidence() -> None:
    assembler = EarlyMainFSJAssembler()
    payload = assembler.build_bundle_graph(_sample_input(has_high=True, has_low=True))

    bundle = payload["bundle"]
    assert bundle["slot"] == "early"
    assert bundle["agent_domain"] == "main"
    assert bundle["section_key"] == "pre_open_main"
    assert bundle["assembly_mode"] == "contract_driven_first_slice"

    objects = payload["objects"]
    facts = [obj for obj in objects if obj["fsj_kind"] == "fact"]
    signals = [obj for obj in objects if obj["fsj_kind"] == "signal"]
    judgments = [obj for obj in objects if obj["fsj_kind"] == "judgment"]

    assert len(facts) >= 3
    assert len(signals) == 1
    assert len(judgments) == 1
    assert judgments[0]["object_type"] == "thesis"
    assert judgments[0]["judgment_action"] == "validate"
    assert "不应视为已确认" in signals[0]["statement"]

    edges = payload["edges"]
    assert any(edge["edge_type"] == "fact_to_signal" for edge in edges)
    assert any(edge["edge_type"] == "signal_to_judgment" for edge in edges)

    evidence_links = payload["evidence_links"]
    assert any(link["evidence_role"] == "slot_replay" for link in evidence_links)
    assert any(link["ref_system"] == "highfreq" for link in evidence_links)

    observed_records = payload["observed_records"]
    assert any(record["source_layer"] == "highfreq" for record in observed_records)
    assert any(record["source_layer"] == "business_seed" for record in observed_records)


def test_assembler_degrades_to_watch_item_when_high_layer_missing() -> None:
    assembler = EarlyMainFSJAssembler()
    payload = assembler.build_bundle_graph(_sample_input(has_high=False, has_low=True))

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    signal = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "signal")
    market_fact = next(obj for obj in payload["objects"] if obj["object_key"] == "fact:early:market_inputs")

    assert judgment["object_type"] == "watch_item"
    assert judgment["judgment_action"] == "watch"
    assert "不输出‘今日主线已成立’" in judgment["statement"]
    assert signal["object_type"] == "risk"
    assert market_fact["attributes_json"]["is_finalized_equivalent"] is False
    assert market_fact["attributes_json"]["degrade_reason"] == "missing_preopen_high_layer"
    assert payload["bundle"]["payload_json"]["degrade"]["candidate_only"] is True


def test_assembler_backfills_runtime_lineage_ids_when_reader_inputs_are_missing() -> None:
    assembler = EarlyMainFSJAssembler()
    payload = assembler.build_bundle_graph(replace(_sample_input(has_high=True, has_low=True), replay_id=None, slot_run_id=None))

    bundle = payload["bundle"]
    assert bundle["slot_run_id"].startswith("fsj-runtime:slot_run:2099-04-22:early:")
    assert bundle["replay_id"].startswith("fsj-runtime:replay:2099-04-22:early:")
    assert any(
        link["evidence_role"] == "slot_replay" and link["ref_key"] == bundle["replay_id"]
        for link in payload["evidence_links"]
    )
