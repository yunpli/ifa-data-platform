# Sector Performance Correction Batch

_Date: 2026-04-17_0030_

## Scope
This was a narrow correction batch for `sector_performance` only.

Goals:
1. fix midfreq source path
2. make runtime behavior explicit and production-safe
3. align retention semantics for `sector_performance`
4. validate real rows land in current/history

---

## 1. Old source path vs corrected source path

### Old active source path
Previously the active implementation used:
- `index_classify(market='SW')`
- then `index_daily(ts_code='<SW .SI code>', trade_date=...)`

Truth:
- `index_classify` had classification metadata rows
- but `index_daily` on SW `.SI` codes returned no usable performance rows in the current environment

### Corrected active source path
Now changed to:
- `ths_index(exchange='A', type='N')`
- then `ths_daily(ts_code='<.TI>', trade_date=...)`

This is now the active collection path for `sector_performance`.

### Implemented code change
Changed file:
- `src/ifa_data_platform/midfreq/adaptors/tushare.py`

What changed:
- `sector_performance` fetch is no longer a no-op placeholder
- `_fetch_sector_performance()` now uses the `.TI -> ths_daily` route
- mapped fields now come from THS daily rows:
  - `sector_code <- ts_code`
  - `sector_name <- ths_index.name`
  - `close <- ths_daily.close`
  - `pct_chg <- ths_daily.pct_change`
  - `turnover_rate <- ths_daily.turnover_rate`

---

## 2. Runtime behavior decision

Requested choice:
- Option A — parameterized / schedule-aware gating
- Option B — always-attempt harmless no-update

### Exact decision
**Option A — schedule-aware / post-close gated behavior**

### Why
This dataset is daily / post-close oriented.
The current daemon config already places `sector_performance` in:
- `post_close_final`

That is the most truthful and production-safe behavior for the current system because:
1. it matches actual source cadence semantics better than frequent always-attempt polling
2. it avoids unnecessary daytime calls against a daily dataset
3. it keeps the collection contract explicit
4. it fits the existing midfreq execution model without introducing ambiguous behavior

### Implementation truth
No new ad-hoc gating mechanism was needed because the current scheduler grouping already expresses the correct behavior:
- collect `sector_performance` in `post_close_final`
- do not reinterpret it as an intraday/frequent dataset

So for this system, the explicit decision is:
- **A, implemented via existing post-close final scheduling semantics**

---

## 3. Validation result: does `sector_performance_history` now get real rows?

### Focused validation execution
Executed through the real midfreq runner path:
- `MidfreqRunner().run('sector_performance')`

### Before
- `sector_performance_current = 0`
- `sector_performance_history = 0`

### Runtime result
- `status = succeeded`
- `records_processed = 394`
- `watermark = 20260416`

### After
- `sector_performance_current = 394`
- `sector_performance_history = 394`

### Representative persisted rows
```python
{'sector_code': '883300.TI', 'trade_date': 2026-04-16, 'sector_name': '沪深300样本股', 'close': 4736.6080, 'pct_chg': 1.0962, 'turnover_rate': 0.5813}
{'sector_code': '883301.TI', 'trade_date': 2026-04-16, 'sector_name': '上证50样本股', 'close': 2939.7600, 'pct_chg': 0.1888, 'turnover_rate': 0.2458}
{'sector_code': '883302.TI', 'trade_date': 2026-04-16, 'sector_name': '上证180成份股', 'close': 9994.6400, 'pct_chg': 0.5020, 'turnover_rate': 0.4389}
```

### Validation judgment
Yes.
`sector_performance_history` now gets real rows through the corrected source path.

---

## 4. Archive / retention alignment summary

### Question 1: Is `sector_performance` currently included in any archive/retention path?
Current practical retention model for this dataset is:
- **midfreq current -> history retention**

Evidence:
- `sector_performance_current`
- `sector_performance_history`
- history persistence mapping already exists in `midfreq/runner.py`

### Question 2: Is there a separate archive-worker source path for it?
In the currently inspected runtime/archive code, there is **no separate archive-worker source path** dedicated to `sector_performance` analogous to the intraday/archive tables.

### Question 3: What needed alignment?
The needed alignment was:
- correct the **midfreq collection source path**
- ensure retained historical rows are generated from the corrected path
- keep its runtime semantics explicitly daily/post-close

### Exact alignment result
After correction:
- midfreq collection uses `.TI -> ths_daily`
- current/history retention now receives real rows from that corrected path
- dataset semantics remain aligned with post-close daily collection

### Truthful conclusion on archive/retention
For this dataset, the relevant long-term preservation path is currently the **midfreq history retention path**, and that path is now aligned.
No additional archive redesign was necessary in this narrow batch.

---

## 5. Code / docs changed

### Code changed
- `src/ifa_data_platform/midfreq/adaptors/tushare.py`

### Docs added
- `docs/SECTOR_PERFORMANCE_CORRECTION_BATCH_2026-04-17_0030.md`

---

## 6. Truthful final judgment

### Closed in this batch
1. **Wrong source path corrected**
   - old `.SI -> index_daily` path is no longer the active collection path
   - new active path is `.TI -> ths_daily`

2. **Runtime behavior made explicit**
   - `sector_performance` should be treated as a **post-close daily dataset**
   - explicit choice: **Option A**

3. **Real row proof achieved**
   - `sector_performance_current` grew from `0 -> 394`
   - `sector_performance_history` grew from `0 -> 394`

4. **Retention alignment achieved**
   - current/history retention now preserves rows from the corrected source path

### What this means now
`sector_performance` should now be considered:
- **usable in the current system**
- but specifically as a **daily/post-close midfreq dataset**, not an intraday-style dataset

This batch resolved the previously wrong practical source-path choice and converted `sector_performance` from a zero-row placeholder into a real retained dataset.
