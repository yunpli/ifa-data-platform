# Archive V2 Milestone 1 Implementation

_Date: 2026-04-18_0314_

## Scope
This batch implements Milestone 1 of the new Archive Layer definition.
This is the first real runtime/DB/code foundation of archive v2.

Milestone 1 target scope:
- profile-file loader / validator
- core run modes skeleton
- new archive DB run logging tables
- completeness skeleton
- daily-only execution skeleton
- new archive namespace/control foundation

This batch does **not** implement all archive families yet.
It implements the framework truthfully so Milestone 2 can begin directly.

---

## 1. Code/modules added or changed

### New modules
- `src/ifa_data_platform/archive_v2/profile.py`
- `src/ifa_data_platform/archive_v2/db.py`
- `src/ifa_data_platform/archive_v2/runner.py`

### New CLI/entry
- `scripts/archive_v2_run.py`

### New sample profile
- `profiles/archive_v2_daily_skeleton.json`

### New test
- `tests/integration/test_archive_v2_milestone1.py`

### Updated stable docs
- `docs/DEVELOPER_COLLECTION_CONTEXT.md`

---

## 2. What Milestone 1 actually implements

### A. Profile schema / loader / validator
Implemented in:
- `src/ifa_data_platform/archive_v2/profile.py`

Supported profile fields include:
- `profile_name`
- `mode`
- `include_daily`
- `include_60m`
- `include_15m`
- `include_1m`
- `include_business_families`
- `include_tradable_families`
- `include_signal_families`
- `broad_market`
- `family_groups`
- `start_date`
- `end_date`
- `backfill_days`
- `repair_incomplete`
- `delete_scope`
- `dry_run`
- `write_enabled`
- `notes`

Validation truthfully rejects invalid mode/date combinations.

### B. Core run modes skeleton
Implemented in:
- `src/ifa_data_platform/archive_v2/runner.py`

Run-mode framework exists for:
- `single_day`
- `date_range`
- `backfill`
- `delete`

Milestone 1 truth:
- mode dispatch is real
- unsupported family-level execution is not faked
- delete mode is skeleton-only and returns `partial` truthfully
- backfill mode dispatch exists as framework

### C. New archive DB control/logging tables
Implemented in:
- `src/ifa_data_platform/archive_v2/db.py`

Created tables:
- `ifa2.ifa_archive_runs`
- `ifa2.ifa_archive_run_items`
- `ifa2.ifa_archive_completeness`
- `ifa2.ifa_archive_profiles`
- `ifa2.ifa_archive_repair_queue`

These are created by runtime SQL bootstrap in code (`ensure_schema()`), consistent with the repo’s SQL-first pattern.

### D. Completeness skeleton
Implemented in:
- `ifa2.ifa_archive_completeness`

Tracked fields include:
- `business_date`
- `family_name`
- `frequency`
- `coverage_scope`
- `status`
- `source_mode`
- `last_run_id`
- `row_count`
- `retry_after`
- `last_error`

Milestone 1 writes truthful `incomplete` completeness rows for not-yet-implemented family groups.

### E. Daily-only execution skeleton
The current sample profile executes a real daily-only skeleton run.

What it does now:
- validates profile
- persists profile to DB
- creates run record
- creates run items for selected family groups
- writes completeness rows
- marks scaffolded/not-yet-implemented families as `incomplete`
- returns overall run status as `partial`

This is intentional and truthful.

### F. New archive namespace foundation
Milestone 1 establishes the new archive system in its own namespace/model via:
- `archive_v2` code modules
- new `ifa_archive_*` control/run/completeness tables

It does **not** yet create the final `ifa_archive_equity_daily`/etc. data tables.
That is deferred to Milestone 2 and beyond.

---

## 3. Sample profile created
Profile:
- `profiles/archive_v2_daily_skeleton.json`

Purpose:
- validate real profile-driven daily-only archive v2 skeleton execution
- broad family-group selection
- no fake write success

Important flags in sample profile:
- `mode = single_day`
- `include_daily = true`
- `include_60m/15m/1m = false`
- `broad_market = true`
- `write_enabled = false`

---

## 4. Direct validation commands run

### Direct profile-driven run
```bash
./.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_daily_skeleton.json
```

Output artifact:
- `artifacts/archive_v2_m1_run_2026-04-18_0310.json`

### DB evidence inspection
Inspected:
- `ifa2.ifa_archive_runs`
- `ifa2.ifa_archive_run_items`
- `ifa2.ifa_archive_completeness`
- `ifa2.ifa_archive_profiles`
- `ifa2.ifa_archive_repair_queue`

### Tests run
```bash
./.venv/bin/pytest -q tests/integration/test_archive_v2_milestone1.py
```

---

## 5. DB/runtime evidence summary

### Run result truth
The sample profile run returned:
- `ok = true`
- `status = partial`

This is correct because family execution is scaffolded, not fully implemented.

### DB table existence truth
After the run, all new control tables existed and were populated:
- `ifa_archive_runs` -> contains new run rows
- `ifa_archive_run_items` -> contains per-family items
- `ifa_archive_completeness` -> contains per-family/frequency completeness rows
- `ifa_archive_profiles` -> contains persisted profile JSON
- `ifa_archive_repair_queue` -> schema exists (skeleton stage)

### Run items truth
Per-family run items were written with:
- `status = incomplete`
- notes such as:
  - `family scaffold only; execution not implemented in Milestone 1`

### Completeness truth
Completeness rows were written with:
- `status = incomplete`
- `last_error = family not yet implemented in Milestone 1`

This proves the new archive layer does not fake success for unimplemented work.

---

## 6. What remains for Milestone 2
Milestone 1 is foundation only.
Milestone 2 must begin real family implementation, especially for broad daily/final tradable families such as:
- equity daily
- index daily
- ETF daily
- non-equity daily
- macro daily

That is when the first true `ifa_archive_*` data tables should be created and written.

Milestone 1 has intentionally stopped short of that so the framework is clean first.

---

## 7. Truthful judgment
### Is Milestone 1 now real?
**Yes.**

Why:
- profile-driven execution is real
- mode dispatch is real
- new DB archive control/run/completeness tables are real
- profile persistence is real
- daily-only execution skeleton is real
- unimplemented families are marked honestly as `incomplete`
- tests passed

### What Milestone 1 is not
It is **not**:
- full archive-family implementation
- new archive data-table rewrite completion
- old archive migration

### Bottom line
Milestone 1 is now a real, executable, DB-backed archive v2 foundation.
It is sufficient to begin Milestone 2 implementation directly, without needing another design-only round.
