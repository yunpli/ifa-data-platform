from __future__ import annotations

from scripts.fsj_artifact_lineage import build_payload


class _DummyStore:
    def get_latest_active_report_artifact_lineage(self, **_: object) -> dict:
        return {"artifact": {"business_date": "2099-04-22"}}

    def get_active_report_artifact_lineage(self, **_: object) -> dict:
        return {
            "artifact": {"artifact_id": "artifact-active", "status": "active", "report_run_id": "run-1"},
            "canonical_lifecycle": {"state": "sent", "reason": "dispatch_receipt_succeeded"},
            "selection": {"selected_artifact_id": "artifact-active", "selected_is_current": True},
            "package": {"paths": {"send_manifest_path": "/tmp/send_manifest.json", "review_manifest_path": "/tmp/review_manifest.json", "workflow_manifest_path": "/tmp/workflow_manifest.json", "delivery_manifest_path": "/tmp/delivery_manifest.json"}},
            "review": {"operator_go_no_go": {"decision": "GO"}, "candidate_comparison": {"candidate_count": 2}},
            "what_user_received": {"dispatch_state": "dispatch_succeeded", "channel": "telegram_document", "provider_message_id": "42", "sent_at": "2099-04-22T10:00:03Z", "error": None},
            "bundle_lineage_summary": {"bundle_count": 2, "missing_bundle_count": 0, "slots": ["early", "late"], "section_keys": ["pre_open_main", "post_close_main"]},
            "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=2/2]"},
        }

    def list_report_artifact_lineages(self, **_: object) -> list[dict]:
        return [
            {"artifact": {"artifact_id": "artifact-active"}},
            {"artifact": {"artifact_id": "artifact-prev"}},
        ]


def test_build_payload_uses_artifact_lineage_store_helpers() -> None:
    payload = build_payload(
        business_date=None,
        agent_domain="main",
        artifact_family="main_final_report",
        strongest_slot="late",
        history_limit=5,
        store=_DummyStore(),
    )

    assert payload["business_date"] == "2099-04-22"
    assert payload["active"]["artifact"]["artifact_id"] == "artifact-active"
    assert payload["active"]["what_user_received"]["provider_message_id"] == "42"
    assert len(payload["history"]) == 2
