# Highfreq Milestone 3 — Schedule / Cadence Implementation

_Date: 2026-04-16 04:02 _

## 1. Purpose of the batch
- Implement real highfreq time-node / daemon-trigger logic.
- Add DB-backed schedule state, execution summaries, health, and watchdog semantics.
- Validate key node windows plus 10-minute light refresh cadence.

## 2. What was supposed to be done
- Implement the required highfreq business-time nodes:
  - 09:15
  - 09:20–09:25 auction window
  - pre-briefing final update / 09:26–09:28 closeout
  - 09:30
  - 09:45
  - 10:15
  - 10:30
  - 11:00
  - 11:25 / 11:30
  - 13:30
  - 14:00
  - 14:30
  - 14:45
  - 14:57–15:00
  - 15:05 final close confirmation
  - plus 10-minute light refresh cadence
- Implement delayed / degraded / partial marking with:
  - target <= 1 minute
  - upper bound <= 2 minutes
- Add daemon/service persistence and operator-readable state surfaces.

## 3. What was actually done
### Schedule/state schema landed
Added DB-backed highfreq schedule/service tables:
- `ifa2.highfreq_daemon_state`
- `ifa2.highfreq_window_state`
- `ifa2.highfreq_execution_summary`

### Schedule-memory / operator surfaces landed
Added:
- `highfreq/schedule_memory.py`
- `highfreq/summary_persistence.py`

These give highfreq a real DB-backed schedule-memory pattern instead of a stateless time match.

### Daemon/runtime behavior landed
Upgraded `highfreq/daemon.py` and `highfreq/daemon_orchestrator.py` so that highfreq now has:
- DB-backed daemon heartbeat/state updates
- window-level persisted run state
- execution summary persistence
- 10-minute light refresh recognition during intraday hours
- window skip behavior when a non-refresh window already succeeded today
- SLA marking:
  - `ok`
  - `degraded`
  - `delayed`
  - `partial`

### Real issues found and fixed in-batch
1. **Daemon orchestrator run_id bug**
- initial daemon path called `HighfreqRunner` without a UUID run_id
- that broke `dataset_versions.run_id` validation before state persistence could complete
- fixed by generating a UUID run_id inside daemon group execution

2. **Health/watchdog timezone bug**
- `highfreq_daemon_state.latest_loop_at` could be read back as naive datetime
- watchdog compared it against aware UTC and crashed
- fixed by normalizing naive timestamps to UTC before elapsed-time comparison

3. **Validation command assembly bug**
- one combined shell validation command had a heredoc boundary error
- this was a command assembly issue only, not a runtime logic failure
- validation was re-run cleanly afterward

## 4. Code files changed
- `alembic/versions/031_highfreq_schedule_state.py`
- `src/ifa_data_platform/highfreq/schedule_memory.py`
- `src/ifa_data_platform/highfreq/summary_persistence.py`
- `src/ifa_data_platform/highfreq/daemon_orchestrator.py`
- `src/ifa_data_platform/highfreq/daemon.py`
- `tests/integration/test_highfreq_milestone3.py`

## 5. Tests run and results
### Migration
- `alembic upgrade head`
- result: succeeded

### Focused integration tests
- `pytest tests/integration/test_highfreq_milestone3.py -q`
- result: `2 passed`

### Direct daemon/service validation
Executed `run_once()` schedule simulations for these Asia/Shanghai nodes:
- `09:15`
- `09:20`
- `09:28`
- `09:30`
- `09:40` (light refresh)
- `10:15`
- `11:30` (light refresh / late-morning node)
- `13:30`
- `14:57`
- `15:05`

Also executed:
- `python src/ifa_data_platform/highfreq/daemon.py --health`
- `python src/ifa_data_platform/highfreq/daemon.py --watchdog`

## 6. DB/runtime evidence
### State persistence evidence
Current DB row counts after validation:
- `highfreq_daemon_state = 1`
- `highfreq_window_state = 10`
- `highfreq_execution_summary = 10`

This proves highfreq now has real daemon/window/summary persistence.

### Latest window-state evidence
Recent persisted highfreq windows include:
- `post_close_1505` -> `close_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=10004`
- `close_auction_1457` -> `close_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=7865`
- `afternoon_1330` -> `intraday_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=8836`
- `light_refresh_1130` -> `intraday_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=9348`
- `check_1015` -> `intraday_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=7335`
- `light_refresh_0940` -> `intraday_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=8021`
- `open_0930` -> `intraday_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=7450`
- `pre_open_finalize_0928` -> `pre_open_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=9446`
- `auction_window_0920` -> `pre_open_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=8969`
- `pre_open_0915` -> `pre_open_core` -> `succeeded` -> `sla_status=ok` -> `duration_ms=7792`

### Operator/service evidence
`--health` now returns a structured payload including:
- daemon name
- health status
- message
- last heartbeat
- last status
- last window type
- configured windows/groups/datasets
- loop interval and light refresh interval

`--watchdog` now returns a DB-backed concise health view using the same underlying daemon-state truth.

Current observed health truth after the synthetic validation run:
- `status = stale`
- `message = Last run 420.1 minutes ago`
- `last_window_type = post_close_1505`

This is a truthful operator signal, not a surface inconsistency.

## 7. Truthful judgment / result
### What is now real in Milestone 3
- Highfreq now has real schedule/cadence implementation, not just configured times.
- DB-backed daemon/window/execution-summary state exists.
- The key required node family is implemented structurally and validated through schedule-aware runs.
- 10-minute light refresh cadence is now real via generated `light_refresh_*` windows.
- SLA/status marking (`ok` / `degraded` / `delayed` / `partial`) is implemented.
- Operator health/watchdog surfaces now exist and work.

### What this means operationally
Highfreq is no longer only a manual/raw ingestion lane. It now has a meaningful daemon/service scheduling substrate consistent with the broader runtime style of the system.

## 8. Residual gaps / blockers / deferred items
### Residuals remaining after this batch
- The current batch validated representative nodes and light-refresh behavior, but not every single configured node was individually simulated one-by-one.
- `status = stale` in health/watchdog after the synthetic run is expected because the last persisted loop time is hours old relative to current wall time; this is truthful current-state behavior, not a bug.

### No fake completeness maintained
- This batch claims schedule/cadence substrate closure, not full end-to-end final acceptance of the entire highfreq lane.

## 9. Whether docs/runtime truth had to be corrected
Yes.
- Before this batch, highfreq had configured windows but not DB-backed schedule memory and operator-grade cadence truth.
- After this batch, highfreq schedule logic is materially real and operator-visible.
- Two real implementation bugs were discovered and fixed during the batch:
  - daemon run_id UUID wiring
  - health/watchdog timezone normalization
