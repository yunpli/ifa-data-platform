# Production-Grade A-Share System Roadmap (P0-P4)

Date: 2026-04-23  
Owner: Developer Lindenwood  
Scope: `ifa-business-layer` + `ifa-data-platform`  
Standard: production-grade, operator-auditable, replayable, bounded-LLM, evidence-first

---

## 0. Executive Summary

This roadmap reorganizes the current A-share 2.0 work into a production-grade implementation program.

Current system target:
- One-main / three-support (`MAIN`, `macro`, `commodities`, `ai_tech`)
- Slot-based production (`early`, `mid`, `late`)
- FSJ-based evidence / signal / judgment persistence
- Deterministic core with bounded LLM assist (currently Grok-centered)
- Operator-facing review / package / dispatch / runtime evidence

This file is **not** the execution source of truth.  
Execution must still be reflected in the Task DB / template change DB / runtime evidence.

---

## 1. Current Progress Snapshot

### Already materially completed
- A-share phase-1 business contracts frozen
- Early / mid / late business consumption contracts frozen
- One-main / three-support business structure frozen
- Support-agent buildout package frozen
- Production SLA / main queue frozen
- Support producer parity complete in business layer:
  - `macro` ✅
  - `ai_tech` ✅
  - `commodities` ✅
- FSJ persistence phase-1 skeleton landed in data platform:
  - bundles / objects / edges / evidence_links / observed_records / report_links
- MAIN producer slices landed in data platform:
  - `early` ✅
  - `mid` ✅
  - `late` ✅
- MAIN delivery stack partially landed:
  - QA gate
  - evaluation harness
  - delivery packaging
  - dispatch helper
  - operator review bundle
  - candidate comparison artifact
- Runtime production incident closure completed (2026-04-23):
  - same-minute duplicate schedule firing fixed
  - trade calendar stale sync/coverage gate fixed
  - `sector_performance` fail-fast timeout fix landed
  - orphan running rows repair landed
  - service wrapper truthfulness hardened

### Current truth about LLM / Grok
- LLM utility exists as repo-owned infrastructure in `ifa-business-layer`
- Grok aliases are live-validated:
  - `grok41_expert`
  - `grok41_thinking`
- Data platform FSJ LLM assist currently defaults to:
  - `grok41_thinking`
- LLM assist is already wired into:
  - `early_main_producer.py`
  - `mid_main_producer.py`
  - `late_main_producer.py`
- Current LLM role is **bounded assist**, not primary unconstrained truth generation

### Not yet fully closed
- SLA-grade end-to-end proof for all required report artifacts by slot
- Fully productionized standalone support-report path for all required outputs
- Stable FSJ query/service façade for downstream consumers
- Unified operator control-plane view for report production
- Full LLM/Grok governance and fallback policy
- Test/live DB isolation hardening

---

## 2. Design Principles

1. **Evidence-first**: no report statement should outrun evidence boundary.
2. **Deterministic core**: LLM may assist; it may not define hard system truth.
3. **Operator visibility**: every slot, artifact, hold, fallback, and rerun must be explainable.
4. **Replayability**: rerun / supersede / compare must be first-class.
5. **Graceful degradation**: partial > stuck; review-only > false-ready.
6. **Bounded LLM**: provider failures, timeouts, and drift must not collapse the system.
7. **Version discipline**: active/superseded/withdrawn semantics must remain coherent end-to-end.

---

# P0 — Core Production Closure

## Goal
Make the required business chain actually produce the required outputs on time, with real artifacts and truthful gating.

## Current Status
**Materially closed for the current roadmap scope.**  
Core slot-by-slot production closure is now evidenced for the 2026-04-23 acceptance slice and normalized in:
- `docs/FSJ_P0_1_P0_2_P0_3_CLOSEOUT_2026-04-24.md`
- `docs/FSJ_P0_4_FINAL_CLOSEOUT_2026-04-23.md`

## Completed / material progress already landed
- Support producer parity complete in business layer
- MAIN early/mid/late producer slices landed
- MAIN QA / packaging / dispatch / review / candidate comparison landed
- Runtime production lane stabilized enough to continue business work safely

## Task Queue

### P0-1. Early slot end-to-end closure (one-main / three-support)
**Status:** Materially closed for current roadmap scope — early support standalone proof is green across all three support domains, final green MAIN acceptance preserves `slot_status.early = ready`, and exact closure proof is documented in `docs/FSJ_P0_1_P0_2_P0_3_CLOSEOUT_2026-04-24.md`  
**Target:** prove stable generation of:
- MAIN early
- macro early
- commodities early
- ai_tech early

**Tasks**
- Verify each early artifact has a truthful build path
- Verify support summary handoff into MAIN
- Verify QA / package / review semantics for early outputs
- Verify artifact persistence + operator visibility
- Verify degradation rules when one support path is missing

**Parallelizable:** yes  
- lane A: MAIN early closure
- lane B: support early closure

---

### P0-2. Mid slot closure (MAIN only in phase-1)
**Status:** Materially closed for current roadmap scope — final green MAIN acceptance package proves `slot_status.mid = ready`, `mid=100`, and all-slot progression complete without missing-slot gaps; exact closure proof is documented in `docs/FSJ_P0_1_P0_2_P0_3_CLOSEOUT_2026-04-24.md`  
**Target:** prove stable generation of MAIN mid by SLA

**Tasks**
- Validate MAIN mid producer → FSJ → QA → package path
- Verify mid-specific boundary rules are enforced
- Verify no false close/final semantics leak into mid
- Verify operator-readable artifact and review state

**Parallelizable:** partly  
- lane A: producer/FSJ/query correctness
- lane B: QA/package/operator path

---

### P0-3. Late slot end-to-end closure (one-main / three-support)
**Status:** Materially closed for current roadmap scope — late support standalone convergence is green across all three support domains, final green MAIN acceptance is delivery-ready with strongest slot `late`, and exact closure proof is documented in `docs/FSJ_P0_1_P0_2_P0_3_CLOSEOUT_2026-04-24.md`  
**Target:** prove stable generation of:
- MAIN late
- macro late
- commodities late
- ai_tech late

**Tasks**
- Verify same-day stable/final evidence gating for late MAIN
- Verify support late outputs as standalone artifacts
- Verify support summary injection into MAIN remains concise and bounded
- Verify hold/review semantics when close package is provisional

**Parallelizable:** yes  
- lane A: MAIN late closure
- lane B: support late closure

---

### P0-4. SLA proof package
**Status:** Acceptance-closed for the 2026-04-23 evidenced package  
**Target:** operator-grade proof that required outputs can be produced within slot deadlines

**Tasks**
- Create repeatable SLA validation procedure
- Record per-slot generation times and artifacts
- Produce operator-readable pass/fail evidence package

**Parallelizable:** no, after slot closures are stable

---

### P0-5. Truthful send-readiness discipline
**Status:** Acceptance-closed on the 2026-04-23 evidenced package  
**Target:** no false-ready / false-sendable state

**Tasks**
- Ensure artifact existence checks precede send claims
- Ensure blocked/review-only/hold semantics are consistent
- Ensure package selected == package reviewed == package sent

**Parallelizable:** yes, but should converge with P1 delivery work

---

# P1 — Strongly Related Production Enablers

## Goal
Turn the core chain into a usable operator-facing production system instead of a collection of landed slices.

## Current Status
**Partially landed.**  
There is meaningful implementation here already, but not yet full system closure.

## Completed / material progress already landed
- MAIN delivery orchestration workflow landed
- canonical support summary aggregator landed
- operator review bundle landed
- candidate comparison artifact landed
- standalone FSJ support report publishing landed
- canonical operator batch command for support standalone publishing landed for early/late support paths:
  - `scripts/fsj_support_batch_publish.py`
  - persistence is built in (`persist-before-publish` is automatic, not a separate operator step)
  - runbook: `docs/FSJ_SUPPORT_STANDALONE_RUNBOOK.md`
- canonical operator command for late MAIN persistence + publish landed:
  - `scripts/fsj_main_late_publish.py`
  - persistence is built in (`persist-before-publish` is automatic inside the operator path)
  - runbook: `docs/FSJ_MAIN_LATE_RUNBOOK.md`

## Task Queue

### P1-1. Support standalone report production path
**Status:** Materially closed for current roadmap scope — support standalone early/late production is canonicalized through `scripts/fsj_support_batch_publish.py`, support artifacts remain independently reviewable/packageable/auditable, early/late three-domain standalone evidence is captured in the 2026-04-23 proof package, and exact closeout proof is documented in `docs/FSJ_P1_1_P1_2_CLOSEOUT_2026-04-24.md`  
**Target:** make support reports fully standalone, reviewable, packageable, auditable

**Delivered in current scope**
- [x] standalone support rendering/publish path for `macro`, `commodities`, `ai_tech`
- [x] early/late artifact generation parity at the canonical operator seam
- [x] QA / package / operator surfaces for support artifacts
- [x] support standalone outputs are proven as non-MAIN side effects
- [x] `scripts/fsj_support_batch_publish.py` remains the canonical persist+publish operator path

**Evidence anchors**
- `docs/FSJ_P1_1_P1_2_CLOSEOUT_2026-04-24.md`
- `docs/FSJ_SUPPORT_STANDALONE_RUNBOOK.md`
- `scripts/fsj_support_batch_publish.py`
- `tests/unit/test_fsj_support_batch_publish_script.py`
- `tests/unit/test_fsj_support_report_publish_script.py`
- `tests/unit/test_fsj_support_bundle_persist_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `docs/FSJ_SLA_PROOF_PACKAGE_2026-04-23.md`

**Deferred non-blocking expansions**
- [ ] broader support benchmarking and analytics belong to `P3-*`, not this seam
- [ ] richer operator automation/control-plane belongs to `P2-*`, not this seam

**Parallelizable:** yes by domain

---

### P1-2. MAIN/support artifact convergence
**Status:** Materially closed for current roadmap scope — MAIN now consumes only concise support summaries with explicit lineage/version mapping preserved through package/read surfaces, a direct non-inline boundary regression is in place, and exact closeout proof is documented in `docs/FSJ_P1_1_P1_2_CLOSEOUT_2026-04-24.md`  
**Target:** ensure MAIN consumes concise support summaries while support stays independently auditable

**Delivered in current scope**
- [x] support summary merge correctness on the canonical MAIN assembly/render path
- [x] support summaries never inline full support report bodies into MAIN
- [x] support summary provenance and version mapping remain explicit

**Evidence anchors**
- `docs/FSJ_P1_1_P1_2_CLOSEOUT_2026-04-24.md`
- `src/ifa_data_platform/fsj/report_assembly.py`
- `src/ifa_data_platform/fsj/report_rendering.py`
- `tests/unit/test_fsj_report_assembly.py`
- `tests/unit/test_fsj_report_rendering.py`
- `docs/FSJ_SLA_PROOF_PACKAGE_2026-04-23.md`
- `docs/FSJ_P0_4_ACCEPTANCE_LEDGER_2026-04-23.md`

**Deferred non-blocking expansions**
- [ ] deeper semantic summary-vs-body diff tooling can be added later without reopening this convergence seam
- [ ] broader replay/governance/control-plane work belongs to `P2-*`, not this seam

**Parallelizable:** yes

---

### P1-3. Stable query / consumption façade
**Status:** Not started as formal façade layer  
**Target:** stop downstream layers from reading raw FSJ graph ad hoc

**Tasks**
- introduce stable service/query interfaces
- provide active-bundle retrieval by slot/domain/topic
- provide support-summary retrieval interfaces
- provide operator review / send-ready package retrieval interfaces

**Parallelizable:** yes, after interface shape is fixed

---

### P1-4. Supersede / active-version discipline
**Status:** Partial foundation only  
**Target:** one coherent active truth per intended reporting surface

**Tasks**
- formalize active/superseded/withdrawn bundle behavior
- formalize package supersede path
- formalize send-manifest version linkage
- prevent version drift between review and send artifacts

**Parallelizable:** partly

---

### P1-5. Operator-facing production board
**Status:** Materially closed for current roadmap scope — the canonical operator board now provides one persisted fleet view across MAIN + support + MAIN history, with canonical operator-state semantics, artifact/version lineage, blocker + next-action visibility, slot/SLA context, and bounded rerun/failure-taxonomy projection; exact closeout proof is captured in `docs/FSJ_P1_5_OPERATOR_BOARD_CLOSEOUT_2026-04-24.md`  
**Target:** a single operator view for slot/domain/report state

**Delivered in current scope**
- [x] show planned/running/review/ready/held/sent states
- [x] show artifact lineage and active version
- [x] show blocking reason and next action
- [x] show slot SLA health

**Thin slices already landed**
- `P1-5a`: board state/data-source provenance (`board_state_source`, provenance summaries, next-action/blocker provenance)
- `P1-5b`: minimal operator board rows on the canonical board surface (`board_rows`) with semantic status, canonical lifecycle, next action, blocker visibility, and CLI parity across main/support/history subjects
- `P1-5c`: board row lineage/SLA enhancement on the canonical board surface (`board_rows`) with selected-artifact visibility, strongest-slot exposure, generated-at timing, dispatch state, bundle counts, missing-bundle visibility, and fleet aggregates for operator triage

**Evidence anchors**
- `docs/FSJ_P1_5_OPERATOR_BOARD_CLOSEOUT_2026-04-24.md`
- `src/ifa_data_platform/fsj/store.py`
- `scripts/fsj_operator_board.py`
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_store_delivery_surface_selectors.py`
- `tests/unit/test_fsj_store_json_serialization.py`

**Deferred non-blocking expansions**
- [ ] broader multi-user control-plane/productization belongs to `P2-*`, not this board seam
- [ ] deeper historical analytics/automation can extend the board later without reopening `P1-5`

**Parallelizable:** no, should reuse P1-3 + P1-4 outputs

---

# P2 — Productization Layer

## Goal
Elevate the engineering pipeline into an operator-grade product surface.

## Current Status
**Mostly not started as a unified layer.**  
Pieces exist, but the product/control-plane form does not yet exist.

## Task Queue

### P2-1. Unified report-production state machine
**Status:** Materially closed for current roadmap scope — canonical lifecycle vocabulary + projector landed in `FSJStore`, bounded invalid dispatch-transition detection is enforced on the canonical read path, operator-facing reuse is present across MAIN/support delivery-status plus operator-board surfaces, and exact closeout proof is captured in `docs/FSJ_P2_1_STATE_MACHINE_CLOSEOUT_2026-04-24.md`  
**Target:** define and enforce one canonical report production lifecycle

**Delivered in current scope**
- [x] define one explicit canonical lifecycle vocabulary covering planned / collecting / producing / qa_pending / review_ready / send_ready / sent / held / failed / superseded
- [x] map persisted artifact/workflow/package/dispatch truth into canonical lifecycle projection via `FSJStore.project_report_lifecycle_state(...)`
- [x] expose canonical semantic status/operator bucket via `FSJStore.project_report_state_vocabulary(...)`
- [x] enforce bounded invalid-state detection for dispatch receipts that appear on non-sendable workflow truth
- [x] reuse canonical lifecycle + transition-integrity truth on MAIN/support delivery-status and operator-board read surfaces

**Evidence anchors**
- `docs/FSJ_P2_1_STATE_MACHINE_CLOSEOUT_2026-04-24.md`
- `src/ifa_data_platform/fsj/store.py`
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `scripts/fsj_operator_board.py`
- `tests/unit/test_fsj_store_json_serialization.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_send_dispatch_failure_status_script.py`
- `tests/unit/test_fsj_support_dispatch_failure_status_script.py`

**Deferred non-blocking expansions**
- [ ] broader write-time transition enforcement across every future mutation path
- [ ] generalized workflow-engine/productization work beyond the current canonical read/projection seam
- [ ] richer promote/retry/override command surfaces outside the current roadmap-close scope

**Parallelizable:** no, foundational

---

### P2-2. Unified artifact registry / lineage index
**Status:** Materially closed for current roadmap scope — canonical artifact-family version-chain summary/query surface landed (`FSJStore.summarize_report_artifact_registry`, `scripts/fsj_artifact_lineage.py`), later board/read integrations made that lineage truth operator-visible on the canonical fleet surface, and exact closeout proof is captured in `docs/FSJ_P2_2_ARTIFACT_REGISTRY_CLOSEOUT_2026-04-24.md`  
**Target:** every report/package/review/send artifact must be queryable and comparable

**Delivered in current scope**
- [x] register artifact families and version chain on the canonical artifact persistence/read surface
- [x] link artifact → bundle graph → package/review/send manifest pointers on one lineage view
- [x] expose artifact lineage for operator and audit via dedicated lineage CLI plus board/read surfaces
- [x] support bounded “what did user actually receive?” queries from persisted dispatch/package truth

**Evidence anchors**
- `docs/FSJ_P2_2_ARTIFACT_REGISTRY_CLOSEOUT_2026-04-24.md`
- `src/ifa_data_platform/fsj/store.py`
- `scripts/fsj_artifact_lineage.py`
- `scripts/fsj_operator_board.py`
- `scripts/fsj_main_delivery_status.py`
- `scripts/fsj_support_delivery_status.py`
- `tests/unit/test_fsj_store_json_serialization.py`
- `tests/unit/test_fsj_artifact_lineage_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_store_delivery_surface_selectors.py`
- `tests/integration/test_fsj_phase1.py`

**Deferred non-blocking expansions**
- [ ] broader cross-family/global registry UX
- [ ] new registry-specific write paths or product surface beyond the current artifact persistence seam
- [ ] replay/rerun productization remains under `P2-3`, not this registry closeout

**Parallelizable:** yes after schema/interface design

---

### P2-3. Rerun / replay productization
**Status:** In progress — first operator compare slice landed on 2026-04-24 via canonical `rerun_compare_summary` projection surfaced symmetrically in MAIN/support delivery-status reads, making rerun-vs-active gaps explicit/auditable without introducing a parallel replay system; follow-on thin slice now normalizes a first-class rerun outcome label (`keep` / `supersede` / `replace` / `hold` / `unknown`) and projects it onto the canonical compare facade plus operator-board/read surfaces so operators can distinguish “better candidate supersedes current” from “replace current/selected truth with a different better candidate” without inventing a replay state machine  
**Target:** rerun becomes an operator action, not an engineering improvisation

**Tasks**
- rerun same slot with same inputs
- rerun same slot with refreshed supports
- compare rerun output vs active version
- declare supersede/replace/hold outcome
- keep replay evidence first-class

**Parallelizable:** yes

---

### P2-4. Production runbooks
**Status:** Materially closed for current roadmap scope — the bounded runbook set requested by this roadmap now exists across early-slot normal operations (`docs/FSJ_EARLY_SLOT_RUNBOOK.md`), mid-slot normal operations (`docs/FSJ_MID_SLOT_RUNBOOK.md`, `scripts/fsj_main_mid_publish.py`), late-slot normal operations (`docs/FSJ_LATE_SLOT_RUNBOOK.md`), LLM fallback (`docs/FSJ_LLM_FALLBACK_RUNBOOK.md`, `scripts/fsj_llm_fallback_status.py`), send/dispatch failure (`docs/FSJ_SEND_DISPATCH_FAILURE_RUNBOOK.md`, `scripts/fsj_send_dispatch_failure_status.py`), and data-source outage (`docs/FSJ_DATA_SOURCE_OUTAGE_RUNBOOK.md`, `scripts/fsj_source_health_status.py`); exact closeout proof is captured in `docs/FSJ_P2_4_RUNBOOK_CLOSEOUT_2026-04-24.md`  
**Target:** slot-specific incident handling and normal operations docs

**Delivered in current scope**
- [x] early-slot runbook
- [x] mid-slot runbook
- [x] late-slot runbook
- [x] LLM fallback runbook
- [x] data-source outage runbook
- [x] send/dispatch failure runbook

**Deferred non-blocking expansions**
- [ ] broader runbook/control-plane framework beyond the current FSJ operator seam
- [ ] downstream channel-receipt incident handling once receipt truth is actually persisted
- [ ] repo-wide incident-routing/productization outside the current roadmap-close boundary

**Parallelizable:** yes by area

---

### P2-5. Human-in-the-loop governance points
**Status:** In progress (`P2-5a` failure-taxonomy first slice landed on canonical operator board surface)  
**Target:** make manual review a designed feature rather than an ad hoc rescue path

**Tasks**
- define which failures auto-retry
- define which failures auto-degrade
- define which failures require hold/review
- define who/what can promote review-ready to send-ready

**Thin slices already landed**
- `P2-5a`: canonical operator board now projects a first bounded failure taxonomy from existing persisted truth, classifying a meaningful subset into `auto_retry` / `auto_degrade` / `hold_review` using dispatch receipts, send-readiness, lineage/source-health degrade posture, candidate-selection mismatch, and bundle/governance blockers; taxonomy is queryable per row and aggregated fleet-wide for operator triage
- `P2-5b`: canonical operator/review/status surfaces now project a first explicit promotion-authority seam from existing persisted truth. `promotion_authority` exposes whether the current package is actually approved to move from review-ready toward send-ready, the bounded authority source (`operator_go_no_go` + workflow + selected_handoff), the required operator action, and a compact provenance summary without introducing a new governance framework
- `P2-5c`: canonical artifact-lineage read surface now exposes the same bounded governance posture carried by board/status reads — `governance`, `promotion_authority`, compact `review_summary` provenance fields, and board-state source breadcrumbs — so package/review/send lineage inspection no longer loses operator-visible approval truth when pivoting away from board/status views

**Parallelizable:** no, policy-heavy

---

# P3 — Quality, Evaluation, and Operations Governance

## Goal
Measure whether the system is good, not just whether it ran.

## Current Status
**Early foundation only.**  
QA exists, but full quality governance does not.

## Task Queue

### P3-1. Multi-axis QA model
**Status:** Not fully designed  
**Target:** quality scoring beyond blocker count

**Tasks**
- separate structural completeness from semantic quality
- add evidence completeness scoring
- add support-main alignment checks
- add time-window legality checks
- add send-appropriateness decision layer

**Parallelizable:** yes after QA taxonomy is defined

---

### P3-2. Historical drift monitoring
**Status:** Materially closed for current roadmap scope — canonical drift monitor landed (`scripts/fsj_drift_monitor.py`), recent-drift streak projection landed on that surface, and the same drift truth is now embedded on the canonical operator board as per-scope summary lines plus a fleet digest  
**Target:** detect quality and behavior drift over time

**Delivered in current scope**
- [x] operator-visible historical trend summary over canonical operator-review surfaces (ready/review/hold, QA posture, lineage degraded/fallback/missing, selected-current mismatch)
- [x] recent consecutive-drift streak projection on the canonical drift monitor surface (hold/fallback/mismatch/QA attention streaks)
- [x] canonical operator-board embedding of the same drift truth (`drift_summary_lines`, `fleet_drift_digest`, `fleet_drift_digest_line`) so operators do not have to pivot to a separate tool to see current multi-day posture

**Deferred non-blocking expansions**
- [ ] slot-level quality trend dashboards
- [ ] support-summary missing rate
- [ ] artifact hold rate
- [ ] rerun frequency
- [ ] generation latency trend
- [ ] LLM assist success/fallback rate

**Parallelizable:** yes

---

### P3-3. Benchmark / golden-case suite
**Status:** Materially closed for current roadmap scope — canonical `early_main`, `mid_main`, `late_main`, `llm_resilience`, and `degraded_data` golden-case families now exist as dedicated regression entrypoints over the shared FSJ persistence/judgment/evidence harness  
**Target:** fixed benchmark cases for regression-proof evolution

**Tasks**
- [x] define one canonical early benchmark family and expose a dedicated regression entrypoint (`tests/integration/test_fsj_main_early_golden_case_family.py`) over the existing main-slot golden harness
- [x] define canonical early benchmark cases
- [x] define canonical mid benchmark family and expose a dedicated regression entrypoint (`tests/integration/test_fsj_main_mid_golden_case_family.py`) over the existing main-slot golden harness
- [x] define canonical late benchmark family and expose a dedicated regression entrypoint (`tests/integration/test_fsj_main_late_golden_case_family.py`) over the existing main-slot golden harness
- [x] define canonical late benchmark cases
- [x] define degraded-data benchmark cases
- [x] define LLM timeout/fallback benchmark cases

**Thin slices already landed**
- `P3-3a`: the first real benchmark seam now exists as the `early_main` family, with stable case descriptors (`describe_slot_golden_case(...)`), dedicated family selection (`EARLY_MAIN_GOLDEN_CASES`), and a focused integration regression surface that pins early-slot FSJ persistence/judgment/evidence expectations without broadening into a full benchmark matrix
- `P3-3b`: the next bounded benchmark seam now exists as the `mid_main` family, extending the same selector/descriptor pattern (`MID_MAIN_GOLDEN_CASES`) and adding a dedicated regression entrypoint that pins mid-slot persistence/judgment/evidence invariants without widening into a degraded/fallback matrix
- `P3-3c`: the next bounded benchmark seam now exists as the `late_main` family, extending the same selector/descriptor pattern (`LATE_MAIN_GOLDEN_CASES`) and adding a dedicated regression entrypoint that pins late-slot persistence/judgment/evidence invariants without widening into a full benchmark matrix
- `P3-3d`: extracted cross-slot `llm_resilience` and `degraded_data` families now reuse the same canonical case catalog (`LLM_RESILIENCE_GOLDEN_CASES`, `DEGRADED_DATA_GOLDEN_CASES`) with dedicated regression entrypoints so the remaining roadmap asks are closed without inventing a parallel benchmark subsystem

**Parallelizable:** yes by slot

---

### P3-4. Test/live isolation hardening
**Status:** Materially closed for current roadmap scope — FSJ pytest flows now fail fast unless an explicit non-live DB is set, publish paths also require an explicit non-live artifact root, default-`FSJStore()` helper/status/operator entrypoints are covered by regression tests, and the canonical FSJ live-touchpoint inventory is documented for audit  
**Target:** prevent tests from polluting live production truth

**Delivered in current scope**
- [x] isolate integration-test FSJ DB paths from live DB via pytest-time explicit non-live `DATABASE_URL` enforcement in `FSJStore`
- [x] isolate fixture/artifact writes from canonical artifact roots via explicit non-live artifact-root guardrails on publish flows
- [x] add destructive/live-write guardrails on default-store helper/status/operator entrypoints that would otherwise resolve canonical truth implicitly under pytest
- [x] review and inventory current FSJ tests/touchpoints touching canonical tables and artifact roots

**Evidence anchors**
- `src/ifa_data_platform/fsj/test_live_isolation.py`
- `src/ifa_data_platform/fsj/store.py`
- `docs/FSJ_P3_4A_LIVE_DB_TOUCHPOINT_INVENTORY_2026-04-24.md`
- `docs/FSJ_P3_4_TEST_LIVE_ISOLATION_CLOSEOUT_2026-04-24.md`
- `tests/unit/test_fsj_store_live_isolation.py`
- `tests/unit/test_fsj_report_dispatch.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_support_dispatch_failure_status_script.py`
- `tests/unit/test_fsj_report_rendering.py`

**Deferred non-blocking expansions**
- [ ] broaden the same isolation contract outside the current FSJ seam (archive/highfreq/lowfreq/midfreq and unrelated scripts)
- [ ] add stronger repo-wide destructive-test linting or CI policy beyond the current FSJ guard envelope

**Parallelizable:** yes

---

### P3-5. Source health gating
**Status:** Partially implicit  
**Target:** collector/source health should affect production decisions explicitly

**Tasks**
- declare required vs optional source families per slot
- define degrade rules by missing source family
- surface source-health state into operator review and QA
- prevent false-ready on missing critical source truth

**Parallelizable:** yes

---

# P4 — LLM / Grok Governance and Strategic Architecture

## Goal
Use LLMs as a production asset rather than an uncontrolled source of semantic drift.

## Current Status
**Partially landed / strategically incomplete.**  
Infra and wiring exist; governance and operational policy are incomplete.

## Current Progress
- business-layer LLM utility exists
- Grok aliases live-validated
- FSJ LLM assist wired into MAIN early/mid/late
- boundary enforcement exists in code for early/mid/late violations
- audit metadata exists for model alias/model id/application trace

## Task Queue

### P4-1. Formal LLM role policy
**Status:** Materially closed for current roadmap scope — canonical FSJ role policy is now explicitly defined in code (`build_fsj_role_policy`), persisted per bundle/review surface, projected with slot-specific boundary modes + deterministic-owner/forbidden-decision/override-precedence semantics, and exposed through publish/delivery/operator-board surfaces; exact closeout proof is captured in `docs/FSJ_P4_1_LLM_ROLE_POLICY_CLOSEOUT_2026-04-24.md`  
**Target:** formally define what LLM may and may not do

**Tasks**
- [x] define LLM-allowed fields
- [x] define LLM-forbidden decisions
- [x] define deterministic override precedence
- [x] define per-slot boundary invariants
- [x] persist policy version + slot boundary mapping onto operator-visible review surfaces
- [x] expose policy review through publish, delivery-status, dispatch, and operator-board seams

**Parallelizable:** no, foundational policy

**Delivered-in-scope evidence**
- canonical policy source: `src/ifa_data_platform/fsj/llm_assist.py`
- review-surface projection: `src/ifa_data_platform/fsj/report_orchestration.py`, `src/ifa_data_platform/fsj/store.py`
- operator-visible surfaces: `scripts/fsj_main_delivery_status.py`, `scripts/fsj_support_delivery_status.py`, `scripts/fsj_operator_board.py`, `src/ifa_data_platform/fsj/main_publish_cli.py`, `scripts/fsj_support_batch_publish.py`
- regression anchors: `tests/unit/test_fsj_main_early_publish_script.py`, `tests/unit/test_fsj_main_mid_publish_script.py`, `tests/unit/test_fsj_main_late_publish_script.py`, `tests/unit/test_fsj_support_batch_publish_script.py`, `tests/unit/test_fsj_report_dispatch.py`, `tests/unit/test_fsj_main_delivery_status_script.py`, `tests/unit/test_fsj_support_delivery_status_script.py`, `tests/unit/test_fsj_operator_board_script.py`, `tests/unit/test_fsj_store_json_serialization.py`

**Explicitly not claimed in this closeout**
- broader multi-provider strategy/cost governance under `P4-2` / `P4-4`
- adopted-vs-discarded field replay completeness under `P4-3`

---

### P4-2. Grok fallback and resilience policy
**Status:** Materially closed for current roadmap scope — canonical FSJ resilient clients now formalize the primary/fallback model chain, timeout/failure classification, deterministic degrade behavior, and operator-visible fallback tagging across early/mid/late; exact closeout proof is captured in `docs/FSJ_P4_2_FALLBACK_RESILIENCE_CLOSEOUT_2026-04-24.md`  
**Target:** provider/model failures degrade gracefully and predictably

**Tasks**
- [x] define primary model per slot/use case
- [x] define backup model or deterministic fallback path
- [x] define timeout and retry policy
- [x] define behavior on malformed output / boundary violation
- [x] define operator-visible fallback tagging

**Parallelizable:** yes after policy skeleton is fixed

**Delivered-in-scope evidence**
- canonical resilience implementation: `src/ifa_data_platform/fsj/llm_assist.py`
- review/operator projection: `src/ifa_data_platform/fsj/report_orchestration.py`, `src/ifa_data_platform/fsj/store.py`
- operator-visible surfaces: `scripts/fsj_main_delivery_status.py`, `scripts/fsj_support_delivery_status.py`, `scripts/fsj_operator_board.py`, `scripts/fsj_llm_fallback_status.py`, `docs/FSJ_LLM_FALLBACK_RUNBOOK.md`
- proof/eval seams: `scripts/prove_fsj_early_llm_fallback.py`, `scripts/prove_fsj_mid_llm_fallback.py`, `scripts/prove_fsj_late_llm_fallback.py`
- regression anchors: `tests/unit/test_fsj_early_llm_assist.py`, `tests/unit/test_fsj_main_mid_producer.py`, `tests/unit/test_fsj_late_llm_assist.py`, `tests/unit/test_fsj_llm_fallback_status_script.py`, `tests/unit/test_fsj_drift_monitor_script.py`, `tests/integration/test_fsj_main_llm_resilience_golden_case_family.py`

**Explicitly not claimed in this closeout**
- broader adopted-vs-discarded field replay/audit completeness under `P4-3`
- budget ceiling / ROI operating policy under `P4-4`

---

### P4-3. LLM audit and lineage tightening
**Status:** Partial  
**Target:** every LLM-assisted statement is explainable

**Tasks**
- persist prompt version / model alias / model id / invocation outcome
- record which fields were adopted vs discarded
- expose audit trail through operator surfaces
- support replay of bounded LLM assist under same prompt version

**Parallelizable:** yes

---

### P4-4. LLM cost / ROI governance
**Status:** Not started  
**Target:** control model usage based on production value

**Tasks**
- measure call frequency by slot
- measure fallback rate and failure rate
- classify where `thinking` is worth it vs overkill
- define cost ceiling / operational budget policy

**Parallelizable:** yes

---

### P4-5. Strategic architecture convergence
**Status:** Open  
**Target:** avoid long-term drift between business/data/report layers

**Tasks**
- formalize canonical contracts and versioning discipline
- define service façade boundaries
- define bundle/query/service ownership boundaries
- prevent hidden logic duplication across repos/layers

**Parallelizable:** partly

---

## 3. Suggested Execution Order

### Immediate recommended order
1. **P0** core slot closure
2. **P1** support/report/service closure around active production path
3. **P2** productization/control-plane layer
4. **P3** quality/governance hardening
5. **P4** LLM/Grok governance + strategic architecture convergence

### Practical parallelization guidance
- Run **MAIN path** and **support path** in parallel where contracts are already frozen
- Run **query/service façade** in parallel with **artifact lineage** once output shapes are stable
- Run **benchmark suite** in parallel with **LLM audit tightening**
- Avoid parallelizing policy-definition items before the canonical state machine / governance vocabulary is fixed

---

## 4. Recommended Next Parallel Work Package

### A-lane
- P0-1 Early slot closure
- P1-1 Support standalone report path
- P1-2 MAIN/support artifact convergence

Canonical operator runbook for the support standalone lane:
- `docs/FSJ_SUPPORT_STANDALONE_RUNBOOK.md`

### B-lane
- P0-2 Mid slot closure
- P1-3 Stable query / consumption façade
- P1-4 Supersede / active-version discipline

### Follow after A/B stabilize
- P0-3 Late slot closure
- P0-4 SLA proof package
- P2-1 Unified state machine
- P2-2 Artifact registry / lineage index
- P4-1 Formal LLM role policy
- P4-2 Grok fallback/resilience policy

---

## 5. Commit-Level Reference Snapshot

### ifa-business-layer
- `53c2bca` feat: add commodities support producer parity
- `df50ab4` feat: add ai-tech support producer
- `ff2504c` feat: add macro llm-assisted support producer
- `8bfdd72` docs: freeze A-share report production SLA and main queue
- `e1c437d` docs: add support-agent business buildout package
- `0468bae` docs: tighten FSJ grok usage boundary
- `4933863` docs: define FSJ persistence contract phase 1
- `bcad600` docs: define a-share early mid late data consumption contract
- `aea8d4f` docs: define a-share 2.0 phase-1 business contracts

### ifa-data-platform
- `3ab724d` Add MAIN candidate comparison artifact
- `5715a6f` feat: add main delivery package browsing index
- `4635bda` feat: polish fsj main report review surface
- `7a041bc` Add main report operator review bundle
- `c986b38` Add canonical support summary aggregator for main
- `9da2813` Harden MAIN delivery package selection handoff
- `c9298e9` Add MAIN morning delivery orchestration workflow
- `bb152af` Add standalone FSJ support report publishing
- `9cc2751` Add FSJ main delivery dispatch helper
- `b834bc2` Add FSJ main report slot evaluation harness
- `d941d84` feat(fsj): add commodities support producer slice
- `ecffbb6` Add FSJ main report delivery packaging
- `89e4567` Add FSJ main report QA gate

---

## 6. Definition of Done for This Roadmap

This roadmap is considered materially achieved only when:
- required slot outputs are generated within SLA
- artifacts are versioned, queryable, and operator-visible
- send readiness is truthful and reproducible
- rerun/supersede behavior is explicit
- LLM/Grok behavior is bounded, audited, and resilient
- quality is measured over time, not inferred from anecdote
- operator runbooks exist for normal and degraded cases
- test/live separation is strong enough to trust production truth

---

## 7. Short Operator Summary

We are no longer at the “idea / contract only” stage.  
We are at the “phase-1 slices landed, now close the production system” stage.

Top implementation order remains:
- **P0:** make required outputs truly close end-to-end
- **P1:** make those outputs operable, queryable, and version-coherent
- **P2:** turn the pipeline into an operator-facing product surface
- **P3:** harden quality/governance/test isolation
- **P4:** formalize and govern Grok/LLM as a bounded production subsystem
