# Archive Runtime and Data Status

Last updated: 2026-04-14
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Final Repaired Runtime State

### Official runtime entry
- Preferred CLI: `python -m ifa_data_platform.archive.daemon`
- Canonical implementation: `src/ifa_data_platform/archive/archive_daemon.py`
- Compatibility entrypoint: `src/ifa_data_platform/archive/daemon.py`

### Runtime modes
- `--once`
  - run at most one eligible window
  - exit immediately if current time is outside configured windows
  - skip if the current business date + window already has `completed` or `partial` summary
- `--loop`
  - continuously wait for enabled windows
  - while outside a window: sleep until next window start
  - after a window has already executed for that business date: sleep until the next enabled window, not 30-second empty polling
- `--health`
  - inspect daemon state + summary + watchdog

### Official windows (Asia/Shanghai)
- `night_window_1`: `21:30–22:30`
- `night_window_2`: `02:00–03:00`

## 2. Archive 30-Second Empty-Run Issue

### Problem observed
Historical cleanup snapshots showed repeated `stock_daily_archive` runs in the same `night_window_1`, indicating empty or duplicate loop churn instead of true once-per-window execution.

### Repair applied
`archive_daemon.py` now:
- computes business date in archive timezone
- checks `archive_summary_daily(date, window_name)` before executing
- skips duplicate same-window runs for statuses `completed` / `partial`
- sleeps until next enabled window instead of fixed high-frequency polling outside useful runtime periods

### Effect
- same window is no longer repeatedly re-fired after success
- no out-of-window 30-second empty-run loop for archive window management
- archive loop behavior now cleanly separates:
  - active polling near active window
  - long sleep until next official window after completion / outside window

## 3. Archive Tables, Purpose, and Current Row Counts

Row counts at audit time:

| Table | Rows | Purpose |
|---|---:|---|
| `ifa2.archive_jobs` | 3 | Registered archive jobs (`stock_daily_archive`, `macro_archive`, `futures_archive`) |
| `ifa2.archive_runs` | 3 | Per-job execution records for archive windows |
| `ifa2.archive_summary_daily` | 1 | Per business-date + window execution summary |
| `ifa2.archive_daemon_state` | 1 | Daemon liveness / loop / last-success state |
| `ifa2.archive_checkpoints` | 3 | Unified resume/checkpoint status across archive datasets |
| `ifa2.stock_history_checkpoint` | 1 | Stock-specific archive checkpoint (primary stock resume state) |
| `ifa2.stock_daily_history` | 4819 | Archived stock daily history asset data |
| `ifa2.macro_history` | 1223 | Archived macro history asset data |
| `ifa2.futures_history` | 778 | Archived futures / commodity history asset data |

## 4. Current Table-Level State

### `archive_jobs`
Current jobs:
- `stock_daily_archive`
- `macro_archive`
- `futures_archive`

All 3 are enabled.

### `archive_runs`
Current retained rows correspond to one clean successful execution set for `night_window_1`:
- `stock_daily_archive` → succeeded → `4819` records
- `macro_archive` → completed → `1223` records
- `futures_archive` → completed → `778` records

### `archive_summary_daily`
Current retained summary:
- date: `2026-04-13`
- window: `night_window_1`
- total jobs: `3`
- succeeded jobs: `3`
- failed jobs: `0`
- total records: `6820`
- status: `completed`

### `archive_daemon_state`
Current retained daemon state:
- daemon name: `default`
- `is_running = false`
- `last_loop_at_utc = 2026-04-14T05:00:57.523880`
- `last_success_at_utc = 2026-04-14T05:00:57.525732`

### `archive_checkpoints`
Retained checkpoints:
- `stock_daily / stock` → completed to `2026-04-13`
- `macro_history / macro` → completed to `2026-04-13`
- `futures_history / futures` → completed to `2026-04-13`

### `stock_history_checkpoint`
Retained stock-specific checkpoint:
- `stock_daily`
- last completed date: `2026-04-13`
- last ts_code: `300536.SZ`
- batch_no: `20`
- status: `completed`

## 5. Data Retention Decision

### Kept
Kept all real asset / checkpoint state:
- `stock_daily_history`
- `macro_history`
- `futures_history`
- current checkpoints
- current clean archive summary / state rows

### Removed
Removed only noisy / redundant archive runtime residue from repeated same-window runs.

## 6. Runtime Chain Status

At cleanup audit time:
- no archive daemon process was found running
- no DB rows with `test_window` / `window_test_window` remained in archive run / summary tables
- no extra archive loop process was found by process scan

## 7. Remaining Risks

1. **Docs drift risk**
   - some historical docs referenced `ifa_data_platform.archive.daemon` before the module existed
   - fixed by adding compatibility entrypoint, but older text may still mention old operational assumptions

2. **Status string inconsistency**
   - `archive_runs` uses both `succeeded` and `completed` depending on code path / writer
   - functionally workable, but should be normalized later

3. **Single-row summary model**
   - current summary is one row per date/window
   - acceptable for control-plane level runtime gating, but not a detailed audit substitute

4. **Midfreq still live outside archive boundary**
   - archive is cleaned, but collection-layer overall runtime still has one live midfreq daemon; next-stage upgrade should confirm if that is intentional

## 8. Remaining Repair Debt

Not blocking this cleanup, but still worth tightening later:
- unify `archive_runs.status` vocabulary (`running/succeeded/failed` vs `completed`)
- add explicit operational script/service wrapper for archive loop if it becomes a long-running daemon in production
- formalize archive config file example under `config/` if the team wants declarative runtime config instead of code-default windows

## 9. Formal Boundary After Cleanup

- archive is a **night-window historical accumulation line** only
- archive is **not** the same-day report production path
- archive should run through **one formal chain only**:
  - `python -m ifa_data_platform.archive.daemon --once`
  - `python -m ifa_data_platform.archive.daemon --loop`
- archive should not coexist with ad-hoc duplicate loops or test windows in the live database
