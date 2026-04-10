# Low-Frequency Ingestion Framework

## Overview

The low-frequency ingestion framework provides a unified way to register, execute, and track low-frequency dataset jobs for iFA China-market / A-share direction. This framework is designed to be provider-agnostic, allowing future data sources to be integrated through a clean adaptor interface.

## Architecture

### Core Components

1. **Models** (`src/ifa_data_platform/lowfreq/models.py`)
   - `DatasetConfig`: Dataset configuration dataclass with fields for dataset_name, market, source_name, job_type, enabled, timezone_semantics, runner_type, watermark_strategy, budget_limits, and metadata.
   - `RunState`: Run-level state including run_id, dataset_name, status, started_at, completed_at, records_processed, watermark, error_message, run_type, and dry_run.
   - Enums: `Market`, `JobType`, `RunnerType`, `TimezoneSemantics`, `WatermarkStrategy`, `JobStatus`

2. **Registry** (`src/ifa_data_platform/lowfreq/registry.py`)
   - Database-backed dataset registry for managing dataset configurations.
   - Methods: `register()`, `get()`, `list_enabled()`, `list_all()`, `enable()`, `disable()`

3. **Run State** (`src/ifa_data_platform/lowfreq/run_state.py`)
   - Manages run-level state including status, records processed, watermark, and error messages.
   - Methods: `create_run()`, `update_status()`, `get()`, `get_latest_for_dataset()`, `list_recent()`

4. **Adaptor Interface** (`src/ifa_data_platform/lowfreq/adaptor.py`)
   - Abstract `BaseAdaptor` class defining the provider-agnostic interface.
   - Methods: `fetch()`, `test_connection()`, `close()`

5. **Runner** (`src/ifa_data_platform/lowfreq/runner.py`)
   - Unified runner supporting dry-run and real-run modes.
   - CLI entrypoint with arguments for dataset selection, dry-run, listing, etc.

6. **Raw Persistence** (`src/ifa_data_platform/lowfreq/raw_persistence.py`)
   - Persists raw fetch results for audit and replay.
   - Stores: source_name, dataset_name, fetched_at_utc, request_params, raw_payload, run_id linkage

7. **Canonical Persistence** (`src/ifa_data_platform/lowfreq/canonical_persistence.py`)
   - Manages canonical current tables for datasets.
   - `TradeCalCurrent`: China-market trading calendar.
   - `StockBasicCurrent`: A-share instrument master data.

### Database Schema

Four new tables in the `ifa2` schema:

- **`lowfreq_datasets`**: Stores dataset configurations (migration `002_lowfreq.py`)
- **`lowfreq_runs`**: Stores run-level state (migration `002_lowfreq.py`)
- **`lowfreq_raw_fetch`**: Raw source mirror for audit/replay (migration `003_lowfreq_raw_canonical.py`)
- **`trade_cal_current`**: Canonical trading calendar (migration `003_lowfreq_raw_canonical.py`)
- **`stock_basic_current`**: Canonical A-share instruments (migration `003_lowfreq_raw_canonical.py`)

## Usage

### Register a Dataset

```python
from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    Market,
    JobType,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.registry import DatasetRegistry

config = DatasetConfig(
    dataset_name="trade_cal",
    market=Market.CHINA_A_SHARE,
    source_name="tushare",
    job_type=JobType.INCREMENTAL,
    enabled=True,
    timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
    runner_type=RunnerType.TUSHARE,
    watermark_strategy=WatermarkStrategy.DATE_BASED,
    budget_records_max=10000,
    budget_seconds_max=300,
    metadata={"api_name": "trade_cal", "exchange": "SSE"},
    description="China A-share trading calendar from Tushare",
)

registry = DatasetRegistry()
dataset_id = registry.register(config)
```

### Run a Dataset

```bash
# Dry-run (simulate execution without writing data)
python -m ifa_data_platform.lowfreq.runner --dataset trade_cal --dry-run

# Real-run
python -m ifa_data_platform.lowfreq.runner --dataset trade_cal

# Run all enabled datasets
python -m ifa_data_platform.lowfreq.runner

# List all datasets
python -m ifa_data_platform.lowfreq.runner --list
```

### Programmatic Usage

```python
from ifa_data_platform.lowfreq.runner import LowFreqRunner

runner = LowFreqRunner()

# Run a specific dataset
result = runner.run("trade_cal", dry_run=False)
print(f"Status: {result.status}, Records: {result.records_processed}, Watermark: {result.watermark}")

# Run all enabled datasets
results = runner.run_all(dry_run=True)
```

### Register Trade Cal and Stock Basic Datasets

```bash
# Register the standard China-market datasets
python scripts/register_datasets.py
```

## Tushare Datasets

The framework includes real Tushare data source implementation:

### trade_cal
- **Description**: China-market trading calendar (SSE)
- **Job Type**: Incremental
- **Watermark Strategy**: Date-based
- **Canonical Table**: `ifa2.trade_cal_current`

### stock_basic
- **Description**: A-share instrument master data
- **Job Type**: Snapshot
- **Watermark Strategy**: None (full refresh)
- **Canonical Table**: `ifa2.stock_basic_current`

## Adaptors

### Built-in Adaptors

- **DummyAdaptor** (`src/ifa_data_platform/lowfreq/adaptors/dummy.py`): Returns mock data for testing.
- **TushareAdaptor** (`src/ifa_data_platform/lowfreq/adaptors/tushare.py`): Real Tushare API for trade_cal and stock_basic.

### Creating a Custom Adaptor

```python
from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult

class MyCustomAdaptor(BaseAdaptor):
    def fetch(self, dataset_name, watermark=None, limit=None, run_id=None, source_name="generic"):
        # Fetch data from your source
        return FetchResult(records=[...], watermark="2024-01-15", fetched_at="...")

    def test_connection(self):
        # Test your connection
        return True
```

## Testing

```bash
# Run all low-frequency tests
pytest tests/unit/test_lowfreq.py tests/integration/test_lowfreq_job3.py

# Run specific test class
pytest tests/unit/test_lowfreq.py::TestDatasetRegistry -v

# Run Job 3 integration tests
pytest tests/integration/test_lowfreq_job3.py -v
```

### Test Coverage

Job 3 integration tests cover:
- Runner trigger functionality
- Adaptor path (dummy and mocked Tushare)
- Raw persistence (store, retrieve, failure records)
- Canonical persistence (upsert, idempotent, bulk)
- Watermark advancement on repeat runs
- Idempotent re-run behavior
- Error status handling
- End-to-end registry-to-runner chain

## Job 4: Current/History/Version (Low-Frequency)

### Overview

Job 4 adds minimal current/history/version mechanics for iFA China-market / A-share datasets. The system maintains:
- **Current tables**: Fast query path for latest data
- **History tables**: Versioned snapshots for audit/replay
- **Version registry**: Track dataset versions with promote/active semantics

### Architecture

#### Version Lifecycle

1. **Ingest creates candidate**: New data creates a candidate version (status: `candidate`)
2. **Promote to active**: Candidate is promoted to active current (status: `active`)
3. **Supersedes previous**: Old active version becomes superseded (status: `superseded`)
4. **History retained**: All versions remain queryable via history tables

#### Database Schema Changes

New tables in `ifa2` schema (migration `004_lowfreq_version_history.py`):

- **`dataset_versions`**: Version registry tracking
  - `id`: Version UUID
  - `dataset_name`: Dataset name
  - `source_name`: Source name
  - `run_id`: Run that created this version
  - `created_at_utc`: Version creation time
  - `promoted_at_utc`: Promotion time (null for candidate)
  - `status`: candidate/active/superseded/archived
  - `is_active`: Boolean for fast lookup
  - `supersedes_version_id`: Previous active version ID
  - `watermark`: Watermark value
  - `metadata`: Optional metadata

- **`trade_cal_history`**: Historical trade calendar records
- **`stock_basic_history`**: Historical stock basic records

- **`version_id` column**: Added to `trade_cal_current` and `stock_basic_current`

#### Query Paths

##### Fast Current Query (Default)

```python
from ifa_data_platform.lowfreq.query import CurrentQuery

query = CurrentQuery()
trade_cal = query.get_trade_cal(date(2024, 1, 15), "SSE")
stocks = query.list_stock_basic(limit=100)
```

##### Version-Aware Query

```python
from ifa_data_platform.lowfreq.query import VersionQuery

vquery = VersionQuery()

# Get active version
active = vquery.get_active_version("trade_cal")

# Get version by ID
version = vquery.get_version_by_id("version-uuid")

# Get version at a specific time (as-of)
version = vquery.get_version_at("trade_cal", datetime(2024, 1, 15, 12, 0, 0))

# Query historical data
records = vquery.query_trade_cal_at_version(version_id, start_date, end_date)
records = vquery.query_stock_basic_at_version(version_id, limit=100)
```

##### As-of Query

```python
# Get data as-of a specific time
records = vquery.query_trade_cal_as_of(
    datetime(2024, 1, 15, 12, 0, 0),
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
)
records = vquery.query_stock_basic_as_of(
    datetime(2024, 1, 15, 12, 0, 0),
    limit=100,
)
```

#### Runner Integration

The runner automatically manages version lifecycle:

```python
from ifa_data_platform.lowfreq.runner import LowFreqRunner

runner = LowFreqRunner()

# Normal run: ingest -> promote to active
result = runner.run("trade_cal")

# Create candidate only (skip promotion)
result = runner.run("trade_cal", skip_promote=True)

# Explicit promotion
runner.promote("trade_cal", version_id)

# Get active version
version = runner.get_active_version("trade_cal")
```

#### Design Principles

1. **Provider-agnostic**: The adaptor interface ensures the framework is not tied to any specific data source.
2. **Minimal schema changes**: Uses existing patterns and adds minimal new tables via Alembic.
3. **Watermark support**: Date-based watermarking for incremental datasets.
4. **Idempotent operations**: Canonical current tables use UPSERT to handle repeat runs.
5. **Clear boundaries**: Raw/source mirror and canonical current are clearly separated.
6. **Audit capability**: Raw persistence stores full request/response for replay and debugging.
7. **Version tracking**: Explicit candidate -> promote -> active lifecycle.
8. **History retention**: All versions remain queryable via history tables.
9. **As-of support**: Query data at any point in time.

## Job 5: Multi-Round Versioned Ingestion Real-World Validation

### Overview

Job 5 validates versioned ingestion with multi-run tests for Tushare real datasets:
- trade_cal: China-market trading calendar
- stock_basic: A-share instrument master data

### Running Multi-Round Ingest

```bash
# Run specific dataset multiple times via runner
python -m ifa_data_platform.lowfreq.runner --dataset trade_cal
python -m ifa_data_platform.lowfreq.runner --dataset stock_basic

# Run all enabled datasets
python -m ifa_data_platform.lowfreq.runner
```

### Inspecting Dataset State

```python
from ifa_data_platform.lowfreq.version_persistence import DatasetVersionRegistry

registry = DatasetVersionRegistry()

# Get all versions
versions = registry.list_versions("trade_cal", limit=100)
print(f"Version count: {len(versions)}")

# Get active version
active = registry.get_active_version("trade_cal")
print(f"Active version: {active['id']}")
print(f"Status: {active['status']}")
print(f"Promoted at: {active['promoted_at_utc']}")

# Get superseded versions
for v in versions:
    if v["status"] == "superseded":
        print(f"Superseded: {v['id']}")
```

### Ingest Semantics

#### trade_cal: Incremental / Date-Watermark

- **Job Type**: `JobType.INCREMENTAL`
- **Watermark Strategy**: `WatermarkStrategy.DATE_BASED`
- **Behavior**: Each run fetches data from start_date to current date
- **Watermark**: Returns current date (YYYYMMDD) as watermark
- **Rerun**: Fetches all records from watermark point (replaces overlapping data)
- **Version**: New version each ingest, replaces previous active

#### stock_basic: Full Snapshot

- **Job Type**: `JobType.SNAPSHOT`
- **Watermark Strategy**: `WatermarkStrategy.NONE`
- **Behavior**: Each run fetches all active instruments (list_status=L)
- **Watermark**: Returns "full_snapshot" (real) or timestamp (DummyAdaptor)
- **Rerun**: Full refresh replaces canonical current
- **Version**: New version each ingest, replaces previous active

### Querying Historical Data

```python
from ifa_data_platform.lowfreq.query import VersionQuery, CurrentQuery
from datetime import datetime, timezone

# Current (latest) - fast path
current = CurrentQuery()
trade_cal_record = current.get_trade_cal(date(2024, 1, 15), "SSE")
stocks = current.list_stock_basic(limit=100)

# Version-aware query
vquery = VersionQuery()

# Get active version
active = vquery.get_active_version("trade_cal")

# Query historical by version ID
records = vquery.query_trade_cal_at_version(version_id, start_date, end_date)
records = vquery.query_stock_basic_at_version(version_id, limit=100)

# As-of query (version at point in time)
as_of = datetime.now(timezone.utc)
version_at = vquery.get_version_at("trade_cal", as_of)
```

### Tests

Run Job 5 integration tests:

```bash
# All Job 5 tests
pytest tests/integration/test_lowfreq_job5.py -v

# Test specific behavior
pytest tests/integration/test_lowfreq_job5.py::TestMultiRoundVersionGrowth -v
pytest tests/integration/test_lowfreq_job5.py::TestSupersededVersions -v
pytest tests/integration/test_lowfreq_job5.py::TestIngestSemantics -v
```

### Real Validation with Tushare

**Prerequisite**: Export Tushare token in environment:
```bash
export TUSHARE_TOKEN="your_tushare_token"
```

**Run validation script:**
```bash
python scripts/validate_job5.py
```

**Or via inline token:**
```bash
TUSHARE_TOKEN="your_token" .venv/bin/python scripts/validate_job5.py
```

**Manual real ingestion:**
```bash
# Run trade_cal multiple times
python -m ifa_data_platform.lowfreq.runner --dataset trade_cal
python -m ifa_data_platform.lowfreq.runner --dataset trade_cal
python -m ifa_data_platform.lowfreq.runner --dataset trade_cal

# Run stock_basic multiple times
python -m ifa_data_platform.lowfreq.runner --dataset stock_basic
python -m ifa_data_platform.lowfreq.runner --dataset stock_basic
python -m ifa_data_platform.lowfreq.runner --dataset stock_basic
```

### Key Validations

1. **Version Growth**: `dataset_versions` grows with each run
2. **Active Switch**: New version becomes active, previous becomes superseded
3. **Superseded Retention**: Old active versions marked superseded (not deleted)
4. **Promoted At**: `promoted_at_utc` set on promotion (monotonic increase)
5. **History Accumulation**: All versions stored in history tables (for trade_cal/stock_basic)
6. **Current Stability**: Canonical current reflects promoted version data
7. **Old-Version Query**: `get_version_at()` returns correct historical version
8. **Rerun Stability**: Multiple reruns create stable sequence of versions