# Archive V2 Milestone 10 — Frequency Expansion Closure (2026-04-18 08:45 PDT)

## Scope
Close the interrupted Milestone 10 batch from the existing partial state and make `60m / 15m / 1m` real Archive V2 capability under explicit profile/operator enablement, without regressing the already-accepted additive frequency-completeness rule.

## Continuation truth
This batch was **not restarted from scratch**.
The repo already contained partial Milestone 10 scaffolding before this round:
- Archive V2 intraday archive tables in `src/ifa_data_platform/archive_v2/db.py`
- profile switches in `src/ifa_data_platform/archive_v2/profile.py`
- intraday family wiring in `src/ifa_data_platform/archive_v2/runner.py`
- Milestone 10 integration tests and profiles under `tests/integration/` and `profiles/`

The actual blocker when this round resumed was real and narrow:
- `runner._fetch_intraday_rows(...)` assumed non-existent source tables / generic date-column logic
- failing path observed earlier: intraday source date-column resolution inside Archive V2 runner

## Root cause
The partial Milestone 10 implementation pointed Archive V2 intraday families at wrong or non-existent source tables such as:
- `equity_60m_bar_history`
- `index_60m_bar_history`
- `equity_15m_bar_history`
- `index_15m_bar_history`
- `equity_1m_bar_history`
- `index_1m_bar_history`

That assumption was false in the real repo/DB state.
Actual source surfaces available in this environment are:
- equity 60m: `ifa2.stock_60min_history`
- equity 15m: `ifa2.stock_15min_history`
- equity 1m: `ifa2.stock_minute_history`
- index 1m: `ifa2.highfreq_index_1m_working`

There is **no retained index 15m/60m source table** in the current schema, so Archive V2 needed explicit family-aware handling instead of generic `date(...)` guessing.

## What changed in this round

### 1) Fixed intraday source/date/time resolution truthfully
Updated `src/ifa_data_platform/archive_v2/runner.py` so intraday families use explicit source metadata:

- `equity_60m` -> `stock_60min_history`
- `equity_15m` -> `stock_15min_history`
- `equity_1m` -> `stock_minute_history`
- `index_1m` -> `highfreq_index_1m_working`
- `index_15m` -> explicit `1m -> 15m` rollup from `highfreq_index_1m_working`
- `index_60m` -> explicit `1m -> 60m` rollup from `highfreq_index_1m_working`

Added explicit intraday metadata helpers instead of relying on naive generic date-column discovery:
- `_intraday_time_col(...)`
- `_intraday_symbol_col(...)`
- `_intraday_date_expr(...)`

This makes the runner family-aware about:
- which table is real
- which timestamp column is authoritative
- which business-date filter expression is correct
- which families need direct row copy vs explicit rollup

### 2) Closed index 15m / 60m with explicit rollup logic
Added bounded explicit rollup path in Archive V2 runner:
- `_fetch_intraday_rollup_rows(...)`
- `_bucket_intraday_time(...)`

Behavior:
- pulls real 1m index rows from `highfreq_index_1m_working`
- groups them into requested 15m / 60m buckets
- preserves open/high/low/close semantics
- sums `vol` and `amount`
- writes real Archive V2 rows into `ifa_archive_index_15m` / `ifa_archive_index_60m`

This is truthful closure for the current repo state because the retained source truth available for index intraday in this environment is 1m working data, not a separate 15m/60m history table.

### 3) Preserved frequency-layer-specific completeness behavior
The partial Milestone 10 runner already had the important frequency-aware completeness shape; this round preserved and validated it:
- completeness is keyed by `(business_date, family_name, frequency, coverage_scope)`
- additive frequency runs can target only one requested layer
- already-completed daily/final layer is not rerun unnecessarily when only `60m` is requested later

### 4) Updated bounded validation scope to a truthful date
Milestone 10 validation profiles/tests were moved to `2026-04-15` because that is the bounded date where the real source surfaces align:
- stock retained 60m/15m/1m rows exist
- highfreq index 1m rows exist
- additive daily + 60m proof is available

Files updated:
- `profiles/archive_v2_milestone10_intraday_sample.json`
- `profiles/archive_v2_milestone10_daily_index_only.json`
- `profiles/archive_v2_milestone10_add_60m_only.json`
- `tests/integration/test_archive_v2_milestone10.py`

## Implementation summary
Files completed/advanced in the Milestone 10 closure path:
- `src/ifa_data_platform/archive_v2/db.py`
- `src/ifa_data_platform/archive_v2/profile.py`
- `src/ifa_data_platform/archive_v2/runner.py`
- `src/ifa_data_platform/runtime/target_manifest.py`
- `profiles/archive_v2_milestone10_intraday_sample.json`
- `profiles/archive_v2_milestone10_daily_index_only.json`
- `profiles/archive_v2_milestone10_add_60m_only.json`
- `tests/integration/test_archive_v2_milestone10.py`

Round-specific closure work in this session was concentrated in runner fix + bounded validation/profile alignment + final doc.

## Validation executed

### A. Integration suite
Command:
```bash
python3 -m pytest -q tests/integration/test_archive_v2_milestone10.py -q
```
Result:
- passed

What this test suite proves:
- Archive V2 `60m / 15m / 1m` branches run
- corresponding Archive V2 tables get real rows
- profile flags drive intraday execution
- additive `daily -> later add only 60m` behavior works
- additive run writes only `index_60m` in the later step

### B. Real bounded Archive V2 intraday profile run
Command:
```bash
python3 scripts/archive_v2_run.py --profile profiles/archive_v2_milestone10_intraday_sample.json
```
Result:
- `ok=true`
- `run_id=3c470417-bc9d-4ace-b254-af92b14822f0`
- `status=completed`
- `dates=1 executed_targets=6 skipped_targets=0`

Run item evidence:
- `equity_60m` -> `27` rows
- `index_60m` -> `1` row
- `equity_15m` -> `51` rows
- `index_15m` -> `1` row
- `equity_1m` -> `723` rows
- `index_1m` -> `6` rows

Archive table row evidence for `business_date=2026-04-15`:
- `ifa_archive_equity_60m` -> `27`
- `ifa_archive_index_60m` -> `1`
- `ifa_archive_equity_15m` -> `51`
- `ifa_archive_index_15m` -> `1`
- `ifa_archive_equity_1m` -> `723`
- `ifa_archive_index_1m` -> `6`

Completeness evidence:
- `equity_60m` / `60m` -> `completed`, `row_count=27`
- `index_60m` / `60m` -> `completed`, `row_count=1`
- `equity_15m` / `15m` -> `completed`, `row_count=51`
- `index_15m` / `15m` -> `completed`, `row_count=1`
- `equity_1m` / `1m` -> `completed`, `row_count=723`
- `index_1m` / `1m` -> `completed`, `row_count=6`

### C. Additive frequency proof
Commands:
```bash
python3 scripts/archive_v2_run.py --profile profiles/archive_v2_milestone10_daily_index_only.json
python3 scripts/archive_v2_run.py --profile profiles/archive_v2_milestone10_add_60m_only.json
```
Results:
- daily run -> `run_id=5151dcbb-1db1-4669-8075-15b0d34c2c64`, `status=completed`
- later 60m-only run -> `run_id=3a5801b5-1e21-424d-a467-b13a1181c9c3`, `status=completed`

Proof of selective execution:
- daily run items:
  - only `index_daily`
- later additive run items:
  - only `index_60m`

This proves:
- daily completeness remained completed
- later explicit `60m` request added only the missing 60m layer
- already completed daily layer was not rerun in the additive step

## Notes / caveats kept truthful
- This closure makes `60m / 15m / 1m` real Archive V2 capability for the currently wired equity/index families in Archive V2.
- The bounded validation here is intentionally small-scope and does **not** claim full-market benchmark throughput.
- Index 15m/60m closure is implemented as explicit rollup from real retained `index 1m` working truth because separate retained index 15m/60m history tables do not exist in the current repo/database state.
- A parallel manual rerun of multiple profiles at once can deadlock in `ensure_schema()` because each process performs DDL-on-startup; the actual bounded validation/proof was completed successfully using sequential runs.

## Final status
Milestone 10 frequency expansion is now closed from the partial state with:
- real Archive V2 intraday tables
- real runner execution branches
- real profile switches
- frequency-specific completeness tracking
- additive frequency behavior validated
- bounded truthful runtime evidence recorded
