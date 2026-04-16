# Full-Chain Alignment + Follow-up Run

_Date: 2026-04-16_0909_

## Scope
This batch clarifies:
1. Business Layer target alignment
2. full-chain logic per worker
3. touched-table / row-delta truth
4. key zero-result classifications
5. one follow-up run through the unified daemon entry

Artifacts generated:
- `scripts/analyze_full_chain.py`
- `artifacts/full_chain_analysis_2026-04-16_0905.json`
- `artifacts/acceptance_monitor/followup_pre.json`
- `artifacts/acceptance_monitor/followup_t_plus_3m.json`
- `artifacts/acceptance_monitor/followup_t_plus_10m.json`
- `artifacts/acceptance_monitor/followup_post.json`

## Business Layer alignment check result
### Verified list presence
Observed Business Layer list presence in DB:
- `default_key_focus`
  - list_type=`key_focus`
  - item_count=`20`
- `default_focus`
  - list_type=`focus`
  - item_count=`100`
- `default_archive_targets_15min`
  - list_type=`archive_targets`
  - frequency_type=`15min`
  - item_count=`40`
- `default_archive_targets_minute`
  - list_type=`archive_targets`
  - frequency_type=`minute`
  - item_count=`20`

### Missing Business Layer targets
Not present in the current accepted scope DB result:
- `default_tech_key_focus`
- `default_tech_focus`

That is an explicit Business Layer gap, not a source-side guess.

### Business Layer rule evidence
Observed rules include:
- `default_key_focus`: `target_size=20`
- `default_focus`: `target_size=100`
- `default_archive_targets_15min`: `granularity=15min`, `target_size=40`
- `default_archive_targets_minute`: `granularity=minute`, `target_size=20`

### Alignment judgment
- key_focus: present
- focus: present
- tech_key_focus: missing
- tech_focus: missing
- archive_targets: present for both 15min and minute

Therefore:
- any expected “tech_*” coverage is currently blocked at the Business Layer target-definition level
- that is not a source-empty problem
- that is not a runtime-daemon failure
- that is a Business Layer inclusion gap if tech-specific coverage is intended

## End-to-end full-chain explanation by worker

### 1. lowfreq
**Business Layer truth**
- lowfreq uses broad default manifest truth, not only a tiny focus list.
- latest run summary shows `manifest_item_count=240` and asset categories including:
  - `stock`
  - `futures`
  - `commodity`
  - `precious_metal`
  - `macro`

**Manifest / scope selection**
- unified daemon creates a manifest snapshot and planned dataset set.
- latest lowfreq planned datasets:
  - `trade_cal`
  - `stock_basic`
  - `index_basic`
  - `fund_basic_etf`
  - `sw_industry_mapping`
  - `announcements`
  - `news`
  - `research_reports`
  - `investor_qa`
  - `index_weight`
  - `etf_daily_basic`
  - `share_float`
  - `company_basic`
  - `stk_managers`
  - `new_share`
  - `name_change`
  - `top10_holders`
  - `top10_floatholders`
  - `pledge_stat`

**Worker execution scope**
- lowfreq executed all 19 planned datasets
- blocked dataset count: `0`

**Source fetch**
- source returned non-zero rows for all executed datasets in the observed runs
- no important lowfreq zero-result case appeared in the accepted/follow-up runs

**Storage write**
- writes went to canonical current/history lowfreq/reference tables
- runtime evidence landed in:
  - `unified_runtime_runs`
  - `job_runs`
  - `lowfreq_runs`

**Runtime evidence**
- latest follow-up lowfreq run:
  - status=`succeeded`
  - governance=`ok`
  - duration=`217995 ms`
  - runtime_budget_sec=`1800`

**Operator-visible result**
- operator can see:
  - unified run row
  - lowfreq job/run growth
  - current/history table growth
  - succeeded per-dataset summary in unified summary JSON

### 2. midfreq
**Business Layer truth**
- latest run summary shows `manifest_item_count=210`
- manifest preview symbols come from default focus universe
- asset categories in summary: `stock`

**Manifest / scope selection**
- planned datasets:
  - `equity_daily_bar`
  - `index_daily_bar`
  - `etf_daily_bar`
  - `northbound_flow`
  - `limit_up_down_status`
  - `margin_financing`
  - `southbound_flow`
  - `turnover_rate`
  - `main_force_flow`
  - `sector_performance`
  - `dragon_tiger_list`
  - `limit_up_detail`

**Worker execution scope**
- all 12 planned datasets executed
- blocked dataset count: `0`

**Source fetch**
- all datasets succeeded
- one important explicit zero-result case occurred:
  - `sector_performance` -> `records_processed=0`

**Storage write**
- writes landed in daily/flow/current-history midfreq tables
- runtime evidence landed in:
  - `unified_runtime_runs`
  - `job_runs`
  - `midfreq_execution_summary` (via runtime summary intent, though row-count view remained 0 in snapshots)

**Runtime evidence**
- latest follow-up midfreq run:
  - status=`succeeded`
  - governance=`ok`
  - duration=`96931 ms`
  - runtime_budget_sec=`1800`

**Operator-visible result**
- unified run row succeeded
- current/history tables advanced for most datasets
- one source-empty case (`sector_performance`) needs explicit classification

### 3. highfreq
**Business Layer truth**
- latest run summary shows `manifest_item_count=0`
- `manifest_preview_symbols=[]`
- highfreq scope is not currently driven by a populated BL symbol manifest in the same way as lowfreq/midfreq/archive

**Manifest / scope selection**
- planned datasets are hard runtime-scope datasets:
  - `stock_1m_ohlcv`
  - `index_1m_ohlcv`
  - `etf_sector_style_1m_ohlcv`
  - `futures_commodity_pm_1m_ohlcv`
  - `open_auction_snapshot`
  - `close_auction_snapshot`
  - `event_time_stream`

**Worker execution scope**
- all 7 planned datasets executed
- blocked dataset count: `0`

**Source fetch**
- all 7 returned non-zero rows in both acceptance and follow-up runs

**Storage write**
- writes landed in highfreq working tables
- runtime evidence landed in:
  - `unified_runtime_runs`
  - `job_runs`
  - `highfreq_runs`
- notable mismatch:
  - runtime summary claims `highfreq_execution_summary` in `tables_updated`
  - snapshot counts showed `highfreq_execution_summary=0`
  - this is an explicit storage/runtime evidence mismatch to track

**Runtime evidence**
- latest follow-up highfreq run:
  - status=`succeeded`
  - governance=`ok`
  - duration=`8523 ms`
  - runtime_budget_sec=`900`
  - execution_mode=`partial_real_run`

**Operator-visible result**
- unified run row succeeded
- highfreq working tables clearly grew
- derived-signal tables remained 0 in the follow-up run snapshots

### 4. archive
**Business Layer truth**
- archive target lists are present:
  - `default_archive_targets_15min` with 40 items
  - `default_archive_targets_minute` with 20 items

**Manifest / scope selection**
- latest summary shows:
  - `manifest_item_count=260`
  - archive total jobs=`13`
  - manifest preview symbols from archive targets

**Worker execution scope**
- archive window executed 13/13 jobs
- catch-up binding rows inserted/completed in follow-up summary: `0`

**Source fetch / progression**
- acceptance run advanced archive materially
- follow-up run then produced 0 records in all archive categories

**Storage write**
- archive writes/evidence land in:
  - `archive_runs`
  - `archive_checkpoints`
  - `archive_target_catchup`
  - `archive_summary_daily`
  - history tables like `stock_15min_history`, `stock_minute_history`, etc.

**Runtime evidence**
- latest follow-up archive run:
  - status=`succeeded`
  - governance=`ok`
  - duration=`144078 ms`
  - runtime_budget_sec=`3600`
  - final window summary: `13/13 succeeded, 0 failed, 0 records`

**Operator-visible result**
- operator sees a succeeded archive run with 0 records
- this is truthful continuation behavior after prior checkpoint advancement, not a runtime failure

## Touched-table / row-delta report per worker
Below, “before” is follow-up pre-snapshot and “after” is follow-up post-snapshot.

### lowfreq
| table | meaning | type | before | after | delta | business objects/categories |
|---|---|---|---:|---:|---:|---|
| `unified_runtime_runs` | unified run governance rows | runtime/audit | 4 | 8 | +4 | run evidence across all workers; lowfreq contributed one new row but table is global |
| `job_runs` | generic job-level evidence | runtime/audit | 4 | 8 | +4 | one new lowfreq job envelope plus other workers |
| `lowfreq_runs` | per-dataset lowfreq run rows | runtime/audit | 19 | 38 | +19 | 19 lowfreq datasets |
| `trade_cal_history` | trading calendar history | history | 124006 | 126304 | +2298 | exchange trading-calendar truth |
| `stock_basic_history` | stock basic reference history | history | 291690 | 297195 | +5505 | stock universe/reference |
| `index_basic_history` | index basic reference history | history | 424018 | 432018 | +8000 | index universe/reference |
| `fund_basic_etf_history` | ETF reference history | history | 380006 | 390006 | +10000 | ETF universe/reference |
| `sw_industry_mapping_history` | industry mapping history | history | 78005 | 81005 | +3000 | stock->SW industry mapping |
| `announcements_history` | announcement history | history | 117548 | 120589 | +3041 | listed-company announcements |
| `news_history` | news history | history | 49501 | 51001 | +1500 | news items |
| `research_reports_history` | research report history | history | 577 | 631 | +54 | broker/analyst reports |
| `investor_qa_history` | IR QA history | history | 7570 | 8134 | +564 | investor QA content |
| `index_weight_history` | index constituent weight history | history | 102608 | 107272 | +4664 | index weights |
| `etf_daily_basic_history` | ETF daily basic history | history | 120000 | 125000 | +5000 | ETF daily basic metrics |
| `share_float_history` | share float history | history | 84000 | 90000 | +6000 | float/share unlock data |
| `company_basic_history` | company basic history | history | 263340 | 269612 | +6272 | company profile/reference |
| `stk_managers_history` | management history | history | 56000 | 60000 | +4000 | company managers |
| `new_share_history` | IPO/new share history | history | 40000 | 42000 | +2000 | new share issuance |
| `name_change_history` | name change history | history | 260000 | 270000 | +10000 | stock name changes |
| `top10_holders_history` | top10 holders history | history | 80000 | 85000 | +5000 | top holders |
| `top10_floatholders_history` | top10 float holders history | history | 30000 | 35000 | +5000 | top float holders |
| `pledge_stat_history` | pledge stats history | history | 30000 | 35000 | +5000 | share pledge stats |

Lowfreq judgment:
- touched history/reference tables heavily
- zero-result issue: none observed in important lowfreq datasets

### midfreq
| table | meaning | type | before | after | delta | business objects/categories |
|---|---|---|---:|---:|---:|---|
| `unified_runtime_runs` | unified run governance rows | runtime/audit | 4 | 8 | +4 | one new midfreq row plus other workers |
| `job_runs` | generic job-level evidence | runtime/audit | 4 | 8 | +4 | one new midfreq job envelope plus other workers |
| `equity_daily_bar_history` | stock daily bar history | history | 340 | 360 | +20 | stock daily bars |
| `index_daily_bar_history` | index daily bar history | history | 215 | 223 | +8 | index daily bars |
| `etf_daily_bar_history` | ETF daily bar history | history | 312 | 324 | +12 | ETF daily bars |
| `northbound_flow_history` | northbound flow history | history | 11 | 12 | +1 | northbound capital flow |
| `limit_up_down_status_history` | limit-up/down breadth history | history | 12 | 13 | +1 | market breadth status |
| `margin_financing_history` | margin financing history | history | 3000 | 3360 | +360 | financing balance |
| `southbound_flow_history` | southbound flow history | history | 7 | 8 | +1 | southbound capital flow |
| `turnover_rate_history` | turnover history | history | 160 | 179 | +19 | turnover metrics |
| `main_force_flow_history` | main-force flow history | history | 539 | 559 | +20 | main-force capital flow |
| `sector_performance_history` | sector performance history | history | 0 | 0 | +0 | sector-level performance |
| `dragon_tiger_list_history` | 龙虎榜 history | history | 1918 | 1997 | +79 | dragon tiger list entries |
| `limit_up_detail_history` | limit-up detail history | history | 52794 | 60336 | +7542 | limit-up detailed records |

Midfreq judgment:
- most midfreq datasets wrote as expected
- `sector_performance_history` stayed 0 -> important explicit zero-result case

### highfreq
| table | meaning | type | before | after | delta | business objects/categories |
|---|---|---|---:|---:|---:|---|
| `unified_runtime_runs` | unified run governance rows | runtime/audit | 4 | 8 | +4 | one new highfreq row plus other workers |
| `job_runs` | generic job-level evidence | runtime/audit | 4 | 8 | +4 | one new highfreq job envelope plus other workers |
| `highfreq_runs` | lane-local highfreq run rows | runtime/audit | 7 | 14 | +7 | 7 highfreq datasets |
| `highfreq_stock_1m_working` | stock 1m working slice | working | 6 | 6 | +0 | 1m stock sample scope refreshed in place |
| `highfreq_index_1m_working` | index 1m working slice | working | 6 | 6 | +0 | 1m index sample scope refreshed in place |
| `highfreq_proxy_1m_working` | ETF/sector/style proxy working slice | working | 1 | 1 | +0 | proxy 1m slice |
| `highfreq_futures_minute_working` | futures/commodity/PM working slice | working | 40 | 40 | +0 | futures + commodity + precious metal minute data |
| `highfreq_open_auction_working` | open auction snapshot | working | 1 | 1 | +0 | open auction |
| `highfreq_close_auction_working` | close auction snapshot | working | 1 | 1 | +0 | close auction |
| `highfreq_event_stream_working` | event timestamp stream | working | 400 | 400 | +0 | event stream rows refreshed in place |
| `highfreq_sector_breadth_working` | breadth derived state | working | 0 | 0 | +0 | sector breadth |
| `highfreq_sector_heat_working` | heat derived state | working | 0 | 0 | +0 | sector heat |
| `highfreq_leader_candidate_working` | leader candidates | working | 0 | 0 | +0 | leader candidates |
| `highfreq_intraday_signal_state_working` | intraday signal state | working | 0 | 0 | +0 | signal state |
| `highfreq_limit_event_stream_working` | limit-event stream | working | 0 | 0 | +0 | limit event stream |
| `highfreq_active_scope` | active dynamic scope | working/state | 0 | 0 | +0 | scope management |
| `highfreq_dynamic_candidate` | dynamic candidate scope | working/state | 0 | 0 | +0 | candidate upgrade scope |

Highfreq judgment:
- many working tables are overwritten/refresh-style, so row delta alone can be 0 while the table was still touched
- operator truth must therefore use both row delta and worker summary/log evidence
- derived signal tables remained 0 in this run

### archive
| table | meaning | type | before | after | delta | business objects/categories |
|---|---|---|---:|---:|---:|---|
| `unified_runtime_runs` | unified run governance rows | runtime/audit | 4 | 8 | +4 | one new archive row plus other workers |
| `archive_runs` | archive job/run evidence | runtime/audit | 13 | 26 | +13 | 13 archive sub-jobs/categories/frequencies |
| `archive_checkpoints` | archive progress anchors | checkpoint | 18 | 18 | +0 | checkpoint rows updated, not new row creation |
| `archive_target_catchup` | catch-up backlog intents | checkpoint/catch-up | 8 | 8 | +0 | no new catch-up intents bound/inserted |
| `archive_summary_daily` | archive summary rollup | runtime/audit | 1 | 1 | +0 | summary refreshed/overwritten |
| `stock_15min_history` | stock 15min history | history | 1290 | 1290 | +0 | no new 15min stock rows in follow-up |
| `stock_minute_history` | stock minute history | history | 2410 | 2410 | +0 | no new minute stock rows in follow-up |
| `futures_15min_history` | futures 15min history | history | 22912 | 22912 | +0 | no new rows |
| `futures_minute_history` | futures minute history | history | 32000 | 32000 | +0 | no new rows |
| `commodity_15min_history` | commodity 15min history | history | 49456 | 49456 | +0 | no new rows |
| `commodity_minute_history` | commodity minute history | history | 56000 | 56000 | +0 | no new rows |
| `precious_metal_15min_history` | precious metal 15min history | history | 16000 | 16000 | +0 | no new rows |
| `precious_metal_minute_history` | precious metal minute history | history | 16000 | 16000 | +0 | no new rows |

Archive judgment:
- archive follow-up touched runtime/checkpoint evidence but added 0 history rows
- this is consistent with checkpoint continuation after the first acceptance run

## Key zero-result classifications
### 1. Missing `tech_key_focus` / `tech_focus`
Classification:
- **Business Layer target gap**

Why:
- explicit BL alignment check found no `default_tech_key_focus` or `default_tech_focus` lists
- therefore any expected tech-specific scope is currently absent before manifest/runtime/source execution even begins

### 2. `midfreq.sector_performance = 0`
Classification:
- **source returned empty** (current best truthful classification)

Why:
- dataset was present in planned scope
- dataset executed, status=`succeeded`
- runtime did not skip it
- manifest did not exclude it
- storage mapping exists (`sector_performance_current/history`)
- row delta remained 0
- therefore the chain did not break at BL/scope/runtime/storage; the source result was empty for this run

### 3. archive follow-up run all-zero result
Classification:
- **checkpoint continuation / no remaining new material in current scope**

Why:
- archive targets are present in BL
- archive executed 13/13 jobs successfully
- first acceptance run advanced 1291 records
- second follow-up run advanced 0 records with succeeded status
- `archive_target_catchup` remained 8 and no new bound/completed catch-up rows were inserted
- history tables showed 0 delta in follow-up
- therefore 0 is explained by already-advanced checkpoints/current continuation state, not runtime failure

### 4. highfreq derived tables remaining 0
Classification:
- **runtime/scope limitation or truthful no-signal outcome; not BL target gap**

Why:
- highfreq latest summary shows `manifest_item_count=0` and `manifest_preview_symbols=[]`
- highfreq planned datasets are hard runtime-scope raw datasets, not BL-symbol-driven in the same way as low/mid/archive
- raw/working tables for 1m/open/close/event all executed successfully with non-zero processed rows
- derived-signal tables (`sector_breadth`, `sector_heat`, `leader_candidate`, `intraday_signal_state`, `limit_event_stream`, `active_scope`, `dynamic_candidate`) remained 0
- so the zero is downstream of raw data capture, not a source connectivity failure and not a BL focus-list absence for current raw scope

### 5. `highfreq_execution_summary` row count staying 0 while runtime says it was updated
Classification:
- **storage/runtime evidence mismatch**

Why:
- run summary lists `ifa2.highfreq_execution_summary` in `tables_updated`
- snapshot counts remained `0`
- therefore this needs targeted follow-up in code/storage mapping; current operator-visible truth should rely on unified run row + highfreq_runs + working tables rather than trusting that summary table count alone

### 6. `midfreq_execution_summary` row count staying 0 in snapshots
Classification:
- **storage/runtime evidence mismatch or non-materialized summary path**

Why:
- unified summary lists it in `tables_updated`
- row-count snapshots remained `0`
- same operator caveat as above: use unified runtime row + touched history tables as authoritative evidence until summary-table materialization is confirmed

## Follow-up run results
Commands used were the same unified-daemon entry with the same budgets:
- lowfreq: `1800 sec`
- midfreq: `1800 sec`
- highfreq: `900 sec`
- archive: `3600 sec`

### Follow-up final outcomes
- lowfreq: `succeeded`, `217995 ms`
- midfreq: `succeeded`, `96931 ms`
- highfreq: `succeeded`, `8523 ms`
- archive: `succeeded`, `144078 ms`

### Follow-up interpretation
- lowfreq: chain re-verified; large history deltas again confirm storage path truth
- midfreq: chain re-verified; `sector_performance` remained explicit source-empty case
- highfreq: chain re-verified for raw/working datasets; derived/evidence tables still require follow-up explanation in code/storage path
- archive: second-pass 0-row result confirmed as continuation/checkpoint truth, not runtime failure

## Final truthful judgment after this batch
1. **Unified runtime/governance layer is proven.**
2. **Business Layer alignment is incomplete for tech-specific coverage.**
   - `key_focus` and `focus` are present
   - `archive_targets` are present
   - `tech_key_focus` and `tech_focus` are missing
3. **Lowfreq full chain is healthy** for the current accepted dataset set.
4. **Midfreq full chain is mostly healthy**, with `sector_performance` currently best classified as source-empty, not BL/scope/runtime missing.
5. **Highfreq full chain is healthy for raw working capture**, but operator summary/derived-state materialization still has mismatches/zeros that need a separate cleanup/debug batch if those tables are expected to be populated.
6. **Archive full chain is healthy and now better understood**:
   - first pass advanced data materially
   - second pass produced 0 because checkpoints already advanced and no new material remained in current scope
7. **Important coverage gap remains on Business Layer side** if tech-specific focus coverage is intended:
   - add `tech_key_focus`
   - add `tech_focus`

## Recommended next action
Before calling the data-layer fully production-clear:
1. decide whether `tech_key_focus` / `tech_focus` should exist in Business Layer now
2. if yes, add them first
3. verify whether `highfreq_execution_summary` / `midfreq_execution_summary` are intended to materialize rows or only be logical table references
4. if summary rows are intended, fix that storage/evidence mismatch before final production declaration
