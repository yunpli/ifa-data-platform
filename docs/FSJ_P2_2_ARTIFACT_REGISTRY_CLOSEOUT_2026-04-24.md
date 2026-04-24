# FSJ P2-2 Artifact Registry / Lineage Index Closeout — 2026-04-24

## Verdict

`P2-2` is materially closed for the current roadmap scope.

No additional production code seam is required for honest closeout.
The first bounded registry slice already landed the canonical artifact-family version-chain summary/query surface, and later board/read integrations now make that lineage truth operator-visible on the main fleet surface as well. The remaining larger ideas (global registry product, new write-paths, cross-family search UX) are optional expansion beyond the current roadmap-close seam.

## Scope required by roadmap

Roadmap target for `P2-2`:
- register artifact families and version chain
- link artifact → bundle graph → support summaries → send manifest
- expose artifact lineage for operator and audit
- support “what did user actually receive?” queries

## Exact closure mapping

### 1) Register artifact families and version chain — closed

Canonical persisted artifact family/version truth:
- `src/ifa_data_platform/fsj/store.py`
  - `register_report_artifact(...)`
  - `get_active_report_artifact(...)`
  - `get_latest_active_report_artifact(...)`
  - `list_report_delivery_surfaces(...)`
  - `summarize_report_artifact_registry(...)`

What is now queryable on the canonical registry summary:
- active head artifact id
- chain depth
- superseded / withdrawn / sent counts
- per-version entries with:
  - `artifact_id`
  - `report_run_id`
  - `supersedes_artifact_id`
  - lifecycle / dispatch state
  - bundle counts / missing-bundle counts
  - governance + promotion-authority state
  - selected/current flags
- anomaly checks:
  - dangling supersedes ids
  - multiply-superseded target ids

Regression evidence:
- `tests/unit/test_fsj_store_json_serialization.py`
  - `test_summarize_report_artifact_registry_exposes_version_chain_audit_surface`

### 2) Link artifact → bundle graph → support summaries → send manifest — closed for current scope

Canonical lineage projection unifies package/review/send/bundle truth:
- `src/ifa_data_platform/fsj/store.py`
  - `report_artifact_lineage_from_surface(...)`
  - `get_active_report_artifact_lineage(...)`
  - `get_latest_active_report_artifact_lineage(...)`
  - `list_report_artifact_lineages(...)`

What the lineage surface now carries together:
- artifact identity/version fields
- package paths and manifest/version pointers
- review/send manifests
- workflow handoff / selected artifact truth
- dispatch receipt + user-received summary
- bundle lineage with `bundle_id`, slot, section key/type, report run id, supersedes bundle id, missing flags
- LLM lineage / governance / review summary / board-state provenance

This is the bounded roadmap-close interpretation of the linkage ask: one canonical read surface joins the already-persisted artifact/package/review/send/bundle chain without inventing a separate registry subsystem.

Regression evidence:
- `tests/unit/test_fsj_store_json_serialization.py`
  - `test_report_artifact_lineage_projection_unifies_package_review_send_and_bundle_surfaces`
- `tests/integration/test_fsj_phase1.py`
  - active + recent superseded lineage queryability from persisted artifacts

### 3) Expose artifact lineage for operator and audit — closed

Canonical operator/audit surfaces:
- focused lineage CLI:
  - `scripts/fsj_artifact_lineage.py`
- operator board embedding / fleet visibility:
  - `src/ifa_data_platform/fsj/store.py`
    - `build_operator_board_surface(...)`
  - `scripts/fsj_operator_board.py`
- non-board delivery/read surfaces:
  - `scripts/fsj_main_delivery_status.py`
  - `scripts/fsj_support_delivery_status.py`

This means lineage truth is now visible in both places that matter for current scope:
- direct per-family inspection via `fsj_artifact_lineage.py`
- fleet/operator inspection via canonical board + delivery status reads

Regression evidence:
- `tests/unit/test_fsj_artifact_lineage_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_store_delivery_surface_selectors.py`

### 4) Support “what did user actually receive?” queries — closed

Canonical answer lives on the lineage surface:
- `src/ifa_data_platform/fsj/store.py`
  - `report_artifact_lineage_from_surface(...)`

Bounded user-received fields now include:
- `dispatch_state`
- `channel`
- `provider_message_id`
- `sent_at`
- `delivery_zip_path`
- `telegram_caption_path`
- `send_manifest_path`
- `error`

That is the exact current-scope answer to “what did user actually receive?” using persisted dispatch/package truth.

Regression evidence:
- `tests/unit/test_fsj_store_json_serialization.py`
- `tests/unit/test_fsj_artifact_lineage_script.py`

## Why no further code seam is needed

The original thin registry slice landed the missing core piece: explicit artifact-family/version-chain auditability.

After that landing, later A-lane work already integrated the same lineage/registry truth into:
- canonical operator board rows and fleet aggregates
- canonical main/support delivery-status reads
- operator-visible governance/promotion-authority context on lineage views

So the open gap is no longer missing registry behavior.
It is only missing closeout proof that the bounded roadmap ask is already satisfied.

## What is intentionally not claimed

This closeout does **not** claim:
- a new schema/table for a broad registry product
- cross-family/global search or indexing UX
- new registry write-paths beyond the existing artifact persistence path
- a separate replay/rerun subsystem
- broader control-plane/product work outside this lineage/index seam

Those are valid future expansions, but not blockers for honest `P2-2` closeout at current roadmap scope.

## Evidence anchors

Implementation:
- `src/ifa_data_platform/fsj/store.py`
- `scripts/fsj_artifact_lineage.py`
- `scripts/fsj_operator_board.py`
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`

Tests:
- `tests/unit/test_fsj_store_json_serialization.py`
- `tests/unit/test_fsj_artifact_lineage_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_store_delivery_surface_selectors.py`
- `tests/integration/test_fsj_phase1.py`

## Close status

- first bounded registry slice: done
- operator/audit visibility: done
- what-user-received query seam: done
- current closeout result: **`P2-2` materially closed for current roadmap scope**
