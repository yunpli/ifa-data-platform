from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_source_health_status.py"
_spec = importlib.util.spec_from_file_location("fsj_source_health_status_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
build_source_health_status_payload = _module.build_source_health_status_payload
_print_text = _module._print_text


class _FakeStore:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def build_operator_board_surface(self, *, business_date=None, history_limit=5):
        return self._payload



def test_build_source_health_status_payload_filters_to_attention_subjects() -> None:
    board_payload = {
        "business_date": "2099-04-23",
        "resolution": {"mode": "explicit_business_date"},
        "main": {
            "artifact": {"artifact_id": "main-1", "business_date": "2099-04-23"},
            "state": {"recommended_action": "hold", "workflow_state": "blocked"},
            "canonical_lifecycle": {"state": "held", "reason": "source_health_blocked"},
            "review_summary": {
                "source_health": {
                    "overall_status": "blocked",
                    "blocking_slot_count": 1,
                    "degraded_slot_count": 0,
                    "slots": [
                        {
                            "slot": "late",
                            "status": "blocked",
                            "degrade_reason": "same_day_final_structure_missing",
                            "contract_mode": "historical_only",
                        }
                    ],
                }
            },
        },
        "support": {
            "macro": {
                "artifact": {"artifact_id": "macro-1", "business_date": "2099-04-23"},
                "state": {"recommended_action": "send", "workflow_state": "ready_to_send"},
                "canonical_lifecycle": {"state": "send_ready", "reason": "ready_for_delivery_send"},
                "review_summary": {
                    "source_health": {
                        "overall_status": "healthy",
                        "blocking_slot_count": 0,
                        "degraded_slot_count": 0,
                        "slots": [],
                    }
                },
            },
            "commodities": {
                "artifact": {"artifact_id": "commodities-1", "business_date": "2099-04-23"},
                "state": {"recommended_action": "send_review", "workflow_state": "review_required"},
                "canonical_lifecycle": {"state": "review_ready", "reason": "manual_review_required"},
                "review_summary": {
                    "source_health": {
                        "overall_status": "degraded",
                        "blocking_slot_count": 0,
                        "degraded_slot_count": 1,
                        "slots": [
                            {
                                "slot": "early",
                                "status": "degraded",
                                "degrade_reason": "missing_background_support",
                            }
                        ],
                    }
                },
            },
            "ai_tech": {
                "artifact": {"artifact_id": "ai-tech-1", "business_date": "2099-04-23"},
                "state": {"recommended_action": "send", "workflow_state": "ready_to_send"},
                "canonical_lifecycle": {"state": "send_ready", "reason": "ready_for_delivery_send"},
                "review_summary": {
                    "source_health": {
                        "overall_status": "healthy",
                        "blocking_slot_count": 0,
                        "degraded_slot_count": 0,
                        "slots": [],
                    }
                },
            },
        },
    }

    payload = build_source_health_status_payload(store=_FakeStore(board_payload))

    assert payload["business_date"] == "2099-04-23"
    assert payload["fleet"]["overall_status"] == "blocked"
    assert payload["fleet"]["attention_subjects"] == ["main", "support:commodities"]
    assert payload["fleet"]["blocked_subjects"] == ["main"]
    assert payload["fleet"]["degraded_subjects"] == ["support:commodities"]
    assert payload["fleet"]["status_counts"] == {"blocked": 1, "healthy": 2, "degraded": 1}
    assert [item["subject"] for item in payload["subjects"]] == ["main", "support:commodities"]
    assert payload["subjects"][0]["summary_line"] == (
        "main: blocked | blocking_slots=1 | reasons=same_day_final_structure_missing"
        " | slots=late:blocked:same_day_final_structure_missing | action=hold | lifecycle=held"
    )
    assert payload["subjects"][1]["summary_line"] == (
        "support:commodities: degraded | degraded_slots=1 | reasons=missing_background_support"
        " | slots=early:degraded:missing_background_support | action=send_review | lifecycle=review_ready"
    )



def test_build_source_health_status_payload_can_include_healthy_subjects() -> None:
    board_payload = {
        "business_date": "2099-04-23",
        "resolution": {"mode": "latest_active_lookup"},
        "main": {
            "artifact": {"artifact_id": "main-1", "business_date": "2099-04-23"},
            "state": {"recommended_action": "send", "workflow_state": "ready_to_send"},
            "canonical_lifecycle": {"state": "send_ready", "reason": "ready_for_delivery_send"},
            "review_summary": {"source_health": {"overall_status": "healthy", "slots": []}},
        },
        "support": {},
    }

    payload = build_source_health_status_payload(store=_FakeStore(board_payload), include_healthy=True)

    assert payload["fleet"]["overall_status"] == "healthy"
    assert payload["fleet"]["attention_subjects"] == []
    assert payload["subjects"][0]["subject"] == "main"
    assert payload["subjects"][0]["summary_line"] == "main: healthy | action=send | lifecycle=send_ready"



def test_print_text_emits_fleet_and_subject_lines(capsys) -> None:
    payload = {
        "business_date": "2099-04-23",
        "resolution": {"mode": "explicit_business_date"},
        "include_healthy": False,
        "fleet": {
            "summary_line": "source-health fleet: blocked | attention=2/4 | blocked=1 | degraded=1",
            "status_counts": {"blocked": 1, "degraded": 1, "healthy": 2},
            "attention_subjects": ["main", "support:commodities"],
            "blocked_subjects": ["main"],
            "degraded_subjects": ["support:commodities"],
        },
        "subjects": [
            {"summary_line": "main: blocked | blocking_slots=1 | reasons=same_day_final_structure_missing | slots=late:blocked:same_day_final_structure_missing | action=hold | lifecycle=held"},
            {"summary_line": "support:commodities: degraded | degraded_slots=1 | reasons=missing_background_support | slots=early:degraded:missing_background_support | action=send_review | lifecycle=review_ready"},
        ],
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "business_date=2099-04-23" in output
    assert "resolution_mode=explicit_business_date" in output
    assert "include_healthy=False" in output
    assert "fleet_summary=source-health fleet: blocked | attention=2/4 | blocked=1 | degraded=1" in output
    assert "fleet_status_counts=blocked:1,degraded:1,healthy:2" in output
    assert "attention_subjects=main,support:commodities" in output
    assert "blocked_subjects=main" in output
    assert "degraded_subjects=support:commodities" in output
    assert "subject_1=main: blocked | blocking_slots=1 | reasons=same_day_final_structure_missing | slots=late:blocked:same_day_final_structure_missing | action=hold | lifecycle=held" in output
    assert "subject_2=support:commodities: degraded | degraded_slots=1 | reasons=missing_background_support | slots=early:degraded:missing_background_support | action=send_review | lifecycle=review_ready" in output
