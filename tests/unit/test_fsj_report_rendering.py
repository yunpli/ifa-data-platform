from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import json
import pytest

from ifa_data_platform.fsj import report_rendering as rr
from ifa_data_platform.fsj.chart_pack import FSJChartPackBuilder
from ifa_data_platform.fsj.report_dispatch import MainReportDeliveryDispatchHelper
from ifa_data_platform.fsj.report_quality import MainReportQAEvaluator, SupportReportQAEvaluator
from ifa_data_platform.fsj.report_rendering import (
    MainReportArtifactPublishingService,
    MainReportHTMLRenderer,
    MainReportRenderingService,
    SupportReportArtifactPublishingService,
    SupportReportHTMLRenderer,
    SupportReportRenderingService,
)
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError as LiveIsolationError


@pytest.fixture(autouse=True)
def _explicit_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp")


def _assembled_sections() -> dict:
    return {
        "artifact_type": "fsj_main_report_sections",
        "artifact_version": "v2",
        "market": "a_share",
        "business_date": "2099-04-22",
        "agent_domain": "main",
        "section_count": 2,
        "support_summary_domains": ["ai_tech", "macro"],
        "sections": [
            {
                "slot": "early",
                "section_key": "pre_open_main",
                "section_render_key": "main.pre_open",
                "title": "盘前主结论",
                "order_index": 10,
                "status": "ready",
                "bundle": {
                    "bundle_id": "bundle-early",
                    "status": "active",
                    "supersedes_bundle_id": None,
                    "bundle_topic_key": "early:pre_open_main",
                    "producer": "ifa_data_platform.fsj.early_main_producer",
                    "producer_version": "phase1-main-early-v1",
                    "section_type": "thesis",
                    "slot_run_id": "slot-run-early",
                    "replay_id": "replay-early",
                    "report_run_id": None,
                    "updated_at": "2099-04-22T08:59:00+08:00",
                },
                "summary": "机器人链条是今日盘前首要验证主线。",
                "judgments": [
                    {
                        "object_key": "judgment:early:mainline_plan",
                        "statement": "若竞价延续强化，则优先观察机器人主线确认。",
                        "judgment_action": "validate",
                        "confidence": "medium",
                        "evidence_level": "E2",
                    }
                ],
                "signals": [
                    {
                        "object_key": "signal:early:confirm",
                        "statement": "竞价成交额与封单强度需同步抬升。",
                        "signal_strength": "medium",
                        "confidence": "medium",
                        "evidence_level": "E2",
                    }
                ],
                "facts": [
                    {
                        "object_key": "fact:early:robotics",
                        "statement": "隔夜催化继续集中在机器人/设备更新方向。",
                        "confidence": "high",
                        "evidence_level": "E1",
                    }
                ],
                "support_summaries": [
                    {
                        "bundle_id": "bundle-support-ai-early",
                        "slot": "early",
                        "agent_domain": "ai_tech",
                        "section_key": "support_ai_tech",
                        "bundle_topic_key": "ai_tech_early_support:2099-04-22",
                        "status": "active",
                        "summary": "AI 科技催化存在，但更适合作为主判断的 adjust 输入。",
                        "producer": "ifa_data_platform.fsj.early_ai_tech_support_producer",
                        "producer_version": "phase1-ai-tech-early-v1",
                        "slot_run_id": "slot-run-early-support-ai",
                        "replay_id": "replay-early-support-ai",
                        "report_run_id": None,
                        "updated_at": "2099-04-22T08:57:00+08:00",
                        "lineage": {
                            "bundle": {"payload_json": {"degrade": {"reason": "missing_background_support"}}},
                            "report_links": [
                                {
                                    "artifact_type": "html",
                                    "artifact_uri": "file:///tmp/support-ai-early.html",
                                    "section_render_key": "support.ai_tech.early",
                                }
                            ],
                            "evidence_links": [
                                {"ref_key": "source:early:ai-tech"},
                            ],
                        },
                    },
                    {
                        "bundle_id": "bundle-support-macro-early",
                        "slot": "early",
                        "agent_domain": "macro",
                        "section_key": "support_macro",
                        "bundle_topic_key": "macro_early_support:2099-04-22",
                        "status": "active",
                        "summary": "宏观背景偏稳定，更多作为边界 support。",
                        "producer": "ifa_data_platform.fsj.early_macro_support_producer",
                        "producer_version": "phase1-macro-early-v1",
                        "slot_run_id": "slot-run-early-support-macro",
                        "replay_id": "replay-early-support-macro",
                        "report_run_id": None,
                        "updated_at": "2099-04-22T08:56:00+08:00",
                        "lineage": {
                            "bundle": {"payload_json": {"degrade": {}}},
                            "report_links": [],
                            "evidence_links": [
                                {"ref_key": "source:early:macro"},
                            ],
                        },
                    },
                ],
                "lineage": {
                    "bundle": {"bundle_id": "bundle-early", "payload_json": {"focus_scope": {"focus_symbols": ["300024.SZ", "002031.SZ", "601138.SH"], "focus_list_types": ["key_focus", "focus"], "items": [{"symbol": "300024.SZ", "name": "机器人龙头A", "company_name": "机器人龙头A", "list_types": ["key_focus"], "list_type": "key_focus", "priority": 1, "key_focus": True, "sector_or_theme": "机器人", "market_evidence": {"has_daily_bar": True, "recent_return_pct": 3.8, "latest_volume": 1800000, "latest_amount": 92000000}, "text_event_evidence": {"announcement_count": 1, "research_count": 1, "investor_qa_count": 0, "dragon_tiger_count": 0, "limit_up_count": 1, "event_count": 2}}, {"symbol": "002031.SZ", "name": "机器人链补涨B", "company_name": "机器人链补涨B", "list_types": ["focus"], "list_type": "focus", "priority": 2, "sector_or_theme": "机器人", "market_evidence": {"has_daily_bar": True, "recent_return_pct": 1.2}, "text_event_evidence": {"announcement_count": 0, "research_count": 0, "investor_qa_count": 1, "dragon_tiger_count": 0, "limit_up_count": 0, "event_count": 0}}, {"symbol": "601138.SH", "name": "工业自动化核心C", "company_name": "工业自动化核心C", "list_types": ["focus"], "list_type": "focus", "priority": 3, "sector_or_theme": "工业自动化", "market_evidence": {"has_daily_bar": False}, "text_event_evidence": {"announcement_count": 0, "research_count": 1, "investor_qa_count": 0, "dragon_tiger_count": 0, "limit_up_count": 0, "event_count": 0}}], "why_included": "当前业务观察池覆盖 3 个 A 股 focus/key-focus 对象，可作为盘前主线验证与噪音过滤锚点。"}, "degrade": {"degrade_reason": "missing_preopen_high_layer", "contract_mode": "candidate_only", "completeness_label": "sparse"}}},
                    "objects": [],
                    "edges": [],
                    "evidence_links": [
                        {"ref_key": "source:early:robotics"},
                    ],
                    "observed_records": [],
                    "report_links": [
                        {
                            "artifact_type": "markdown",
                            "artifact_uri": "file:///tmp/earlier-early.md",
                            "section_render_key": "main.pre_open",
                        }
                    ],
                    "support_bundle_ids": ["bundle-support-ai-early", "bundle-support-macro-early"],
                },
            },
            {
                "slot": "late",
                "section_key": "post_close_main",
                "section_render_key": "main.post_close",
                "title": "收盘主结论",
                "order_index": 30,
                "status": "ready",
                "bundle": {
                    "bundle_id": "bundle-late",
                    "status": "active",
                    "supersedes_bundle_id": None,
                    "bundle_topic_key": "late:post_close_main",
                    "producer": "ifa_data_platform.fsj.late_main_producer",
                    "producer_version": "phase1-main-late-v1",
                    "section_type": "thesis",
                    "slot_run_id": "slot-run-late",
                    "replay_id": "replay-late",
                    "report_run_id": None,
                    "updated_at": "2099-04-22T15:05:00+08:00",
                },
                "summary": "收盘确认主线强化，但高位分歧增大。",
                "judgments": [],
                "signals": [
                    {
                        "object_key": "signal:late:close_package_state",
                        "statement": "same-day final market packet ready，收盘 close package 可用。",
                        "signal_strength": "high",
                        "confidence": "high",
                        "evidence_level": "E1",
                        "attributes_json": {
                            "contract_mode": "full_close_package",
                            "provisional_close_only": False,
                        },
                    }
                ],
                "facts": [],
                "support_summaries": [],
                "lineage": {
                    "bundle": {"bundle_id": "bundle-late", "payload_json": {"degrade": {}}},
                    "objects": [],
                    "edges": [],
                    "evidence_links": [],
                    "observed_records": [],
                    "report_links": [],
                    "support_bundle_ids": [],
                },
            },
        ],
    }


def test_main_report_html_renderer_emits_sendable_html_with_lineage_hooks() -> None:
    renderer = MainReportHTMLRenderer()

    rendered = renderer.render(
        _assembled_sections(),
        report_run_id="report-run-2099-04-22",
        artifact_uri="file:///tmp/a-share-main-2099-04-22.html",
        generated_at=datetime(2099, 4, 22, 8, 0, tzinfo=timezone.utc),
    )

    assert rendered["artifact_type"] == "fsj_main_report_html"
    assert rendered["artifact_version"] == "v2"
    assert rendered["render_format"] == "html"
    assert rendered["content_type"] == "text/html"
    assert "A股主报告｜2099-04-22" in rendered["title"]
    assert "盘前主结论" in rendered["content"]
    assert "收盘主结论" in rendered["content"]
    assert "phase1-main-early-v1" in rendered["content"]
    assert "source:early:robotics" in rendered["content"]
    assert "Support 摘要（非全文）" in rendered["content"]
    assert "执行覆盖" in rendered["content"]
    assert "晚报合同口径" in rendered["content"]
    assert "正式收盘口径" in rendered["content"]
    assert "AI / 科技" in rendered["content"]
    assert "宏观" in rendered["content"]
    assert "support-ai-early.html" in rendered["content"]
    assert rendered["metadata"]["source_artifact_type"] == "fsj_main_report_sections"
    assert rendered["metadata"]["renderer_version"] == "v3"
    assert rendered["metadata"]["focus_module"]["focus_symbol_count"] == 3
    assert rendered["metadata"]["focus_module"]["chart_refs"][0]["chart_key"] == "key_focus_window"
    assert rendered["metadata"]["support_summary_domains"] == ["ai_tech", "macro"]
    assert rendered["metadata"]["support_summary_bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert rendered["metadata"]["existing_report_links"][0]["artifact_uri"] == "file:///tmp/earlier-early.md"
    assert rendered["metadata"]["existing_report_links"][1]["artifact_uri"] == "file:///tmp/support-ai-early.html"
    assert [link["bundle_id"] for link in rendered["report_links"]] == ["bundle-early", "bundle-late"]
    assert all(link["artifact_type"] == "html" for link in rendered["report_links"])
    assert rendered["report_links"][0]["section_render_key"] == "main.pre_open"


def _chart_manifest() -> dict:
    return {
        "artifact_type": "fsj_main_chart_pack",
        "artifact_version": "v1",
        "business_date": "2099-04-22",
        "chart_count": 3,
        "ready_chart_count": 2,
        "degrade_status": "partial",
        "degrade_reason": ["key_focus_return_bar:focus/equity daily bars missing for requested window"],
        "chart_classes": ["key_focus_bar", "key_focus_line", "market_index_line"],
        "assets": [
            {
                "chart_key": "market_index_window",
                "chart_class": "market_index_line",
                "title": "市场/指数窗口图",
                "relative_path": "charts/market_index_window.svg",
                "source_window": {"source_table": "ifa2.index_daily_bar_history", "frequency": "daily", "lookback_bars": 20, "end_business_date": "2099-04-22"},
                "status": "ready",
                "note": None,
            },
            {
                "chart_key": "key_focus_window",
                "chart_class": "key_focus_line",
                "title": "Key Focus 窗口图",
                "relative_path": "charts/key_focus_window.svg",
                "source_window": {"source_table": "ifa2.equity_daily_bar_history", "frequency": "daily", "lookback_bars": 20, "end_business_date": "2099-04-22"},
                "status": "ready",
                "note": None,
            },
            {
                "chart_key": "key_focus_return_bar",
                "chart_class": "key_focus_bar",
                "title": "Key Focus 日度涨跌幅",
                "relative_path": "charts/key_focus_return_bar.svg",
                "source_window": {"source_table": "ifa2.equity_daily_bar_history", "frequency": "daily", "lookback_bars": 2, "end_business_date": "2099-04-22"},
                "status": "missing",
                "note": "focus/equity daily bars missing for requested window",
            },
        ],
        "html_embed_blocks": [
            {"chart_key": "market_index_window", "title": "市场/指数窗口图", "status": "ready", "relative_path": "charts/market_index_window.svg", "source_window": {"source_table": "ifa2.index_daily_bar_history", "frequency": "daily", "lookback_bars": 20, "end_business_date": "2099-04-22"}, "caption": "window=20 daily bars"},
            {"chart_key": "key_focus_window", "title": "Key Focus 窗口图", "status": "ready", "relative_path": "charts/key_focus_window.svg", "source_window": {"source_table": "ifa2.equity_daily_bar_history", "frequency": "daily", "lookback_bars": 20, "end_business_date": "2099-04-22"}, "caption": "window=20 daily bars"},
            {"chart_key": "key_focus_return_bar", "title": "Key Focus 日度涨跌幅", "status": "missing", "relative_path": "charts/key_focus_return_bar.svg", "source_window": {"source_table": "ifa2.equity_daily_bar_history", "frequency": "daily", "lookback_bars": 2, "end_business_date": "2099-04-22"}, "caption": "focus/equity daily bars missing for requested window"},
        ],
    }


class _StubAssemblyService:
    def __init__(self, artifact: dict):
        self.artifact = artifact
        self.calls: list[tuple[str, bool]] = []

    def assemble_main_sections(self, *, business_date: str, include_empty: bool = False) -> dict:
        self.calls.append((business_date, include_empty))
        return self.artifact


def test_main_report_qa_evaluator_emits_delivery_ready_verdict_for_contract_complete_report() -> None:
    assembled = _assembled_sections()
    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-1",
        artifact_uri="file:///tmp/final.html",
        generated_at=datetime(2099, 4, 22, 8, 0, tzinfo=timezone.utc),
    )

    evaluation = MainReportQAEvaluator().evaluate(assembled, rendered)

    assert evaluation["artifact_type"] == "fsj_main_report_qa"
    assert evaluation["ready_for_delivery"] is True
    assert evaluation["summary"]["late_contract_mode"] == "full_close_package"
    assert evaluation["summary"]["source_health"]["overall_status"] == "degraded"
    assert evaluation["summary"]["blocker_count"] == 0
    assert evaluation["summary"]["warning_count"] >= 1
    assert evaluation["summary"]["qa_axes"]["structural"]["ready"] is True
    assert evaluation["summary"]["qa_axes"]["policy"]["warning_count"] >= 1
    assert any(issue["code"] == "slot_missing" and issue.get("slot") == "mid" for issue in evaluation["issues"])


def test_main_report_renderer_emits_customer_profile_without_engineering_metadata_in_html() -> None:
    rendered = MainReportHTMLRenderer().render(
        _assembled_sections(),
        report_run_id="report-run-customer-1",
        artifact_uri="file:///tmp/customer.html",
        generated_at=datetime(2099, 4, 22, 8, 3, tzinfo=timezone.utc),
        output_profile="customer",
    )

    assert rendered["title"] == "A股市场简报｜2099-04-22"
    assert "iFA A股市场日报｜2099-04-22" in rendered["content"]
    assert "Created by Lindenwood Management LLC" in rendered["content"]
    assert "核心判断：" in rendered["content"]
    assert "风险与下一步" in rendered["content"]
    assert "风险提示" in rendered["content"]
    assert "明日观察 / 下一步" in rendered["content"]
    assert "免责声明" in rendered["content"]
    assert "今日 核心关注 / 关注" in rendered["content"]
    assert "核心关注" in rendered["content"]
    assert "关注" in rendered["content"]
    assert "机器人龙头A（300024.SZ）" in rendered["content"]
    assert "纳入原因：列入核心观察名单，当前已具备本地市场侧样本与文本/事件侧线索，机器人龙头A更适合继续核验强度、承接与主线带动性，而不是直接上升为确定性判断" in rendered["content"]
    assert "盘中观察要点：盘中重点看已有线索能否继续扩展为更明确的量价配合、资金承接与板块共振确认" in rendered["content"]
    assert "需要下调关注的情形：若后续跟踪中量价配合转弱、承接不足或板块共振没有延续，应及时降回观察级别" in rendered["content"]
    assert "分时段重点解读" in rendered["content"]
    assert "开盘前关注" in rendered["content"]
    assert "<h3>盘中观察</h3>" not in rendered["content"]  # assembled fixture only has early/late sections
    assert "收盘复盘" in rendered["content"]
    assert "bundle-early" not in rendered["content"]
    assert "phase1-main-early-v1" not in rendered["content"]
    assert "slot-run-early" not in rendered["content"]
    assert "replay-early" not in rendered["content"]
    assert "source:early:robotics" not in rendered["content"]
    assert rendered["metadata"]["output_profile"] == "customer"
    assert rendered["metadata"]["presentation_schema_version"] == "v1"
    customer_presentation = rendered["metadata"]["customer_presentation"]
    assert customer_presentation["schema_type"] == "fsj_customer_main_presentation"
    assert customer_presentation["brand"] == "iFA"
    assert customer_presentation["created_by"] == "Created by Lindenwood Management LLC"
    assert customer_presentation["top_judgment"]
    assert customer_presentation["risk_block"]
    assert customer_presentation["next_steps"]
    assert customer_presentation["disclaimer"]
    assert customer_presentation["focus_module"]["focus_symbol_count"] == 3
    assert customer_presentation["focus_module"]["key_focus_items"][0]["display_name"] == "机器人龙头A"
    assert customer_presentation["focus_module"]["focus_watch_items"][0]["display_name"] == "机器人链补涨B"
    assert customer_presentation["focus_module"]["focus_watch_items"][1]["display_name"] == "工业自动化核心C"
    assert customer_presentation["focus_module"]["watchlist_tiers"][0]["label"] == "核心关注 / 核心关注列表"
    assert customer_presentation["focus_module"]["watchlist_tiers"][1]["label"] == "关注 / 关注列表"
    assert customer_presentation["focus_module"]["key_focus_items"][0]["evidence_depth"] == "market_and_text"
    assert customer_presentation["focus_module"]["focus_watch_items"][0]["evidence_depth"] == "market_and_text"
    assert customer_presentation["focus_module"]["focus_watch_items"][1]["evidence_depth"] == "text_only"
    assert customer_presentation["sections"][0]["title"] == "开盘前关注"
    assert customer_presentation["sections"][1]["title"] == "收盘复盘"


def test_main_report_renderer_uses_professional_focus_fallback_wording_when_watchlist_tier_is_empty() -> None:
    assembled = _assembled_sections()
    assembled["sections"][0]["lineage"]["bundle"]["payload_json"]["focus_scope"] = {
        "focus_symbols": ["300024.SZ"],
        "focus_list_types": ["key_focus"],
        "items": [{"symbol": "300024.SZ", "name": "机器人龙头A", "list_types": ["key_focus"], "priority": 1}],
        "why_included": "当前报告优先跟踪核心验证对象。",
    }

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-empty-focus-tier-1",
        artifact_uri="file:///tmp/customer-empty-focus-tier.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="customer",
    )

    assert "关注列表暂未展开" in rendered["content"]
    assert "当前报告把研究资源优先放在核心验证对象上" in rendered["content"]
    assert "若盘中出现更明确的扩散线索、联动方向或分歧修复信号，再补充进入观察范围" in rendered["content"]
    assert "暂无 Focus Watchlist" not in rendered["content"]



def test_main_report_renderer_keeps_missing_name_watchlist_rows_readable_without_duplicate_code_dump() -> None:
    assembled = _assembled_sections()
    assembled["sections"][0]["lineage"]["bundle"]["payload_json"]["focus_scope"] = {
        "focus_symbols": ["000001.SZ", "000002.SZ"],
        "focus_list_types": ["key_focus"],
        "items": [
            {"symbol": "000001.SZ", "list_types": ["key_focus"], "priority": 1},
            {"symbol": "000002.SZ", "list_types": ["key_focus"], "priority": 2},
        ],
        "why_included": "当前业务观察池覆盖 2 个 A 股 focus/key-focus 对象，可作为盘前主线验证与噪音过滤锚点。",
    }

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-missing-focus-names-1",
        artifact_uri="file:///tmp/customer-missing-focus-names.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="customer",
    )
    customer_presentation = rendered["metadata"]["customer_presentation"]

    assert "核心观察标的一（000001.SZ）" in rendered["content"]
    assert "A股标的 000001.SZ（000001.SZ）" not in rendered["content"]
    assert customer_presentation["focus_module"]["key_focus_items"][0]["code"] == "000001.SZ"
    assert customer_presentation["focus_module"]["key_focus_items"][0]["display_name"] == "核心观察标的一"
    assert customer_presentation["focus_module"]["key_focus_items"][0]["short_label"] == "核心观察标的一（000001.SZ）"




def test_main_report_renderer_honors_default_focus_display_limits_and_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rr, "KEY_FOCUS_DISPLAY_LIMIT", 30)
    monkeypatch.setattr(rr, "FOCUS_DISPLAY_LIMIT", 50)
    assembled = _assembled_sections()
    items = []
    focus_symbols = []
    for i in range(1, 61):
        symbol = f"{i:06d}.SZ"
        focus_symbols.append(symbol)
        items.append({"symbol": symbol, "name": f"样本{i}", "list_types": ["key_focus"] if i <= 30 else ["focus"], "priority": i})
    assembled["sections"][0]["lineage"]["bundle"]["payload_json"]["focus_scope"] = {
        "focus_symbols": focus_symbols,
        "focus_list_types": ["key_focus", "focus"],
        "items": items,
        "why_included": "测试显示上限与封顶。",
    }

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-focus-limit-1",
        artifact_uri="file:///tmp/customer-focus-limit.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="customer",
    )
    focus_module = rendered["metadata"]["customer_presentation"]["focus_module"]

    assert len(focus_module["key_focus_items"]) == 20
    assert len(focus_module["focus_watch_items"]) == 40
    assert len(focus_module["key_focus_symbols"]) == 20
    assert len(focus_module["focus_watch_symbols"]) == 40

def test_main_report_renderer_differentiates_watchlist_rationale_by_symbol_evidence_depth() -> None:
    assembled = _assembled_sections()
    assembled["sections"][0]["lineage"]["bundle"]["payload_json"]["focus_scope"] = {
        "focus_symbols": ["000001.SZ", "000002.SZ", "000003.SZ"],
        "focus_list_types": ["key_focus", "focus"],
        "items": [
            {
                "symbol": "000001.SZ",
                "name": "样本一",
                "list_types": ["key_focus"],
                "priority": 1,
                "sector_or_theme": "银行",
                "market_evidence": {"has_daily_bar": True, "recent_return_pct": 2.6, "latest_volume": 1000000},
                "text_event_evidence": {"announcement_count": 1, "research_count": 1, "investor_qa_count": 0, "dragon_tiger_count": 0, "limit_up_count": 0, "event_count": 1},
            },
            {
                "symbol": "000002.SZ",
                "name": "样本二",
                "list_types": ["focus"],
                "priority": 2,
                "sector_or_theme": "地产",
                "market_evidence": {"has_daily_bar": True, "recent_return_pct": 0.8},
                "text_event_evidence": {"announcement_count": 0, "research_count": 0, "investor_qa_count": 0, "dragon_tiger_count": 0, "limit_up_count": 0, "event_count": 0},
            },
            {
                "symbol": "000003.SZ",
                "name": "样本三",
                "list_types": ["focus"],
                "priority": 3,
                "text_event_evidence": {"announcement_count": 0, "research_count": 1, "investor_qa_count": 1, "dragon_tiger_count": 0, "limit_up_count": 0, "event_count": 0},
            },
        ],
        "why_included": "当前业务观察池覆盖 3 个 A 股 focus/key-focus 对象，可作为盘前主线验证与噪音过滤锚点。",
    }

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-focus-evidence-1",
        artifact_uri="file:///tmp/customer-focus-evidence.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="customer",
    )
    focus_module = rendered["metadata"]["customer_presentation"]["focus_module"]
    item1 = focus_module["key_focus_items"][0]
    item2 = focus_module["focus_watch_items"][0]
    item3 = focus_module["focus_watch_items"][1]

    assert item1["evidence_depth"] == "market_and_text"
    assert item2["evidence_depth"] == "market_only"
    assert item3["evidence_depth"] == "text_only"
    assert item1["observation_rationale"] != item2["observation_rationale"]
    assert item2["observation_rationale"] != item3["observation_rationale"]
    assert "本地市场侧样本与文本/事件侧线索" in item1["observation_rationale"]
    assert "已有基础盘面样本可供跟踪" in item2["observation_rationale"]
    assert "主要依赖本地文本/事件线索" in item3["observation_rationale"]


def test_main_report_renderer_emits_review_profile_with_internal_lineage_visible() -> None:
    rendered = MainReportHTMLRenderer().render(
        _assembled_sections(),
        report_run_id="report-run-review-1",
        artifact_uri="file:///tmp/review.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="review",
    )

    assert rendered["title"] == "A股主报告审阅包｜2099-04-22"
    assert rendered["metadata"]["output_profile"] == "review"
    assert rendered["metadata"]["presentation_schema_version"] is None
    assert "核心关注 / 关注 模块" in rendered["content"]
    assert "机器人龙头A（300024.SZ）" in rendered["content"]
    assert "盘中重点看已有线索能否继续扩展为更明确的量价配合、资金承接与板块共振确认。" in rendered["content"]
    assert "bundle-early" in rendered["content"]
    assert "phase1-main-early-v1" in rendered["content"]
    assert "source:early:robotics" in rendered["content"]


def test_customer_profile_sanitizes_upstream_contract_phrasing_but_review_keeps_it() -> None:
    assembled = _assembled_sections()
    assembled["sections"][0]["summary"] = "candidate_with_open_validation：主线基于 high+reference 形成。"
    assembled["sections"][0]["judgments"][0]["statement"] = "candidate_with_open_validation：先跟踪，不做确认。"
    assembled["sections"][0]["signals"][0]["statement"] = "watchlist_only：若竞价不足则留在观察池。"
    assembled["sections"][1]["signals"][0]["statement"] = "same-day stable/final market packet ready，收盘 close package 可用。"

    customer = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-sanitize-1",
        artifact_uri="file:///tmp/customer-sanitize.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="customer",
    )
    review = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-review-sanitize-1",
        artifact_uri="file:///tmp/review-sanitize.html",
        generated_at=datetime(2099, 4, 22, 8, 4, tzinfo=timezone.utc),
        output_profile="review",
    )

    assert "candidate_with_open_validation" not in customer["content"]
    assert "high+reference" not in customer["content"]
    assert "watchlist_only" not in customer["content"]
    assert "same-day stable/final" not in customer["content"]
    assert "close package" not in customer["content"]
    assert "证据已具雏形，但仍需开盘验证" in customer["content"]
    assert "盘前交易与资讯线索" in customer["content"]
    assert "暂列观察名单" in customer["content"]
    assert "收盘依据已完整" in customer["content"]
    assert "收盘确认材料" in customer["content"]

    assert "candidate_with_open_validation" in review["content"]
    assert "high+reference" in review["content"]
    assert "watchlist_only" in review["content"]
    assert "same-day stable/final" in review["content"]


def test_customer_profile_polishes_section_level_contract_shaped_prose() -> None:
    assembled = _assembled_sections()
    assembled["sections"][0]["facts"][0]["statement"] = "盘前 盘中结构信号 与 观察名单 已足以形成待开盘验证的主线候选，但仍不应视为已确认"
    assembled["sections"].insert(
        1,
        {
            "slot": "mid",
            "section_key": "intraday_main",
            "section_render_key": "main.midday",
            "title": "盘中结构更新",
            "order_index": 20,
            "status": "ready",
            "bundle": {
                "bundle_id": "bundle-mid",
                "status": "active",
                "producer_version": "phase1-main-mid-v1",
                "slot_run_id": "slot-run-mid",
                "replay_id": "replay-mid",
            },
            "summary": "A股盘中主线更新：盘中 盘中结构信号 证据不足或不够新鲜，仅保留跟踪/观察级更新",
            "judgments": [],
            "signals": [{"statement": "午后继续验证点：等待盘中 盘中结构信号 刷新后再判断是否出现强化、扩散或分歧"}],
            "facts": [{"statement": "盘中锚点：A股盘中主线更新：盘中 盘中结构信号 证据不足或不够新鲜，仅保留跟踪/观察级更新"}],
            "support_summaries": [],
            "lineage": {"bundle": {"payload_json": {"focus_scope": {"focus_symbols": ["300024.SZ"]}}}},
        },
    )
    assembled["sections"][2]["judgments"] = [{"statement": "将当前 收盘依据已完整 事实作为晚报主线收盘结论依据；盘中留存信息 仅做演化解释，T-1 仅做历史对照"}]
    assembled["sections"][2]["signals"] = [
        {"statement": "收盘依据已完整 市场表与同日文本事实已足以形成收盘 收盘确认材料，可以做晚报主线结论"},
        {"statement": "日内 retained highfreq 证据可用于解释从盘中到收盘的演化，但不能替代 收盘依据已完整 close 证据"},
    ]
    assembled["sections"][2]["facts"] = [
        {"statement": "当日 盘中留存信息 context：事件流 8 条，leader 0 个，signal-state 0 条；仅用于解释日内演变，不作为收盘 final 确认证据"},
        {"statement": "当日 收盘稳定市场层覆盖：日线 20 条，北向资金 1 条，涨停明细 85 条，涨跌停状态 1 条，龙虎榜 61 条，板块表现 394 条"},
    ]

    customer = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-prose-1",
        artifact_uri="file:///tmp/customer-prose.html",
        generated_at=datetime(2099, 4, 22, 8, 6, tzinfo=timezone.utc),
        output_profile="customer",
    )
    review = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-review-prose-1",
        artifact_uri="file:///tmp/review-prose.html",
        generated_at=datetime(2099, 4, 22, 8, 6, tzinfo=timezone.utc),
        output_profile="review",
    )

    assert "盘中 盘中结构信号" not in customer["content"]
    assert "收盘 收盘确认材料" not in customer["content"]
    assert "盘前线索与观察名单已经给出初步方向" in customer["content"]
    assert "午后继续观察盘中结构是否修复" in customer["content"]
    assert "盘中锚点：当前结构证据仍不够扎实" in customer["content"]
    assert "晚报结论应以当日收盘后的完整证据为基础" in customer["content"]
    assert "收盘阶段的核心市场与文本证据已经基本到齐" in customer["content"]
    assert "盘中过程信息可用于解释日内演化" in customer["content"]
    assert "收盘后的核心市场数据覆盖已经相对完整" in customer["content"]
    assert "今日判断更适合按“盘前预案—盘中修正—收盘复核”的顺序理解" in customer["content"]
    assert "盘中最容易出现的问题，是把阶段性修复或局部异动误读为全天定论" in customer["content"]
    assert "午后优先核对盘中修复能否扩展到板块层与核心标的层" in customer["content"]

    assert "盘中 盘中结构信号" in review["content"]
    assert "same-day stable/final" not in customer["content"]


def test_customer_profile_uses_mid_only_top_judgment_without_pretending_close_finality() -> None:
    assembled = _assembled_sections()
    assembled["sections"] = [
        {
            "slot": "mid",
            "section_key": "intraday_main",
            "section_render_key": "main.midday",
            "title": "盘中结构更新",
            "order_index": 20,
            "status": "ready",
            "bundle": {
                "bundle_id": "bundle-mid-only",
                "status": "active",
                "producer_version": "phase1-main-mid-v1",
                "slot_run_id": "slot-run-mid-only",
                "replay_id": "replay-mid-only",
            },
            "summary": "盘中证据仍偏谨慎，当前更适合把市场理解为跟踪与校准阶段，而不是提前下收盘定论。",
            "judgments": [],
            "signals": [{"statement": "午后继续验证点：等待盘中 盘中结构信号 刷新后再判断是否出现强化、扩散或分歧"}],
            "facts": [{"statement": "盘中锚点：A股盘中主线更新：盘中 盘中结构信号 证据不足或不够新鲜，仅保留跟踪/观察级更新"}],
            "support_summaries": [],
            "lineage": {"bundle": {"payload_json": {"focus_scope": {"focus_symbols": ["300024.SZ"]}}}},
        }
    ]

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-mid-only-1",
        artifact_uri="file:///tmp/customer-mid-only.html",
        generated_at=datetime(2099, 4, 22, 8, 6, tzinfo=timezone.utc),
        output_profile="customer",
    )

    assert "盘中阶段更强调修正与校准" in rendered["content"]
    assert "当前不宜提前替收盘结论定调" in rendered["content"]
    assert "午后优先核对盘中修复能否扩展到板块层与核心标的层" in rendered["content"]
    assert "盘中最容易出现的问题，是把阶段性修复或局部异动误读为全天定论" in rendered["content"]


def test_customer_profile_filters_full_sections_for_early_slot_requests() -> None:
    assembled = _assembled_sections()
    assembled["sections"].insert(
        1,
        {
            "slot": "mid",
            "section_key": "intraday_main",
            "section_render_key": "main.midday",
            "title": "盘中结构更新",
            "order_index": 20,
            "status": "ready",
            "bundle": {
                "bundle_id": "bundle-mid",
                "status": "active",
                "producer_version": "phase1-main-mid-v1",
                "slot_run_id": "slot-run-mid",
                "replay_id": "replay-mid",
            },
            "summary": "盘中阶段正在验证早盘主线是否扩散。",
            "judgments": [{"statement": "盘中判断：主线仍需确认。"}],
            "signals": [{"statement": "午后观察扩散与承接。"}],
            "facts": [{"statement": "盘中事实：结构修复仍待确认。"}],
            "support_summaries": [],
            "lineage": {"bundle": {"payload_json": {"focus_scope": {"focus_symbols": ["300024.SZ"]}}}},
        },
    )
    assembled["requested_customer_slot"] = "early"

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-slot-early-1",
        artifact_uri="file:///tmp/customer-slot-early.html",
        generated_at=datetime(2099, 4, 22, 8, 7, tzinfo=timezone.utc),
        output_profile="customer",
    )

    assert "<h3>开盘前关注</h3>" in rendered["content"]
    assert "<h3>盘中观察</h3>" not in rendered["content"]
    assert "<h3>收盘复盘</h3>" not in rendered["content"]
    assert rendered["metadata"]["customer_presentation"]["requested_slot"] == "early"
    assert [item["slot"] for item in rendered["metadata"]["customer_presentation"]["sections"]] == ["early"]


def test_customer_profile_filters_full_sections_for_mid_slot_requests_but_keeps_early_review_context() -> None:
    assembled = _assembled_sections()
    assembled["sections"].insert(
        1,
        {
            "slot": "mid",
            "section_key": "intraday_main",
            "section_render_key": "main.midday",
            "title": "盘中结构更新",
            "order_index": 20,
            "status": "ready",
            "bundle": {
                "bundle_id": "bundle-mid",
                "status": "active",
                "producer_version": "phase1-main-mid-v1",
                "slot_run_id": "slot-run-mid",
                "replay_id": "replay-mid",
            },
            "summary": "盘中阶段正在验证早盘主线是否扩散。",
            "judgments": [{"statement": "盘中判断：主线仍需确认。"}],
            "signals": [{"statement": "午后观察扩散与承接。"}],
            "facts": [{"statement": "盘中事实：结构修复仍待确认。"}],
            "support_summaries": [],
            "lineage": {"bundle": {"payload_json": {"focus_scope": {"focus_symbols": ["300024.SZ"]}}}},
        },
    )
    assembled["requested_customer_slot"] = "mid"

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-slot-mid-1",
        artifact_uri="file:///tmp/customer-slot-mid.html",
        generated_at=datetime(2099, 4, 22, 8, 7, tzinfo=timezone.utc),
        output_profile="customer",
    )

    assert "<h3>开盘前关注</h3>" not in rendered["content"]
    assert "<h3>盘中观察</h3>" in rendered["content"]
    assert "<h3>收盘复盘</h3>" not in rendered["content"]
    assert [item["slot"] for item in rendered["metadata"]["customer_presentation"]["sections"]] == ["mid"]
    assert [item["slot"] for item in rendered["metadata"]["customer_presentation"]["summary_cards"]] == ["early", "mid"]


def test_customer_profile_filters_full_sections_for_late_slot_requests_and_keeps_day_mapping_context() -> None:
    assembled = _assembled_sections()
    assembled["sections"].insert(
        1,
        {
            "slot": "mid",
            "section_key": "intraday_main",
            "section_render_key": "main.midday",
            "title": "盘中结构更新",
            "order_index": 20,
            "status": "ready",
            "bundle": {
                "bundle_id": "bundle-mid",
                "status": "active",
                "producer_version": "phase1-main-mid-v1",
                "slot_run_id": "slot-run-mid",
                "replay_id": "replay-mid",
            },
            "summary": "盘中阶段正在验证早盘主线是否扩散。",
            "judgments": [{"statement": "盘中判断：主线仍需确认。"}],
            "signals": [{"statement": "午后观察扩散与承接。"}],
            "facts": [{"statement": "盘中事实：结构修复仍待确认。"}],
            "support_summaries": [],
            "lineage": {"bundle": {"payload_json": {"focus_scope": {"focus_symbols": ["300024.SZ"]}}}},
        },
    )
    assembled["requested_customer_slot"] = "late"

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-slot-late-1",
        artifact_uri="file:///tmp/customer-slot-late.html",
        generated_at=datetime(2099, 4, 22, 8, 7, tzinfo=timezone.utc),
        output_profile="customer",
    )

    assert "<h3>开盘前关注</h3>" not in rendered["content"]
    assert "<h3>盘中观察</h3>" not in rendered["content"]
    assert "<h3>收盘复盘</h3>" in rendered["content"]
    assert [item["slot"] for item in rendered["metadata"]["customer_presentation"]["sections"]] == ["late"]
    assert [item["slot"] for item in rendered["metadata"]["customer_presentation"]["summary_cards"]] == ["early", "mid", "late"]


def test_customer_profile_rewrites_raw_telemetry_and_text_fragments_into_advisory_prose() -> None:
    assembled = _assembled_sections()
    assembled["sections"].insert(
        1,
        {
            "slot": "mid",
            "section_key": "intraday_main",
            "section_render_key": "main.midday",
            "title": "盘中结构更新",
            "order_index": 20,
            "status": "ready",
            "bundle": {
                "bundle_id": "bundle-mid",
                "status": "active",
                "producer_version": "phase1-main-mid-v1",
                "slot_run_id": "slot-run-mid",
                "replay_id": "replay-mid",
            },
            "summary": "盘中仍处于验证阶段。",
            "judgments": [{"statement": "盘中结构层覆盖：1m 样本 0 条，广度 0 条，热度 0 条，信号状态 0 条；最新 validation=unknown，emotion=unknown。"}],
            "signals": [{"statement": "盘中领涨/事件层覆盖：龙头候选 0 个，事件流 8 条；当前优先观察对象包括：300024.SZ。"}],
            "facts": [{"statement": "盘中文本/事件解释线索 8 条，最近样本包括：投资者问答：请问订单情况如何？；公司回复：谢谢关注。"}],
            "support_summaries": [],
            "lineage": {"bundle": {"payload_json": {"focus_scope": {"focus_symbols": ["300024.SZ"]}}}},
        },
    )
    assembled["sections"][0]["facts"][0]["statement"] = "盘前市场侧输入覆盖：竞价样本 0 条，事件流 8 条，候选龙头 0 个，信号状态 0 条。"

    customer = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-telemetry-1",
        artifact_uri="file:///tmp/customer-telemetry.html",
        generated_at=datetime(2099, 4, 22, 8, 5, tzinfo=timezone.utc),
        output_profile="customer",
    )
    review = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-review-telemetry-1",
        artifact_uri="file:///tmp/review-telemetry.html",
        generated_at=datetime(2099, 4, 22, 8, 5, tzinfo=timezone.utc),
        output_profile="review",
    )

    assert "竞价样本 0 条" not in customer["content"]
    assert "候选龙头 0 个" not in customer["content"]
    assert "1m 样本 0 条" not in customer["content"]
    assert "validation=unknown" not in customer["content"]
    assert "emotion=unknown" not in customer["content"]
    assert "投资者问答" not in customer["content"]
    assert "公司回复：谢谢关注" not in customer["content"]
    assert "盘前市场侧确认仍然偏弱" in customer["content"]
    assert "盘中结构验证尚不充分" in customer["content"]
    assert "盘中事件线索仍在演化" in customer["content"]
    assert "相关文本与事件线索可作为背景参考" in customer["content"]

    assert "竞价样本 0 条" in review["content"]
    assert "validation=unknown" in review["content"]
    assert "投资者问答" in review["content"]


def test_main_report_renderer_renders_chart_pack_with_explicit_windows_and_missing_degrade() -> None:
    rendered = MainReportHTMLRenderer().render(
        _assembled_sections(),
        report_run_id="report-run-chart-pack-1",
        artifact_uri="file:///tmp/chart-pack.html",
        generated_at=datetime(2099, 4, 22, 8, 5, tzinfo=timezone.utc),
        chart_manifest=_chart_manifest(),
    )

    assert "关键图表包" in rendered["content"]
    assert "市场/指数窗口图" in rendered["content"]
    assert "Key Focus 窗口图" in rendered["content"]
    assert "Key Focus 日度涨跌幅" in rendered["content"]
    assert "charts/market_index_window.svg" in rendered["content"]
    assert "charts/key_focus_return_bar.svg" in rendered["content"]
    assert "chart_degrade_status=partial" in rendered["content"]
    assert "focus/equity daily bars missing for requested window" in rendered["content"]
    assert rendered["metadata"]["chart_pack"]["ready_chart_count"] == 2
    assert rendered["metadata"]["chart_pack"]["assets"][2]["status"] == "missing"


def test_chart_pack_builder_uses_focus_scope_symbols_for_key_focus_assets(tmp_path: Path) -> None:
    builder = FSJChartPackBuilder()
    assembled = _assembled_sections()

    manifest = builder.build_main_chart_pack(
        business_date="2099-04-22",
        assembled=assembled,
        package_dir=tmp_path,
    )

    focus_assets = {asset["chart_key"]: asset for asset in manifest["assets"] if asset["chart_key"].startswith("key_focus")}
    assert focus_assets["key_focus_window"]["source_window"]["symbols"] == ["300024.SZ", "002031.SZ", "601138.SH"]
    assert focus_assets["key_focus_return_bar"]["source_window"]["symbols"] == ["300024.SZ", "002031.SZ", "601138.SH"]
    assert "观察池标的" in manifest["html_embed_blocks"][1]["caption"]


def test_chart_pack_builder_prioritizes_db_backed_key_focus_items_before_plain_focus(tmp_path: Path) -> None:
    builder = FSJChartPackBuilder()
    assembled = _assembled_sections()
    assembled["sections"][0]["lineage"]["bundle"]["payload_json"]["focus_scope"] = {
        "focus_symbols": ["000002.SZ", "000003.SZ", "000001.SZ", "000004.SZ"],
        "focus_list_types": ["focus", "key_focus"],
        "items": [
            {"symbol": "000003.SZ", "name": "补充观察B", "list_types": ["focus"], "priority": 3},
            {"symbol": "000001.SZ", "name": "核心观察A", "list_types": ["key_focus"], "priority": 1},
            {"symbol": "000004.SZ", "name": "补充观察C", "list_types": ["focus"], "priority": 4},
            {"symbol": "000002.SZ", "name": "核心观察D", "list_types": ["key_focus"], "priority": 2},
        ],
    }

    manifest = builder.build_main_chart_pack(
        business_date="2099-04-22",
        assembled=assembled,
        package_dir=tmp_path,
    )

    focus_assets = {asset["chart_key"]: asset for asset in manifest["assets"] if asset["chart_key"].startswith("key_focus")}
    assert focus_assets["key_focus_window"]["source_window"]["symbols"][:3] == ["000001.SZ", "000002.SZ", "000003.SZ"]


def test_main_report_renderer_keeps_support_content_at_concise_summary_boundary() -> None:
    assembled = _assembled_sections()
    assembled["sections"][0]["support_summaries"][0]["full_report_body"] = "AI 支持报告全文：绝不应直接进入 MAIN HTML。"
    assembled["sections"][0]["support_summaries"][0]["judgments"] = [
        {
            "statement": "support judgment detail that must stay outside the MAIN report body",
        }
    ]
    assembled["sections"][0]["support_summaries"][0]["facts"] = [
        {
            "statement": "support fact detail that must stay outside the MAIN report body",
        }
    ]

    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-concise-boundary",
        artifact_uri="file:///tmp/final-concise-boundary.html",
        generated_at=datetime(2099, 4, 22, 8, 5, tzinfo=timezone.utc),
    )

    assert "AI 科技催化存在，但更适合作为主判断的 adjust 输入。" in rendered["content"]
    assert "AI 支持报告全文：绝不应直接进入 MAIN HTML。" not in rendered["content"]
    assert "support judgment detail that must stay outside the MAIN report body" not in rendered["content"]
    assert "support fact detail that must stay outside the MAIN report body" not in rendered["content"]
    assert "support-ai-early.html" in rendered["content"]


def test_main_report_rendering_service_delegates_assembly_then_render() -> None:
    stub = _StubAssemblyService(_assembled_sections())
    service = MainReportRenderingService(assembly_service=stub)

    rendered = service.render_main_report_html(
        business_date="2099-04-22",
        include_empty=True,
        report_run_id="report-run-1",
        artifact_uri="file:///tmp/final.html",
    )

    assert stub.calls == [("2099-04-22", True)]
    assert rendered["metadata"]["artifact_uri"] == "file:///tmp/final.html"
    assert rendered["report_links"][1]["bundle_id"] == "bundle-late"


class _StubStore:
    def __init__(self) -> None:
        self.registered: list[dict] = []
        self.attached: list[tuple[str, list[dict]]] = []

    def register_report_artifact(self, payload: dict) -> dict:
        self.registered.append(payload)
        return {**payload, "status": payload["status"]}

    def attach_report_links(self, bundle_id: str, report_links: list[dict]) -> list[dict]:
        self.attached.append((bundle_id, report_links))
        return report_links


def test_main_report_qa_evaluator_blocks_historical_only_late_report() -> None:
    assembled = _assembled_sections()
    assembled["sections"][1]["signals"][0]["attributes_json"]["contract_mode"] = "historical_only"
    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-2",
        artifact_uri="file:///tmp/final-historical-only.html",
        generated_at=datetime(2099, 4, 22, 8, 0, tzinfo=timezone.utc),
    )

    evaluation = MainReportQAEvaluator().evaluate(assembled, rendered)

    assert evaluation["ready_for_delivery"] is False
    assert evaluation["summary"]["late_contract_mode"] == "historical_only"
    assert evaluation["summary"]["qa_axes"]["policy"]["ready"] is False
    assert any(issue["code"] == "late_historical_only" for issue in evaluation["issues"])


def test_main_report_qa_evaluator_blocks_when_late_source_health_is_missing_required_family() -> None:
    assembled = _assembled_sections()
    assembled["sections"][1]["lineage"]["bundle"]["payload_json"] = {
        "degrade": {
            "degrade_reason": "same_day_final_structure_missing",
            "contract_mode": "post_close_observation_only",
            "completeness_label": "sparse",
        }
    }
    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-2b",
        artifact_uri="file:///tmp/final-late-source-health-blocked.html",
        generated_at=datetime(2099, 4, 22, 8, 0, tzinfo=timezone.utc),
    )

    evaluation = MainReportQAEvaluator().evaluate(assembled, rendered)

    assert evaluation["ready_for_delivery"] is False
    assert evaluation["summary"]["source_health"]["overall_status"] == "blocked"
    assert evaluation["summary"]["source_health"]["blocking_slot_count"] == 1
    assert any(issue["code"] == "source_health_blocked" and issue.get("slot") == "late" for issue in evaluation["issues"])


def test_main_report_renderer_customer_profile_surfaces_chart_assets_without_internal_ids() -> None:
    rendered = MainReportHTMLRenderer().render(
        _assembled_sections(),
        report_run_id="report-run-customer-chart-1",
        artifact_uri="file:///tmp/customer-chart.html",
        generated_at=datetime(2099, 4, 22, 8, 6, tzinfo=timezone.utc),
        output_profile="customer",
        chart_manifest=_chart_manifest(),
    )

    assert "关键图表" in rendered["content"]
    assert "charts/market_index_window.svg" not in rendered["content"]
    assert "部分图表因连续行情样本不足暂不展示涨跌幅对比，本期保留指数与核心关注窗口图作为主要参考。" in rendered["content"]
    assert "chart_degrade_status=partial" not in rendered["content"]
    assert "ready_chart_count=2/3" not in rendered["content"]
    assert "bundle-early" not in rendered["content"]
    assert rendered["metadata"]["customer_presentation"]["chart_pack"]["chart_count"] == 3


def test_main_report_qa_evaluator_exposes_extended_qa_axes_and_customer_readiness() -> None:
    assembled = _assembled_sections()
    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-qa-axes-1",
        artifact_uri="file:///tmp/final-qa-axes.html",
        generated_at=datetime(2099, 4, 22, 8, 7, tzinfo=timezone.utc),
    )

    evaluation = MainReportQAEvaluator().evaluate(assembled, rendered)

    assert evaluation["summary"]["qa_axes"]["editorial"]["ready"] is True
    assert evaluation["summary"]["qa_axes"]["leakage"]["ready"] is True
    assert evaluation["summary"]["qa_axes"]["time_window"]["ready"] is True
    assert evaluation["summary"]["qa_axes"]["customer_readiness"]["ready"] is True
    assert evaluation["summary"]["customer_report_readiness"]["ready"] is True
    assert evaluation["summary"]["golden_sample_regression_hooks"]["recommended_tests"]


def test_main_report_qa_evaluator_blocks_customer_html_when_internal_tokens_leak() -> None:
    assembled = _assembled_sections()
    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-customer-leak-1",
        artifact_uri="file:///tmp/customer-leak.html",
        generated_at=datetime(2099, 4, 22, 8, 8, tzinfo=timezone.utc),
        output_profile="customer",
    )
    rendered["content"] = rendered["content"].replace("</body>", "<div>bundle-early</div></body>")

    evaluation = MainReportQAEvaluator().evaluate(assembled, rendered)

    assert evaluation["ready_for_delivery"] is False
    assert evaluation["summary"]["qa_axes"]["leakage"]["ready"] is False
    assert evaluation["summary"]["qa_axes"]["customer_readiness"]["ready"] is False
    assert evaluation["summary"]["customer_report_readiness"]["customer_safe"] is False
    assert "customer_internal_field_leak" in [issue["code"] for issue in evaluation["issues"]]


def test_main_report_artifact_publisher_writes_html_manifest_and_qa_with_report_wiring(tmp_path: Path) -> None:
    stub = _StubAssemblyService(_assembled_sections())
    rendering_service = MainReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store, artifact_root=tmp_path)

    published = publisher.publish_main_report_html(
        business_date="2099-04-22",
        output_dir=tmp_path,
        include_empty=False,
        report_run_id="report-run-final-1",
        generated_at=datetime(2099, 4, 22, 9, 30, tzinfo=timezone.utc),
    )

    html_path = Path(published["html_path"])
    qa_path = Path(published["qa_path"])
    eval_path = Path(published["eval_path"])
    manifest_path = Path(published["manifest_path"])
    assert html_path.exists()
    assert qa_path.exists()
    assert eval_path.exists()
    assert manifest_path.exists()
    assert "盘前主结论" in html_path.read_text(encoding="utf-8")
    assert published["artifact"]["artifact_family"] == "main_final_report"
    assert published["artifact"]["report_run_id"] == "report-run-final-1"
    assert store.registered[0]["metadata_json"]["artifact_file_path"] == str(html_path)
    assert store.registered[0]["metadata_json"]["quality_gate"]["ready_for_delivery"] is True
    assert store.registered[0]["metadata_json"]["support_summary_bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert store.registered[0]["metadata_json"]["chart_pack"]["chart_count"] == 3
    assert Path(tmp_path / "charts" / "chart_manifest.json").exists()
    qa_payload = json.loads(qa_path.read_text(encoding="utf-8"))
    assert qa_payload["ready_for_delivery"] is True
    assert qa_payload["summary"]["late_contract_mode"] == "full_close_package"
    eval_payload = json.loads(eval_path.read_text(encoding="utf-8"))
    assert eval_payload["artifact_type"] == "fsj_main_report_evaluation"
    assert eval_payload["summary"]["slot_scores"]["late"] >= 0
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_payload["qa"]["ready_for_delivery"] is True
    assert manifest_payload["evaluation"]["artifact_type"] == "fsj_main_report_evaluation"
    assert [bundle_id for bundle_id, _ in store.attached] == ["bundle-early", "bundle-late"]
    first_link = store.attached[0][1][0]
    assert first_link["artifact_locator_json"]["report_artifact_id"] == published["artifact"]["artifact_id"]
    assert first_link["artifact_uri"] == html_path.as_uri()


def test_main_report_artifact_publisher_builds_delivery_package_with_chat_ready_files(tmp_path: Path) -> None:
    stub = _StubAssemblyService(_assembled_sections())
    rendering_service = MainReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store, artifact_root=tmp_path)

    published = publisher.publish_delivery_package(
        business_date="2099-04-22",
        output_dir=tmp_path,
        include_empty=False,
        report_run_id="report-run-delivery-1",
        generated_at=datetime(2099, 4, 22, 9, 45, tzinfo=timezone.utc),
    )

    package_dir = Path(published["delivery_package_dir"])
    delivery_manifest_path = Path(published["delivery_manifest_path"])
    delivery_eval_path = Path(published["delivery_eval_path"])
    caption_path = Path(published["telegram_caption_path"])
    zip_path = Path(published["delivery_zip_path"])

    assert package_dir.exists()
    assert delivery_manifest_path.exists()
    assert delivery_eval_path.exists()
    assert caption_path.exists()
    assert zip_path.exists()
    assert Path(published["html_path"]).name in {path.name for path in package_dir.iterdir()}
    caption_text = caption_path.read_text(encoding="utf-8")
    assert "A股主报告交付包｜2099-04-22" in caption_text
    assert "状态：READY｜score=" in caption_text
    delivery_manifest = json.loads(delivery_manifest_path.read_text(encoding="utf-8"))
    assert delivery_manifest["artifact_type"] == "fsj_main_report_delivery_package"
    assert delivery_manifest["package_state"] == "ready"
    assert delivery_manifest["quality_gate"]["late_contract_mode"] == "full_close_package"
    assert delivery_manifest["quality_gate"]["qa_axes"]["policy"]["warning_count"] >= 1
    assert delivery_manifest["quality_gate"]["source_health"]["overall_status"] == "degraded"
    assert delivery_manifest["lineage"]["support_summary_bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert delivery_manifest["slot_evaluation"]["strongest_slot"] in {"early", "late"}
    assert delivery_manifest["support_summary_aggregate"]["domains"] == ["ai_tech", "macro"]
    assert delivery_manifest["support_summary_aggregate"]["bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert delivery_manifest["chart_pack"]["chart_count"] == 3
    assert delivery_manifest["chart_pack"]["ready_chart_count"] >= 0
    assert delivery_manifest["focus_module"]["focus_symbol_count"] == 3
    assert delivery_manifest["focus_module"]["chart_refs"][0]["chart_key"] == "key_focus_window"
    assert delivery_manifest["judgment_review_surface"]["judgment_item_count"] == 1
    assert delivery_manifest["judgment_mapping_ledger"]["mapping_count"] == 1
    assert delivery_manifest["judgment_mapping_ledger"]["retrospective_link_count"] == 1
    assert delivery_manifest["artifacts"]["evaluation"].endswith(".eval.json")
    assert delivery_manifest["artifacts"]["charts_dir"] == "charts"
    assert delivery_manifest["artifacts"]["chart_manifest"] == "charts/chart_manifest.json"
    assert delivery_manifest["artifacts"]["package_index"] == "package_index.json"
    assert delivery_manifest["artifacts"]["browse_readme"] == "BROWSE_PACKAGE.md"
    assert delivery_manifest["artifacts"]["judgment_review_surface"] == "judgment_review_surface.json"
    assert delivery_manifest["artifacts"]["judgment_mapping_ledger"] == "judgment_mapping_ledger.json"
    assert delivery_manifest["dispatch_advice"]["recommended_action"] == "send"
    assert published["dispatch_advice"]["artifact_id"] == published["artifact"]["artifact_id"]
    assert Path(published["package_index_path"]).exists()
    assert Path(published["package_browse_readme_path"]).exists()
    judgment_review_surface = json.loads((package_dir / "judgment_review_surface.json").read_text(encoding="utf-8"))
    assert judgment_review_surface["review_status"] == "pending_operator_item_review"
    assert judgment_review_surface["items"][0]["judgment_key"] == "judgment:early:mainline_plan"
    assert "focus_scope_alignment" in judgment_review_surface["items"][0]["review"]["review_focus"]
    assert judgment_review_surface["items"][0]["focus_module_refs"]["focus_symbol_count"] == 3
    assert judgment_review_surface["items"][0]["review"]["allowed_actions"] == ["approve", "needs_edit", "reject", "monitor"]
    judgment_mapping_ledger = json.loads((package_dir / "judgment_mapping_ledger.json").read_text(encoding="utf-8"))
    assert judgment_mapping_ledger["mappings"][0]["support_bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert judgment_mapping_ledger["mappings"][0]["focus_symbols"] == ["300024.SZ", "002031.SZ", "601138.SH"]
    assert judgment_mapping_ledger["mappings"][0]["customer_wording"] == "若竞价延续强化，则优先观察机器人主线确认。"
    assert judgment_mapping_ledger["retrospective_links"][0]["linked_prior_judgment_key"] == "judgment:early:mainline_plan"
    package_index = json.loads(Path(published["package_index_path"]).read_text(encoding="utf-8"))
    assert package_index["support_summary_aggregate"]["domains"] == ["ai_tech", "macro"]
    assert package_index["chart_pack"]["chart_count"] == 3
    assert package_index["focus_module"]["focus_symbol_count"] == 3
    assert delivery_manifest["quality_gate"]["source_health"]["degraded_slot_count"] == 1
    assert any(item["role"] == "delivery_manifest" and item["exists"] is True for item in package_index["files"])
    assert any(item["role"] == "charts_dir" and item["exists"] is True for item in package_index["files"])
    assert any(item["role"] == "judgment_review_surface" and item["exists"] is True for item in package_index["files"])
    assert any(item["role"] == "judgment_mapping_ledger" and item["exists"] is True for item in package_index["files"])
    browse_readme = Path(published["package_browse_readme_path"]).read_text(encoding="utf-8")
    assert "## Snapshot" in browse_readme
    assert "## Files" in browse_readme


def _assembled_support_section() -> dict:
    return {
        "artifact_type": "fsj_support_report_section",
        "artifact_version": "v1",
        "market": "a_share",
        "business_date": "2099-04-22",
        "agent_domain": "macro",
        "slot": "early",
        "section_key": "support_macro",
        "section_render_key": "support.macro.early",
        "title": "宏观 support｜盘前",
        "status": "ready",
        "bundle": {
            "bundle_id": "bundle-support-macro-early",
            "status": "active",
            "supersedes_bundle_id": None,
            "bundle_topic_key": "macro_early_support:2099-04-22",
            "producer": "ifa_data_platform.fsj.early_macro_support_producer",
            "producer_version": "phase1-macro-early-v1",
            "section_type": "support",
            "slot_run_id": "slot-run-support-macro-early",
            "replay_id": "replay-support-macro-early",
            "report_run_id": None,
            "updated_at": "2099-04-22T08:56:00+08:00",
        },
        "summary": "宏观背景偏稳定，更多作为边界 support。",
        "judgments": [
            {
                "object_key": "judgment:early:macro:risk_boundary",
                "statement": "宏观更多用于约束风险预算，不直接改写主线。",
                "judgment_action": "support",
                "confidence": "medium",
                "evidence_level": "E2",
            }
        ],
        "signals": [
            {
                "object_key": "signal:early:macro:stability",
                "statement": "利率/汇率未出现会破坏风险偏好的异常波动。",
                "signal_strength": "medium",
                "confidence": "medium",
                "evidence_level": "E2",
            }
        ],
        "facts": [
            {
                "object_key": "fact:early:macro:liquidity",
                "statement": "最新流动性与政策背景未见明显收紧。",
                "confidence": "high",
                "evidence_level": "E1",
            }
        ],
        "lineage": {
            "bundle": {"bundle_id": "bundle-support-macro-early", "payload_json": {"degrade": {"reason": "missing_background_support"}}},
            "objects": [],
            "edges": [],
            "evidence_links": [{"ref_key": "source:early:macro"}],
            "observed_records": [],
            "report_links": [],
        },
    }


class _StubSupportAssemblyService:
    def __init__(self, artifact: dict) -> None:
        self.artifact = artifact
        self.calls: list[tuple[str, str, str]] = []

    def assemble_support_section(self, *, business_date: str, agent_domain: str, slot: str) -> dict:
        self.calls.append((business_date, agent_domain, slot))
        return self.artifact


def test_support_report_html_renderer_emits_customer_profile_without_engineering_metadata_in_html() -> None:
    rendered = SupportReportHTMLRenderer().render(
        _assembled_support_section(),
        report_run_id="support-report-run-customer-1",
        artifact_uri="file:///tmp/support-macro-customer.html",
        generated_at=datetime(2099, 4, 22, 8, 0, tzinfo=timezone.utc),
        output_profile="customer",
    )

    assert "A股宏观简报｜盘前｜2099-04-22" in rendered["title"]
    assert "客户展示层仅保留摘要、关键信号与已知事实" in rendered["content"]
    assert "bundle-support-macro-early" not in rendered["content"]
    assert "phase1-macro-early-v1" not in rendered["content"]
    assert "slot-run-support-macro-early" not in rendered["content"]
    assert "source:early:macro" not in rendered["content"]
    assert rendered["metadata"]["output_profile"] == "customer"
    assert rendered["metadata"]["presentation_schema_version"] == "v1"


def test_support_report_html_renderer_emits_review_profile_with_internal_lineage_visible() -> None:
    rendered = SupportReportHTMLRenderer().render(
        _assembled_support_section(),
        report_run_id="support-report-run-review-1",
        artifact_uri="file:///tmp/support-macro-review.html",
        generated_at=datetime(2099, 4, 22, 8, 1, tzinfo=timezone.utc),
        output_profile="review",
    )

    assert "A股宏观审阅包｜盘前｜2099-04-22" in rendered["title"]
    assert rendered["metadata"]["output_profile"] == "review"
    assert rendered["metadata"]["presentation_schema_version"] is None
    assert "bundle-support-macro-early" in rendered["content"]
    assert "phase1-macro-early-v1" in rendered["content"]
    assert "source:early:macro" in rendered["content"]


def test_support_report_html_renderer_emits_standalone_support_html() -> None:
    rendered = SupportReportHTMLRenderer().render(
        _assembled_support_section(),
        report_run_id="support-report-run-1",
        artifact_uri="file:///tmp/support-macro-early.html",
        generated_at=datetime(2099, 4, 22, 8, 0, tzinfo=timezone.utc),
    )

    assert rendered["artifact_type"] == "fsj_support_report_html"
    assert "A股宏观 support 报告｜盘前｜2099-04-22" in rendered["title"]
    assert "support 独立成文" in rendered["content"]
    assert "MAIN 仅消费 concise support summary" in rendered["content"]
    assert rendered["metadata"]["agent_domain"] == "macro"
    assert rendered["metadata"]["section_render_key"] == "support.macro.early"
    assert rendered["report_links"][0]["bundle_id"] == "bundle-support-macro-early"
    assert rendered["report_links"][0]["section_render_key"] == "support.macro.early"


def test_support_report_qa_evaluator_surfaces_degraded_source_health_without_blocking_delivery() -> None:
    assembled = _assembled_support_section()
    rendered = SupportReportHTMLRenderer().render(
        assembled,
        report_run_id="support-report-run-qa-1",
        artifact_uri="file:///tmp/support-macro-early-qa.html",
        generated_at=datetime(2099, 4, 22, 8, 0, tzinfo=timezone.utc),
    )

    qa = SupportReportQAEvaluator().evaluate(assembled, rendered)

    assert qa["ready_for_delivery"] is True
    assert qa["summary"]["source_health"]["overall_status"] == "degraded"
    assert qa["summary"]["source_health"]["degrade_reason"] == "missing_background_support"
    assert qa["summary"]["qa_axes"]["editorial"]["ready"] is True
    assert qa["summary"]["qa_axes"]["leakage"]["ready"] is True
    assert qa["summary"]["customer_report_readiness"]["ready"] is True
    assert any(issue["code"] == "support_source_health_degraded" for issue in qa["issues"])


def test_support_report_rendering_service_delegates_assembly_then_render() -> None:
    stub = _StubSupportAssemblyService(_assembled_support_section())
    service = SupportReportRenderingService(assembly_service=stub)

    rendered = service.render_support_report_html(
        business_date="2099-04-22",
        agent_domain="macro",
        slot="early",
        report_run_id="support-report-run-2",
        artifact_uri="file:///tmp/support-macro-early.html",
    )

    assert stub.calls == [("2099-04-22", "macro", "early")]
    assert rendered["metadata"]["artifact_uri"] == "file:///tmp/support-macro-early.html"


def test_support_report_artifact_publisher_writes_html_manifest_and_linkage(tmp_path: Path) -> None:
    stub = _StubSupportAssemblyService(_assembled_support_section())
    rendering_service = SupportReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = SupportReportArtifactPublishingService(rendering_service=rendering_service, store=store, artifact_root=tmp_path)

    published = publisher.publish_support_report_html(
        business_date="2099-04-22",
        agent_domain="macro",
        slot="early",
        output_dir=tmp_path,
        report_run_id="support-report-run-3",
        generated_at=datetime(2099, 4, 22, 9, 0, tzinfo=timezone.utc),
    )

    html_path = Path(published["html_path"])
    manifest_path = Path(published["manifest_path"])
    assert html_path.exists()
    assert manifest_path.exists()
    assert "宏观 support" in html_path.read_text(encoding="utf-8")
    assert published["artifact"]["artifact_family"] == "support_domain_report"
    assert published["artifact"]["agent_domain"] == "macro"
    assert store.registered[0]["metadata_json"]["section_render_key"] == "support.macro.early"
    assert [bundle_id for bundle_id, _ in store.attached] == ["bundle-support-macro-early"]
    first_link = store.attached[0][1][0]
    assert first_link["artifact_locator_json"]["report_artifact_id"] == published["artifact"]["artifact_id"]
    assert first_link["section_render_key"] == "support.macro.early"


def test_support_report_qa_evaluator_accepts_ready_support_html() -> None:
    assembled = _assembled_support_section()
    rendered = SupportReportHTMLRenderer().render(
        assembled,
        report_run_id="support-report-run-qa",
        artifact_uri="file:///tmp/support-macro-early.html",
        generated_at=datetime(2099, 4, 22, 9, 0, tzinfo=timezone.utc),
    )

    qa = SupportReportQAEvaluator().evaluate(assembled, rendered)

    assert qa["artifact_type"] == "fsj_support_report_qa"
    assert qa["ready_for_delivery"] is True
    assert qa["summary"]["agent_domain"] == "macro"
    assert qa["summary"]["source_health"]["overall_status"] == "degraded"
    assert qa["summary"]["slot"] == "early"
    assert qa["summary"]["report_link_count"] == 1


def test_support_report_artifact_publisher_builds_delivery_package(tmp_path: Path) -> None:
    stub = _StubSupportAssemblyService(_assembled_support_section())
    rendering_service = SupportReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = SupportReportArtifactPublishingService(rendering_service=rendering_service, store=store, artifact_root=tmp_path)

    published = publisher.publish_delivery_package(
        business_date="2099-04-22",
        agent_domain="macro",
        slot="early",
        output_dir=tmp_path,
        report_run_id="support-report-run-4",
        generated_at=datetime(2099, 4, 22, 10, 0, tzinfo=timezone.utc),
    )

    package_dir = Path(published["delivery_package_dir"])
    delivery_manifest = json.loads(Path(published["delivery_manifest_path"]).read_text(encoding="utf-8"))
    package_index = json.loads(Path(published["package_index_path"]).read_text(encoding="utf-8"))
    operator_summary = Path(published["operator_summary_path"]).read_text(encoding="utf-8")

    assert package_dir.exists()
    assert Path(published["qa_path"]).exists()
    assert Path(published["delivery_zip_path"]).exists()
    assert delivery_manifest["artifact_type"] == "fsj_support_report_delivery_package"
    assert delivery_manifest["package_state"] == "ready"
    assert delivery_manifest["quality_gate"]["score"] == published["qa"]["score"]
    assert delivery_manifest["quality_gate"]["source_health"]["overall_status"] == "degraded"
    assert delivery_manifest["lineage"]["bundle_id"] == "bundle-support-macro-early"
    assert package_index["artifact_type"] == "fsj_support_report_delivery_package_index"
    assert any(item["role"] == "delivery_manifest" and item["exists"] is True for item in package_index["files"])
    assert "Support delivery package｜2099-04-22｜macro｜early" in operator_summary


def test_main_report_artifact_delivery_package_marks_blocked_when_qa_fails(tmp_path: Path) -> None:
    assembled = _assembled_sections()
    assembled["sections"][1]["signals"][0]["attributes_json"]["contract_mode"] = "historical_only"
    stub = _StubAssemblyService(assembled)
    rendering_service = MainReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store, artifact_root=tmp_path)

    published = publisher.publish_delivery_package(
        business_date="2099-04-22",
        output_dir=tmp_path,
        include_empty=False,
        report_run_id="report-run-delivery-blocked",
        generated_at=datetime(2099, 4, 22, 9, 50, tzinfo=timezone.utc),
    )

    delivery_manifest = json.loads(Path(published["delivery_manifest_path"]).read_text(encoding="utf-8"))
    caption_text = Path(published["telegram_caption_path"]).read_text(encoding="utf-8")
    assert published["evaluation"]["ready_for_delivery"] is False
    assert delivery_manifest["package_state"] == "blocked"
    assert delivery_manifest["ready_for_delivery"] is False
    assert delivery_manifest["dispatch_advice"]["recommended_action"] == "hold"
    assert "状态：BLOCKED｜score=" in caption_text


def test_main_report_delivery_dispatch_helper_prefers_ready_best_candidate() -> None:
    helper = MainReportDeliveryDispatchHelper()
    ready_late = {
        "artifact": {"artifact_id": "artifact-ready-late", "report_run_id": "run-ready-late", "business_date": "2099-04-22"},
        "delivery_package_dir": "/tmp/ready-late",
        "delivery_manifest_path": "/tmp/ready-late/delivery_manifest.json",
        "delivery_zip_path": "/tmp/ready-late.zip",
        "delivery_manifest": {
            "artifact_id": "artifact-ready-late",
            "business_date": "2099-04-22",
            "report_run_id": "run-ready-late",
            "package_state": "ready",
            "ready_for_delivery": True,
            "quality_gate": {"score": 88, "blocker_count": 0, "warning_count": 2, "late_contract_mode": "full_close_package"},
            "slot_evaluation": {"strongest_slot": "late", "weakest_slot": "early", "slot_scores": {"early": 70, "mid": 80, "late": 92}, "average_slot_score": 80.7, "slot_score_span": 22},
        },
        "report_evaluation": {"summary": {"slot_scores": {"early": 70, "mid": 80, "late": 92}, "average_slot_score": 80.7, "slot_score_span": 22, "strongest_slot": "late", "weakest_slot": "early"}},
    }
    blocked_mid = {
        "artifact": {"artifact_id": "artifact-blocked-mid", "report_run_id": "run-blocked-mid", "business_date": "2099-04-22"},
        "delivery_package_dir": "/tmp/blocked-mid",
        "delivery_manifest_path": "/tmp/blocked-mid/delivery_manifest.json",
        "delivery_zip_path": "/tmp/blocked-mid.zip",
        "delivery_manifest": {
            "artifact_id": "artifact-blocked-mid",
            "business_date": "2099-04-22",
            "report_run_id": "run-blocked-mid",
            "package_state": "blocked",
            "ready_for_delivery": False,
            "quality_gate": {"score": 96, "blocker_count": 2, "warning_count": 0, "late_contract_mode": "historical_only"},
            "slot_evaluation": {"strongest_slot": "mid", "weakest_slot": "early", "slot_scores": {"early": 80, "mid": 98, "late": 40}, "average_slot_score": 72.7, "slot_score_span": 58},
        },
        "report_evaluation": {"summary": {"slot_scores": {"early": 80, "mid": 98, "late": 40}, "average_slot_score": 72.7, "slot_score_span": 58, "strongest_slot": "mid", "weakest_slot": "early"}},
    }

    decision = helper.choose_best([blocked_mid, ready_late])

    assert decision["recommended_action"] == "send"
    assert decision["selected"]["artifact_id"] == "artifact-ready-late"
    assert decision["ready_candidate_count"] == 1
    assert decision["alternatives"][0]["artifact_id"] == "artifact-blocked-mid"
    assert decision["ranked_candidates"][0]["artifact_id"] == "artifact-ready-late"
    assert decision["ranked_candidates"][1]["delta_vs_selected"]["qa_score_delta"] == 8
    assert decision["ranked_candidates"][1]["delta_vs_selected"]["ready_state_change"] == "False->True"


def test_main_report_delivery_dispatch_helper_loads_and_discovers_delivery_packages(tmp_path: Path) -> None:
    helper = MainReportDeliveryDispatchHelper()
    root = tmp_path / "out"
    package = root / "a_share_main_report_delivery_2099-04-22_20990422T095700Z_artifact-ready"
    package.mkdir(parents=True)
    (package / "telegram_caption.txt").write_text("caption", encoding="utf-8")
    (root / f"{package.name}.zip").write_text("zip", encoding="utf-8")
    (package / "artifact.eval.json").write_text(json.dumps({"summary": {"slot_scores": {"early": 72, "mid": 84, "late": 95}, "average_slot_score": 83.7, "slot_score_span": 23, "strongest_slot": "late", "weakest_slot": "early"}}), encoding="utf-8")
    (package / "delivery_manifest.json").write_text(json.dumps({
        "artifact_id": "artifact-ready",
        "business_date": "2099-04-22",
        "report_run_id": "run-ready",
        "artifact_family": "a_share_main",
        "package_state": "ready",
        "ready_for_delivery": True,
        "quality_gate": {"score": 91, "blocker_count": 0, "warning_count": 1, "late_contract_mode": "full_close_package"},
        "slot_evaluation": {"strongest_slot": "late", "weakest_slot": "early", "slot_scores": {"early": 72, "mid": 84, "late": 95}},
        "artifacts": {"evaluation": "artifact.eval.json", "telegram_caption": "telegram_caption.txt"},
    }), encoding="utf-8")

    loaded = helper.load_published_candidate(package)
    discovered = helper.discover_published_candidates(root, business_date="2099-04-22")

    assert loaded["delivery_manifest"]["artifact_id"] == "artifact-ready"
    assert loaded["telegram_caption_path"].endswith("telegram_caption.txt")
    assert loaded["delivery_zip_path"].endswith("artifact-ready.zip")
    assert loaded["report_evaluation"]["summary"]["strongest_slot"] == "late"
    assert loaded["package_index"] == {}
    assert len(discovered) == 1
    assert discovered[0]["delivery_manifest_path"].endswith("delivery_manifest.json")


def test_main_report_delivery_dispatch_helper_prefers_db_surfaces_before_filesystem_scan(tmp_path: Path) -> None:
    helper = MainReportDeliveryDispatchHelper()
    root = tmp_path / "out"
    package = root / "a_share_main_report_delivery_2099-04-22_20990422T095700Z_artifact-ready"
    package.mkdir(parents=True)
    manifest_path = package / "delivery_manifest.json"
    manifest_path.write_text(json.dumps({
        "artifact_id": "artifact-fs",
        "business_date": "2099-04-22",
        "report_run_id": "run-fs",
        "artifact_family": "a_share_main",
        "package_state": "ready",
        "ready_for_delivery": True,
        "quality_gate": {"score": 88},
    }), encoding="utf-8")

    class _StubStore:
        pass

    helper.list_db_delivery_candidates = lambda *, business_date, store=None, limit=8: [
        {
            "artifact": {"artifact_id": "artifact-db", "business_date": business_date, "artifact_family": "main_final_report"},
            "delivery_manifest_path": str(manifest_path.resolve()),
            "delivery_manifest": {"artifact_id": "artifact-db", "business_date": business_date},
            "source": "db_active_delivery_surface",
        },
        {
            "artifact": {"artifact_id": "artifact-db-history", "business_date": business_date, "artifact_family": "main_final_report"},
            "delivery_manifest_path": str((root / "db-history" / "delivery_manifest.json").resolve()),
            "delivery_manifest": {"artifact_id": "artifact-db-history", "business_date": business_date},
            "source": "db_delivery_history_surface",
        },
    ]

    discovered = helper.discover_published_candidates(
        root,
        business_date="2099-04-22",
        limit=5,
        store=_StubStore(),
        prefer_db_active=True,
    )

    assert len(discovered) == 2
    assert [item["artifact"]["artifact_id"] for item in discovered] == ["artifact-db", "artifact-db-history"]
    assert discovered[0]["source"] == "db_active_delivery_surface"
    assert discovered[1]["source"] == "db_delivery_history_surface"


def test_main_report_delivery_dispatch_helper_falls_back_to_send_review_for_best_available_provisional_candidate() -> None:
    helper = MainReportDeliveryDispatchHelper()
    provisional = {
        "artifact": {"artifact_id": "artifact-provisional", "report_run_id": "run-provisional", "business_date": "2099-04-22"},
        "delivery_package_dir": "/tmp/provisional",
        "delivery_manifest_path": "/tmp/provisional/delivery_manifest.json",
        "delivery_zip_path": "/tmp/provisional.zip",
        "delivery_manifest": {
            "artifact_id": "artifact-provisional",
            "business_date": "2099-04-22",
            "report_run_id": "run-provisional",
            "package_state": "blocked",
            "ready_for_delivery": False,
            "quality_gate": {"score": 79, "blocker_count": 1, "warning_count": 1, "late_contract_mode": "provisional_close_only"},
            "slot_evaluation": {"strongest_slot": "late", "weakest_slot": "early", "slot_scores": {"early": 65, "mid": 72, "late": 90}},
        },
        "report_evaluation": {"summary": {"slot_scores": {"early": 65, "mid": 72, "late": 90}, "average_slot_score": 75.7, "slot_score_span": 25, "strongest_slot": "late", "weakest_slot": "early"}},
    }

    decision = helper.choose_best([provisional])
    comparison = helper.build_candidate_comparison([provisional], current_artifact_id="artifact-provisional")

    assert decision["recommended_action"] == "send_review"
    assert decision["selected"]["artifact_id"] == "artifact-provisional"
    assert decision["selection_reason"] == "best_available_candidate provisional_close_only_requires_review"
    assert comparison["selected_artifact_id"] == "artifact-provisional"
    assert comparison["current_vs_selected"]["delta_current_vs_selected"]["qa_score_delta"] == 0


def test_main_report_artifact_publisher_requires_explicit_non_live_artifact_root_under_pytest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp")

    with pytest.raises(LiveIsolationError, match="artifact_root must be set explicitly"):
        MainReportArtifactPublishingService(
            rendering_service=MainReportRenderingService(assembly_service=_StubAssemblyService(_assembled_sections())),
            store=_StubStore(),
        )

    publisher = MainReportArtifactPublishingService(
        rendering_service=MainReportRenderingService(assembly_service=_StubAssemblyService(_assembled_sections())),
        store=_StubStore(),
        artifact_root=tmp_path,
    )
    escaped_output = tmp_path.parent / "escaped-output"

    with pytest.raises(LiveIsolationError, match="escapes explicit artifact_root contract"):
        publisher.publish_main_report_html(
            business_date="2099-04-22",
            output_dir=escaped_output,
            report_run_id="report-run-escaped",
            generated_at=datetime(2099, 4, 22, 9, 30, tzinfo=timezone.utc),
        )


def test_support_report_artifact_publisher_requires_explicit_non_live_artifact_root_under_pytest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp")

    with pytest.raises(LiveIsolationError, match="artifact_root must be set explicitly"):
        SupportReportArtifactPublishingService(
            rendering_service=SupportReportRenderingService(assembly_service=_StubSupportAssemblyService(_assembled_support_section())),
            store=_StubStore(),
        )

    publisher = SupportReportArtifactPublishingService(
        rendering_service=SupportReportRenderingService(assembly_service=_StubSupportAssemblyService(_assembled_support_section())),
        store=_StubStore(),
        artifact_root=tmp_path,
    )
    escaped_output = tmp_path.parent / "escaped-support-output"

    with pytest.raises(LiveIsolationError, match="escapes explicit artifact_root contract"):
        publisher.publish_support_report_html(
            business_date="2099-04-22",
            agent_domain="macro",
            slot="early",
            output_dir=escaped_output,
            report_run_id="support-report-run-escaped",
            generated_at=datetime(2099, 4, 22, 9, 0, tzinfo=timezone.utc),
        )
