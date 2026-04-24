from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_llm_fallback_status.py"
_spec = importlib.util.spec_from_file_location("fsj_llm_fallback_status_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
build_fallback_status_payload = _module.build_fallback_status_payload
_print_text = _module._print_text


def test_build_fallback_status_payload_filters_to_attention_scopes(monkeypatch) -> None:
    payloads = {
        "main": {
            "reported_day_count": 3,
            "business_dates": ["2099-04-23", "2099-04-22", "2099-04-21"],
            "aggregate": {
                "attention_dates": ["2099-04-22"],
                "qa_attention_dates": ["2099-04-22"],
                "qa_blocked_dates": [],
                "llm_fallback_dates": ["2099-04-22"],
                "llm_degraded_dates": ["2099-04-22"],
                "llm_missing_bundle_dates": [],
                "llm_operator_tags": ["llm_timeout"],
                "llm_model_counts": {"gemini31_pro_jmr": 1, "grok41_thinking": 2},
                "llm_slot_counts": {"late": 2, "mid": 1},
                "llm_fallback_rate": 0.3333,
                "llm_degraded_rate": 0.3333,
                "llm_missing_bundle_rate": 0.0,
                "selection_mismatch_dates": [],
                "posture_counts": {"ready_to_send": 2, "review_required": 1, "blocked": 0},
                "lineage_status_counts": {"applied": 2, "degraded": 1},
            },
        },
        "support:macro": {
            "reported_day_count": 3,
            "business_dates": ["2099-04-23", "2099-04-22", "2099-04-21"],
            "aggregate": {
                "attention_dates": [],
                "qa_attention_dates": [],
                "qa_blocked_dates": [],
                "llm_fallback_dates": [],
                "llm_degraded_dates": [],
                "llm_missing_bundle_dates": [],
                "llm_operator_tags": [],
                "llm_model_counts": {"grok41_thinking": 1},
                "llm_slot_counts": {"early": 1},
                "llm_fallback_rate": 0.0,
                "llm_degraded_rate": 0.0,
                "llm_missing_bundle_rate": 0.0,
                "selection_mismatch_dates": [],
                "posture_counts": {"ready_to_send": 3, "review_required": 0, "blocked": 0},
                "lineage_status_counts": {"applied": 3},
            },
        },
        "support:commodities": {
            "reported_day_count": 2,
            "business_dates": ["2099-04-23", "2099-04-22"],
            "aggregate": {
                "attention_dates": ["2099-04-23"],
                "qa_attention_dates": [],
                "qa_blocked_dates": ["2099-04-23"],
                "llm_fallback_dates": [],
                "llm_degraded_dates": [],
                "llm_missing_bundle_dates": ["2099-04-23"],
                "llm_operator_tags": ["missing_bundle"],
                "llm_model_counts": {"grok41_thinking": 1},
                "llm_slot_counts": {"late": 1},
                "llm_fallback_rate": 0.0,
                "llm_degraded_rate": 0.0,
                "llm_missing_bundle_rate": 0.5,
                "selection_mismatch_dates": ["2099-04-23"],
                "posture_counts": {"ready_to_send": 1, "review_required": 0, "blocked": 1},
                "lineage_status_counts": {"applied": 1, "incomplete": 1},
            },
        },
        "support:ai_tech": {
            "reported_day_count": 1,
            "business_dates": ["2099-04-23"],
            "aggregate": {
                "attention_dates": [],
                "qa_attention_dates": [],
                "qa_blocked_dates": [],
                "llm_fallback_dates": [],
                "llm_degraded_dates": [],
                "llm_missing_bundle_dates": [],
                "llm_operator_tags": [],
                "llm_model_counts": {},
                "llm_slot_counts": {},
                "llm_fallback_rate": 0.0,
                "llm_degraded_rate": 0.0,
                "llm_missing_bundle_rate": 0.0,
                "selection_mismatch_dates": [],
                "posture_counts": {"ready_to_send": 1, "review_required": 0, "blocked": 0},
                "lineage_status_counts": {"not_applied": 1},
            },
        },
    }

    monkeypatch.setattr(_module, "build_drift_payload", lambda *, scope, days, store=None: payloads[scope])

    payload = build_fallback_status_payload(days=3)

    assert payload["fleet_attention"]["scope_count"] == 4
    assert payload["fleet_attention"]["attention_scope_count"] == 2
    assert payload["fleet_attention"]["fallback_scope_count"] == 1
    assert payload["fleet_attention"]["missing_scope_count"] == 1
    assert payload["fleet_attention"]["attention_scopes"] == ["main", "support:commodities"]
    assert [item["scope"] for item in payload["scopes"]] == ["main", "support:commodities"]
    assert payload["scopes"][0]["summary_line"] == "main: 3d | fallback=2099-04-22 | degraded=2099-04-22 | tags=llm_timeout"
    assert payload["scopes"][1]["summary_line"] == "support:commodities: 2d | missing=2099-04-23 | qa_blocked=2099-04-23 | mismatch=2099-04-23 | tags=missing_bundle"


def test_print_text_emits_fleet_and_scope_lines(capsys) -> None:
    payload = {
        "window_days": 3,
        "include_clean": False,
        "fleet_attention": {
            "summary_line": "llm-fallback fleet: attention 2/4 | fallback_scopes=1 | degraded_scopes=1 | missing_scopes=1",
            "attention_scopes": ["main", "support:commodities"],
            "fallback_scopes": ["main"],
            "degraded_scopes": ["main"],
            "missing_scopes": ["support:commodities"],
        },
        "scopes": [
            {"summary_line": "main: 3d | fallback=2099-04-22 | degraded=2099-04-22 | tags=llm_timeout"},
            {"summary_line": "support:commodities: 2d | missing=2099-04-23 | qa_blocked=2099-04-23 | mismatch=2099-04-23 | tags=missing_bundle"},
        ],
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "window_days=3" in output
    assert "fleet_summary=llm-fallback fleet: attention 2/4 | fallback_scopes=1 | degraded_scopes=1 | missing_scopes=1" in output
    assert "attention_scopes=main,support:commodities" in output
    assert "fallback_scopes=main" in output
    assert "degraded_scopes=main" in output
    assert "missing_scopes=support:commodities" in output
    assert "scope_1=main: 3d | fallback=2099-04-22 | degraded=2099-04-22 | tags=llm_timeout" in output
    assert "scope_2=support:commodities: 2d | missing=2099-04-23 | qa_blocked=2099-04-23 | mismatch=2099-04-23 | tags=missing_bundle" in output
