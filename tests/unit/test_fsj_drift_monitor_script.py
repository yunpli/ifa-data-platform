from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_drift_monitor.py"
_spec = importlib.util.spec_from_file_location("fsj_drift_monitor_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
build_drift_payload = _module.build_drift_payload
build_fleet_drift_digest = _module.build_fleet_drift_digest
format_fleet_drift_digest_line = _module.format_fleet_drift_digest_line
resolve_latest_business_dates = _module.resolve_latest_business_dates
_print_text = _module._print_text


class _DummyStore:
    def __init__(self) -> None:
        self.list_calls: list[dict] = []
        self.surface_calls: list[dict] = []

    def list_report_business_dates(self, **kwargs: object) -> list[str]:
        self.list_calls.append(dict(kwargs))
        return ["2099-04-23", "2099-04-22", "2099-04-21"]

    def get_active_report_operator_review_surface(self, **kwargs: object) -> dict | None:
        self.surface_calls.append(dict(kwargs))
        business_date = str(kwargs["business_date"])
        if business_date == "2099-04-23":
            return {
                "artifact": {"artifact_id": "main-3", "report_run_id": "run-3"},
                "state": {
                    "recommended_action": "send",
                    "workflow_state": "ready_to_send",
                    "send_ready": True,
                    "review_required": False,
                    "qa_axes": {
                        "structural": {"ready": True, "blocker_count": 0, "warning_count": 0},
                        "lineage": {"ready": True, "blocker_count": 0, "warning_count": 0},
                        "policy": {"ready": True, "blocker_count": 0, "warning_count": 0},
                    },
                },
                "review_summary": {"qa_score": 97, "blocker_count": 0, "warning_count": 0},
                "candidate_comparison": {"current_artifact_id": "main-3", "selected_artifact_id": "main-3"},
                "selected_handoff": {"selected_artifact_id": "main-3", "selected_is_current": True},
                "llm_lineage": {"summary": {"bundle_count": 2, "applied_count": 2, "degraded_count": 0, "fallback_applied_count": 0, "missing_bundle_count": 0, "operator_tags": []}},
                "llm_lineage_summary": {"status": "applied", "summary_line": "applied [applied=2/2 | primary=2]", "models": ["grok41_thinking"], "slots": ["late"], "token_totals": {"total_tokens": 400}, "usage_bundle_count": 2, "uncosted_bundle_count": 0, "estimated_cost_usd": 0.008},
            }
        if business_date == "2099-04-22":
            return {
                "artifact": {"artifact_id": "main-2", "report_run_id": "run-2"},
                "state": {
                    "recommended_action": "send_review",
                    "workflow_state": "review_required",
                    "send_ready": False,
                    "review_required": True,
                    "qa_axes": {
                        "structural": {"ready": True, "blocker_count": 0, "warning_count": 0},
                        "lineage": {"ready": True, "blocker_count": 0, "warning_count": 1},
                        "policy": {"ready": True, "blocker_count": 0, "warning_count": 0},
                    },
                },
                "review_summary": {"qa_score": 91, "blocker_count": 0, "warning_count": 2},
                "candidate_comparison": {"current_artifact_id": "main-2", "selected_artifact_id": "main-2-selected"},
                "selected_handoff": {"selected_artifact_id": "main-2-selected", "selected_is_current": False},
                "llm_lineage": {"summary": {"bundle_count": 2, "applied_count": 1, "degraded_count": 1, "fallback_applied_count": 1, "missing_bundle_count": 0, "operator_tags": ["llm_timeout"]}},
                "llm_lineage_summary": {"status": "degraded", "summary_line": "degraded [applied=1/2 | fallback=1 | degraded=1 | tags=llm_timeout]", "models": ["gemini31_pro_jmr"], "slots": ["mid"], "token_totals": {"total_tokens": 600}, "usage_bundle_count": 2, "uncosted_bundle_count": 2, "estimated_cost_usd": None},
            }
        return {
            "artifact": {"artifact_id": "main-1", "report_run_id": "run-1"},
            "state": {
                "recommended_action": "hold",
                "workflow_state": "blocked",
                "send_ready": False,
                "review_required": False,
                "qa_axes": {
                    "structural": {"ready": True, "blocker_count": 0, "warning_count": 0},
                    "lineage": {"ready": False, "blocker_count": 1, "warning_count": 0},
                    "policy": {"ready": True, "blocker_count": 0, "warning_count": 0},
                },
            },
            "review_summary": {"qa_score": 83, "blocker_count": 1, "warning_count": 0},
            "candidate_comparison": {"current_artifact_id": "main-1", "selected_artifact_id": "main-1"},
            "selected_handoff": {"selected_artifact_id": "main-1", "selected_is_current": True},
            "llm_lineage": {"summary": {"bundle_count": 2, "applied_count": 0, "degraded_count": 0, "fallback_applied_count": 0, "missing_bundle_count": 1, "operator_tags": ["missing_bundle"]}},
            "llm_lineage_summary": {"status": "incomplete", "summary_line": "incomplete [applied=0/2 | missing=1 | tags=missing_bundle]", "models": ["grok41_thinking"], "slots": ["early"], "token_totals": {"total_tokens": 200}, "usage_bundle_count": 1, "uncosted_bundle_count": 1, "estimated_cost_usd": None},
        }


def test_resolve_latest_business_dates_uses_store_truth() -> None:
    store = _DummyStore()

    business_dates = resolve_latest_business_dates(scope="main", days=3, store=store)

    assert business_dates == ["2099-04-23", "2099-04-22", "2099-04-21"]
    assert store.list_calls == [
        {
            "agent_domain": "main",
            "artifact_family": "main_final_report",
            "statuses": ["active"],
            "limit": 3,
            "max_business_date": store.list_calls[0]["max_business_date"],
        }
    ]


def test_build_drift_payload_summarizes_multi_day_operator_drift() -> None:
    store = _DummyStore()

    payload = build_drift_payload(scope="main", days=3, store=store)

    assert payload["scope"] == "main"
    assert payload["reported_day_count"] == 3
    assert payload["aggregate"]["posture_counts"] == {"ready_to_send": 1, "review_required": 1, "blocked": 1}
    assert payload["aggregate"]["posture_rates"] == {"ready_to_send": 0.3333, "review_required": 0.3333, "blocked": 0.3333}
    assert payload["aggregate"]["qa_posture_counts"] == {"ready": 1, "attention": 1, "blocked": 1}
    assert payload["aggregate"]["lineage_status_counts"] == {"applied": 1, "degraded": 1, "incomplete": 1}
    assert payload["aggregate"]["lineage_attention_rate"] == 0.6667
    assert payload["aggregate"]["qa_attention_rate"] == 0.6667
    assert payload["aggregate"]["qa_blocked_rate"] == 0.3333
    assert payload["aggregate"]["selection_mismatch_rate"] == 0.3333
    assert payload["aggregate"]["llm_fallback_rate"] == 0.3333
    assert payload["aggregate"]["llm_degraded_rate"] == 0.3333
    assert payload["aggregate"]["llm_missing_bundle_rate"] == 0.3333
    assert payload["aggregate"]["average_qa_score"] == 90.33
    assert payload["aggregate"]["max_blocker_count"] == 1
    assert payload["aggregate"]["max_warning_count"] == 2
    assert payload["aggregate"]["attention_dates"] == ["2099-04-22", "2099-04-21"]
    assert payload["aggregate"]["selection_mismatch_dates"] == ["2099-04-22"]
    assert payload["aggregate"]["llm_fallback_dates"] == ["2099-04-22"]
    assert payload["aggregate"]["llm_degraded_dates"] == ["2099-04-22"]
    assert payload["aggregate"]["llm_missing_bundle_dates"] == ["2099-04-21"]
    assert payload["aggregate"]["llm_operator_tags"] == ["llm_timeout", "missing_bundle"]
    assert payload["aggregate"]["llm_model_counts"] == {"gemini31_pro_jmr": 1, "grok41_thinking": 2}
    assert payload["aggregate"]["llm_slot_counts"] == {"early": 1, "late": 1, "mid": 1}
    assert payload["aggregate"]["llm_total_tokens"] == 1200
    assert payload["aggregate"]["llm_usage_bundle_count"] == 5
    assert payload["aggregate"]["llm_uncosted_bundle_count"] == 3
    assert payload["aggregate"]["llm_estimated_cost_usd"] == 0.008
    assert payload["aggregate"]["recent_streaks"] == {
        "blocked": 0,
        "review_required": 0,
        "lineage_attention": 0,
        "qa_attention": 0,
        "qa_blocked": 0,
        "selection_mismatch": 0,
        "llm_fallback": 0,
        "llm_degraded": 0,
        "llm_missing_bundle": 0,
    }
    assert payload["aggregate"]["selection_mismatch_dates"] == ["2099-04-22"]
    assert payload["days"][1]["posture"] == "review_required"
    assert payload["days"][1]["selection_mismatch"] is True
    assert payload["days"][2]["qa_posture"] == "blocked"
    assert payload["days"][2]["not_ready_axes"] == ["lineage"]


def test_resolve_latest_business_dates_with_slot_filters_to_matching_surfaces() -> None:
    class SlotStore(_DummyStore):
        def list_report_business_dates(self, **kwargs: object) -> list[str]:
            self.list_calls.append(dict(kwargs))
            return ["2099-04-23", "2099-04-22", "2099-04-21", "2099-04-20"]

        def get_active_report_delivery_surface(self, **kwargs: object) -> dict | None:
            self.surface_calls.append(dict(kwargs))
            business_date = str(kwargs["business_date"])
            slot = "late" if business_date in {"2099-04-22", "2099-04-20"} else "early"
            return {"delivery_package": {"slot_evaluation": {"strongest_slot": slot}}}

    store = SlotStore()
    business_dates = resolve_latest_business_dates(scope="main", days=2, slot="late", store=store)

    assert business_dates == ["2099-04-22", "2099-04-20"]
    assert store.list_calls[0]["limit"] == 20
    assert len(store.surface_calls) == 4


def test_print_text_emits_operator_visible_trend_lines(capsys) -> None:
    payload = {
        "scope": "main",
        "agent_domain": "main",
        "artifact_family": "main_final_report",
        "window_days": 3,
        "reported_day_count": 3,
        "business_dates": ["2099-04-23", "2099-04-22", "2099-04-21"],
        "days": [
            {
                "business_date": "2099-04-23",
                "artifact_id": "main-3",
                "posture": "ready_to_send",
                "qa_posture": "ready",
                "llm_lineage_status": "applied",
                "llm_fallback_count": 0,
                "llm_models": ["grok41_thinking"],
                "llm_slots": ["late"],
                "llm_total_tokens": 400,
                "llm_estimated_cost_usd": 0.008,
                "llm_uncosted_bundle_count": 0,
                "selection_mismatch": False,
                "axes_with_attention": [],
                "not_ready_axes": [],
            },
            {
                "business_date": "2099-04-22",
                "artifact_id": "main-2",
                "posture": "review_required",
                "qa_posture": "attention",
                "llm_lineage_status": "degraded",
                "llm_fallback_count": 1,
                "llm_models": ["gemini31_pro_jmr"],
                "llm_slots": ["mid"],
                "llm_total_tokens": 600,
                "llm_estimated_cost_usd": None,
                "llm_uncosted_bundle_count": 2,
                "selection_mismatch": True,
                "axes_with_attention": ["lineage"],
                "not_ready_axes": [],
            },
        ],
        "aggregate": {
            "posture_counts": {"ready_to_send": 1, "review_required": 1, "blocked": 1},
            "posture_rates": {"ready_to_send": 0.3333, "review_required": 0.3333, "blocked": 0.3333},
            "qa_posture_counts": {"ready": 1, "attention": 1, "blocked": 1},
            "qa_posture_rates": {"ready": 0.3333, "attention": 0.3333, "blocked": 0.3333},
            "lineage_status_counts": {"applied": 1, "degraded": 1, "incomplete": 1},
            "lineage_attention_rate": 0.6667,
            "qa_attention_rate": 0.6667,
            "qa_blocked_rate": 0.3333,
            "selection_mismatch_rate": 0.3333,
            "llm_fallback_rate": 0.3333,
            "llm_degraded_rate": 0.3333,
            "llm_missing_bundle_rate": 0.3333,
            "average_qa_score": 90.33,
            "max_blocker_count": 1,
            "max_warning_count": 2,
            "attention_dates": ["2099-04-22", "2099-04-21"],
            "qa_attention_dates": ["2099-04-22", "2099-04-21"],
            "qa_blocked_dates": ["2099-04-21"],
            "selection_mismatch_dates": ["2099-04-22"],
            "llm_fallback_dates": ["2099-04-22"],
            "llm_degraded_dates": ["2099-04-22"],
            "llm_missing_bundle_dates": ["2099-04-21"],
            "llm_operator_tags": ["llm_timeout", "missing_bundle"],
            "llm_model_counts": {"gemini31_pro_jmr": 1, "grok41_thinking": 2},
            "llm_slot_counts": {"early": 1, "late": 1, "mid": 1},
            "llm_total_tokens": 1200,
            "llm_usage_bundle_count": 5,
            "llm_uncosted_bundle_count": 3,
            "llm_estimated_cost_usd": 0.008,
            "recent_streaks": {
                "blocked": 0,
                "lineage_attention": 0,
                "llm_degraded": 0,
                "llm_fallback": 0,
                "llm_missing_bundle": 0,
                "qa_attention": 0,
                "qa_blocked": 0,
                "review_required": 0,
                "selection_mismatch": 0,
            },
        },
    }

    _print_text(payload)
    output = capsys.readouterr().out

    assert "scope=main" in output
    assert "reported_day_count=3" in output
    assert "business_dates=2099-04-23,2099-04-22,2099-04-21" in output
    assert "posture_counts=ready_to_send:1,review_required:1,blocked:1" in output
    assert "posture_rates=ready_to_send:0.3333,review_required:0.3333,blocked:0.3333" in output
    assert "qa_posture_counts=ready:1,attention:1,blocked:1" in output
    assert "lineage_status_counts=applied:1,degraded:1,incomplete:1" in output
    assert "selection_mismatch_rate=0.3333" in output
    assert "llm_fallback_rate=0.3333" in output
    assert "llm_missing_bundle_dates=2099-04-21" in output
    assert "llm_operator_tags=llm_timeout,missing_bundle" in output
    assert "llm_model_counts=gemini31_pro_jmr:1,grok41_thinking:2" in output
    assert "llm_slot_counts=early:1,late:1,mid:1" in output
    assert "llm_total_tokens=1200" in output
    assert "llm_usage_bundle_count=5" in output
    assert "llm_uncosted_bundle_count=3" in output
    assert "llm_estimated_cost_usd=0.008" in output
    assert "recent_streaks=blocked:0,lineage_attention:0,llm_degraded:0,llm_fallback:0,llm_missing_bundle:0,qa_attention:0,qa_blocked:0,review_required:0,selection_mismatch:0" in output
    assert "summary_line=3d drift main: hold 1/3 | fallback 1/3 | mismatch 1/3 | qa_attn 2/3" in output
    assert "day_1=business_date:2099-04-23|artifact_id:main-3|posture:ready_to_send|qa_posture:ready|llm_lineage_status:applied|llm_fallback_count:0|llm_models:grok41_thinking|llm_slots:late|llm_total_tokens:400|llm_estimated_cost_usd:0.008|llm_uncosted_bundle_count:0|selection_mismatch:False|axes_attention:|not_ready_axes:" in output
    assert "day_2=business_date:2099-04-22|artifact_id:main-2|posture:review_required|qa_posture:attention|llm_lineage_status:degraded|llm_fallback_count:1|llm_models:gemini31_pro_jmr|llm_slots:mid|llm_total_tokens:600|llm_estimated_cost_usd:None|llm_uncosted_bundle_count:2|selection_mismatch:True|axes_attention:lineage|not_ready_axes:" in output


def test_build_drift_payload_tracks_recent_streaks_for_latest_days() -> None:
    class StreakStore(_DummyStore):
        def list_report_business_dates(self, **kwargs: object) -> list[str]:
            self.list_calls.append(dict(kwargs))
            return ["2099-04-23", "2099-04-22", "2099-04-21"]

        def get_active_report_operator_review_surface(self, **kwargs: object) -> dict | None:
            business_date = str(kwargs["business_date"])
            base = {
                "artifact": {"artifact_id": f"main-{business_date}", "report_run_id": f"run-{business_date}"},
                "candidate_comparison": {"current_artifact_id": f"main-{business_date}", "selected_artifact_id": f"main-{business_date}"},
                "selected_handoff": {"selected_artifact_id": f"main-{business_date}", "selected_is_current": True},
            }
            if business_date in {"2099-04-23", "2099-04-22"}:
                return {
                    **base,
                    "state": {
                        "recommended_action": "hold",
                        "workflow_state": "blocked",
                        "send_ready": False,
                        "review_required": False,
                        "qa_axes": {
                            "structural": {"ready": True, "blocker_count": 0, "warning_count": 0},
                            "lineage": {"ready": True, "blocker_count": 0, "warning_count": 0},
                            "policy": {"ready": True, "blocker_count": 0, "warning_count": 1},
                        },
                    },
                    "review_summary": {"qa_score": 88, "blocker_count": 0, "warning_count": 1},
                    "llm_lineage": {"summary": {"bundle_count": 1, "applied_count": 1, "degraded_count": 0, "fallback_applied_count": 1, "missing_bundle_count": 0, "operator_tags": ["llm_timeout"]}},
                    "llm_lineage_summary": {"status": "degraded", "summary_line": "degraded", "models": ["grok41_thinking"], "slots": ["late"], "token_totals": {"total_tokens": 100}, "usage_bundle_count": 1, "uncosted_bundle_count": 0, "estimated_cost_usd": 0.001},
                }
            return {
                **base,
                "state": {
                    "recommended_action": "send",
                    "workflow_state": "ready_to_send",
                    "send_ready": True,
                    "review_required": False,
                    "qa_axes": {
                        "structural": {"ready": True, "blocker_count": 0, "warning_count": 0},
                        "lineage": {"ready": True, "blocker_count": 0, "warning_count": 0},
                        "policy": {"ready": True, "blocker_count": 0, "warning_count": 0},
                    },
                },
                "review_summary": {"qa_score": 96, "blocker_count": 0, "warning_count": 0},
                "llm_lineage": {"summary": {"bundle_count": 1, "applied_count": 1, "degraded_count": 0, "fallback_applied_count": 0, "missing_bundle_count": 0, "operator_tags": []}},
                "llm_lineage_summary": {"status": "applied", "summary_line": "applied", "models": ["grok41_thinking"], "slots": ["late"], "token_totals": {"total_tokens": 100}, "usage_bundle_count": 1, "uncosted_bundle_count": 0, "estimated_cost_usd": 0.001},
            }

    payload = build_drift_payload(scope="main", days=3, store=StreakStore())

    assert payload["aggregate"]["recent_streaks"] == {
        "blocked": 2,
        "review_required": 0,
        "lineage_attention": 2,
        "qa_attention": 2,
        "qa_blocked": 0,
        "selection_mismatch": 0,
        "llm_fallback": 2,
        "llm_degraded": 0,
        "llm_missing_bundle": 0,
    }
    assert (
        _module.format_drift_summary_line(payload)
        == "3d drift main: hold 2/3 | fallback 2/3 | mismatch 0/3 | qa_attn 2/3 | recent hold_streak=2; fallback_streak=2; qa_attn_streak=2"
    )


def test_build_fleet_drift_digest_aggregates_main_vs_support_groups() -> None:
    main_payload = build_drift_payload(scope="main", days=3, store=_DummyStore())
    digest = build_fleet_drift_digest(
        {
            "main": main_payload,
            "support:ai_tech": {
                "scope": "support:ai_tech",
                "reported_day_count": 2,
                "aggregate": {
                    "posture_counts": {"blocked": 1},
                    "llm_fallback_dates": ["2099-04-22"],
                    "selection_mismatch_dates": [],
                    "qa_attention_dates": ["2099-04-23"],
                    "llm_model_counts": {"grok41_thinking": 2},
                    "llm_slot_counts": {"early": 2},
                    "llm_total_tokens": 700,
                    "llm_usage_bundle_count": 2,
                    "llm_uncosted_bundle_count": 1,
                    "llm_estimated_cost_usd": 0.014,
                },
            },
            "support:macro": {
                "scope": "support:macro",
                "reported_day_count": 2,
                "aggregate": {
                    "posture_counts": {"blocked": 0},
                    "llm_fallback_dates": [],
                    "selection_mismatch_dates": ["2099-04-21"],
                    "qa_attention_dates": ["2099-04-21"],
                    "llm_model_counts": {"gemini31_pro_jmr": 1},
                    "llm_slot_counts": {"late": 1},
                    "llm_total_tokens": 350,
                    "llm_usage_bundle_count": 1,
                    "llm_uncosted_bundle_count": 1,
                    "llm_estimated_cost_usd": None,
                },
            },
            "support:commodities": {
                "scope": "support:commodities",
                "reported_day_count": 1,
                "aggregate": {
                    "posture_counts": {"blocked": 1},
                    "llm_fallback_dates": ["2099-04-20"],
                    "selection_mismatch_dates": ["2099-04-20"],
                    "qa_attention_dates": [],
                    "llm_model_counts": {"grok41_thinking": 1},
                    "llm_slot_counts": {"late": 1},
                    "llm_total_tokens": 250,
                    "llm_usage_bundle_count": 1,
                    "llm_uncosted_bundle_count": 0,
                    "llm_estimated_cost_usd": 0.005,
                },
            },
        }
    )

    assert digest["window_days"] == 3
    assert digest["main"] == {
        "label": "main",
        "scope_count": 1,
        "reported_day_count": 3,
        "hold_count": 1,
        "fallback_count": 1,
        "mismatch_count": 1,
        "qa_attention_count": 2,
        "llm_model_counts": {"gemini31_pro_jmr": 1, "grok41_thinking": 2},
        "llm_slot_counts": {"early": 1, "late": 1, "mid": 1},
        "llm_total_tokens": 1200,
        "llm_usage_bundle_count": 5,
        "llm_uncosted_bundle_count": 3,
        "llm_estimated_cost_usd": 0.008,
    }
    assert digest["support"] == {
        "label": "support",
        "scope_count": 3,
        "reported_day_count": 5,
        "hold_count": 2,
        "fallback_count": 2,
        "mismatch_count": 2,
        "qa_attention_count": 2,
        "llm_model_counts": {"gemini31_pro_jmr": 1, "grok41_thinking": 3},
        "llm_slot_counts": {"early": 2, "late": 2},
        "llm_total_tokens": 1300,
        "llm_usage_bundle_count": 4,
        "llm_uncosted_bundle_count": 2,
        "llm_estimated_cost_usd": 0.019,
    }
    assert (
        format_fleet_drift_digest_line(digest)
        == "3d fleet drift: main hold 1/3 (1 scope) | fallback 1/3 | mismatch 1/3 | qa_attn 2/3 || support hold 2/5 (3 scope) | fallback 2/5 | mismatch 2/5 | qa_attn 2/5"
    )
