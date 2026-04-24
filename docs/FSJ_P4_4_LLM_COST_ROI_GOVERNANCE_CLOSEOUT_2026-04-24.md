# FSJ P4-4 LLM cost / ROI governance closeout — 2026-04-24

## Verdict

`P4-4` is materially closed for the current roadmap scope.

The roadmap line item was stale. The bounded production-grade seam requested by `P4-4` already exists in shipped code and operator-visible surfaces:
- call frequency is measured from persisted bundle lineage
- fallback and degraded/failure rates are computed and surfaced
- slot/model usage is classified on canonical per-artifact and fleet views
- explicit budget ceiling / operational policy is loaded from config and enforced as operator-visible governance posture

The last real operator-read gap inside this scope was lineage parity, and that was landed via `scripts/fsj_artifact_lineage.py` in commit `c688b26`.

## What is already implemented

### 1) Budget / ROI policy source is explicit
File:
- `ifa-business-layer/config/llm/models.yaml`

Current FSJ budget policy defines bounded operating thresholds:
- `require_pricing_for_all_usage: true`
- `max_total_tokens_per_artifact: 12000`
- `max_total_tokens_fleet: 40000`
- `max_fallback_rate: 0.50`
- `max_degraded_rate: 0.50`

This is already a real operator policy surface, not a placeholder.

### 2) Canonical cost estimation + governance evaluation exist in `FSJStore`
File:
- `src/ifa_data_platform/fsj/store.py`

Implemented seams:
- `_estimate_usage_cost_usd(...)`
- `_llm_budget_posture(...)`
- `_evaluate_llm_budget_governance(...)`

These compute and classify:
- priced vs unpriced usage posture
- estimated cost by configured model pricing
- token ceilings
- fallback rate
- degraded rate
- governance states such as:
  - `within_budget`
  - `pricing_incomplete`
  - `budget_exceeded`
  - `token_budget_exceeded`
  - `roi_review_required`

This closes the roadmap asks for:
- measure call frequency by slot
- measure fallback rate and failure/degraded rate
- classify where thinking/fallback posture requires review
- define cost ceiling / operational budget policy

### 3) Operator-visible read surfaces already expose the policy truth
Files:
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`
- `scripts/fsj_artifact_lineage.py`
- `scripts/fsj_drift_monitor.py`

These surfaces now expose, in bounded operator-readable form:
- `llm_usage_bundle_count`
- `llm_estimated_cost_usd`
- `llm_uncosted_bundle_count`
- `llm_budget_posture`
- `llm_budget_summary_line`
- `llm_budget_governance_status`
- `llm_budget_governance_required_action`
- `llm_budget_governance_summary_line`
- model-level usage breakdown
- slot-level usage breakdown
- fleet aggregate budget posture

This is enough to answer both per-artifact and fleet operator questions without inventing a new control-plane.

### 4) Regression evidence already covers the bounded seam
Core evidence anchors:
- `tests/unit/test_fsj_store_json_serialization.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_artifact_lineage_script.py`
- `tests/unit/test_fsj_drift_monitor_script.py`

Covered behaviors include:
- estimated cost when model pricing is configured
- pricing-incomplete posture when unpriced usage remains
- per-artifact governance summaries on main/support status surfaces
- fleet governance summaries and model/slot breakdowns on operator board
- lineage parity for budget-governance fields
- drift views carrying cost/uncosted posture over time

## Exact bounded scope being closed

This closeout is intentionally bounded to the current roadmap scope:
- truthful measurement and classification from persisted FSJ LLM usage
- explicit operator policy thresholds
- operator-visible budget/ROI governance posture on canonical read surfaces

## Explicitly not claimed

This closeout does **not** claim:
- dynamic model-routing optimization beyond current threshold review signals
- financial ROI attribution to downstream trading/report outcomes
- broader multi-provider procurement / vendor strategy
- `P4-5` strategic architecture convergence

Those are broader expansions, not required to honestly close the current `P4-4` seam.

## Evidence summary

### Policy/config
- `ifa-business-layer/config/llm/models.yaml`

### Canonical implementation
- `src/ifa_data_platform/fsj/store.py`

### Operator/read surfaces
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`
- `scripts/fsj_artifact_lineage.py`
- `scripts/fsj_drift_monitor.py`

### Regression anchors
- `tests/unit/test_fsj_store_json_serialization.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_artifact_lineage_script.py`
- `tests/unit/test_fsj_drift_monitor_script.py`

## Recommended roadmap status update

`P4-4. LLM cost / ROI governance` => **Materially closed for current roadmap scope**

Reason:
- budget policy exists
- cost estimation exists
- pricing posture exists
- fallback/degraded ROI review thresholds exist
- per-artifact and fleet operator surfaces exist
- bounded lineage parity gap is already closed
