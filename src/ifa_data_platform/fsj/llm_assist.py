from __future__ import annotations

import hashlib
import json
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

BUSINESS_REPO_ROOT = Path("/Users/neoclaw/repos/ifa-business-layer")
BUSINESS_REPO_PYTHON = Path("/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python")
BUSINESS_REPO_CLI = BUSINESS_REPO_ROOT / "scripts/ifa_llm_cli.py"
FSJ_LATE_PROMPT_VERSION = "fsj_late_main_v1"
FSJ_EARLY_PROMPT_VERSION = "fsj_early_main_v1"
FSJ_MID_PROMPT_VERSION = "fsj_mid_main_v1"
FSJ_MODEL_ALIAS = "grok41_thinking"
FSJ_FALLBACK_MODEL_ALIAS = "gemini31_pro_jmr"
BUSINESS_REPO_MODELS_CONFIG = BUSINESS_REPO_ROOT / "config" / "llm" / "models.yaml"


def build_fsj_role_policy(*, slot: str, contract_mode: str, completeness_label: str, degrade_reason: str | None) -> dict[str, Any]:
    slot_policy: dict[str, dict[str, Any]] = {
        "early": {
            "boundary_mode": "candidate_only",
            "allowed_output_fields": [
                "bundle.summary",
                "signal.statement",
                "judgment.statement",
                "judgment.invalidators",
                "judgment.attributes.llm_reasoning_trace",
            ],
            "forbidden_decisions": [
                "promote_candidate_to_same_day_confirmed_theme",
                "rewrite_contract_mode_or_completeness_label",
                "invent_open_or_post_open_market_truth",
                "override_deterministic_object_type_or_judgment_action",
            ],
            "boundary_invariants": [
                "llm_must_frame_output_as_candidate_pending_open_validation",
                "llm_must_not_state_same_day_theme_is_confirmed",
                "t_minus_1_or_text_context_cannot_be_presented_as_same_day_confirmation",
            ],
        },
        "mid": {
            "boundary_mode": "intraday_working",
            "allowed_output_fields": [
                "bundle.summary",
                "validation_signal.statement",
                "afternoon_signal.statement",
                "judgment.statement",
                "judgment.invalidators",
                "judgment.attributes.llm_reasoning_trace",
            ],
            "forbidden_decisions": [
                "declare_close_final_confirmation",
                "rewrite_contract_mode_or_completeness_label",
                "invent_afternoon_or_close_outcome",
                "override_deterministic_object_type_or_judgment_action",
            ],
            "boundary_invariants": [
                "llm_must_frame_output_as_intraday_working_state",
                "llm_must_keep_afternoon_signal_as_follow_up_not_result",
                "early_anchor_or_t_minus_1_context_cannot_be_presented_as_intraday_fact",
            ],
        },
        "late": {
            "boundary_mode": "same_day_close",
            "allowed_output_fields": [
                "bundle.summary",
                "close_signal.statement",
                "context_signal.statement",
                "judgment.statement",
                "judgment.invalidators",
                "judgment.attributes.llm_reasoning_trace",
            ],
            "forbidden_decisions": [
                "upgrade_provisional_close_without_required_same_day_evidence",
                "rewrite_contract_mode_or_completeness_label",
                "treat_intraday_context_as_final_close_confirmation",
                "override_deterministic_object_type_or_judgment_action",
            ],
            "boundary_invariants": [
                "llm_must_bind_close_conclusions_to_same_day_final_or_stable_inputs_only",
                "intraday_context_is_explanatory_only_not_final_confirmation",
                "llm_must_not_change_operator_visible_degrade_posture",
            ],
        },
    }
    policy = dict(slot_policy[slot])
    policy.update(
        {
            "policy_version": "fsj_llm_role_policy_v1",
            "slot": slot,
            "contract_mode": contract_mode,
            "completeness_label": completeness_label,
            "degrade_reason": degrade_reason,
            "deterministic_owner_fields": [
                "implemented_scope",
                "degrade.contract_mode",
                "degrade.completeness_label",
                "degrade.degrade_reason",
                "object_types",
                "judgment.action",
                "workflow_state_and_send_readiness",
            ],
            "override_precedence": [
                "deterministic_input_contract",
                "deterministic_boundary_and_degrade_policy",
                "validated_llm_text_fields_only",
                "operator_review_and_send_selection",
            ],
        }
    )
    return policy


def _audit_field_lineage(*, slot: str, applied: bool, reason: str | None = None) -> dict[str, Any]:
    policy = build_fsj_role_policy(
        slot=slot,
        contract_mode="audit_projection",
        completeness_label="audit_projection",
        degrade_reason=reason,
    )
    allowed_output_fields = [
        str(field)
        for field in (policy.get("allowed_output_fields") or [])
        if str(field).strip()
    ]
    adopted_output_fields = list(allowed_output_fields) if applied else []
    discarded_output_fields = [] if applied else list(allowed_output_fields)
    return {
        "allowed_output_fields": allowed_output_fields,
        "adopted_output_fields": adopted_output_fields,
        "discarded_output_fields": discarded_output_fields,
        "adopted_output_field_count": len(adopted_output_fields),
        "discarded_output_field_count": len(discarded_output_fields),
        "field_replay_ready": bool(applied),
        "discard_reason": None if applied else (reason or "llm_output_not_adopted"),
    }


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
            **_audit_field_lineage(slot="late", applied=True),
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
            **_audit_field_lineage(slot="early", applied=True),
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
            **_audit_field_lineage(slot="mid", applied=True),
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


@dataclass(frozen=True)
class LLMInvocationFailure(RuntimeError):
    classification: str
    detail: str
    model_alias: str

    def __str__(self) -> str:
        return f"{self.classification}: {self.detail}"


def _load_configured_model_aliases(config_path: Path = BUSINESS_REPO_MODELS_CONFIG) -> set[str]:
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return set()
    models = payload.get("models")
    if not isinstance(models, dict):
        return set()
    return {str(key) for key in models.keys()}


CONFIGURED_MODEL_ALIASES = _load_configured_model_aliases()
FSJ_ASSIST_MODEL_CHAIN = tuple(
    alias
    for alias in (FSJ_MODEL_ALIAS, FSJ_FALLBACK_MODEL_ALIAS)
    if alias in CONFIGURED_MODEL_ALIASES or alias == FSJ_MODEL_ALIAS
)


def _classify_llm_exception(exc: Exception) -> str:
    if isinstance(exc, LLMInvocationFailure):
        return exc.classification
    text = str(exc).lower()
    if isinstance(exc, subprocess.TimeoutExpired) or "timed out" in text or "timeout" in text:
        return "timeout"
    if "boundary violated" in text:
        return "boundary_violation"
    if "did not contain parsed_json object" in text or "non-json envelope" in text or "invalid llm field" in text:
        return "malformed_output"
    if "unknown model alias" in text or "provider not found" in text or "unsupported api_type" in text:
        return "configuration_error"
    if "business repo llm cli failed" in text:
        return "provider_failure"
    if "llm assist disabled" in text:
        return "disabled"
    return "invoke_error"


def _wrap_resilience_raw_response(raw_response: dict[str, Any] | list[Any] | None, *, attempted_model_chain: list[str], failures: list[dict[str, str]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "_fsj_resilience": {
            "attempted_model_chain": attempted_model_chain,
            "failures": failures,
        }
    }
    if isinstance(raw_response, dict):
        payload.update(raw_response)
    elif raw_response is not None:
        payload["raw_response"] = raw_response
    return payload


class ResilientLateLLMClient:
    prompt_version = FSJ_LATE_PROMPT_VERSION
    primary_model_alias = FSJ_MODEL_ALIAS
    fallback_model_aliases = tuple(alias for alias in FSJ_ASSIST_MODEL_CHAIN[1:])

    def __init__(self, clients: list[BusinessRepoLateLLMClient] | None = None) -> None:
        self.clients = clients or [BusinessRepoLateLLMClient(model_alias=alias) for alias in FSJ_ASSIST_MODEL_CHAIN]
        self.model_alias = self.clients[0].model_alias if self.clients else FSJ_MODEL_ALIAS

    def synthesize(self, request: FSJLateLLMRequest) -> FSJLateLLMResult:
        failures: list[dict[str, str]] = []
        attempted_model_chain = [client.model_alias for client in self.clients]
        for client in self.clients:
            try:
                result = client.synthesize(request)
                object.__setattr__(
                    result,
                    "raw_response",
                    _wrap_resilience_raw_response(result.raw_response, attempted_model_chain=attempted_model_chain, failures=failures),
                )
                return result
            except Exception as exc:
                failures.append(
                    {
                        "model_alias": client.model_alias,
                        "classification": _classify_llm_exception(exc),
                        "detail": str(exc),
                    }
                )
        if failures:
            last = failures[-1]
            raise LLMInvocationFailure(last["classification"], json.dumps({"failures": failures}, ensure_ascii=False), last["model_alias"])
        raise LLMInvocationFailure("disabled", "no llm clients configured", self.model_alias)


class ResilientEarlyLLMClient:
    prompt_version = FSJ_EARLY_PROMPT_VERSION
    primary_model_alias = FSJ_MODEL_ALIAS
    fallback_model_aliases = tuple(alias for alias in FSJ_ASSIST_MODEL_CHAIN[1:])

    def __init__(self, clients: list[BusinessRepoEarlyLLMClient] | None = None) -> None:
        self.clients = clients or [BusinessRepoEarlyLLMClient(model_alias=alias) for alias in FSJ_ASSIST_MODEL_CHAIN]
        self.model_alias = self.clients[0].model_alias if self.clients else FSJ_MODEL_ALIAS

    def synthesize(self, request: FSJEarlyLLMRequest) -> FSJEarlyLLMResult:
        failures: list[dict[str, str]] = []
        attempted_model_chain = [client.model_alias for client in self.clients]
        for client in self.clients:
            try:
                result = client.synthesize(request)
                object.__setattr__(
                    result,
                    "raw_response",
                    _wrap_resilience_raw_response(result.raw_response, attempted_model_chain=attempted_model_chain, failures=failures),
                )
                return result
            except Exception as exc:
                failures.append(
                    {
                        "model_alias": client.model_alias,
                        "classification": _classify_llm_exception(exc),
                        "detail": str(exc),
                    }
                )
        if failures:
            last = failures[-1]
            raise LLMInvocationFailure(last["classification"], json.dumps({"failures": failures}, ensure_ascii=False), last["model_alias"])
        raise LLMInvocationFailure("disabled", "no llm clients configured", self.model_alias)


class ResilientMidLLMClient:
    prompt_version = FSJ_MID_PROMPT_VERSION
    primary_model_alias = FSJ_MODEL_ALIAS
    fallback_model_aliases = tuple(alias for alias in FSJ_ASSIST_MODEL_CHAIN[1:])

    def __init__(self, clients: list[BusinessRepoMidLLMClient] | None = None) -> None:
        self.clients = clients or [BusinessRepoMidLLMClient(model_alias=alias) for alias in FSJ_ASSIST_MODEL_CHAIN]
        self.model_alias = self.clients[0].model_alias if self.clients else FSJ_MODEL_ALIAS

    def synthesize(self, request: FSJMidLLMRequest) -> FSJMidLLMResult:
        failures: list[dict[str, str]] = []
        attempted_model_chain = [client.model_alias for client in self.clients]
        for client in self.clients:
            try:
                result = client.synthesize(request)
                object.__setattr__(
                    result,
                    "raw_response",
                    _wrap_resilience_raw_response(result.raw_response, attempted_model_chain=attempted_model_chain, failures=failures),
                )
                return result
            except Exception as exc:
                failures.append(
                    {
                        "model_alias": client.model_alias,
                        "classification": _classify_llm_exception(exc),
                        "detail": str(exc),
                    }
                )
        if failures:
            last = failures[-1]
            raise LLMInvocationFailure(last["classification"], json.dumps({"failures": failures}, ensure_ascii=False), last["model_alias"])
        raise LLMInvocationFailure("disabled", "no llm clients configured", self.model_alias)


class FSJLateLLMAssistant:
    def __init__(self, client: FSJLateLLMClient | None = None) -> None:
        self.client = client or ResilientLateLLMClient()

    def maybe_synthesize(self, request: FSJLateLLMRequest) -> tuple[FSJLateLLMResult | None, dict[str, Any]]:
        input_digest = hashlib.sha1(
            json.dumps(request.evidence_packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        try:
            result = self.client.synthesize(request)
            audit = result.audit_payload(input_digest=input_digest)
            audit["policy"] = {
                "primary_model_alias": getattr(self.client, "primary_model_alias", getattr(self.client, "model_alias", FSJ_MODEL_ALIAS)),
                "fallback_model_aliases": list(getattr(self.client, "fallback_model_aliases", [])),
                "attempted_model_chain": (getattr(result, "raw_response", {}) or {}).get("_fsj_resilience", {}).get("attempted_model_chain", [result.model_alias]),
                "outcome": "fallback_applied" if result.model_alias != getattr(self.client, "primary_model_alias", result.model_alias) else "primary_applied",
            }
            failures = (getattr(result, "raw_response", {}) or {}).get("_fsj_resilience", {}).get("failures", [])
            if failures:
                audit["policy"]["prior_failures"] = failures
            return result, audit
        except Exception as exc:
            classification = _classify_llm_exception(exc)
            fallback_model_aliases = list(getattr(self.client, "fallback_model_aliases", []))
            attempted_model_chain = [getattr(self.client, "model_alias", FSJ_MODEL_ALIAS), *fallback_model_aliases]
            error_detail = str(exc)
            prior_failures = None
            if isinstance(exc, LLMInvocationFailure):
                try:
                    parsed = json.loads(exc.detail)
                    prior_failures = parsed.get("failures") if isinstance(parsed, dict) else None
                except Exception:
                    prior_failures = None
                error_detail = exc.detail
            return None, {
                "applied": False,
                "model_alias": getattr(self.client, "model_alias", FSJ_MODEL_ALIAS),
                "prompt_version": getattr(self.client, "prompt_version", FSJ_LATE_PROMPT_VERSION),
                "input_digest": input_digest,
                "error": error_detail,
                "failure_classification": classification,
                "policy": {
                    "primary_model_alias": getattr(self.client, "primary_model_alias", getattr(self.client, "model_alias", FSJ_MODEL_ALIAS)),
                    "fallback_model_aliases": fallback_model_aliases,
                    "attempted_model_chain": attempted_model_chain,
                    "outcome": "deterministic_degrade",
                    "operator_tag": f"llm_{classification}",
                },
                **_audit_field_lineage(slot="late", applied=False, reason=classification),
                **({"attempt_failures": prior_failures} if prior_failures else {}),
            }


class FSJEarlyLLMAssistant:
    def __init__(self, client: FSJEarlyLLMClient | None = None) -> None:
        self.client = client or ResilientEarlyLLMClient()

    def maybe_synthesize(self, request: FSJEarlyLLMRequest) -> tuple[FSJEarlyLLMResult | None, dict[str, Any]]:
        input_digest = hashlib.sha1(
            json.dumps(request.evidence_packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        try:
            result = self.client.synthesize(request)
            audit = result.audit_payload(input_digest=input_digest)
            audit["policy"] = {
                "primary_model_alias": getattr(self.client, "primary_model_alias", getattr(self.client, "model_alias", FSJ_MODEL_ALIAS)),
                "fallback_model_aliases": list(getattr(self.client, "fallback_model_aliases", [])),
                "attempted_model_chain": (getattr(result, "raw_response", {}) or {}).get("_fsj_resilience", {}).get("attempted_model_chain", [result.model_alias]),
                "outcome": "fallback_applied" if result.model_alias != getattr(self.client, "primary_model_alias", result.model_alias) else "primary_applied",
            }
            failures = (getattr(result, "raw_response", {}) or {}).get("_fsj_resilience", {}).get("failures", [])
            if failures:
                audit["policy"]["prior_failures"] = failures
            return result, audit
        except Exception as exc:
            classification = _classify_llm_exception(exc)
            fallback_model_aliases = list(getattr(self.client, "fallback_model_aliases", []))
            attempted_model_chain = [getattr(self.client, "model_alias", FSJ_MODEL_ALIAS), *fallback_model_aliases]
            error_detail = str(exc)
            prior_failures = None
            if isinstance(exc, LLMInvocationFailure):
                try:
                    parsed = json.loads(exc.detail)
                    prior_failures = parsed.get("failures") if isinstance(parsed, dict) else None
                except Exception:
                    prior_failures = None
                error_detail = exc.detail
            return None, {
                "applied": False,
                "model_alias": getattr(self.client, "model_alias", FSJ_MODEL_ALIAS),
                "prompt_version": getattr(self.client, "prompt_version", FSJ_EARLY_PROMPT_VERSION),
                "input_digest": input_digest,
                "error": error_detail,
                "failure_classification": classification,
                "policy": {
                    "primary_model_alias": getattr(self.client, "primary_model_alias", getattr(self.client, "model_alias", FSJ_MODEL_ALIAS)),
                    "fallback_model_aliases": fallback_model_aliases,
                    "attempted_model_chain": attempted_model_chain,
                    "outcome": "deterministic_degrade",
                    "operator_tag": f"llm_{classification}",
                },
                **_audit_field_lineage(slot="early", applied=False, reason=classification),
                **({"attempt_failures": prior_failures} if prior_failures else {}),
            }


class FSJMidLLMAssistant:
    def __init__(self, client: FSJMidLLMClient | None = None) -> None:
        self.client = client or ResilientMidLLMClient()

    def maybe_synthesize(self, request: FSJMidLLMRequest) -> tuple[FSJMidLLMResult | None, dict[str, Any]]:
        input_digest = hashlib.sha1(
            json.dumps(request.evidence_packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        try:
            result = self.client.synthesize(request)
            audit = result.audit_payload(input_digest=input_digest)
            audit["policy"] = {
                "primary_model_alias": getattr(self.client, "primary_model_alias", getattr(self.client, "model_alias", FSJ_MODEL_ALIAS)),
                "fallback_model_aliases": list(getattr(self.client, "fallback_model_aliases", [])),
                "attempted_model_chain": (getattr(result, "raw_response", {}) or {}).get("_fsj_resilience", {}).get("attempted_model_chain", [result.model_alias]),
                "outcome": "fallback_applied" if result.model_alias != getattr(self.client, "primary_model_alias", result.model_alias) else "primary_applied",
            }
            failures = (getattr(result, "raw_response", {}) or {}).get("_fsj_resilience", {}).get("failures", [])
            if failures:
                audit["policy"]["prior_failures"] = failures
            return result, audit
        except Exception as exc:
            classification = _classify_llm_exception(exc)
            fallback_model_aliases = list(getattr(self.client, "fallback_model_aliases", []))
            attempted_model_chain = [getattr(self.client, "model_alias", FSJ_MODEL_ALIAS), *fallback_model_aliases]
            error_detail = str(exc)
            prior_failures = None
            if isinstance(exc, LLMInvocationFailure):
                try:
                    parsed = json.loads(exc.detail)
                    prior_failures = parsed.get("failures") if isinstance(parsed, dict) else None
                except Exception:
                    prior_failures = None
                error_detail = exc.detail
            return None, {
                "applied": False,
                "model_alias": getattr(self.client, "model_alias", FSJ_MODEL_ALIAS),
                "prompt_version": getattr(self.client, "prompt_version", FSJ_MID_PROMPT_VERSION),
                "input_digest": input_digest,
                "error": error_detail,
                "failure_classification": classification,
                "policy": {
                    "primary_model_alias": getattr(self.client, "primary_model_alias", getattr(self.client, "model_alias", FSJ_MODEL_ALIAS)),
                    "fallback_model_aliases": fallback_model_aliases,
                    "attempted_model_chain": attempted_model_chain,
                    "outcome": "deterministic_degrade",
                    "operator_tag": f"llm_{classification}",
                },
                **_audit_field_lineage(slot="mid", applied=False, reason=classification),
                **({"attempt_failures": prior_failures} if prior_failures else {}),
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
