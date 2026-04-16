# Unified Runtime Daemon Validation

_Date: 2026-04-16_0705_

## Passing tests
- `python3 -m pytest -q tests/integration/test_unified_runtime_daemon.py`
- Result: `4 passed, 72 warnings in 0.41s`

## Code artifacts in this batch
- `alembic/versions/034_unified_runtime_daemon_core.py`
- `src/ifa_data_platform/runtime/unified_daemon.py`
- `tests/integration/test_unified_runtime_daemon.py`
- `docs/UNIFIED_RUNTIME_DAEMON_IMPLEMENTATION_2026-04-16_0650.md`

## DB/runtime evidence
### Enabled central schedules by worker
- archive: 4 enabled schedules
- highfreq: 17 enabled schedules
- lowfreq: 3 enabled schedules
- midfreq: 7 enabled schedules

### Recent unified runtime runs
- lane=highfreq trigger=scheduled schedule_key=highfreq:pre_open_0915 governance=ok status=succeeded runtime_budget_sec=900 duration_ms=35 error_count=0 started_at=2026-04-16 07:04:49.370810 completed_at=2026-04-16 07:04:49.375136
- lane=archive trigger=manual schedule_key=archive:0730 governance=ok status=succeeded runtime_budget_sec=None duration_ms=52 error_count=0 started_at=2026-04-16 07:04:49.325904 completed_at=2026-04-16 07:04:49.330711
- lane=highfreq trigger=manual schedule_key=None governance=ok status=succeeded runtime_budget_sec=None duration_ms=35 error_count=0 started_at=2026-04-16 07:04:49.266996 completed_at=2026-04-16 07:04:49.271650
- lane=midfreq trigger=manual schedule_key=None governance=ok status=succeeded runtime_budget_sec=None duration_ms=40 error_count=0 started_at=2026-04-16 07:04:49.223363 completed_at=2026-04-16 07:04:49.228566
- lane=lowfreq trigger=manual schedule_key=None governance=ok status=succeeded runtime_budget_sec=None duration_ms=56 error_count=0 started_at=2026-04-16 07:04:49.174039 completed_at=2026-04-16 07:04:49.179442
- lane=highfreq trigger=scheduled schedule_key=highfreq:pre_open_0915 governance=ok status=succeeded runtime_budget_sec=900 duration_ms=37 error_count=0 started_at=2026-04-16 07:04:42.002065 completed_at=2026-04-16 07:04:42.006804
- lane=highfreq trigger=manual schedule_key=None governance=ok status=succeeded runtime_budget_sec=None duration_ms=57 error_count=0 started_at=2026-04-16 07:04:41.949120 completed_at=2026-04-16 07:04:41.955217
- lane=lowfreq trigger=manual schedule_key=None governance=None status=running runtime_budget_sec=None duration_ms=None error_count=0 started_at=2026-04-16 07:03:29.607732 completed_at=None

### Central worker state
- worker=archive last_schedule_key=archive:0730 last_trigger_mode=manual last_status=succeeded active_run_id=None next_due_at_utc=2026-04-16 10:30:00
- worker=highfreq last_schedule_key=highfreq:pre_open_0915 last_trigger_mode=scheduled last_status=succeeded active_run_id=None next_due_at_utc=2026-04-15 18:20:00
- worker=lowfreq last_schedule_key=None last_trigger_mode=manual last_status=succeeded active_run_id=None next_due_at_utc=2026-04-16 07:45:00
- worker=midfreq last_schedule_key=None last_trigger_mode=manual last_status=succeeded active_run_id=None next_due_at_utc=2026-04-16 16:20:00

## Exact manual mode behavior after this batch
- Entry surface: `python3 -m ifa_data_platform.runtime.unified_daemon --worker <lowfreq|midfreq|highfreq|archive>`
- Optional bounded validation mode: add `--dry-run-manifest-only`
- Manual mode always enters through the unified runtime daemon, not a lane-specific daemon entry.
- Unified daemon seeds/loads central schedule rows, then dispatches the chosen worker through the unified adapter.
- Execution record is written to `ifa2.unified_runtime_runs` and worker state to `ifa2.runtime_worker_state`.
- For `archive`, optional `--schedule-key` can stamp the manual trigger context (example used in validation: `archive:0730`).
- In bounded validation mode, worker invocation uses manifest-preview path so governance/state surfaces are exercised without unbounded collection runtime.

## Exact automatic mode behavior after this batch
- Entry surface: `python3 -m ifa_data_platform.runtime.unified_daemon --once` or `--loop`
- `--once`:
  - loads central schedule rows from `ifa2.runtime_worker_schedules`
  - evaluates current UTC mapped to Beijing time
  - selects due worker slots
  - dispatches through the same unified adapter path
  - writes centralized run/state evidence
- `--loop`:
  - repeats the same due-slot evaluation continuously at `--loop-interval-sec`
  - therefore automatic/service execution and manual execution now share one daemon entry and one governance path
- In the current hardened implementation, scheduled validation dispatch uses bounded manifest-preview mode by default to keep service governance deterministic while the broader real-run convergence continues.

## Final daemon / worker relationship after this batch
- Main operational entry added: `runtime/unified_daemon.py`
- Worker domains under it:
  - lowfreq worker
  - midfreq worker
  - highfreq worker
  - archive worker
- Central governance owned by unified daemon:
  - schedule loading / seeding
  - due-slot evaluation
  - trigger mode (`manual` / `scheduled`)
  - worker state tracking (`ifa2.runtime_worker_state`)
  - centralized execution records (`ifa2.unified_runtime_runs`)
  - runtime budget / overlap / timeout marking hooks
- Legacy lane daemons still exist in repo as transitional compatibility/internal execution surfaces.
- Therefore the post-batch architecture is:
  - **one unified runtime daemon entry is now implemented as the primary operating surface**
  - **four worker domains run underneath it through the unified adapter/governance model**
  - **lane daemons are no longer the only operational entry model, but transitional internal paths remain**

## Truthful limitation after this batch
- The unified daemon operating model is real and DB-backed.
- However, full production convergence is still transitional in one important sense:
  - scheduled path is currently validated/hardened with bounded manifest-preview dispatch by default
  - legacy lane-specific deep execution paths still exist and remain the underlying execution substrate for broader real-run behavior
- So this batch establishes the unified operating model and governance substrate cleanly, without falsely claiming that all lane-local runtime internals have already been fully deleted/converged.
