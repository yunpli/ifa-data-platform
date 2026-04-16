# Architecture

## 1. Product anchor

The correct anchor for this repository is **iFA 2.0 product delivery**.

The product is not "a generic AI report bot". It is a market-clock-driven market-intelligence system for A-share and US equity workflows. In version 2.0, the deliverable is:

- briefing
- general market long reports
- one-main three-support structure
- pre-market / intraday / post-market continuity
- evidence-backed professional output

Therefore the architecture cannot be reduced to "a few agents generate text on schedule". The backend must provide a stable substrate for evidence, facts, signals, run control, and continuity validation.

## 2. Architectural conclusion

iFA 2.0 should be implemented as a **Market-Intelligence Operating System** shape, not merely a timed generation chain.

At repo scope, this repository currently covers the **data/runtime substrate** portion of that operating model.

That means the repo should evolve toward supporting:
- source ingestion and normalization
- fact/signal accumulation
- evidence provenance
- block/material input assembly
- run-state / deadline / retry / degrade control hooks
- report-generation inputs that are deterministic enough to debug

## 3. Scope boundary of this repository

### This repo owns
- raw evidence capture and persistence boundaries
- normalized internal market/release/filing objects
- typed facts and future derived signals
- runtime job state and health checks
- migration-managed schema in `ifa2`
- minimal materialization inputs for report production

### This repo does not own yet
- full report rendering system
- full delivery system
- full subscription and commercialization logic
- complete control-plane implementation
- full multi-agent product orchestration
- 2.1/2.2 personalization features

### Why this boundary is correct
Because iFA 2.0 still needs a real backend spine, but this repo should not pretend to already be the entire product system. It is the engineering backbone for the product, not the entire surface area.

## 4. Product-to-technical mapping

### Product requirement: market-clock continuity
Technical implication:
- pre / intra / post windows must share durable state and comparable evidence
- report generation cannot rely on purely transient prompts

### Product requirement: evidence-backed professional output
Technical implication:
- conclusions must trace to source records, normalized objects, and fact-bearing inputs
- provenance and timestamping are first-class

### Product requirement: one-main three-support structure
Technical implication:
- backend inputs should be reusable across multiple report types/agents
- materialization should support section/block reuse, not one giant opaque prompt

### Product requirement: continuity validation
Technical implication:
- later runs should be able to compare against earlier hypotheses
- the substrate must preserve enough state to mark validation / partial validation / invalidation later

### Product requirement: future 2.1 / 2.2 / 3.x extensibility
Technical implication:
- current schema/runtime should not dead-end at static report generation
- fact/signal/judgment-oriented evolution path must stay open

## 5. Current canonical backend flow

At the current stage, the working backend flow is:

`raw evidence -> normalized objects -> typed facts/signals -> report material inputs`

A slightly more complete target form is:

`raw -> refined -> facts/signals -> section/material bundle -> generation -> rendering/delivery`

This repo is currently focused on the left/middle portion of that chain.

## 6. Layer model

### 6.1 Source & ingestion layer
Purpose:
- fetch from official/public/market sources
- track source identity and runtime execution
- preserve replayability

Representative concerns:
- source policy
- job lifecycle
- fetch timestamps
- retries / cadence / audit hooks

### 6.2 Raw evidence layer
Purpose:
- preserve what was acquired
- retain hashes, payload linkage, timestamps, and source/run relations

Current representative object:
- `raw_records`

### 6.3 Normalization layer
Purpose:
- turn heterogeneous inputs into stable internal shapes before generation-time interpretation

Current representative objects:
- `items`
- `official_events`
- `market_bars`
- `filings`

### 6.4 Fact/signal layer
Purpose:
- produce reusable typed information from normalized records
- support future continuity checks and richer report blocks

Current representative objects:
- `facts`
- `fact_sources`

### 6.5 Materialization/input assembly layer
Purpose:
- bridge durable backend assets into report-ready bundles
- support reusable sections/blocks instead of full opaque prompt assembly

Current representative object:
- `slot_materializations`

This table/object is still only a minimal placeholder. The architectural meaning is more important than the present implementation depth.

## 7. Runtime/control implications

Even in 2.0, report production is a timed system. Therefore the backend must be designed with support for:
- run states
- deadlines
- retries
- degradation rules
- notification hooks
- replay/backfill
- schedule policy by market/business day type
- operator-readable worker state and recent run evidence

### Current runtime truth
The repository has now converged to a **unified runtime daemon** as the official long-running entry:
- `python -m ifa_data_platform.runtime.unified_daemon --loop`

The unified daemon owns:
- central schedule loading from `ifa2.runtime_worker_schedules`
- Beijing/Shanghai business-time schedule semantics
- trading-day classification via `ifa2.trade_cal_current`
- worker dispatch for:
  - `lowfreq`
  - `midfreq`
  - `highfreq`
  - `archive`
- centralized run evidence in `ifa2.unified_runtime_runs`
- centralized worker state in `ifa2.runtime_worker_state`
- runtime budget / overlap / timeout governance hooks

Lane-specific `lowfreq` / `midfreq` / `highfreq` daemon modules still exist, but their long-running `--loop` role has been demoted to compatibility/manual-wrapper status rather than remaining primary operational entry points.

## 7.1 Schedule policy truth
Production schedule policy is now explicitly modeled by runtime day type:
- `trading_day`
- `non_trading_weekday`
- `saturday`
- `sunday`

Trading-day truth is DB-backed through:
- `ifa2.trade_cal_current`

Current high-level schedule shape:
- trading day:
  - lowfreq pre-report refresh
  - highfreq pre-open / intraday / close support
  - midfreq midday / post-close support
  - archive evening backlog/archive run
- non-trading weekday:
  - lowfreq reference refresh
  - archive run
- Saturday:
  - lowfreq weekly-review support
  - midfreq weekly-review support
  - archive run
- Sunday:
  - lowfreq next-week preview support
  - midfreq preview-support refresh
  - archive run

Highfreq is intentionally not scheduled as a normal weekend/non-trading-weekday lane.

## 7.2 Business Layer influence on execution
Business Layer truth now materially affects runtime scope:
- `focus_lists`
- `focus_list_items`
- `focus_list_rules`

Important current truth:
- `default_key_focus` and `default_focus` exist and drive broad stock-oriented scope
- `default_archive_targets_15min` and `default_archive_targets_minute` exist and drive archive target scope
- `default_tech_key_focus` and `default_tech_focus` were later seeded to close a Business Layer gap in tech coverage
- commodity / precious_metal focus-style lists still do not exist as first-class Business Layer definitions

That means some coverage gaps can be Business Layer target-definition gaps rather than source/runtime failures.

## 8. OpenClaw boundary

OpenClaw should remain above this repository as:
- operator surface
- workflow orchestrator
- consumer of outputs
- watchdog/observer

It should not replace the internal runtime/data contracts of the repo.

## 9. Why old IFA/ICD chains are reference only

Old chains contain valuable lessons and object ideas, but they were optimized around shipping reports, not around maintaining a durable, auditable, replayable operating substrate.

That old coupling mixed:
- fetch
- interpret
- assemble
- archive
- deliver

The new repo should extract lessons, not inherit that coupling as the new core.

## 10. Current implemented reality

As of the current checkpoint, this repo has:
- migration-managed `ifa2` schema
- core placeholder tables for source/raw/item/event/bar/filing/fact/materialization objects
- a runnable minimal runtime/job loop
- health check coverage for schema + job state path

So the correct description is:

**not complete iFA 2.0**, but **a now-real backend skeleton aligned to iFA 2.0 architecture instead of a generic toy scaffold**.
