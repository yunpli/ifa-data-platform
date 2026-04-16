# Unified Runtime Convergence + Schedule/Trading-Calendar Redesign

_Date: 2026-04-16_0737_

## Scope of this batch
This batch combines:
1. runtime daemon convergence
2. schedule / trading-calendar redesign and clarification

Target outcome:
- one unified runtime daemon as the sole official long-running entry
- four workers underneath it: lowfreq / midfreq / highfreq / archive
- DB-backed trading-calendar truth for runtime day classification
- operator-readable schedule model for trading day / non-trading weekday / Saturday / Sunday
- centralized runtime budget / timeout governance

## Code artifacts changed
- `src/ifa_data_platform/runtime/unified_daemon.py`
- `src/ifa_data_platform/runtime/trading_calendar.py`
- `src/ifa_data_platform/runtime/schedule_policy.py`
- `src/ifa_data_platform/lowfreq/daemon.py`
- `src/ifa_data_platform/midfreq/daemon.py`
- `src/ifa_data_platform/highfreq/daemon.py`
- `src/ifa_data_platform/lowfreq/__init__.py`
- `alembic/versions/035_runtime_schedule_policy_redesign.py`
- `tests/integration/test_unified_runtime_daemon.py`

## Passing tests
Command:
- `python3 -m pytest -q tests/integration/test_unified_runtime_daemon.py`

Result:
- `5 passed, 72 warnings in 0.52s`

## Migration state
Command:
- `python3 -m alembic current`

Result:
- `035_runtime_schedule_policy (head)`

## Runtime convergence result
### Official long-running runtime entry
Official long-running production entry is now explicitly:
- `python3 -m ifa_data_platform.runtime.unified_daemon --loop`

This is also surfaced by unified daemon status under:
- `official_long_running_entry`

### Lane-specific daemon status after convergence
- `lowfreq.daemon`
- `midfreq.daemon`
- `highfreq.daemon`

These have been demoted into compatibility/manual wrappers.
They are no longer acceptable as primary long-running production entries.
If `--loop` is used on them, they exit with a demotion message pointing to the unified daemon.

### Direct/manual worker execution preserved
Manual worker execution is preserved through the unified daemon:
- `python3 -m ifa_data_platform.runtime.unified_daemon --worker lowfreq`
- `python3 -m ifa_data_platform.runtime.unified_daemon --worker midfreq`
- `python3 -m ifa_data_platform.runtime.unified_daemon --worker highfreq`
- `python3 -m ifa_data_platform.runtime.unified_daemon --worker archive`

Bounded validation remains available via:
- `--dry-run-manifest-only`

Manual runtime-budget override remains available via:
- `--runtime-budget-sec <n>`

## Centralized runtime-budget / timeout model
Default centralized budgets:
- lowfreq: 1800 sec
- midfreq: 1800 sec
- highfreq: 900 sec
- archive: 3600 sec

Behavior:
- scheduled runs inherit runtime budget from central schedule rows
- manual runs may override via CLI
- overlap state is checked centrally through `ifa2.runtime_worker_state`
- overdue active runs can be marked `timed_out`
- overlap before timeout can be marked `overlap_conflict`
- governance truth is written centrally to `ifa2.unified_runtime_runs`

## Trading-day logic
### Current truthful path
Runtime day classification is now explicit and DB-backed through:
- `src/ifa_data_platform/runtime/trading_calendar.py`
- table: `ifa2.trade_cal_current`

Decision rules:
- Saturday -> `saturday`
- Sunday -> `sunday`
- weekday + `is_open=1` in `ifa2.trade_cal_current` -> `trading_day`
- weekday + `is_open=0` -> `non_trading_weekday`
- if DB row is missing -> fallback to `fallback_weekday_only`

### Observed runtime truth in this batch
Unified daemon status showed:
- `runtime_day_type = non_trading_weekday`
- `trading_day_status.source = ifa2.trade_cal_current`

This means runtime schedule gating is now explicitly tied to persisted calendar truth rather than vague lane-local assumptions.

## Final schedule model by day type
### trading_day
- lowfreq `07:20`
  - purpose: refresh calendar/reference/fundamental support before early report
- highfreq `09:15`
  - purpose: pre-open/auction support for trading-day early report
- highfreq `11:25`
  - purpose: intraday support approaching midday report
- midfreq `11:45`
  - purpose: support midday report snapshot after morning session
- highfreq `14:57`
  - purpose: close/auction support for late report
- midfreq `15:20`
  - purpose: support late report and close data
- archive `21:30`
  - purpose: daily archive and backlog absorption after market/reporting cycle

### non_trading_weekday
- lowfreq `08:30` enabled
  - purpose: refresh slow/reference data on non-trading weekday
- midfreq disabled
  - purpose: no regular midfreq reporting cadence on non-trading weekday
- highfreq disabled
  - purpose: no highfreq market session on non-trading weekday
- archive `21:30` enabled
  - purpose: archive/catch-up still runs on non-trading weekdays

### saturday
- lowfreq `09:00` enabled
  - purpose: support Saturday weekly review / past-week recap
- midfreq `10:30` enabled
  - purpose: support weekly review dataset refresh
- highfreq disabled
  - purpose: no highfreq weekend session
- archive `21:30` enabled
  - purpose: archive/catch-up continues on Saturday

### sunday
- lowfreq `09:00` enabled
  - purpose: support Sunday next-week preview/setup
- midfreq `10:30` enabled
  - purpose: refresh swing/close-support data for next-week preview
- highfreq disabled
  - purpose: no highfreq weekend session
- archive `21:30` enabled
  - purpose: archive/catch-up continues on Sunday

## Final lane behavior by business day type
### lowfreq
- trading day: yes
- non-trading weekday: yes
- Saturday: yes
- Sunday: yes

Why:
- lowfreq supports reference / slower-moving / report-support workflows, including off-market review and preview work.

### midfreq
- trading day: yes
- non-trading weekday: no regular cadence
- Saturday: yes
- Sunday: yes

Why:
- midfreq supports midday/late trading-day reporting and also weekend review/preview refresh, but does not need a normal non-trading weekday cadence.

### highfreq
- trading day: yes
- non-trading weekday: no
- Saturday: no
- Sunday: no

Why:
- highfreq is market-session driven and should not pretend to have a meaningful off-market weekend cadence.

### archive
- trading day: yes
- non-trading weekday: yes
- Saturday: yes
- Sunday: yes

Why:
- archive is operationally daily and supports catch-up / retention / post-cycle storage every day.

## DB/runtime evidence
### Manual-mode evidence in this batch
Validated through unified daemon manual worker path with explicit runtime budgets:
- lowfreq manual: `--runtime-budget-sec 1200`
- midfreq manual: `--runtime-budget-sec 1500`
- highfreq manual: `--runtime-budget-sec 600`
- archive manual: `--runtime-budget-sec 2400`

Observed persisted central run rows included:
- lowfreq manual succeeded with `runtime_budget_sec=1200`
- midfreq manual succeeded with `runtime_budget_sec=1500`
- highfreq manual succeeded with `runtime_budget_sec=600`
- archive manual succeeded with `runtime_budget_sec=2400`

### Scheduled evidence
Observed central scheduled run evidence included:
- highfreq scheduled run
- `schedule_key=highfreq:pre_open_0915`
- `trigger_mode=scheduled`
- `runtime_budget_sec=900`
- `governance_state=ok`
- `status=succeeded`

### Central tables now actively used
- `ifa2.runtime_worker_schedules`
- `ifa2.runtime_worker_state`
- `ifa2.unified_runtime_runs`
- `ifa2.trade_cal_current`

## Exact manual mode after this batch
Manual mode now means:
1. operator invokes unified daemon with `--worker <lane>`
2. optional `--runtime-budget-sec` overrides the default budget
3. optional `--dry-run-manifest-only` bounds validation work
4. unified daemon dispatches the worker
5. centralized run evidence is written
6. centralized worker-state row is updated

## Exact automatic mode after this batch
Automatic mode now means:
1. service/operator runs `python3 -m ifa_data_platform.runtime.unified_daemon --loop`
2. daemon determines Beijing runtime day type from DB-backed trading calendar truth
3. daemon loads central schedule policy from `ifa2.runtime_worker_schedules`
4. daemon dispatches due worker slots
5. budgets / overlap / timeout governance are centrally recorded
6. status/history remain queryable through unified runtime tables

## Final daemon/worker relationship after convergence
Top-level official runtime:
- unified runtime daemon

Workers underneath it:
- lowfreq worker
- midfreq worker
- highfreq worker
- archive worker

Legacy lane daemons:
- compatibility/manual wrappers only
- not official long-running production entry points anymore

## Truthful judgment
### Unified daemon convergence status
- implemented at the operational-entry level
- unified daemon is now the sole official long-running runtime model
- lane long-running loops are demoted

### Schedule redesign status
- implemented and documented
- day-type schedule model is explicit
- trading-calendar truth is DB-backed
- Saturday / Sunday behavior is explicitly defined

### Remaining truthful limitation
- some underlying lane-specific execution internals still exist beneath unified dispatch
- but they are no longer exposed as competing official long-running runtime entry models
- the key operational ambiguity has been removed
