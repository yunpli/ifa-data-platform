from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj.report_rendering import MainReportArtifactPublishingService, MainReportHTMLRenderer, MainReportRenderingService


def _assembled_sections() -> dict:
    return {
        "artifact_type": "fsj_main_report_sections",
        "artifact_version": "v1",
        "market": "a_share",
        "business_date": "2099-04-22",
        "agent_domain": "main",
        "section_count": 2,
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
                "signals": [],
                "facts": [],
                "lineage": {
                    "bundle": {"bundle_id": "bundle-late"},
                    "objects": [],
                    "edges": [],
                    "evidence_links": [],
                    "observed_records": [],
                    "report_links": [],
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
    assert rendered["render_format"] == "html"
    assert rendered["content_type"] == "text/html"
    assert "A股主报告｜2099-04-22" in rendered["title"]
    assert "盘前主结论" in rendered["content"]
    assert "收盘主结论" in rendered["content"]
    assert "phase1-main-early-v1" in rendered["content"]
    assert "source:early:robotics" in rendered["content"]
    assert rendered["metadata"]["source_artifact_type"] == "fsj_main_report_sections"
    assert rendered["metadata"]["existing_report_links"][0]["artifact_uri"] == "file:///tmp/earlier-early.md"
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


def test_main_report_artifact_publisher_writes_html_and_manifest_with_report_wiring(tmp_path: Path) -> None:
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
    manifest_path = Path(published["manifest_path"])
    assert html_path.exists()
    assert manifest_path.exists()
    assert "盘前主结论" in html_path.read_text(encoding="utf-8")
    assert published["artifact"]["artifact_family"] == "main_final_report"
    assert published["artifact"]["report_run_id"] == "report-run-final-1"
    assert store.registered[0]["metadata_json"]["artifact_file_path"] == str(html_path)
    assert [bundle_id for bundle_id, _ in store.attached] == ["bundle-early", "bundle-late"]
    first_link = store.attached[0][1][0]
    assert first_link["artifact_locator_json"]["report_artifact_id"] == published["artifact"]["artifact_id"]
    assert first_link["artifact_uri"] == html_path.as_uri()
