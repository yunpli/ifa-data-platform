# Unified Runtime Daemon Implementation Plan

_Date: 2026-04-16 06:50_

## Objective
Move the collection layer toward **one unified runtime / data-collector daemon entry** that becomes the primary operational entry for the whole data collection system.

Target worker domains under the unified daemon:
1. lowfreq worker
2. midfreq worker
3. highfreq worker
4. archive worker

This implementation must support:
- one unified **manual** runtime entry
- one unified **automatic loop/service** entry
- one central schedule model
- one central execution-record model
- truthful timeout / overlap / overdue governance
- operator-facing status/query surfaces suitable for future management UI

---

## Current truth before this batch
The current architecture is hybrid and operationally closer to multiple lane-specific daemons:
- `lowfreq/daemon.py` owns lowfreq schedule loop
- `midfreq/daemon.py` owns midfreq schedule loop
- `highfreq/daemon.py` owns highfreq schedule loop
- archive owns archive-specific orchestrator/runtime path
- `runtime/unified_runtime.py` already exists, but is mainly a bounded manual/operator-facing execution + evidence substrate

Therefore, the gap is not cosmetic. It is a real runtime operating-model consolidation.

---

## Architectural target for this batch
This batch will implement a **central unified runtime daemon layer** with the following roles:

### 1. Central runtime daemon entry
New unified daemon entry should own:
- schedule loading
- current-time evaluation
- worker dispatch decision
- trigger mode handling (`manual`, `scheduled`)
- execution record lifecycle
- overlap / timeout / overdue marking
- operator-facing status view

### 2. Four worker-domain adapters
The unified daemon will invoke four worker domains through explicit worker adapters:
- lowfreq adapter
- midfreq adapter
- highfreq adapter
- archive adapter

Important design principle:
- lane-specific code may still exist internally during transition
- but the **main operational entry** becomes the unified runtime daemon
- legacy lane daemons become transitional/internal compatibility surfaces, not the primary future model

### 3. Central schedule model
Schedule state should be unified under runtime governance.

This batch target:
- define a central DB-backed runtime schedule table/model
- support loading effective schedule rows for all four workers
- keep schedule state readable/queryable centrally
- allow fallback/default schedule seeding from current code/config truth where needed

If some lanes still derive defaults from existing config structures, that truth must be:
- normalized into one runtime schedule representation
- queryable centrally
- documented clearly as config-seeded vs DB-authored

### 4. Central execution record model
Every worker execution must produce a centralized execution record containing at minimum:
- worker_type / lane
- run_id
- trigger_mode (`manual` / `scheduled`)
- schedule key / window key when applicable
- start time
- end time
- duration
- status (`running`, `succeeded`, `failed`, `partial`, `degraded`, `timed_out`, `skipped`, `overlap_conflict`)
- concrete tasks executed
- tables updated
- outputs / row counts / summaries
- errors

This record becomes the basis for future runtime management page / operator console.

### 5. Timeout / overlap governance
Unified daemon must govern:
- runtime budget by worker
- overdue / timed_out truth marking
- overlap/conflict detection when next slot arrives while prior run is still active
- policy outcome per worker schedule:
  - wait
  - skip
  - retry
  - degrade
  - overlap_conflict

This batch will implement DB-backed policy/evidence for these outcomes.

---

## Implementation strategy

### Phase A — DB/runtime governance foundation
Add DB-backed tables for:
- unified runtime schedules
- unified runtime worker state / latest state
- unified runtime execution events or richer execution records

Use these to support:
- schedule query
- last/next run visibility
- active-run visibility
- timeout / overlap marking

### Phase B — worker adapter layer
Create explicit worker adapters mapping unified daemon → lane execution:
- lowfreq adapter uses current lowfreq execution path
- midfreq adapter uses current midfreq execution path
- highfreq adapter uses current highfreq execution path
- archive adapter uses current archive execution path

Adapters should return normalized execution summaries.

### Phase C — unified manual entry
Support operator command shape conceptually like:
- run one worker manually via unified entry
- optionally choose group/window semantics later

Manual invocation must still generate the same central execution record model.

### Phase D — unified loop/service entry
Implement a unified daemon loop that:
- loads effective schedule set
- evaluates Beijing-time schedule points
- determines which worker(s) are due
- enforces overlap/timeout policy
- dispatches workers
- records execution outcomes centrally

### Phase E — operator-facing status/history surfaces
Provide central status/health/history methods for:
- configured schedules
- current worker states
- active run(s)
- recent run history
- next due windows if computable

---

## Transitional truth / non-fake constraints
This batch should not fake full final convergence if not yet complete.
Truthful expected outcome after this batch:
- unified runtime daemon becomes the **real primary operating entry** for manual and scheduled execution
- lane-specific daemons may still remain in repo as transitional/internal compatibility paths
- some schedule defaults may still originate from code/config but must now flow through the central runtime schedule model
- future cleanup can demote/remove legacy direct daemon entrypoints once fully stabilized

---

## Acceptance criteria for this batch
1. Already-accepted previous work pushed to remote first. ✅
2. New timestamped design/execution markdown created. ✅
3. New unified runtime daemon code landed.
4. Central schedule model landed and queryable.
5. Central execution-record model materially strengthened and queryable.
6. Manual unified entry works for each worker domain.
7. Automatic unified loop/service path works from the same daemon entry.
8. Tests cover manual dispatch, scheduled trigger selection, overlap/timeout governance, and central record persistence.
9. Runtime/DB evidence proves the new operating model truthfully.

---

## Planned artifacts
Expected artifact classes from this batch:
- migration(s)
- runtime daemon module(s)
- worker adapter module(s)
- schedule/state store module(s)
- tests (unit/integration)
- timestamped implementation evidence markdown

