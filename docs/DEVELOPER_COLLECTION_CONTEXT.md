# Developer Collection Context

Last updated: 2026-04-14
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Repo / Runtime Basics

- Repo path: `/Users/neoclaw/repos/ifa-data-platform`
- Python env: `.venv`
- Source root: `src/`
- Main schema: `ifa2`
- Primary database: PostgreSQL via `DATABASE_URL` in `.env`
- Local stray SQLite file: `ifa.db` at repo root is **not** the production collection DB and should stay ignored.

## 2. DB / Schema

Primary DSN is loaded from `.env`:

```env
DATABASE_URL=postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp
IFA_DB_SCHEMA=ifa2
```

Primary collection tables relevant to runtime:

### lowfreq
- `ifa2.lowfreq_datasets`
- `ifa2.lowfreq_runs`
- `ifa2.lowfreq_raw_fetch`
- `ifa2.lowfreq_daemon_state`
- `ifa2.lowfreq_group_state`

### midfreq
- `ifa2.midfreq_datasets`
- `ifa2.midfreq_execution_summary`
- `ifa2.midfreq_daemon_state`
- `ifa2.midfreq_window_state`

### archive
- `ifa2.archive_jobs`
- `ifa2.archive_runs`
- `ifa2.archive_summary_daily`
- `ifa2.archive_daemon_state`
- `ifa2.archive_checkpoints`
- `ifa2.stock_history_checkpoint`
- asset tables including `stock_daily_history`, `macro_history`, `futures_history`

### shared / universe
- `ifa2.symbol_universe`
- `ifa2.dataset_versions`
- `ifa2.job_runs`

## 3. Token / Secret Loading

Secrets are loaded from `.env` or ignored runtime env files.

Current local pattern:
- `DATABASE_URL` from repo `.env`
- `TUSHARE_TOKEN` from repo `.env`
- optional runtime env files under `config/runtime/*.env`

Rule:
- do not hardcode tokens into source
- keep `.env` local-only
- keep `config/runtime/*.env` gitignored

## 4. Runtime Daemon / Archiver Positioning

### lowfreq daemon
- Module: `ifa_data_platform.lowfreq.daemon`
- Purpose: low-frequency collection for daily-light / weekly-deep datasets
- Official CLI:
  - `python -m ifa_data_platform.lowfreq.daemon --once`
  - `python -m ifa_data_platform.lowfreq.daemon --loop`
  - `python -m ifa_data_platform.lowfreq.daemon --health`
- Shell helper: `scripts/run_lowfreq_daemon.sh`
- Current policy: **currently stopped intentionally** before next-stage collection upgrade

### midfreq daemon
- Module: `ifa_data_platform.midfreq.daemon`
- Purpose: same-day / post-close collection windows
- Official CLI:
  - `python -m ifa_data_platform.midfreq.daemon --once`
  - `python -m ifa_data_platform.midfreq.daemon --loop`
  - `python -m ifa_data_platform.midfreq.daemon --health`
  - `python -m ifa_data_platform.midfreq.daemon --watchdog`
- Current runtime finding: a persistent midfreq daemon process exists and is the only live collection daemon process found during this cleanup

### archive daemon / archiver
- Canonical implementation: `ifa_data_platform.archive.archive_daemon`
- CLI compatibility alias added: `ifa_data_platform.archive.daemon`
- Purpose: night-window long-history accumulation / backfill; not same-day report production
- Official windows (Asia/Shanghai):
  - `21:30–22:30`
  - `02:00–03:00`
- Official modes:
  - `--once` = one eligible window execution then exit
  - `--loop` = wait for official windows and run at most once per window/date
  - `--health` = state/summary/watchdog inspection

## 5. Current Collection Layer Structure

- `lowfreq/`: daily-light and weekly-deep batch collection + DB-backed daemon state
- `midfreq/`: windowed same-day collection + execution summary / watchdog
- `archive/`: long-horizon history accumulation with checkpoints and window summary
- `scripts/`: helpers / registration / validation
- `docs/`: runbooks, framework docs, acceptance notes
- `ops/snapshots/`: local cleanup snapshots; gitignored

## 6. Current Runtime Status (post-cleanup baseline)

### lowfreq
- Official chain: `python -m ifa_data_platform.lowfreq.daemon --loop`
- Helper chain: `scripts/run_lowfreq_daemon.sh`
- Current status: **not running**
- Reason: intentionally stopped / held before upgrade work
- DB state remains preserved (`lowfreq_*` tables retained)

### midfreq
- Official chain: `python -m ifa_data_platform.midfreq.daemon --loop`
- Current status: **running** as standalone process
- PID observed during audit: `42398`
- Latest DB state showed stale failure history in `ifa2.midfreq_daemon_state`; runtime owner should validate whether the live process should continue or be restarted cleanly in next phase
- No stop performed in this cleanup because instruction only required stopping lowfreq and avoiding collateral damage

### archive
- Official chain after cleanup:
  - `python -m ifa_data_platform.archive.daemon --once`
  - `python -m ifa_data_platform.archive.daemon --loop`
- Current status: **not running** at audit time
- Official policy after repair:
  - no out-of-window looping every 30 seconds
  - no duplicate execution for same business date + window
  - sleep until next enabled window when outside window or when current window already completed

## 7. Formal vs Residual Runtime Chains

### Formal chains
- lowfreq: `python -m ifa_data_platform.lowfreq.daemon --loop`
- midfreq: `python -m ifa_data_platform.midfreq.daemon --loop`
- archive: `python -m ifa_data_platform.archive.daemon --loop` (compat alias) / implementation in `archive.archive_daemon`

### Residual / historical items identified
- root-level `ifa.db`: local stray sqlite artifact, not formal runtime DB
- `ops/snapshots/*`: local cleanup snapshots, should not be committed
- historical archive test terminology in tests/docs (`test_window`, `test_window_1`, `test_window_2`) exists in code/tests/docs only; no live DB rows remained after cleanup
- old docs referenced `ifa_data_platform.archive.daemon` before module existed; fixed by compatibility entrypoint

## 8. Repo Hygiene Rules

Keep:
- source code
- docs
- migrations
- tracked config templates

Ignore / local-only:
- `.env`
- `config/runtime/*.env`
- `ifa.db`
- `logs/`
- `config/archiver_test.yaml`
- `ops/snapshots/`

## 9. Next-Phase Upgrade Starting Point

Before further collection expansion:
1. keep lowfreq stopped until runtime boundary is re-confirmed
2. decide whether the current midfreq daemon should stay running or be relaunched cleanly
3. use only one archive daemon chain (`python -m ifa_data_platform.archive.daemon`)
4. preserve real asset history tables and checkpoints
5. implement focused-watchlist logic on top of `symbol_universe` instead of ad-hoc side channels
