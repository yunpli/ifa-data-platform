# Job 9 — Event Surface Extension + Slow Variable Enhancement

## Scope

Job 9 extends lowfreq for P0 event metadata and P1 slow variables:

1. News metadata
2. Research report metadata
3. Secretary Q&A / IR Q&A
4. Slow variables: name change, IPO, management, dividend, capital change (select 2–4 high-value items)
5. Daemon group semantics: `daily_light` for metadata, `weekly_deep` for heavy slow variables

No facts/signals/report work in this job.

## Dataset List

### P0 Event Metadata

#### 1. news_basic
- Source: Tushare `news`
- Purpose: China-market financial news metadata
- Expected key: `ts_code` + `datetime`
- Frequency: daily_light

#### 2. stock_repurchase
- Source: Tushare `stock_repurchase`
- Purpose: Stock repurchase announcements
- Expected key: `ts_code` + `ann_date`
- Frequency: daily_light

#### 3. stock_dividend
- Source: Tushare `dividend`
- Purpose: Dividend announcements
- Expected key: `ts_code` + `divi_date`
- Frequency: daily_light

### P1 Slow Variables

#### 4. name_change
- Source: Tushare `stock_namechange`
- Purpose: Security name change history
- Expected key: `ts_code` + `start_date`
- Frequency: weekly_deep

#### 5. new_stock
- Source: Tushare `new_share`
- Purpose: IPO schedule and results
- Expected key: `ts_code`
- Frequency: weekly_deep

#### 6. management
- Source: Tushare `stock_manager`
- Purpose: Management team information
- Expected key: `ts_code` + `end_date`
- Frequency: weekly_deep

#### 7. stock_equity_change
- Source: Tushare `stock_equity_change`
- Purpose: Equity changes (capital increase/decrease)
- Expected key: `ts_code` + `ann_date`
- Frequency: weekly_deep

## Field Design

### news_basic current/history
- ts_code
- title
- content
- datetime
- source
- url
- version_id

### stock_repurchase current/history
- ts_code
- ann_date
- holder_name
- holder_type
- repur_amount
- repur_price
- volume
- progress
- version_id

### stock_dividend current/history
- ts_code
- divi_date
- divi_cash
- divi_stock
- record_date
- ex_date
- pay_date
- ann_date
- version_id

### name_change current/history
- ts_code
- name
- start_date
- end_date
- version_id

### new_stock current/history
- ts_code
- name
- ipo_date
- issue_date
- offer_price
- total_share
- net_assets
- pe
- venue
- status
- version_id

### management current/history
- ts_code
- name
- gender
- title
- edu
- nationality
- birthday
- begin_date
- end_date
- resume
- version_id

### stock_equity_change current/history
- ts_code
- ann_date
- change_type
- change_vol
- change_pct
- after_share
- after_capital
- version_id

## Current/History Design

All datasets follow existing framework shape:
- dataset registry entry
- runner-managed execution
- raw fetch persisted into `ifa2.lowfreq_raw_fetch`
- canonical current table
- version registry in `ifa2.dataset_versions`
- per-dataset history table
- current table carries `version_id`

## Daemon Integration

Add all datasets to daemon groups:
- `daily_light`: news_basic, stock_repurchase, stock_dividend
- `weekly_deep`: name_change, new_stock, management, stock_equity_change

## Acceptance Criteria

1. All 7 datasets register successfully in registry
2. Real Tushare adaptor fetch path exists for all datasets
3. Raw fetch rows stored for all datasets
4. Current tables populate correctly
5. Version rows grow across multiple ingests
6. History accumulates across multiple ingests
7. Daemon config includes all datasets in correct groups
8. Integration tests cover ingest, version growth, current correctness
9. Token remains only in local runtime config