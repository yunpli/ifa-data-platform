# Documentation Backfill and Truth Alignment

_Date: 2026-04-16_0930_

## Scope
This batch aligns repository documentation with the current code/runtime/data truth after the recent development sequence around:
- highfreq lane build-out
- unified runtime daemon convergence
- schedule policy redesign
- Business Layer alignment clarification
- archive/backfill truth clarification
- acceptance/follow-up runtime validation

## Commit/history range reviewed
Recent history reviewed:
- `a77e625` — Complete highfreq milestone 4-6 operability and runtime audit
- `2d24c50` — Converge runtime daemon and redesign schedule policy
- `ef5d902` — Run unified acceptance cleanup and validation batch
- `d8b55ff` — Document full-chain alignment and follow-up run truth
- `7774b0d` — Seed tech focus lists and clarify archive backfill

Also inspected immediate preceding highfreq build commits:
- `1357a72`
- `61d03ca`
- `23736d2`
- `c3b819e`
- `53079ee`
- `508d4d1`

## Major areas already documented reasonably well
These were already present in timestamped docs and did not require full re-authoring:
- highfreq milestone-by-milestone implementation notes
- runtime architecture audit point-in-time notes
- unified acceptance run evidence doc
- full-chain/touched-table follow-up truth doc
- tech seeding + archive clarification point-in-time doc

However, most of that truth lived in timestamped audit docs rather than in durable core repository docs.

## Major documentation gaps/incompleteness found
### 1. Core architecture doc lagged behind runtime truth
`docs/architecture.md` still described only an early skeleton/control model and did not reflect:
- unified runtime daemon as the official long-running entry
- runtime schedule day types
- DB-backed trading-calendar gating
- Business Layer impact on execution scope
- demotion of lane-daemon long-running roles

### 2. Runbook lagged behind operational truth
`docs/runbook.md` still centered a demo-runtime skeleton and did not truthfully describe:
- official unified runtime commands
- manual worker execution through unified daemon
- runtime budgets
- limitations around summary-table materialization and BL scope incompleteness

### 3. Archive status doc was stale and misleading as official runtime guidance
`docs/ARCHIVE_RUNTIME_AND_DATA_STATUS.md` still treated archive as a separate official long-running runtime path and used outdated row-count/progress assumptions.
It did not reflect:
- archive now sitting under unified runtime
- current archive target breakdown
- uneven backfill progression
- zero-row follow-up archive runs as checkpoint-continuation truth

### 4. Developer collection context doc lagged on formal runtime and BL truth
`docs/DEVELOPER_COLLECTION_CONTEXT.md` still documented lane daemons as formal primary runtime chains and did not reflect:
- unified daemon as official runtime
- BL tech lists seeded later
- commodity/precious-metal focus-list absence
- current archive progress unevenness

## Docs updated in this batch
Updated durable repo docs:
- `docs/architecture.md`
- `docs/runbook.md`
- `docs/ARCHIVE_RUNTIME_AND_DATA_STATUS.md`
- `docs/DEVELOPER_COLLECTION_CONTEXT.md`

Created batch report:
- `docs/DOCUMENTATION_BACKFILL_AND_TRUTH_ALIGNMENT_2026-04-16_0930.md`

## Truth added/corrected
### In `docs/architecture.md`
Added/corrected:
- unified runtime daemon as official long-running entry
- central ownership of:
  - schedule loading
  - day-type policy
  - worker dispatch
  - unified run evidence
  - unified worker state
- day-type schedule truth:
  - trading_day
  - non_trading_weekday
  - saturday
  - sunday
- DB-backed market-calendar gating via `trade_cal_current`
- Business Layer influence on scope
- note that tech BL lists were later seeded, while commodity/precious-metal focus lists still do not exist

### In `docs/runbook.md`
Added/corrected:
- official runtime commands now point to `runtime.unified_daemon`
- manual worker execution examples for all four workers
- bounded validation option via `--dry-run-manifest-only`
- lane daemons no longer documented as equal official long-running alternatives
- current limitations updated to include:
  - summary-table materialization mismatch risk
  - BL incompleteness for some classes
  - archive/backfill unevenness
  - acceptance-run data not being final production baseline

### In `docs/ARCHIVE_RUNTIME_AND_DATA_STATUS.md`
Added/corrected:
- archive no longer presented as separate official long-running runtime model
- archive documented as a worker under unified runtime
- current archive target breakdown by category/frequency
- current backfill progression truth by category
- explicit statement that archive is unevenly advanced
- explicit statement that zero-row follow-up archive run can be truthful checkpoint continuation

### In `docs/DEVELOPER_COLLECTION_CONTEXT.md`
Added/corrected:
- unified runtime daemon as official runtime entry
- lane daemons recast as compatibility/manual wrappers
- accepted runtime budgets
- BL truth updated to include seeded tech lists
- explicit gaps retained:
  - no commodity key-focus/focus lists
  - no precious_metal key-focus/focus lists
  - no explicit archive index target coverage in current archive lists
- archive progress unevenness documented

## Final judgment on repository documentation completeness
### What is now in much better shape
The repository is now materially more understandable to a future engineer because the durable docs now reflect:
- the real runtime entry model
- the real worker relationship
- the real schedule/day-type model
- the real BL influence on execution scope
- the real archive/backfill truth
- the fact that some data/summary surfaces are still partial or mismatched

### What is still only partially covered / should be improved later
1. No single stable reference doc yet fully enumerates all runtime/control tables with exact schema roles.
2. Highfreq derived-signal semantics still live more in milestone docs than in one durable consolidated reference.
3. Midfreq/highfreq summary-table materialization behavior should eventually get a dedicated troubleshooting/data-contract doc.
4. Business Layer list taxonomy and seeding policy would benefit from a dedicated durable reference doc rather than only timestamped change records.

### Truthful overall assessment
Documentation is no longer badly behind code on the core operational model.
However, the repository is still best described as:
- **operationally understandable**,
- **much more maintainable than before**,
- but **not yet perfectly normalized into a final long-lived docs IA**.

The highest-risk truth gap — code/runtime having materially changed while core docs still described the old lane-daemon model — has now been corrected.
