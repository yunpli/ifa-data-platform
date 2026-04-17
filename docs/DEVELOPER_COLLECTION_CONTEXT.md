# Developer Collection Context

Last updated: 2026-04-16
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

## 4. Runtime Positioning

### Unified runtime daemon (official)
Production-safe bring-up path:
- `zsh scripts/unified_daemon_service.sh preflight`
- `zsh scripts/unified_daemon_service.sh start`
- `zsh scripts/unified_daemon_service.sh status`
- `zsh scripts/unified_daemon_service.sh stop`

Official long-running runtime entry used by the service wrapper:
- `python -m ifa_data_platform.runtime.unified_daemon --loop`

Operator/manual entry surfaces:
- `python -m ifa_data_platform.runtime.unified_daemon --once`
- `python -m ifa_data_platform.runtime.unified_daemon --status`
- `python -m ifa_data_platform.runtime.unified_daemon --worker lowfreq --runtime-budget-sec 1800`
- `python -m ifa_data_platform.runtime.unified_daemon --worker midfreq --runtime-budget-sec 1800`
- `python -m ifa_data_platform.runtime.unified_daemon --worker highfreq --runtime-budget-sec 900`
- `python -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600`

Preflight/repair truth before service start:
- auto-clears stale active runtime markers older than threshold if found
- auto-marks stale archive checkpoints stuck in `in_progress` as `abandoned`
- reports stale `pending/observed` catch-up rows without destructive cleanup
- writes operator-visible JSON under `artifacts/service/runtime_preflight_latest.json`

Unified daemon currently owns:
- schedule loading from `ifa2.runtime_worker_schedules`
- trading-day classification from `ifa2.trade_cal_current`
- central worker state via `ifa2.runtime_worker_state`
- central run evidence via `ifa2.unified_runtime_runs`
- worker dispatch across lowfreq/midfreq/highfreq/archive

### Lane daemons (compatibility/manual wrappers)
- `ifa_data_platform.lowfreq.daemon`
- `ifa_data_platform.midfreq.daemon`
- `ifa_data_platform.highfreq.daemon`

These still exist for compatibility/manual use, but their long-running `--loop` role is no longer the official production runtime model.

### Archive worker positioning
Archive should now be understood as a worker under the unified daemon.
Archive-specific code still exists under `archive/`, but official long-running operation should not be documented as a parallel independent runtime path.

## 5. Current Collection Layer Structure

- `lowfreq/`: daily-light and weekly-deep batch collection + DB-backed daemon state
- `midfreq/`: windowed same-day collection + execution summary / watchdog
- `archive/`: long-horizon history accumulation with checkpoints and window summary
- `scripts/`: helpers / registration / validation
- `docs/`: runbooks, framework docs, acceptance notes
- `ops/snapshots/`: local cleanup snapshots; gitignored

## 6. Current Runtime/Data Truth (post-convergence)

### Runtime truth
- unified daemon is the official long-running runtime model
- accepted runtime budgets:
  - lowfreq: `1800 sec`
  - midfreq: `1800 sec`
  - highfreq: `900 sec`
  - archive: `3600 sec`
- schedule policy is day-type driven:
  - `trading_day`
  - `non_trading_weekday`
  - `saturday`
  - `sunday`

### Business Layer truth relevant to runtime
Present:
- `default_key_focus`
- `default_focus`
- `default_archive_targets_15min`
- `default_archive_targets_minute`
- `default_tech_key_focus` (seeded later)
- `default_tech_focus` (seeded later)

Missing / still not fully defined or populated as of the latest clarification:
- financial-futures coverage should not be assumed from the current non-equity bucket
- non-equity Business Layer now explicitly uses:
  - commodity
  - metal
  - precious_metal
  - black_chain
- category-family coverage is still incomplete in places (for example precious_metal remains small; financial-futures roots are still absent from current accessible source truth)
- archive index coverage is not explicitly represented in current archive target lists

### Archive backfill truth
Archive progression is uneven:
- stock minute / 15min relatively advanced to `2026-04-15`
- macro relatively advanced to `2026-04-16`
- current practical non-equity intraday bucket is a mixed industrial/commodity/metals/precious-metal source universe
- this should not be read as financial-futures coverage
- futures minute / 15min only to `2025-09-12`
- commodity minute / 15min only to `2025-06-16`
- precious_metal minute / 15min only to `2025-06-16`

A second-pass archive run producing 0 rows can be a truthful checkpoint-continuation result rather than a failure.

## 7. Formal vs Residual Runtime Chains

### Formal chain
- unified production/runtime chain:
  - `python -m ifa_data_platform.runtime.unified_daemon --loop`

### Manual worker chain
- `python -m ifa_data_platform.runtime.unified_daemon --worker <lowfreq|midfreq|highfreq|archive>`

### Residual / compatibility chains
- `lowfreq.daemon`
- `midfreq.daemon`
- `highfreq.daemon`
- legacy archive-specific module paths

These remain in the repo but are not the official long-running runtime model.

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
