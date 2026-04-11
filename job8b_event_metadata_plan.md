# Job 8B — Event/Document Low-Frequency Metadata Ingestion Plan

## Scope

Add 4 event/document metadata datasets to the lowfreq framework:

1. `announcements` - 上市公司全量公告 (China-market company announcements)
2. `news` - 即时财经新闻 (China-market financial news)
3. `research_reports` - 券商研究报告 (Broker research reports)
4. `investor_qa` - 互动易 IR问答 (Investor Q&A from 互动易 platform)

This is metadata layer only — no full-text parsing, no NLP, no embeddings.

## Dataset List

### 1. announcements (anns_d)
- **Source**: Tushare `anns_d` API
- **Purpose**: Company announcement metadata
- **Key**: ts_code + ann_date
- **Frequency**: Daily refresh (non-trading days allowed)

### 2. news (news)
- **Source**: Tushare `news` API
- **Purpose**: Financial news metadata
- **Key**: datetime + title (composite)
- **Frequency**: Daily refresh

### 3. research_reports (research_report)
- **Source**: Tushare `research_report` API
- **Purpose**: Broker research report metadata
- **Key**: ts_code + trade_date + title
- **Frequency**: Daily refresh

### 4. investor_qa (irm_qa_sz + irm_qa_sh)
- **Source**: Tushare `irm_qa_sz` (SZSE) + `irm_qa_sh` (SSE)
- **Purpose**: Investor Q&A / IR Q&A metadata
- **Key**: ts_code + trade_date + q (question)
- **Frequency**: Daily refresh

## Field Design

### announcements current/history
- ann_date
- ts_code
- name (stock name)
- title
- url
- rec_time (publish time)

### news current/history
- datetime
- classify (category)
- title
- source
- url
- content (optional, truncated)

### research_reports current/history
- trade_date
- ts_code
- name (stock name)
- title
- report_type
- author
- inst_csname (broker)
- ind_name (industry)
- url

### investor_qa current/history
- ts_code
- name (stock name)
- trade_date (Q&A date)
- q (question)
- a (answer)
- pub_time (answer time)

## Current/History Design

All 4 datasets follow existing framework:

- Dataset registry entry
- Runner-managed execution
- Raw fetch persisted to `ifa2.lowfreq_raw_fetch`
- Canonical current table
- Version registry in `ifa2.dataset_versions`
- Per-dataset history table
- Current table carries `version_id`

## Daemon Integration

Add all 4 datasets to both groups:
- `daily_light`
- `weekly_deep`

Key: Non-trading days allowed (document data should not skip weekends/holidays).

## Implementation Tasks

1. Add canonical persistence classes for all 4 datasets
2. Add version history classes for all 4 datasets  
3. Add Tushare API fetch methods for all 4 datasets
4. Update runner to handle new datasets
5. Update daemon config to include new datasets
6. Database migrations
7. Integration tests

## Acceptance Criteria

1. Datasets register in registry
2. Real Tushare API fetch works for all 4
3. Raw fetch stored
4. Current tables populate
5. Versions grow
6. History accumulates
7. Daemon includes all 4 datasets
8. Integration tests pass
9. Token remains local only