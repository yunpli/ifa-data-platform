# Trailblazer Archive Operator-State Alignment

_Date: 2026-04-15 23:27 _

## 1. Purpose of this batch
- Align archive operator/status surfaces to the corrected truthful runtime scope.
- Remove stale unsupported macro intraday backlog from operator-visible archive status.

## 2. What was supposed to be done
- Clean up or reclassify stale operator-state for unsupported macro intraday archive assumptions.
- Re-run archive-status.
- Confirm operator surfaces only expose truthful current supported scope.
- Update canonical docs only if needed.

## 3. What was actually done
- Identified stale `archive_target_catchup` rows for unsupported `macro + minute` backlog assumptions still surfacing as pending operator backlog.
- Updated `archive_catchup_status()` in `src/ifa_data_platform/runtime/unified_runtime.py` to exclude unsupported active-backlog states for `macro` intraday (`minute`, `15min`) from operator-facing archive-status output.
- Re-ran `archive-status --limit 10` and verified the stale macro intraday pending rows no longer appear in operator-visible backlog/status summaries.

## 4. Code files changed
- `src/ifa_data_platform/runtime/unified_runtime.py`

## 5. Tests run and results
- Direct operator-status validation run:
  - `python scripts/runtime_manifest_cli.py archive-status --limit 10`
  - result: operator-visible `summary_by_status` no longer reports pending stale macro intraday backlog rows
- No additional broad test expansion was done in this narrow batch.

## 6. DB/runtime evidence
### Before alignment
Pending unsupported operator backlog rows existed in `ifa2.archive_target_catchup`, for example:
- `archive|minute|macro|CN_M2`
- `status = pending`
- repeated historical rows created under older assumptions

Operator-visible effect before alignment:
- `archive-status.summary_by_status` included:
  - `pending = 6`
- `recent_catchup_rows` exposed stale unsupported macro minute rows

### After alignment
Fresh operator-status output now shows:
- `summary_by_status`:
  - `completed = 1`
  - `observed = 1`
- no operator-visible `pending` stale macro intraday rows
- `recent_catchup_rows` now only show truthful supported-scope rows:
  - one historical completed stock catch-up proof row
  - one observed removed stock membership row

Checkpoint/operator consistency after alignment:
- recent checkpoints remain visible for supported archive datasets only
- recent archive runs remain visible for supported archive jobs only
- archive-status now matches corrected runtime truth much more closely end-to-end

## 7. Truthful result / judgment
- Archive operator/status surfaces are now aligned to the corrected supported runtime scope for practical operator use.
- Unsupported stale macro intraday backlog no longer appears as active operator backlog.
- Current truthful operator-facing archive scope is:
  - stock / futures / commodity / precious_metal: daily + 15min + minute
  - macro: historical/daily only

## 8. Residual gaps / blockers if any
- Historical unsupported macro intraday rows still exist in the table as historical records; this batch intentionally narrowed scope to operator-surface truth alignment rather than destructive data cleanup.
- If later needed, a separate maintenance batch can reclassify or archive those rows in-place at the storage level.

## 9. Whether docs had to be corrected because runtime/source reality did not support the earlier assumption
Only minimally in this batch.
- Canonical current-state docs already state the corrected runtime truth.
- This batch mainly brought operator-visible status surfaces into line with that existing canonical truth.
