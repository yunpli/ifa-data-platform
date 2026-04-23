from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import json

from ifa_data_platform.fsj.report_orchestration import MainReportMorningDeliveryOrchestrator
from ifa_data_platform.fsj.report_rendering import MainReportArtifactPublishingService, MainReportRenderingService


def _assembled_sections() -> dict:
    return {
        "artifact_type": "fsj_main_report_sections",
        "artifact_version": "v2",
        "market": "a_share",
        "business_date": "2099-04-22",
        "agent_domain": "main",
        "section_count": 2,
        "support_summary_domains": ["macro"],
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
                "judgments": [{"object_key": "judgment:early:main", "statement": "若竞价延续强化，则优先观察机器人主线确认。", "judgment_action": "validate", "confidence": "medium", "evidence_level": "E2"}],
                "signals": [{"object_key": "signal:early:confirm", "statement": "竞价成交额与封单强度需同步抬升。", "signal_strength": "medium", "confidence": "medium", "evidence_level": "E2"}],
                "facts": [{"object_key": "fact:early:robotics", "statement": "隔夜催化继续集中在机器人方向。", "confidence": "high", "evidence_level": "E1"}],
                "support_summaries": [{
                    "bundle_id": "bundle-support-macro-early",
                    "slot": "early",
                    "agent_domain": "macro",
                    "section_key": "support_macro",
                    "bundle_topic_key": "macro_early_support:2099-04-22",
                    "status": "active",
                    "summary": "宏观背景偏稳定。",
                    "producer": "ifa_data_platform.fsj.early_macro_support_producer",
                    "producer_version": "phase1-macro-early-v1",
                    "slot_run_id": "slot-run-early-support-macro",
                    "replay_id": "replay-early-support-macro",
                    "report_run_id": None,
                    "updated_at": "2099-04-22T08:56:00+08:00",
                    "lineage": {"report_links": [], "evidence_links": [{"ref_key": "source:early:macro"}]},
                }],
                "lineage": {
                    "bundle": {"bundle_id": "bundle-early"},
                    "objects": [],
                    "edges": [],
                    "evidence_links": [{"ref_key": "source:early:robotics"}],
                    "observed_records": [],
                    "report_links": [],
                    "support_bundle_ids": ["bundle-support-macro-early"],
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
                "signals": [{
                    "object_key": "signal:late:close_package_state",
                    "statement": "same-day final market packet ready，收盘 close package 可用。",
                    "signal_strength": "high",
                    "confidence": "high",
                    "evidence_level": "E1",
                    "attributes_json": {"contract_mode": "full_close_package", "provisional_close_only": False},
                }],
                "facts": [],
                "support_summaries": [],
                "lineage": {"bundle": {"bundle_id": "bundle-late"}, "objects": [], "edges": [], "evidence_links": [], "observed_records": [], "report_links": [], "support_bundle_ids": []},
            },
        ],
    }


class _StubAssemblyService:
    def __init__(self, artifact: dict):
        self.artifact = artifact
        self.calls: list[tuple[str, bool]] = []

    def assemble_main_sections(self, *, business_date: str, include_empty: bool = False) -> dict:
        self.calls.append((business_date, include_empty))
        return self.artifact


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


def _build_orchestrator() -> MainReportMorningDeliveryOrchestrator:
    stub = _StubAssemblyService(_assembled_sections())
    rendering_service = MainReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store)
    return MainReportMorningDeliveryOrchestrator(publisher=publisher)


def test_main_report_morning_delivery_workflow_emits_send_and_review_manifests(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator()

    result = orchestrator.run_workflow(
        business_date="2099-04-22",
        output_dir=tmp_path,
        report_run_id="report-run-morning-ready",
        generated_at=datetime(2099, 4, 22, 9, 55, tzinfo=timezone.utc),
    )

    workflow = json.loads(Path(result["workflow_manifest_path"]).read_text(encoding="utf-8"))
    send_manifest = json.loads(Path(result["send_manifest_path"]).read_text(encoding="utf-8"))
    review_manifest = json.loads(Path(result["review_manifest_path"]).read_text(encoding="utf-8"))
    operator_summary = Path(result["operator_summary_path"]).read_text(encoding="utf-8")

    assert result["dispatch_decision"]["recommended_action"] == "send"
    assert workflow["workflow_state"] == "ready_to_send"
    assert send_manifest["recommended_action"] == "send"
    assert send_manifest["workflow_state"] == "ready_to_send"
    assert review_manifest["blocking_items"] == []
    assert any(item["item"] == "quality_gate_ready_for_delivery" and item["status"] == "pass" for item in review_manifest["checklist"])
    assert "recommended_action=send" in operator_summary


def test_main_report_morning_delivery_workflow_marks_review_required_for_provisional_candidate(tmp_path: Path) -> None:
    assembled = _assembled_sections()
    assembled["sections"][1]["signals"][0]["attributes_json"]["contract_mode"] = "provisional_close_only"
    stub = _StubAssemblyService(assembled)
    rendering_service = MainReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store)
    orchestrator = MainReportMorningDeliveryOrchestrator(publisher=publisher)

    result = orchestrator.run_workflow(
        business_date="2099-04-22",
        output_dir=tmp_path,
        report_run_id="report-run-morning-review",
        generated_at=datetime(2099, 4, 22, 9, 56, tzinfo=timezone.utc),
    )

    workflow = json.loads(Path(result["workflow_manifest_path"]).read_text(encoding="utf-8"))
    review_manifest = json.loads(Path(result["review_manifest_path"]).read_text(encoding="utf-8"))

    assert result["dispatch_decision"]["recommended_action"] == "send"
    assert workflow["recommended_action"] == "send_review"
    assert workflow["dispatch_recommended_action"] == "send"
    assert workflow["workflow_state"] == "review_required"
    assert any(item["item"] == "late_contract_mode" and item["status"] == "warn" for item in review_manifest["checklist"])
    assert review_manifest["warning_items"]


def test_main_report_morning_delivery_workflow_marks_superseded_when_better_ready_candidate_exists(tmp_path: Path) -> None:
    orchestrator = _build_orchestrator()
    better_ready = {
        "artifact": {"artifact_id": "artifact-better-ready", "report_run_id": "run-better-ready", "business_date": "2099-04-22"},
        "delivery_package_dir": "/tmp/better-ready",
        "delivery_manifest_path": "/tmp/better-ready/delivery_manifest.json",
        "delivery_zip_path": "/tmp/better-ready.zip",
        "delivery_manifest": {
            "artifact_id": "artifact-better-ready",
            "business_date": "2099-04-22",
            "report_run_id": "run-better-ready",
            "package_state": "ready",
            "ready_for_delivery": True,
            "quality_gate": {"score": 99, "blocker_count": 0, "warning_count": 0, "late_contract_mode": "full_close_package"},
            "slot_evaluation": {"strongest_slot": "late", "weakest_slot": "early", "slot_scores": {"early": 88, "mid": 90, "late": 99}, "average_slot_score": 92.3, "slot_score_span": 11},
        },
        "report_evaluation": {"summary": {"slot_scores": {"early": 88, "mid": 90, "late": 99}, "average_slot_score": 92.3, "slot_score_span": 11, "strongest_slot": "late", "weakest_slot": "early"}},
    }

    result = orchestrator.run_workflow(
        business_date="2099-04-22",
        output_dir=tmp_path,
        report_run_id="report-run-current",
        generated_at=datetime(2099, 4, 22, 9, 57, tzinfo=timezone.utc),
        comparison_candidates=[better_ready],
    )

    workflow = json.loads(Path(result["workflow_manifest_path"]).read_text(encoding="utf-8"))
    send_manifest = json.loads(Path(result["send_manifest_path"]).read_text(encoding="utf-8"))
    review_manifest = json.loads(Path(result["review_manifest_path"]).read_text(encoding="utf-8"))

    assert result["dispatch_decision"]["selected"]["artifact_id"] == "artifact-better-ready"
    assert workflow["workflow_state"] == "superseded_by_better_candidate"
    assert send_manifest["selected_is_current"] is False
    assert any(item["item"] == "confirm_selected_candidate" and item["status"] == "warn" for item in review_manifest["checklist"])
