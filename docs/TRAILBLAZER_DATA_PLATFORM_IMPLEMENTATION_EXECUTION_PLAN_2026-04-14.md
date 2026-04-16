# Trailblazer Implementation Execution Plan for iFA Data Platform

> **Document status:** Historical baseline execution-plan document. Superseded as a current-state source by later canonical current-state documents and retained only as historical planning context.
_Date: 2026-04-14_

## 1. Purpose of this document

This document converts the approved Trailblazer architecture baseline into an **execution-grade implementation plan**.

It is not another architecture discussion.
It is the document that should govern how implementation proceeds in a controlled, reviewable, testable, and auditable way.

This plan is designed to ensure that the eventual output is not a partially assembled refactor, but a platform upgrade that is:
- structured
- evidence-backed
- reviewable milestone by milestone
- directly runnable
- operable by another developer without tribal chat knowledge

This document does **not** start implementation.
It defines the implementation path that should be followed **after approval**.

---

## 2. Baseline assumptions

This execution plan assumes the architecture baseline in:
- `docs/TRAILBLAZER_DATA_PLATFORM_UPGRADE_PLAN_2026-04-14.md`

That baseline established the following approved directions:
- Business Layer becomes the upstream selector of collection targets
- Data Platform resolves Business Layer selector inputs into normalized execution manifests
- Lowfreq and midfreq separate daemon architectures are transitional, not final
- One lightweight unified runtime daemon plus explicit workers is the target shape
- Archive/backfill remains a distinct concern, even while sharing common infrastructure patterns
- Operability, reproducibility, and run-state auditability are first-class requirements

This execution plan derives directly from that baseline and does not reopen those design decisions.

---

## 3. Implementation strategy overview

### 3.1 Overall implementation philosophy

The implementation should proceed in **controlled layers**, not as an all-at-once rewrite.

The correct strategy is:
1. establish the selector and runtime contracts first
2. close schema/init parity gaps before building on top of them
3. introduce the unified daemon/worker control path without throwing away proven collection logic prematurely
4. migrate lowfreq and midfreq execution behind the new control model
5. integrate archive delta/catch-up handling after the control substrate is stable
6. only declare closure after reproducibility, operability, and evidence expectations are satisfied

### 3.2 Why this order is correct

This order minimizes risk because:
- target selection contract must be stable before worker migration begins
- runtime control model must exist before lowfreq/midfreq can be safely moved under it
- schema/init uncertainty must be resolved before audit/run-state work becomes trustworthy
- archive delta/catch-up logic depends on manifest and run-state foundations
- documentation and reproducibility must be developed alongside implementation, not postponed to the end

### 3.3 What is strictly sequential vs parallelizable

#### Strictly sequential work
The following must happen in sequence:
1. contract freeze and schema parity audit
2. target manifest implementation foundation
3. unified runtime daemon/worker control path
4. lowfreq migration into unified path
5. midfreq migration into unified path
6. archive delta/catch-up control integration
7. final reproducibility / operability closure

#### Work that may be partially parallelized
The following can run in parallel within a milestone, once prerequisites are met:
- documentation updates aligned to completed milestone outputs
- test writing aligned to implementation of the relevant modules
- profiling harness preparation
- runbook drafting
- repo hygiene work

#### Work that should not be parallelized prematurely
The following should not be split too early:
- lowfreq and midfreq migration before unified worker contract exists
- archive delta handling before manifest/version linkage exists
- final service-mode hardening before one-shot paths are proven

---

## 4. Implementation sequencing

This is the authoritative milestone sequence.

### Milestone 0 — Execution readiness and repo/schema parity
Objective:
- verify the repo and live DB are ready for controlled implementation
- close gaps that would otherwise invalidate later runtime work

### Milestone 1 — Business Layer selector and target manifest foundation
Objective:
- implement the Business Layer -> Data Platform contract as code and testable artifacts
- create the normalized target manifest layer

### Milestone 2 — Unified runtime daemon/worker control substrate
Objective:
- implement the real unified control path for daemon + worker execution and audit records
- without yet migrating all lanes fully

### Milestone 3 — Lowfreq migration into unified runtime path
Objective:
- make lowfreq runnable through the new unified control path
- preserve lowfreq data quality and observability

### Milestone 4 — Midfreq migration into unified runtime path
Objective:
- make midfreq runnable through the new unified control path
- retire duplicated orchestration where feasible

### Milestone 5 — Archive upgrade: manifest-driven targeting, delta detection, catch-up planning
Objective:
- connect archive target resolution to Business Layer archive selectors
- implement membership delta and catch-up planning under the approved policy

### Milestone 6 — Directly runnable closure: config, docs, reproducibility, profiling, sustained operability
Objective:
- make the upgraded system cleanly runnable, inspectable, reproducible, and handoff-ready

---

## 5. Milestone-by-milestone execution plan

## Milestone 0 — Execution readiness and repo/schema parity

### Objective
Create a clean, auditable starting point for implementation by confirming schema/code parity, initialization reality, and repo hygiene.

### Inputs / prerequisites
- approved Trailblazer architecture baseline
- current live DB access
- current repository state

### Exact scope
Included:
- audit code-referenced tables vs live `ifa2` tables
- classify tables as present / missing / stale / unclear
- identify Data Platform-owned schema/init gaps
- establish canonical implementation docs/entrypoints to avoid ambiguity
- confirm repo initialization expectations

Excluded:
- no runtime refactor yet
- no Business Layer changes
- no daemon implementation changes

### Outputs / deliverables
- schema/code parity audit result
- resolved list of implied-missing tables and disposition plan
- canonical initialization path draft
- repo audit note identifying canonical runtime entrypoints and transitional paths

### Dependencies
None. This is the true implementation starting point.

### What must NOT be changed yet
- no runtime execution paths
- no worker semantics
- no Business Layer table logic

### Required artifacts
- audit note or markdown file under `docs/`
- exact command transcript used for parity audit
- issue list of missing/stale tables
- explicit list of canonical vs transitional runtime modules

### Testing and validation
Must run:
- schema parity audit command/script
- migration status check
- DB table existence verification
- repo audit review

Manual validation:
- confirm current initialization path can at least be described clearly

### DB state that must be verified
- which runtime tables exist and are populated
- which code-implied tables do not exist
- whether `job_runs` / `midfreq_window_state` remain unused/stale

### Evidence required
- exact commands run
- DB query outputs
- table classification result
- file/module list with canonical/transitional classification

### Exit criteria
Milestone 0 is complete only when:
- schema/code parity issues are documented
- missing tables are explicitly dispositioned
- canonical entrypoints are identified
- there is no ambiguity about what implementation should build on next

### Risks / rollback / guardrails
Risks:
- building on missing or stale schema assumptions
- implementing on top of the wrong runtime substrate

Detection:
- parity audit reveals missing tables / dead paths

Rollback/containment:
- stop before Milestone 1 if parity and ownership questions remain open

Regression guardrail:
- do not add new runtime logic on top of unresolved schema ambiguity

---

## Milestone 1 — Business Layer selector and target manifest foundation

### Objective
Implement the Business Layer -> Data Platform read-only selector integration and normalized target manifest contract.

### Inputs / prerequisites
- Milestone 0 complete
- Business Layer live table family present and canonical owner scope established

### Exact scope
Included:
- selector reader(s) for Business Layer tables
- manifest resolution logic
- list-to-lane mapping logic
- dedupe rules for overlapping lists such as `focus` + `tech_focus`
- theme tag handling
- frequency/granularity mapping for archive target sets

Excluded:
- no unified daemon service-mode implementation yet
- no lowfreq/midfreq orchestration migration yet
- no archive catch-up execution yet

### Outputs / deliverables
- target-resolution module(s)
- manifest contract definition
- manifest dry-run path
- manifest tests
- contract documentation

### Dependencies
- schema/code parity known
- Business Layer schema understood as read-only input

### What must NOT be changed yet
- do not redesign Business Layer tables
- do not mutate Business Layer rows during runtime
- do not migrate lowfreq/midfreq daemons yet

### Required artifacts
- code modules for selector + manifest resolution
- tests for manifest resolution and lane mapping
- doc describing manifest fields and semantics
- sample manifest outputs for canonical list families

### Testing and validation
Tests to write/run:
- unit tests for `key_focus` mapping
- unit tests for `focus` mapping
- unit tests for `tech_key_focus` / `tech_focus` theme overlay handling
- unit tests for `archive_targets` frequency mapping
- dedupe tests for overlapping stock targets

Manual validation:
- one dry-run manifest generation against live Business Layer data
- inspect manifest rows for canonical owner `default/default`

One-shot commands that must succeed
Examples:
- dry-run manifest generation for runtime selector scope
- dry-run manifest generation for archive selector scope

### DB state that must be verified
- live `focus_lists`, `focus_list_items`, `focus_list_rules` are being read correctly
- manifest output aligns with actual selector inputs

### Evidence required
- exact commands run
- selector input query results
- manifest samples
- test output
- explicit mapping examples for:
  - `default_key_focus`
  - `default_focus`
  - `tech_key_focus`
  - `tech_focus`
  - `archive_targets` by frequency

### Exit criteria
Milestone 1 is complete only when:
- manifest contract is implemented and documented
- live Business Layer data resolves into deterministic manifests
- overlap handling is explicit and test-backed
- no runtime lane still depends on ambiguous ad hoc selector logic for the scoped proof path

### Risks / rollback / guardrails
Risks:
- leaking Business Layer semantics into Data Platform-owned logic incorrectly
- hidden mutation of Business Layer state
- poor dedupe causing target inflation

Detection:
- mismatched manifest vs live selector input
- duplicate target rows without controlled reason

Rollback/containment:
- keep selector integration behind explicit dry-run/manual command until verified

Regression guardrail:
- no worker migration begins until manifest contract is stable

---

## Milestone 2 — Unified runtime daemon/worker control substrate

### Objective
Build the real daemon/worker control substrate, run-state model, and audit linkage.

### Inputs / prerequisites
- Milestone 1 complete
- approved run-state/audit model

### Exact scope
Included:
- unified daemon entrypoint
- worker launch/supervision path
- worker contract input/output model
- run record creation/update flow
- daemon state handling
- manifest-version/hash linkage to runs
- timeout and retry classification

Excluded:
- no full lowfreq or midfreq migration yet
- no archive delta/catch-up logic yet

### Outputs / deliverables
- daemon module / entrypoint
- worker execution wrapper / launcher
- run/audit state artifacts
- run summary output path
- daemon/worker runbook draft

### Dependencies
- manifest contract exists
- schema authority plan for runtime state is clear

### What must NOT be changed yet
- do not rewrite all source-specific lowfreq/midfreq logic here
- do not retire old daemons yet unless explicit compatibility wrapper exists

### Required artifacts
- unified daemon code modules
- worker invocation contract modules
- migrations/init for runtime audit artifacts if needed
- tests for dispatch, timeout, and run-state lifecycle
- operator runbook draft

### Testing and validation
Tests to write/run:
- unit tests for daemon dispatch logic
- unit tests for worker contract serialization
- timeout tests
- retry classification tests
- run-state lifecycle tests

Manual validation:
- one dry-run daemon invocation with manifest resolution
- one manual worker invocation through the new control path

One-shot commands that must succeed:
- daemon one-shot dispatch in test/manual mode
- worker one-shot execution wrapper
- run-record query after execution

### DB state that must be verified
- run records are created and updated correctly
- daemon state reflects actual execution progress
- manifest linkage is visible per run

### Evidence required
- exact daemon/worker commands
- run record query outputs
- daemon state query outputs
- timeout test evidence
- sample logs with run IDs and manifest linkage

### Exit criteria
Milestone 2 is complete only when:
- one canonical daemon/worker control path exists
- run-state model is visible and coherent
- timeout/retry/status semantics are observable
- the new control path can launch a bounded worker round successfully

### Risks / rollback / guardrails
Risks:
- introducing a daemon that is too heavy
- unclear status lifecycle
- missing manifest linkage

Detection:
- runs exist without manifest reference
- ambiguous status outcomes
- daemon loop complexity expanding too early

Rollback/containment:
- keep old lane-specific runtime paths intact during substrate proving period

Regression guardrail:
- no service-mode production claims until one-shot control path is proven stable

---

## Milestone 3 — Lowfreq migration into unified runtime path

### Objective
Move lowfreq execution under the unified daemon/worker control path while preserving data correctness and observability.

### Inputs / prerequisites
- Milestone 2 complete
- lowfreq registry/runner patterns identified as reusable

### Exact scope
Included:
- lowfreq worker adapter
- lowfreq manifest-driven selector integration
- lowfreq run-state integration
- one-shot lowfreq execution through unified path
- service-mode lowfreq dispatch proof

Excluded:
- do not migrate midfreq in this milestone
- do not integrate archive delta logic here

### Outputs / deliverables
- lowfreq worker adapter(s)
- lowfreq lane integration under unified control path
- updated lowfreq tests
- lowfreq runtime runbook draft
- lowfreq profiling baseline

### Dependencies
- unified daemon/worker substrate must exist
- selector/manifest contract must be stable

### What must NOT be changed yet
- do not attempt to solve all midfreq issues here
- do not redesign dataset-level lowfreq storage patterns unnecessarily

### Required artifacts
- lowfreq worker modules/adapters
- config updates for lowfreq lane under unified daemon
- tests for lowfreq one-shot and dispatch
- runbook updates
- profiling output for lowfreq one-shot

### Testing and validation
Tests to write/run:
- lowfreq one-shot integration tests through unified path
- lowfreq dispatch tests from daemon
- lowfreq timeout/retry tests where applicable

Manual validation:
- run one lowfreq one-shot through unified daemon/manual path
- confirm lowfreq result rows persist correctly

One-shot commands that must succeed:
- lowfreq one-shot through unified control path
- lowfreq dry-run/preview path if present

### DB state that must be verified
- expected lowfreq current/history/version/raw rows are written
- run records and summaries reflect the lowfreq execution
- daemon state shows correct dispatch/completion

### Evidence required
- exact commands run
- row-count or query evidence for affected lowfreq tables
- run record outputs
- lowfreq summary output
- profiling numbers for lowfreq one-shot
- relevant log references

### Exit criteria
Milestone 3 is complete only when:
- lowfreq can be executed successfully through the unified path in one-shot mode
- run records and logs are coherent
- lowfreq data persistence remains correct
- service-mode dispatch for lowfreq is at least smoke-validated

### Risks / rollback / guardrails
Risks:
- lowfreq data regression
- worker/daemon integration breaking stable runner logic

Detection:
- row-count mismatches
- lowfreq datasets no longer materializing expected outputs

Rollback/containment:
- keep compatibility path to old lowfreq execution during migration

Regression guardrail:
- lowfreq data correctness outranks elegance of refactor

---

## Milestone 4 — Midfreq migration into unified runtime path

### Objective
Move midfreq execution under the unified control model and retire redundant orchestration logic where practical.

### Inputs / prerequisites
- Milestone 3 complete
- unified control path proven on lowfreq

### Exact scope
Included:
- midfreq worker adapter
- midfreq manifest-driven target resolution path
- midfreq run-state integration
- one-shot midfreq execution through unified path
- service-mode midfreq dispatch proof

Excluded:
- do not merge archive logic into midfreq lane
- do not redesign archive scheduling here

### Outputs / deliverables
- midfreq worker adapter(s)
- unified midfreq execution path
- updated midfreq tests
- midfreq runtime runbook draft
- midfreq profiling baseline

### Dependencies
- unified runtime substrate proven on lowfreq
- target manifest path stable

### What must NOT be changed yet
- do not collapse archive into the same lane semantics
- do not overgeneralize before midfreq path is stable

### Required artifacts
- midfreq worker modules/adapters
- config updates for midfreq lane under unified daemon
- tests for midfreq one-shot and dispatch
- docs/runbook updates
- profiling output for midfreq one-shot

### Testing and validation
Tests to write/run:
- midfreq one-shot integration tests
- daemon dispatch smoke tests for midfreq windows
- timeout/status tests for midfreq worker path

Manual validation:
- run one midfreq one-shot through unified path
- verify expected current/history/state updates

One-shot commands that must succeed:
- midfreq one-shot through unified control path

### DB state that must be verified
- expected midfreq data tables are updated
- run records/summaries reflect actual execution
- daemon state shows intelligible lane behavior

### Evidence required
- exact commands run
- DB query outputs
- run summary output
- profiling numbers for midfreq one-shot
- log references

### Exit criteria
Milestone 4 is complete only when:
- midfreq can be executed successfully through the unified path in one-shot mode
- service-mode dispatch is smoke-validated
- duplicated midfreq orchestration is clearly transitional or retired
- observability is on par with lowfreq under the new control model

### Risks / rollback / guardrails
Risks:
- carrying lowfreq assumptions into midfreq incorrectly
- leaving two conflicting midfreq control paths active without clarity

Detection:
- divergence between old midfreq outputs and new path outputs
- ambiguous canonical entrypoint for midfreq

Rollback/containment:
- preserve explicit compatibility wrapper until unified path is accepted

Regression guardrail:
- no milestone close if canonical midfreq path is ambiguous

---

## Milestone 5 — Archive upgrade: manifest-driven targeting, delta detection, catch-up planning

### Objective
Connect archive execution to Business Layer archive selectors and implement the approved membership-delta and catch-up policy.

### Inputs / prerequisites
- Milestone 4 complete
- manifest linkage and run-state substrate already proven

### Exact scope
Included:
- archive selector integration from `archive_targets`
- frequency-specific archive target resolution
- archive manifest snapshot/diff support
- membership delta detection
- catch-up/backfill intent creation
- backlog priority policy implementation
- archive one-shot proof path

Excluded:
- no high-frequency logic
- no Business Layer redesign
- no retention-policy redesign beyond documented handling of removed targets

### Outputs / deliverables
- archive target snapshot/delta module(s)
- catch-up planner / backlog logic
- archive worker integration with manifest-driven targeting
- archive delta/catch-up tests
- archive delta handling documentation
- archive profiling outputs

### Dependencies
- unified run-state model
- manifest linkage
- lowfreq/midfreq already stable under unified control path

### What must NOT be changed yet
- do not change Business Layer archive list semantics
- do not let backlog scheduling starve current production work

### Required artifacts
- code modules for archive target diff and catch-up planning
- schema/init artifacts for catch-up/checkpoint state if needed
- tests for archive additions/removals/metadata/granularity changes
- archive runbook updates
- profiling outputs for backfill runs

### Testing and validation
Tests to write/run:
- archive one-shot execution tests
- checkpoint/resume tests
- membership-add tests
- metadata-change tests
- granularity-change tests
- backlog priority tests

Manual validation:
- add or simulate one new archive target
- verify delta detection
- verify catch-up intent creation
- run partial catch-up
- verify checkpoint advance and incomplete/complete state visibility

One-shot commands that must succeed:
- archive one-shot for a supported granularity
- archive catch-up one-shot for a newly-added target

### DB state that must be verified
- archive run records and summaries are written
- checkpoint state advances correctly
- catch-up/backlog state is visible
- newly-added targets enter catch-up flow without hidden manual steps

### Evidence required
- exact commands run
- before/after membership query results
- checkpoint/catch-up query outputs
- archive summary outputs
- profiling numbers for:
  - 1-day backfill
  - multi-day backfill
  - sample minute-level catch-up run

### Exit criteria
Milestone 5 is complete only when:
- archive targeting is Business Layer-driven for the approved scope
- membership delta detection is working and test-backed
- catch-up flow is visible, resumable, and auditable
- archive current work and backlog policy do not conflict operationally

### Risks / rollback / guardrails
Risks:
- backlog overwhelm
- newly-added targets causing uncontrolled historical work explosion
- archive starvation of current runtime work

Detection:
- catch-up queue growth without progress
- archive runs consuming windows needed by current work

Rollback/containment:
- apply explicit rate limits and shard sizes
- keep backlog processing policy bounded and observable

Regression guardrail:
- current archive freshness and production windows must be protected first

---

## Milestone 6 — Directly runnable closure: config, docs, reproducibility, profiling, sustained operability

### Objective
Close the implementation so the upgraded system is directly runnable, reproducible, inspectable, and handoff-ready.

### Inputs / prerequisites
- Milestones 0–5 complete

### Exact scope
Included:
- config convergence and cleanup
- cold-start setup path
- reproducible initialization path
- runbooks and troubleshooting docs
- testing/acceptance guide completion
- profiling evidence consolidation
- long-running operability review
- repo hygiene closure

Excluded:
- no new major architecture scope
- no new feature lane beyond approved Trailblazer target

### Outputs / deliverables
- finalized configuration model and examples
- cold-start setup guide
- daemon/worker runbook
- archive runbook
- troubleshooting guide
- testing/acceptance guide
- profiling report bundle
- readiness review evidence package

### Dependencies
- all prior milestones complete and evidence-backed

### What must NOT be changed yet
- no new feature scope introduced during closure
- no late architecture redesign under the banner of docs/hardening

### Required artifacts
- config docs and example config files
- cold-start guide
- troubleshooting guide
- testing/acceptance guide
- profiling outputs and summary notes
- clean repo state and documented canonical entrypoints

### Testing and validation
Tests to write/run:
- cold-start initialization test from clean clone
- end-to-end one-shot validation path
- service-mode smoke validation
- archive one-shot/catch-up validation
- documentation-following test by another developer if possible

Manual validation:
- clone/setup/run from docs only
- verify logs, run records, and states are inspectable
- verify service mode remains coherent across repeated cycles

One-shot commands that must succeed:
- one-shot lowfreq
- one-shot midfreq
- one-shot archive
- manifest dry-run
- health/status inspection commands

### DB state that must be verified
- run records visible for all core modes
- daemon state coherent
- archive checkpoints/catch-up state coherent
- no missing required schema artifacts for the approved scope

### Evidence required
- clean-clone command transcript
- migration transcript
- one-shot run transcripts for lowfreq/midfreq/archive
- run-state DB query outputs
- profiling report outputs
- docs file paths used for validation
- long-running operability review checklist result

### Exit criteria
Milestone 6 is complete only when:
- another developer can initialize and run the system from documentation
- one-shot lowfreq, one-shot midfreq, and one-shot archive all succeed through approved paths
- service mode works and is inspectable
- logs/run records/state are operationally intelligible
- docs are handoff-quality
- profiling evidence exists for the required core paths

### Risks / rollback / guardrails
Risks:
- system appears correct in engineering context but is not reproducible by another developer
- docs lag implementation
- service mode remains fragile despite one-shot success

Detection:
- clean-clone setup fails
- docs-driven validation fails
- service mode creates unclear state during repeated cycles

Rollback/containment:
- do not declare closure until docs-driven reproducibility is proven

Regression guardrail:
- operational closure requires evidence, not engineering confidence alone

---

## 6. Required artifacts by milestone (consolidated view)

This section provides a concise cross-milestone artifact checklist.

### Milestone 0
- parity audit note
- schema gap list
- canonical entrypoint inventory
- initialization draft

### Milestone 1
- selector reader module(s)
- manifest module(s)
- manifest tests
- manifest contract doc
- dry-run manifest output samples

### Milestone 2
- unified daemon entrypoint
- worker invocation layer
- runtime audit artifacts
- daemon/worker tests
- daemon/worker runbook draft

### Milestone 3
- lowfreq worker adapter(s)
- lowfreq integration tests
- lowfreq profiling baseline
- lowfreq runbook updates
- DB/run evidence bundle

### Milestone 4
- midfreq worker adapter(s)
- midfreq integration tests
- midfreq profiling baseline
- midfreq runbook updates
- DB/run evidence bundle

### Milestone 5
- archive delta detector
- archive catch-up planner
- archive delta/catch-up tests
- archive runbook updates
- checkpoint/catch-up evidence
- archive profiling outputs

### Milestone 6
- config docs
- cold-start setup guide
- troubleshooting guide
- testing/acceptance guide
- profiling summary package
- long-running operability review result
- clean repo closure evidence

---

## 7. Integrated testing plan by milestone

Testing is not an end-of-project activity. It is built into each milestone.

### Milestone 0 testing
- schema parity checks
- migration status checks
- DB existence/absence verification for referenced tables

### Milestone 1 testing
- selector unit tests
- manifest unit tests
- dedupe tests
- live dry-run manifest validation

### Milestone 2 testing
- daemon dispatch tests
- worker contract tests
- timeout tests
- run-state lifecycle tests

### Milestone 3 testing
- lowfreq one-shot integration tests
- lowfreq dispatch smoke tests
- lowfreq data persistence verification

### Milestone 4 testing
- midfreq one-shot integration tests
- midfreq dispatch smoke tests
- midfreq persistence verification

### Milestone 5 testing
- archive one-shot tests
- checkpoint/resume tests
- membership delta tests
- catch-up tests
- backlog priority tests

### Milestone 6 testing
- clean-clone reproducibility test
- docs-following initialization test
- final service-mode smoke validation
- final handoff/operability validation

---

## 8. Runtime / operability completion path

The implementation path should lead to a final state where:

### 8.1 Initialization is clean
- repo can be cloned cleanly
- dependencies can be installed from documented steps
- DB/schema can be initialized reproducibly

### 8.2 Another developer can configure and run it
- env vars and config files are documented
- one-shot validation commands work from docs only

### 8.3 One-shot runs work
- lowfreq one-shot works
- midfreq one-shot works
- archive one-shot works

### 8.4 Service mode works
- unified daemon can run in service mode
- window dispatch works
- state remains coherent over repeated loops

### 8.5 Archive/catch-up works
- archive target additions create catch-up work
- catch-up progresses incrementally
- completion state is visible

### 8.6 Logs/state/run records are inspectable
- run IDs are visible
- manifest linkage is visible
- daemon and worker status is queryable
- archive checkpoint state is intelligible

### 8.7 Sustained independent operation is credible
- system is not dependent on hidden tribal knowledge
- docs support restart, inspection, and troubleshooting

---

## 9. Documentation completion path

Documentation should be produced progressively, not at the very end.

### Milestone 0
- parity audit note
- canonical entrypoint note

### Milestone 1
- selector/manifest contract doc

### Milestone 2
- daemon/worker runbook draft
- runtime audit model note

### Milestone 3
- lowfreq execution notes integrated into runbook

### Milestone 4
- midfreq execution notes integrated into runbook

### Milestone 5
- archive delta/catch-up guide
- archive runbook expansion

### Milestone 6
- final system overview
- final cold-start guide
- final troubleshooting guide
- final testing/acceptance guide
- final config reference

The documentation completion path should ensure that by the time operational closure is claimed, the docs already exist rather than needing to be written afterward.

---

## 10. Performance / profiling execution plan

Profiling should be integrated into implementation rather than postponed until the end.

### 10.1 Milestone timing for profiling

#### Milestone 1
Measure:
- manifest resolution time
- selector query time

#### Milestone 2
Measure:
- daemon idle overhead
- worker spawn overhead
- run-record write overhead

#### Milestone 3
Measure:
- lowfreq one-shot total runtime
- fetch vs persistence split
- target-count vs runtime relationship

#### Milestone 4
Measure:
- midfreq one-shot total runtime
- fetch vs persistence split
- target-count vs runtime relationship

#### Milestone 5
Measure:
- archive 1-day backfill runtime
- archive multi-day backfill runtime
- minute/15min/daily catch-up throughput
- checkpoint overhead

#### Milestone 6
Consolidate profiling outputs into a final evidence package.

### 10.2 Required profiling evidence

At the appropriate milestones, evidence should include:
- exact commands run
- target counts processed
- wall-clock duration
- persistence timing if measured separately
- bottleneck interpretation
- notes on source throttling / DB cost / worker overhead

### 10.3 Profiling acceptance expectation

Profiling is not only for optimization.
It is required to prove the system is operationally understood.
A lane should not be considered mature if there is no measured understanding of its runtime characteristics.

---

## 11. Risks / rollback / guardrails during implementation

This section defines milestone-aware control discipline.

### 11.1 Milestone 0 risks
- parity audit misses a hidden schema dependency
- implementation begins on top of stale assumptions

Rollback/containment:
- pause before Milestone 1 until parity is explicit

### 11.2 Milestone 1 risks
- selector logic leaks Business Layer semantics incorrectly
- manifest contract is too vague or too coupled to one lane

Rollback/containment:
- keep manifest behind dry-run/manual validation until reviewed

### 11.3 Milestone 2 risks
- daemon becomes too heavy
- run-state model becomes inconsistent
- manifest linkage omitted in practice

Rollback/containment:
- stop before migrating lanes if the control substrate is not clean

### 11.4 Milestone 3 and 4 risks
- lowfreq or midfreq data regressions
- unclear coexistence between old and new control paths
- too much refactor pressure on proven runner logic

Rollback/containment:
- compatibility wrappers remain until unified path is accepted
- preserve working dataset-specific fetch/persist logic where possible

### 11.5 Milestone 5 risks
- archive backlog explosion
- membership-change catch-up starves current work
- checkpoint semantics become ambiguous

Rollback/containment:
- bounded shard sizes
- bounded backlog processing policy
- explicit operator-visible backlog state

### 11.6 Milestone 6 risks
- docs lag implementation
- reproducibility fails despite internal engineering success
- long-running service mode reveals instability not seen in one-shot tests

Rollback/containment:
- do not claim closure until clean-clone and sustained operability checks succeed

### 11.7 Protected non-regression areas
The following must be treated as protected areas throughout implementation:
- Business Layer tables remain read-only from Data Platform runtime
- live production-like data tables must not be casually rewritten during control-path work
- archive historical data must not be purged by membership-change handling logic
- schema/init authority must remain explicit and migration-backed

---

## 12. Final execution recommendation

The implementation should proceed milestone-by-milestone under explicit review gates.

The system should not be considered ready merely because code exists.
It should only be considered ready when:
- selector contract is stable
- unified control substrate is working
- lowfreq and midfreq run through the new path
- archive delta/catch-up policy is real and auditable
- initialization is reproducible
- documentation is handoff-quality
- profiling evidence exists
- long-running operability review passes

This is the implementation path most likely to produce a directly runnable, auditable, senior-approval-grade Data Platform upgrade rather than a partial refactor that still depends on implicit knowledge.
