# Non-Equity Intraday Proof Reassessment

_Date: 2026-04-16_1852_

## Scope
This narrow batch had two goals:
1. improve practical BL non-equity coverage under the corrected category model
2. rerun archive and reassess whether positive-row proof for non-equity intraday archive can now be obtained

Artifacts:
- `scripts/non_equity_intraday_snapshot.py`
- `artifacts/non_equity_intraday/before_non_equity_intraday_proof.json`
- `artifacts/non_equity_intraday/after_non_equity_intraday_proof.json`

## BL coverage improvement summary
After the BL-side improvement batch, practical non-equity category coverage is now:
- commodity: 4
- metal: 8
- precious_metal: 4
- black_chain: 6

This means the earlier mixed-bucket BL issue is no longer the main blocker for intraday proof assessment.

## Real archive run summary
Command:
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600
```

Unified runtime result:
- succeeded
- archive completed cleanly

## Positive-row proof result
### Outcome
Positive-row proof for non-equity intraday archive was **still not achieved** in this rerun.

Affected jobs:
- `futures_15min_archive`
- `futures_minute_archive`
- `commodity_15min_archive`
- `commodity_minute_archive`
- `precious_metal_15min_archive`
- `precious_metal_minute_archive`

All remained `0 records`.

## Touched-table summary
Before vs after:
- `futures_15min_history`: unchanged
- `futures_minute_history`: unchanged
- `commodity_15min_history`: unchanged
- `commodity_minute_history`: unchanged
- `precious_metal_15min_history`: unchanged
- `precious_metal_minute_history`: unchanged
- `archive_runs`: increased as jobs executed again

Meaning:
- runtime path is real
- archive jobs did run
- storage tables exist
- but no new non-equity intraday rows were added in this rerun

## Exact zero-result full-chain classification
### Commodity / metal / black_chain intraday path
Business Layer scope:
- now cleaner and explicitly categorized
- scope is no longer blocked by the old mixed-category semantics

Manifest / selection:
- archive selection path runs with current BL-driven selection semantics
- jobs are scheduled and executed

Source fetch / eligible material:
- current run still found no fresh forward-eligible material for the tested intraday categories

Archive selection:
- forward-only semantics remain in force
- previously archived forward slices are not re-backfilled

Storage write attempt:
- no new rows qualified, so storage history tables stayed unchanged

Final delta:
- `0`

### Precious_metal intraday path
Business Layer scope:
- still thin (4 symbols)

Manifest / selection:
- path is active

Source fetch / eligible material:
- no fresh forward-eligible material in this rerun

Storage write:
- no new rows

Final delta:
- `0`

### “Futures” intraday path in current practical sense
Business Layer scope:
- current practical bucket is still limited by source truth
- the financial-futures question is already resolved and not the issue here

Selection / runtime:
- job runs

Final delta:
- `0`

## Exact root-cause judgment for the remaining zero-result case
The best current classification is:
1. **no new eligible forward data** in the current forward-only window
2. BL coverage is now cleaner, but still relatively small
3. runtime selection path is real
4. storage path is real
5. this batch does **not** support classifying the problem as a storage-mapping or runtime-selection failure

So the remaining zero-result case is primarily a **forward-window / fresh-material availability issue**, not just a BL taxonomy problem anymore.

## Truthful final judgment
- BL coverage improvement was real but modest
- archive intraday runtime path remains real
- positive-row proof for non-equity intraday archive is still not achieved
- after the BL cleanup, the most defensible explanation is now:
  - **no fresh eligible forward material in the tested window**, with coverage still somewhat thin but no evidence of a broken runtime/storage chain
