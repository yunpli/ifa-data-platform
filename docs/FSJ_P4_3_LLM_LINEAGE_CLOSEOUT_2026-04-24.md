# FSJ P4-3 LLM lineage closeout — 2026-04-24

## Verdict

P4-3 is now materially closed for the current thin-slice roadmap scope.

The last unresolved gap called out by the roadmap was explicit adopted-vs-discarded LLM field lineage. That gap is now implemented at bundle audit level, projected through lineage summaries, and regression-covered.

## What landed

### 1) Bundle-level adopted vs discarded field lineage is now persisted

File: `src/ifa_data_platform/fsj/llm_assist.py`

Each FSJ slot assistant audit payload now records:
- `allowed_output_fields`
- `adopted_output_fields`
- `discarded_output_fields`
- `adopted_output_field_count`
- `discarded_output_field_count`
- `field_replay_ready`
- `discard_reason`

Behavior:
- successful validated LLM application => allowed fields are marked adopted, `field_replay_ready=true`
- deterministic degrade / failure => allowed fields are marked discarded with explicit `discard_reason`

This closes the previously missing “which validated fields were actually adopted vs dropped” audit seam.

### 2) Operator/audit lineage surfaces now project the field lineage

File: `src/ifa_data_platform/fsj/store.py`

`report_llm_lineage_from_artifact(...)` now carries per-bundle field-lineage facts into the projected lineage surface.

`report_llm_lineage_summary(...)` now aggregates and exposes:
- `adopted_output_field_count`
- `discarded_output_field_count`
- `field_replay_ready_bundle_count`
- summary-line tokens such as `adopted_fields=...`, `discarded_fields=...`, `field_replay_ready=...`

Because operator review surfaces already consume canonical lineage/summary projection, this makes the new audit facts operator-visible without adding a new parallel surface.

### 3) Bounded replay support is sufficient for current scope

Current bounded replay evidence remains intact via existing persisted:
- `prompt_version`
- `model_alias`
- `input_digest`
- slot lineage ids / replay ids

With the new adopted/discarded field projection, bounded replay can now answer both:
- what prompt/model/input digest produced the attempt
- which allowed fields were actually adopted into the persisted bundle

That is enough for honest closeout of the current roadmap slice without expanding into a broader replay framework.

## Evidence

### Code
- `src/ifa_data_platform/fsj/llm_assist.py`
- `src/ifa_data_platform/fsj/store.py`

### Regression tests
- `tests/unit/test_fsj_early_llm_assist.py`
- `tests/unit/test_fsj_store_json_serialization.py`

### Focused assertions now covered
- success-path audit payload includes adopted fields + replay readiness
- failure-path audit payload includes discarded count + discard reason
- artifact lineage projection carries per-bundle field lineage
- aggregate lineage summary surfaces adopted/discarded/replay-ready counts

## Explicit boundary

This closeout does **not** claim:
- broad strategic cross-repo architecture convergence (`P4-5`)
- model budget / ROI policy (`P4-4`)
- a larger generic replay subsystem beyond the current bounded FSJ lineage surface

Those remain outside this thin-slice P4-3 closeout.

## Recommended roadmap status update

`P4-3. LLM audit and lineage tightening` => **closed for current scope**

Reason:
- prompt/model/outcome lineage already existed
- adopted-vs-discarded field lineage now exists
- operator-visible lineage projection now includes the new facts
- bounded same-prompt-version replay explanation is sufficiently supported for the current production-grade FSJ slice
