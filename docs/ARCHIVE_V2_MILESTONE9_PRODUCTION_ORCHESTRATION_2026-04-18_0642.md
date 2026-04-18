# Archive V2 Milestone 9 — Production Orchestration / Runtime Integration / Runbook Handoff

_Date: 2026-04-18 06:42 America/Los_Angeles_

## 1. Summary

Milestone 9 turns Archive V2 into the intended steady-state production operating path for daily/final archive truth.

This batch implemented:
- a concrete production orchestration model for Archive V2
- a safe runtime/daemon integration step via a dedicated `archive_v2` lane
- explicit separation between automatic nightly runs vs manual backfill vs operator repair
- a clearer legacy-archive supersession judgment
- a concrete operator production runbook / handoff

This batch did **not** broaden into unrelated runtime work and did **not** make `60m / 15m / 1m` the main scope.

---

## 2. Exact Milestone 9 scope implemented

### A. Production orchestration model
Archive V2 now has a real production operating model:

#### 1) Automatic nightly production path
- entrypoint: unified runtime lane `archive_v2`
- production CLI equivalent: `scripts/archive_v2_production_cli.py nightly`
- default profile name: `archive_v2_production_nightly_daily_final`
- purpose: steady-state nightly daily/final truth production

#### 2) Manual bounded backfill path
- entrypoint: `scripts/archive_v2_production_cli.py backfill`
- default profile name: `archive_v2_production_manual_backfill`
- purpose: bounded replay/backfill over retained-history-backed families

#### 3) Manual/operator repair path
- entrypoint: `scripts/archive_v2_operator_cli.py repair-batch ...`
- trigger source: `operator_repair_batch`
- purpose: targeted repair/coordination work, not normal nightly truth generation

This makes the production story explicit instead of ambiguous.

### B. Runtime / daemon integration step
Implemented a safe production integration step:
- added a dedicated unified runtime lane: `archive_v2`
- added production helper module: `src/ifa_data_platform/archive_v2/production.py`
- added production CLI wrapper: `scripts/archive_v2_production_cli.py`
- wired unified runtime to execute Archive V2 nightly production directly
- extended runtime CLI / daemon worker choices to include `archive_v2`

This is a safer step than mutating the legacy `archive` lane in place.

### C. Automatic vs manual/operator separation
The system now explicitly separates:

#### Automatic nightly production
- lane: `archive_v2`
- trigger sources:
  - `production_nightly_archive_v2`
  - `runtime_archive_v2_nightly`

#### Manual bounded backfill
- trigger source:
  - `manual_archive_v2_backfill`

#### Manual/operator repair
- trigger source:
  - `operator_repair_batch`

This means steady-state truth production is no longer mixed up with exceptional recovery work.

### D. Legacy archive-path supersession judgment
Safe supersession step in this batch:
- **Archive V2 is now the intended nightly production path**
- legacy `archive` lane remains present only as:
  - coexistence
  - manual fallback
  - legacy/manual-only operational path for now
- no destructive migration was performed
- no old tables/data were deleted

### E. Operator runbook / production handoff
Added stable operator doc:
- `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`

This runbook now covers:
- nightly production entrypoint
- manual backfill entrypoint
- manual repair entrypoint
- verification commands
- legacy-path truth
- current limitations

---

## 3. Code / tooling / schedule changes

### 3.1 `src/ifa_data_platform/archive_v2/production.py`
New production helper module providing:
- production business-date resolution
- nightly production profile construction
- manual backfill profile construction
- `run_nightly_production(...)`
- `run_manual_backfill(...)`

### 3.2 `scripts/archive_v2_production_cli.py`
New production wrapper CLI:
- `nightly`
- `backfill`
- `plan`

### 3.3 `src/ifa_data_platform/archive_v2/runner.py`
Added:
- `run_with_context(...)` so production paths can record explicit trigger sources/notes

### 3.4 `src/ifa_data_platform/runtime/unified_runtime.py`
Added:
- dedicated runtime lane handling for `archive_v2`
- unified runtime finalization now records Archive V2 nightly production summary into `unified_runtime_runs`

### 3.5 `src/ifa_data_platform/runtime/unified_daemon.py`
Updated:
- worker choices now include `archive_v2`
- default budget added for `archive_v2`

### 3.6 `scripts/runtime_manifest_cli.py`
Updated:
- CLI lane choices now include `archive_v2`

### 3.7 `src/ifa_data_platform/runtime/schedule_policy.py`
Production scheduling judgment now made explicit:
- `archive_v2 / trading_day` → **enabled** nightly production row
- legacy `archive / trading_day` → **disabled** as default nightly path
- non-trading day/weekend Archive V2 nightly rows are present but disabled
- manual backfill remains the intended catch-up path off schedule

### 3.8 Stable runbook
Added:
- `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`

### 3.9 Focused test
Added:
- `tests/integration/test_archive_v2_milestone9.py`

---

## 4. Production orchestration model now implemented

## 4.1 Automatic nightly Archive V2 production
Intended steady-state automatic path:
```bash
.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane archive_v2 --owner-type default --owner-id default
```

Equivalent production CLI wrapper:
```bash
.venv/bin/python scripts/archive_v2_production_cli.py nightly --business-date YYYY-MM-DD
```

Default nightly profile:
- `archive_v2_production_nightly_daily_final`

Default nightly scope:
- implemented daily/final Archive V2 families
- tradable daily
- business/event daily/final
- selected finalized highfreq daily families
- excludes known non-actionable placeholders from the production path

## 4.2 Manual bounded backfill
Manual bounded backfill path:
```bash
.venv/bin/python scripts/archive_v2_production_cli.py backfill --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

Truthful production judgment here:
- manual backfill defaults to retained-history-backed families
- this is safer operationally than trying to replay every direct-API tradable family through a generic range path
- targeted nightly holes should usually go to operator `repair-batch`

## 4.3 Manual/operator repair
Repair remains intentionally operator/manual:
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch ...
```

This keeps exceptional repair work separate from steady-state nightly truth production.

---

## 5. Runtime / daemon integration step implemented

### 5.1 Safe integration choice
This batch does **not** delete or destructively replace the old archive path.
Instead, it implements the safer production truth:
- `archive_v2` is the new intended nightly production lane
- legacy `archive` is retained as disabled-by-default coexistence/manual fallback

### 5.2 Why this is the safe step
Benefits:
- clear production path now exists
- unified runtime can run Archive V2 directly
- legacy path still exists for fallback while supersession settles
- no destructive migration needed yet

### 5.3 What the runtime now records
Unified runtime now writes explicit `archive_v2` lane runs into `unified_runtime_runs`, including summary fields such as:
- profile name
- profile path
- business date
- Archive V2 run id
- Archive V2 run status
- supersession truth (`legacy_archive_superseded_for_nightly=true`)

---

## 6. Automatic vs manual path separation

### Automatic
- lane: `archive_v2`
- purpose: nightly production truth
- trigger sources:
  - `production_nightly_archive_v2`
  - `runtime_archive_v2_nightly`

### Manual
- bounded replay/backfill:
  - `manual_archive_v2_backfill`
- operator repair:
  - `operator_repair_batch`

This gives operators a coherent story:
- nightly = normal truth generation
- backfill = bounded replay/catch-up
- repair = targeted recovery work

---

## 7. Legacy archive-path supersession judgment

### What is now superseded operationally
- legacy `archive` is superseded as the **default nightly production** path
- Archive V2 is now the intended nightly daily/final production path

### What still coexists for now
- legacy archive code/tables/workers remain in repo and DB
- legacy path can still serve as coexistence/manual fallback while cutover settles

### What was **not** done
- no deletion of old archive tables/data
- no destructive migration
- no claim that every legacy behavior is removed already

This is a controlled production supersession step, not a destructive cutover.

---

## 8. Operator runbook / production handoff

Stable runbook added:
- `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`

It now tells a future operator/new session:
- how nightly Archive V2 is run
- what profile is used
- how to check recent success
- how to inspect completeness/backlog
- how to run manual bounded backfill
- how to run manual repair batches
- how to interpret the operator surfaces
- what the current truthful limitations still are

---

## 9. Validation commands used

### 9.1 Compile / syntax
```bash
.venv/bin/python -m py_compile \
  src/ifa_data_platform/archive_v2/production.py \
  src/ifa_data_platform/archive_v2/runner.py \
  src/ifa_data_platform/runtime/unified_runtime.py \
  src/ifa_data_platform/runtime/unified_daemon.py \
  scripts/archive_v2_production_cli.py \
  scripts/runtime_manifest_cli.py \
  tests/integration/test_archive_v2_milestone9.py
```

### 9.2 Focused tests
```bash
.venv/bin/pytest tests/integration/test_archive_v2_milestone9.py -q
```

Observed result:
- `3 passed in 24.10s`

### 9.3 Direct production-path validation commands
```bash
.venv/bin/python scripts/archive_v2_production_cli.py nightly --business-date 2026-04-17
.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane archive_v2 --owner-type default --owner-id default
.venv/bin/python scripts/archive_v2_production_cli.py backfill --start-date 2026-04-15 --end-date 2026-04-17
.venv/bin/python scripts/archive_v2_operator_cli.py recent-runs --limit 10
.venv/bin/python scripts/runtime_manifest_cli.py run-status --lane archive_v2 --limit 10
.venv/bin/python scripts/archive_v2_production_cli.py plan --business-date 2026-04-17
```

---

## 10. DB / runtime evidence

### 10.1 Direct nightly production CLI evidence
Observed run:
- Archive V2 run id: `063bbe26-865f-41bb-96fd-e2389330d976`
- trigger source: `production_nightly_archive_v2`
- profile: `archive_v2_production_nightly_daily_final`
- status: `partial`
- notes: `dates=1 executed_targets=19 skipped_targets=0 target_policy=all`

Truthful note:
- `partial` is expected/acceptable evidence here because the production path must surface real incomplete families rather than fake completeness

### 10.2 Direct unified runtime nightly lane evidence
Observed runtime-backed nightly run:
- unified runtime id: `a10fb7b1-a493-4dbb-8200-a7472fad86d0`
- lane: `archive_v2`
- worker type: `archive_v2_production_worker`
- trigger mode: `manual_once`
- unified runtime status: `partial`
- linked Archive V2 run id in summary: `1d156872-8efe-40b5-945e-1281ec30b27c`
- supersession flag in summary: `legacy_archive_superseded_for_nightly = true`

This proves the runtime/daemon integration path is now real.

### 10.3 Manual bounded backfill evidence
Observed run:
- Archive V2 run id: `2bd8553b-b7d7-43ec-a52f-a01d05ca0e3b`
- trigger source: `manual_archive_v2_backfill`
- profile: `archive_v2_production_manual_backfill`
- status: `partial`
- notes: `dates=3 executed_targets=48 skipped_targets=0 target_policy=all`

### 10.4 Trigger-source separation evidence
Observed trigger-source rows in `ifa_archive_runs` now clearly separate:
- `production_nightly_archive_v2`
- `runtime_archive_v2_nightly`
- `manual_archive_v2_backfill`
- `operator_repair_batch`

This is the core production separation the batch needed.

### 10.5 Completeness slice evidence
Representative completeness rows:

For `2026-04-17`:
- `equity_daily` → `completed`, `5497`
- `index_daily` → `completed`, `8`
- `announcements_daily` → `completed`, `7666`
- `news_daily` → `completed`, `3223`
- `research_reports_daily` → `completed`, `71`
- `dragon_tiger_daily` → `completed`, `68`
- `sector_performance_daily` → `completed`, `394`

For runtime-resolved nightly date `2026-04-18`:
- `announcements_daily` → `completed`, `5036`
- `news_daily` → `completed`, `629`
- `equity_daily` → `incomplete`, `0`
- `index_daily` → `incomplete`, `0`
- `research_reports_daily` → `incomplete`, `0`
- `dragon_tiger_daily` → `incomplete`, `0`
- `highfreq_event_stream_daily` → `incomplete`, `0`
- `sector_performance_daily` → `incomplete`, `0`

Truthful production interpretation:
- the production path is working and recording truth
- current partial/incomplete outcomes are visible, not hidden
- operator surfaces remain the place to inspect/follow up with repair/backfill

---

## 11. Truthful judgment

### 11.1 What is now materially real
Milestone 9 makes Archive V2 the intended production operating path for daily/final archive truth:
- nightly production path is explicit
- runtime/daemon integration is explicit
- manual backfill is explicit
- manual repair path remains explicit
- legacy supersession is no longer ambiguous
- runbook/handoff is concrete

### 11.2 What is still not finished
This does **not** mean production cutover is “finished forever.”
Still unfinished / next-step scope includes:
- stronger steady-state scheduling/automation policy around non-trading dates and repair automation hooks
- deeper lease/worker orchestration for repair automation
- broader production hardening around family-specific nightly incompleteness handling
- eventual stronger legacy-archive retirement steps once coexistence confidence is sufficient

---

## 12. What remains for the next milestone

Most natural next milestone work:
1. production hardening around nightly partials/incompletes:
   - what should auto-retry
   - what should stay manual
   - what should escalate to operators
2. stronger repair automation hooks on top of the current manual/operator repair path
3. richer production analytics / SLA-style reporting for nightly Archive V2 health
4. clearer final retirement plan for the legacy archive path once confidence is high enough

---

## 13. Bottom line

Milestone 9 makes Archive V2 the **formal steady-state production path** for nightly daily/final archive truth:
- nightly production is explicit
- runtime integration is explicit
- manual backfill vs manual repair are clearly separated
- legacy archive supersession is operationally clear
- operators now have a real runbook for using and verifying the production path.
