# Job 8A Implementation Report

**Date:** 2026-04-10  
**Status:** COMPLETED

## Scope

Added end-to-end lowfreq support for:
1. `index_basic` - China-market index master data
2. `fund_basic_etf` - ETF/fund master data (ETF-first subset)
3. `sw_industry_mapping` - Shenwan industry hierarchy mapping

## Implementation Summary

### 1. Canonical Persistence (canonical_persistence.py)
- Added `IndexBasicCurrent` class with upsert, bulk_upsert, get_by_ts_code, list_all
- Added `FundBasicEtfCurrent` class with upsert, bulk_upsert, get_by_ts_code, list_all
- Added `SwIndustryMappingCurrent` class with upsert, bulk_upsert, get_by_member, list_all

### 2. Version History (version_persistence.py)
- Added `IndexBasicHistory` class with store_version, query_by_version
- Added `FundBasicEtfHistory` class with store_version, query_by_version
- Added `SwIndustryMappingHistory` class with store_version, query_by_version

### 3. Tushare Adaptor (adaptors/tushare.py)
- Added `_fetch_index_basic()` method
- Added `_fetch_fund_basic_etf()` method (ETF-first filter)
- Added `_fetch_sw_industry_mapping()` method (uses index_member)
- Updated `fetch()` to handle all three new datasets
- Updated `_persist_canonical()` to handle all three datasets

### 4. Runner Integration (runner.py)
- Added history instances for all three new datasets
- Updated `_store_version_history()` to handle all three datasets

### 5. Daemon Config (daemon_config.py)
- Updated both `daily_light` and `weekly_deep` groups to include:
  - index_basic
  - fund_basic_etf
  - sw_industry_mapping

### 6. Database Migrations (alembic)
- `006_lowfreq_job8a.py` - Creates all current and history tables
- `007_add_sw_constraint.py` - Adds unique constraint for sw_industry_mapping

## Test Results

All 16 integration tests pass:
- 3 tests for index_basic canonical operations
- 3 tests for fund_basic_etf canonical operations
- 4 tests for sw_industry_mapping canonical operations
- 2 tests for index_basic history
- 1 test for fund_basic_etf history
- 1 test for sw_industry_mapping history
- 2 tests for daemon config inclusion

Backward compatibility verified: Job 4 tests (12/12) pass.

## Notes

- Token remains in local runtime config only (config/runtime/tushare.env)
- No secrets exposed or committed
- ETF-first filtering in fund_basic_etf uses "ETF" substring in fund_type field
- SW industry mapping uses Tushare `index_member` API with src="sw" tag