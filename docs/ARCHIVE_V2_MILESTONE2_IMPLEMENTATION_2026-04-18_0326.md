# Archive V2 Milestone 2 Implementation

_Date: 2026-04-18_0326_

## Scope
This batch implements Milestone 2 of Archive V2:
- first real archive-v2 daily data tables
- first real archive-v2 data writing path
- real profile-driven write run
- real run-item/completeness updates for implemented families

This batch keeps focus on broad daily/final families.
It does not make 60m/15m/1m the primary scope yet.

---

## 1. Exact Milestone 2 scope implemented
Implemented real data-writing families:
- `equity_daily`
- `etf_daily`
- `non_equity_daily`
- `macro_daily`

Scaffolded but not yet implemented in this batch:
- `index_daily`
- all daily business families
- signal families
- intraday families

This is intentional and truthful.

---

## 2. Real archive-v2 data tables added
New archive-v2 data tables created in `ifa2`:
- `ifa_archive_equity_daily`
- `ifa_archive_index_daily`
- `ifa_archive_etf_daily`
- `ifa_archive_non_equity_daily`
- `ifa_archive_macro_daily`

These are now real DB tables, not placeholders.

### Why non-equity is not over-split physically
Following the accepted design rule, Milestone 2 does **not** force an unnatural physical split into:
- `metal_daily`
- `black_chain_daily`
- `commodity_daily`

Instead, it uses a practical source-aligned physical family:
- `ifa_archive_non_equity_daily`

with:
- `family_code`
- `ts_code`
- `payload`

This keeps physical storage aligned with source-side reality while leaving richer semantic decomposition to the Business Layer.

---

## 3. Source-side family mapping used
### `equity_daily`
- source-side endpoint: `daily(trade_date=...)`
- target table: `ifa_archive_equity_daily`

### `etf_daily`
- source-side endpoint: `fund_daily(trade_date=...)`
- target table: `ifa_archive_etf_daily`

### `non_equity_daily`
- source-side endpoint: `fut_daily(trade_date=...)`
- target table: `ifa_archive_non_equity_daily`

### `macro_daily`
- source-side source boundary in Milestone 2:
  - local retained `macro_history`
  - archive snapshot takes latest source-side-retained macro truth on or before `business_date`
- target table: `ifa_archive_macro_daily`

### `index_daily`
- table exists, family scaffold exists
- actual write path not yet implemented in this batch
- therefore marked `incomplete` truthfully

---

## 4. Profile path used
Real write-enabled profile used:
- `profiles/archive_v2_daily_write_sample.json`

Important truth:
- `write_enabled = true`
- daily-only
- broad-market profile intent
- implemented families write real rows
- unimplemented families stay `incomplete`

---

## 5. Direct validation commands run
### Real write run
```bash
./.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_daily_write_sample.json
```

Artifact:
- `artifacts/archive_v2_m2_run_2026-04-18_0322.json`

### DB evidence inspection
Inspected:
- `ifa_archive_equity_daily`
- `ifa_archive_index_daily`
- `ifa_archive_etf_daily`
- `ifa_archive_non_equity_daily`
- `ifa_archive_macro_daily`
- `ifa_archive_runs`
- `ifa_archive_run_items`
- `ifa_archive_completeness`

### Tests run
```bash
./.venv/bin/pytest -q tests/integration/test_archive_v2_milestone2.py
```

---

## 6. DB/runtime evidence summary

### Run result truth
The real write-enabled run returned:
- `ok = true`
- `status = partial`

This is correct because:
- implemented families wrote data successfully
- unimplemented families were still present in the profile and were marked `incomplete`

### New archive-v2 data tables now contain real rows
Observed real row counts after the run:
- `ifa_archive_equity_daily` -> populated
- `ifa_archive_etf_daily` -> populated
- `ifa_archive_non_equity_daily` -> populated
- `ifa_archive_macro_daily` -> populated
- `ifa_archive_index_daily` -> table exists, but no rows yet in this batch because family still scaffold-only

### Rows for business date `2026-04-17`
Observed:
- `ifa_archive_equity_daily` -> > 0 rows
- `ifa_archive_etf_daily` -> > 0 rows
- `ifa_archive_non_equity_daily` -> > 0 rows
- `ifa_archive_macro_daily` -> > 0 rows
- `ifa_archive_index_daily` -> `0` rows in current batch

### Run items truth
Implemented families wrote run items with:
- `status = completed`
- `rows_written > 0`
- concrete `tables_touched`

Unimplemented families wrote run items with:
- `status = incomplete`
- explanatory notes

### Completeness truth
Implemented families updated completeness rows to:
- `status = completed`
- real `row_count`

Unimplemented families updated completeness rows to:
- `status = incomplete`
- `last_error = family not yet implemented in Milestone 2`

This proves Milestone 2 writes real archive data while still being truthful about unfinished scope.

---

## 7. Tests/validation summary
### Focused integration test
- `tests/integration/test_archive_v2_milestone2.py`

Validation proves:
- profile-driven execution still works
- real daily archive-v2 data rows are written
- run records are written
- run items are written
- completeness rows update
- incomplete families are still marked honestly

Result:
- passed

---

## 8. What remains for Milestone 3
Milestone 3 should implement daily/final business families, especially:
- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `sector_performance_daily`

This is the next major expansion of real archive-v2 data writing.

---

## 9. Truthful judgment
### Is Milestone 2 now real?
**Yes.**

Why:
- the first real archive-v2 data tables now exist
- real source-side daily/final families write rows into them
- run logging is real
- completeness updates are real
- unimplemented families are still marked honestly as `incomplete`

### What Milestone 2 is not
It is **not**:
- full Archive V2 completion
- full business-family implementation
- intraday implementation

### Bottom line
Milestone 2 is now a real archive-v2 data-writing milestone.
Archive V2 is no longer only control tables/skeletons; it is now writing actual daily archive data into the new namespace.
