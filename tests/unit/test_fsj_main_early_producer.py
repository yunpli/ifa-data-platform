from __future__ import annotations

from dataclasses import replace
from datetime import date

from ifa_data_platform.fsj import early_main_producer as early_main_producer_module
from ifa_data_platform.fsj.early_main_producer import EarlyMainFSJAssembler, EarlyMainProducerInput, SqlEarlyMainInputReader


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
        focus_items=[
            {
                "symbol": "300024.SZ",
                "name": "机器人龙头A",
                "company_name": "机器人龙头A",
                "list_types": ["key_focus"],
                "list_type": "key_focus",
                "priority": 1,
                "key_focus": True,
                "sector_or_theme": "机器人",
                "market_evidence": {"has_daily_bar": True, "recent_return_pct": 3.2, "latest_volume": 1200000, "latest_amount": 56000000},
                "text_event_evidence": {"announcement_count": 1, "research_count": 1, "investor_qa_count": 0, "dragon_tiger_count": 0, "limit_up_count": 1, "event_count": 2},
            },
            {
                "symbol": "002031.SZ",
                "name": "机器人链补涨B",
                "company_name": "机器人链补涨B",
                "list_types": ["focus"],
                "list_type": "focus",
                "priority": 2,
                "sector_or_theme": "机器人",
                "market_evidence": {"has_daily_bar": True, "recent_return_pct": 1.1},
                "text_event_evidence": {"announcement_count": 0, "research_count": 0, "investor_qa_count": 1, "dragon_tiger_count": 0, "limit_up_count": 0, "event_count": 0},
            },
            {
                "symbol": "601127.SH",
                "name": "汽车链核心C",
                "company_name": "汽车链核心C",
                "list_types": ["focus"],
                "list_type": "focus",
                "priority": 3,
                "sector_or_theme": "汽车零部件",
                "market_evidence": {"has_daily_bar": False},
                "text_event_evidence": {"announcement_count": 0, "research_count": 0, "investor_qa_count": 0, "dragon_tiger_count": 0, "limit_up_count": 0, "event_count": 0},
            },
        ],
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


def test_assembler_threads_db_backed_focus_item_metadata_into_payload_scope() -> None:
    assembler = EarlyMainFSJAssembler()
    payload = assembler.build_bundle_graph(_sample_input(has_high=True, has_low=True))

    focus_scope = payload["bundle"]["payload_json"]["focus_scope"]
    assert focus_scope["name_map"]["300024.SZ"] == "机器人龙头A"
    assert focus_scope["items"][0]["symbol"] == "300024.SZ"
    assert focus_scope["items"][0]["list_types"] == ["key_focus"]
    assert focus_scope["items"][0]["market_evidence"]["has_daily_bar"] is True
    assert focus_scope["items"][0]["text_event_evidence"]["event_count"] == 2
    assert focus_scope["items"][0]["sector_or_theme"] == "机器人"
    assert any(item["symbol"] == "002031.SZ" and item["list_types"] == ["focus"] for item in focus_scope["items"])


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


class _FakeMappingsResult:
    def __init__(self, *, rows=None, first=None, one=None):
        self._rows = rows if rows is not None else []
        self._first = first
        self._one = one

    def mappings(self):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        return self._first

    def one(self):
        return self._one


class _FakeConnection:
    def __init__(self, focus_rows):
        self.focus_rows = focus_rows
        self.focus_sql = None

    def execute(self, statement, params=None):
        sql = str(statement)
        if "from ifa2.trade_cal_history" in sql:
            return _FakeMappingsResult(first={"cal_date": date(2026, 4, 23), "is_open": True, "pretrade_date": date(2026, 4, 22)})
        if "from ifa2.focus_lists fl" in sql:
            self.focus_sql = sql
            return _FakeMappingsResult(rows=self.focus_rows)
        if "from ifa2.highfreq_open_auction_working" in sql:
            return _FakeMappingsResult(one={"cnt": 0, "snapshot_time": None})
        if "from ifa2.highfreq_event_stream_working" in sql:
            return _FakeMappingsResult(rows=[])
        if "from ifa2.highfreq_leader_candidate_working" in sql:
            return _FakeMappingsResult(rows=[])
        if "from ifa2.highfreq_intraday_signal_state_working" in sql:
            return _FakeMappingsResult(rows=[])
        if "with latest_text as" in sql:
            return _FakeMappingsResult(rows=[])
        if "from ifa2.ifa_fsj_bundles" in sql:
            return _FakeMappingsResult(first=None)
        raise AssertionError(f"unexpected SQL: {sql}")


class _FakeBegin:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, conn):
        self.conn = conn

    def begin(self):
        return _FakeBegin(self.conn)


def test_sql_reader_prefers_focus_item_name_over_db_fallback_and_queries_ts_code_first(monkeypatch) -> None:
    focus_rows = [
        {"symbol": "000001.SZ", "name": "平安银行", "list_type": "key_focus", "priority": 1},
        {"symbol": "000002.SZ", "name": "万科Ａ", "list_type": "focus", "priority": 2},
        {"symbol": "000004.SZ", "name": "配置内名称优先", "list_type": "focus", "priority": 3},
    ]
    fake_conn = _FakeConnection(focus_rows)
    monkeypatch.setattr(early_main_producer_module, "make_engine", lambda: _FakeEngine(fake_conn))

    data = SqlEarlyMainInputReader().read(business_date="2026-04-23")

    assert "sbc.ts_code = fi.symbol" in fake_conn.focus_sql
    assert "sbh.ts_code = fi.symbol" in fake_conn.focus_sql
    assert "split_part(fi.symbol, '.', 1)" in fake_conn.focus_sql
    assert data.focus_items[0]["name"] == "平安银行"
    assert any(item["symbol"] == "000002.SZ" and item["name"] == "万科Ａ" for item in data.focus_items)
    assert any(item["symbol"] == "000004.SZ" and item["name"] == "配置内名称优先" for item in data.focus_items)
