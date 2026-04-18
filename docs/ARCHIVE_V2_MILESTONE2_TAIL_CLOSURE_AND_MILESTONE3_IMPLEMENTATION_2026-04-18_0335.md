# Archive V2 Milestone 2 Tail Closure + Milestone 3 Implementation

_Date: 2026-04-18_0335_

## Scope
This batch does two things in one continuous implementation round:

1. closes the remaining Milestone 2 tail completely by implementing `index_daily`
2. moves directly into Milestone 3 for daily/final business families

This batch is real implementation, not design-only work.

---

## 1. Milestone 2 tail closure result
### `index_daily` is now truly implemented
Milestone 2 previously left one tail:
- `index_daily` table existed
- but real archive-v2 write logic had not been completed

This batch closes that tail.

### What was implemented for `index_daily`
- real archive-v2 writer for `index_daily`
- source-side final truth path used:
  - retained final history table `ifa2.index_daily_bar_history`
- target archive-v2 table:
  - `ifa2.ifa_archive_index_daily`
- run items now record:
  - `status = completed`
  - `rows_written > 0`
  - `tables_touched = ["ifa_archive_index_daily"]`
- completeness now records:
  - `status = completed`
  - real `row_count`
  - no fake tail remains

### Tail-closure truth
Milestone 2 is now cleanly closed.
There is no remaining `index_daily` tail from Milestone 2.

---

## 2. Milestone 3 implementation summary
Milestone 3 target:
archive-v2 begins preserving daily finalized business/event truth in its own archive layer.

Implemented real archive-v2 business families in this batch:
- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `sector_performance_daily`

Together with the already-implemented tradable families, Archive V2 now writes real archive rows for:
- `equity_daily`
- `index_daily`
- `etf_daily`
- `non_equity_daily`
- `macro_daily`
- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `sector_performance_daily`

---

## 3. New archive-v2 data tables added in this round
New business-family archive-v2 data tables:
- `ifa_archive_announcements_daily`
- `ifa_archive_news_daily`
- `ifa_archive_research_reports_daily`
- `ifa_archive_investor_qa_daily`
- `ifa_archive_dragon_tiger_daily`
- `ifa_archive_limit_up_detail_daily`
- `ifa_archive_limit_up_down_status_daily`
- `ifa_archive_sector_performance_daily`

Also completed in this round:
- `ifa_archive_index_daily` real writer now active

---

## 4. Source-side/final truth paths used
### `index_daily`
- source-side final truth path:
  - `ifa2.index_daily_bar_history`
- archive target:
  - `ifa_archive_index_daily`

### `announcements_daily`
- source-side final truth path:
  - `ifa2.announcements_history`
- archive target:
  - `ifa_archive_announcements_daily`

### `news_daily`
- source-side final truth path:
  - `ifa2.news_history`
  - filtered by `date(datetime) = business_date`
- archive target:
  - `ifa_archive_news_daily`

### `research_reports_daily`
- source-side final truth path:
  - `ifa2.research_reports_history`
- archive target:
  - `ifa_archive_research_reports_daily`

### `investor_qa_daily`
- source-side final truth path:
  - `ifa2.investor_qa_history`
- archive target:
  - `ifa_archive_investor_qa_daily`

### `dragon_tiger_daily`
- source-side final truth path:
  - `ifa2.dragon_tiger_list_history`
- archive target:
  - `ifa_archive_dragon_tiger_daily`

### `limit_up_detail_daily`
- source-side final truth path:
  - `ifa2.limit_up_detail_history`
- archive target:
  - `ifa_archive_limit_up_detail_daily`

### `limit_up_down_status_daily`
- source-side final truth path:
  - `ifa2.limit_up_down_status_history`
- archive target:
  - `ifa_archive_limit_up_down_status_daily`

### `sector_performance_daily`
- source-side final truth path:
  - `ifa2.sector_performance_history`
- archive target:
  - `ifa_archive_sector_performance_daily`

This follows the accepted design principle:
Archive V2 is a separate finalized truth layer, even when collection/runtime already has retained-history tables.

---

## 5. Profile path used
Combined write-enabled validation profile:
- `profiles/archive_v2_daily_business_write_sample.json`

This profile includes both:
- tradable daily/final families
- business daily/final families

with:
- `write_enabled = true`
- `mode = single_day`
- `start_date = 2026-04-17`

---

## 6. Direct validation commands run
### Combined direct write run
```bash
./.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_daily_business_write_sample.json
```

Artifact:
- `artifacts/archive_v2_m3_run_2026-04-18_0331.json`

### Focused integration test
```bash
./.venv/bin/pytest -q tests/integration/test_archive_v2_milestone3.py
```

---

## 7. DB/runtime evidence summary
### A. Milestone 2 tail closure: `index_daily`
Observed for business date `2026-04-17`:
- `ifa_archive_index_daily` -> real rows written
- run item -> `completed`
- completeness -> `completed`

This proves `index_daily` is no longer scaffold-only.

### B. Milestone 3 business families now write real archive-v2 rows
Observed for business date `2026-04-17`:
- `ifa_archive_announcements_daily` -> populated
- `ifa_archive_news_daily` -> populated
- `ifa_archive_research_reports_daily` -> populated
- `ifa_archive_investor_qa_daily` -> populated
- `ifa_archive_dragon_tiger_daily` -> populated
- `ifa_archive_limit_up_detail_daily` -> populated
- `ifa_archive_limit_up_down_status_daily` -> populated
- `ifa_archive_sector_performance_daily` -> populated

### C. Run logging works
- `ifa_archive_runs` recorded the profile run
- `ifa_archive_run_items` recorded per-family results
- for this combined batch, implemented families recorded `completed`

### D. Completeness works
- `ifa_archive_completeness` updated with real per-family row counts
- implemented families recorded `completed`

### E. Honest incomplete behavior still exists
Families not implemented in this round remain capable of being marked `incomplete` truthfully.
For the selected validation profile in this batch, all selected families completed.

---

## 8. Test/validation result
Focused integration test:
- `tests/integration/test_archive_v2_milestone3.py`

Validation proves:
- `index_daily` is now truly implemented
- Milestone 3 business families write real archive-v2 rows
- run logging works
- completeness works
- the combined selected profile completed successfully

Result:
- passed

---

## 9. What remains for Milestone 4
Milestone 4 should focus on the next archive-v2 expansion area, likely including one or more of:
- higher-fidelity finalize/reconciliation rules for business families
- repair/retry queue execution semantics
- date-range/backfill productionization across implemented families
- intraday archive families (`60m` / `15m` / `1m`) when intentionally brought into scope
- stricter snapshot/finalize semantics for archive-v2 replay guarantees

Milestone 4 is no longer about basic daily archive-v2 existence.
That foundation is now real.

---

## 10. Truthful judgment
### Is Milestone 2 tail now fully closed?
**Yes.**

### Is Milestone 3 now real?
**Yes.**

Why:
- `index_daily` now writes real archive-v2 rows
- daily/final business families now write real archive-v2 rows
- run logging is real
- completeness updates are real
- validation passed
- no fake completion was used

### Bottom line
Archive V2 is now beyond control-table scaffolding and beyond tradable-only writes.
It now preserves both tradable daily truth and daily business/event finalized truth in its own archive layer.
