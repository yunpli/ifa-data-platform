# Archive V2 Live Schedule Switch — Legacy Archive to archive_v2

Generated: 2026-04-18 20:25 PDT  
Repo: `/Users/neoclaw/repos/ifa-data-platform`
DB: `ifa2.runtime_worker_schedules`, `ifa2.runtime_worker_state`

## 1. Batch goal

Make the live runtime schedule DB use `archive_v2` as the nightly production archive lane instead of leaving legacy `archive` as the active scheduled path.

This batch was executed directly against the live DB with short, auditable commands only.
No destructive migration was performed.
No legacy tables/data/code were removed.

---

## 2. Before-state live schedule truth

Before the switch, the live DB truth was:

### `runtime_worker_schedules`
Enabled legacy `archive` rows existed for all day types:
- `archive:trade_day_evening_archive` at `21:30` Beijing time — **enabled**
- `archive:offday_archive` at `21:30` — **enabled**
- `archive:saturday_archive` at `21:30` — **enabled**
- `archive:sunday_archive` at `21:30` — **enabled**

At the same time:
- `archive_v2` had **no schedule rows**

### `runtime_worker_state`
- `archive` row existed
- `archive_v2` row did **not** exist

This was the exact mismatch between accepted runbook truth and live runtime DB truth.

---

## 3. Exact switch plan applied

### Legacy archive rows to disable
Disable all seeded `archive` schedule rows:
- `archive:trade_day_evening_archive`
- `archive:offday_archive`
- `archive:saturday_archive`
- `archive:sunday_archive`

### archive_v2 rows to enable/create
Seed `archive_v2` rows from current runtime schedule policy:
- `archive_v2:trade_day_nightly_daily_final` — trading day — `21:40` — **enabled**
- `archive_v2:offday_skip` — non-trading weekday — `21:40` — **disabled**
- `archive_v2:saturday_skip` — Saturday — `21:40` — **disabled**
- `archive_v2:sunday_skip` — Sunday — `21:40` — **disabled**

### Lane / cadence / role after switch
- active nightly production archive lane: `archive_v2`
- active nightly schedule key: `archive_v2:trade_day_nightly_daily_final`
- active cadence: `21:40` Beijing time on trading days
- profile linkage in accepted runtime/runbook truth: `archive_v2_production_nightly_daily_final`
- legacy `archive` role after switch: coexistence/manual fallback only, not default scheduled nightly

---

## 4. Exact DB changes applied

### Step 1 — attempted policy seeding via daemon bootstrap/status
Command used:
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --status
```

Truthful result:
- did **not** fully rewrite the stale archive/archive_v2 schedule state in this environment
- so a direct DB correction step was still required

### Step 2 — direct schedule DB correction
Commands executed (short audited DB steps only):

#### Disable seeded legacy archive rows / seed archive_v2 rows
- direct DB update using current `DEFAULT_SCHEDULE_POLICY`
- legacy `archive` seeded rows set to `enabled=false`
- `archive_v2` rows inserted/updated from code policy

#### Ensure `archive_v2` worker-state row exists
- inserted `runtime_worker_state(worker_type='archive_v2', last_status='idle')` if missing

No legacy code/tables were deleted.
No archive data tables were touched.

---

## 5. After-state live schedule truth

## 5.1 `runtime_worker_schedules`
After the switch, live DB rows are:

### legacy archive rows
- `archive:offday_archive` — **disabled**
- `archive:saturday_archive` — **disabled**
- `archive:sunday_archive` — **disabled**
- `archive:trade_day_evening_archive` — **disabled**

### archive_v2 rows
- `archive_v2:offday_skip` — **disabled**
- `archive_v2:saturday_skip` — **disabled**
- `archive_v2:sunday_skip` — **disabled**
- `archive_v2:trade_day_nightly_daily_final` — **enabled**

### Active nightly production row now
```text
worker_type = archive_v2
schedule_key = archive_v2:trade_day_nightly_daily_final
beijing_time_hm = 21:40
enabled = true
schedule_source = policy_seeded
group_name = archive_v2_main
purpose = Archive V2 steady-state nightly daily/final truth production
```

## 5.2 `runtime_worker_state`
After the switch:
- `archive` row still exists with historical last-run information
- `archive_v2` row now exists with:
  - `last_status = idle`
  - no prior schedule/run fields yet
  - state row present so runtime truth is aligned with the active schedule model

---

## 6. Validation commands and evidence

### 6.1 Before/after schedule inspection
```bash
python3 - <<'PY'
from sqlalchemy import create_engine, text
engine=create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
with engine.begin() as conn:
    rows=conn.execute(text("select worker_type, day_type, schedule_key, beijing_time_hm, enabled, schedule_source, purpose, group_name from ifa2.runtime_worker_schedules where worker_type in ('archive','archive_v2') order by worker_type, day_type, schedule_key")).mappings().all()
    for r in rows:
        print(dict(r))
PY
```

### 6.2 Worker-state verification
```bash
python3 - <<'PY'
from sqlalchemy import create_engine, text
engine=create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
with engine.begin() as conn:
    rows=conn.execute(text("select worker_type, last_status, last_schedule_key, last_trigger_mode, next_due_at_utc, updated_at from ifa2.runtime_worker_state where worker_type in ('archive','archive_v2') order by worker_type")).mappings().all()
    for r in rows:
        print(dict(r))
PY
```

### 6.3 Active archive_v2 nightly row verification
```bash
python3 - <<'PY'
from sqlalchemy import create_engine, text
engine=create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
with engine.begin() as conn:
    rows=conn.execute(text("select worker_type, day_type, schedule_key, beijing_time_hm, enabled from ifa2.runtime_worker_schedules where worker_type='archive_v2' and enabled=true order by day_type, schedule_key")).mappings().all()
    for r in rows:
        print(dict(r))
PY
```

### 6.4 Runtime-visible status surface
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --status
```

Truthful note:
- this status surface is useful for runtime visibility
- but the decisive source of truth for this batch was the DB schedule tables above

---

## 7. Legacy vs archive_v2 role after switch

### archive_v2
- **now the real nightly production archive lane**
- active trading-day nightly schedule
- enabled in live DB
- aligned with accepted runbook truth

### legacy archive
- no longer the active default scheduled production path
- still present in DB and code for coexistence/manual fallback
- disabled in live schedule rows
- retained non-destructively

---

## 8. Stable documentation alignment

Updated stable doc:
- `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`

The runbook now states the post-switch truth:
- `archive_v2` is the real scheduled nightly production lane
- `archive` remains coexistence/manual fallback only
- live schedule DB is aligned with runbook truth

---

## 9. Truthful final judgment

### What the live schedule DB looked like before
- legacy `archive` rows enabled
- `archive_v2` missing from live schedule DB
- `archive_v2` missing from worker-state DB

### Exactly what changed
- all seeded legacy `archive` schedule rows were disabled
- all seeded `archive_v2` schedule rows were inserted/updated from accepted policy
- active nightly row is now `archive_v2:trade_day_nightly_daily_final`
- `archive_v2` worker-state row was created
- runbook was updated to remove the stale mismatch language

### What the live schedule DB looks like after
- `archive_v2` trading-day nightly row enabled at `21:40` Beijing time
- all `archive` seeded rows disabled
- `archive_v2` worker-state row exists

### Is archive_v2 now the real nightly production lane?
**Yes.**

### What role does legacy archive still have?
- coexistence/manual fallback only
- present but not enabled as the active default nightly schedule
