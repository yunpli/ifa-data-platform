from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from ifa_data_platform.fsj.llm_assist import (
    FSJMidLLMAssistant,
    FSJMidLLMRequest,
    FSJMidLLMResult,
    ResilientMidLLMClient,
)
from ifa_data_platform.fsj.mid_main_producer import MidMainFSJAssembler, MidMainProducerInput


class PrimaryTimeoutMidLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_mid_main_v1"

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        raise subprocess.TimeoutExpired(cmd=["ifa_llm_cli.py"], timeout=120)


class FallbackSuccessMidLLMClient:
    model_alias = "gemini31_pro_jmr"
    prompt_version = "fsj_mid_main_v1"

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        return FSJMidLLMResult(
            summary="A股盘中主线更新：机器人链条在盘中 working 结构、leader/event 与盘前锚点之间保持一致，primary 超时后由 fallback 模型完成 mid-slot 补强，但午后仍需继续验证。",
            validation_signal_statement="盘中 working 结构、leader/event 与 validation_state=confirmed 已支持机器人链条继续作为 intraday adjust 输入；本次由 fallback 模型在 primary 超时后完成表达补强，但当前仍只是盘中验证。",
            afternoon_signal_statement="午后继续验证点：跟踪机器人链条是否继续向 breadth/heat 扩散，并观察 validation_state 是否维持 confirmed 或转弱。",
            judgment_statement="将机器人链条作为盘中主线修正输入：允许做 intraday thesis/adjust；本次由 fallback 模型在 primary 超时后完成补强，但必须保留午后继续验证与失效边界，不把盘中 working 证据写成收盘结论。",
            invalidators=[
                "盘中 structure high layer 未继续刷新或关键表再次断档",
                "leader/breadth/heat 之间无法形成一致强化",
                "盘前预案锚点与盘中 working 证据出现明显背离",
            ],
            reasoning_trace=[
                "intraday structure packet present",
                "leader event packet present",
                "primary timeout then fallback success",
            ],
            provider="eval-stub",
            model_alias=self.model_alias,
            model_id="gemini-3.1-pro",
            prompt_version=self.prompt_version,
            usage={"total_tokens": 355},
            raw_response={"stub": True, "fallback": True},
        )


class AllFailMidLLMClient(PrimaryTimeoutMidLLMClient):
    model_alias = "gemini31_pro_jmr"

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        raise RuntimeError("business repo llm cli failed: synthetic provider failure")


def sample_input() -> MidMainProducerInput:
    return MidMainProducerInput(
        business_date="2099-04-22",
        slot="mid",
        section_key="midday_main",
        section_type="thesis",
        bundle_topic_key="mainline_mid_update:2099-04-22",
        summary_topic="A股盘中主线更新",
        stock_1m_count=128,
        stock_1m_latest_time="2099-04-22T11:18:00+08:00",
        breadth_count=24,
        breadth_latest_time="2099-04-22T11:16:00+08:00",
        breadth_sector_code="BK0421",
        breadth_spread_ratio=0.72,
        heat_count=20,
        heat_latest_time="2099-04-22T11:17:00+08:00",
        heat_sector_code="BK0421",
        heat_score=8.4,
        leader_count=5,
        leader_latest_time="2099-04-22T11:19:00+08:00",
        leader_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        leader_confirmation_states=["confirmed", "candidate_confirming"],
        signal_scope_count=2,
        signal_latest_time="2099-04-22T11:20:00+08:00",
        latest_validation_state="confirmed",
        latest_emotion_stage="expanding",
        latest_risk_state="balanced",
        event_count=4,
        event_latest_time="2099-04-22T11:21:00+08:00",
        event_titles=["机器人链条盘中继续扩散", "算力方向再获催化"],
        latest_text_count=3,
        latest_text_titles=["机器人政策催化", "AI 应用发布", "龙头预告更新"],
        early_plan_summary="盘前预案聚焦机器人链条强度延续",
        previous_late_summary="T-1 晚报维持机器人主线高位扩散",
        replay_id="replay-mid-2099-04-22",
        slot_run_id="slot-run-mid-2099-04-22",
        report_run_id=None,
    )


def _extract_proof(bundle_graph: dict) -> dict:
    llm_assist = bundle_graph["bundle"]["payload_json"]["llm_assist"]
    judgment = next(obj for obj in bundle_graph["objects"] if obj["fsj_kind"] == "judgment")
    validation_signal = next(obj for obj in bundle_graph["objects"] if obj["object_key"] == "signal:mid:plan_validation_state")
    return {
        "bundle_summary": bundle_graph["bundle"]["summary"],
        "validation_signal_statement": validation_signal["statement"],
        "judgment_statement": judgment["statement"],
        "judgment_attributes": judgment["attributes_json"],
        "llm_assist": llm_assist,
        "policy": llm_assist.get("policy"),
    }


def main() -> int:
    data = sample_input()
    fallback_graph = MidMainFSJAssembler(
        llm_assistant=FSJMidLLMAssistant(
            ResilientMidLLMClient(clients=[PrimaryTimeoutMidLLMClient(), FallbackSuccessMidLLMClient()])
        )
    ).build_bundle_graph(data)
    degrade_graph = MidMainFSJAssembler(
        llm_assistant=FSJMidLLMAssistant(
            ResilientMidLLMClient(clients=[PrimaryTimeoutMidLLMClient(), AllFailMidLLMClient()])
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
            "verified_at_mid_assembler_eval_seam": "scripts/prove_fsj_mid_llm_fallback.py",
        },
    }
    out = Path("artifacts/evals/fsj_mid_llm_fallback_proof.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
