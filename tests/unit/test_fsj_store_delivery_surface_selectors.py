from __future__ import annotations

import uuid

import pytest

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.store import FSJStore


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"


def _clear_caches() -> None:
    make_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture()
def store(monkeypatch: pytest.MonkeyPatch) -> FSJStore:
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    _clear_caches()
    instance = FSJStore(database_url=TEST_DB_URL)
    try:
        yield instance
    finally:
        instance.engine.dispose()


def _artifact_payload(*, artifact_id: str, business_date: str, status: str = "active", strongest_slot: str = "late") -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "artifact_family": "main_final_report",
        "market": "cn",
        "business_date": business_date,
        "agent_domain": "main",
        "render_format": "html",
        "artifact_type": "report",
        "content_type": "text/html",
        "title": f"Main report {artifact_id}",
        "status": status,
        "report_run_id": f"run-{artifact_id}",
        "artifact_uri": f"file:///tmp/{artifact_id}.html",
        "metadata_json": {
            "delivery_package": {
                "slot": strongest_slot,
                "slot_evaluation": {"strongest_slot": strongest_slot},
                "workflow": {
                    "workflow_state": "ready_to_send",
                    "recommended_action": "send",
                    "next_step": "send_selected_package_to_primary_channel",
                    "package_state": "ready",
                    "ready_for_delivery": True,
                    "send_ready": True,
                    "review_required": False,
                    "selection_reason": f"selected {artifact_id}",
                    "dispatch_selected_artifact_id": artifact_id,
                    "qa_score": 1.0,
                    "blocker_count": 0,
                    "warning_count": 0,
                },
            },
            "workflow_linkage": {
                "selected_handoff": {
                    "selected_artifact_id": artifact_id,
                    "selected_is_current": True,
                }
            },
            "review_surface": {
                "operator_go_no_go": {
                    "decision": "GO",
                    "rationale": "quality gate and artifact integrity both pass",
                    "next_step": "send_selected_package_to_primary_channel",
                    "action_required": False,
                }
            },
        },
    }


def test_get_latest_active_report_delivery_surface_respects_slot_and_max_business_date(store: FSJStore) -> None:
    old_artifact_id = f"test-main-old-{uuid.uuid4().hex}"
    current_artifact_id = f"test-main-current-{uuid.uuid4().hex}"
    future_artifact_id = f"test-main-future-{uuid.uuid4().hex}"

    store.register_report_artifact(_artifact_payload(artifact_id=old_artifact_id, business_date="2099-04-22", strongest_slot="early"))
    store.register_report_artifact(_artifact_payload(artifact_id=current_artifact_id, business_date="2099-04-23", strongest_slot="late"))
    store.register_report_artifact(_artifact_payload(artifact_id=future_artifact_id, business_date="2099-04-24", strongest_slot="late"))

    resolved = store.get_latest_active_report_delivery_surface(
        agent_domain="main",
        artifact_family="main_final_report",
        strongest_slot="late",
        max_business_date="2099-04-23",
    )

    assert resolved is not None
    assert resolved["artifact"]["artifact_id"] == current_artifact_id
    assert str(resolved["artifact"]["business_date"]) == "2099-04-23"
    assert resolved["delivery_package"]["slot_evaluation"]["strongest_slot"] == "late"


def test_register_active_report_artifact_supersedes_previous_active_and_surfaces_active_first(store: FSJStore) -> None:
    first_artifact_id = f"test-main-first-{uuid.uuid4().hex}"
    second_artifact_id = f"test-main-second-{uuid.uuid4().hex}"
    business_date = "2099-04-25"

    store.register_report_artifact(_artifact_payload(artifact_id=first_artifact_id, business_date=business_date, strongest_slot="mid"))
    second = store.register_report_artifact(_artifact_payload(artifact_id=second_artifact_id, business_date=business_date, strongest_slot="late"))

    active = store.get_active_report_delivery_surface(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
    )
    history = store.list_report_delivery_surfaces(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
        statuses=["active", "superseded"],
        limit=5,
    )
    first_after = store.get_report_artifact(first_artifact_id)

    assert second["supersedes_artifact_id"] == first_artifact_id
    assert first_after is not None
    assert first_after["status"] == "superseded"
    assert active is not None
    assert active["artifact"]["artifact_id"] == second_artifact_id
    assert [item["artifact"]["artifact_id"] for item in history[:2]] == [second_artifact_id, first_artifact_id]
    assert [item["artifact"]["status"] for item in history[:2]] == ["active", "superseded"]


def test_operator_review_selector_reuses_canonical_active_surface_after_supersede(store: FSJStore) -> None:
    superseded_artifact_id = f"test-main-superseded-{uuid.uuid4().hex}"
    active_artifact_id = f"test-main-active-{uuid.uuid4().hex}"
    business_date = "2099-04-26"

    store.register_report_artifact(_artifact_payload(artifact_id=superseded_artifact_id, business_date=business_date, strongest_slot="early"))
    store.register_report_artifact(_artifact_payload(artifact_id=active_artifact_id, business_date=business_date, strongest_slot="late"))

    review_surface = store.get_active_report_operator_review_surface(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
    )
    review_history = store.list_report_operator_review_surfaces(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
        statuses=["active", "superseded"],
        limit=5,
    )

    assert review_surface is not None
    assert review_surface["artifact"]["artifact_id"] == active_artifact_id
    assert review_surface["selected_handoff"]["selected_is_current"] is True
    assert review_surface["state"]["workflow_state"] == "ready_to_send"
    assert [item["artifact"]["artifact_id"] for item in review_history[:2]] == [active_artifact_id, superseded_artifact_id]
    assert review_history[1]["canonical_lifecycle"]["state"] == "superseded"
    assert review_history[1]["canonical_lifecycle"]["reason"] == "artifact_status_superseded"
