# IFA Data Platform

IFA Data Platform is the backend data/runtime foundation for **iFA 2.0**.

It exists to support the **iFA 2.0 report system**: a market-clock-driven, AI-native market-intelligence product for A-share and US equity workflows. In 2.0, the product focus is **briefing + general market long reports**, delivered in a stable rhythm under the **one-main three-support** structure, not personalized watchlist/holdings intelligence yet.

This repository should therefore be understood as a **supporting engineering backbone** for iFA 2.0 report production — not as a detached generic Python skeleton, and not yet as the full end-state of iFA 3.x.

## What this repo is for

The purpose of this repo is to make iFA 2.0 report generation:

- evidence-backed
- replayable
- auditable
- deadline-aware
- operationally stable

That means building the minimum durable backend contracts behind report delivery:

- source ingestion
- raw evidence retention
- normalized market/release/filing objects
- typed facts and derived signals
- section/block materialization inputs
- job state, health checks, and operational traces

The immediate product it serves is **iFA 2.0 briefing + long-report delivery**, not standalone data monetization.

## Product position in iFA evolution

### iFA 2.0
Current target:
- general market intelligence only
- briefing + long report
- one-main three-support agent/report structure
- market-clock delivery (pre-market / intraday / post-market)
- continuity validation across time windows
- no personalized watchlist / holdings decisions

This repo supports that by providing the backend substrate for:
- evidence capture
- fact/signal preparation
- report block inputs
- run-state / deadline / retry foundations

### iFA 2.1
Planned extension direction:
- watchlist intelligence
- trigger tracking
- multi-horizon monitoring inputs

### iFA 2.2
Planned extension direction:
- holdings intelligence
- exposure/risk views
- more personalized strategy-facing inputs

### iFA 3.x
Longer-term direction:
- strategy intelligence
- stock-selection intelligence
- stronger judgment/outcome loops
- model evolution on top of accumulated facts/signals/judgments/results

## Why this repo exists

The old IFA / ICD execution chain is useful as historical reference, but it is not a strong enough backbone for iFA 2.0.

Old patterns mixed together:
- fetching
- one-off interpretation
- report assembly
- archive handling
- delivery-time logic

That creates several problems:
- repeated re-fetching instead of durable accumulation
- weak evidence continuity across pre/intra/post windows
- hard-to-debug late-stage failures
- unclear provenance for final report statements
- poor support for replay, validation, and future model improvement

For iFA 2.0, report delivery is the product surface — but stable delivery requires a stronger backend substrate underneath it.

## Current phase

Current phase is:

**preparation + architecture + skeleton + minimum runnable closure**

This is intentional.

At this stage, the goal is **not** to fully build the complete iFA 2.0 production system in one shot. The goal is to establish the minimum correct backbone so later report workflows are built on durable contracts instead of another coupled script chain.

### In scope now
- independent repo and Python project skeleton
- real PostgreSQL schema `ifa2` inside existing `ifa_db`
- Alembic migration flow
- minimal runtime/job state loop
- health checks and runnable demo
- core data-layer boundaries for raw -> normalized -> facts
- architecture docs aligned to iFA 2.0 product delivery

### Not in scope now
- full iFA 2.0 product completion
- all report templates and rendering paths
- full FastAPI/Celery/Redis production rollout
- all source adapters and all markets onboarded
- 2.1 watchlist intelligence
- 2.2 holdings intelligence
- 3.x strategy/stock-selection intelligence

## Architecture stance

The correct architectural stance is:

**iFA 2.0 is not just "scheduled prompts + pushes".**

It must be implemented as a market-intelligence system with:
- a durable data/fact/signal substrate
- report-block-oriented materialization
- run state + deadline + retry/degrade controls
- evidence traceability
- continuity checks across report windows

This repo currently covers the **backend substrate side** of that architecture.

Canonical backend flow at this stage:

`raw evidence -> normalized objects -> typed facts/signals -> report material inputs / slot-oriented bundles`

## OpenClaw boundary

OpenClaw is not the core data-processing runtime of this repository.

OpenClaw should remain:
- orchestration/operator surface
- watchdog/observer
- upper-layer consumer
- surrounding workflow coordinator

The core repo should stay independently operable with its own:
- schema
- migrations
- runtime loop
- job state
- health checks
- future API / worker contracts

## Storage and runtime direction

Current implemented direction:
- PostgreSQL as operational store
- `ifa_db` as current host database
- `ifa2` as isolated schema
- Python runtime skeleton
- migration-managed schema evolution
- minimal job lifecycle persistence in `ifa2.job_runs`

Near-term compatible direction:
- Redis for coordination/cache
- richer fact/signal materialization
- block-oriented report inputs
- deadline/retry/degrade control plane semantics
- future report-generation and delivery integration

## Current status

- Checkpoint 1: repo skeleton established
- Checkpoint 2: real `ifa2` schema migration landed in `ifa_db`
- Workstream 3: minimal runtime/job loop runnable and verified

## Local development quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Add TUSHARE_TOKEN to .env for China-market data
alembic upgrade head
pytest
python scripts/demo_runtime.py
```

## Tushare configuration (China-market low-frequency acquisition)

To enable Tushare data ingestion:

```bash
# Add to .env
TUSHARE_TOKEN=your_token_here
```

Obtain token from https://tushare.pro. See [Runbook](docs/runbook.md) for verification steps.

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [Migration Notes](docs/migration_notes.md)
- [Low-Frequency Framework](docs/lowfreq_framework.md)
- [Job 7 Lowfreq Gap & Expansion Plan](job7_lowfreq_gap_and_expansion_plan.md)

## Low-Frequency Ingestion Framework

The low-frequency ingestion framework provides a unified way to register, execute, and track low-frequency dataset jobs for iFA China-market / A-share direction.

### Core Components

- **Models** (`src/ifa_data_platform/lowfreq/models.py`): Dataset/job abstractions including `DatasetConfig`, `RunState`, and enums for `Market`, `JobType`, `RunnerType`, `WatermarkStrategy`, etc.
- **Registry** (`src/ifa_data_platform/lowfreq/registry.py`): Database-backed dataset registry for managing dataset configurations.
- **Run State** (`src/ifa_data_platform/lowfreq/run_state.py`): Manages run-level state including status, records processed, watermark, and error messages.
- **Adaptor Interface** (`src/ifa_data_platform/lowfreq/adaptor.py`): Provider-agnostic interface for data source adaptors.
- **Runner** (`src/ifa_data_platform/lowfreq/runner.py`): Unified runner supporting dry-run and real-run modes.

### Usage

```bash
# Register a dataset
python -c "
from ifa_data_platform.lowfreq.models import DatasetConfig, Market, JobType, RunnerType
from ifa_data_platform.lowfreq.registry import DatasetRegistry
config = DatasetConfig(dataset_name='test', market=Market.CHINA_A_SHARE, source_name='tushare', job_type=JobType.INCREMENTAL, runner_type=RunnerType.DUMMY)
registry = DatasetRegistry()
registry.register(config)
"

# Run a dataset (dry-run)
python -m ifa_data_platform.lowfreq.runner --dataset test --dry-run

# Run a dataset (real-run)
python -m ifa_data_platform.lowfreq.runner --dataset test

# List all datasets
python -m ifa_data_platform.lowfreq.runner --list
```

### Tests

```bash
# Run all low-frequency tests
pytest tests/unit/test_lowfreq.py tests/integration/test_lowfreq_job3.py

# Run specific dataset
python -m ifa_data_platform.lowfreq.runner --dataset trade_cal
python -m ifm ifa_data_platform.lowfreq.runner --dataset stock_basic

# Register standard datasets
python scripts/register_datasets.py
```

### Low-Frequency Daemon (Job 6)

```bash
# Run daemon once
python -m ifa_data_platform.lowfreq.daemon --once

# Run daemon in loop mode
python -m ifa_data_platform.lowfreq.daemon --loop

# Show daemon health/status
python -m ifa_data_platform.lowfreq.daemon --health

# Run with custom config
python -m ifa_data_platform.lowfreq.daemon --config /path/to/config.yaml --once

# Run daemon validation script
python scripts/validate_daemon.py --show-config
python scripts/validate_daemon.py --once
python scripts/validate_daemon.py --health
```
