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
**In progress / partially landed.**  
Core contracts and slices exist, but full slot-by-slot production closure is not yet fully proven.

## Completed / material progress already landed
- Support producer parity complete in business layer
- MAIN early/mid/late producer slices landed
- MAIN QA / packaging / dispatch / review / candidate comparison landed
- Runtime production lane stabilized enough to continue business work safely

## Task Queue

### P0-1. Early slot end-to-end closure (one-main / three-support)
**Status:** In progress  
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
**Status:** In progress  
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
**Status:** In progress  
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
**Status:** In progress  
**Target:** make support reports fully standalone, reviewable, packageable, auditable

**Tasks**
- finalize standalone support rendering for `macro`, `commodities`, `ai_tech`
- ensure early/late artifact generation parity
- add QA / package / operator surfaces for support artifacts
- confirm support standalone outputs are not MAIN-only side effects
- keep `scripts/fsj_support_batch_publish.py` as the canonical operator path so persistence + publish stay version-linked and auditable

**Parallelizable:** yes by domain

---

### P1-2. MAIN/support artifact convergence
**Status:** In progress  
**Target:** ensure MAIN consumes concise support summaries while support stays independently auditable

**Tasks**
- verify support summary merge correctness
- verify support summaries never inline full support report bodies into MAIN
- verify support summary provenance and version mapping

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
**Status:** In progress (`P1-5a` provenance slice + `P1-5b` minimal board surface slice + `P1-5c` lineage/SLA row enhancement slice landed)  
**Target:** a single operator view for slot/domain/report state

**Tasks**
- show planned/running/review/ready/held/sent states
- show artifact lineage and active version
- show blocking reason and next action
- show slot SLA health

**Thin slices already landed**
- `P1-5a`: board state/data-source provenance (`board_state_source`, provenance summaries, next-action/blocker provenance)
- `P1-5b`: minimal operator board rows on the canonical board surface (`board_rows`) with semantic status, canonical lifecycle, next action, blocker visibility, and CLI parity across main/support/history subjects
- `P1-5c`: board row lineage/SLA enhancement on the canonical board surface (`board_rows`) with selected-artifact visibility, strongest-slot exposure, generated-at timing, dispatch state, bundle counts, missing-bundle visibility, and fleet aggregates for operator triage

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
**Status:** In progress — `P2-1a` canonical state vocabulary first slice landed  
**Target:** define and enforce one canonical report production lifecycle

**Tasks**
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

**Thin slices already landed**
- `P2-1a`: explicit canonical lifecycle vocabulary projection now exists in `FSJStore` and is reused by operator review/readiness/board surfaces to normalize lifecycle → operator-visible semantic status/bucket mapping without introducing transition enforcement yet
- `P2-1c` first slice: explicit invalid dispatch-transition detection now exists in `FSJStore` for persisted `dispatch_attempted` / `dispatch_failed` / `dispatch_succeeded` receipts that appear on non-sendable workflow truth (`recommended_action!=send` or `ready_for_delivery=false`); these now project as operator-visible transition-integrity attention and force canonical lifecycle `failed` with a stable reason code instead of silently looking like normal forward progress

**Parallelizable:** no, foundational

---

### P2-2. Unified artifact registry / lineage index
**Status:** In progress — first bounded registry slice landed via canonical artifact-family version-chain summary/query surface (`FSJStore.summarize_report_artifact_registry`, `scripts/fsj_artifact_lineage.py`)  
**Target:** every report/package/review/send artifact must be queryable and comparable

**Tasks**
- register artifact families and version chain
- link artifact → bundle graph → support summaries → send manifest
- expose artifact lineage for operator and audit
- support “what did user actually receive?” queries

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
**Status:** In progress — early-slot normal-operations slice landed (`docs/FSJ_EARLY_SLOT_RUNBOOK.md`), mid-slot normal-operations slice landed (`docs/FSJ_MID_SLOT_RUNBOOK.md`, `scripts/fsj_main_mid_publish.py`), late-slot normal-operations slice landed (`docs/FSJ_LATE_SLOT_RUNBOOK.md`), thin LLM fallback slice landed (`docs/FSJ_LLM_FALLBACK_RUNBOOK.md`, `scripts/fsj_llm_fallback_status.py`), thin send/dispatch-failure slice landed (`docs/FSJ_SEND_DISPATCH_FAILURE_RUNBOOK.md`, `scripts/fsj_send_dispatch_failure_status.py`), and thin data-source outage slice landed (`docs/FSJ_DATA_SOURCE_OUTAGE_RUNBOOK.md`, `scripts/fsj_source_health_status.py`)  
**Target:** slot-specific incident handling and normal operations docs

**Tasks**
- early-slot runbook
- mid-slot runbook
- late-slot runbook
- LLM fallback runbook
- data-source outage runbook
- send/dispatch failure runbook

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
**Status:** In progress — thin production slice landed (`scripts/fsj_drift_monitor.py`), then expanded with recent-drift streak projection on the same operator surface  
**Target:** detect quality and behavior drift over time

**Tasks**
- [x] operator-visible historical trend summary over canonical operator-review surfaces (ready/review/hold, QA posture, lineage degraded/fallback/missing, selected-current mismatch)
- [x] recent consecutive-drift streak projection on the canonical drift monitor surface (hold/fallback/mismatch/QA attention streaks)
- [ ] slot-level quality trend dashboards
- [ ] support-summary missing rate
- [ ] artifact hold rate
- [ ] rerun frequency
- [ ] generation latency trend
- [ ] LLM assist success/fallback rate

**Parallelizable:** yes

---

### P3-3. Benchmark / golden-case suite
**Status:** In progress — bounded `early_main` and `mid_main` golden-case family selectors + dedicated regression entrypoints landed over existing FSJ persistence/judgment/evidence truth  
**Target:** fixed benchmark cases for regression-proof evolution

**Tasks**
- [x] define one canonical early benchmark family and expose a dedicated regression entrypoint (`tests/integration/test_fsj_main_early_golden_case_family.py`) over the existing main-slot golden harness
- [ ] define canonical early benchmark cases
- [x] define canonical mid benchmark family and expose a dedicated regression entrypoint (`tests/integration/test_fsj_main_mid_golden_case_family.py`) over the existing main-slot golden harness
- [ ] define canonical late benchmark cases
- [ ] define degraded-data benchmark cases
- [ ] define LLM timeout/fallback benchmark cases

**Thin slice already landed**
- `P3-3a`: the first real benchmark seam now exists as the `early_main` family, with stable case descriptors (`describe_slot_golden_case(...)`), dedicated family selection (`EARLY_MAIN_GOLDEN_CASES`), and a focused integration regression surface that pins early-slot FSJ persistence/judgment/evidence expectations without broadening into a full benchmark matrix
- `P3-3b`: the next bounded benchmark seam now exists as the `mid_main` family, extending the same selector/descriptor pattern (`MID_MAIN_GOLDEN_CASES`) and adding a dedicated regression entrypoint that pins mid-slot persistence/judgment/evidence invariants without widening into a degraded/fallback matrix

**Parallelizable:** yes by slot

---

### P3-4. Test/live isolation hardening
**Status:** Open risk  
**Target:** prevent tests from polluting live production truth

**Tasks**
- isolate integration test DB from live DB
- isolate fixture writes
- add destructive-test guardrails
- review current tests touching canonical tables

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
**Status:** Partial / implicit  
**Target:** formally define what LLM may and may not do

**Tasks**
- define LLM-allowed fields
- define LLM-forbidden decisions
- define deterministic override precedence
- define per-slot boundary invariants

**Parallelizable:** no, foundational policy

---

### P4-2. Grok fallback and resilience policy
**Status:** Not formalized  
**Target:** provider/model failures degrade gracefully and predictably

**Tasks**
- define primary model per slot/use case
- define backup model or deterministic fallback path
- define timeout and retry policy
- define behavior on malformed output / boundary violation
- define operator-visible fallback tagging

**Parallelizable:** yes after policy skeleton is fixed

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
