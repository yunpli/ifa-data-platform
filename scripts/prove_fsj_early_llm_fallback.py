from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from ifa_data_platform.fsj.early_main_producer import EarlyMainFSJAssembler, EarlyMainProducerInput
from ifa_data_platform.fsj.llm_assist import (
    FSJEarlyLLMAssistant,
    FSJEarlyLLMRequest,
    FSJEarlyLLMResult,
    ResilientEarlyLLMClient,
)


class PrimaryTimeoutEarlyLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        raise subprocess.TimeoutExpired(cmd=["ifa_llm_cli.py"], timeout=120)


class FallbackSuccessEarlyLLMClient:
    model_alias = "gemini31_pro_jmr"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        return FSJEarlyLLMResult(
            summary="A股盘前主线预案：机器人链条在竞价、事件流与 focus seed 之间形成优先候选，primary 超时后由 fallback 模型完成候选表达补强，但仍待开盘验证。",
            candidate_signal_statement="盘前竞价、事件流与 focus seed 已共同支持机器人链条进入主线候选，当前由 fallback 模型在 primary 超时后完成表达补强，但这仍只是待开盘验证的 candidate state。",
            judgment_statement="将机器人链条列为开盘首要验证候选：本次由 fallback 模型在 primary 超时后完成补强；若竞价承接、事件延续与 focus 对齐不能继续兑现，立即降回观察项，不把盘前候选写成已确认主线。",
            invalidators=[
                "09:27后竞价承接快速回落且高频覆盖未继续刷新",
                "事件流与候选龙头无法在 focus 池中形成一致验证",
                "若把隔夜文本催化直接写成 same-day 开盘确认，则当前判断无效",
            ],
            reasoning_trace=[
                "preopen auction packet present",
                "event and leader packet present",
                "primary timeout then fallback success",
            ],
            provider="eval-stub",
            model_alias=self.model_alias,
            model_id="gemini-3.1-pro",
            prompt_version=self.prompt_version,
            usage={"total_tokens": 341},
            raw_response={"stub": True, "fallback": True},
        )


class AllFailEarlyLLMClient(PrimaryTimeoutEarlyLLMClient):
    model_alias = "gemini31_pro_jmr"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        raise RuntimeError("business repo llm cli failed: synthetic provider failure")


def sample_input() -> EarlyMainProducerInput:
    return EarlyMainProducerInput(
        business_date="2099-04-22",
        slot="early",
        section_key="pre_open_main",
        section_type="thesis",
        bundle_topic_key="mainline_candidate:2099-04-22",
        summary_topic="A股盘前主线预案",
        trading_day_open=True,
        trading_day_label="open",
        focus_symbols=["300024.SZ", "002031.SZ", "601127.SH"],
        focus_list_types=["focus", "key_focus"],
        auction_count=18,
        auction_snapshot_time="2099-04-22T09:27:00+08:00",
        event_count=6,
        event_latest_time="2099-04-22T09:25:00+08:00",
        event_titles=["机器人链条隔夜催化", "算力链订单更新"],
        leader_count=4,
        leader_symbols=["300024.SZ", "002031.SZ"],
        signal_scope_count=1,
        latest_signal_state="candidate_confirming",
        text_catalyst_count=3,
        text_catalyst_titles=["机器人政策催化", "AI 应用发布", "龙头预告更新"],
        previous_archive_summary="昨日机器人主线维持高位扩散",
        replay_id="replay-early-2099-04-22",
        slot_run_id="slot-run-early-2099-04-22",
        report_run_id=None,
    )


def _extract_proof(bundle_graph: dict) -> dict:
    llm_assist = bundle_graph["bundle"]["payload_json"]["llm_assist"]
    judgment = next(obj for obj in bundle_graph["objects"] if obj["fsj_kind"] == "judgment")
    candidate_signal = next(obj for obj in bundle_graph["objects"] if obj["object_key"] == "signal:early:mainline_candidate_state")
    return {
        "bundle_summary": bundle_graph["bundle"]["summary"],
        "candidate_signal_statement": candidate_signal["statement"],
        "judgment_statement": judgment["statement"],
        "judgment_attributes": judgment["attributes_json"],
        "llm_assist": llm_assist,
        "policy": llm_assist.get("policy"),
    }


def main() -> int:
    data = sample_input()
    fallback_graph = EarlyMainFSJAssembler(
        llm_assistant=FSJEarlyLLMAssistant(
            ResilientEarlyLLMClient(clients=[PrimaryTimeoutEarlyLLMClient(), FallbackSuccessEarlyLLMClient()])
        )
    ).build_bundle_graph(data)
    degrade_graph = EarlyMainFSJAssembler(
        llm_assistant=FSJEarlyLLMAssistant(
            ResilientEarlyLLMClient(clients=[PrimaryTimeoutEarlyLLMClient(), AllFailEarlyLLMClient()])
        )
    ).build_bundle_graph(data)

    fallback_proof = _extract_proof(fallback_graph)
    degrade_proof = _extract_proof(degrade_graph)
    policy = fallback_proof["policy"] or {}
    assert fallback_proof["llm_assist"]["applied"] is True
    assert policy.get("outcome") == "fallback_applied"
    assert policy.get("attempted_model_chain") == ["grok41_thinking", "gemini31_pro_jmr"]
    assert policy.get("prior_failures", [{}])[0].get("classification") == "timeout"
    assert fallback_proof["judgment_attributes"]["llm_assist_applied"] is True
    assert degrade_proof["llm_assist"]["applied"] is False
    assert degrade_proof["policy"].get("outcome") == "deterministic_degrade"

    result = {
        "fixture": asdict(data),
        "fallback_success": fallback_proof,
        "deterministic_degrade": degrade_proof,
        "verification": {
            "policy_envelope_visible_beyond_unit_scope": True,
            "verified_at_early_assembler_eval_seam": "scripts/prove_fsj_early_llm_fallback.py",
        },
    }
    out = Path("artifacts/evals/fsj_early_llm_fallback_proof.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
