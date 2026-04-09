# Migration Notes

## 1. Migration principle

This repository is the new main branch for the IFA data substrate. Migration means **reusing object boundaries and operational lessons**, not inheriting historical execution-chain pollution.

The goal is to carry forward:
- useful object ideas
- stable identifiers and field concepts
- proven domain boundaries
- operational lessons learned

and leave behind:
- coupled manual/archive/runs execution patterns
- report-chain-first structure
- ad-hoc script glue as the primary architecture
- historical one-off fixes embedded as system design

## 2. Why old manual/archive/runs should not remain the backbone

The old chains were optimized around getting reports out, not around maintaining a durable evidence and fact substrate.

That created several problems:
- repeated re-fetching and re-interpretation
- weak separation between data collection and report generation
- operational state tied to execution chains instead of durable facts
- poor replayability
- higher debugging cost when a run failed late in the chain

The new repo exists specifically to break that pattern.

## 3. What is reasonable to reference from old assets

### Reusable ideas
- practical object boundaries from existing `ifa_*` scripts and tables
- useful market/fact/source naming patterns
- lessons from ingestion pain points and slot-query expectations
- existing `ifa_db.py` connectivity assumptions for `ifa_db`

### Reusable fields or concepts
- source registry style concepts
- market bar identity patterns
- filing/fact relationships
- slot-oriented serving expectations
- run tracking as an explicit object

### Historical assets that are reference-only
- old archive directories
- report outputs
- run artifacts
- manual scripts for specific domains
- one-off recovery notes / backups / rollout docs

## 4. What should not be carried over directly

- old report-generation-first script chains
- manual/archive/runs directories as primary design anchors
- OpenClaw-specific business execution logic inside the new core
- domain-specific repair code as generalized platform abstractions
- schema shapes that only make sense for a single report flow

## 5. Current migration stance

### New mainline
- `ifa-data-platform` repo
- PostgreSQL schema `ifa2`
- Alembic-managed migrations
- scheduler/worker/adapter/client contracts

### Old system role going forward
- reference
- source of lessons
- source of candidate field ideas
- source of operational examples
- not the primary backbone

## 6. Current concrete environment findings

Current environment already indicates:
- existing PostgreSQL database `ifa_db`
- local connection path via `/tmp:5432`
- existing helper logic in `/Users/neoclaw/.openclaw/workspace/scripts/ifa_db.py`
- prior `ifa_*` implementation material that can inform boundaries but should not be transplanted wholesale

## 7. Next migration method

Migration should proceed as:
1. establish independent schema + migrations
2. stabilize runtime and object contracts
3. selectively reference old field/object ideas
4. onboard first real sources through new adapters
5. let upper layers consume slot-query outputs from the new system
