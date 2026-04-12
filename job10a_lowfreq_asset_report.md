# Job 10A Lowfreq Asset Report

## Overview
This report documents the implementation of Job 10A - adding 6 lowfreq asset-layer datasets to the main lowfreq chain.

**Implementation Date:** 2026-04-11

---

## Dataset List

The following 6 datasets were implemented:

| # | Dataset Name | Tushare API | Description |
|---|--------------|------------|-------------|
| 1 | top10_holders | top10_holders | Top 10 shareholders |
| 2 | top10_floatholders | top10_floatholders | Top 10 floating shareholders |
| 3 | pledge_stat | pledge_stat | Pledge statistics |
| 4 | stock_fund_forecast | stock_fund_forecast | Stock fund forecast |
| 5 | margin | margin | Margin trading data |
| 6 | north_south_flow | moneyflow_hsgt | North-South flow (HSGT) |

---

## Migration Status

### Migration Files Created

| File | Datasets |
|------|----------|
| `012_lowfreq_asset_batch1.py` | top10_holders, top10_floatholders, pledge_stat |
| `013_lowfreq_asset_batch2.py` | stock_fund_forecast, margin, north_south_flow |

### Table Schema

**Current Tables:**
- `ifa2.top10_holders_current`
- `ifa2.top10_floatholders_current`
- `ifa2.pledge_stat_current`
- `ifa2.stock_fund_forecast_current`
- `ifa2.margin_current`
- `ifa2.north_south_flow_current`

**History Tables:**
- `ifa2.top10_holders_history`
- `ifa2.top10_floatholders_history`
- `ifa2.pledge_stat_history`
- `ifa2.stock_fund_forecast_history`
- `ifa2.margin_history`
- `ifa2.north_south_flow_history`

---

## Current Counts

| Dataset | Current Count | Notes |
|---------|---------------|-------|
| top10_holders | N/A | Requires DB execution |
| top10_floatholders | N/A | Requires DB execution |
| pledge_stat | N/A | Requires DB execution |
| stock_fund_forecast | N/A | Requires DB execution |
| margin | N/A | Requires DB execution |
| north_south_flow | N/A | Requires DB execution |

**Note:** Current counts require running the migration and executing the daemon. Counts will be available after running:
```bash
alembic upgrade head
python scripts/register_job10a1_datasets.py
python scripts/register_job10a2_datasets.py
python -m ifa_data_platform.lowfreq.daemon
```

---

## History Counts

| Dataset | History Count | Notes |
|---------|---------------|-------|
| top10_holders | N/A | Requires DB execution |
| top10_floatholders | N/A | Requires DB execution |
| pledge_stat | N/A | Requires DB execution |
| stock_fund_forecast | N/A | Requires DB execution |
| margin | N/A | Requires DB execution |
| north_south_flow | N/A | Requires DB execution |

**Note:** History counts require version promotion after daemon runs.

---

## Version Status

### dataset_versions Table

| Dataset | Active Version | Status |
|---------|---------------|--------|
| top10_holders | N/A | Requires promotion |
| top10_floatholders | N/A | Requires promotion |
| pledge_stat | N/A | Requires promotion |
| stock_fund_forecast | N/A | Requires promotion |
| margin | N/A | Requires promotion |
| north_south_flow | N/A | Requires promotion |

**Note:** Version status will be populated after daemon execution completes successfully.

---

## Daemon Execution

### Group Configuration

All 6 datasets are wired into `weekly_deep` group in `daemon_config.py`:

```python
GroupConfig(
    group_name="weekly_deep",
    datasets=[
        "top10_holders",
        "top10_floatholders",
        "pledge_stat",
        "stock_fund_forecast",
        "margin",
        "north_south_flow",
        # ... existing datasets
    ],
    description="Weekly deep ingestion",
)
```

### Execution Result

**Status:** Pending daemon execution

The daemon is scheduled to run:
- **Schedule:** weekly_deep (Friday 10:00 Asia/Shanghai)
- **Runner:** LowFreqRunner with TushareAdaptor

To execute manually:
```bash
python -m ifa_data_platform.lowfreq.daemon --group weekly_deep
```

---

## Tests

### Test Results

**Syntax Validation:** Passed
- `canonical_persistence.py` - OK
- `version_persistence.py` - OK
- `tushare.py` - OK
- `runner.py` - OK
- `daemon_config.py` - OK

**Integration Tests:** Not run (requires DB)

To run tests:
```bash
python -m pytest tests/ -v
```

---

## Known Issues

1. **DB Connection Required:** Full validation requires PostgreSQL database connection with proper schema setup.

2. **Tushare Token:** Real ingest validation requires valid Tushare token in `config/runtime/tushare.env`.

3. **First Run:** On first execution, the system will fetch all historical data for each dataset. Subsequent runs will use watermark-based incremental fetching.

4. **Rate Limiting:** Tushare API has rate limits. The implementation uses token-backed validation but may need throttling for large datasets.

---

## Implementation Summary

### Files Modified

1. `alembic/versions/012_lowfreq_asset_batch1.py` - (existing) tables for top10_holders, top10_floatholders, pledge_stat
2. `alembic/versions/013_lowfreq_asset_batch2.py` - NEW tables for forecast, margin, north_south_flow
3. `src/ifa_data_platform/lowfreq/canonical_persistence.py` - NEW classes: StockFundForecastCurrent, MarginCurrent, NorthSouthFlowCurrent
4. `src/ifa_data_platform/lowfreq/version_persistence.py` - NEW classes: StockFundForecastHistory, MarginHistory, NorthSouthFlowHistory
5. `src/ifa_data_platform/lowfreq/adaptors/tushare.py` - NEW fetch methods and persistence handlers
6. `src/ifa_data_platform/lowfreq/runner.py` - NEW history wiring
7. `src/ifa_data_platform/lowfreq/daemon_config.py` - UPDATED weekly_deep group with all 6 datasets

### Files Created

1. `scripts/register_job10a2_datasets.py` - NEW registration script for new datasets
2. `job10a_lowfreq_asset_report.md` - This report

### Route

All datasets follow the standard route:
```
raw -> current -> history -> version
```

### Group Assignment

- `weekly_deep` - YES (all 6 datasets)
- `daily_light` - NO (not added per requirements)

---

## Validation Commands

To fully validate the implementation:

```bash
# 1. Run migrations
alembic upgrade head

# 2. Register datasets
python scripts/register_job10a1_datasets.py
python scripts/register_job10a2_datasets.py

# 3. Run daemon (weekly_deep group)
python -m ifa_data_platform.lowfreq.daemon --group weekly_deep

# 4. Check counts
psql -c "SELECT COUNT(*) FROM ifa2.top10_holders_current;" ifa_db
psql -c "SELECT COUNT(*) FROM ifa2.top10_floatholders_current;" ifa_db
psql -c "SELECT COUNT(*) FROM ifa2.pledge_stat_current;" ifa_db
psql -c "SELECT COUNT(*) FROM ifa2.stock_fund_forecast_current;" ifa_db
psql -c "SELECT COUNT(*) FROM ifa2.margin_current;" ifa_db
psql -c "SELECT COUNT(*) FROM ifa2.north_south_flow_current;" ifa_db

# 5. Check version status
psql -c "SELECT dataset_name, version_id, status FROM ifa2.dataset_versions WHERE dataset_name IN ('top10_holders', 'top10_floatholders', 'pledge_stat', 'stock_fund_forecast', 'margin', 'north_south_flow');" ifa_db
```

---

*Report generated: 2026-04-11*