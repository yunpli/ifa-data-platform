from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from ifa_data_platform.fsj.store import FSJStore


class _ProjectionOnlyStore(FSJStore):
    def __init__(self) -> None:
        pass


def test_json_dumps_normalizes_non_native_json_types() -> None:
    store = _ProjectionOnlyStore()

    dumped = store._json_dumps(
        {
            "whole": Decimal("12"),
            "fraction": Decimal("12.34"),
            "date": date(2026, 4, 23),
            "dt": datetime(2026, 4, 23, 11, 42, 0),
            "path": Path("/tmp/example"),
        }
    )

    payload = json.loads(dumped)
    assert payload == {
        "whole": 12,
        "fraction": 12.34,
        "date": "2026-04-23",
        "dt": "2026-04-23T11:42:00",
        "path": "/tmp/example",
    }


def test_report_workflow_handoff_projection_preserves_operator_readiness_fields() -> None:
    from ifa_data_platform.fsj.store import FSJStore

    store = _ProjectionOnlyStore()
    summary = store.report_workflow_handoff_from_surface({
        "artifact": {
            "artifact_id": "artifact-current",
            "report_run_id": "run-current",
            "business_date": "2099-04-22",
            "status": "active",
        },
        "delivery_package": {
            "package_state": "ready",
            "ready_for_delivery": True,
            "quality_gate": {
                "score": 93,
                "blocker_count": 0,
                "warning_count": 1,
                "late_contract_mode": "full_close_package",
            },
            "workflow": {
                "recommended_action": "send_review",
                "dispatch_recommended_action": "send",
                "workflow_state": "selected_candidate_mismatch",
                "next_step": "operator_review_selected_candidate",
                "selection_reason": "best_ready_candidate strongest_slot=late qa_score=93",
                "dispatch_selected_artifact_id": "artifact-selected",
                "send_blockers": ["selected_candidate_differs_from_current"],
            },
        },
        "workflow_linkage": {
            "selected_handoff": {
                "selected_artifact_id": "artifact-selected",
                "selected_report_run_id": "run-selected",
                "selected_business_date": "2099-04-22",
                "selected_is_current": False,
                "delivery_package_dir": "/tmp/selected-pkg",
                "delivery_manifest_path": "/tmp/selected-pkg/delivery_manifest.json",
                "delivery_zip_path": "/tmp/selected-pkg.zip",
                "telegram_caption_path": "/tmp/selected-pkg/telegram_caption.txt",
            },
            "send_manifest_path": "/tmp/current/send_manifest.json",
        },
    })

    assert summary["selected_handoff"]["selected_is_current"] is False
    assert summary["selected_handoff"]["selected_artifact_id"] == "artifact-selected"
    assert summary["state"]["dispatch_recommended_action"] == "send"
    assert summary["state"]["next_step"] == "operator_review_selected_candidate"
    assert summary["state"]["selection_reason"] == "best_ready_candidate strongest_slot=late qa_score=93"
    assert summary["state"]["dispatch_selected_artifact_id"] == "artifact-selected"
    assert summary["state"]["send_blockers"] == ["selected_candidate_differs_from_current"]


def test_report_package_surface_projection_preserves_review_and_send_package_pointers() -> None:
    store = _ProjectionOnlyStore()
    surface = {
        "artifact": {
            "artifact_id": "artifact-current",
            "report_run_id": "run-current",
            "business_date": "2099-04-22",
            "status": "active",
            "artifact_version": "v1",
        },
        "delivery_package": {
            "delivery_package_dir": "/tmp/current-pkg",
            "package_state": "ready",
            "ready_for_delivery": True,
            "quality_gate": {"score": 93, "blocker_count": 0, "warning_count": 1},
            "slot_evaluation": {"strongest_slot": "late"},
            "dispatch_advice": {"recommended_action": "send_review"},
            "support_summary_aggregate": {"domain_count": 3},
            "artifacts": {
                "delivery_manifest": "delivery_manifest.json",
                "send_manifest": "send_manifest.json",
                "review_manifest": "review_manifest.json",
                "workflow_manifest": "workflow_manifest.json",
                "package_index": "package_index.json",
            },
            "workflow": {
                "recommended_action": "send_review",
                "workflow_state": "selected_candidate_mismatch",
            },
        },
        "workflow_linkage": {
            "selected_handoff": {
                "selected_artifact_id": "artifact-selected",
                "selected_report_run_id": "run-selected",
                "selected_business_date": "2099-04-22",
                "selected_is_current": False,
                "delivery_package_dir": "/tmp/selected-pkg",
                "delivery_manifest_path": "/tmp/selected-pkg/delivery_manifest.json",
                "delivery_zip_path": "/tmp/selected-pkg.zip",
                "telegram_caption_path": "/tmp/selected-pkg/telegram_caption.txt",
            },
            "send_manifest_path": "/tmp/current/send_manifest.json",
            "review_manifest_path": "/tmp/current/review_manifest.json",
            "workflow_manifest_path": "/tmp/current/workflow_manifest.json",
            "operator_review_bundle_path": "/tmp/current/operator_review_bundle.json",
            "operator_review_readme_path": "/tmp/current/OPERATOR_REVIEW.md",
        },
    }

    summary = store.report_package_surface_from_surface(surface)

    assert summary["artifact"]["artifact_id"] == "artifact-current"
    assert summary["selected_handoff"]["selected_artifact_id"] == "artifact-selected"
    assert summary["package_paths"]["delivery_package_dir"] == "/tmp/selected-pkg"
    assert summary["package_paths"]["delivery_manifest_path"] == "/tmp/selected-pkg/delivery_manifest.json"
    assert summary["package_paths"]["send_manifest_path"] == "/tmp/current/send_manifest.json"
    assert summary["package_paths"]["review_manifest_path"] == "/tmp/current/review_manifest.json"
    assert summary["package_paths"]["operator_review_bundle_path"] == "/tmp/current/operator_review_bundle.json"
    assert summary["package_versions"]["artifact_version"] == "v1"
    assert summary["package_versions"]["review_manifest_version"] == "review_manifest.json"
    assert summary["package_state"]["support_summary_aggregate"]["domain_count"] == 3
    assert summary["workflow_handoff"]["state"]["workflow_state"] == "selected_candidate_mismatch"


def test_report_operator_review_surface_projection_prefers_db_backed_review_payload() -> None:
    class _Store(_ProjectionOnlyStore):
        def get_bundle_graph(self, bundle_id: str) -> dict | None:
            graphs = {
                "bundle-early": {
                    "bundle": {
                        "bundle_id": "bundle-early",
                        "slot": "early",
                        "section_key": "pre_open_main",
                        "summary": "early summary",
                        "payload_json": {
                            "llm_assist": {
                                "applied": False,
                                "model_alias": "grok41_thinking",
                                "prompt_version": "fsj_early_main_v1",
                                "failure_classification": "timeout",
                                "policy": {
                                    "outcome": "deterministic_degrade",
                                    "operator_tag": "llm_timeout",
                                    "attempted_model_chain": ["grok41_thinking", "gemini31_pro_jmr"],
                                },
                            }
                        },
                    }
                },
                "bundle-late": {
                    "bundle": {
                        "bundle_id": "bundle-late",
                        "slot": "late",
                        "section_key": "post_close_main",
                        "summary": "late summary",
                        "payload_json": {
                            "llm_assist": {
                                "applied": True,
                                "model_alias": "gemini31_pro_jmr",
                                "prompt_version": "fsj_late_main_v1",
                                "policy": {
                                    "outcome": "fallback_applied",
                                    "attempted_model_chain": ["grok41_thinking", "gemini31_pro_jmr"],
                                },
                            }
                        },
                    }
                },
            }
            return graphs.get(bundle_id)

    store = _Store()
    surface = {
        "artifact": {
            "artifact_id": "artifact-current",
            "report_run_id": "run-current",
            "business_date": "2099-04-22",
            "status": "active",
            "artifact_version": "v2",
            "metadata_json": {"bundle_ids": ["bundle-early", "bundle-late"]},
        },
        "delivery_package": {
            "delivery_package_dir": "/tmp/current-pkg",
            "package_state": "ready",
            "ready_for_delivery": False,
            "quality_gate": {"score": 91, "blocker_count": 1, "warning_count": 2},
            "workflow": {
                "recommended_action": "send_review",
                "workflow_state": "review_required",
            },
        },
        "workflow_linkage": {
            "selected_handoff": {
                "selected_artifact_id": "artifact-selected",
                "selected_is_current": False,
                "delivery_package_dir": "/tmp/selected-pkg",
                "delivery_manifest_path": "/tmp/selected-pkg/delivery_manifest.json",
            },
            "review_surface": {
                "candidate_comparison": {
                    "selected_artifact_id": "artifact-selected",
                    "current_artifact_id": "artifact-current",
                    "candidate_count": 2,
                    "ready_candidate_count": 1,
                    "ranked_candidates": [
                        {"artifact_id": "artifact-selected", "ready_for_delivery": True},
                        {"artifact_id": "artifact-current", "ready_for_delivery": False},
                    ],
                    "current_vs_selected": {
                        "current_artifact_id": "artifact-current",
                        "selected_artifact_id": "artifact-selected",
                        "current_rank": 2,
                        "selected_rank": 1,
                    },
                },
                "operator_go_no_go": {
                    "decision": "NO_GO",
                    "artifact_integrity_ok": True,
                    "missing_artifacts": [],
                },
                "review_manifest": {"next_step": "switch_to_selected_package_and_do_not_send_current"},
                "send_manifest": {"next_step": "switch_to_selected_package_and_do_not_send_current"},
            },
        },
    }

    summary = store.report_operator_review_surface_from_surface(surface)

    assert summary["candidate_comparison"]["selected_artifact_id"] == "artifact-selected"
    assert summary["candidate_comparison"]["current_artifact_id"] == "artifact-current"
    assert summary["candidate_comparison"]["candidate_count"] == 2
    assert summary["candidate_comparison"]["ready_candidate_count"] == 1
    assert summary["operator_go_no_go"]["decision"] == "NO_GO"
    assert summary["review_manifest"]["next_step"] == "switch_to_selected_package_and_do_not_send_current"
    assert summary["review_summary"]["go_no_go_decision"] == "NO_GO"
    assert summary["review_summary"]["selected_is_current"] is False
    assert summary["package_paths"]["delivery_package_dir"] == "/tmp/selected-pkg"
    assert summary["llm_lineage"]["summary"]["bundle_count"] == 2
    assert summary["llm_lineage"]["summary"]["applied_count"] == 1
    assert summary["llm_lineage"]["summary"]["degraded_count"] == 1
    assert summary["llm_lineage"]["summary"]["fallback_applied_count"] == 1
    assert summary["llm_lineage"]["summary"]["operator_tags"] == ["llm_timeout"]
    assert summary["llm_lineage_summary"]["status"] == "degraded"
    assert summary["llm_lineage_summary"]["summary_line"] == "degraded [applied=1/2 | fallback=1 | degraded=1 | deterministic=1 | tags=llm_timeout | slots=early,late]"
    assert summary["review_summary"]["llm_bundle_count"] == 2
    assert summary["review_summary"]["llm_applied_count"] == 1
    assert summary["review_summary"]["llm_degraded_count"] == 1
    assert summary["review_summary"]["llm_fallback_count"] == 1
    assert summary["review_summary"]["llm_lineage_status"] == "degraded"
    assert summary["review_summary"]["llm_lineage_summary"] == "degraded [applied=1/2 | fallback=1 | degraded=1 | deterministic=1 | tags=llm_timeout | slots=early,late]"


def test_report_llm_lineage_from_artifact_projects_bundle_level_attempts() -> None:
    class _Store(_ProjectionOnlyStore):
        def get_bundle_graph(self, bundle_id: str) -> dict | None:
            if bundle_id == "bundle-missing":
                return None
            return {
                "bundle": {
                    "bundle_id": bundle_id,
                    "slot": "mid",
                    "section_key": "midday_main",
                    "summary": "mid summary",
                    "payload_json": {
                        "llm_assist": {
                            "applied": True,
                            "model_alias": "grok41_thinking",
                            "prompt_version": "fsj_mid_main_v1",
                            "policy": {
                                "outcome": "primary_applied",
                                "attempted_model_chain": ["grok41_thinking"],
                            },
                        },
                        "llm_role_policy": {
                            "policy_version": "fsj_llm_role_policy_v1",
                            "boundary_mode": "intraday_working",
                            "forbidden_decisions": ["declare_close_final_confirmation"],
                            "deterministic_owner_fields": ["judgment.action"],
                            "override_precedence": ["deterministic_input_contract", "validated_llm_text_fields_only"],
                        },
                    },
                }
            }

    lineage = _Store().report_llm_lineage_from_artifact(
        {
            "artifact_id": "artifact-1",
            "metadata_json": {"bundle_ids": ["bundle-mid", "bundle-missing"]},
        }
    )

    assert lineage["artifact_id"] == "artifact-1"
    assert lineage["summary"]["bundle_count"] == 2
    assert lineage["summary"]["primary_applied_count"] == 1
    assert lineage["summary"]["missing_bundle_count"] == 1
    assert lineage["summary"]["role_policy_versions"] == ["fsj_llm_role_policy_v1"]
    assert lineage["summary"]["boundary_modes"] == ["intraday_working"]
    assert lineage["role_policy"]["forbidden_decisions"] == ["declare_close_final_confirmation"]
    assert lineage["bundles"][0]["bundle_id"] == "bundle-mid"
    assert lineage["bundles"][0]["role_policy_boundary_mode"] == "intraday_working"
    assert lineage["bundles"][1]["missing"] is True


def test_report_operator_review_surface_prefers_exported_workflow_linkage_llm_lineage() -> None:
    store = _ProjectionOnlyStore()
    summary = store.report_operator_review_surface_from_surface(
        {
            "artifact": {"artifact_id": "artifact-exported"},
            "delivery_package": {
                "package_state": "ready",
                "ready_for_delivery": True,
                "quality_gate": {"score": 98, "blocker_count": 0, "warning_count": 0},
                "workflow": {"recommended_action": "send", "workflow_state": "ready_to_send"},
            },
            "workflow_linkage": {
                "llm_lineage": {
                    "artifact_id": "artifact-exported",
                    "bundle_ids": ["bundle-exported"],
                    "summary": {"bundle_count": 1, "applied_count": 1, "degraded_count": 0, "fallback_applied_count": 0, "primary_applied_count": 1},
                    "bundles": [{"bundle_id": "bundle-exported", "slot": "late", "outcome": "primary_applied", "applied": True}],
                }
            },
        }
    )

    assert summary["llm_lineage"]["artifact_id"] == "artifact-exported"
    assert summary["llm_lineage"]["summary"]["bundle_count"] == 1
    assert summary["llm_role_policy"] == {}
    assert summary["llm_lineage_summary"]["status"] == "applied"
    assert summary["llm_lineage_summary"]["summary_line"] == "applied [applied=1/1 | primary=1]"
    assert summary["review_summary"]["llm_applied_count"] == 1
    assert summary["review_summary"]["llm_lineage_status"] == "applied"
    assert summary["review_summary"]["llm_lineage_summary"] == "applied [applied=1/1 | primary=1]"


def test_report_operator_review_query_helpers_project_from_delivery_surfaces() -> None:
    class _Store(FSJStore):
        def __init__(self) -> None:
            pass

        def get_active_report_delivery_surface(self, **_: object) -> dict | None:
            return {
                "artifact": {"artifact_id": "artifact-active", "status": "active"},
                "delivery_package": {
                    "package_state": "ready",
                    "ready_for_delivery": True,
                    "quality_gate": {"score": 99, "blocker_count": 0, "warning_count": 0},
                    "workflow": {"recommended_action": "send", "workflow_state": "ready_to_send"},
                },
                "workflow_linkage": {},
            }

        def get_latest_active_report_delivery_surface(self, **_: object) -> dict | None:
            return self.get_active_report_delivery_surface()

        def list_report_delivery_surfaces(self, **_: object) -> list[dict]:
            return [self.get_active_report_delivery_surface()]

    store = _Store()

    active = store.get_active_report_operator_review_surface(
        business_date="2099-04-22",
        agent_domain="main",
        artifact_family="main_final_report",
    )
    latest = store.get_latest_active_report_operator_review_surface(
        agent_domain="main",
        artifact_family="main_final_report",
    )
    history = store.list_report_operator_review_surfaces(
        business_date="2099-04-22",
        agent_domain="main",
        artifact_family="main_final_report",
    )

    assert active is not None
    assert active["artifact"]["artifact_id"] == "artifact-active"
    assert active["review_summary"]["go_no_go_decision"] == "GO"
    assert latest is not None
    assert latest["artifact"]["artifact_id"] == "artifact-active"
    assert history[0]["artifact"]["artifact_id"] == "artifact-active"
