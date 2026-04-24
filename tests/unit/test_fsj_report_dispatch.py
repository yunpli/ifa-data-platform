from __future__ import annotations

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.report_dispatch import MainReportDeliveryDispatchHelper
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError as LiveIsolationError


class _DummyStore:
    def get_active_report_operator_review_surface(self, **_: object) -> dict | None:
        return self._review_surface("artifact-active", status="active")

    def list_report_operator_review_surfaces(self, **_: object) -> list[dict]:
        return [
            self._review_surface("artifact-active", status="active"),
            self._review_surface("artifact-older", status="superseded"),
        ]

    def _review_surface(self, artifact_id: str, *, status: str) -> dict:
        return {
            "artifact": {
                "artifact_id": artifact_id,
                "report_run_id": f"run-{artifact_id}",
                "business_date": "2099-04-22",
                "artifact_family": "main_final_report",
                "status": status,
            },
            "selected_handoff": {
                "selected_artifact_id": "artifact-selected",
                "selected_delivery_package_dir": "/normalized/pkg",
            },
            "state": {
                "recommended_action": "send_review",
                "workflow_state": "review_required",
                "qa_axes": {
                    "structural": {"ready": True, "score": 95, "blocker_count": 0, "warning_count": 0, "issue_codes": []},
                    "lineage": {"ready": True, "score": 92, "blocker_count": 0, "warning_count": 1, "issue_codes": ["llm_degraded"]},
                    "policy": {"ready": False, "score": 88, "blocker_count": 1, "warning_count": 0, "issue_codes": ["policy_boundary_violation"]},
                },
            },
            "package_paths": {
                "delivery_package_dir": "/normalized/pkg",
                "delivery_manifest_path": "/normalized/pkg/delivery_manifest.json",
                "send_manifest_path": "/normalized/pkg/send_manifest.json",
                "review_manifest_path": "/normalized/pkg/review_manifest.json",
                "workflow_manifest_path": "/normalized/pkg/workflow_manifest.json",
                "operator_review_bundle_path": "/normalized/pkg/operator_review_bundle.json",
                "operator_review_readme_path": "/normalized/pkg/OPERATOR_REVIEW.md",
                "package_index_path": "/normalized/pkg/package_index.json",
                "package_browse_readme_path": "/normalized/pkg/BROWSE_PACKAGE.md",
                "telegram_caption_path": "/normalized/pkg/telegram_caption.txt",
                "delivery_zip_path": "/normalized/pkg.zip",
            },
            "package_versions": {},
            "package_state": {
                "package_state": "ready",
                "ready_for_delivery": True,
                "quality_gate": {"score": 93},
                "slot_evaluation": {"strongest_slot": "late"},
                "dispatch_advice": {"recommended_action": "send_review"},
                "support_summary_aggregate": {},
            },
            "package_artifacts": {},
            "workflow_handoff": {
                "artifact": {"artifact_id": artifact_id},
                "selected_handoff": {
                    "selected_artifact_id": "artifact-selected",
                    "selected_delivery_package_dir": "/normalized/pkg",
                },
                "state": {"recommended_action": "send_review"},
                "manifest_pointers": {
                    "delivery_manifest_path": "/normalized/pkg/delivery_manifest.json",
                    "send_manifest_path": "/normalized/pkg/send_manifest.json",
                    "review_manifest_path": "/normalized/pkg/review_manifest.json",
                    "workflow_manifest_path": "/normalized/pkg/workflow_manifest.json",
                    "operator_review_bundle_path": "/normalized/pkg/operator_review_bundle.json",
                    "operator_review_readme_path": "/normalized/pkg/OPERATOR_REVIEW.md",
                    "package_index_path": "/normalized/pkg/package_index.json",
                    "package_browse_readme_path": "/normalized/pkg/BROWSE_PACKAGE.md",
                    "telegram_caption_path": "/normalized/pkg/telegram_caption.txt",
                    "delivery_zip_path": "/normalized/pkg.zip",
                },
                "version_pointers": {},
            },
            "candidate_comparison": {
                "selected_artifact_id": "artifact-selected",
                "current_artifact_id": artifact_id,
                "ranked_candidates": [],
                "current_vs_selected": {
                    "current_artifact_id": artifact_id,
                    "selected_artifact_id": "artifact-selected",
                },
            },
            "operator_go_no_go": {"decision": "REVIEW"},
            "llm_lineage_summary": {
                "status": "degraded",
                "summary_line": "degraded [applied=2/3 | degraded=1 | slots=early,late]",
            },
            "llm_role_policy": {
                "policy_versions": ["fsj_llm_role_policy_v1"],
                "boundary_modes": ["validated_llm_text_fields_only"],
                "deterministic_owner_fields": ["judgment.action"],
                "forbidden_decisions": ["declare_close_final_confirmation"],
                "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                "slot_boundary_modes": {"early": "validated_llm_text_fields_only", "late": "validated_llm_text_fields_only"},
            },
        }


def test_published_candidate_from_review_surface_uses_canonical_operator_review_surface() -> None:
    helper = MainReportDeliveryDispatchHelper()
    review_surface = _DummyStore()._review_surface("artifact-active", status="active")

    published = helper._published_candidate_from_review_surface(review_surface, source="db_active_delivery_surface")

    assert published is not None
    assert published["delivery_package_dir"] == "/normalized/pkg"
    assert published["delivery_manifest_path"] == "/normalized/pkg/delivery_manifest.json"
    assert published["send_manifest_path"] == "/normalized/pkg/send_manifest.json"
    assert published["review_manifest_path"] == "/normalized/pkg/review_manifest.json"
    assert published["workflow_manifest_path"] == "/normalized/pkg/workflow_manifest.json"
    assert published["selected_handoff"]["selected_artifact_id"] == "artifact-selected"
    assert published["workflow_handoff"]["manifest_pointers"]["operator_review_bundle_path"] == "/normalized/pkg/operator_review_bundle.json"
    assert published["package_surface"]["package_paths"]["operator_review_bundle_path"] == "/normalized/pkg/operator_review_bundle.json"
    assert published["candidate_comparison"]["selected_artifact_id"] == "artifact-selected"
    assert published["operator_go_no_go"]["decision"] == "REVIEW"


def test_list_db_delivery_candidates_uses_canonical_review_surface_queries() -> None:
    helper = MainReportDeliveryDispatchHelper()

    published = helper.list_db_delivery_candidates(business_date="2099-04-22", store=_DummyStore(), limit=8)

    assert [item["artifact"]["artifact_id"] for item in published] == ["artifact-active", "artifact-older"]
    assert published[0]["source"] == "db_active_delivery_surface"
    assert published[1]["source"] == "db_delivery_history_surface"


def test_summarize_candidate_projects_qa_axes_lineage_and_policy_from_review_surface() -> None:
    helper = MainReportDeliveryDispatchHelper()

    published = helper._published_candidate_from_review_surface(
        _DummyStore()._review_surface("artifact-active", status="active"),
        source="db_active_delivery_surface",
    )

    summary = helper.summarize_candidate(published)

    assert summary["qa_axes_posture"] == "blocked"
    assert summary["qa_axes_summary"]["axes_with_attention"] == ["lineage", "policy"]
    assert summary["qa_axes_summary"]["not_ready_axes"] == ["policy"]
    assert summary["llm_lineage_summary"]["status"] == "degraded"
    assert summary["llm_role_policy"]["policy_versions"] == ["fsj_llm_role_policy_v1"]
    assert summary["llm_role_policy"]["slot_boundary_modes"]["late"] == "validated_llm_text_fields_only"


def test_choose_best_projects_qa_posture_into_ranked_candidates() -> None:
    helper = MainReportDeliveryDispatchHelper()
    store = _DummyStore()

    ready_surface = store._review_surface("artifact-ready", status="active")
    ready_surface["package_state"] = {
        "package_state": "ready",
        "ready_for_delivery": True,
        "quality_gate": {
            "score": 97,
            "blocker_count": 0,
            "warning_count": 0,
            "qa_axes": {
                "structural": {"ready": True, "score": 97, "blocker_count": 0, "warning_count": 0, "issue_codes": []},
                "lineage": {"ready": True, "score": 97, "blocker_count": 0, "warning_count": 0, "issue_codes": []},
                "policy": {"ready": True, "score": 97, "blocker_count": 0, "warning_count": 0, "issue_codes": []},
            },
        },
        "slot_evaluation": {"strongest_slot": "late", "slot_scores": {"early": 88, "mid": 92, "late": 97}},
        "dispatch_advice": {"recommended_action": "send"},
        "support_summary_aggregate": {},
    }
    ready_surface["state"] = {
        "recommended_action": "send",
        "workflow_state": "ready_to_send",
        "qa_axes": ready_surface["package_state"]["quality_gate"]["qa_axes"],
    }
    ready_surface["llm_lineage_summary"] = {"status": "applied", "summary_line": "applied [applied=3/3]"}

    blocked_published = helper._published_candidate_from_review_surface(
        store._review_surface("artifact-blocked", status="superseded"),
        source="db_delivery_history_surface",
    )
    ready_published = helper._published_candidate_from_review_surface(
        ready_surface,
        source="db_active_delivery_surface",
    )

    decision = helper.choose_best([blocked_published, ready_published])
    comparison = helper.build_candidate_comparison([blocked_published, ready_published], current_artifact_id="artifact-blocked")

    assert decision["selected"]["artifact_id"] == "artifact-ready"
    assert decision["selected"]["qa_axes_posture"] == "ready"
    assert decision["ranked_candidates"][0]["llm_lineage_summary"]["status"] == "applied"
    assert decision["ranked_candidates"][1]["qa_axes_summary"]["not_ready_axes"] == ["policy"]
    assert comparison["ranked_candidates"][0]["qa_axes_posture"] == "ready"
    assert comparison["current_vs_selected"]["delta_current_vs_selected"]["qa_score_delta"] < 0


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"
LIVE_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp"


def _clear_caches() -> None:
    make_engine.cache_clear()
    get_settings.cache_clear()


def test_list_db_delivery_candidates_requires_explicit_non_live_db_under_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    _clear_caches()

    with pytest.raises(LiveIsolationError, match="DATABASE_URL must be set explicitly"):
        MainReportDeliveryDispatchHelper().list_db_delivery_candidates(business_date="2099-04-22")


def test_list_db_delivery_candidates_rejects_canonical_live_db_under_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", LIVE_DB_URL)
    _clear_caches()

    with pytest.raises(LiveIsolationError, match="canonical/live DB"):
        MainReportDeliveryDispatchHelper().list_db_delivery_candidates(business_date="2099-04-22")


def test_list_db_delivery_candidates_allows_explicit_test_db_under_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    _clear_caches()

    class _EmptyStore(_DummyStore):
        def list_report_operator_review_surfaces(self, **_: object) -> list[dict]:
            return []

    published = MainReportDeliveryDispatchHelper().list_db_delivery_candidates(
        business_date="2099-04-22",
        store=_EmptyStore(),
    )

    assert published == []
