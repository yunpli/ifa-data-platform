# Collection Layer Readiness Gap Closure Plan

> **Document status:** Historical/intermediate readiness-gap planning document. Retained for audit trail only; not the canonical current-state source of truth.
_Date: 2026-04-15_

## Document purpose

This document defines the **remaining readiness-gap closure phase** for the Data Platform collection layer.

This is **not** another Trailblazer main-line architecture phase.
This is **not** highfreq planning.
This is a **production-minded execution-scoping document** for the current collection layer reality, focused on:
- lowfreq
- midfreq
- archive

The objective is to close the most important remaining operational-readiness gaps so that the collection layer aligns with **Business Layer target reality as far as realistically possible in this phase**, before any highfreq phase begins.

This document is intended to be used as the **execution basis** for the next phase.
It is not a loose planning note.

---

# A. Scope and objective

## A1. In-scope
This phase covers readiness-gap closure for:
- **lowfreq**
- **midfreq**
- **archive**

Specifically, this phase must address:
- Business Layer target alignment
- runnable coverage truth
- missing implementation coverage
- daemon/runtime/worker operability gaps
- evidence-backed closure work
- acceptance-grade tests, DB/runtime evidence, profiling, and final packaging

## A2. Explicitly out of scope
The following are **not** part of this phase:
- **highfreq implementation**
- broad Trailblazer blueprint expansion
- unrelated architecture redesign
- speculative future collection lanes not required for lowfreq/midfreq/archive readiness closure

## A3. Phase objective
At the end of this phase, the collection layer should have a much tighter and more truthful alignment between:
1. what the Business Layer is currently targeting,
2. what the collection layer actually implements,
3. what is actually runnable and evidenced,
4. what remains honestly deferred until later.

This phase is complete only when lowfreq, midfreq, and archive each have:
- clear Business Layer alignment accounting,
- materially improved operational readiness,
- evidence-backed coverage claims,
- explicit unresolved gaps narrowed to a small, intentional deferred remainder.

## A4. Hard scoping rule for this phase
This document fixes the required closure scope for this phase.

That means this phase must explicitly lock:
- which archive frequencies are required now,
- which archive categories are required now,
- which lowfreq datasets must be proven now,
- which midfreq datasets must be proven now,
- which validations must be non-dry-run,
- which validations may remain dry-run in this phase,
- whether service-mode smoke is required now.

Anything not explicitly listed as required in this phase is treated as deferred.

---

# B. Business Layer alignment matrix

## B1. Business Layer target reality now

Current live Business Layer archive-target reality under `owner_type=default`, `owner_id=default` includes:
- `minute`
- `15min`
- `daily`

Categories currently present in default archive target lists:
- `stock`
- `macro`
- `futures`
- `commodity`
- `precious_metal`

Current live lowfreq/midfreq target reality is broader than the currently proven manual collection coverage and includes multi-category selector presence that must not be over-claimed as runnable coverage without evidence.

## B2. Alignment matrix

### Lowfreq

| Dimension | Business Layer target reality | Current implementation reality | Current runnable evidence | Current missing coverage |
|---|---|---|---|---|
| Category breadth | selector/manifest includes stock + macro + futures + commodity + precious_metal | lowfreq daemon, registry, groups, runner, DB state are implemented | manual unified proof now covers `trade_cal`, `stock_basic`, `index_basic`, `fund_basic_etf`, `sw_industry_mapping`, `news_basic` | no direct proved lowfreq execution yet for macro/futures/commodity/precious_metal collection-specific datasets in this phase |
| Frequency role | lowfreq business role is broad reference / slower-changing data support | real daemon groups `daily_light` + `weekly_deep` exist | one-shot proof widened to 6 datasets | current proof still narrower than configured/registered surface |
| Operator readiness | should support sustained operation with evidence | daemon + health/state + registry exist | yes, but not fully closed across all category claims | needs broader category-specific proof and possibly targeted execution path expansion |

### Midfreq

| Dimension | Business Layer target reality | Current implementation reality | Current runnable evidence | Current missing coverage |
|---|---|---|---|---|
| Category breadth | currently mostly stock-adjacent market/session datasets | daemon + registry + Tushare adaptor + summary/watchdog exist | manual unified proof now covers `equity_daily_bar`, `index_daily_bar`, `etf_daily_bar`, `northbound_flow`, `limit_up_down_status` | still dry-run weighted; not yet full non-dry-run operational proof |
| Dataset breadth | daemon config expects a wider post-close group | registry exists but some config-vs-registry mismatch historically appeared | widened proof now validates 5 datasets | remaining configured datasets still need truth-check or pruning/deferral |
| Environment dependency | should run cleanly under intended production env | currently depends on `TUSHARE_TOKEN` and correct Tushare API mapping | current proof is runnable after ETF endpoint + registry fixes | still needs explicit production expectation and stronger non-dry-run proof |

### Archive

| Dimension | Business Layer target reality | Current implementation reality | Current runnable evidence | Current missing coverage |
|---|---|---|---|---|
| Frequency | `minute`, `15min`, `daily` target lists exist now | current default archive runtime only runs 3 jobs | manual archive one-shot proves only current 3-job scope | no operational implementation yet for minute / 15min archive collection lanes |
| Category breadth | stock + macro + futures + commodity + precious_metal | current runtime jobs: `stock_daily`, `macro_history`, `futures_history` | stock/macro/futures are proven runnable | commodity / precious_metal not implemented as real archive collection jobs |
| Catch-up/backfill | Business Layer targets imply broader archive retention expectations | catch-up state machinery exists and was proven on a small case | yes: insertion / binding / checkpoint linkage / completion were proven | still lacks broader frequency/category implementation and heavier backfill evidence |
| Operability | should reflect Business Layer archive reality more fully | runtime/health/checkpoints are strongest among lanes | yes for current limited scope | implementation scope materially lags Business Layer target reality |

## B3. Core alignment conclusion

The current collection layer does **not yet align fully** with Business Layer target reality.

The biggest remaining alignment problem is **archive**:
- Business Layer asks for more frequencies and categories than the current archive runtime implements.

Lowfreq and midfreq also still have alignment gaps:
- selector/manifest and configured dataset surfaces still exceed what has been operationally proven.

## B4. Fixed phase-closure target matrix

### Archive — fixed target for this phase

#### Frequencies
- **Required in this phase**:
  - `daily`
  - `15min`
- **Explicitly deferred from this phase**:
  - `minute`

Reason:
- `daily` is already partially implemented and must be brought closer to Business Layer truth.
- `15min` is the next most important missing Business Layer archive frequency and must stop being selector-only.
- `minute` is larger-volume and should not be mixed into this phase if the goal is to close archive gaps before highfreq without exploding scope.

#### Categories
- **Required in this phase**:
  - `stock`
  - `macro`
  - `futures`
  - `commodity`
  - `precious_metal`
- **Explicitly deferred from this phase**:
  - any category not already present in current default Business Layer archive targets under `default/default`

#### Meaning of required
For a required frequency/category combination, this phase must either:
1. implement real runtime coverage and prove it with evidence, or
2. explicitly prove why it cannot be closed in this phase and mark it as a reviewed residual gap.

The phase cannot claim archive closure if `15min` remains completely selector-only.

### Lowfreq — fixed target for this phase

The phase must produce closure evidence for the following concrete lowfreq datasets:
- `trade_cal`
- `stock_basic`
- `index_basic`
- `fund_basic_etf`
- `sw_industry_mapping`
- `news_basic`

These are the **minimum mandatory lowfreq proof datasets** for this phase.

Additionally, the phase must attempt to extend proof into at least one broader non-equity-reference/business-support area beyond the above set **if such a dataset is truly runnable now**.
If that attempt fails or no such dataset is truly runnable, the report must say so explicitly.

### Midfreq — fixed target for this phase

The phase must produce closure evidence for the following concrete midfreq datasets:
- `equity_daily_bar`
- `index_daily_bar`
- `etf_daily_bar`
- `northbound_flow`
- `limit_up_down_status`

These are the **minimum mandatory midfreq proof datasets** for this phase.

The phase must also truth-check the following configured-but-not-yet-fully-proven set and either validate or explicitly defer each item:
- `margin_financing`
- `southbound_flow`
- `turnover_rate`
- `main_force_flow`
- `sector_performance`
- `dragon_tiger_list`
- `limit_up_detail`

---

# C. Remaining gap list

## C1. Gap: lowfreq category-proof gap
- **What**: lowfreq now proves several real datasets, but still does not prove collection coverage across the broader category set implied by manifest/business-layer presence.
- **Why it matters**: lowfreq cannot honestly be called fully ready while category coverage is inferred from selector presence rather than demonstrated execution.
- **Affects**: lowfreq
- **Phase status**: required in this phase

## C2. Gap: lowfreq proof-set vs configured-set mismatch
- **What**: daemon config/registry surface is materially broader than the currently evidenced manual/unified proof set.
- **Why it matters**: operators need truth on which datasets are actually stable/runnable now.
- **Affects**: lowfreq
- **Phase status**: required in this phase

## C3. Gap: midfreq still dry-run weighted
- **What**: current improved proof set is broader, but still dominated by dry-run execution evidence.
- **Why it matters**: dry-run evidence is useful but weaker than real persisted non-dry-run evidence for production readiness.
- **Affects**: midfreq
- **Phase status**: required in this phase

## C4. Gap: midfreq dataset-surface truthing
- **What**: configured/registered datasets must be reconciled against what is truly runnable and clean under current environment and adaptor behavior.
- **Why it matters**: false-positive dataset availability creates operator overconfidence.
- **Affects**: midfreq
- **Phase status**: required in this phase

## C5. Gap: midfreq credentialed operational expectation
- **What**: `TUSHARE_TOKEN` dependency must be codified as a real operational requirement, not an incidental note.
- **Why it matters**: clean reproducible operation depends on explicit environment requirements.
- **Affects**: midfreq
- **Phase status**: required in this phase

## C6. Gap: archive frequency gap vs Business Layer
- **What**: Business Layer asks for `minute`, `15min`, and `daily`; current archive runtime only runs 3 jobs and does not operationally implement `15min`.
- **Why it matters**: archive is materially under-aligned to Business Layer targets.
- **Affects**: archive
- **Phase status**: required in this phase for `15min`; `minute` explicitly deferred

## C7. Gap: archive category gap vs Business Layer
- **What**: `commodity` / `precious_metal` target categories exist in Business Layer archive lists but are not implemented as real archive collection jobs in current runtime.
- **Why it matters**: archive readiness is currently overstated if judged only by daemon/state machinery.
- **Affects**: archive
- **Phase status**: required in this phase

## C8. Gap: archive heavy backfill evidence gap
- **What**: current archive evidence includes no-op/low-work cycles and small catch-up proof, but not yet meaningful heavier backfill timing evidence for the broadened target reality.
- **Why it matters**: fast success cycles should not be mistaken for full historical backfill readiness.
- **Affects**: archive
- **Phase status**: required in this phase

## C9. Gap: cross-layer truthfulness gap
- **What**: lowfreq/midfreq/archive each still need a consistent distinction between selector presence, registered datasets, runnable datasets, and proven collected coverage.
- **Why it matters**: this is a production-system truthfulness issue.
- **Affects**: multiple layers
- **Phase status**: required in this phase

## C10. Gap: final evidence-packaging gap for readiness closure
- **What**: closure of this phase must end with one acceptance-grade evidence package specific to collection-layer readiness gaps.
- **Why it matters**: review cannot rely on scattered chat summaries.
- **Affects**: lowfreq / midfreq / archive
- **Phase status**: required in this phase

## C11. Deferred gap: highfreq
- **What**: highfreq is still absent operationally.
- **Why it matters**: important, but explicitly deferred.
- **Affects**: highfreq
- **Phase status**: deferred until after this phase is approved and completed

---

# D. Implementation work checklist

## D1. Lowfreq work
- [ ] inventory all enabled lowfreq datasets from DB registry
- [ ] map each enabled lowfreq dataset to a concrete business category / role
- [ ] execute and prove the mandatory lowfreq proof set:
  - `trade_cal`
  - `stock_basic`
  - `index_basic`
  - `fund_basic_etf`
  - `sw_industry_mapping`
  - `news_basic`
- [ ] classify each mandatory proof dataset as:
  - non-dry-run required
  - dry-run allowed
- [ ] **non-dry-run required in this phase**:
  - at least `trade_cal`
  - at least `stock_basic`
  if the environment/supporting adaptor path allows safe execution
- [ ] **dry-run allowed in this phase**:
  - `index_basic`
  - `fund_basic_etf`
  - `sw_industry_mapping`
  - `news_basic`
  unless non-dry-run execution is proven safe and practical
- [ ] attempt at least one additional broader lowfreq/business-support dataset outside the minimum set if truly runnable now
- [ ] add/update integration tests to assert widened lowfreq runnable proof set
- [ ] record DB/runtime evidence for widened lowfreq runs
- [ ] update report/runbook/evidence docs to separate:
  - registered dataset presence
  - manifest category presence
  - real executed coverage

## D2. Midfreq work
- [ ] inventory all enabled/configured midfreq datasets from DB registry and daemon config
- [ ] reconcile mismatches between daemon config and registry
- [ ] execute and prove the mandatory midfreq proof set:
  - `equity_daily_bar`
  - `index_daily_bar`
  - `etf_daily_bar`
  - `northbound_flow`
  - `limit_up_down_status`
- [ ] truth-check and classify the secondary configured set:
  - `margin_financing`
  - `southbound_flow`
  - `turnover_rate`
  - `main_force_flow`
  - `sector_performance`
  - `dragon_tiger_list`
  - `limit_up_detail`
- [ ] **non-dry-run required in this phase**:
  - at least one midfreq dataset that safely persists current/history evidence in the present environment
  - preferred order: `northbound_flow`, `limit_up_down_status`, `index_daily_bar`
- [ ] **dry-run allowed in this phase**:
  - `equity_daily_bar`
  - `etf_daily_bar`
  if safe non-dry-run persistence remains blocked by current adaptor/environment constraints
- [ ] fix any local runtime/adaptor/registry bugs surfaced by widened proof execution
- [ ] establish explicit `TUSHARE_TOKEN` production expectation in docs and runtime evidence
- [ ] add/update integration tests to assert widened midfreq runnable proof set
- [ ] record DB/runtime evidence for widened midfreq runs
- [ ] separate clearly:
  - registered dataset presence
  - runnable dataset reality
  - dry-run evidence
  - non-dry-run evidence

## D3. Archive work
- [ ] inventory Business Layer archive-target reality from live `focus_lists`, `focus_list_items`, `focus_list_rules`
- [ ] inventory current actual archive job implementation and current default windows/jobs
- [ ] build explicit mapping from Business Layer target frequency/category to current archive runtime coverage
- [ ] implement/archive-close the following **required frequency/category scope for this phase**:
  - `daily` + `stock`
  - `daily` + `macro`
  - `daily` + `futures`
  - `daily` + `commodity`
  - `daily` + `precious_metal`
  - `15min` + `stock`
  - `15min` + `macro`
  - `15min` + `futures`
  - `15min` + `commodity`
  - `15min` + `precious_metal`
- [ ] **explicitly not required in this phase**:
  - `minute` frequency implementation
- [ ] if a required combination cannot be fully implemented in this phase, the report must name that exact combination and explain the blocker/residual gap explicitly
- [ ] prove any new archive coverage with real manual runs
- [ ] distinguish no-op cycles from meaningful catch-up/backfill work
- [ ] capture at least one more meaningful archive timing/backfill example if scope expansion lands
- [ ] update archive status/query/reporting surfaces if needed for new scope

## D4. Runtime / daemon / worker tasks
- [ ] keep daemon/runtime truth consistent with actual coverage
- [ ] avoid inflating operator surfaces beyond what is truly runnable
- [ ] ensure widened proof paths persist run-state/audit cleanly
- [ ] ensure new scope remains inspectable via DB/runtime queries

## D5. Tests
- [ ] extend integration tests for widened lowfreq proof set
- [ ] extend integration tests for widened midfreq proof set
- [ ] add archive coverage tests if new archive jobs/scope are added
- [ ] keep test expectations aligned with real DB schema and live runtime semantics

## D6. Runtime evidence
- [ ] capture exact commands used
- [ ] capture exact dataset/job lists executed
- [ ] capture exact categories covered
- [ ] capture exact runtime status fields
- [ ] capture exact run IDs / checkpoint IDs / relevant archive status rows
- [ ] capture wall-clock timings

## D7. DB evidence
- [ ] `job_runs`
- [ ] `unified_runtime_runs`
- [ ] `target_manifest_snapshots`
- [ ] `archive_target_catchup`
- [ ] `archive_checkpoints`
- [ ] `archive_runs`
- [ ] any lowfreq/midfreq current/history tables touched by closure work

## D8. Profiling
- [ ] lowfreq widened proof-set timing
- [ ] midfreq widened proof-set timing
- [ ] archive widened scope timing (if archive scope changes land)
- [ ] distinguish low-work cycles from meaningful work

## D9. Service-mode / long-running validation
- [ ] lowfreq service-mode smoke is required in this phase
  - minimum validation: start one bounded loop cycle or one daemon `--once`/health/state round that proves service-mode dispatch path and state visibility
- [ ] midfreq service-mode smoke is required in this phase
  - minimum validation: daemon `--once` or bounded loop round plus health/watchdog surface check
- [ ] archive service-mode smoke is required in this phase
  - minimum validation: daemon `--once` or bounded loop round plus health/checkpoint/run-state visibility check
- [ ] if service-mode smoke is not executed for a lane, that lane cannot be called long-running-readiness closed in this phase

## D10. Docs / runbook updates
- [ ] update readiness-gap closure report
- [ ] update runtime runbook if operational expectations change
- [ ] update repro/smoke docs if environment requirements become more explicit
- [ ] update final evidence package after readiness closure is complete

## D11. Final evidence packaging
- [ ] one reviewable closure report for this phase
- [ ] exact commands / DB queries / runtime evidence
- [ ] strict final judgments for lowfreq / midfreq / archive
- [ ] explicit statement of what remains deferred to highfreq or later phases

---

# E. Acceptance criteria

## E1. Lowfreq acceptance criteria
Lowfreq is considered closed for this phase only if:
- the mandatory lowfreq proof set is executed and reported,
- at least the required non-dry-run subset is completed or an explicit blocker is recorded,
- service-mode smoke is executed,
- the report clearly shows which datasets are truly runnable now,
- the report clearly separates registered vs manifest vs executed coverage,
- the resulting readiness judgment is evidence-backed and no longer based on a single-dataset proof.

## E2. Midfreq acceptance criteria
Midfreq is considered closed for this phase only if:
- the mandatory midfreq proof set is executed and reported,
- at least one required non-dry-run midfreq dataset is completed or an explicit blocker is recorded,
- service-mode smoke is executed,
- any local runtime defects blocking truthful widened proof are fixed,
- the role of `TUSHARE_TOKEN` is explicitly documented as operational expectation,
- the report clearly states whether the path is still dry-run weighted or has moved beyond that.

## E3. Archive acceptance criteria
Archive is considered closed for this phase only if:
- Business Layer archive-target reality is explicitly mapped against current runtime reality,
- all required frequency/category combinations for this phase are either implemented and evidenced or explicitly named as residual gaps,
- service-mode smoke is executed,
- any remaining mismatch is clearly documented by frequency and category,
- archive timing evidence distinguishes low-work orchestration runs from meaningful catch-up/backfill work,
- the final judgment does not overstate archive readiness relative to Business Layer asks.

## E4. Cross-layer acceptance criteria
This phase is considered complete only if:
- lowfreq, midfreq, and archive all have explicit final readiness judgments,
- the judgments are backed by code/runtime/DB evidence,
- no claim depends only on selector presence or configured dataset names,
- deferred items are explicitly limited and cleanly handed off to later phases.

---

# F. Final review evidence required

The review package returned after implementation must include, at minimum:

## F1. One final reviewable Markdown report
The report must cover:
- Business Layer archive target reality vs actual archive implementation
- lowfreq closure results and readiness
- midfreq closure results and readiness
- archive closure results and readiness
- strict final judgments

## F2. Exact commands run
Include:
- runtime commands
- DB query commands
- profiling/timing commands
- any test commands

## F3. Exact DB queries used
Include the actual SQL used for:
- Business Layer archive-target inspection
- runtime run inspection
- archive checkpoint/catch-up/run inspection
- any lowfreq/midfreq persistence evidence

## F4. Exact implementation evidence
Include:
- code files changed
- tests added/updated
- DB evidence created
- runtime evidence created
- commit hashes

## F5. Strict final judgments required in the final review package
Must explicitly state:
- whether archive currently matches Business Layer targets or still not
- for archive, which exact required frequency/category combinations were closed and which were not
- whether lowfreq is closed or still partial
- which exact mandatory lowfreq datasets were proven non-dry-run vs dry-run
- whether midfreq is closed or still partial
- which exact mandatory midfreq datasets were proven non-dry-run vs dry-run
- whether service-mode smoke was completed for lowfreq / midfreq / archive
- what remains before highfreq phase can begin

---

# Final planning conclusion

This phase is **not** lowfreq/midfreq only.
It is a **three-lane readiness-gap closure phase** for:
- lowfreq
- midfreq
- archive

The most important scope correction is that **archive under-alignment to Business Layer targets is a real closure problem**, not a solved problem.

No further readiness-gap coding should begin until this tightened planning document is reviewed and accepted.
