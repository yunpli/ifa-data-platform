# Job 8A — Lowfreq Base Extension Plan

## Scope

This job extends the existing lowfreq framework for the minimum P0 China-market base datasets required by iFA 2.0:

1. `index_basic`
2. `fund_basic_etf`
3. `sw_industry_mapping`

No facts/signals/report work in this job.

## Dataset list

### 1. index_basic
- Source: Tushare
- Purpose: Index master table for major China-market indices
- Expected key: `ts_code`
- Frequency: light daily refresh + weekend deep sync

### 2. fund_basic_etf
- Source: Tushare
- Purpose: ETF/fund master table, ETF-first subset for 2.0 market structure
- Expected key: `ts_code`
- Frequency: light daily refresh + weekend deep sync

### 3. sw_industry_mapping
- Source: Tushare
- Purpose: Shenwan industry hierarchy / security mapping substrate
- Expected key: composite mapping key derived from symbol/object pair
- Frequency: light daily refresh + weekend deep sync

## Field design

### index_basic current/history
- ts_code
- name
- market
- publisher
- category
- base_date
- base_point
- list_date
- weight_rule / desc (if available)
- version_id

### fund_basic_etf current/history
- ts_code
- name
- market
- fund_type
- management
- custodian
- list_date
- due_date
- issue_date
- delist_date
- invest_type
- benchmark
- status
- version_id

### sw_industry_mapping current/history
- index_code / industry_code
- industry_name
- level
- parent_code
- src
- member_ts_code (nullable if hierarchy row)
- member_name (nullable)
- in_date / out_date (nullable)
- is_active
- version_id

## Current/history design

All three datasets must follow the same existing framework shape:

- dataset registry entry
- runner-managed execution
- raw fetch persisted into `ifa2.lowfreq_raw_fetch`
- canonical current table
- version registry in `ifa2.dataset_versions`
- per-dataset history table
- current table carries `version_id`

## Daemon integration

Add all three datasets into both groups:

- `daily_light`
- `weekly_deep`

Execution semantics:

- trading day: normal ingest
- non-trading day: no heavy/full sync
- weekend: `weekly_deep` full sync path

Implementation preference:

- dataset-level gating should be explicit in adaptor/fetch path using current date + run context metadata
- daemon remains orchestration layer, not dataset business-logic layer

## Acceptance criteria

1. Datasets register successfully in registry
2. Real Tushare adaptor fetch path exists for all three datasets
3. Raw fetch rows are stored for all three datasets
4. Current tables populate correctly
5. Version rows grow across multiple ingests
6. History accumulates across multiple ingests
7. Daemon config includes all three datasets in `daily_light` and `weekly_deep`
8. Integration tests cover ingest, version growth, current correctness, daemon scheduling
9. Token remains only in local runtime config and is not committed
