# IFA Data Platform

IFA Data Platform is the independent **data and evidence substrate** for **IFA 2.0** and future **IFA 2.x / 3.x** systems.

Its job is **not** to render reports directly. Its job is to build a durable, queryable, replayable foundation that separates:

- source acquisition
- raw evidence accumulation
- normalization
- fact derivation
- provenance / audit
- slot-oriented serving

from downstream report generation, chat, strategy, and delivery layers.

## Why this repo exists

The old IFA / ICD chains mixed together data fetching, one-off interpretation, archive handling, and report generation. That made the system harder to audit, replay, debug, and evolve. IFA 2.0 requires a stronger substrate:

- evidence should accumulate over time rather than being re-fetched for every report
- facts should be queryable over months/years, not trapped inside one run
- every fact should be traceable back to raw payloads, normalized records, adapter runs, and source policy
- source policy, freshness, cadence, and retry behavior should be centrally enforced
- upper layers should consume deterministic slot bundles, not rebuild evidence from scratch every time

This repository is the engineering starting point for that substrate.

## Product position in IFA 2.0 -> 2.x -> 3.x

### IFA 2.0
This repo provides the **data layer / evidence foundation** for a market-intelligence system serving A-share and US equity workflows around market-clock delivery.

### IFA 2.x
This repo is intended to support:
- watchlist intelligence
- holdings intelligence
- reusable fact bundles
- slot-oriented market state retrieval
- evidence-backed downstream decisions

### IFA 3.x
This repo is intended to remain the durable base for:
- strategy intelligence
- longitudinal fact history
- replay and drift analysis
- learned systems built on persistent evidence instead of transient prompts

## Current phase

Current phase is **preparation + architecture + skeleton implementation**.

### In scope now
- independent repo and Python project skeleton
- PostgreSQL schema `ifa2`
- migration framework
- source adapter abstractions
- raw -> normalized -> fact -> serving data model boundaries
- scheduler / worker / job lifecycle skeleton
- health / audit / provenance contracts
- provider-agnostic client and ingestion framework
- minimal runnable demo for long-running service architecture

### Not in scope now
- full provider onboarding
- fixing the old IFA / ICD report chain
- making report rendering the primary focus
- trying to finalize every vendor selection before the platform exists
- putting OpenClaw in charge of core ingestion loops
- one-shot building of every future IFA capability

## OpenClaw boundary

OpenClaw is **not** the primary ingestion/data-processing skeleton for this system.

OpenClaw should act as:
- upper-layer consumer
- watchdog / health observer
- operator entrypoint
- orchestration layer for surrounding workflows

The data platform itself should remain independently operable as a service/library with its own runtime, schema, migrations, and operational contracts.

## Core architecture direction

Canonical flow:

`raw evidence -> normalized objects -> typed facts -> slot query bundle`

The long-term contract to upper layers is a slot query surface that returns a deterministic bundle of facts, evidence coverage, freshness, and gaps.

## Storage direction

Current engineering direction for this repository:
- PostgreSQL as the primary operational store
- `ifa_db` as the current host database
- `ifa2` as the new isolated schema
- Redis reserved as runtime/cache coordination layer
- object storage compatibility reserved for raw payload expansion
- provider-agnostic adapter-first ingestion model

The uploaded design materials also point toward a broader long-term stack (time-series optimization, vector/RAG support, object-store raw archive, local/offline replay). This repository is being shaped so those directions can be added without redoing the backbone.

## Repository layout

```text
README.md
docs/
  architecture.md
  runbook.md
  migration_notes.md
src/ifa_data_platform/
  api/
  adapters/
  clients/
  config/
  contracts/
  db/
  models/
  runtime/
  services/
tests/
alembic/
config/
scripts/
```

## Local development quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
pytest
python scripts/demo_runtime.py
```

## Progress status

- Checkpoint 1: repo skeleton established
- Checkpoint 2: schema + migration in progress / being closed against real `ifa_db`
- Workstream 3: runtime skeleton and demo being added

## Implementation phases

1. Skeleton and architecture backbone
2. Real schema + migration closure in `ifa2`
3. Scheduler/worker/job state/health minimal loop
4. First provider-agnostic adapter and client demo
5. Controlled first real source onboarding

## Design rule

This repo reuses **object boundaries and lessons** from old assets when helpful, but it does **not** inherit old execution-chain pollution as the new system backbone.

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [Migration Notes](docs/migration_notes.md)
