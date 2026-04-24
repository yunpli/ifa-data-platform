# FSJ P2-1 Unified Report-Production State Machine Closeout — 2026-04-24

## Verdict

`P2-1` is materially closed for the current roadmap scope.

No additional production code seam is required for honest closeout.
The bounded roadmap ask was to establish one canonical report lifecycle vocabulary, map current persisted workflow/package/dispatch truth into that vocabulary, and surface invalid-state attention instead of letting broken transitions masquerade as progress. That is now present on the canonical store projection and reused by the operator-facing read surfaces.

What is **not** claimed here is a broad workflow engine or hard transition-enforcement subsystem across all future runtime mutations. That would be a larger product branch, and it is not required to honestly close the current roadmap slice.

## Scope required by roadmap

Roadmap target for `P2-1`:
- define allowed states:
  - planned
  - collecting
  - producing
  - qa_pending
  - review_ready
  - send_ready
  - sent
  - held
  - failed
  - superseded
- map current module-local states into canonical states
- enforce transitions and invalid-state detection

## Exact closure mapping

### 1) Allowed canonical states are explicitly defined — closed

Canonical lifecycle/state vocabulary now lives in the canonical FSJ store projection layer:
- `src/ifa_data_platform/fsj/store.py`
  - `CANONICAL_REPORT_LIFECYCLE_STATES`
  - `CANONICAL_REPORT_STATE_VOCABULARY`
  - `project_report_state_vocabulary(...)`

This provides one stable vocabulary for operator-visible status semantics and buckets instead of each read surface inventing its own state labels.

Regression evidence:
- `tests/unit/test_fsj_store_json_serialization.py`
  - `test_project_report_state_vocabulary_exposes_explicit_canonical_mapping`

### 2) Current workflow/package/dispatch truth is mapped into the canonical lifecycle — closed

Canonical lifecycle projection now exists in one place:
- `src/ifa_data_platform/fsj/store.py`
  - `project_report_lifecycle_state(...)`

This projector resolves persisted artifact/workflow/package/dispatch truth into canonical states including:
- `planned`
- `collecting`
- `producing`
- `qa_pending`
- `review_ready`
- `send_ready`
- `sent`
- `held`
- `failed`
- `superseded`

Key bounded mappings already implemented:
- `artifact.status=superseded` → `superseded`
- successful dispatch receipt → `sent`
- failed dispatch receipt → `failed`
- `recommended_action=send` + `ready_for_delivery=true` → `send_ready`
- review-required workflow / `send_review` → `review_ready`
- withdrawn / hold states → `held`
- package ready without final workflow approval → `qa_pending`
- producing/assembling/rendering/publishing → `producing`
- collecting / scheduled / planned → `collecting` or `planned`
- selected-candidate mismatch downgrades non-terminal ready states into operator-visible review attention

Regression evidence:
- `tests/unit/test_fsj_store_json_serialization.py`
  - `test_report_operator_review_surface_projects_dispatch_state_from_receipt_and_send_ready`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`

## 3) Invalid transition / state integrity detection exists at the bounded seam — closed

The first honest transition-enforcement slice is already implemented:
- `src/ifa_data_platform/fsj/store.py`
  - `project_report_transition_integrity(...)`

What it currently enforces:
- persisted `dispatch_attempted` / `dispatch_failed` / `dispatch_succeeded` receipts are only considered valid when the workflow truth is actually sendable
- if dispatch receipts appear on non-sendable workflow truth (`recommended_action != send` or `ready_for_delivery = false`), the artifact is projected as:
  - `transition_integrity.invalid_transition = true`
  - stable `reason_code = dispatch_receipt_without_sendable_workflow`
  - canonical lifecycle `failed`

This is the bounded roadmap-close interpretation of “enforce transitions and invalid-state detection”: invalid persisted forward progress is made explicit and operator-visible on the canonical read path.

Regression evidence:
- `tests/unit/test_fsj_store_json_serialization.py`
  - `test_project_report_transition_integrity_flags_dispatch_without_sendable_workflow`
  - `test_report_operator_review_surface_projects_invalid_dispatch_transition_as_failed_attention`
- `tests/unit/test_fsj_operator_board_script.py`
  - invalid-transition reason projects into board blocking reason / aggregate history

### 4) Canonical state truth is reused by operator-facing read surfaces — closed

The canonical lifecycle and transition-integrity projection is not stranded in store-only helpers; it is reused across operator surfaces:

Canonical projection ingress:
- `src/ifa_data_platform/fsj/store.py`
  - `report_operator_review_surface_from_surface(...)`
  - `build_operator_board_surface(...)`

Operator read surfaces:
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`

Operator-visible outputs now include:
- `canonical_lifecycle_state`
- `canonical_lifecycle_reason`
- `transition_integrity_valid`
- `transition_integrity_reason`
- semantic board status / operator bucket derived from canonical truth
- fleet aggregate lifecycle counts on the operator board

Regression evidence:
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_send_dispatch_failure_status_script.py`
- `tests/unit/test_fsj_support_dispatch_failure_status_script.py`

## 5) Why no further state-machine seam is required right now

The remaining ideas would broaden scope into a larger product branch, for example:
- a runtime mutation engine that refuses all illegal transitions at write time
- a generalized orchestration/state-machine framework for every future report action
- command-driven promote/retry/override workflow actions with persistent transition journals
- broad re-architecture of all module-local progress states before roadmap closeout

Those may be valid future improvements, but they are not necessary to honestly say the current roadmap slice is done.

For current scope, the essential outcomes already exist:
- one canonical state vocabulary
- one canonical lifecycle projector
- one bounded invalid-transition detector
- operator-visible projection on the main read surfaces
- regression coverage proving that persisted state truth is normalized and broken transitions are surfaced as attention

## Evidence anchors

Implementation:
- `src/ifa_data_platform/fsj/store.py`
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`

Tests:
- `tests/unit/test_fsj_store_json_serialization.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_send_dispatch_failure_status_script.py`
- `tests/unit/test_fsj_support_dispatch_failure_status_script.py`

## Close status

- canonical lifecycle vocabulary: done
- canonical lifecycle projection: done
- bounded invalid-transition detection: done
- operator-facing reuse on read surfaces: done
- current closeout result: **`P2-1` materially closed for current roadmap scope**

## Deferred non-blocking expansions

These are intentionally deferred and are not blockers for this closeout:
- broader write-time transition enforcement across every future mutation path
- generalized workflow-engine/productization work
- expanded command/control surfaces for promote/retry/override beyond current read-side governance projection
- any broader state-machine product branch outside the thinnest honest roadmap-close seam
