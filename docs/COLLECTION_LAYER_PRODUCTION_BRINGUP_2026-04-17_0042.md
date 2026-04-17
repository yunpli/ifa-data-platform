# Collection Layer Production Bring-up

_Date: 2026-04-17_0042_

## Scope
Final production bring-up + watchdog verification + operator/business handoff for the collection layer.

Milestones completed:
- A. anti-hang / watchdog verification
- B. final cleanup
- C. production-mode bring-up
- D. operator validation
- E. documentation / handoff

Artifacts:
- `scripts/final_production_cleanup.py`
- `artifacts/final_production_cleanup_2026-04-17_0039.json`
- `artifacts/unified_daemon_status_after_bringup_2026-04-17_0040.json`

---

## 1. Watchdog / anti-hang / stuck-run truth

### What exists now
There is now a **real DB-backed governance layer** in the unified runtime daemon for:
1. runtime-budget awareness
2. overlap prevention
3. timeout marking
4. stale-active / stale-heartbeat visibility for operators

Code location:
- `src/ifa_data_platform/runtime/unified_daemon.py`

### Exact mechanisms currently present
#### A. Timeout handling
Each worker schedule carries a runtime budget from:
- `ifa2.runtime_worker_schedules.runtime_budget_sec`

Default budgets if no override:
- lowfreq: `1800`
- midfreq: `1800`
- highfreq: `900`
- archive: `3600`

When dispatch sees an existing `active_run_id` and the active runtime age exceeds the worker budget:
- prior run is marked `timed_out`
- governance state is written as `timed_out`
- worker state is closed with timeout error context

#### B. Overlap handling
If a worker is still active and has **not yet exceeded** the runtime budget when the next scheduled slot arrives:
- new scheduled invocation is not allowed to overlap
- unified daemon writes an `overlap_conflict` governance record
- overlap policy is effectively **skip / mark conflict**

This prevents run pile-up at the scheduler level.

#### C. Active-run state
The daemon now marks worker active **before** executing the real worker path.
This closes the earlier gap where active state was only written after execution returned.

#### D. Stale/hung visibility
`--status` now exposes a `watchdog` section per worker with states such as:
- `idle`
- `active_within_budget`
- `stale_active_timeout_exceeded`
- `healthy_recent_heartbeat`
- `stale_heartbeat`

This gives operators direct DB-backed visibility into whether a worker appears stale.

### What does NOT yet exist
Be explicit:
- there is **not yet** an external OS/process supervisor that forcibly kills a truly hung inline worker from outside the daemon process
- there is **not yet** a separate restart daemon that reaps zombie worker subprocesses, because workers currently run inline inside the unified daemon process

### Production-truth judgment on anti-hang
Current protection story is:
- **yes**: runtime budgets
- **yes**: overlap prevention
- **yes**: stale/timeout marking
- **yes**: operator-visible watchdog state
- **no**: external hard kill / subprocess watchdog recovery

So the system now has a truthful governance and operator-detection layer for stuck runs, but not a full out-of-process kill/restart supervisor.

For current bring-up this is acceptable only if documented honestly, which this batch does.

---

## 2. Final cleanup executed
Cleanup helper:
- `scripts/final_production_cleanup.py`

Artifact:
- `artifacts/final_production_cleanup_2026-04-17_0039.json`

### Cleaned
- recent unified runtime run evidence
- recent job run evidence
- recent worker-run evidence
- target manifest snapshots from validation
- lowfreq raw fetch residue
- highfreq working tables
- highfreq derived-state working tables
- recent archive evidence/output residue from last 5 days

### Kept intact
- Business Layer truth/config tables
- list-family truth tables
- runtime schedule/policy truth tables
- trading calendar truth tables
- long-term reference/history truth tables
- archive checkpoints / catch-up anchors

### Why
This removed repeated validation/sanity residue without destroying production baseline truth.

---

## 3. Production-mode bring-up
### Exact bring-up command
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --loop --loop-interval-sec 60
```

### Environment
- repo: `/Users/neoclaw/repos/ifa-data-platform`
- venv: `/Users/neoclaw/repos/ifa-data-platform/.venv`

### Launch mode
- direct local background process
- current live exec session: `fast-dune`

### Runtime coverage
Unified daemon covers all four domains through one official long-running entry:
- `lowfreq`
- `midfreq`
- `highfreq`
- `archive`

---

## 4. Current runtime status summary
Live status was captured after bring-up via:
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --status
```

Artifact:
- `artifacts/unified_daemon_status_after_bringup_2026-04-17_0040.json`

### Current truth at capture time
- daemon long-running loop is active
- schedule policy is seeded and visible
- worker states are DB-backed and visible
- watchdog section is visible
- runtime day type at capture time: `non_trading_weekday`

That means current live schedule behavior at capture time is naturally dominated by:
- lowfreq offday reference refresh
- archive offday archive/catch-up
- midfreq/highfreq non-trading-day skip behavior where configured

---

## 5. Operator inspection surfaces

### Commands
#### Runtime status
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --status
```

#### Manual one-cycle due trigger
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --once
```

#### Manual worker trigger
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker lowfreq
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker midfreq
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker highfreq
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive
```

### Key DB tables
#### Runtime / status / watchdog truth
- `ifa2.runtime_worker_schedules` — schedule policy truth
- `ifa2.runtime_worker_state` — per-worker active/last/heartbeat/next_due state
- `ifa2.unified_runtime_runs` — centralized run evidence + governance status
- `ifa2.job_runs` — lower-level job/run evidence

#### Archive progression
- `ifa2.archive_runs`
- `ifa2.archive_checkpoints`
- `ifa2.archive_target_catchup`
- `ifa2.archive_summary_daily`

#### Lowfreq / midfreq / highfreq operational data
- lowfreq writes reference/current/history tables across fundamentals/reference/news/calendars
- midfreq writes current/history market-structure datasets such as daily bars, flows, limit-up detail, sector performance
- highfreq writes working/raw intraday tables + derived-state working tables

### What the watchdog surface means
From `--status`:
- `active_within_budget` = worker currently active and within runtime budget
- `stale_active_timeout_exceeded` = active run appears to have exceeded budget
- `stale_heartbeat` = no recent worker heartbeat / no recent run completion visible
- `healthy_recent_heartbeat` = recent activity seen

---

## 6. Worker/lane semantics for downstream developers

### lowfreq
Role:
- slow/reference/fundamental/news/calendar support layer

Cadence:
- premarket on trading days
- reference refresh on offdays
- weekly deep refresh on weekend support windows

Writes to:
- long-term reference/history tables (e.g. trade calendar, stock/index/fund basics, announcements, news, research, IR QA, holdings, pledge data, etc.)

### midfreq
Role:
- daily/post-session market-structure and report-support layer

Cadence:
- midday final support on trading days
- post-close final support on trading days
- weekly/preview support on weekends

Writes to:
- current/history datasets for equity/index/ETF daily bars, flows, turnover, limit-up detail, dragon tiger list, sector performance, etc.

### highfreq
Role:
- intraday raw/auction/event/derived working layer

Cadence:
- pre-open
- intraday near midday
- close/auction support
- disabled on non-trading sessions

Writes to:
- highfreq working tables for 1m slices / auctions / event stream
- derived working tables for breadth / heat / leader candidates / signal state / limit event state

### archive
Role:
- retained history / archive progression / catch-up execution

Cadence:
- evening archive windows on trading and non-trading days

Writes to:
- archive run evidence
- archive checkpoint/catch-up state
- retained history layers
- structured archive output snapshots

---

## 7. Archive retention semantics (business-facing)

### Long-term retained
- daily / broader-history archive layers
- 60m archive layers
- structured output archive snapshots
- checkpoint / catch-up truth

### Practical forward-only behavior
- 1m / 15m intraday archive lanes currently behave as forward-window accumulation lanes
- they can legitimately produce zero rows if no fresh eligible forward slices exist

This remains a truthful runtime/storage characteristic, not a newly reopened design issue.

---

## 8. Remaining truthful limitations
1. There is **no external hard-kill subprocess watchdog yet**; watchdog is DB-governance/operator-visible, not a separate reaper process.
2. `sector_performance` is now corrected and usable, but should be treated as a daily/post-close midfreq dataset.
3. 1m/15m archive remains forward-only in practical behavior.
4. Midfreq/highfreq status invocations currently re-register datasets on startup logs; not harmful, but noisy.

---

## 9. Final judgment
This batch brought the collection layer into real 24x7 unified-daemon mode and documented the truthful operator story.

What is real now:
- production daemon is running
- schedule policy is DB-backed
- worker status is DB-backed
- overlap/timeout governance exists
- watchdog visibility exists
- cleanup was executed before bring-up
- operator/business-facing inspection surfaces are documented

What is not being faked:
- there is not yet an out-of-process hard-kill watchdog supervisor

So the collection layer is now brought up with a truthful, inspectable operational story rather than an overstated one.
