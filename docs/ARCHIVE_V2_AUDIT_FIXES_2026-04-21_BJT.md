# Archive V2 Audit Fixes — 2026-04-21 (BJT)

## Scope
This batch closes the confirmed Archive V2 production-audit bugs found on 2026-04-21.

## What changed

### 1) True dry-run isolation
- `dry_run=true` no longer persists Archive V2 profile truth.
- `dry_run=true` no longer mutates completeness truth or repair-queue truth.
- archive data writes are now gated by `write_enabled and not dry_run`.
- run evidence is still recorded, but now explicitly marked with `ifa_archive_runs.dry_run=true`.

### 2) Operator-visible write semantics
- `ifa_archive_run_items.rows_written` / `tables_touched` now mean **actual persisted final writes**.
- `ifa_archive_run_items.would_write_rows` / `would_write_tables` now mean **simulated/requested writes**.
- operator recent-run / repair-history surfaces expose the distinction so dry-run and real-run are not conflated.

### 3) Historical multi-day execution is trading-day aware
- `date_range` and `backfill` now switch to trading-day selection when the requested families are market-calendar families.
- the multi-day historical path no longer blindly walks calendar days for Archive V2 daily market families.

### 4) Historical calendar robustness
- historical trading-day selection now merges:
  - `ifa2.trade_cal_current` open days
  - observed dates from `ifa2.index_daily_bar_history`
- this avoids blindly trusting stale/broken DB calendar truth for audited historical windows.
- if neither source has data, Archive V2 falls back to weekday-only behavior as the last-resort safety net.

### 5) Run lifecycle hardening
- every new Archive V2 run now auto-closes older stale `running` rows as `aborted` with end-time/duration/error notes.
- validated path: a later execution cannot silently leave older Archive V2 run truth stuck at `running`.

### 6) Family completeness visibility
- family-level completeness metrics are extracted when notes include `expected=... actual=... coverage=...`.
- persisted into completeness/run-item truth:
  - `family_expected_rows`
  - `family_observed_rows`
  - `family_coverage_ratio`
- operator gap/family/date views now surface the family-coverage picture directly.

## Operator interpretation
- Beijing-time schedule framing remains unchanged for production windows.
- For dry-run/operator review:
  - use `rows_written` / `tables_touched` for what truly persisted
  - use `would_write_rows` / `would_write_tables` for simulation intent
- For family-level incomplete cases like `sector_performance_daily`, review `family_expected_rows`, `family_observed_rows`, and `family_coverage_ratio` in operator views.

## Residual caveat
- The historical fallback remains weekday-only if both `trade_cal_current` and `index_daily_bar_history` are absent for the requested window. That is materially safer than the prior behavior, but the strongest path is still to keep at least one authoritative historical trading-day source populated.
