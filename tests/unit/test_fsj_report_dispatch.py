from __future__ import annotations

from ifa_data_platform.fsj.report_dispatch import MainReportDeliveryDispatchHelper


class _DummyStore:
    def report_workflow_handoff_from_surface(self, surface: dict) -> dict:
        return {
            "artifact": {"artifact_id": surface["artifact"]["artifact_id"]},
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
        }

    def report_package_surface_from_surface(self, surface: dict) -> dict:
        workflow_handoff = self.report_workflow_handoff_from_surface(surface)
        return {
            "artifact": workflow_handoff["artifact"],
            "selected_handoff": workflow_handoff["selected_handoff"],
            "state": workflow_handoff["state"],
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
            "package_state": {},
            "package_artifacts": {},
            "workflow_handoff": workflow_handoff,
        }


def test_published_candidate_from_surface_uses_canonical_workflow_handoff() -> None:
    helper = MainReportDeliveryDispatchHelper()
    surface = {
        "artifact": {
            "artifact_id": "artifact-active",
            "report_run_id": "run-active",
            "business_date": "2099-04-22",
            "artifact_family": "main_final_report",
        },
        "delivery_package": {
            "delivery_package_dir": "/raw/pkg",
            "delivery_manifest_path": "/raw/pkg/delivery_manifest.json",
            "delivery_zip_path": "/raw/pkg.zip",
            "telegram_caption_path": "/raw/pkg/telegram_caption.txt",
            "package_index_path": "/raw/pkg/package_index.json",
            "package_browse_readme_path": "/raw/pkg/BROWSE_PACKAGE.md",
            "package_state": "ready",
            "ready_for_delivery": True,
            "quality_gate": {"score": 93},
            "slot_evaluation": {"strongest_slot": "late"},
            "dispatch_advice": {"recommended_action": "send_review"},
            "artifacts": {},
            "workflow": {"workflow_state": "review_required"},
        },
        "workflow_linkage": {
            "send_manifest_path": "/raw/pkg/send_manifest.json",
            "review_manifest_path": "/raw/pkg/review_manifest.json",
            "workflow_manifest_path": "/raw/pkg/workflow_manifest.json",
            "selected_handoff": {"selected_artifact_id": "artifact-raw"},
        },
    }

    published = helper._published_candidate_from_surface(surface, source="db_active_delivery_surface", store=_DummyStore())

    assert published is not None
    assert published["delivery_package_dir"] == "/normalized/pkg"
    assert published["delivery_manifest_path"] == "/normalized/pkg/delivery_manifest.json"
    assert published["send_manifest_path"] == "/normalized/pkg/send_manifest.json"
    assert published["review_manifest_path"] == "/normalized/pkg/review_manifest.json"
    assert published["workflow_manifest_path"] == "/normalized/pkg/workflow_manifest.json"
    assert published["selected_handoff"]["selected_artifact_id"] == "artifact-selected"
    assert published["workflow_handoff"]["manifest_pointers"]["operator_review_bundle_path"] == "/normalized/pkg/operator_review_bundle.json"
    assert published["package_surface"]["package_paths"]["operator_review_bundle_path"] == "/normalized/pkg/operator_review_bundle.json"
