# Trailblazer Archive Scope Truth Alignment

> **Document status:** Intermediate batch record. Preserved as a timestamped truth-alignment artifact. Superseded as current-state source by the refreshed canonical current-state docs after the latest sanity batch.
_Date: 2026-04-15 22:46 _

## 1. Purpose of this batch
- Eliminate the current truthful archive failure caused by unsupported macro intraday archive jobs.
- Align runtime scope to real source/storage reality instead of keeping unsupported macro 15min/minute jobs enabled.

## 2. What was supposed to be done
- Verify the macro intraday category/frequency mismatch against live DB/runtime truth.
- If no truthful source/storage path exists, stop pretending support and constrain runtime scope accordingly.
- Re-run archive unified runtime and validate the post-alignment state.

## 3. What was actually done
- Verified Business Layer still contains `macro` targets in `15min` and `minute` archive lists.
- Verified DB schema contains `macro_history` only and no truthful macro intraday storage tables.
- Confirmed archive runtime code path explicitly raised `NotImplementedError` for macro intraday archive handling.
- Disabled `macro_15min_archive` and `macro_minute_archive` in `archive_config.py`.
- Re-ran unified archive real-run validation after scope correction.

## 4. Code files changed
- `src/ifa_data_platform/archive/archive_config.py`

## 5. Tests run and results
- targeted archive integration subset:
  - `pytest tests/integration/test_unified_runtime.py::test_unified_runtime_run_once_archive_real_run_executes tests/integration/test_unified_runtime.py::test_unified_runtime_persists_manifest_snapshot_and_archive_catchup_rows -q`
  - result: pending at time of document write; runtime validation result below is the current source of truth for this batch

## 6. DB/runtime evidence
### Business Layer target reality
Live focus-list distribution still includes:
- `15min + macro = 8`
- `minute + macro = 4`

### Storage/schema reality
Macro-related archive tables present in `ifa2`:
- `macro_history`

No truthful macro intraday archive storage tables were found.

### Runtime truth before alignment
- archive unified real-run had `archive_total_jobs = 14`
- `archive_failed_jobs = 1`
- failing path: `macro_15min_archive`
- failure mode: explicit `NotImplementedError`

### Runtime truth after alignment
- unified run id: `3167ca9b-ce4a-4fd6-94c4-10f6d1d67823`
- `worker_type = archive_real_run_worker`
- `status = succeeded`
- `execution_mode = real_run`
- `archive_total_jobs = 13`
- `archive_succeeded_jobs = 13`
- `archive_failed_jobs = 0`

## 7. Truthful result / judgment
- The previous archive partial state was caused by an unsupported category/frequency claim, not by a bug in an otherwise-supported path.
- In the current repo/runtime truth, macro is supported only at the historical/daily archive level.
- Macro `15min` and `minute` archive are **not truthfully supported** and should not remain enabled in the active archive runtime scope.
- After disabling unsupported macro intraday jobs, the unified archive lane is now truthfully green for its actually supported implemented scope.

## 8. Residual gaps / blockers if any
- Business Layer still contains macro intraday targets that exceed current truthful archive source/storage/runtime support.
- That is now a classified scope mismatch, not a hidden runtime failure.
- Residual next-step decision surface:
  1. either Business Layer archive target definitions should be narrowed for unsupported macro intraday frequencies, or
  2. a real macro intraday source/storage/runtime path must be designed and implemented later.

## 9. Whether docs had to be corrected because runtime/source reality did not support the earlier assumption
Yes.

This batch proves that current truthful archive support must be stated as:
- stock / futures / commodity / precious_metal: daily + 15min + minute implemented scope
- macro: historical/daily only

Any wording that implies macro 15min/minute archive is currently supported would be false and must be corrected.
