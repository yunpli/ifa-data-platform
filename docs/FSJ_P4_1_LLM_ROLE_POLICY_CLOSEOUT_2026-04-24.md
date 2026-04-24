# FSJ P4-1 closeout — formal LLM role policy

## Scope
This closeout is intentionally narrow and only covers roadmap item `P4-1` at the current FSJ roadmap seam.

It does **not** claim full closure of:
- `P4-2` fallback/resilience governance
- `P4-3` adopted-vs-discarded field replay/audit completeness
- `P4-4` budget ceiling / ROI operating policy

The question here is only whether the current production FSJ seam already has a **formal, explicit, operator-visible LLM role policy** instead of an implicit one.

## Verdict
Yes.

No additional production code seam was required for honest closeout.
The implementation already provides the bounded policy contract requested by `P4-1`; what was missing was explicit closeout proof and roadmap truth normalization.

## What `P4-1` asked for
Roadmap target:
- define what LLM may and may not do
- define LLM-allowed fields
- define LLM-forbidden decisions
- define deterministic override precedence
- define per-slot boundary invariants

## Existing implementation that satisfies the bounded ask

### 1) Canonical policy is explicitly defined in code
File:
- `src/ifa_data_platform/fsj/llm_assist.py`

`build_fsj_role_policy(...)` already formalizes slot-specific policy for `early`, `mid`, and `late`.

It explicitly defines:
- `allowed_output_fields`
- `forbidden_decisions`
- `boundary_invariants`
- `deterministic_owner_fields`
- `override_precedence`
- `policy_version = fsj_llm_role_policy_v1`
- slot-specific `boundary_mode`

That means the policy is not merely implied by prompt text or scattered conventions; it is a canonical structured contract.

### 2) Policy is persisted into bundle/review payloads
Files:
- `src/ifa_data_platform/fsj/early_main_producer.py`
- `src/ifa_data_platform/fsj/mid_main_producer.py`
- `src/ifa_data_platform/fsj/late_main_producer.py`
- `src/ifa_data_platform/fsj/report_orchestration.py`
- `src/ifa_data_platform/fsj/store.py`

The role policy is attached to LLM-assisted bundle payloads and then projected into operator review surfaces.

In particular:
- `report_orchestration._build_llm_role_policy_review(...)` extracts operator-review policy facts
- `FSJStore` persists and reprojects:
  - `policy_versions`
  - `slot_boundary_modes`
  - `deterministic_owner_fields`
  - `forbidden_decisions`
  - `override_precedence`

So the policy survives past generation-time and becomes review/audit state.

### 3) Policy is operator-visible on canonical read surfaces
Files:
- `src/ifa_data_platform/fsj/main_publish_cli.py`
- `scripts/fsj_support_batch_publish.py`
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`
- `src/ifa_data_platform/fsj/report_dispatch.py`

The policy is surfaced in exactly the operator seams that matter for production use:
- publish summaries
- delivery-status scripts
- dispatch/read surfaces
- fleet operator board

Those surfaces expose at least:
- policy version(s)
- boundary mode(s)
- forbidden-decision count / details
- deterministic-owner fields
- override precedence
- slot boundary mode mapping

This is enough to satisfy the roadmap requirement that LLM behavior be formally defined and explainable at operator review time.

## Why this is enough for honest closeout
`P4-1` did **not** require:
- full fallback strategy governance
- full cost-ceiling enforcement
- full adopted/discarded field replay trail

Those are real adjacent roadmap concerns, but they belong under later `P4-*` items.

For the current bounded ask, the system already has:
1. an explicit formal policy source,
2. slot-specific invariants,
3. deterministic precedence semantics,
4. forbidden-decision semantics, and
5. operator-visible projection on canonical read surfaces.

That is materially sufficient to call `P4-1` closed for current roadmap scope.

## Test evidence
Verification sweep run:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest \
  tests/unit/test_fsj_main_early_publish_script.py \
  tests/unit/test_fsj_main_mid_publish_script.py \
  tests/unit/test_fsj_main_late_publish_script.py \
  tests/unit/test_fsj_support_batch_publish_script.py \
  tests/unit/test_fsj_report_dispatch.py \
  tests/unit/test_fsj_main_delivery_status_script.py \
  tests/unit/test_fsj_support_delivery_status_script.py \
  tests/unit/test_fsj_operator_board_script.py \
  tests/unit/test_fsj_store_json_serialization.py \
  -q
```

Result:
- `72 passed in 0.51s`

## Evidence anchors
### Canonical policy source
- `src/ifa_data_platform/fsj/llm_assist.py`

### Review projection / persistence
- `src/ifa_data_platform/fsj/report_orchestration.py`
- `src/ifa_data_platform/fsj/store.py`

### Operator-visible surfaces
- `src/ifa_data_platform/fsj/main_publish_cli.py`
- `scripts/fsj_support_batch_publish.py`
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`
- `src/ifa_data_platform/fsj/report_dispatch.py`

### Regression tests
- `tests/unit/test_fsj_main_early_publish_script.py`
- `tests/unit/test_fsj_main_mid_publish_script.py`
- `tests/unit/test_fsj_main_late_publish_script.py`
- `tests/unit/test_fsj_support_batch_publish_script.py`
- `tests/unit/test_fsj_report_dispatch.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_store_json_serialization.py`

## Current closeout result
- current closeout result: **`P4-1` materially closed for current roadmap scope**

## Explicit non-claims / next seam
This closeout does **not** claim:
- provider fallback policy is fully closed (`P4-2`)
- adopted-vs-discarded field persistence is fully closed (`P4-3`)
- budget ceiling / ROI operating policy is fully closed (`P4-4`)

Shortest next honest B-lane move after this is to inspect whether `P4-2` has a similarly bounded truth-normalization closeout available, or whether one final thin functional seam is still required before that claim can be made.
