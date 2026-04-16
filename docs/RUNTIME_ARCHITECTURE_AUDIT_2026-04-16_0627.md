# Runtime Architecture Audit

_Date: 2026-04-16 06:27 _

## Purpose
This document audits the **current real runtime architecture** in the repo, with one goal:

Determine whether the system is already a single unified runtime daemon architecture, or whether it is still primarily multiple lane-specific daemons with a unified runtime used for manual/operator entry.

The audit is based on current repo code structure, current daemon/orchestrator implementations, and the accepted runtime behavior already landed.

---

## Short answer
The current system is **not** a single unified runtime daemon that centrally schedules and triggers all lanes.

The current real architecture is closest to:

**C — a hybrid state, but operationally much closer to B.**

More explicitly:
- lowfreq has its own daemon
- midfreq has its own daemon
- highfreq has its own daemon
- archive has its own archive runtime/orchestrator path, but not yet a comparable standalone daemon loop in the same mature sense as lowfreq/midfreq/highfreq
- unified runtime is primarily a **manual/operator-facing one-shot execution and evidence layer**, not the single long-running scheduling center

So if forced to choose the closest simplified answer, the most truthful one is:

**B — multiple lane-specific daemons + unified runtime mainly serving one-shot/operator entry**

with the nuance that the system is **hybridized** because unified runtime already normalizes execution records and lane dispatch for manual runs.

---

## 1. Is lowfreq currently an independent daemon?
**Yes.**

### Evidence from code
`src/ifa_data_platform/lowfreq/daemon.py` contains:
- a daemon CLI
- `run_once(...)`
- `run_loop(...)`
- signal handling
- schedule matching logic
- health surface

This is a real lane-specific daemon implementation.

### Operational meaning
Lowfreq can run independently of unified runtime as its own long-running scheduled process.

---

## 2. Is midfreq currently an independent daemon?
**Yes.**

### Evidence from code
`src/ifa_data_platform/midfreq/daemon.py` contains:
- a daemon CLI
- `run_once(...)`
- `run_loop(...)`
- health / watchdog surfaces
- schedule-window logic
- independent orchestration path

This is also a real lane-specific daemon implementation.

### Operational meaning
Midfreq can run independently of unified runtime as its own long-running scheduled process.

---

## 3. Is highfreq currently an independent daemon?
**Yes.**

### Evidence from code
`src/ifa_data_platform/highfreq/daemon.py` now contains:
- daemon CLI
- `run_once(...)`
- `run_loop(...)`
- `--health`
- `--watchdog`
- `--status`
- `--retention-run`
- schedule matching logic
- DB-backed schedule state and execution summary wiring

This is a real lane-specific daemon implementation.

### Operational meaning
Highfreq now has its own independent daemon/service substrate and is not waiting for a unified runtime daemon to trigger it.

---

## 4. Does archive currently have its own daemon / archive runtime loop?
**Not in the same way as lowfreq / midfreq / highfreq.**

### What archive does have
Archive has:
- `archive_config.py`
- `archive_orchestrator.py`
- checkpoint progression logic
- target-delta / catch-up logic
- unified runtime archive lane integration
- operator/status surfaces (`archive-status`)

### What archive does not have right now
Archive does **not** currently present as a fully parallel standalone daemon loop file with the same mature pattern as:
- `lowfreq/daemon.py`
- `midfreq/daemon.py`
- `highfreq/daemon.py`

So archive has its own runtime/orchestrator path, but not the same explicit independent daemon loop abstraction as the other three lanes.

### Practical conclusion
Archive is independently orchestrated, but it is not currently a fully symmetric standalone daemon in the same style as lowfreq/midfreq/highfreq.

---

## 5. What role does unified runtime currently play?
The current unified runtime is primarily:

- a **manual/operator-facing one-shot execution layer**
- a **lane-dispatch layer** for manual runs
- a **normalized run-evidence layer**
- a **shared manifest/snapshot layer**
- a **shared operator-status/run-history surface**

It is **not yet** the single long-running scheduling center for the whole system.

### Evidence from code
`src/ifa_data_platform/runtime/unified_runtime.py` does all of the following:
- takes a lane (`lowfreq`, `midfreq`, `archive`, `highfreq`)
- builds/uses the manifest snapshot
- chooses datasets/jobs for that lane
- executes the lane through runner/orchestrator integrations
- writes normalized run records into `unified_runtime_runs`
- exposes normalized run-status semantics

### But what it does not do
It does not itself run as the one central daemon that:
- wakes up every minute
- decides which lane should fire next
- triggers all lane workers centrally
- owns the only scheduling loop for the whole system

That job is still distributed across lane-specific daemon loops.

So the truthful summary is:

**Unified runtime is already a unified execution/evidence layer, but not yet a unified scheduling daemon.**

---

## 6. Which architecture is the current system closest to?
### Best matching answer
**C — a hybrid state, but functionally closest to B.**

### Why not A?
A would mean:
- one unified runtime daemon
- one central schedule brain
- lowfreq/midfreq/highfreq mostly behaving as worker/lane handlers under that one daemon

That is **not** the current code reality.

### Why not pure B without qualification?
Because unified runtime already does more than a thin wrapper:
- it normalizes run records
- it normalizes operator-facing run evidence
- it dispatches lane execution in a shared way for manual/operator runs
- it already acts like a unifying execution substrate

So the strictest truthful wording is:

**The current architecture is hybrid, but the operational scheduling model is still much closer to B than to A.**

---

## 7. If current architecture is not “one unified runtime daemon”, what is it actually?
### Current real architecture
The current real architecture is:

- **lane-specific daemons for lowfreq / midfreq / highfreq**
- **archive-specific orchestrator/runtime path**
- **unified runtime as shared one-shot/operator/evidence substrate**

More concretely:
- lowfreq owns its own daemon schedule logic
- midfreq owns its own daemon schedule logic
- highfreq owns its own daemon schedule logic
- archive owns its own archive orchestration and checkpoint/catch-up path
- unified runtime provides a common manual run path and a common normalized run record/status model

### Gap vs target architecture
If the target architecture is:

> one unified runtime daemon that centrally schedules all lanes and triggers lane workers

then the current gap is:
- scheduling is still lane-local, not centrally unified
- health/watchdog logic is still lane-local, not centrally unified
- cadence logic is still lane-local, not centrally unified
- the unified runtime does not yet own the single global event loop / scheduler

### How to classify that gap?
Most truthfully, this gap is:
- partly **historical design inheritance** from how lowfreq and midfreq were built first
- partly an **intentional staged evolution**, because unified runtime was first landed as shared manual/evidence substrate before becoming a possible future central scheduler

### Is this small change or structural refactor?
This is **structural refactor territory**, not a tiny patch.

Why:
- it would require centralizing schedule ownership
- centralizing trigger logic
- centralizing watchdog/health semantics
- deciding whether lane daemons become workers or remain optional local executors
- reconciling archive timing/orchestration with a unified central scheduler model

So the move from current architecture to “one unified runtime daemon triggers all lanes” is **not a small tweak**. It is an architectural consolidation project.

---

## 8. Lane-by-lane code reality
### Unified runtime
Current role:
- manual/operator-facing one-shot execution
- manifest + snapshot normalization
- lane dispatch for manual runs
- normalized run evidence and status

Not current role:
- single global scheduler daemon

### Lowfreq
Current role:
- independent daemon
- own schedule logic
- own orchestrator
- own runner
- DB-backed daemon/group state
- health surface

### Midfreq
Current role:
- independent daemon
- own schedule-window logic
- own orchestrator
- own runner
- DB-backed daemon/window/execution summary state
- health/watchdog surfaces

### Highfreq
Current role:
- independent daemon
- own schedule-window logic
- own orchestrator
- own runner
- DB-backed daemon/window/execution summary state
- health/watchdog/status/retention surfaces

### Archive
Current role:
- own archive orchestrator and checkpoint/catch-up system
- own archive job config
- own archive status surface
- integrated into unified runtime for manual/operator runs

Not current role:
- not yet a fully symmetric standalone daemon loop in the same style as lowfreq/midfreq/highfreq

---

## Final conclusion
### Is the current system “one unified runtime daemon”? 
**No.**

### What is the most truthful current runtime architecture?
The system is currently:

**multiple lane-specific daemons (lowfreq / midfreq / highfreq), plus archive-specific runtime/orchestration, with unified runtime acting as a shared one-shot/operator/evidence layer.**

### Closest architecture label
**Closest answer: C (hybrid), operationally closer to B than A.**

### What that means in one sentence
The system already has a unified execution/evidence surface, but it does **not** yet have a single unified scheduling daemon controlling all lanes.
