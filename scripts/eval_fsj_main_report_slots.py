from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj.report_evaluation import MainReportEvaluationHarness
from ifa_data_platform.fsj.report_quality import MainReportQAEvaluator
from ifa_data_platform.fsj.report_rendering import MainReportHTMLRenderer


def sample_assembled() -> dict:
    return {
        "artifact_type": "fsj_main_report_sections",
        "artifact_version": "v2",
        "market": "a_share",
        "business_date": "2099-04-22",
        "agent_domain": "main",
        "section_count": 3,
        "support_summary_domains": ["ai_tech", "macro"],
        "sections": [
            {
                "slot": "early",
                "section_key": "pre_open_main",
                "section_render_key": "main.pre_open",
                "title": "盘前主结论",
                "order_index": 10,
                "status": "ready",
                "bundle": {"bundle_id": "bundle-early", "status": "active", "bundle_topic_key": "early:pre_open_main", "producer": "ifa_data_platform.fsj.early_main_producer", "producer_version": "phase1-main-early-v1", "section_type": "thesis", "slot_run_id": "slot-run-early", "replay_id": "replay-early", "report_run_id": None, "updated_at": "2099-04-22T08:59:00+08:00"},
                "summary": "机器人链条是今日盘前首要验证主线。",
                "judgments": [{"object_key": "judgment:early:main", "statement": "开盘前先 validate。", "judgment_action": "validate", "confidence": "medium", "evidence_level": "E2"}],
                "signals": [{"object_key": "signal:early:confirm", "statement": "竞价承接需抬升。", "signal_strength": "medium", "confidence": "medium", "evidence_level": "E2"}],
                "facts": [{"object_key": "fact:early:robotics", "statement": "隔夜催化集中于机器人。", "confidence": "high", "evidence_level": "E1"}],
                "support_summaries": [{"bundle_id": "bundle-support-ai-early", "slot": "early", "agent_domain": "ai_tech", "section_key": "support_ai_tech", "summary": "AI 科技催化存在，但更适合作为 adjust 输入。", "producer_version": "phase1-ai-tech-early-v1", "lineage": {"report_links": [], "evidence_links": [{"ref_key": "source:early:ai-tech"}]}}],
                "lineage": {"bundle": {"bundle_id": "bundle-early"}, "objects": [], "edges": [], "evidence_links": [{"ref_key": "source:early:robotics"}], "observed_records": [{"source_layer": "highfreq", "source_record_key": "record:early"}], "report_links": [{"artifact_type": "markdown", "artifact_uri": "file:///tmp/early.md", "section_render_key": "main.pre_open"}], "support_bundle_ids": ["bundle-support-ai-early"]},
            },
            {
                "slot": "mid",
                "section_key": "midday_main",
                "section_render_key": "main.midday",
                "title": "盘中主结论",
                "order_index": 20,
                "status": "ready",
                "bundle": {"bundle_id": "bundle-mid", "status": "active", "bundle_topic_key": "mid:midday_main", "producer": "ifa_data_platform.fsj.mid_main_producer", "producer_version": "phase1-main-mid-v1", "section_type": "thesis", "slot_run_id": "slot-run-mid", "replay_id": "replay-mid", "report_run_id": None, "updated_at": "2099-04-22T11:25:00+08:00"},
                "summary": "盘中机器人主线继续扩散，但午后仍需验证。",
                "judgments": [{"object_key": "judgment:mid:main", "statement": "允许 intraday adjust。", "judgment_action": "adjust", "confidence": "medium", "evidence_level": "E2"}],
                "signals": [{"object_key": "signal:mid:validation", "statement": "validation_state=confirmed。", "signal_strength": "medium", "confidence": "medium", "evidence_level": "E2"}],
                "facts": [{"object_key": "fact:mid:breadth", "statement": "breadth/heat 同步扩散。", "confidence": "medium", "evidence_level": "E2"}],
                "support_summaries": [],
                "lineage": {"bundle": {"bundle_id": "bundle-mid"}, "objects": [], "edges": [], "evidence_links": [{"ref_key": "source:mid:breadth"}, {"ref_key": "source:mid:heat"}], "observed_records": [{"source_layer": "highfreq", "source_record_key": "record:mid-1"}, {"source_layer": "highfreq", "source_record_key": "record:mid-2"}], "report_links": [{"artifact_type": "markdown", "artifact_uri": "file:///tmp/mid.md", "section_render_key": "main.midday"}], "support_bundle_ids": []},
            },
            {
                "slot": "late",
                "section_key": "post_close_main",
                "section_render_key": "main.post_close",
                "title": "收盘主结论",
                "order_index": 30,
                "status": "ready",
                "bundle": {"bundle_id": "bundle-late", "status": "active", "bundle_topic_key": "late:post_close_main", "producer": "ifa_data_platform.fsj.late_main_producer", "producer_version": "phase1-main-late-v1", "section_type": "thesis", "slot_run_id": "slot-run-late", "replay_id": "replay-late", "report_run_id": None, "updated_at": "2099-04-22T15:05:00+08:00"},
                "summary": "收盘确认主线强化，但高位分歧增大。",
                "judgments": [{"object_key": "judgment:late:main", "statement": "收盘后继续 monitor 分歧。", "judgment_action": "monitor", "confidence": "medium", "evidence_level": "E2"}],
                "signals": [{"object_key": "signal:late:close_package_state", "statement": "same-day final market packet ready。", "signal_strength": "high", "confidence": "high", "evidence_level": "E1", "attributes_json": {"contract_mode": "full_close_package", "provisional_close_only": False}}],
                "facts": [{"object_key": "fact:late:close", "statement": "收盘主线已具备当日闭环。", "confidence": "high", "evidence_level": "E1"}],
                "support_summaries": [],
                "lineage": {"bundle": {"bundle_id": "bundle-late"}, "objects": [], "edges": [], "evidence_links": [{"ref_key": "source:late:close"}], "observed_records": [{"source_layer": "midfreq", "source_record_key": "record:late"}], "report_links": [{"artifact_type": "markdown", "artifact_uri": "file:///tmp/late.md", "section_render_key": "main.post_close"}], "support_bundle_ids": []},
            },
        ],
    }


def main() -> int:
    assembled = sample_assembled()
    rendered = MainReportHTMLRenderer().render(
        assembled,
        report_run_id="report-run-slot-eval-2099-04-22",
        artifact_uri="file:///tmp/a_share_main_2099-04-22.html",
        generated_at=datetime(2099, 4, 22, 8, 0, tzinfo=timezone.utc),
    )
    qa = MainReportQAEvaluator().evaluate(assembled, rendered)
    evaluation = MainReportEvaluationHarness().evaluate(assembled, rendered, qa)
    payload = {"qa": qa, "evaluation": evaluation}
    out = Path("artifacts/evals/fsj_main_report_slot_eval.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
