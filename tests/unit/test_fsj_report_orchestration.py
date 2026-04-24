from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import json
import pytest

from ifa_data_platform.fsj.report_orchestration import (
    MainReportMorningDeliveryOrchestrator,
    build_main_report_morning_delivery_orchestrator,
)
from ifa_data_platform.fsj.report_rendering import MainReportArtifactPublishingService, MainReportRenderingService
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
                    "lineage": {"bundle": {"payload_json": {"degrade": {"reason": "missing_background_support"}}}, "report_links": [], "evidence_links": [{"ref_key": "source:early:macro"}]},
                }],
                "lineage": {
                    "bundle": {"bundle_id": "bundle-early", "payload_json": {"degrade": {"degrade_reason": "missing_preopen_high_layer", "contract_mode": "candidate_only", "completeness_label": "sparse"}}},
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
                "lineage": {"bundle": {"bundle_id": "bundle-late", "payload_json": {"degrade": {}}}, "objects": [], "edges": [], "evidence_links": [], "observed_records": [], "report_links": [], "support_bundle_ids": []},
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
        self.persisted_workflow_linkages: list[tuple[str, dict]] = []

    def register_report_artifact(self, payload: dict) -> dict:
        self.registered.append(payload)
        return {**payload, "status": payload["status"]}

    def attach_report_links(self, bundle_id: str, report_links: list[dict]) -> list[dict]:
        self.attached.append((bundle_id, report_links))
        return report_links

    def persist_report_workflow_linkage(self, artifact_id: str, workflow_linkage: dict) -> dict:
        self.persisted_workflow_linkages.append((artifact_id, workflow_linkage))
        return {"artifact_id": artifact_id, "metadata_json": {"workflow_linkage": workflow_linkage}}


def _build_orchestrator(artifact_root: Path) -> tuple[MainReportMorningDeliveryOrchestrator, _StubStore]:
    stub = _StubAssemblyService(_assembled_sections())
    store = _StubStore()
    orchestrator = build_main_report_morning_delivery_orchestrator(
        assembly_service=stub,
        store=store,
        artifact_root=artifact_root,
    )
    return orchestrator, store


def test_main_report_orchestration_factory_requires_explicit_non_live_artifact_root_under_pytest() -> None:
    with pytest.raises(LiveIsolationError, match="artifact_root must be set explicitly"):
        build_main_report_morning_delivery_orchestrator(
            assembly_service=_StubAssemblyService(_assembled_sections()),
            store=_StubStore(),
            artifact_root=None,
        )


def test_main_report_morning_delivery_workflow_emits_send_and_review_manifests(tmp_path: Path) -> None:
    orchestrator, store = _build_orchestrator(tmp_path)

    result = orchestrator.run_workflow(
        business_date="2099-04-22",
        output_dir=tmp_path,
        report_run_id="report-run-morning-ready",
        generated_at=datetime(2099, 4, 22, 9, 55, tzinfo=timezone.utc),
    )

    workflow = json.loads(Path(result["workflow_manifest_path"]).read_text(encoding="utf-8"))
    send_manifest = json.loads(Path(result["send_manifest_path"]).read_text(encoding="utf-8"))
    review_manifest = json.loads(Path(result["review_manifest_path"]).read_text(encoding="utf-8"))
    operator_review_bundle = json.loads(Path(result["operator_review_bundle_path"]).read_text(encoding="utf-8"))
    operator_review_readme = Path(result["operator_review_readme_path"]).read_text(encoding="utf-8")
    operator_summary = Path(result["operator_summary_path"]).read_text(encoding="utf-8")

    assert result["dispatch_decision"]["recommended_action"] == "send"
    assert workflow["workflow_state"] == "ready_to_send"
    assert send_manifest["recommended_action"] == "send"
    assert send_manifest["workflow_state"] == "ready_to_send"
    assert send_manifest["next_step"] == "send_selected_package_to_primary_channel"
    assert send_manifest["send_blockers"] == []
    assert workflow["selected_handoff"]["selected_is_current"] is True
    assert review_manifest["blocking_items"] == []
    assert any(item["item"] == "quality_gate_ready_for_delivery" and item["status"] == "pass" for item in review_manifest["checklist"])
    assert any(item["item"] == "source_health_overall_status" and item["status"] == "warn" for item in review_manifest["checklist"])
    assert operator_review_bundle["recommended_action"] == "send"
    assert operator_review_bundle["candidate_overview"]["candidate_count"] == 1
    assert operator_review_bundle["operator_go_no_go"]["decision"] == "GO"
    assert operator_review_bundle["operator_go_no_go"]["artifact_integrity_ok"] is True
    assert any(item["artifact"] == "html" and item["exists"] is True for item in operator_review_bundle["artifact_checks"])
    assert workflow["package_artifacts"]["operator_review_bundle"].endswith("operator_review_bundle.json")
    assert workflow["package_artifacts"]["operator_review_readme"].endswith("OPERATOR_REVIEW.md")
    assert workflow["package_artifacts"]["candidate_comparison"].endswith("candidate_comparison.json")
    assert workflow["package_artifacts"]["package_index"].endswith("package_index.json")
    assert workflow["package_artifacts"]["package_browse_readme"].endswith("BROWSE_PACKAGE.md")
    assert result["candidate_comparison"]["ranked_candidates"][0]["artifact_id"] == result["dispatch_decision"]["selected"]["artifact_id"]
    assert Path(result["candidate_comparison_path"]).exists()
    assert "## Candidate Comparison" in operator_review_readme
    assert workflow["support_summary_aggregate"]["domains"] == ["macro"]
    assert "## Review Checklist" in operator_review_readme
    assert "## Operator Go / No-Go" in operator_review_readme
    assert "## Artifact Integrity" in operator_review_readme
    assert "## Support Summary Aggregate" in operator_review_readme
    assert "recommended_action=send" in operator_summary
    assert "source_health overall=degraded" in operator_summary
    assert "selected_package_dir=" in operator_summary
    assert "package_index=" in operator_summary
    assert store.persisted_workflow_linkages
    persisted_artifact_id, linkage = store.persisted_workflow_linkages[-1]
    assert persisted_artifact_id == result["artifact"]["artifact_id"]
    assert linkage["send_manifest_path"] == result["send_manifest_path"]
    assert linkage["review_manifest_path"] == result["review_manifest_path"]
    assert linkage["workflow_manifest_path"] == result["workflow_manifest_path"]
    assert linkage["selected_handoff"]["selected_artifact_id"] == result["artifact"]["artifact_id"]
    assert linkage["review_surface"]["candidate_comparison"]["selected_artifact_id"] == result["artifact"]["artifact_id"]
    assert linkage["review_surface"]["operator_go_no_go"]["decision"] == "GO"
    assert linkage["review_surface"]["review_manifest"]["next_step"] == "send_selected_package_to_primary_channel"


def test_main_report_morning_delivery_workflow_marks_review_required_for_provisional_candidate(tmp_path: Path) -> None:
    assembled = _assembled_sections()
    assembled["sections"][1]["signals"][0]["attributes_json"]["contract_mode"] = "provisional_close_only"
    stub = _StubAssemblyService(assembled)
    rendering_service = MainReportRenderingService(assembly_service=stub)
    store = _StubStore()
    publisher = MainReportArtifactPublishingService(rendering_service=rendering_service, store=store, artifact_root=tmp_path)
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
    assert review_manifest["next_step"] == "review_current_package_then_send_if_accepted"
    assert any(item["item"] == "late_contract_mode" and item["status"] == "warn" for item in review_manifest["checklist"])
    assert result["operator_review_bundle"]["operator_go_no_go"]["decision"] == "REVIEW"
    assert review_manifest["warning_items"]


def test_main_report_morning_delivery_workflow_marks_superseded_when_better_ready_candidate_exists(tmp_path: Path) -> None:
    orchestrator, _ = _build_orchestrator(tmp_path)
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
    operator_review_bundle = json.loads(Path(result["operator_review_bundle_path"]).read_text(encoding="utf-8"))
    operator_review_readme = Path(result["operator_review_readme_path"]).read_text(encoding="utf-8")

    assert result["dispatch_decision"]["selected"]["artifact_id"] == "artifact-better-ready"
    assert workflow["workflow_state"] == "superseded_by_better_candidate"
    assert workflow["selected_handoff"]["selected_artifact_id"] == "artifact-better-ready"
    assert send_manifest["selected_is_current"] is False
    assert send_manifest["next_step"] == "switch_to_selected_package_and_do_not_send_current"
    assert "current_package_not_selected" in send_manifest["send_blockers"]
    assert operator_review_bundle["candidate_overview"]["selected_artifact_id"] == "artifact-better-ready"
    assert operator_review_bundle["operator_go_no_go"]["decision"] == "NO_GO"
    assert operator_review_bundle["candidate_comparison"]["current_vs_selected"]["selected_artifact_id"] == "artifact-better-ready"
    assert "## Alternative Candidates" in operator_review_readme
    assert "## Current vs Selected Delta" in operator_review_readme
    assert "artifact-better-ready" in operator_review_readme
    assert any(item["item"] == "confirm_selected_candidate" and item["status"] == "warn" for item in review_manifest["checklist"])
