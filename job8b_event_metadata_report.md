# Job 8B Implementation Report

**Date:** 2026-04-10  
**Status:** COMPLETED

## Scope

Added end-to-end lowfreq support for event/document metadata datasets:

1. `announcements` - China-market company announcements (anns_d API)
2. `news` - China-market financial news (news API)
3. `research_reports` - Broker research reports (research_report API)
4. `investor_qa` - Investor Q&A from 互动易 (irm_qa_sz + irm_qa_sh APIs)

This is metadata layer only — no full-text parsing, no NLP, no embeddings.

## Implementation Summary

### 1. Canonical Persistence (canonical_persistence.py)
- Added `AnnouncementsCurrent` class with upsert, bulk_upsert, get_by_ts_code, list_all
- Added `NewsCurrent` class with upsert, bulk_upsert, list_all
- Added `ResearchReportsCurrent` class with upsert, bulk_upsert, get_by_ts_code, list_all
- Added `InvestorQaCurrent` class with upsert, bulk_upsert, get_by_ts_code, list_all

### 2. Version History (version_persistence.py)
- Added `AnnouncementsHistory` class with store_version, query_by_version
- Added `NewsHistory` class with store_version, query_by_version
- Added `ResearchReportsHistory` class with store_version, query_by_version
- Added `InvestorQaHistory` class with store_version, query_by_version

### 3. Tushare Adaptor (adaptors/tushare.py)
- Added `_fetch_announcements()` method using anns_d API
- Added `_fetch_news()` method using news API
- Added `_fetch_research_reports()` method using research_report API
- Added `_fetch_investor_qa()` method using irm_qa_sz and irm_qa_sh APIs
- Updated `fetch()` to handle all 4 new datasets
- Updated `_persist_canonical()` to handle all 4 datasets

### 4. Runner Integration (runner.py)
- Added history instances for all 4 new datasets
- Updated `_store_version_history()` to handle all 4 datasets

### 5. Daemon Config (daemon_config.py)
- Updated both `daily_light` and `weekly_deep` groups to include:
  - announcements
  - news
  - research_reports
  - investor_qa

### 6. Database Migrations (alembic)
- `009_lowfreq_job8b.py` - Creates all current and history tables for 4 datasets

### 7. Dataset Registration
- Registered all 4 datasets in lowfreq_datasets table

## Test Results

All 17 integration tests pass:
- 3 tests for announcements canonical operations
- 2 tests for news canonical operations
- 3 tests for research_reports canonical operations
- 3 tests for investor_qa canonical operations
- 1 test for announcements history
- 1 test for news history
- 1 test for research_reports history
- 1 test for investor_qa history
- 2 tests for daemon config inclusion

Backward compatibility verified: Job 8A tests (16/16) pass.

## Data Verification

Current table record counts (after tests):
- announcements_current: 3 records
- news_current: 2 records
- research_reports_current: 3 records
- investor_qa_current: 3 records

History table record counts:
- announcements_history: 1 records
- news_history: 1 records
- research_reports_history: 1 records
- investor_qa_history: 1 records

## Limitations

1. Real Tushare API fetch requires valid token (not included in this commit)
2. News API returns data without date filtering (get all recent news)
3. investor_qa combines both SZSE (irm_qa_sz) and SSE (irm_qa_sh) sources
4. No full-text content stored (only metadata)

## Notes

- Token remains in local runtime config only (config/runtime/tushare.env)
- No secrets exposed or committed
- Daemon allows non-trading day execution (document data should not skip weekends)
- All 4 datasets follow the same version lifecycle pattern as existing datasets