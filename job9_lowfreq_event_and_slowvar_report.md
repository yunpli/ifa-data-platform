# Job 9 Implementation Report

**Date:** 2026-04-10  
**Status:** IN PROGRESS

## Scope

Job 9 extends lowfreq for P0 event metadata and P1 slow variables:
1. News metadata (news_basic)
2. Stock repurchase (stock_repurchase)
3. Stock dividend (stock_dividend)
4. Name change (name_change)
5. New stock/IPO (new_stock)
6. Management (management)
7. Stock equity change (stock_equity_change)

## Implementation Summary

### 1. Canonical Persistence (canonical_persistence.py)
- Added `NewsBasicCurrent` class with upsert, bulk_upsert
- Added `StockRepurchaseCurrent` class with upsert, bulk_upsert
- Added `StockDividendCurrent` class with upsert, bulk_upsert
- Added `NameChangeCurrent` class with upsert, bulk_upsert
- Added `NewStockCurrent` class with upsert, bulk_upsert
- Added `ManagementCurrent` class with upsert, bulk_upsert
- Added `StockEquityChangeCurrent` class with upsert, bulk_upsert

### 2. Version History (version_persistence.py)
- Added `NewsBasicHistory` class with store_version, query_by_version
- Added `StockRepurchaseHistory` class with store_version, query_by_version
- Added `StockDividendHistory` class with store_version, query_by_version
- Added `NameChangeHistory` class with store_version, query_by_version
- Added `NewStockHistory` class with store_version, query_by_version
- Added `ManagementHistory` class with store_version, query_by_version
- Added `StockEquityChangeHistory` class with store_version, query_by_version

### 3. Tushare Adaptor (adaptors/tushare.py)
- Added `_fetch_news_basic()` method using Tushare `news` API
- Added `_fetch_stock_repurchase()` method using Tushare `stock_repurchase` API
- Added `_fetch_stock_dividend()` method using Tushare `dividend` API
- Added `_fetch_name_change()` method using Tushare `stock_namechange` API
- Added `_fetch_new_stock()` method using Tushare `new_share` API
- Added `_fetch_management()` method using Tushare `stock_manager` API
- Added `_fetch_stock_equity_change()` method using Tushare `stock_equity_change` API
- Updated `fetch()` to handle all seven new datasets
- Updated `_persist_canonical()` to handle all seven datasets

### 4. Runner Integration (runner.py)
- Added history instances for all seven new datasets
- Updated `_store_version_history()` to handle all seven datasets

### 5. Daemon Config (daemon_config.py)
- Updated `daily_light` group to include: news_basic, stock_repurchase, stock_dividend
- Updated `weekly_deep` group to include: name_change, new_stock, management, stock_equity_change

### 6. Dataset Registration
- Created `scripts/register_job9_datasets.py` to register all 7 new datasets

### 7. Database Migrations (alembic)
- `008_lowfreq_job9.py` - Creates all current and history tables for the 7 new datasets

## Acceptance Criteria

1. [ ] All 7 datasets register successfully in registry
2. [ ] Real Tushare adaptor fetch path exists for all datasets
3. [ ] Raw fetch rows stored for all datasets
4. [ ] Current tables populate correctly
5. [ ] Version rows grow across multiple ingests
6. [ ] History accumulates across multiple ingests
7. [ ] Daemon config includes all datasets in correct groups
8. [ ] Integration tests cover ingest, version growth, current correctness
9. [ ] Token remains only in local runtime config

## Notes

- Token remains in local runtime config only (config/runtime/tushare.env)
- No secrets exposed or committed
- P0 datasets (daily_light): news_basic, stock_repurchase, stock_dividend
- P1 datasets (weekly_deep): name_change, new_stock, management, stock_equity_change