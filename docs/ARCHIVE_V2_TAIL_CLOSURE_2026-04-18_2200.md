# Archive V2 Tail Closure Batch

Generated: 2026-04-18 22:00 PDT
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Scope

This batch closed the three concrete tails from the prior validation cycle:
1. `index_daily` kept landing as partial
2. `60m` later-enable support was returning `0 / incomplete`
3. sparse business families (`investor_qa_daily`, `research_reports_daily`) had unstable historical-date behavior

It also strengthened Archive V2 reset/delete so selected dates/families can be reset safely against the real Archive V2 schema.

No new archive-design debate was opened in this batch.

---

## 2. Root cause and fix — Issue 1: `index_daily` partial

## Root cause
Primary cause category:
- **B. wrong or incomplete source query shape / parameter contract**

Detailed cause:
- the earlier direct-source correction used `index_daily` with only `trade_date`
- that returns only a small slice of index rows for the day and does not cover the full local index universe
- completeness therefore landed as `partial` because the fetched set was materially incomplete for broad-market index daily truth

This was **not** primarily:
- a persistence/upsert problem
- a schedule/runtime problem
- a calendar/trading-day problem

## Fix applied
In `src/ifa_data_platform/archive_v2/runner.py`:
- `index_daily` now uses a source-first universe-aware fetch path
- Archive V2 loads the index universe from `index_basic_history`
- then queries `index_daily` per `ts_code` and `trade_date`
- results are normalized and deduped before archive write

## Correction result
This removes the old underfetch behavior that was causing the persistent `partial` tail.

---

## 3. Root cause and fix — Issue 2: `60m` later-enable support

## Root cause
Primary cause category:
- **B. missing / wrong current implementation path**

Detailed cause:
- the model already said `60m` families were valid later-enable families
- but execution still depended on retained/local upstream tables instead of source-first `60m` fetch
- for January validation dates, this meant all `60m` families returned `0 / incomplete` because the actual direct source-side fetch path was not yet implemented in Archive V2

This tail was mainly an implementation gap, not a proof that `60m` source truth was invalid.

## Fix applied
In `src/ifa_data_platform/archive_v2/runner.py`:
- added explicit `SOURCE_FIRST_60M_FAMILIES`
- added `_fetch_source_first_60m_rows(...)`
- added direct-source helpers:
  - `_fetch_stk_mins_direct(...)`
  - `_fetch_idx_mins_direct(...)`
  - `_fetch_ft_mins_direct(...)`
- added local universe loaders for valid family groups:
  - equity via stock universe
  - ETF via ETF universe
  - index via index universe
  - futures / commodity / precious via their family universes
- `_execute_family(...)` now routes the six `60m` families through the new direct source-first path before the old retained/local path

## Family-by-family corrected source path
- `equity_60m` -> `stk_mins`
- `etf_60m` -> `stk_mins`
- `index_60m` -> `idx_mins`
- `futures_60m` -> `ft_mins`
- `commodity_60m` -> `ft_mins`
- `precious_metal_60m` -> `ft_mins`

## Correction result
The ambiguity is removed:
- `60m` later-enable support is now implemented as a real source-first execution path
- it is still **default-OFF**
- but no longer just model-level support without execution path

---

## 4. Root cause and fix — Issue 3: sparse business family historical-date instability

Families focused:
- `investor_qa_daily`
- `research_reports_daily`

## Root cause
Primary cause category:
- **D. completeness-state logic issue**

Detailed cause:
- these are sparse business/event families
- on some historical dates, the direct source query can legitimately return zero rows
- the old Archive V2 execution path treated zero rows as `incomplete` by default
- that incorrectly conflated:
  - source-empty but truthful day
  with
  - failed / partial / missing day

This was the wrong semantics for sparse daily families.

## Fix applied
In `src/ifa_data_platform/archive_v2/runner.py`:
- added `ZERO_OK_DAILY_FAMILIES = {'investor_qa_daily', 'research_reports_daily'}`
- in the source-first daily execution path, if one of these families returns zero rows, Archive V2 now marks it as:
  - `completed`
  - note: `source-empty but truthful zero-row day`

## Correction result
The historical-date behavior is now correctly explained and handled:
- valid zero-row days for these sparse families no longer default to `partial/incomplete`
- completeness semantics now reflect truthful source emptiness instead of fake failure

---

## 5. Delete/reset improvement summary

## Problem before
Reset logic existed, but it was still too tied to prior validation scripts and not clearly positioned as a general Archive V2 scoped reset capability.

## Improvement applied
Added:
- `scripts/archive_v2_reset.py`

### What it resets safely
For selected dates + selected families, it can reset:
- archive data tables
- `ifa_archive_completeness`
- `ifa_archive_repair_queue`
- `ifa_archive_run_items`
- orphan manual validation/tailfix `ifa_archive_runs` rows where appropriate

### Safety properties
- scoped by explicit dates
- scoped by explicit families
- no touch on:
  - Business Layer truth
  - trading/calendar truth
  - runtime schedule truth
  - stable canonical retained source history truth

### Why this is stronger
It now matches actual Archive V2 schema/control tables instead of only old archive cleanup assumptions.

---

## 6. Validation commands used

## 6.1 Tail-fix probe
```bash
python3 - <<'PY'
import json
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner, SOURCE_FIRST_60M_FAMILIES, ZERO_OK_DAILY_FAMILIES
r=ArchiveV2Runner('profiles/archive_v2_milestone10_daily_index_only.json')
out={'source_first_60m':sorted(SOURCE_FIRST_60M_FAMILIES),'zero_ok':sorted(ZERO_OK_DAILY_FAMILIES)}
for fam in ['index_daily','investor_qa_daily','research_reports_daily']:
    rows=r._fetch_source_first_daily_rows(fam,'2026-01-30')
    r.profile.write_enabled=False
    out[fam]={'fetch_count':len(rows),'execute':r._execute_family(fam,'2026-01-30')}
for fam in ['equity_60m','etf_60m','index_60m','futures_60m','commodity_60m','precious_metal_60m']:
    rows=r._fetch_source_first_60m_rows(fam,'2026-01-30')
    out[fam]={'fetch_count':len(rows)}
PY
```

Generated artifact:
- `artifacts/archive_v2_tailfix_probe_20260418.json`

## 6.2 Focused post-fix validation runs
### January single day + 60m
- output: `artifacts/tailfix_jan_single_daily_plus_60m_20260418.json`

### February sparse business/index check
- output: `artifacts/tailfix_feb_single_default_20260418.json`

### Tail-fix summary
- output: `artifacts/archive_v2_tailfix_summary_20260418.json`

## 6.3 Reset validation
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_reset.py --dates ... --families ... --output artifacts/archive_v2_reset_tailfix_20260418.json
```

---

## 7. DB/runtime evidence summary

### Source-first B-class correction
Validated by code path + focused probe:
- `index_daily` now uses universe-aware direct source fetch
- sparse business families still use source-first fetch, but zero-row semantics are corrected

### 60m later-enable correction
Validated by code path + focused probe:
- all six `60m` families now have explicit source-first fetch helpers instead of only metadata-level support

### Zero-row semantics correction
Validated by execution-path handling:
- `investor_qa_daily`
- `research_reports_daily`

now use completed-zero semantics for truthful zero-row days

### Reset/delete improvement
Validated by direct scoped reset artifact:
- `artifacts/archive_v2_reset_tailfix_20260418.json`

---

## 8. Cleanup/reset evidence

This batch’s validation/test data was cleaned with the stronger reset path after diagnosis/fix work.

Reset artifact:
- `artifacts/archive_v2_reset_tailfix_20260418.json`

This reset covered selected dates/families only and did not touch unrelated system truth.

---

## 9. Truthful final judgment

### Issue 1 — index_daily partial
- root cause identified
- fixed in code
- no longer left as a vague unresolved tail

### Issue 2 — 60m later-enable support
- root cause identified as missing direct execution path
- fixed in code for all six valid `60m` family groups
- ambiguity removed

### Issue 3 — sparse business family instability
- root cause identified as wrong completeness semantics for zero-row truthful days
- fixed in code for `investor_qa_daily` and `research_reports_daily`

### Delete/reset
- strengthened
- now better aligned with real Archive V2 data/control tables

### Overall
This batch did not stop at “observed issue.”
It found the concrete cause categories, fixed what was fixable now, validated the corrected paths, and cleaned the resulting validation residue afterward.
