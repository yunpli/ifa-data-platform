# D2 Stock Archive Report

**Date:** 2026-04-13
**Status:** Completed

## D2 Overview

D2 implements the stock historical archive layer on top of the D1 archive framework. This provides persistent storage of stock daily OHLCV data for historical backfill and analysis.

## What Was Implemented

### 1. Database Schema (Migration 018)

**Tables Created:**
- `ifa2.stock_daily_history` - Stock daily OHLCV data archive
  - ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
  - Primary key: (ts_code, trade_date) unique index
- `ifa2.stock_history_checkpoint` - Checkpoint persistence for resume

### 2. Archive Implementation

**Stock Daily Archiver (`stock_daily_archiver.py`):**
- Fetches daily data from Tushare `daily` API
- Supports configurable stock universe (top 20 active stocks default)
- Checkpoint-based backfill with resume support
- Idempotent writes using INSERT ON CONFLICT DO NOTHING

### 3. Job Integration

**Configured Job:**
- `stock_daily_archive` - Stock daily historical data archive
- Dataset: `stock_daily`, asset_type: `stock`

**Orchestrator Routing:**
- Routes stock jobs to `_process_stock_job()` 
- Uses real Tushare data fetch

## Testing Results

### First Run
```
Job stock_daily_archive: 4819 records archived
```

### Second Run (Resume)
```
Job stock_daily_archive: 0 records (already processed)
Checkpoints correctly advanced
```

### Data Verification
- 4826 records in stock_daily_history
- Checkpoint shows batch_no=20, last_completed_date=2026-04-12
- archive_runs shows proper status tracking

## Deferred Items

The following are explicitly deferred to future phases:
1. **Minute history** - Requires separate API (pro_bar) and storage
2. **Full market scope** - Currently limited to top 20 active stocks
3. **Multiple exchanges** - Currently focused on A-share universe

## Health/Watchdog Status

- Health: Shows checkpoint_advanced=true (stock path working)
- Watchdog: Reports alive/stale based on last run time
- Archive runs properly tracked in archive_runs table

## Checkpoint Unification Fix (2026-04-13)

### Problem Identified

Two checkpoint tables existed with inconsistent state:
- `stock_history_checkpoint` - Stock-specific checkpoint (D2 native)
- `archive_checkpoints` - Unified archive framework checkpoint

State before fix:
- stock_history_checkpoint: last_completed_date=2026-04-12, batch_no=20, status=completed
- archive_checkpoints: last_completed_date=2025-05-17, batch_no=5, status=completed

This caused "业务路径推进了，但 archive_checkpoints 没推进" mismatch.

### Solution Implemented

1. **Immediate sync**: Updated archive_checkpoints to match stock_history_checkpoint
2. **Code fix**: Modified `stock_daily_archiver.py` to sync both tables on every checkpoint update
   - Added `sync_to_archive_checkpoints()` method
   - `upsert_checkpoint()` now writes to both tables atomically

### Unified Checkpoint口径

After fix, both tables are kept in sync:
- **Primary source for stock path**: `stock_history_checkpoint`
- **Framework checkpoint**: `archive_checkpoints` (synced from stock_history_checkpoint)
- Checkpoint consistency verified on every run

## Current State (Post-Fix)

- stock_history_checkpoint: last_completed_date=2026-04-13, batch_no=5, status=completed
- archive_checkpoints: last_completed_date=2026-04-13, batch_no=5, status=completed
- stock_daily_history: 4831 records
- Checkpoint consistency: VERIFIED

## Sign-off

D2 stock historical archive layer is complete and functional:
- Real Tushare data fetching works
- Checkpoint/resume operational
- Checkpoint tables unified (stock_history_checkpoint + archive_checkpoints)
- Health monitoring reflects stock path
- Documentation delivered

**Ready for next phase (D3 Macro).**