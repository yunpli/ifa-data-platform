from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.test_live_isolation import TestLiveIsolationError as LiveIsolationError


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_support_dispatch_failure_status.py"
_spec = importlib.util.spec_from_file_location("fsj_support_dispatch_failure_status_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
_history_row = _module._history_row
build_dispatch_failure_payload = _module.build_dispatch_failure_payload


def test_history_row_projects_support_dispatch_receipt_fields() -> None:
    row = _history_row(
        {
            "artifact": {"artifact_id": "support-artifact", "report_run_id": "run-1", "status": "active"},
            "selected_handoff": {"selected_is_current": True},
            "state": {
                "workflow_state": "ready_to_send",
                "recommended_action": "send",
                "package_state": "ready",
                "ready_for_delivery": True,
                "send_ready": True,
                "review_required": False,
            },
            "canonical_lifecycle": {"state": "failed", "reason": "dispatch_receipt_failed"},
            "artifact_lineage": {
                "bundle_lineage_summary": {"bundle_count": 1, "missing_bundle_count": 0},
                "what_user_received": {"dispatch_state": "dispatch_failed", "provider_message_id": "tg-99"},
            },
            "dispatch_receipt": {
                "dispatch_state": "dispatch_failed",
                "attempted_at": "2099-04-23T10:00:00Z",
                "failed_at": "2099-04-23T10:00:03Z",
                "channel": "telegram_document",
                "error": "429 rate limit",
            },
            "review_summary": {
                "dispatch_attempted": False,
                "dispatch_succeeded": False,
                "dispatch_failed": True,
            },
        }
    )

    assert row["artifact_id"] == "support-artifact"
    assert row["canonical_lifecycle_state"] == "failed"
    assert row["dispatch_state"] == "dispatch_failed"
    assert row["provider_message_id"] == "tg-99"
    assert row["dispatch_receipt_channel"] == "telegram_document"
    assert row["dispatch_receipt_error"] == "429 rate limit"


def test_build_dispatch_failure_payload_uses_support_status_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        _module,
        "build_support_status_payload",
        lambda **_: {
            "business_date": "2099-04-23",
            "agent_domain": "macro",
            "resolution": {"mode": "explicit_business_date", "business_date": "2099-04-23", "agent_domain": "macro"},
            "active_surface": {
                "artifact": {"artifact_id": "artifact-1"},
                "selected_handoff": {"selected_is_current": True},
                "state": {"recommended_action": "hold", "send_ready": False, "review_required": False, "send_blockers": ["recommended_action_hold"]},
                "operator_go_no_go": {"decision": "NO_GO"},
                "send_manifest": {"send_blockers": ["recommended_action_hold"]},
                "review_manifest": {"blocking_items": []},
                "package_paths": {},
                "review_summary": {"go_no_go_decision": "NO_GO"},
            },
            "history": [
                {
                    "artifact": {"artifact_id": "artifact-history", "status": "superseded"},
                    "selected_handoff": {"selected_is_current": False},
                    "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "package_state": "ready", "ready_for_delivery": True, "send_ready": True, "review_required": False},
                    "canonical_lifecycle": {"state": "failed", "reason": "dispatch_receipt_failed"},
                    "artifact_lineage": {"what_user_received": {"dispatch_state": "dispatch_failed", "provider_message_id": "tg-41"}},
                    "dispatch_receipt": {"dispatch_state": "dispatch_failed", "attempted_at": "2099-04-23T10:00:00Z", "failed_at": "2099-04-23T10:00:03Z", "error": "429 rate limit"},
                    "review_summary": {"dispatch_attempted": False, "dispatch_succeeded": False, "dispatch_failed": True},
                }
            ],
        },
    )

    payload = build_dispatch_failure_payload(business_date="2099-04-23", agent_domain="macro", history_limit=3)

    assert payload["agent_domain"] == "macro"
    assert payload["dispatch_failure"]["dispatch_posture"] == "artifact_integrity_failed"
    assert "recommended_action_hold" in payload["dispatch_failure"]["failure_reasons"]
    assert payload["history_rows"][0]["canonical_lifecycle_state"] == "failed"
    assert payload["history_rows"][0]["dispatch_receipt_error"] == "429 rate limit"


def test_support_cli_json_contract_handles_missing_latest(monkeypatch, capsys) -> None:
    class _DummyStore:
        def get_latest_active_report_operator_review_surface(self, **_: object) -> None:
            return None

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())
    monkeypatch.setattr(
        "sys.argv",
        ["fsj_support_dispatch_failure_status.py", "--latest", "--agent-domain", "macro", "--format", "json"],
    )

    _module.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["agent_domain"] == "macro"
    assert payload["dispatch_failure"]["dispatch_posture"] == "no_active_artifact"


def test_support_cli_json_contract_uses_latest_active_surface(monkeypatch, capsys) -> None:
    surface = {
        "artifact": {
            "artifact_id": "artifact-active",
            "report_run_id": "run-active",
            "business_date": "2099-04-23",
            "status": "active",
        },
        "package_state": {"slot_evaluation": {"strongest_slot": "late"}},
        "selected_handoff": {"selected_is_current": True},
        "state": {"recommended_action": "send", "workflow_state": "ready_to_send", "send_ready": True, "review_required": False, "send_blockers": []},
        "operator_go_no_go": {"decision": "GO"},
        "send_manifest": {"send_blockers": []},
        "review_manifest": {"blocking_items": []},
        "package_paths": {},
        "review_summary": {"go_no_go_decision": "GO"},
    }

    class _DummyStore:
        def get_latest_active_report_operator_review_surface(self, **kwargs: object) -> dict:
            assert kwargs["agent_domain"] == "commodities"
            assert kwargs["artifact_family"] == "support_domain_report"
            assert kwargs["strongest_slot"] == "late"
            return surface

    monkeypatch.setattr(_module, "FSJStore", lambda: _DummyStore())
    monkeypatch.setattr(
        _module,
        "build_dispatch_failure_payload",
        lambda **kwargs: {
            "business_date": kwargs["business_date"],
            "agent_domain": kwargs["agent_domain"],
            "resolution": kwargs["resolution"],
            "active_surface": surface,
            "history": [],
            "dispatch_failure": {"dispatch_posture": "ready_to_dispatch", "channel_delivery_truth": "unknown_not_modeled"},
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        ["fsj_support_dispatch_failure_status.py", "--latest", "--agent-domain", "commodities", "--slot", "late", "--format", "json"],
    )

    _module.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["resolution"]["resolved_artifact_id"] == "artifact-active"
    assert payload["resolution"]["resolved_slot"] == "late"
    assert payload["resolution"]["agent_domain"] == "commodities"
    assert payload["dispatch_failure"]["dispatch_posture"] == "ready_to_dispatch"


LIVE_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp"


def _clear_caches() -> None:
    make_engine.cache_clear()
    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("argv", "expected_error"),
    [
        (["fsj_support_dispatch_failure_status.py", "--latest", "--agent-domain", "macro", "--format", "json"], "DATABASE_URL must be set explicitly"),
        (["fsj_support_dispatch_failure_status.py", "--latest", "--agent-domain", "macro", "--format", "json"], "canonical/live DB"),
    ],
)
def test_support_dispatch_failure_latest_entrypoint_blocks_default_store_live_db_paths_under_pytest(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    expected_error: str,
) -> None:
    if expected_error == "canonical/live DB":
        monkeypatch.setenv("DATABASE_URL", LIVE_DB_URL)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    _clear_caches()
    monkeypatch.setattr("sys.argv", argv)

    with pytest.raises(LiveIsolationError, match=expected_error):
        _module.main()


def test_build_dispatch_failure_payload_blocks_via_support_status_default_store_under_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    _clear_caches()

    with pytest.raises(LiveIsolationError, match="DATABASE_URL must be set explicitly"):
        build_dispatch_failure_payload(business_date="2099-04-23", agent_domain="macro")
