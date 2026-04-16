# Trailblazer Archive Real-Run Truth Update

_Date: 2026-04-15 22:42 _

## 1. Purpose of this batch
- Close the false dry-run / real-run drift in the unified archive lane.
- Revalidate actual archive / lowfreq / midfreq runtime truth from current HEAD.
- Record truthful current production-closure judgment.

## 2. What was supposed to be done
- Switch unified archive lane from dry-run to truthful execution for implemented archive jobs.
- Run runtime validation.
- Collect DB/runtime evidence.
- Commit the batch.
- Correct runtime-reality statements where earlier documents drifted from current code/runtime truth.

## 3. What was actually done
- Changed unified archive execution from `dry_run=True` to `dry_run=False` in the unified runtime path.
- Changed archive unified worker label from `archive_dryrun_worker` to `archive_real_run_worker`.
- Added `execution_mode: real_run` to the archive unified summary payload.
- Re-ran archive through the unified lane and observed real execution of implemented daily / 15min / minute archive jobs.
- Re-ran lowfreq and midfreq live unified runtime paths from current HEAD.
- Committed the code batch.

## 4. Code files changed
- `src/ifa_data_platform/runtime/unified_runtime.py`
- `tests/integration/test_unified_runtime.py`

## 5. Tests run and results
- `pytest tests/integration/test_unified_runtime.py -q`
  - result: `12 passed in 379.28s`
- targeted archive/lowfreq/midfreq integration subset
  - result: `4 passed in 163.99s`
- targeted archive persistence subset
  - result: `2 passed in 118.99s`

## 6. DB/runtime evidence
### Lowfreq live run
- execution mode: `real_run`
- datasets executed:
  - `trade_cal` -> `2298`
  - `stock_basic` -> `5505`
  - `index_basic` -> `8000`
  - `announcements` -> `2811`
  - `news` -> `1500`
  - `company_basic` -> `6272`
- executed dataset count: `6`

### Midfreq live run
- execution mode: `real_run`
- datasets executed:
  - `equity_daily_bar` -> `20`
  - `index_daily_bar` -> `7`
  - `etf_daily_bar` -> `12`
  - `margin_financing` -> `360`
  - `main_force_flow` -> `20`
  - `dragon_tiger_list` -> `79`
- executed dataset count: `6`

### Archive live run after patch
- unified run id: `5132d412-78dd-4635-b74b-1b84a6d17c4b`
- worker type: `archive_real_run_worker`
- status: `partial`
- execution mode: `real_run`
- total jobs: `14`
- succeeded jobs: `13`
- failed jobs: `1`
- failure source: `macro_15min_archive` -> `NotImplementedError` because no real source/storage path exists in current repo

### Real archive execution observed for implemented paths
- daily:
  - stock
  - futures
  - commodity
  - precious_metal
  - macro
- 15min:
  - stock
  - futures
  - commodity
  - precious_metal
- minute:
  - stock
  - futures
  - commodity
  - precious_metal

### Table counts observed after real archive execution
- `archive_runs = 674`
- `archive_checkpoints = 18`
- `stock_minute_history = 1205`
- `futures_minute_history = 32000`
- `commodity_minute_history = 56000`
- `precious_metal_minute_history = 16000`
- `stock_15min_history = 1205`
- `futures_15min_history = 22912`
- `commodity_15min_history = 49456`
- `precious_metal_15min_history = 16000`

## 7. Truthful result / judgment
- **archive**
  - unified archive lane is now truthfully executing implemented jobs, not pretending via dry-run
  - archive is **partially closed / partially operational** at the unified-lane level because `macro_15min_archive` still has no real source/storage path and fails truthfully
- **lowfreq**
  - validated operational in real-run mode for the current proof set
- **midfreq**
  - validated operational in real-run mode for the current proof set
- **minute archive**
  - stock / futures / commodity / precious_metal minute archive paths are implemented and executed through the unified archive lane

## 8. Residual gaps / blockers if any
- `macro_15min_archive` remains a truthful blocker because current repo/runtime has no real source/storage path
- archive remains `partial` until unsupported category/frequency combinations are either:
  - implemented truthfully with real source/storage/runtime support, or
  - removed/reclassified from the claimed supported runtime scope and corrected in docs

## 9. Whether docs had to be corrected because runtime/source reality did not support the earlier assumption
Yes.

The earlier review-state docs drifted in two ways:
1. some documents still described archive as effectively a smaller 3-job/default-scope runtime, while current code/runtime truth is a 14-job implemented archive surface;
2. some implicit wording could be read as if all category/frequency combinations should work uniformly, but current runtime truth shows that `macro_15min` does not have a real source/storage path and must be classified honestly rather than hand-waved.

## Commit created
- `1b126b9` — `Run unified archive lane in real execution mode`
