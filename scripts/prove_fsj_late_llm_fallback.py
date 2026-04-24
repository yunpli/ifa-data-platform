from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from ifa_data_platform.fsj.late_main_producer import LateMainFSJAssembler, LateMainProducerInput
from ifa_data_platform.fsj.llm_assist import (
    FSJLateLLMAssistant,
    FSJLateLLMRequest,
    FSJLateLLMResult,
    ResilientLateLLMClient,
)


class PrimaryTimeoutLateLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_late_main_v1"

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        raise subprocess.TimeoutExpired(cmd=["ifa_llm_cli.py"], timeout=120)


class FallbackSuccessLateLLMClient:
    model_alias = "gemini31_pro_jmr"
    prompt_version = "fsj_late_main_v1"

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        return FSJLateLLMResult(
            summary="A股收盘主线复盘：机器人链条在同日收盘稳定表、涨停结构与盘后文本之间形成共振，已通过 fallback 模型完成主线收盘结论补强。",
            close_signal_statement="same-day stable/final 市场表已齐，北向/涨停/板块强度与盘后文本相互印证；primary 超时后由 fallback 模型完成 close package 表达。",
            context_signal_statement="盘中机器人回流、龙头样本与 validation=confirmed 只用于解释日内强化路径，不替代收盘 final confirmation。",
            judgment_statement="晚报主线聚焦机器人链条：结论以同日 stable/final 事实为准；本次由 fallback 模型在 primary 超时后完成补强，盘中与T-1背景仅作演化解释和历史对照。",
            invalidators=[
                "若盘后稳定表复核后关键字段回撤或缺失，则当前主线结论回退",
                "若同日文本样本无法对应机器人链条，则不得把结论扩写成更宽泛题材",
                "若把 retained intraday context 当成收盘最终确认，则该判断无效",
            ],
            reasoning_trace=[
                "same-day final tables present",
                "same-day timed text present",
                "primary timeout then fallback success",
            ],
            provider="eval-stub",
            model_alias=self.model_alias,
            model_id="gemini-3.1-pro",
            prompt_version=self.prompt_version,
            usage={"total_tokens": 377},
            raw_response={"stub": True, "fallback": True},
        )


class AllFailLateLLMClient(PrimaryTimeoutLateLLMClient):
    model_alias = "gemini31_pro_jmr"

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        raise RuntimeError("business repo llm cli failed: synthetic provider failure")


def sample_input() -> LateMainProducerInput:
    return LateMainProducerInput(
        business_date="2099-04-22",
        slot="late",
        section_key="post_close_main",
        section_type="thesis",
        bundle_topic_key="mainline_close:2099-04-22",
        summary_topic="A股收盘主线复盘",
        equity_daily_count=420,
        equity_daily_latest_trade_date="2099-04-22",
        equity_daily_sample_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        northbound_flow_count=1,
        northbound_latest_trade_date="2099-04-22",
        northbound_net_amount=38.5,
        limit_up_detail_count=78,
        limit_up_detail_latest_trade_date="2099-04-22",
        limit_up_detail_sample_symbols=["300024.SZ", "002031.SZ"],
        limit_up_down_status_count=1,
        limit_up_down_latest_trade_date="2099-04-22",
        limit_up_count=56,
        limit_down_count=3,
        dragon_tiger_count=12,
        dragon_tiger_latest_trade_date="2099-04-22",
        dragon_tiger_sample_symbols=["300024.SZ", "002031.SZ"],
        sector_performance_count=42,
        sector_performance_latest_trade_date="2099-04-22",
        sector_performance_top_sector="机器人",
        sector_performance_top_pct_chg=4.8,
        latest_text_count=4,
        latest_text_titles=["盘后业绩快报", "政策催化", "龙头澄清", "机构点评"],
        latest_text_source_times=["2099-04-22T16:03:00+08:00", "2099-04-22T15:41:00+08:00"],
        intraday_event_count=5,
        intraday_event_latest_time="2099-04-22T14:56:00+08:00",
        intraday_event_titles=["机器人午后回流", "AI 应用分支走强"],
        intraday_leader_count=3,
        intraday_leader_latest_time="2099-04-22T14:57:00+08:00",
        intraday_leader_symbols=["300024.SZ", "002031.SZ"],
        intraday_signal_scope_count=2,
        intraday_signal_latest_time="2099-04-22T14:58:00+08:00",
        intraday_validation_state="confirmed",
        previous_late_summary="T-1 晚报维持机器人主线高位扩散",
        same_day_mid_summary="盘中机器人链条继续扩散并保持 validation=confirmed",
        replay_id="replay-late-2099-04-22",
        slot_run_id="slot-run-late-2099-04-22",
        report_run_id=None,
    )


def _extract_proof(bundle_graph: dict) -> dict:
    llm_assist = bundle_graph["bundle"]["payload_json"]["llm_assist"]
    judgment = next(obj for obj in bundle_graph["objects"] if obj["fsj_kind"] == "judgment")
    return {
        "bundle_summary": bundle_graph["bundle"]["summary"],
        "judgment_statement": judgment["statement"],
        "judgment_attributes": judgment["attributes_json"],
        "llm_assist": llm_assist,
        "policy": llm_assist.get("policy"),
    }


def main() -> int:
    data = sample_input()
    fallback_graph = LateMainFSJAssembler(
        llm_assistant=FSJLateLLMAssistant(
            ResilientLateLLMClient(clients=[PrimaryTimeoutLateLLMClient(), FallbackSuccessLateLLMClient()])
        )
    ).build_bundle_graph(data)
    degrade_graph = LateMainFSJAssembler(
        llm_assistant=FSJLateLLMAssistant(
            ResilientLateLLMClient(clients=[PrimaryTimeoutLateLLMClient(), AllFailLateLLMClient()])
        )
    ).build_bundle_graph(data)

    fallback_proof = _extract_proof(fallback_graph)
    degrade_proof = _extract_proof(degrade_graph)
    policy = fallback_proof["policy"] or {}
    assert fallback_proof["llm_assist"]["applied"] is True
    assert policy.get("outcome") == "fallback_applied"
    assert policy.get("attempted_model_chain") == ["grok41_thinking", "gemini31_pro_jmr"]
    assert policy.get("prior_failures", [{}])[0].get("classification") == "timeout"
    assert degrade_proof["llm_assist"]["applied"] is False
    assert degrade_proof["policy"].get("outcome") == "deterministic_degrade"

    result = {
        "fixture": asdict(data),
        "fallback_success": fallback_proof,
        "deterministic_degrade": degrade_proof,
        "verification": {
            "policy_envelope_visible_beyond_unit_scope": True,
            "verified_at_cli_eval_seam": "scripts/prove_fsj_late_llm_fallback.py",
        },
    }
    out = Path("artifacts/evals/fsj_late_llm_fallback_proof.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
