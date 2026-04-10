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

## Design Principles

1. **Provider-agnostic**: The adaptor interface ensures the framework is not tied to any specific data source.
2. **Minimal schema changes**: Uses existing patterns and adds minimal new tables via Alembic.
3. **Watermark support**: Date-based watermarking for incremental datasets.
4. **Idempotent operations**: Canonical current tables use UPSERT to handle repeat runs.
5. **Clear boundaries**: Raw/source mirror and canonical current are clearly separated.
6. **Audit capability**: Raw persistence stores full request/response for replay and debugging.