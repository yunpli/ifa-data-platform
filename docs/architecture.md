# Architecture

## 1. Product-driven architecture rationale

IFA 2.0 is a market-intelligence system, not just a report generator. Its long-term value comes from maintaining a structured, queryable, reviewable flow of evidence and facts over time. That product goal directly determines the architecture:

- evidence must be preserved outside a single report run
- normalization must be separated from downstream interpretation
- facts must remain queryable over time
- upper layers must consume a deterministic contract rather than scrape and reinterpret sources repeatedly
- provenance, freshness, source policy, and auditability must be first-class system concerns

The IFA Data Platform exists to make those properties operational.

## 2. System boundary

The data platform is an independent service/library layer.

### It owns
- source registry and source policy
- ingestion jobs and adapter lifecycle
- raw evidence archive pointers and metadata
- normalized internal objects
- typed facts and fact provenance
- slot materialization and serving contracts
- job state, audit, observability, health

### It does not own
- report rendering as a primary concern
- subscription/delivery logic as a core design anchor
- old manual/archive/runs chain semantics
- OpenClaw runtime logic as its core execution model

### OpenClaw relation
OpenClaw should sit above this system as:
- consumer
- watchdog
- operator surface
- orchestration layer for adjacent workflows

It should not be the primary ingestion skeleton for the data layer.

## 3. Canonical layers

### 3.1 Raw layer
Purpose:
- preserve source payload identity, hashes, timestamps, source/run linkage, and replayability
- provide evidence retention independent of report jobs

Representative objects:
- `raw_records`
- future object-store payload pointers

### 3.2 Normalized object layer
Purpose:
- land heterogeneous sources into stable internal object boundaries before any fact semantics
- isolate parsing from downstream business interpretation

Representative objects:
- `items`
- `official_events`
- `market_bars`
- `filings`

### 3.3 Fact layer
Purpose:
- derive typed, reusable, evidence-backed facts
- support revisions, confidence, and later evidence graph expansion

Representative objects:
- `facts`
- `fact_sources`

### 3.4 Serving / slot layer
Purpose:
- expose a stable contract to upper layers
- materialize domain/date/slot views instead of forcing re-fetch + re-parse loops

Representative objects:
- `slot_materializations`

Long-term serving contract:
- input: `(domain, date, slot, policy)`
- output: facts bundle + evidence coverage + freshness + gaps

## 4. Provider-agnostic first

At the current stage, upstream vendor choice should not block foundational engineering. Therefore the platform starts adapter-first and provider-agnostic:

- source capability is described explicitly
- normalization contracts remain internal and stable
- provenance policy remains consistent even when providers change
- the scheduler/worker/job framework can be completed before every market data source is finalized

This is a deliberate anti-lock-in and anti-blocking choice.

## 5. Operational model

The intended runtime loop is:

1. scheduler decides what should run
2. worker executes fetch / normalize / upsert / derive
3. job lifecycle is written into `job_runs`
4. health checks validate freshness and service liveness
5. upper layers consume slot-oriented materialization instead of raw script chains

## 6. Current storage direction vs long-term direction

### Current fixed direction for this phase
- Python implementation
- PostgreSQL operational database
- `ifa_db` host database
- isolated `ifa2` schema
- Redis reserved in interface/runtime contracts

### Long-term design direction absorbed from uploaded specifications
The uploaded design specs reinforce several future-compatible directions that this repo should stay open to:
- raw payloads may expand into object storage pointers
- time-series workloads may deserve dedicated optimization paths
- vector/RAG support may become part of evidence retrieval
- slot query should become the only supported upper-layer interface

This repository does **not** have to implement every one of those now, but its contracts should not block them later.

## 7. Why old IFA/manual/archive/runs are not the new backbone

Old assets are useful as:
- examples of domain object boundaries
- field naming references
- evidence of real operational pain points
- migration/reference material

They are not suitable as the primary backbone because they tightly coupled:
- acquisition
- interpretation
- archive handling
- report delivery
- one-off execution logic

That coupling is precisely what the new platform is meant to undo.
