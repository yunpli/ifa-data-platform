from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ifa_data_platform.fsj.report_orchestration import (
    build_main_report_morning_delivery_orchestrator,
    build_support_report_delivery_publisher,
)
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError as LiveIsolationError


@pytest.fixture(autouse=True)
def _explicit_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp")


class _StubAssemblyService:
    def assemble_main_sections(self, *, business_date: str, include_empty: bool = False) -> dict:
        return {
            "artifact_type": "fsj_main_report_sections",
            "artifact_version": "v2",
            "market": "a_share",
            "business_date": business_date,
            "agent_domain": "main",
            "section_count": 1,
            "support_summary_domains": [],
            "sections": [
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
                    "summary": "收盘确认主线强化。",
                    "judgments": [],
                    "signals": [
                        {
                            "object_key": "signal:late:close_package_state",
                            "statement": "same-day final market packet ready，收盘 close package 可用。",
                            "signal_strength": "high",
                            "confidence": "high",
                            "evidence_level": "E1",
                            "attributes_json": {"contract_mode": "full_close_package", "provisional_close_only": False},
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
                }
            ],
        }


class _StubSupportAssemblyService:
    def assemble_support_section(self, *, business_date: str, agent_domain: str, slot: str) -> dict:
        return {
            "artifact_type": "fsj_support_section",
            "artifact_version": "v1",
            "market": "a_share",
            "business_date": business_date,
            "agent_domain": agent_domain,
            "slot": slot,
            "section_render_key": f"support.{agent_domain}.{slot}",
            "status": "ready",
            "title": f"{agent_domain} support",
            "summary": f"{agent_domain} ready summary",
            "judgments": [],
            "signals": [],
            "facts": [],
            "bundle": {
                "bundle_id": f"bundle-{agent_domain}-{slot}",
                "status": "active",
                "producer": "ifa_data_platform.fsj.support_producer",
                "producer_version": "phase1-support-v1",
                "slot_run_id": f"slot-run-{agent_domain}-{slot}",
                "replay_id": f"replay-{agent_domain}-{slot}",
                "updated_at": "2099-04-22T15:05:00+08:00",
            },
            "lineage": {
                "bundle": {"bundle_id": f"bundle-{agent_domain}-{slot}", "payload_json": {}},
                "objects": [],
                "edges": [],
                "evidence_links": [],
                "observed_records": [],
                "report_links": [],
            },
        }


class _StubStore:
    def __init__(self) -> None:
        self.registered: list[dict] = []

    def register_report_artifact(self, payload: dict) -> dict:
        self.registered.append(payload)
        return {**payload, "status": payload["status"]}

    def attach_report_links(self, bundle_id: str, report_links: list[dict]) -> list[dict]:
        return report_links

    def persist_report_workflow_linkage(self, artifact_id: str, workflow_linkage: dict) -> dict:
        return {"artifact_id": artifact_id, "metadata_json": {"workflow_linkage": workflow_linkage}}


def test_support_report_delivery_factory_blocks_missing_artifact_root_under_pytest() -> None:
    with pytest.raises(LiveIsolationError, match="artifact_root must be set explicitly"):
        build_support_report_delivery_publisher(
            assembly_service=_StubSupportAssemblyService(),
            store=_StubStore(),
            artifact_root=None,
        )


def test_support_report_delivery_factory_runs_with_explicit_non_live_artifact_root(tmp_path: Path) -> None:
    publisher = build_support_report_delivery_publisher(
        assembly_service=_StubSupportAssemblyService(),
        store=_StubStore(),
        artifact_root=tmp_path,
    )

    result = publisher.publish_delivery_package(
        business_date="2099-04-22",
        agent_domain="macro",
        slot="early",
        output_dir=tmp_path,
        report_run_id="integration-support-factory-path",
        generated_at=datetime(2099, 4, 22, 9, 58, tzinfo=timezone.utc),
    )

    assert Path(result["delivery_manifest_path"]).exists()
    assert Path(result["delivery_zip_path"]).exists()
    assert Path(result["operator_summary_path"]).exists()


def test_main_report_orchestration_factory_blocks_missing_artifact_root_under_pytest() -> None:
    with pytest.raises(LiveIsolationError, match="artifact_root must be set explicitly"):
        build_main_report_morning_delivery_orchestrator(
            assembly_service=_StubAssemblyService(),
            store=_StubStore(),
            artifact_root=None,
        )


def test_main_report_orchestration_factory_runs_with_explicit_non_live_artifact_root(tmp_path: Path) -> None:
    orchestrator = build_main_report_morning_delivery_orchestrator(
        assembly_service=_StubAssemblyService(),
        store=_StubStore(),
        artifact_root=tmp_path,
    )

    result = orchestrator.run_workflow(
        business_date="2099-04-22",
        output_dir=tmp_path,
        report_run_id="integration-factory-path",
        generated_at=datetime(2099, 4, 22, 9, 58, tzinfo=timezone.utc),
    )

    assert Path(result["workflow_manifest_path"]).exists()
    assert Path(result["delivery_manifest_path"]).exists()
    assert Path(result["delivery_zip_path"]).exists()
