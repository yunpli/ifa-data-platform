from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ifa_data_platform.fsj.early_main_producer import EarlyMainFSJAssembler, EarlyMainProducerInput
from ifa_data_platform.fsj.llm_assist import FSJEarlyLLMAssistant, FSJEarlyLLMRequest, FSJEarlyLLMResult


class EvalStubEarlyLLMClient:
    model_alias = "grok41_thinking"
    prompt_version = "fsj_early_main_v1"

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        return FSJEarlyLLMResult(
            summary="A股盘前主线预案：机器人链条在竞价、事件流与 focus seed 上形成优先候选，但仍需开盘验证后才能升级。",
            candidate_signal_statement="盘前竞价样本、事件强化与 focus seed 已把机器人链条推到主线候选前排，开盘后仍需继续验证，不能写成已确认主线。",
            judgment_statement="将机器人链条列为开盘首要验证候选：若竞价承接、事件延续和 seed 对齐不能继续兑现，立即降回观察项，不把盘前候选升级成已确认判断。",
            invalidators=[
                "09:27后竞价承接明显回落且高频覆盖未继续强化",
                "事件流与候选龙头无法在 focus 池中形成一致验证",
                "近期文本催化缺少盘前市场侧呼应，无法支撑主线候选继续前移",
            ],
            reasoning_trace=[
                "auction packet present",
                "event and leader packet present",
                "candidate boundary preserved",
            ],
            provider="eval-stub",
            model_alias=self.model_alias,
            model_id="grok-4.1-thinking",
            prompt_version=self.prompt_version,
            usage={"total_tokens": 333},
            raw_response={"stub": True},
        )


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


def score_payload(payload: dict) -> dict[str, int]:
    judgment = next(obj for obj in payload["objects"] if obj["fsj_kind"] == "judgment")
    signal = next(obj for obj in payload["objects"] if obj["object_key"] == "signal:early:mainline_candidate_state")
    bundle_summary = payload["bundle"]["summary"]
    text = "\n".join([bundle_summary, judgment["statement"], signal["statement"], *judgment["invalidators"]])
    score = {
        "specific_sector_named": int("机器人" in text),
        "candidate_boundary_explicit": int("候选" in text and "验证" in text and "已确认" not in text),
        "preopen_grounding_explicit": int(any(token in text for token in ["竞价", "event", "focus", "盘前"])),
        "clear_invalidators": int(len(judgment["invalidators"]) >= 3),
        "summary_non_generic": int(len(bundle_summary) >= 26 and ("候选" in bundle_summary or "验证" in bundle_summary)),
    }
    score["total"] = sum(score.values())
    return score


def main() -> int:
    data = sample_input()
    baseline = EarlyMainFSJAssembler().build_bundle_graph(data)
    llm = EarlyMainFSJAssembler(llm_assistant=FSJEarlyLLMAssistant(EvalStubEarlyLLMClient())).build_bundle_graph(data)

    baseline_score = score_payload(baseline)
    llm_score = score_payload(llm)
    result = {
        "fixture": asdict(data),
        "baseline": {
            "summary": baseline["bundle"]["summary"],
            "judgment_statement": next(obj for obj in baseline["objects"] if obj["fsj_kind"] == "judgment")["statement"],
            "score": baseline_score,
        },
        "llm_assisted": {
            "summary": llm["bundle"]["summary"],
            "judgment_statement": next(obj for obj in llm["objects"] if obj["fsj_kind"] == "judgment")["statement"],
            "score": llm_score,
            "llm_audit": llm["bundle"]["payload_json"]["llm_assist"],
        },
        "delta": llm_score["total"] - baseline_score["total"],
    }
    out = Path("artifacts/evals/fsj_early_llm_slice_eval.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
