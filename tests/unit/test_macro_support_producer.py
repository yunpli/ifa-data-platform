from __future__ import annotations

from ifa_data_platform.fsj.macro_support_producer import MacroSupportAssembler, MacroSupportProducerInput, SqlMacroSupportInputReader
from ifa_data_platform.fsj.support_common import SupportSnapshot, SupportTextItem


def _sample_input(*, slot: str = "early", with_background: bool = True, with_fresh_change: bool = True) -> MacroSupportProducerInput:
    snapshots = []
    texts = []
    if with_background:
        snapshots = [
            SupportSnapshot(
                object_key="macro:liquidity",
                label="中国M2",
                source_layer="lowfreq",
                source_family="macro_history",
                source_table="ifa2.macro_history",
                source_record_key="CN_M2@2099-04-22" if with_fresh_change else "CN_M2@2099-04-21",
                freshness_label="fresh" if with_fresh_change else "t_minus_1",
                confidence="high",
                value_text="中国M2 最新值 8.4%",
                observed_at="2099-04-22" if with_fresh_change else "2099-04-21",
                attributes={"report_date": "2099-04-22" if with_fresh_change else "2099-04-21"},
            ),
            SupportSnapshot(
                object_key="macro:fx",
                label="美元指数",
                source_layer="lowfreq",
                source_family="macro_history",
                source_table="ifa2.macro_history",
                source_record_key="USD_INDEX@2099-04-21",
                freshness_label="t_minus_1",
                confidence="medium",
                value_text="美元指数 最新值 101.2",
                observed_at="2099-04-21",
                attributes={"report_date": "2099-04-21"},
            ),
        ]
    if with_fresh_change:
        texts = [
            SupportTextItem(title="央行流动性表述更新", published_at="2099-04-22T07:10:00+08:00", source_table="news_history"),
            SupportTextItem(title="海外利率预期回摆", published_at="2099-04-22T06:45:00+08:00", source_table="news_history"),
        ]

    return MacroSupportProducerInput(
        business_date="2099-04-22",
        slot=slot,
        agent_domain="macro",
        section_key="support_macro",
        section_type="support",
        bundle_topic_key=f"macro_{slot}_support:2099-04-22",
        summary_topic="A股宏观 support",
        macro_snapshots=snapshots,
        latest_text_items=texts,
        archive_macro_count=3 if with_background else 0,
        archive_macro_latest_business_date="2099-04-21" if with_background else None,
        archive_news_count=8 if with_background else 0,
        northbound_net_flow=42.5 if slot == "late" else None,
        prior_main_summary="主判断维持科技修复" if with_background else None,
        previous_support_summary="上一期宏观以背景 support 为主" if with_background else None,
        replay_id="replay-2099-04-22",
        slot_run_id="slot-run-2099-04-22",
        report_run_id=None,
    )


def test_early_macro_support_prefers_adjust_when_fresh_change_exists() -> None:
    payload = MacroSupportAssembler().build_bundle_graph(_sample_input(slot="early", with_background=True, with_fresh_change=True))

    bundle = payload["bundle"]
    assert bundle["slot"] == "early"
    assert bundle["agent_domain"] == "macro"
    assert bundle["section_key"] == "support_macro"
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


def test_early_macro_support_degrades_to_watch_when_background_missing() -> None:
    payload = MacroSupportAssembler().build_bundle_graph(_sample_input(slot="early", with_background=False, with_fresh_change=False))

    bundle = payload["bundle"]
    assert bundle["payload_json"]["primary_relation"] == "adjust"
    assert bundle["payload_json"]["degrade"]["reason"] == "missing_background_support"

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    signal = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "signal")
    assert judgment["object_type"] == "watch_item"
    assert judgment["judgment_action"] == "observe"
    assert signal["object_type"] == "risk"


def test_late_macro_support_turns_fresh_change_into_next_day_prepare() -> None:
    payload = MacroSupportAssembler().build_bundle_graph(_sample_input(slot="late", with_background=True, with_fresh_change=True))

    bundle = payload["bundle"]
    assert bundle["slot"] == "late"
    assert bundle["payload_json"]["primary_relation"] == "adjust"

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    assert judgment["object_type"] == "next_step"
    assert judgment["judgment_action"] == "prepare"
    assert "next-day watch" in judgment["statement"]


def test_late_macro_support_can_confirm_background_mode() -> None:
    payload = MacroSupportAssembler().build_bundle_graph(_sample_input(slot="late", with_background=True, with_fresh_change=False))

    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    bundle = payload["bundle"]
    assert bundle["payload_json"]["primary_relation"] == "support"
    assert judgment["object_type"] == "support"
    assert judgment["judgment_action"] == "confirm"
    assert bundle["payload_json"]["degrade"]["has_background_support"] is True


def test_sql_reader_late_uses_north_money_column(monkeypatch) -> None:
    class _FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def mappings(self):
            return self

        def all(self):
            return self._rows

        def one(self):
            return self._rows[0]

        def first(self):
            return self._rows[0] if self._rows else None

    class _FakeConn:
        def execute(self, stmt, params):
            sql = str(stmt)
            if "from ifa2.macro_history" in sql and "row_number() over" in sql:
                return _FakeResult([
                    {"macro_series": "CN_M2", "indicator_name": "中国M2", "report_date": "2099-04-22", "value": 8.4, "unit": "%"}
                ])
            if "from ifa2.news_history" in sql:
                return _FakeResult([])
            if "from ifa2.announcements_history" in sql:
                return _FakeResult([])
            if "from ifa2.ifa_archive_macro_daily" in sql:
                return _FakeResult([{"cnt": 3, "latest_business_date": "2099-04-21"}])
            if "from ifa2.ifa_archive_news_daily" in sql:
                return _FakeResult([{"cnt": 5}])
            if "agent_domain = 'main'" in sql:
                return _FakeResult([{"summary": "main late summary"}])
            if "agent_domain = 'macro'" in sql:
                return _FakeResult([{"summary": "previous macro summary"}])
            if "from ifa2.northbound_flow_history" in sql:
                assert "north_money as northbound_net_flow" in sql
                return _FakeResult([{"northbound_net_flow": 306404.91}])
            raise AssertionError(sql)

    class _FakeEngine:
        def begin(self):
            class _Ctx:
                def __enter__(self_inner):
                    return _FakeConn()

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Ctx()

    monkeypatch.setattr("ifa_data_platform.fsj.macro_support_producer.make_engine", lambda: _FakeEngine())

    payload = SqlMacroSupportInputReader().read(business_date="2099-04-22", slot="late")

    assert payload.northbound_net_flow == 306404.91
    assert payload.archive_macro_count == 3
    assert payload.prior_main_summary == "main late summary"
