# FSJ P1-1 / P1-2 Closeout — 2026-04-24

## Verdict

`P1-1` and `P1-2` are materially closed for the current roadmap scope.

The support lane is now independently producible, reviewable, packageable, and operator-auditable through the canonical support batch publish seam, while MAIN consumes only concise support summaries with preserved lineage/version mapping. The remaining broader product/control-plane work belongs to later roadmap items, not to these two seams.

## Scope required by roadmap

### P1-1 support standalone report production path
Roadmap target:
- support reports must be standalone, reviewable, packageable, auditable
- early/late artifact generation parity across `macro`, `commodities`, `ai_tech`
- support artifacts must not exist only as MAIN side effects
- canonical operator path remains `scripts/fsj_support_batch_publish.py`

### P1-2 MAIN/support artifact convergence
Roadmap target:
- MAIN consumes concise support summaries
- support summaries never inline full support report bodies into MAIN
- support summary provenance and version mapping remain explicit

## Exact closure mapping

### 1) Support standalone operator path is canonical and version-linked — closed (`P1-1`)

Canonical operator path:
- `scripts/fsj_support_batch_publish.py`
- `scripts/fsj_support_bundle_persist.py`
- `scripts/fsj_support_report_publish.py`

What is now true:
- persistence is built into the operator path (`persist-before-publish`)
- one batch command handles all three support domains for `early` / `late`
- package/workflow/review surfaces are resolved back through canonical FSJ truth after publish
- blocked handling is truthful via `--require-ready`

Operator/runbook evidence:
- `docs/FSJ_SUPPORT_STANDALONE_RUNBOOK.md`
- `docs/FSJ_EARLY_SLOT_RUNBOOK.md`
- `docs/FSJ_LATE_SLOT_RUNBOOK.md`

Regression evidence:
- `tests/unit/test_fsj_support_batch_publish_script.py`
- `tests/unit/test_fsj_support_report_publish_script.py`
- `tests/unit/test_fsj_support_bundle_persist_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`

### 2) Early/late support standalone parity across all three domains is evidenced — closed (`P1-1`)

Operator/live evidence anchors:
- `docs/FSJ_SLA_PROOF_PACKAGE_2026-04-23.md`
- `docs/FSJ_P0_4_ACCEPTANCE_LEDGER_2026-04-23.md`

Specific evidenced facts:
- early support standalone live proof exists for all three support domains
- late support standalone convergence proof exists and preserves the honest initial blocked-to-green story
- all three support domains are emitted as standalone artifacts, not MAIN-only side effects

Artifact evidence paths cited by the acceptance package:
- `artifacts/fsj_support_batch_20260423_liveproof_subA/`
- `artifacts/fsj_support_batch_20260423_late_liveproof_subA/`
- `artifacts/fsj_support_batch_20260423_late_liveproof_subA_rerun/`

### 3) Support stays independently auditable on its own rendering/publishing path — closed (`P1-1`)

Standalone support rendering/publish surfaces:
- `src/ifa_data_platform/fsj/report_rendering.py`
  - `SupportReportHTMLRenderer`
  - `SupportReportArtifactPublishingService`
- `src/ifa_data_platform/fsj/report_assembly.py`
  - `SupportReportAssemblyService`

Regression evidence:
- `tests/unit/test_fsj_report_rendering.py`
- `tests/unit/test_fsj_report_assembly.py`

What is explicitly preserved:
- support report artifact family stays separate from MAIN artifact family
- support artifacts keep their own bundle/report-link lineage
- support report HTML remains directly publishable and auditable as its own operator-facing artifact

### 4) MAIN consumes concise support summaries only — closed (`P1-2`)

Canonical convergence implementation:
- `src/ifa_data_platform/fsj/report_assembly.py`
  - `MainReportAssemblyService.assemble_support_summary_aggregate(...)`
- `src/ifa_data_platform/fsj/report_rendering.py`
  - `MainReportHTMLRenderer`
  - delivery/package lineage projection carrying `support_summary_aggregate`

Regression evidence:
- `tests/unit/test_fsj_report_assembly.py`
  - asserts `main_consumes_only_concise_support_summaries`
  - asserts support aggregate items do not carry full graph/object payloads
- `tests/unit/test_fsj_report_rendering.py`
  - asserts support summaries are rendered as summaries/links in MAIN
  - asserts injected support full-body/detail fields do not appear in MAIN HTML

Acceptance-package evidence:
- `docs/FSJ_SLA_PROOF_PACKAGE_2026-04-23.md`
- `docs/FSJ_P0_4_ACCEPTANCE_LEDGER_2026-04-23.md`

### 5) Support-summary provenance and version mapping are explicit — closed (`P1-2`)

Canonical persisted lineage fields now carried through MAIN package/read surfaces:
- `support_summary_bundle_ids`
- `support_summary_aggregate.bundle_ids`
- `support_summary_aggregate.domains`
- `report_links` back to support artifacts

Implementation evidence:
- `src/ifa_data_platform/fsj/report_rendering.py`
- `src/ifa_data_platform/fsj/report_orchestration.py`
- `src/ifa_data_platform/fsj/report_dispatch.py`

Regression evidence:
- `tests/unit/test_fsj_report_rendering.py`
- `tests/unit/test_fsj_report_orchestration.py`
- `tests/unit/test_fsj_store_json_serialization.py`

Package evidence:
- `docs/FSJ_SLA_PROOF_PACKAGE_2026-04-23.md`
  - cites six support summary bundle IDs preserved across early/late convergence proof

## Why this is enough for honest closeout

`P1-1` and `P1-2` asked for a production-capable support standalone lane and bounded MAIN/support convergence.

That bar is now met:
- support has its own canonical persist+publish operator path
- support early/late outputs are evidenced as standalone artifacts across all three domains
- support artifacts are reviewable/packageable/operator-visible on their own seam
- MAIN consumes concise support summaries only
- support bundle/report-link provenance survives into MAIN package/read surfaces
- regression coverage now includes an explicit non-inline boundary assertion for support detail fields

What is **not** required to honestly close these seams:
- broader replay/state-machine/control-plane work (`P2-*`)
- deeper query façade work already tracked under `P1-3 / P1-4`
- semantic approval/governance expansion already tracked under `P2-5`
- broader multi-day SLA or dispatch-green proof beyond the already accepted 2026-04-23 evidence slice

## Evidence anchors

Implementation:
- `scripts/fsj_support_batch_publish.py`
- `scripts/fsj_support_bundle_persist.py`
- `scripts/fsj_support_report_publish.py`
- `scripts/fsj_main_early_publish.py`
- `scripts/fsj_main_late_publish.py`
- `src/ifa_data_platform/fsj/report_assembly.py`
- `src/ifa_data_platform/fsj/report_rendering.py`
- `src/ifa_data_platform/fsj/report_orchestration.py`
- `src/ifa_data_platform/fsj/report_dispatch.py`

Docs / proof:
- `docs/FSJ_SUPPORT_STANDALONE_RUNBOOK.md`
- `docs/FSJ_SLA_PROOF_PACKAGE_2026-04-23.md`
- `docs/FSJ_P0_4_ACCEPTANCE_LEDGER_2026-04-23.md`
- `docs/FSJ_EARLY_SLOT_RUNBOOK.md`
- `docs/FSJ_LATE_SLOT_RUNBOOK.md`

Tests:
- `tests/unit/test_fsj_support_batch_publish_script.py`
- `tests/unit/test_fsj_support_report_publish_script.py`
- `tests/unit/test_fsj_support_bundle_persist_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_report_assembly.py`
- `tests/unit/test_fsj_report_rendering.py`
- `tests/unit/test_fsj_report_orchestration.py`
- `tests/unit/test_fsj_store_json_serialization.py`

## Deferred non-blocking expansions

These may be worthwhile later, but are not blockers for `P1-1 / P1-2` closeout:
- richer support-side benchmarking beyond current scope (`P3-*`)
- broader operator automation/control-plane around support promotion/send (`P2-*`)
- stronger semantic diff tooling for summary-vs-body comparison beyond the current concise-boundary assertion
