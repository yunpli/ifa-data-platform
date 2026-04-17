# Runtime Survivability and Preflight Hardening

_Date: 2026-04-17_1658_

## Scope
This batch hardened restart safety and production survivability for the unified runtime daemon.

Goals:
1. replace the fragile harness-tied bring-up path with a more survivable local bring-up method
2. add startup preflight / dirty-state classification and repair
3. make the bring-up path operator-visible, testable, and documented

No daemon restart was performed in this batch.
The goal here was to engineer the safer flow first.

Artifacts / code:
- `scripts/runtime_preflight.py`
- `scripts/unified_daemon_service.sh`
- `artifacts/runtime_preflight_validation_2026-04-17_1650.json`
- `artifacts/service/runtime_preflight_latest.json`
- `tests/integration/test_runtime_preflight.py`

---

## 1. Why the old bring-up path was fragile
The old production bring-up used the current OpenClaw/lobster exec background-session path.
That path proved fragile because:
- the unified daemon lived under the harness/session lifecycle
- prior evidence showed the daemon process died with external `SIGKILL`
- when that happened, there was no automatic recovery path

So the old path was not sufficiently survivable for a 24x7 daemon.

---

## 2. New bring-up method
### New official bring-up path
A repo-owned service wrapper now exists:
- `scripts/unified_daemon_service.sh`

Supported commands:
- `zsh scripts/unified_daemon_service.sh preflight`
- `zsh scripts/unified_daemon_service.sh start`
- `zsh scripts/unified_daemon_service.sh status`
- `zsh scripts/unified_daemon_service.sh stop`

### How it avoids the old harness-tied path
The service wrapper starts the daemon via:
- `nohup ... &`
- with PID file under `artifacts/service/unified_daemon.pid`
- stdout/stderr logs under `artifacts/service/`

Meaning:
- daemon start is no longer defined as “OpenClaw exec background session is the service”
- instead, the repo now owns a repeatable detached local bring-up path

This is materially safer than the old harness-tied start path.

### Truthful limitation
This is still not a full OS-native service manager such as `launchd/systemd`.
But it is a real detached local bring-up path and is materially less fragile than the old chat/harness background session model.

---

## 3. Startup preflight summary
### Preflight script
- `scripts/runtime_preflight.py`

### What it checks
#### Runtime state
- stale `runtime_worker_state.active_run_id`
- stale `active_started_at` older than threshold

#### Archive checkpoints
- `archive_checkpoints.status = 'in_progress'`
- aged/stale `in_progress` rows that indicate abnormal termination residue

#### Catch-up backlog/control rows
- `archive_target_catchup.status in ('pending','observed')`
- age / reason / checkpoint linkage

### Restart-safe policy
#### Auto-repairable
1. stale active runtime markers
   - auto-cleared if active age exceeds threshold
2. stale archive checkpoints stuck in `in_progress`
   - auto-marked to `abandoned` if stale beyond threshold

#### Report-only / no destructive auto-clean
1. `archive_target_catchup` rows in `pending` / `observed`
   - reported and classified
   - not automatically deleted or force-flipped in this batch

### Why this policy is truthful
- stale active runtime markers and stale `in_progress` checkpoints are classic abnormal-termination residue and are directly restart-dangerous
- catch-up backlog rows may represent valid work intent, so they are reported, not blindly destroyed

---

## 4. Dirty-state handling summary
### What was found in validation
Preflight validation found:
- 2 stale archive checkpoints still marked `in_progress`
- 7 stale catch-up rows in `pending` / `observed`
- 0 stale active runtime markers

### What was auto-repaired
Auto-repaired:
- `stock_15min_history` checkpoint: `in_progress -> abandoned`
- `test_resume_dataset` checkpoint: `in_progress -> abandoned`

### What was only reported
Reported-only:
- `stock_daily_catchup` observed row for `399999.SZ`
- multiple `macro / minute / CN_M2` pending catch-up rows

These remain visible for operator classification and future targeted cleanup/processing.

---

## 5. Validation / tests
### Preflight validation run
Executed:
- `python scripts/runtime_preflight.py --repair --out artifacts/runtime_preflight_validation_2026-04-17_1650.json`

Observed summary:
- `total_findings = 9`
- `stale_runtime_active = 0`
- `in_progress_checkpoints = 2`
- `catchup_pending_or_observed = 7`

### Service wrapper validation
Executed:
- `zsh scripts/unified_daemon_service.sh status`
- `zsh scripts/unified_daemon_service.sh preflight`

Truth:
- service wrapper correctly reports `not_running` when daemon is not up
- preflight writes operator-visible JSON and reflects repaired/remaining dirty state

### Tests
Executed:
- `pytest -q tests/integration/test_runtime_preflight.py`

Result:
- `2 passed`

---

## 6. Durable doc update
Updated durable operator/runtime context:
- `docs/DEVELOPER_COLLECTION_CONTEXT.md`

It now makes the official production-safe path explicit:
- preflight
- start
- status
- stop

rather than leaving the production bring-up path ambiguous.

---

## 7. Final truthful judgment
### Materially improved now
Yes.
Production restart safety is materially improved because:
1. daemon bring-up now has a repo-owned detached local service wrapper
2. startup preflight now classifies and repairs restart-dangerous dirty state
3. stale `in_progress` checkpoint residue is no longer left as purely manual tribal cleanup
4. operator-visible preflight JSON exists
5. tests and validation were run

### What is still not claimed
- this batch does not claim full OS-level supervision/restart recovery yet
- this batch does not claim all catch-up backlog rows are automatically resolvable

### Bottom line
The runtime is now meaningfully more survivable and restart-safe than before.
The official bring-up path is no longer “start it under the harness and hope.”
Instead, it is:
- preflight
- detached start
- explicit status/stop
with concrete dirty-state handling before start.
