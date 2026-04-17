# Tail Closure Before Final Full Test

_Date: 2026-04-16_2128_

## Scope
This batch closed the remaining pre-final-test tails in three areas:
1. highfreq derived-state zero tables
2. midfreq `sector_performance`
3. archive forward/backfill/retention tail classification

Artifacts / helpers:
- `scripts/tail_closure_inspect.py`
- `artifacts/tail_closure_inspect_2026-04-16_2120.json`

---

## 1. Highfreq derived-state source-truth findings

### Question
Why did these stay zero after the bounded unified-daemon highfreq run?
- `highfreq_sector_breadth_working`
- `highfreq_sector_heat_working`
- `highfreq_leader_candidate_working`
- `highfreq_intraday_signal_state_working`
- `highfreq_limit_event_stream_working`

### Raw-source truth at time of inspection
Observed upstream working data was **not zero**:
- `highfreq_stock_1m_working`: `6`
- `highfreq_index_1m_working`: `6`
- `highfreq_proxy_1m_working`: `1`
- `highfreq_futures_minute_working`: `40`
- `highfreq_event_stream_working`: `400`

This rules out explanation `(1) no accessible source at all`.

### Builder truth
The derived builder exists in:
- `src/ifa_data_platform/highfreq/derived_signals.py`

Its logic clearly inserts into:
- `highfreq_sector_breadth_working`
- `highfreq_sector_heat_working`
- `highfreq_leader_candidate_working`
- `highfreq_limit_event_stream_working`
- `highfreq_intraday_signal_state_working`

The builder consumes:
- stock 1m working rows
- proxy 1m working rows
- close-auction rows

### Real execution proof
Manual direct execution of the derived builder produced non-zero outputs immediately:
- `highfreq_sector_breadth_working`: `0 -> 1`
- `highfreq_sector_heat_working`: `0 -> 1`
- `highfreq_leader_candidate_working`: `0 -> 6`
- `highfreq_limit_event_stream_working`: `0 -> 1`
- `highfreq_intraday_signal_state_working`: `0 -> 1`

Returned proof payload:
- `sector_code='885728.TI'`
- `up_count=2`
- `down_count=3`
- `limit_up_count=1`
- `leader_candidate_count=6`
- `limit_event_count=1`

### Exact classification
The zero state after the bounded highfreq unified run is best classified as:
- **(2) source exists, builder logic works, but the bounded unified highfreq run path did not invoke the derived-state builder**

This is **not** primarily:
- no-source
- storage failure
- “current window generated no signal-worthy output”

There *was* enough raw input to generate derived outputs.
The missing link is runtime wiring / orchestration coverage inside the highfreq unified run path.

### Breadth / heat exact explanation
For breadth and heat specifically:
- there is enough current upstream material to compute a minimal breadth/heat snapshot
- but it is still **thin** (`1` proxy row, `6` stock rows), so this is not yet rich production-grade breadth breadth/heat coverage
- however, the reason the tables were zero after the bounded run was **not** absence of enough minimal source material
- the reason was that the derived builder was not triggered by that bounded unified run path

### Closure status
- **Closed as diagnosis**
- residual engineering task for the final/full path: ensure highfreq unified execution actually invokes derived-state build when raw working inputs are present

---

## 2. Midfreq `sector_performance` source-truth finding

### Question
Why is `sector_performance_history` still zero?

### Code-path truth
`sector_performance` is registered in midfreq runtime and mapped to persistence:
- fetch path exists in `src/ifa_data_platform/midfreq/adaptors/tushare.py`
- runner registration exists in `src/ifa_data_platform/midfreq/runner.py`
- current/history mapping exists in `src/ifa_data_platform/midfreq/runner.py`

So this is not “dataset forgotten by code”.

### Real source check
Direct call to the live accessible source path returned:
- `trade_date='20260416'`
- `row_count=0`

Meaning:
- the current environment’s accessible source call for `sector_performance` currently returns **no sector rows**

### Exact chain classification
Chain:
- source: current live call returns `0` rows
- mapping: code path exists
- runtime: dataset is registered and runnable
- storage: history table exists but receives nothing
- result: `sector_performance_history` stays `0`

### Exact classification
This is best classified as:
- **(3) source limitation / source-empty result in the current environment**

It is **not** currently best explained as:
- missing history mapping
- storage write failure
- dataset-registration failure

### Closure status
- **Closed as diagnosis**
- residual is source-side availability/coverage, not a newly discovered persistence bug

---

## 3. Archive forward-only clarification

### 1m / 15m truth
Current archive truth remains:
- `1m` / `15m` archive lanes are effectively **forward-only accumulation lanes** in current behavior
- recent bounded reruns produced `0` rows because there were **no fresh eligible forward slices** in the tested window

Evidence from recent archive jobs:
- `stock_minute_archive`: `records_processed=0`
- `futures_minute_archive`: `records_processed=0`
- `commodity_minute_archive`: `records_processed=0`
- `precious_metal_minute_archive`: `records_processed=0`
- `stock_15min_archive`: `records_processed=0`
- `futures_15min_archive`: `records_processed=0`
- `commodity_15min_archive`: `records_processed=0`
- `precious_metal_15min_archive`: `records_processed=0`

This is consistent with forward-only/no-fresh-window behavior rather than a broken storage chain.

---

## 4. Archive bounded backfill proof/result

### What was required
An explicit check that backfill is not only parameterized, but can really close bounded recent gaps.

### Real control/evidence truth
Inspection of `archive_target_catchup` shows completed catch-up evidence, for example:
- `asset_category='stock'`
- `granularity='daily'`
- `symbol_or_series_id='399999.SZ'`
- `status='completed'`
- `checkpoint_dataset_name='stock_daily_catchup'`
- `progress_note='catch-up execution closed ... checkpoint advanced'`

This is real proof that catch-up/backfill is not merely theoretical metadata.
It has executed and closed at least one daily bounded catch-up intent.

### Exact bounded-backfill judgment
- **Positive proof exists at the daily / broader-history catch-up layer**
- This proves bounded backfill capability exists in the archive control plane and can advance checkpoints

### Important limit
This batch still does **not** provide a positive-row proof that `1m/15m` intraday archive lanes perform day-by-day recent-gap backfill in the same way.
Those lanes still behave as forward-only in current practical runtime behavior.

So the truthful split is:
- **bounded backfill proof: yes, for daily/broader-history catch-up**
- **bounded backfill proof: not established for current 1m/15m practical behavior**

---

## 5. Archive long-term retention clarification

### Long-lived historical retention is real for
- equities daily / catch-up archive layers
- non-equity broader-history layers (`futures_history`, `commodity_history`, `precious_metal_history`)
- `60m` archive layers for stock / futures / commodity / precious_metal
- current-day compact structured outputs via `daily_structured_output_archive`

### Forward-window accumulation is the current practical model for
- `stock_minute_history`
- `stock_15min_history`
- `futures_minute_history`
- `futures_15min_history`
- `commodity_minute_history`
- `commodity_15min_history`
- `precious_metal_minute_history`
- `precious_metal_15min_history`

### Plain-language retention model
What is truly kept long-term:
- daily and broader history
- 60m archive layers
- structured output archive snapshots

What is not currently demonstrated as broad historical backfill/retention:
- 1m / 15m intraday lanes

Those remain operationally closer to forward-window accumulation lanes.

---

## 6. Final-test preparation / cleanup note

Before the final full production-facing test, clean again:
- recent validation-generated `unified_runtime_runs`
- recent validation-generated `job_runs`
- recent validation-generated `highfreq_runs` / `lowfreq_runs`
- recent validation-generated `archive_runs`
- recent validation-generated `archive_summary_daily`
- recent validation-generated `daily_structured_output_archive` rows from validation phase only
- highfreq working/temporary state tables
- derived-state working tables produced in this tail-closure batch

Keep intact before final test:
- Business Layer truth/config tables
- focus/list-family truth tables
- runtime schedule/policy tables
- trading-day / trading-calendar truth
- archive checkpoints and catch-up control truth
- long-term reference/history baseline tables
- broader retained archive history already serving as baseline truth

### Important note
Because this tail batch manually invoked the highfreq derived builder for diagnosis, the derived-state working tables now contain diagnostic rows.
These should be cleaned before the final full test so the final run starts from an interpretable zeroed working-state baseline.

---

## 7. Final truthful judgment

### Closed in this batch
1. **Highfreq derived-state diagnosis closed**
   - source exists
   - builder works
   - zero-after-run was due to runtime wiring gap, not no-source

2. **Midfreq `sector_performance` diagnosis closed**
   - code path exists
   - live accessible source currently returns zero rows
   - current zero is best classified as source limitation in this environment

3. **Archive retention model clarified**
   - 1m/15m = forward-only practical behavior
   - 60m/daily/broader-history/structured-output = real retained historical layers

4. **Archive bounded-backfill capability clarified**
   - real completed daily catch-up/backfill evidence exists
   - intraday 1m/15m backfill remains unproven and should not be overstated

### Still residual before final full test
1. wire highfreq derived-state build into the intended full run path (if not already being addressed elsewhere)
2. clean validation residue again before final full test
3. do not overclaim `sector_performance` until the source returns real rows
4. do not overclaim intraday 1m/15m broad backfill retention

Overall:
- the remaining tails are now much narrower and better classified
- the biggest remaining non-source engineering tail is the **highfreq derived-state run-path wiring**
- the biggest remaining non-engineering limitation is **midfreq sector_performance source emptiness**
- archive truth is now sufficiently clarified for the final production-facing test design
