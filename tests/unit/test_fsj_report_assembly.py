from __future__ import annotations

from ifa_data_platform.fsj.report_assembly import MainReportSectionAssembler


def _graph(
    *,
    slot: str,
    section_key: str,
    bundle_id: str,
    status: str = "active",
    supersedes_bundle_id: str | None = None,
    updated_at: str = "2099-04-22T12:00:00+08:00",
    summary: str | None = None,
    agent_domain: str = "main",
    producer: str | None = None,
    producer_version: str | None = None,
) -> dict:
    return {
        "bundle": {
            "bundle_id": bundle_id,
            "market": "a_share",
            "business_date": "2099-04-22",
            "slot": slot,
            "agent_domain": agent_domain,
            "section_key": section_key,
            "section_type": "thesis",
            "bundle_topic_key": f"{slot}:{section_key}",
            "producer": producer or f"ifa_data_platform.fsj.{slot}_{agent_domain}_producer",
            "producer_version": producer_version or f"phase1-{agent_domain}-{slot}-v1",
            "assembly_mode": "contract_driven_first_slice",
            "status": status,
            "supersedes_bundle_id": supersedes_bundle_id,
            "slot_run_id": f"slot-run-{slot}",
            "replay_id": f"replay-{slot}",
            "report_run_id": None,
            "summary": summary or f"{slot} summary",
            "updated_at": updated_at,
            "payload_json": {},
        },
        "objects": [
            {
                "fsj_kind": "fact",
                "object_key": f"fact:{slot}:market",
                "statement": f"{slot} fact",
                "object_type": "observation",
                "confidence": "medium",
                "evidence_level": "E2",
                "attributes_json": {"source_layer": slot},
                "invalidators": [],
                "priority": "p1",
                "direction": "neutral",
                "horizon": "same_day",
            },
            {
                "fsj_kind": "signal",
                "object_key": f"signal:{slot}:state",
                "statement": f"{slot} signal",
                "object_type": "confirmation",
                "signal_strength": "medium",
                "confidence": "medium",
                "evidence_level": "E2",
                "attributes_json": {},
                "invalidators": [],
                "priority": "p1",
                "direction": "conditional",
                "horizon": "same_day",
            },
            {
                "fsj_kind": "judgment",
                "object_key": f"judgment:{slot}:main",
                "statement": f"{slot} judgment",
                "object_type": "thesis",
                "judgment_action": "validate",
                "confidence": "medium",
                "evidence_level": "E2",
                "attributes_json": {},
                "invalidators": ["watch liquidity"],
                "priority": "p0",
                "direction": "up",
                "horizon": "same_day",
            },
        ],
        "edges": [
            {
                "edge_type": "fact_to_signal",
                "from_object_key": f"fact:{slot}:market",
                "to_object_key": f"signal:{slot}:state",
            },
            {
                "edge_type": "signal_to_judgment",
                "from_object_key": f"signal:{slot}:state",
                "to_object_key": f"judgment:{slot}:main",
            },
        ],
        "evidence_links": [
            {
                "evidence_role": "source_observed",
                "object_key": f"fact:{slot}:market",
                "ref_system": "runtime",
                "ref_key": f"source:{slot}",
            }
        ],
        "observed_records": [
            {
                "fsj_kind": "fact",
                "object_key": f"fact:{slot}:market",
                "source_layer": slot,
                "source_record_key": f"record:{slot}",
            }
        ],
        "report_links": [],
    }


def test_report_assembly_builds_stable_slot_order_with_lineage() -> None:
    assembler = MainReportSectionAssembler()
    artifact = assembler.build(
        [
            _graph(slot="late", section_key="post_close_main", bundle_id="bundle-late"),
            _graph(slot="early", section_key="pre_open_main", bundle_id="bundle-early"),
            _graph(slot="mid", section_key="midday_main", bundle_id="bundle-mid"),
        ],
        business_date="2099-04-22",
    )

    assert artifact["artifact_type"] == "fsj_main_report_sections"
    assert artifact["artifact_version"] == "v2"
    assert [section["slot"] for section in artifact["sections"]] == ["early", "mid", "late"]
    assert [section["section_render_key"] for section in artifact["sections"]] == [
        "main.pre_open",
        "main.midday",
        "main.post_close",
    ]
    assert artifact["sections"][0]["bundle"]["bundle_id"] == "bundle-early"
    assert artifact["sections"][1]["judgments"][0]["object_key"] == "judgment:mid:main"
    assert artifact["sections"][2]["lineage"]["evidence_links"][0]["ref_key"] == "source:late"


def test_report_assembly_prefers_active_bundle_over_superseded_bundle() -> None:
    assembler = MainReportSectionAssembler()
    artifact = assembler.build(
        [
            _graph(
                slot="mid",
                section_key="midday_main",
                bundle_id="bundle-mid-old",
                status="superseded",
                updated_at="2099-04-22T12:30:00+08:00",
            ),
            _graph(
                slot="mid",
                section_key="midday_main",
                bundle_id="bundle-mid-new",
                status="active",
                supersedes_bundle_id="bundle-mid-old",
                updated_at="2099-04-22T12:20:00+08:00",
                summary="mid active summary",
            ),
        ],
        business_date="2099-04-22",
    )

    mid_section = artifact["sections"][0]
    assert mid_section["slot"] == "mid"
    assert mid_section["bundle"]["bundle_id"] == "bundle-mid-new"
    assert mid_section["bundle"]["supersedes_bundle_id"] == "bundle-mid-old"
    assert mid_section["summary"] == "mid active summary"


def test_report_assembly_can_emit_empty_expected_sections() -> None:
    assembler = MainReportSectionAssembler()
    artifact = assembler.build([], business_date="2099-04-22", include_empty=True)

    assert len(artifact["sections"]) == 3
    assert [section["status"] for section in artifact["sections"]] == ["missing", "missing", "missing"]
    assert artifact["sections"][0]["section_key"] == "pre_open_main"
    assert artifact["sections"][2]["section_render_key"] == "main.post_close"


def test_report_assembly_merges_support_summaries_by_slot_without_inlining_support_content() -> None:
    assembler = MainReportSectionAssembler()

    artifact = assembler.build(
        [
            _graph(slot="early", section_key="pre_open_main", bundle_id="bundle-early", summary="盘前主线候选聚焦机器人"),
            _graph(slot="late", section_key="post_close_main", bundle_id="bundle-late", summary="收盘主线强化但分歧加大"),
        ],
        support_bundle_graphs=[
            _graph(
                slot="early",
                section_key="support_macro",
                bundle_id="bundle-support-macro-early",
                agent_domain="macro",
                summary="宏观背景偏稳定，更多作为边界 support。",
                producer="ifa_data_platform.fsj.early_macro_support_producer",
                producer_version="phase1-macro-early-v1",
            ),
            _graph(
                slot="early",
                section_key="support_ai_tech",
                bundle_id="bundle-support-ai-early",
                agent_domain="ai_tech",
                summary="AI 科技催化存在，但更适合 adjust 输入。",
                producer="ifa_data_platform.fsj.early_ai_tech_support_producer",
                producer_version="phase1-ai-tech-early-v1",
            ),
            _graph(
                slot="late",
                section_key="support_commodities",
                bundle_id="bundle-support-commodities-late",
                agent_domain="commodities",
                summary="商品链条更像次日风险变量，不改写主线结论。",
                producer="ifa_data_platform.fsj.late_commodities_support_producer",
                producer_version="phase1-commodities-late-v1",
            ),
        ],
        business_date="2099-04-22",
    )

    assert artifact["support_summary_domains"] == ["ai_tech", "commodities", "macro"]
    early = artifact["sections"][0]
    late = artifact["sections"][1]
    assert [item["agent_domain"] for item in early["support_summaries"]] == ["ai_tech", "macro"]
    assert early["support_summaries"][0]["summary"] == "AI 科技催化存在，但更适合 adjust 输入。"
    assert early["support_summaries"][1]["bundle_id"] == "bundle-support-macro-early"
    assert early["lineage"]["support_bundle_ids"] == ["bundle-support-ai-early", "bundle-support-macro-early"]
    assert late["support_summaries"][0]["agent_domain"] == "commodities"
    assert late["support_summaries"][0]["producer_version"] == "phase1-commodities-late-v1"
    assert "objects" not in late["support_summaries"][0]
