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

### Database Schema

Two new tables in the `ifa2` schema:

- **`lowfreq_datasets`**: Stores dataset configurations
- **`lowfreq_runs`**: Stores run-level state

See migration `002_lowfreq.py` for details.

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
    dataset_name="china_a_share_daily",
    market=Market.CHINA_A_SHARE,
    source_name="tushare",
    job_type=JobType.INCREMENTAL,
    enabled=True,
    timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
    runner_type=RunnerType.DUMMY,
    watermark_strategy=WatermarkStrategy.DATE_BASED,
    budget_records_max=5000,
    budget_seconds_max=300,
    metadata={"api_name": "daily"},
    description="China A-share daily market data",
)

registry = DatasetRegistry()
dataset_id = registry.register(config)
```

### Run a Dataset

```bash
# Dry-run (simulate execution without writing data)
python -m ifa_data_platform.lowfreq.runner --dataset china_a_share_daily --dry-run

# Real-run
python -m ifa_data_platform.lowfreq.runner --dataset china_a_share_daily

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
result = runner.run("china_a_share_daily", dry_run=False)
print(f"Status: {result.status}, Records: {result.records_processed}, Watermark: {result.watermark}")

# Run all enabled datasets
results = runner.run_all(dry_run=True)
```

## Adaptors

### Built-in Adaptors

- **DummyAdaptor** (`src/ifa_data_platform/lowfreq/adaptors/dummy.py`): Returns mock data for testing and placeholder jobs.
- **TushareAdaptor** (`src/ifa_data_platform/lowfreq/adaptors/tushare.py`): Placeholder for Tushare China-market data.

### Creating a Custom Adaptor

```python
from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult

class MyCustomAdaptor(BaseAdaptor):
    def fetch(self, dataset_name, watermark=None, limit=None):
        # Fetch data from your source
        return FetchResult(records=[...], watermark="2024-01-15", fetched_at="...")

    def test_connection(self):
        # Test your connection
        return True
```

## Testing

```bash
# Run all low-frequency tests
pytest tests/unit/test_lowfreq.py

# Run specific test class
pytest tests/unit/test_lowfreq.py::TestDatasetRegistry -v
```

## Design Principles

1. **Provider-agnostic**: The adaptor interface ensures the framework is not tied to any specific data source.
2. **Minimal schema changes**: Uses existing `job_runs` pattern and adds minimal new tables.
3. **Watermark support**: Placeholder for date/datetime/version-based watermarking.
4. **Budget/limits**: Placeholder for record count and time budget enforcement.
5. **Clear boundaries**: Adaptor interface separates provider-specific logic from framework logic.