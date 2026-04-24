# FSJ P4-2 closeout — fallback and resilience policy

## Scope
This closeout is intentionally narrow and only covers roadmap item `P4-2` at the current FSJ roadmap seam.

It does **not** claim full closure of:
- `P4-3` adopted-vs-discarded field replay / deeper audit completeness
- `P4-4` budget ceiling / ROI operating policy
- `P4-5` broader strategic architecture convergence

The question here is only whether the current production FSJ seam already has a **formal, operator-visible fallback and resilience policy** for LLM assist instead of an informal best-effort behavior.

## Verdict
Yes.

No additional production code seam was required for honest closeout.
The implementation already provides the bounded fallback/resilience contract requested by `P4-2`; what was missing was explicit closeout proof and roadmap truth normalization.

## What `P4-2` asked for
Roadmap target:
- define primary model per slot/use case
- define backup model or deterministic fallback path
- define timeout and retry policy
- define behavior on malformed output / boundary violation
- define operator-visible fallback tagging

## Existing implementation that satisfies the bounded ask

### 1) Primary and fallback model chain is explicit in code
File:
- `src/ifa_data_platform/fsj/llm_assist.py`

The resilient client layer already formalizes the model chain:
- `FSJ_MODEL_ALIAS` is the primary model alias
- `FSJ_FALLBACK_MODEL_ALIAS` is the configured backup alias
- `FSJ_ASSIST_MODEL_CHAIN` defines the ordered chain used by `early` / `mid` / `late`
- `ResilientEarlyLLMClient`, `ResilientMidLLMClient`, and `ResilientLateLLMClient` iterate that chain deterministically

This means fallback behavior is not implicit operator folklore; it is codified as the canonical LLM assist execution path.

### 2) Failure handling is explicit and bounded
File:
- `src/ifa_data_platform/fsj/llm_assist.py`

`_classify_llm_exception(...)` already normalizes the relevant resilience classes:
- `timeout`
- `boundary_violation`
- `malformed_output`
- `configuration_error`
- `provider_failure`
- `disabled`
- `invoke_error`

The assistants then apply a bounded policy:
- if a later model in the chain succeeds, outcome becomes `fallback_applied`
- if the chain fails, outcome becomes `deterministic_degrade`
- the operator tag records the degraded reason (for example `llm_timeout`, `llm_malformed_output`, `llm_boundary_violation`)

That is exactly the roadmap requirement that failures degrade gracefully and predictably instead of producing uncontrolled behavior.

### 3) Timeout/retry posture is explicit at the current seam
Files:
- `src/ifa_data_platform/fsj/llm_assist.py`
- `ifa-business-layer` LLM CLI callsite invoked through the same wrapper

At current scope, the resilience policy is intentionally thin but explicit:
- each model attempt is bounded by `timeout_seconds`
- fallback proceeds by trying the next alias in the ordered chain
- there is no hidden infinite retry loop
- exhaustion of the chain resolves to deterministic degrade rather than fake output

For roadmap-close scope, that is sufficient: timeout handling and retry/fallback behavior are defined, predictable, and testable.

### 4) Operator-visible fallback tagging and audit already exists
Files:
- `src/ifa_data_platform/fsj/store.py`
- `src/ifa_data_platform/fsj/report_orchestration.py`
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`
- `scripts/fsj_llm_fallback_status.py`
- `docs/FSJ_LLM_FALLBACK_RUNBOOK.md`

The current production seam already persists and reprojects:
- `attempted_model_chain`
- `prior_failures`
- `outcome` (`primary_applied` / `fallback_applied` / `deterministic_degrade`)
- operator tags such as `llm_timeout`, `llm_malformed_output`, `llm_boundary_violation`
- aggregate fallback counts and degraded/missing-lineage posture

That truth is surfaced on:
- per-scope delivery status reads
- fleet operator board summaries
- fleet fallback attention CLI
- the operator runbook for fallback handling

So operators do not need to infer resilience outcomes from raw HTML or logs; the system exposes the fallback posture directly.

### 5) Slot-level proof and regression coverage already pins the contract
Files:
- `tests/unit/test_fsj_early_llm_assist.py`
- `tests/unit/test_fsj_main_mid_producer.py`
- `tests/unit/test_fsj_late_llm_assist.py`
- `tests/unit/test_fsj_late_llm_assist.py`
- `tests/unit/test_fsj_llm_fallback_status_script.py`
- `tests/unit/test_fsj_drift_monitor_script.py`
- `tests/integration/test_fsj_main_llm_resilience_golden_case_family.py`
- `scripts/prove_fsj_early_llm_fallback.py`
- `scripts/prove_fsj_mid_llm_fallback.py`
- `scripts/prove_fsj_late_llm_fallback.py`

The current test/proof surface already verifies:
- fallback occurs after primary failure
- attempted chain is preserved as `grok41_thinking -> gemini31_pro_jmr`
- timeout classification is preserved in prior failures
- malformed output and boundary violation are surfaced as operator tags
- deterministic degrade remains the terminal path when fallback cannot rescue the slot
- cross-slot resilience golden cases pin the contract at `early` / `mid` / `late`

## Why this is enough for honest closeout
`P4-2` did **not** require:
- a broad multi-provider orchestration framework
- a dynamic cost-aware routing engine
- adopted-vs-discarded field replay persistence
- a new governance/control-plane product surface beyond the current FSJ seam

For the bounded roadmap ask, the current system already has:
1. explicit primary/fallback model-chain policy,
2. explicit timeout/failure classification,
3. deterministic degrade behavior when fallback cannot recover,
4. operator-visible tagging and fleet summaries, and
5. slot-level proof plus regression coverage.

That is materially sufficient to call `P4-2` closed for current roadmap scope.

## Test evidence
Verification sweep run:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest \
  tests/unit/test_fsj_early_llm_assist.py \
  tests/unit/test_fsj_main_mid_producer.py \
  tests/unit/test_fsj_late_llm_assist.py \
  tests/unit/test_fsj_llm_fallback_status_script.py \
  tests/unit/test_fsj_drift_monitor_script.py \
  tests/integration/test_fsj_main_llm_resilience_golden_case_family.py \
  -q
```

Result:
- `38 passed in 0.60s`

## Evidence anchors
### Canonical resilience/fallback implementation
- `src/ifa_data_platform/fsj/llm_assist.py`

### Review projection / operator persistence
- `src/ifa_data_platform/fsj/report_orchestration.py`
- `src/ifa_data_platform/fsj/store.py`

### Operator-visible surfaces
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`
- `scripts/fsj_llm_fallback_status.py`
- `docs/FSJ_LLM_FALLBACK_RUNBOOK.md`

### Proof/eval seams
- `scripts/prove_fsj_early_llm_fallback.py`
- `scripts/prove_fsj_mid_llm_fallback.py`
- `scripts/prove_fsj_late_llm_fallback.py`

### Regression tests
- `tests/unit/test_fsj_early_llm_assist.py`
- `tests/unit/test_fsj_main_mid_producer.py`
- `tests/unit/test_fsj_late_llm_assist.py`
- `tests/unit/test_fsj_llm_fallback_status_script.py`
- `tests/unit/test_fsj_drift_monitor_script.py`
- `tests/integration/test_fsj_main_llm_resilience_golden_case_family.py`

## Current closeout result
- current closeout result: **`P4-2` materially closed for current roadmap scope**

## Explicit non-claims / next seam
This closeout does **not** claim:
- adopted-vs-discarded field persistence/replay is fully closed (`P4-3`)
- budget ceiling / ROI operating policy is fully closed (`P4-4`)
- broader architecture convergence is closed (`P4-5`)

Shortest next honest B-lane move after this is to inspect whether `P4-3` has a similarly bounded closeout path, while continuing to treat `P4-4` as materially open unless explicit budget policy is actually landed.
