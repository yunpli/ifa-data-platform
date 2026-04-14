# Collection Runtime Audit — 2026-04-14

Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Request Scope

This pass is a pre-upgrade collection-layer cleanup and repair pass.
Target was **not** feature expansion. Target was to:
- stop lowfreq cleanly
- audit lowfreq / midfreq / archive runtime chains
- stop archive empty-run churn
- clean repo state
- perform minimal necessary DB cleanup
- write formal operator docs and status snapshot

## 2. Runtime Audit Result

### lowfreq
**Formal chain**
- `python -m ifa_data_platform.lowfreq.daemon --loop`
- helper: `scripts/run_lowfreq_daemon.sh`

**Observed runtime status**
- no live lowfreq daemon process found during audit

**Conclusion**
- lowfreq is currently stopped
- no kill action was required because there was no matching live lowfreq runtime process to terminate

### midfreq
**Formal chain**
- `python -m ifa_data_platform.midfreq.daemon --loop`

**Observed runtime status**
- live process found:
  - PID `42398`
  - command: `python -m ifa_data_platform.midfreq.daemon`
- DB carried stale failure state in `midfreq_daemon_state`

**Conclusion**
- midfreq is the only confirmed live collection daemon process at audit time
- preserved intentionally; not stopped in this pass to avoid collateral damage

### archive
**Formal chain after repair**
- `python -m ifa_data_platform.archive.daemon --once`
- `python -m ifa_data_platform.archive.daemon --loop`
- implementation remains in `archive.archive_daemon`

**Observed runtime status**
- no live archive daemon process found during audit
- historical repeated same-window archive execution residue existed in snapshots and DB before minimal cleanup

**Conclusion**
- archive runtime is now formalized to a single CLI path with duplicate-window guard and next-window sleeping strategy

## 3. What Was Stopped vs Preserved

### Stopped
- lowfreq runtime target state: stopped
- archive duplicate same-window re-execution behavior: stopped in code path
- archive noise rows from repeated same-window runtime residue: removed

### Preserved
- live midfreq daemon process
- all real asset tables and their data
- valid archive checkpoints
- valid current archive summary/state
- lowfreq runtime state tables and asset-side collection history

## 4. Archive 30-Second Empty-Run Problem

### Root issue
Archive loop was previously capable of waking continuously and re-triggering work within the same official window, creating noisy repeated `stock_daily_archive` rows.

### Repair result
Current archive loop now:
- computes business date in Asia/Shanghai
- skips if same `date + window_name` already recorded as `completed`/`partial`
- sleeps until next enabled official window instead of fixed short empty polling after completion or when out of window

## 5. Repo Hygiene Result

### Dirty items observed at start
- `.gitignore` modified
- `src/ifa_data_platform/archive/archive_daemon.py` modified
- `ops/` untracked
- stray repo-root `ifa.db`

### Hygiene decisions
Keep tracked:
- docs
- runtime code changes
- compatibility archive CLI module

Ignore / local-only:
- `ifa.db`
- `logs/`
- `config/archiver_test.yaml`
- `ops/snapshots/`

## 6. Minimal Necessary DB Cleanup Result

### Cleanup performed
- removed earlier duplicate archive job-run noise, retaining the latest clean run per archive job
- removed `dummy_source_healthcheck` noise rows from `ifa2.job_runs`
- removed stale failed `midfreq_window_state` residue for clean baseline handoff
- retained only the clean current archive summary row per business-date/window

### Explicitly not cleaned
- `stock_daily_history`
- `macro_history`
- `futures_history`
- `symbol_universe`
- `lowfreq_runs`
- `lowfreq_raw_fetch`
- `lowfreq_datasets`
- `midfreq_datasets`
- `archive_checkpoints`
- `stock_history_checkpoint`

### Reason
Those are real data assets, current control state, or historical collection facts that still have operator value.

## 7. Documents Produced

- `docs/DEVELOPER_COLLECTION_CONTEXT.md`
- `docs/ARCHIVE_RUNTIME_AND_DATA_STATUS.md`
- `docs/FOCUSED_WATCHLIST_DESIGN.md`
- `docs/COLLECTION_RUNTIME_AUDIT_2026-04-14.md`
- `docs/COLLECTION_STATUS_SNAPSHOT_2026-04-14.txt`

## 8. Current Boundary After Cleanup

- lowfreq: intentionally stopped
- midfreq: still running; only live collection daemon observed
- archive: repaired formal chain, currently not running
- no justification remains for multiple old archive chains running in parallel

## 9. Remaining Blocker

Single remaining blocker for a perfectly "green" runtime handoff:
- midfreq still has a live process (`PID 42398`) whose desired owner state was not changed in this pass because the instruction only explicitly required stopping lowfreq and avoiding collateral damage. If you want a totally frozen collection baseline before next-stage upgrade, midfreq should be explicitly reviewed and likely stopped/relaunched under a single confirmed owner path.
