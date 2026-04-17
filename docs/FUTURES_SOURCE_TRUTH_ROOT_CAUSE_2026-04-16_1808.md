# Futures Source-Truth Root Cause

_Date: 2026-04-16_1808_

## Scope
This batch investigates the futures coverage gap directly and concretely.
Question:
Is futures BL coverage still 0 because the upstream accessible source truly does not provide the approved futures roots,
or because our own mapping / interpretation / resolution logic is wrong?

Artifacts:
- `scripts/investigate_futures_source_truth.py`
- `artifacts/futures_source_truth_2026-04-16_1805.json`

Approved futures roots under investigation:
- `IF`
- `IH`
- `IC`
- `IM`
- `TS`
- `TF`
- `T`
- `TL`

## Inspected source paths / accessible truth
The current accessible futures-related DB/source paths in our environment are:
- `ifa2.futures_history`
- `ifa2.futures_15min_history`
- `ifa2.futures_minute_history`
- `ifa2.futures_60min_history`
- `ifa2.highfreq_futures_minute_working`
- current BL/archive items with `asset_category='futures'`
- archive runtime evidence for futures datasets

## What the accessible source actually contains
### Distinct symbols in `futures_history`
Representative symbols actually present:
- `AG2506.SHF`
- `AL2506.SHF`
- `AU2506.SHF`
- `B2506.DCE`
- `CU2506.SHF`
- `HC2506.SHF`
- `I2506.DCE`
- `J2506.DCE`
- `J2509.DCE`
- `JM2506.DCE`
- `MA2506.ZCE`
- `NI2506.SHF`
- `PB2506.SHF`
- `RB2506.SHF`
- `RU2506.SHF`
- `TA2506.ZCE`
- `ZN2506.SHF`

### Distinct symbols in `futures_15min_history`
Actually present:
- `I2506.DCE`
- `J2506.DCE`
- `J2509.DCE`
- `JM2506.DCE`

### Distinct symbols in `futures_minute_history`
Actually present:
- `I2506.DCE`
- `J2506.DCE`
- `J2509.DCE`
- `JM2506.DCE`

### Distinct symbols in `futures_60min_history`
Actually present:
- `J2509.DCE`

### Current BL/archive futures items
Current BL/archive futures item symbols observed:
- `I0`
- `JM0`

## Sample field evidence
### `futures_history` sample fields
Example row fields actually available:
- `ts_code`
- `trade_date`
- `pre_close`
- `pre_settle`
- `open`
- `high`
- `low`
- `close`
- `settle`
- `change1`
- `change2`
- `vol`
- `amount`
- `oi`
- `oi_chg`
- `source`

Representative sample:
- `ts_code=J2509.DCE`
- `trade_date=2025-09-12`
- `open=1502.0000`
- `high=1525.0000`
- `low=1502.0000`
- `close=1525.0000`
- `source=tushare`

### `futures_15min_history` sample fields
Example row fields actually available:
- `ts_code`
- `trade_time`
- `open`
- `high`
- `low`
- `close`
- `vol`
- `amount`
- `oi`
- `freq`
- `source`

Representative sample:
- `ts_code=J2509.DCE`
- `trade_time=2025-09-12 15:00:00`
- `freq=15min`
- `source=tushare`

### `futures_minute_history` sample fields
Example row fields actually available:
- `ts_code`
- `trade_time`
- `open`
- `high`
- `low`
- `close`
- `vol`
- `amount`
- `oi`
- `freq`
- `source`

Representative sample:
- `ts_code=J2509.DCE`
- `trade_time=2025-09-12 15:00:00`
- `freq=1min`
- `source=tushare`

## Expected roots vs actually available truth
### Direct root-hit comparison
For each approved root, checked whether it appears anywhere in:
- futures history tables
- futures intraday tables
- futures 60m table
- BL/archive futures items

Result:
- `IF` -> no hits anywhere
- `IH` -> no hits anywhere
- `IC` -> no hits anywhere
- `IM` -> no hits anywhere
- `TS` -> no hits anywhere
- `TF` -> no hits anywhere
- `TL` -> no hits anywhere
- `T` -> no true futures hit; one false-positive prefix collision with `TA2506.ZCE`

Important note:
- root `T` naively prefix-matches `TA2506.ZCE`
- that is **not** a treasury futures contract
- it proves a symbol-root normalization trap in the current simplistic prefix logic

## Exact root-cause judgment
The futures gap is caused by a **combination** of factors:

### 1. Source truth genuinely missing the approved financial-futures roots in our current accessible path
This is the primary cause.
Direct evidence:
- none of `IF/IH/IC/IM/TS/TF/TL` appears in any currently accessible futures-related table samples or BL/archive futures item state
- `T` only appears as a false-positive collision with `TA`

So for the currently accessible DB/source truth, the approved financial-futures universe is genuinely absent.

### 2. Our current mapping / interpretation of “futures” is too broad and semantically mixed
Also true.
Current `futures_history` includes symbols such as:
- `AG`, `AU`, `CU`, `AL`, `ZN`, `RB`, `RU`, `TA`, `MA`, `I`, `J`, `JM`

These are not the approved financial-futures universe.
They are commodity / metals / precious-metal style contracts mixed under a generic futures path.

So one problem is not just source absence — it is also that our current “futures” bucket does not mean “financial futures” in a clean business sense.

### 3. Symbol normalization/root-resolution logic is incomplete
Also true.
The current simple root check can misclassify:
- approved root `T`
- actual commodity symbol root `TA`

So even if some approved roots were present later, the current resolution logic needs stricter root-token normalization to avoid false hits.

### 4. Wrong reference-table choice contributed to earlier wrong conclusions
Also true.
Earlier attempts looked at equity-oriented or too-thin reference layers first.
This batch shows the correct investigation surface is the actual accessible history/source tables.

## Final classification
The truthful classification is:
- **not** just “BL seeding logic is wrong”
- **not** just “mapping logic is wrong”
- **not** just “wrong reference table choice”
- but a combination of:
  1. **current accessible source truth does not expose the approved financial-futures roots**
  2. **our current futures bucket is semantically mixed with commodity-like contracts**
  3. **root normalization logic is incomplete and can produce false positives (`T` vs `TA`)**

## What needs to change next
### If the business wants the approved financial-futures universe (`IF/IH/IC/IM/TS/TF/T/TL`)
Then we need one or more of:
1. a source path that actually exposes these instruments in the current accessible environment
2. a dedicated financial-futures reference table or ingestion path
3. stricter symbol-root normalization logic
4. separation of:
   - financial futures
   - commodity / industrial / precious-metal contracts

### What does NOT need to change first
- BL list-family taxonomy is not the main blocker anymore
- the core blocker is upstream accessible source/reference truth plus category semantics

## Bottom-line judgment
The futures coverage gap is **primarily a source/reference-truth gap**, with **secondary mapping/normalization issues**.
The current accessible “futures” path does not actually expose the approved financial-futures roots.
So saying only “futures is still 0” was insufficient — the precise answer is now:
- the approved financial-futures instruments are not present in the current accessible source truth we are using,
- and our current generic `futures_*` path is semantically mixed enough that it should not be treated as proof of financial-futures coverage.
