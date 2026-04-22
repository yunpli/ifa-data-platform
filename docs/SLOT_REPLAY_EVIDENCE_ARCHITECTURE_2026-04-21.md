# Slot Replay Evidence Architecture

## Why this exists

The report layer needs a durable answer to a simple but operationally critical question:

> For trade_date + report slot (`early` / `mid` / `late`), what exactly did the system know, use, and produce at that point in time?

This implementation adds a **slot-level replay evidence layer** without turning the platform into a heavy full-table H/M/L archive system.

The goal is not to persist every intermediate row forever. The goal is to persist enough **replay evidence** to support:

- same-day **as-known-at-the-time** reconstruction
- later **best-corrected** reconstruction
- explicit coexistence of those two viewpoints
- a stable contract for future report artifact integration

## Core design

Two new tables are introduced:

- `ifa2.slot_replay_evidence`
- `ifa2.slot_replay_evidence_runs`

### `slot_replay_evidence`

One row = one captured evidence snapshot for:

- `trade_date`
- `slot_key` (`early`, `mid`, `late`)
- `perspective` (`observed`, `corrected`)

Each row stores structured JSON contexts instead of raw heavy archives:

- `selection_policy`
  - how runs were selected
  - whether selection was explicit (`--run-id`, `--schedule-key`) or inferred from slot rules
- `manifest_context`
  - primary manifest snapshot id/hash
  - all selected manifest snapshots involved
- `trigger_context`
  - trigger modes
  - schedule keys
  - Beijing trigger times
- `worker_context`
  - selected runtime runs
  - worker types, durations, budgets, governance state
  - tables/tasks touched
- `dataset_context`
  - dataset/family names chosen from selected runs
  - run-linked status / watermark / row counts / errors
- `snapshot_context`
  - lightweight durable probes against current/history/working tables
  - row counts, latest observed value, latest version id when available
- `artifact_context`
  - either a real artifact reference (`path`, `sha256`, `bytes`, `content_type`) or a placeholder contract when the report layer is not yet integrated

### `slot_replay_evidence_runs`

This links each evidence snapshot to the concrete `unified_runtime_runs` rows that fed it.

That gives us durable provenance without duplicating full run payloads into another normalized run table.

## Slot semantics

Canonical slots are intentionally narrow and practical:

- `early`
  - observed cutoff: `09:30` Beijing
  - lanes considered: `lowfreq`, `midfreq`, `highfreq`
- `mid`
  - observed cutoff: `13:30` Beijing
  - lanes considered: `lowfreq`, `midfreq`, `highfreq`
- `late`
  - observed cutoff: `17:30` Beijing
  - lanes considered: `lowfreq`, `midfreq`, `highfreq`, `archive_v2`

### Perspective rules

#### `observed`

Select the latest successful/partial run per lane whose Beijing start time is on `trade_date` and **not later than the slot cutoff**.

This is the durable answer to:

> What did we know at that slot when the report should have been generated?

#### `corrected`

Select the latest successful/partial run per lane tied to the trade date, even if it completed later.

This is the durable answer to:

> If we replay that slot later using best corrected truth, what should we use now?

These two perspectives intentionally coexist. We do **not** collapse them into one mutable row.

## Why this is not a heavy archive system

This layer stores:

- run references
- manifest references
- dataset/family references
- watermarks
- row counts
- lightweight state probes
- artifact references / hashes

It does **not** store:

- full H/M/L report input tables per slot
- full table snapshots for every selected dataset
- giant denormalized row payload dumps

That keeps the system durable enough for replay evidence while remaining operationally sane.

## Report artifact contract

If the report layer already has an artifact path, pass it during capture and the evidence row stores:

- artifact path
- sha256 hash
- content type
- byte size
- generated timestamp

If the report layer is not integrated yet, the evidence row stores a placeholder contract:

- `status = pending_integration`
- producer = `slot_replay_evidence`
- note explaining why the artifact is absent

This is deliberate. We preserve the contract now instead of faking brittle report coupling.

## CLI usage

### Capture observed evidence

```bash
PYTHONPATH=src DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp' \
python scripts/slot_replay_evidence_cli.py capture \
  --trade-date 2026-04-18 \
  --slot early \
  --perspective observed
```

### Capture corrected evidence with explicit report artifact

```bash
PYTHONPATH=src DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp' \
python scripts/slot_replay_evidence_cli.py capture \
  --trade-date 2026-04-18 \
  --slot late \
  --perspective corrected \
  --artifact-path reports/2026-04-18-late.html \
  --artifact-producer report-layer
```

### Force capture from explicit runtime runs

```bash
PYTHONPATH=src DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp' \
python scripts/slot_replay_evidence_cli.py capture \
  --trade-date 2026-04-18 \
  --slot late \
  --run-id <run-uuid-1> \
  --run-id <run-uuid-2>
```

### Inspect snapshots

```bash
python scripts/slot_replay_evidence_cli.py list --trade-date 2026-04-18
python scripts/slot_replay_evidence_cli.py get <evidence-id>
```

## Integration path for the future report layer

The intended flow is:

1. collection/runtime lanes run as normal
2. report builder chooses `trade_date + slot`
3. report builder generates artifact
4. report builder calls capture with:
   - slot
   - perspective
   - optional explicit run ids if report selection was custom
   - artifact path/hash contract
5. replay/regeneration later reads the evidence row first

That means the evidence row becomes the durable control-plane object for replay.

## Limitations / current caveats

1. **Dataset version probing is best-effort**
   - `snapshot_context` uses known table hints and version columns where available
   - not every dataset/family has a perfect canonical version table yet

2. **Observed selection uses runtime start time**
   - this is intentional and practical today
   - if the report layer later needs finer “input freeze” semantics, add an explicit report-generation timestamp and/or report-request event id

3. **Archive V2 is only included in `late` inferred selection**
   - because early/mid slots should not accidentally bind to a nightly archive truth run

4. **No automatic daemon hook yet**
   - current implementation is a first-class storage/service/CLI layer
   - report-layer or orchestration-layer integration should call it explicitly when a slot artifact is produced

## Files introduced

- `src/ifa_data_platform/runtime/replay_evidence.py`
- `scripts/slot_replay_evidence_cli.py`
- `alembic/versions/038_slot_replay_evidence.py`
- `tests/integration/test_slot_replay_evidence.py`

## Summary

This gives the platform a durable, queryable, production-usable **slot replay evidence plane** with:

- slot-scoped provenance
- observed vs corrected coexistence
- run + manifest linkage
- lightweight dataset/version/snapshot evidence
- report artifact contract support

without forcing a heavy per-slot full-table archival model.
