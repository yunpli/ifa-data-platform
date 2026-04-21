# H/M/L Scope + Tushare Alignment (2026-04-20 23:48 PDT / 北京时间 2026-04-21 14:48)

## What changed

### 1. Scope routing
- `highfreq` now only consumes `key_focus` families.
- `midfreq` and `lowfreq` consume `focus` + `key_focus` families.
- `archive` scope is frequency-aware and derived from the same Business Layer manifest instead of hardcoded symbol lists.

### 2. Minute/intraday source rules
- `stock` / `etf` highfreq 1m -> `stk_mins`
- `index` highfreq 1m -> `idx_mins`
- futures-family minute/highfreq/archive -> `ft_mins`
- futures-family live contract selection is resolved by `runtime.contract_resolver.ContractResolver` from focus/key-focus aliases into current live `ts_code` via `fut_basic`.

### 3. Midfreq Tushare endpoint corrections
- `limit_up_down_status` -> `limit_list_ths`
- `limit_up_detail` -> `limit_list_d`
- `turnover_rate` remains `daily_basic`
- `sector_performance` remains `ths_index -> ths_daily`

### 4. Runtime duplicate/overlap governance
- `runtime.unified_daemon` now takes a PostgreSQL advisory lock per worker before dispatch.
- This suppresses duplicate multi-process scheduled entry in addition to the existing active-run state checks.

### 5. Current/history duplication guard
- `midfreq.runner._persist_current_to_history()` now inserts only rows not already present for the same `version_id` + business key.
- This prevents repeated promotion/history-copy duplication when reruns happen against the same version snapshot.

## Operator notes
- All schedule semantics should be discussed in **Beijing time**. The daemon schedule table already stores `beijing_time_hm` and `timezone=Asia/Shanghai`.
- No runtime daemon restart was performed as part of this implementation batch.
- To inspect the normalized manifest:
  - `python3 - <<'PY'`
  - `from ifa_data_platform.runtime.target_manifest import build_target_manifest`
  - `print(build_target_manifest().item_count)`
  - `PY`
- To dry-run a worker through unified runtime:
  - `python3 -m ifa_data_platform.runtime.unified_daemon --worker highfreq --dry-run-manifest-only`
  - `python3 -m ifa_data_platform.runtime.unified_daemon --worker midfreq --dry-run-manifest-only`

## Files touched for this batch
- `src/ifa_data_platform/runtime/target_manifest.py`
- `src/ifa_data_platform/runtime/contract_resolver.py`
- `src/ifa_data_platform/runtime/unified_daemon.py`
- `src/ifa_data_platform/highfreq/adaptor_tushare.py`
- `src/ifa_data_platform/highfreq/runner.py`
- `src/ifa_data_platform/midfreq/adaptors/tushare.py`
- `src/ifa_data_platform/midfreq/runner.py`
- `src/ifa_data_platform/archive/archive_policy.py`
- `src/ifa_data_platform/archive/archive_orchestrator.py`
