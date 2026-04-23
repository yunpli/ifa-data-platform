from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import json

from ifa_data_platform.fsj.report_dispatch import MainReportDeliveryDispatchHelper
from ifa_data_platform.fsj.report_quality import MainReportQAEvaluator
from ifa_data_platform.fsj.report_rendering import (
    MainReportArtifactPublishingService,
    MainReportHTMLRenderer,
    MainReportRenderingService,
    SupportReportArtifactPublishingService,
    SupportReportHTMLRenderer,
    SupportReportRenderingService,
)


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
                        "object_key": "judgment:early:main",
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
                            "report_links": [],
                            "evidence_links": [
                                {"ref_key": "source:early:macro"},
                            ],
                        },
                    },
                ],
                "lineage": {
                    "bundle": {"bundle_id": "bundle-early"},
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
                    "bundle": {"bundle_id": "bundle-late"},
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
    assert rendered["metadata"]["support_summary_domains"] == ["ai_tech", "macro"]
    assert rendered["metadata"]["support_summary_bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert rendered["metadata"]["existing_report_links"][0]["artifact_uri"] == "file:///tmp/earlier-early.md"
    assert rendered["metadata"]["existing_report_links"][1]["artifact_uri"] == "file:///tmp/support-ai-early.html"
    assert [link["bundle_id"] for link in rendered["report_links"]] == ["bundle-early", "bundle-late"]
    assert all(link["artifact_type"] == "html" for link in rendered["report_links"])
    assert rendered["report_links"][0]["section_render_key"] == "main.pre_open"


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
    assert evaluation["summary"]["blocker_count"] == 0
    assert evaluation["summary"]["warning_count"] >= 1
    assert any(issue["code"] == "slot_missing" and issue.get("slot") == "mid" for issue in evaluation["issues"])


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
    assert any(issue["code"] == "late_historical_only" for issue in evaluation["issues"])


def test_main_report_artifact_publisher_writes_html_manifest_and_qa_with_report_wiring(tmp_path: Path) -> None:
    stub = _StubAssemblyService(_assembled_sections())
    rendering_service = MainReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store)

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
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store)

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
    assert delivery_manifest["lineage"]["support_summary_bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert delivery_manifest["slot_evaluation"]["strongest_slot"] in {"early", "late"}
    assert delivery_manifest["support_summary_aggregate"]["domains"] == ["ai_tech", "macro"]
    assert delivery_manifest["support_summary_aggregate"]["bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert delivery_manifest["artifacts"]["evaluation"].endswith(".eval.json")
    assert delivery_manifest["artifacts"]["package_index"] == "package_index.json"
    assert delivery_manifest["artifacts"]["browse_readme"] == "BROWSE_PACKAGE.md"
    assert delivery_manifest["dispatch_advice"]["recommended_action"] == "send"
    assert published["dispatch_advice"]["artifact_id"] == published["artifact"]["artifact_id"]
    assert Path(published["package_index_path"]).exists()
    assert Path(published["package_browse_readme_path"]).exists()
    package_index = json.loads(Path(published["package_index_path"]).read_text(encoding="utf-8"))
    assert package_index["support_summary_aggregate"]["domains"] == ["ai_tech", "macro"]
    assert any(item["role"] == "delivery_manifest" and item["exists"] is True for item in package_index["files"])
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
            "bundle": {"bundle_id": "bundle-support-macro-early"},
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
    publisher = SupportReportArtifactPublishingService(rendering_service=rendering_service, store=store)

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


def test_main_report_artifact_delivery_package_marks_blocked_when_qa_fails(tmp_path: Path) -> None:
    assembled = _assembled_sections()
    assembled["sections"][1]["signals"][0]["attributes_json"]["contract_mode"] = "historical_only"
    stub = _StubAssemblyService(assembled)
    rendering_service = MainReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store)

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

    assert decision["recommended_action"] == "send_review"
    assert decision["selected"]["artifact_id"] == "artifact-provisional"
    assert decision["selection_reason"] == "best_available_candidate provisional_close_only_requires_review"
