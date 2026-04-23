from __future__ import annotations

import hashlib
import json
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

BUSINESS_REPO_ROOT = Path("/Users/neoclaw/repos/ifa-business-layer")
BUSINESS_REPO_PYTHON = Path("/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python")
BUSINESS_REPO_CLI = BUSINESS_REPO_ROOT / "scripts/ifa_llm_cli.py"
FSJ_LATE_PROMPT_VERSION = "fsj_late_main_v1"
FSJ_EARLY_PROMPT_VERSION = "fsj_early_main_v1"
FSJ_MID_PROMPT_VERSION = "fsj_mid_main_v1"
FSJ_MODEL_ALIAS = "grok41_thinking"


@dataclass(frozen=True)
class FSJLateLLMRequest:
    business_date: str
    section_key: str
    contract_mode: str
    completeness_label: str
    degrade_reason: str | None
    evidence_packet: dict[str, Any]


@dataclass(frozen=True)
class FSJLateLLMResult:
    summary: str
    close_signal_statement: str
    context_signal_statement: str
    judgment_statement: str
    invalidators: list[str]
    reasoning_trace: list[str]
    provider: str | None
    model_alias: str
    model_id: str | None
    prompt_version: str
    usage: dict[str, Any] | None
    raw_response: dict[str, Any] | list[Any] | None

    def audit_payload(self, *, input_digest: str) -> dict[str, Any]:
        return {
            "applied": True,
            "provider": self.provider,
            "model_alias": self.model_alias,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "input_digest": input_digest,
            "usage": self.usage,
            "reasoning_trace": self.reasoning_trace,
        }


@dataclass(frozen=True)
class FSJEarlyLLMRequest:
    business_date: str
    section_key: str
    contract_mode: str
    completeness_label: str
    degrade_reason: str | None
    evidence_packet: dict[str, Any]


@dataclass(frozen=True)
class FSJEarlyLLMResult:
    summary: str
    candidate_signal_statement: str
    judgment_statement: str
    invalidators: list[str]
    reasoning_trace: list[str]
    provider: str | None
    model_alias: str
    model_id: str | None
    prompt_version: str
    usage: dict[str, Any] | None
    raw_response: dict[str, Any] | list[Any] | None

    def audit_payload(self, *, input_digest: str) -> dict[str, Any]:
        return {
            "applied": True,
            "provider": self.provider,
            "model_alias": self.model_alias,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "input_digest": input_digest,
            "usage": self.usage,
            "reasoning_trace": self.reasoning_trace,
        }


class FSJLateLLMClient(Protocol):
    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult: ...


class FSJEarlyLLMClient(Protocol):
    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult: ...


@dataclass(frozen=True)
class FSJMidLLMRequest:
    business_date: str
    section_key: str
    contract_mode: str
    completeness_label: str
    degrade_reason: str | None
    evidence_packet: dict[str, Any]


@dataclass(frozen=True)
class FSJMidLLMResult:
    summary: str
    validation_signal_statement: str
    afternoon_signal_statement: str
    judgment_statement: str
    invalidators: list[str]
    reasoning_trace: list[str]
    provider: str | None
    model_alias: str
    model_id: str | None
    prompt_version: str
    usage: dict[str, Any] | None
    raw_response: dict[str, Any] | list[Any] | None

    def audit_payload(self, *, input_digest: str) -> dict[str, Any]:
        return {
            "applied": True,
            "provider": self.provider,
            "model_alias": self.model_alias,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "input_digest": input_digest,
            "usage": self.usage,
            "reasoning_trace": self.reasoning_trace,
        }


class FSJMidLLMClient(Protocol):
    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult: ...


class BusinessRepoLateLLMClient:
    def __init__(
        self,
        *,
        repo_root: Path = BUSINESS_REPO_ROOT,
        python_bin: Path = BUSINESS_REPO_PYTHON,
        cli_path: Path = BUSINESS_REPO_CLI,
        model_alias: str = FSJ_MODEL_ALIAS,
        prompt_version: str = FSJ_LATE_PROMPT_VERSION,
        timeout_seconds: int = 120,
    ) -> None:
        self.repo_root = repo_root
        self.python_bin = python_bin
        self.cli_path = cli_path
        self.model_alias = model_alias
        self.prompt_version = prompt_version
        self.timeout_seconds = timeout_seconds

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        prompt = build_fsj_late_prompt(request)
        envelope = _run_business_repo_llm(
            repo_root=self.repo_root,
            python_bin=self.python_bin,
            cli_path=self.cli_path,
            model_alias=self.model_alias,
            prompt=prompt,
            timeout_seconds=self.timeout_seconds,
        )
        parsed = envelope.get("parsed_json")
        if not isinstance(parsed, dict):
            raise RuntimeError("llm response did not contain parsed_json object")
        return parse_fsj_late_result(parsed=parsed, envelope=envelope, prompt_version=self.prompt_version, model_alias=self.model_alias)


class BusinessRepoEarlyLLMClient:
    def __init__(
        self,
        *,
        repo_root: Path = BUSINESS_REPO_ROOT,
        python_bin: Path = BUSINESS_REPO_PYTHON,
        cli_path: Path = BUSINESS_REPO_CLI,
        model_alias: str = FSJ_MODEL_ALIAS,
        prompt_version: str = FSJ_EARLY_PROMPT_VERSION,
        timeout_seconds: int = 120,
    ) -> None:
        self.repo_root = repo_root
        self.python_bin = python_bin
        self.cli_path = cli_path
        self.model_alias = model_alias
        self.prompt_version = prompt_version
        self.timeout_seconds = timeout_seconds

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        prompt = build_fsj_early_prompt(request)
        envelope = _run_business_repo_llm(
            repo_root=self.repo_root,
            python_bin=self.python_bin,
            cli_path=self.cli_path,
            model_alias=self.model_alias,
            prompt=prompt,
            timeout_seconds=self.timeout_seconds,
        )
        parsed = envelope.get("parsed_json")
        if not isinstance(parsed, dict):
            raise RuntimeError("llm response did not contain parsed_json object")
        return parse_fsj_early_result(parsed=parsed, envelope=envelope, prompt_version=self.prompt_version, model_alias=self.model_alias)




class BusinessRepoMidLLMClient:
    def __init__(
        self,
        *,
        repo_root: Path = BUSINESS_REPO_ROOT,
        python_bin: Path = BUSINESS_REPO_PYTHON,
        cli_path: Path = BUSINESS_REPO_CLI,
        model_alias: str = FSJ_MODEL_ALIAS,
        prompt_version: str = FSJ_MID_PROMPT_VERSION,
        timeout_seconds: int = 120,
    ) -> None:
        self.repo_root = repo_root
        self.python_bin = python_bin
        self.cli_path = cli_path
        self.model_alias = model_alias
        self.prompt_version = prompt_version
        self.timeout_seconds = timeout_seconds

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        prompt = build_fsj_mid_prompt(request)
        envelope = _run_business_repo_llm(
            repo_root=self.repo_root,
            python_bin=self.python_bin,
            cli_path=self.cli_path,
            model_alias=self.model_alias,
            prompt=prompt,
            timeout_seconds=self.timeout_seconds,
        )
        parsed = envelope.get("parsed_json")
        if not isinstance(parsed, dict):
            raise RuntimeError("llm response did not contain parsed_json object")
        return parse_fsj_mid_result(parsed=parsed, envelope=envelope, prompt_version=self.prompt_version, model_alias=self.model_alias)


class NoopLateLLMClient:
    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        raise RuntimeError("llm assist disabled")


class NoopEarlyLLMClient:
    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        raise RuntimeError("llm assist disabled")


class NoopMidLLMClient:
    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        raise RuntimeError("llm assist disabled")


class FSJLateLLMAssistant:
    def __init__(self, client: FSJLateLLMClient | None = None) -> None:
        self.client = client or BusinessRepoLateLLMClient()

    def maybe_synthesize(self, request: FSJLateLLMRequest) -> tuple[FSJLateLLMResult | None, dict[str, Any]]:
        input_digest = hashlib.sha1(
            json.dumps(request.evidence_packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        try:
            result = self.client.synthesize(request)
            return result, result.audit_payload(input_digest=input_digest)
        except Exception as exc:
            return None, {
                "applied": False,
                "model_alias": getattr(self.client, "model_alias", FSJ_MODEL_ALIAS),
                "prompt_version": getattr(self.client, "prompt_version", FSJ_LATE_PROMPT_VERSION),
                "input_digest": input_digest,
                "error": str(exc),
            }


class FSJEarlyLLMAssistant:
    def __init__(self, client: FSJEarlyLLMClient | None = None) -> None:
        self.client = client or BusinessRepoEarlyLLMClient()

    def maybe_synthesize(self, request: FSJEarlyLLMRequest) -> tuple[FSJEarlyLLMResult | None, dict[str, Any]]:
        input_digest = hashlib.sha1(
            json.dumps(request.evidence_packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        try:
            result = self.client.synthesize(request)
            return result, result.audit_payload(input_digest=input_digest)
        except Exception as exc:
            return None, {
                "applied": False,
                "model_alias": getattr(self.client, "model_alias", FSJ_MODEL_ALIAS),
                "prompt_version": getattr(self.client, "prompt_version", FSJ_EARLY_PROMPT_VERSION),
                "input_digest": input_digest,
                "error": str(exc),
            }


class FSJMidLLMAssistant:
    def __init__(self, client: FSJMidLLMClient | None = None) -> None:
        self.client = client or BusinessRepoMidLLMClient()

    def maybe_synthesize(self, request: FSJMidLLMRequest) -> tuple[FSJMidLLMResult | None, dict[str, Any]]:
        input_digest = hashlib.sha1(
            json.dumps(request.evidence_packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        try:
            result = self.client.synthesize(request)
            return result, result.audit_payload(input_digest=input_digest)
        except Exception as exc:
            return None, {
                "applied": False,
                "model_alias": getattr(self.client, "model_alias", FSJ_MODEL_ALIAS),
                "prompt_version": getattr(self.client, "prompt_version", FSJ_MID_PROMPT_VERSION),
                "input_digest": input_digest,
                "error": str(exc),
            }


def build_fsj_late_prompt(request: FSJLateLLMRequest) -> dict[str, Any]:
    system = textwrap.dedent(
        """
        你是 A 股收盘主线复盘的 business-layer synthesis assist。
        你的职责只有：把已经给定、且可追溯的 same-day / retained context 证据整理成更高质量的中文结构化表达。

        硬约束：
        1. 不得发明未提供的数据、板块、涨跌幅、因果、资金结论。
        2. 不得越权改变 contract_mode / completeness_label / degrade_reason。
        3. 不得把 retained intraday context 或 T-1 背景表述成 same-day final confirmation。
        4. 输出必须是 JSON object，字段完整，invalidators 必须是字符串数组。
        5. 语气要像生产级晚报：简洁、具体、证据绑定，不写空话。

        目标：
        - summary：给 bundle 顶层 summary 用，一句话收敛结论。
        - close_signal_statement：准确描述收盘 close package 状态。
        - context_signal_statement：说明 intraday/context 的作用边界。
        - judgment_statement：形成最终 judgment 文案，但不改 judgment_action/object_type。
        - invalidators：给出 2-4 条真正可执行的失效边界。
        - reasoning_trace：2-4 条极短 bullet，说明你依据了哪些输入维度；不要暴露长推理。
        """
    ).strip()
    return {
        "system": system,
        "instruction": "基于给定 evidence_packet 生成严格 JSON，不要输出 markdown 代码块。",
        "required_json_schema": {
            "summary": "string",
            "close_signal_statement": "string",
            "context_signal_statement": "string",
            "judgment_statement": "string",
            "invalidators": ["string"],
            "reasoning_trace": ["string"],
        },
        "request": {
            "business_date": request.business_date,
            "section_key": request.section_key,
            "contract_mode": request.contract_mode,
            "completeness_label": request.completeness_label,
            "degrade_reason": request.degrade_reason,
            "evidence_packet": request.evidence_packet,
        },
    }


def build_fsj_early_prompt(request: FSJEarlyLLMRequest) -> dict[str, Any]:
    system = textwrap.dedent(
        """
        你是 A 股盘前主线预案的 business-layer synthesis assist。
        你的职责只有：把已经给定、且可追溯的盘前/隔夜证据整理成更高质量的中文结构化候选表达。

        硬约束：
        1. 不得发明未提供的数据、题材、竞价强度、资金结论、连板情况或开盘后走势。
        2. 不得越权改变 contract_mode / completeness_label / degrade_reason。
        3. 盘前输出只能是“候选/待验证/观察”，不得写成“今日主线已确认”。
        4. T-1 背景和近期文本催化只能作为参考，不得冒充 same-day 开盘确认。
        5. 输出必须是 JSON object，字段完整，invalidators 必须是字符串数组。
        6. 语气要像生产级盘前预案：简洁、具体、边界清楚。

        目标：
        - summary：给 bundle 顶层 summary 用，一句话收敛候选状态。
        - candidate_signal_statement：准确描述盘前 candidate state，强调待开盘验证。
        - judgment_statement：形成最终 judgment 文案，但不改 judgment_action/object_type。
        - invalidators：给出 2-4 条真正可执行的失效边界。
        - reasoning_trace：2-4 条极短 bullet，说明你依据了哪些输入维度；不要暴露长推理。
        """
    ).strip()
    return {
        "system": system,
        "instruction": "基于给定 evidence_packet 生成严格 JSON，不要输出 markdown 代码块。",
        "required_json_schema": {
            "summary": "string",
            "candidate_signal_statement": "string",
            "judgment_statement": "string",
            "invalidators": ["string"],
            "reasoning_trace": ["string"],
        },
        "request": {
            "business_date": request.business_date,
            "section_key": request.section_key,
            "contract_mode": request.contract_mode,
            "completeness_label": request.completeness_label,
            "degrade_reason": request.degrade_reason,
            "evidence_packet": request.evidence_packet,
        },
    }


def parse_fsj_late_result(*, parsed: dict[str, Any], envelope: dict[str, Any], prompt_version: str, model_alias: str) -> FSJLateLLMResult:
    summary = _require_text(parsed, "summary")
    close_signal_statement = _require_text(parsed, "close_signal_statement")
    context_signal_statement = _require_text(parsed, "context_signal_statement")
    judgment_statement = _require_text(parsed, "judgment_statement")
    invalidators = _require_text_list(parsed, "invalidators", min_items=2, max_items=4)
    reasoning_trace = _require_text_list(parsed, "reasoning_trace", min_items=2, max_items=4)
    return FSJLateLLMResult(
        summary=summary,
        close_signal_statement=close_signal_statement,
        context_signal_statement=context_signal_statement,
        judgment_statement=judgment_statement,
        invalidators=invalidators,
        reasoning_trace=reasoning_trace,
        provider=envelope.get("provider"),
        model_alias=envelope.get("model_alias") or model_alias,
        model_id=envelope.get("model_id"),
        prompt_version=prompt_version,
        usage=envelope.get("usage") if isinstance(envelope.get("usage"), dict) else None,
        raw_response=envelope.get("raw_response"),
    )


def parse_fsj_early_result(*, parsed: dict[str, Any], envelope: dict[str, Any], prompt_version: str, model_alias: str) -> FSJEarlyLLMResult:
    summary = _require_text(parsed, "summary")
    candidate_signal_statement = _require_text(parsed, "candidate_signal_statement")
    judgment_statement = _require_text(parsed, "judgment_statement")
    invalidators = _require_text_list(parsed, "invalidators", min_items=2, max_items=4)
    reasoning_trace = _require_text_list(parsed, "reasoning_trace", min_items=2, max_items=4)
    _ensure_early_candidate_boundary(summary, candidate_signal_statement, judgment_statement, invalidators)
    return FSJEarlyLLMResult(
        summary=summary,
        candidate_signal_statement=candidate_signal_statement,
        judgment_statement=judgment_statement,
        invalidators=invalidators,
        reasoning_trace=reasoning_trace,
        provider=envelope.get("provider"),
        model_alias=envelope.get("model_alias") or model_alias,
        model_id=envelope.get("model_id"),
        prompt_version=prompt_version,
        usage=envelope.get("usage") if isinstance(envelope.get("usage"), dict) else None,
        raw_response=envelope.get("raw_response"),
    )


def build_fsj_late_evidence_packet(data: Any, *, contract_mode: str, completeness_label: str, degrade_reason: str | None) -> dict[str, Any]:
    return {
        "summary_topic": data.summary_topic,
        "contract_mode": contract_mode,
        "completeness_label": completeness_label,
        "degrade_reason": degrade_reason,
        "same_day_final_market": {
            "equity_daily_count": data.equity_daily_count,
            "equity_daily_sample_symbols": data.equity_daily_sample_symbols[:5],
            "northbound_flow_count": data.northbound_flow_count,
            "northbound_net_amount": data.northbound_net_amount,
            "limit_up_detail_count": data.limit_up_detail_count,
            "limit_up_detail_sample_symbols": data.limit_up_detail_sample_symbols[:5],
            "limit_up_count": data.limit_up_count,
            "limit_down_count": data.limit_down_count,
            "dragon_tiger_count": data.dragon_tiger_count,
            "dragon_tiger_sample_symbols": data.dragon_tiger_sample_symbols[:5],
            "sector_performance_count": data.sector_performance_count,
            "sector_performance_top_sector": data.sector_performance_top_sector,
            "sector_performance_top_pct_chg": data.sector_performance_top_pct_chg,
        },
        "same_day_text": {
            "count": data.latest_text_count,
            "titles": data.latest_text_titles[:6],
            "source_times": data.latest_text_source_times[:6],
        },
        "same_day_mid_anchor": data.same_day_mid_summary,
        "intraday_context": {
            "event_count": data.intraday_event_count,
            "event_titles": data.intraday_event_titles[:5],
            "leader_count": data.intraday_leader_count,
            "leader_symbols": data.intraday_leader_symbols[:5],
            "signal_scope_count": data.intraday_signal_scope_count,
            "validation_state": data.intraday_validation_state,
        },
        "t_minus_1_background": data.previous_late_summary,
        "guardrails": {
            "full_close_ready": data.full_close_ready,
            "provisional_close_only": data.provisional_close_only,
            "has_same_day_final_structure": data.has_same_day_final_structure,
            "has_same_day_stable_market_support": data.has_same_day_stable_market_support,
            "has_same_day_low_text": data.has_same_day_low_text,
            "has_intraday_context": data.has_intraday_context,
        },
    }


def build_fsj_early_evidence_packet(data: Any, *, contract_mode: str, completeness_label: str, degrade_reason: str | None) -> dict[str, Any]:
    return {
        "summary_topic": data.summary_topic,
        "contract_mode": contract_mode,
        "completeness_label": completeness_label,
        "degrade_reason": degrade_reason,
        "trading_day": {
            "open": data.trading_day_open,
            "label": data.trading_day_label,
        },
        "preopen_market": {
            "auction_count": data.auction_count,
            "auction_snapshot_time": data.auction_snapshot_time,
            "event_count": data.event_count,
            "event_latest_time": data.event_latest_time,
            "event_titles": data.event_titles[:5],
            "leader_count": data.leader_count,
            "leader_symbols": data.leader_symbols[:5],
            "signal_scope_count": data.signal_scope_count,
            "latest_signal_state": data.latest_signal_state,
        },
        "reference_scope": {
            "focus_symbol_count": len(data.focus_symbols),
            "focus_symbols": data.focus_symbols[:10],
            "focus_list_types": data.focus_list_types,
        },
        "recent_text_catalysts": {
            "count": data.text_catalyst_count,
            "titles": data.text_catalyst_titles[:6],
        },
        "t_minus_1_background": data.previous_archive_summary,
        "guardrails": {
            "has_high_evidence": data.has_high_evidence,
            "has_low_evidence": data.has_low_evidence,
            "candidate_only": contract_mode == "candidate_only",
        },
    }


def build_fsj_mid_prompt(request: FSJMidLLMRequest) -> dict[str, Any]:
    system = textwrap.dedent(
        """
        你是 A 股盘中主线更新的 business-layer synthesis assist。
        你的职责只有：把已经给定、且可追溯的盘中 working 证据、盘前锚点和 T-1/文本背景整理成更高质量的中文结构化表达。

        硬约束：
        1. 不得发明未提供的数据、题材、涨跌幅、资金方向或午后结果。
        2. 不得越权改变 contract_mode / completeness_label / degrade_reason。
        3. 盘中输出只能写成“intraday adjust / 继续验证 / 观察项”，不得写成收盘最终确认。
        4. early 预案与 T-1 背景只能作为锚点/对照，不得冒充盘中结构事实。
        5. 输出必须是 JSON object，字段完整，invalidators 必须是字符串数组。
        6. 语气要像生产级午盘更新：简洁、具体、边界清楚。

        目标：
        - summary：给 bundle 顶层 summary 用，一句话收敛盘中状态。
        - validation_signal_statement：准确描述盘中验证状态，强调 working/intraday 边界。
        - afternoon_signal_statement：给出午后继续验证点，不得写成已兑现结果。
        - judgment_statement：形成最终 judgment 文案，但不改 judgment_action/object_type。
        - invalidators：给出 2-4 条真正可执行的失效边界。
        - reasoning_trace：2-4 条极短 bullet，说明你依据了哪些输入维度；不要暴露长推理。
        """
    ).strip()
    return {
        "system": system,
        "instruction": "基于给定 evidence_packet 生成严格 JSON，不要输出 markdown 代码块。",
        "required_json_schema": {
            "summary": "string",
            "validation_signal_statement": "string",
            "afternoon_signal_statement": "string",
            "judgment_statement": "string",
            "invalidators": ["string"],
            "reasoning_trace": ["string"],
        },
        "request": {
            "business_date": request.business_date,
            "section_key": request.section_key,
            "contract_mode": request.contract_mode,
            "completeness_label": request.completeness_label,
            "degrade_reason": request.degrade_reason,
            "evidence_packet": request.evidence_packet,
        },
    }


def parse_fsj_mid_result(*, parsed: dict[str, Any], envelope: dict[str, Any], prompt_version: str, model_alias: str) -> FSJMidLLMResult:
    summary = _require_text(parsed, "summary")
    validation_signal_statement = _require_text(parsed, "validation_signal_statement")
    afternoon_signal_statement = _require_text(parsed, "afternoon_signal_statement")
    judgment_statement = _require_text(parsed, "judgment_statement")
    invalidators = _require_text_list(parsed, "invalidators", min_items=2, max_items=4)
    reasoning_trace = _require_text_list(parsed, "reasoning_trace", min_items=2, max_items=4)
    _ensure_mid_intraday_boundary(summary, validation_signal_statement, afternoon_signal_statement, judgment_statement, invalidators)
    return FSJMidLLMResult(
        summary=summary,
        validation_signal_statement=validation_signal_statement,
        afternoon_signal_statement=afternoon_signal_statement,
        judgment_statement=judgment_statement,
        invalidators=invalidators,
        reasoning_trace=reasoning_trace,
        provider=envelope.get("provider"),
        model_alias=envelope.get("model_alias") or model_alias,
        model_id=envelope.get("model_id"),
        prompt_version=prompt_version,
        usage=envelope.get("usage") if isinstance(envelope.get("usage"), dict) else None,
        raw_response=envelope.get("raw_response"),
    )


def build_fsj_mid_evidence_packet(data: Any, *, contract_mode: str, completeness_label: str, degrade_reason: str | None, freshness: str) -> dict[str, Any]:
    return {
        "summary_topic": data.summary_topic,
        "contract_mode": contract_mode,
        "completeness_label": completeness_label,
        "degrade_reason": degrade_reason,
        "freshness_label": freshness,
        "intraday_structure": {
            "stock_1m_count": data.stock_1m_count,
            "stock_1m_latest_time": data.stock_1m_latest_time,
            "breadth_count": data.breadth_count,
            "breadth_latest_time": data.breadth_latest_time,
            "breadth_sector_code": data.breadth_sector_code,
            "breadth_spread_ratio": data.breadth_spread_ratio,
            "heat_count": data.heat_count,
            "heat_latest_time": data.heat_latest_time,
            "heat_sector_code": data.heat_sector_code,
            "heat_score": data.heat_score,
            "signal_scope_count": data.signal_scope_count,
            "signal_latest_time": data.signal_latest_time,
            "latest_validation_state": data.latest_validation_state,
            "latest_emotion_stage": data.latest_emotion_stage,
            "latest_risk_state": data.latest_risk_state,
        },
        "intraday_leader_event": {
            "leader_count": data.leader_count,
            "leader_latest_time": data.leader_latest_time,
            "leader_symbols": data.leader_symbols[:6],
            "leader_confirmation_states": data.leader_confirmation_states[:6],
            "event_count": data.event_count,
            "event_latest_time": data.event_latest_time,
            "event_titles": data.event_titles[:5],
        },
        "reference_context": {
            "early_plan_summary": data.early_plan_summary,
            "previous_late_summary": data.previous_late_summary,
            "latest_text_count": data.latest_text_count,
            "latest_text_titles": data.latest_text_titles[:6],
        },
        "guardrails": {
            "has_any_high_evidence": data.has_any_high_evidence,
            "has_sufficient_high_evidence": data.has_sufficient_high_evidence,
            "freshness_label": freshness,
            "monitoring_only": degrade_reason is not None,
        },
    }


def _run_business_repo_llm(*, repo_root: Path, python_bin: Path, cli_path: Path, model_alias: str, prompt: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(python_bin),
            str(cli_path),
            "--model",
            model_alias,
            "--output-format",
            "json",
            "--parse-json-response",
            "--prompt",
            json.dumps(prompt, ensure_ascii=False),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"business repo llm cli failed: {stderr}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("business repo llm cli returned non-json envelope") from exc


def _require_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise RuntimeError(f"invalid llm field: {key}")
    cleaned = value.strip()
    if not cleaned or "```" in cleaned:
        raise RuntimeError(f"invalid llm field: {key}")
    if len(cleaned) > 280:
        raise RuntimeError(f"invalid llm field: {key}")
    return cleaned


def _require_text_list(payload: dict[str, Any], key: str, *, min_items: int, max_items: int) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise RuntimeError(f"invalid llm field: {key}")
    out = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned and "```" not in cleaned and len(cleaned) <= 180:
                out.append(cleaned)
    if not (min_items <= len(out) <= max_items):
        raise RuntimeError(f"invalid llm field: {key}")
    return out


def _ensure_early_candidate_boundary(summary: str, candidate_signal_statement: str, judgment_statement: str, invalidators: list[str]) -> None:
    joined = "\n".join([summary, candidate_signal_statement, judgment_statement, *invalidators])
    banned_tokens = ["最终确认", "收盘", "晚报", "已确认主线", "主线已成立"]
    if any(token in joined for token in banned_tokens):
        raise RuntimeError("invalid llm field: early candidate boundary violated")
    if "候选" not in candidate_signal_statement or "验证" not in candidate_signal_statement:
        raise RuntimeError("invalid llm field: early candidate boundary violated")


def _ensure_mid_intraday_boundary(summary: str, validation_signal_statement: str, afternoon_signal_statement: str, judgment_statement: str, invalidators: list[str]) -> None:
    joined = "\n".join([summary, validation_signal_statement, afternoon_signal_statement, judgment_statement, *invalidators])
    banned_tokens = ["收盘最终确认", "晚报主线已确认", "已收盘", "final truth", "收盘结论已成立"]
    if any(token in joined for token in banned_tokens):
        raise RuntimeError("invalid llm field: mid intraday boundary violated")
    if not any(token in validation_signal_statement for token in ["盘中", "working", "intraday"]):
        raise RuntimeError("invalid llm field: mid intraday boundary violated")
    if not any(token in afternoon_signal_statement for token in ["午后", "继续验证", "跟踪"]):
        raise RuntimeError("invalid llm field: mid intraday boundary violated")
