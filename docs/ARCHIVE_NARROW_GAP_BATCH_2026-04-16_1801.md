# Archive Narrow Gap Batch

_Date: 2026-04-16 18:01_

## Scope
This batch focused narrowly on three goals:
1. improve BL non-equity coverage as far as truth allows
2. fix archive summary counting bug
3. try to obtain positive-row proof for non-equity intraday archive

## Archive summary bug fix
### Root cause
In `archive_orchestrator.py`, the archive window summary used:
- `total_jobs = len(enabled_jobs)`
while
- `succeeded_jobs` counted the final `results` list

After adding `structured_output_archive` as an extra result outside the original `enabled_jobs` set, summary logs could report impossible counts such as:
- `18/17 succeeded`

### Code fix
Changed summary computation and log output to use the final `results` list consistently:
- `total_jobs = len(results)`
- log denominator also uses `len(results)`

### Real proof after fix
Real rerun result:
- `Window manual_archive completed: 18/18 succeeded, 0 failed, 0 records`

This proves the counting bug is closed.

## Real archive rerun summary
Command:
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600
```

Unified runtime result:
- `status=succeeded`
- `governance_state=ok`
- `duration_ms=47082`

### Per-job summary in this rerun
All 18 jobs succeeded:
- 5 daily jobs
- 4 sixty-minute jobs
- 4 fifteen-minute jobs
- 4 one-minute jobs
- 1 structured-output archive job

Records produced in this rerun:
- daily jobs: all `0`
- 60m jobs: all `0`
- 15m jobs: all `0`
- 1m jobs: all `0`
- structured-output archive: `0`

## Per-job / per-table touched-table truth for this rerun
### Runtime / audit tables
| table | meaning | class | before | after | delta |
|---|---|---|---:|---:|---:|
| `archive_runs` | archive per-job evidence | runtime/audit | 56 | 73 | +17 |
| `archive_summary_daily` | archive summary rollup | runtime/audit | 1 | 2 | +1 |
| `unified_runtime_runs` | unified runtime evidence | runtime/audit | 13 | 14 | +1 |
| `job_runs` | generic runtime/job evidence | runtime/audit | 13 | 14 | +1 |

### Checkpoint / catch-up tables
| table | meaning | class | before | after | delta |
|---|---|---|---:|---:|---:|
| `archive_checkpoints` | archive checkpoint anchors | checkpoint | 18 | 18 | 0 |
| `archive_target_catchup` | catch-up intent/progress | catch-up | 8 | 8 | 0 |

### 60m history tables
| table | meaning | class | before | after | delta |
|---|---|---|---:|---:|---:|
| `stock_60min_history` | stock 60m archive | history | 60 | 60 | 0 |
| `futures_60min_history` | futures 60m archive | history | 250 | 250 | 0 |
| `commodity_60min_history` | commodity 60m archive | history | 250 | 250 | 0 |
| `precious_metal_60min_history` | precious metal 60m archive | history | 250 | 250 | 0 |

### 15m / 1m history tables
All unchanged:
- `stock_15min_history`: `1290 -> 1290`
- `stock_minute_history`: `2410 -> 2410`
- `futures_15min_history`: `22912 -> 22912`
- `futures_minute_history`: `32000 -> 32000`
- `commodity_15min_history`: `49456 -> 49456`
- `commodity_minute_history`: `56000 -> 56000`
- `precious_metal_15min_history`: `16000 -> 16000`
- `precious_metal_minute_history`: `16000 -> 16000`

### Structured-output archive table
- `daily_structured_output_archive`: `890 -> 890` (`0`)

## Positive-row proof for non-equity intraday archive
### Outcome
This batch did **not** obtain positive-row proof for non-equity intraday archive.

### Exact classification why
This rerun came **after** the prior forward-only archive run had already advanced the currently eligible forward slices.
Observed facts:
- 1m and 15m jobs all ran successfully
- row deltas remained `0`
- checkpoints remained unchanged
- history tables remained unchanged

Therefore the correct classification for this batch is:
- **no new eligible forward data in the current forward-only window**

This is **not** best classified as:
- runtime failure
- storage mapping failure
- job not running
- policy not wired

### Category-specific truth
- futures 1m/15m: still no positive-row proof; constrained both by no new forward data and weak BL/reference coverage
- commodity 1m/15m: still no positive-row proof in this rerun; best current classification is no new eligible forward data after prior archive advancement
- precious_metal 1m/15m: same classification, with additional BL coverage thinness

## What is now truly implemented vs still partial/unsupported
### Truly implemented
- archive summary counting is fixed
- 60m archive exists and was already proven to write rows in the prior real run
- current-day structured-output archive exists and was already proven to write rows in the prior real run
- this rerun confirms those paths can rerun cleanly without corrupt summary counts

### Still partial / unsupported
- positive-row proof for non-equity intraday archive in a fresh eligible forward window is still missing
- futures BL coverage remains 0
- precious-metal BL coverage remains thin
- commodity focus still below target

## Final truthful judgment
This narrow-gap batch closed one concrete defect completely:
- archive summary counting bug is fixed and proven by real run

It also truthfully attempted the non-equity intraday positive-row proof question.
The answer from this rerun is:
- **not achieved in this run**
- because there was **no new eligible forward data** after the earlier forward-only archive advancement

So the current truthful state is:
- counting bug: **closed**
- BL coverage: **slightly improved but still incomplete**
- non-equity intraday positive-row proof: **still pending a real future eligible forward window / richer source truth**
