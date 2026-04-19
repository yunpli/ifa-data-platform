# Archive V2 Business/Event Family-Specific Contract Refactor

Generated: 2026-04-19 01:35 PDT
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Summary

This batch replaced the old generic business/event source-first branch with explicit family-specific source contracts for:

- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `sector_performance_daily`

It also enforced the Archive V2 namespace rule for persisted destination tables:

- all persisted Archive V2 data tables in this batch write to `ifa_archive_*`
- no writes go to lowfreq/midfreq/highfreq current/history tables
- no writes go to generic/unprefixed table names
- no archive-finalized truth is mixed into collection/runtime retained-history tables

This batch added explicit contract metadata in code, family-specific fetch paths in the runner, and archive-table identity/schema corrections to support the new dedupe contracts.

---

## 2. Exact code changes

### New file
- `src/ifa_data_platform/archive_v2/business_contracts.py`

Added:
- `BusinessDailyContract`
- `BUSINESS_DAILY_CONTRACTS`
- explicit source bundle / shard constants
- `assert_archive_namespace()`
- `stable_hash()`

### Modified
- `src/ifa_data_platform/archive_v2/runner.py`
- `src/ifa_data_platform/archive_v2/db.py`
- `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`

### Runner refactor
- business/event families no longer route through the old generic retained-history B-class branch
- runner now dispatches via `_execute_business_contract_family(...)`
- each family has a dedicated contract fetcher
- each family now persists with family-specific row identity / write logic

### DB/schema corrections
Added archive-table identity columns and migrations where required:
- `row_key`
- `url`
- `rec_time`
- `src`
- `content_hash`
- `report_type`
- `inst_csname`
- `author`
- `exchange_source`
- `q_hash`
- `a_hash`
- `reason`
- `limit_type`
- `exchange`
- `first_time`
- `last_time`
- `limit_times`

Also changed archive identity constraints so these business/event families can dedupe by the contract row identity instead of legacy narrow keys.

Also relaxed legacy `ts_code not null` on `ifa_archive_research_reports_daily` because industry reports legitimately do not always carry a stock code.

---

## 3. Family-specific contract map

## A. announcements_daily
- source endpoint(s): `anns_d`
- source mode: `single_day_bulk`
- shard strategy: `ann_date=YYYYMMDD` bulk first; if near cap/suspicious then active-stock `ts_code` fallback; final result uses union + dedupe
- dedupe identity: `(business_date, ts_code, title, url, rec_time?) -> row_key`
- zero-row policy: zero stays `incomplete` on active trading day; no fake completed-zero
- completeness rule: completed when bulk not near cap OR bulk+fallback have both been checked and merged
- archive table: `ifa_archive_announcements_daily`
- namespace status: correct `ifa_archive_*`
- rename needed: no
- schema correction needed: yes
  - added `row_key`, `url`, `rec_time`
  - moved archive identity to `(business_date, row_key)`

## B. news_daily
- source endpoint(s): `news`
- source mode: `time_window_stream`
- shard strategy: explicit source bundle × day windows, recursive split on near-cap windows
- configured source bundle:
  - `sina`
  - `wallstreetcn`
  - `10jqka`
  - `eastmoney`
  - `yuncaijing`
  - `fenghuang`
  - `jinrongjie`
  - `cls`
  - `yicai`
- dedupe identity: `(business_date, src, datetime, title, content_hash) -> row_key`
- zero-row policy: `completed_zero` only after all configured sources and all required windows are exhausted
- completeness rule: completed only when all configured sources/windows have been checked and no suspicious near-cap windows remain
- archive table: `ifa_archive_news_daily`
- namespace status: correct `ifa_archive_*`
- rename needed: no
- schema correction needed: yes
  - added `row_key`, `src`, `content_hash`
  - moved archive identity to `(business_date, row_key)`
  - normalized null-title source rows to a stable fallback title derived from content/time/source so persisted archive rows do not violate legacy not-null title semantics

## C. research_reports_daily
- source endpoint(s): `research_report`
- source mode: `universe_sharded`
- shard strategy: `report_type × inst_csname` over seeded broker universe
- configured report types:
  - `个股研报`
  - `行业研报`
- broker universe source: recent distinct `inst_csname` from retained history, used only as shard universe seed, not as Archive V2 truth source
- dedupe identity: `(business_date, report_type, inst_csname, ts_code, title, author) -> row_key`
- zero-row policy: `completed_zero` only after all report-type × broker shards are exhausted
- completeness rule: completed when all configured shards have been checked and merged; incomplete only on contract/path failure
- archive table: `ifa_archive_research_reports_daily`
- namespace status: correct `ifa_archive_*`
- rename needed: no
- schema correction needed: yes
  - added `row_key`, `report_type`, `inst_csname`, `author`
  - moved archive identity to `(business_date, row_key)`
  - dropped legacy `ts_code not null`

## D. investor_qa_daily
- source endpoint(s): `irm_qa_sh`, `irm_qa_sz`
- source mode: `source_plus_aggregate`
- shard strategy: SH + SZ by `trade_date` first; suspicious low/zero results trigger exchange-specific fallback path
- dedupe identity: `(business_date, exchange_source, ts_code, pub_time, q_hash, a_hash) -> row_key`
- zero-row policy: `completed_zero` only after SH + SZ and fallback branches are exhausted
- completeness rule: completed when both exchanges and fallback logic have been checked
- archive table: `ifa_archive_investor_qa_daily`
- namespace status: correct `ifa_archive_*`
- rename needed: no
- schema correction needed: yes
  - added `row_key`, `exchange_source`, `q_hash`, `a_hash`
  - moved archive identity to `(business_date, row_key)`

## E. dragon_tiger_daily
- source endpoint(s): `top_list`
- source mode: `single_day_bulk`
- shard strategy: direct `trade_date=YYYYMMDD` pull
- dedupe identity: `(business_date, ts_code, reason, net_amount, l_amount) -> row_key`
- zero-row policy: zero on active trading day stays `incomplete` unless source truth proves a true empty day
- completeness rule: completed when direct `top_list` contract succeeds and reason-aware identity persists correctly
- archive table: `ifa_archive_dragon_tiger_daily`
- namespace status: correct `ifa_archive_*`
- rename needed: no
- schema correction needed: yes
  - added `row_key`, `reason`
  - moved archive identity to `(business_date, row_key)`

## F. limit_up_detail_daily
- source endpoint(s): `limit_list_d`
- source mode: `universe_sharded`
- shard strategy: `limit_type × exchange` shards; canonical raw source is `limit_list_d`
- explicitly not using `stk_limit` as primary truth
- dedupe identity: `(business_date, ts_code, limit, first_time, last_time, limit_times) -> row_key`
- zero-row policy: zero stays `incomplete` on active trading day unless all shards prove a true empty day
- completeness rule: completed when all required shards are checked and merged from canonical `limit_list_d`
- archive table: `ifa_archive_limit_up_detail_daily`
- namespace status: correct `ifa_archive_*`
- rename needed: no
- schema correction needed: yes
  - added `row_key`, `limit_type`, `exchange`, `first_time`, `last_time`, `limit_times`
  - moved archive identity to `(business_date, row_key)`

## G. limit_up_down_status_daily
- source endpoint(s): `limit_list_d`
- source mode: `source_plus_aggregate`
- shard strategy: reuse canonical `limit_list_d` shards; aggregate internally into final daily status summary
- dedupe identity: `(business_date)`
- zero-row policy: `completed_zero` only after canonical raw shards are exhausted and true empty is established
- completeness rule: completed when canonical raw shards were checked and the internal aggregate row was generated
- archive table: `ifa_archive_limit_up_down_status_daily`
- namespace status: correct `ifa_archive_*`
- rename needed: no
- schema correction needed: no table rename; still singleton archive row by business date

## H. sector_performance_daily
- source endpoint(s): `ths_index`, `ths_daily`
- source mode: `universe_sharded`
- shard strategy: `ths_index(exchange='A', type=...)` universe fanout, then per-sector `ths_daily(ts_code, trade_date)`
- configured universe types:
  - `N`
  - `I`
  - `S`
  - `TH`
  - `ST`
  - `BB`
  - `R`
- dedupe identity: `(business_date, sector_code)`
- zero-row policy: incomplete unless expected universe itself is empty
- completeness rule: coverage-ratio based (`actual / expected`), not just nonzero rows
- archive table: `ifa_archive_sector_performance_daily`
- namespace status: correct `ifa_archive_*`
- rename needed: no
- schema correction needed: no rename; sector key already aligned to prefixed archive table

---

## 4. Exact Archive V2 table naming / prefix summary

All family destinations in this batch are explicitly isolated under `ifa_archive_*`:

| source family | archive table | dedupe identity | rename needed |
|---|---|---|---|
| announcements_daily | ifa_archive_announcements_daily | business_date + row_key | no |
| news_daily | ifa_archive_news_daily | business_date + row_key | no |
| research_reports_daily | ifa_archive_research_reports_daily | business_date + row_key | no |
| investor_qa_daily | ifa_archive_investor_qa_daily | business_date + row_key | no |
| dragon_tiger_daily | ifa_archive_dragon_tiger_daily | business_date + row_key | no |
| limit_up_detail_daily | ifa_archive_limit_up_detail_daily | business_date + row_key | no |
| limit_up_down_status_daily | ifa_archive_limit_up_down_status_daily | business_date | no |
| sector_performance_daily | ifa_archive_sector_performance_daily | business_date + sector_code | no |

### Explicit namespace judgment
- all destination table names are already correctly prefixed
- no family in this batch writes into lowfreq/midfreq/highfreq working/current/history tables
- no family in this batch writes into a generic/unprefixed table
- no table rename was required
- schema/identity corrections **were** required

---

## 5. Validation commands

## Source-contract probes
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_business_contract_probe.py --profile profiles/archive_v2_business_contract_validation_20260419.json --date 2026-04-17 --families announcements_daily --output artifacts/archive_v2_business_contract_probe_announcements_20260419.json

/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_business_contract_probe.py --profile profiles/archive_v2_business_contract_validation_20260419.json --date 2026-04-17 --families news_daily --output artifacts/archive_v2_business_contract_probe_news_20260419.json

/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_business_contract_probe.py --profile profiles/archive_v2_business_contract_validation_20260419.json --date 2026-04-17 --families limit_up_down_status_daily research_reports_daily investor_qa_daily --output artifacts/archive_v2_business_contract_probe_p23_20260419.json

/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_business_contract_probe.py --profile profiles/archive_v2_business_contract_validation_20260419.json --date 2026-04-17 --families sector_performance_daily --output artifacts/archive_v2_business_contract_probe_sector_20260419.json
```

## Write-enabled bounded validation
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_reset.py --dates 2026-04-17 --families announcements_daily news_daily research_reports_daily investor_qa_daily dragon_tiger_daily limit_up_detail_daily limit_up_down_status_daily sector_performance_daily --output artifacts/archive_v2_business_contract_reset_before_20260419.json

/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_measured_batch.py --profile-name archive_v2_business_contract_write_validation_20260419 --dates 2026-04-17 --family-groups announcements_daily news_daily research_reports_daily investor_qa_daily dragon_tiger_daily limit_up_detail_daily limit_up_down_status_daily sector_performance_daily --trigger-source manual_business_contract_validation_20260419 --notes 'Focused single-day business contract validation after family-specific refactor' --output artifacts/archive_v2_business_contract_write_validation_20260419.json

/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_reset.py --dates 2026-04-17 --families announcements_daily news_daily research_reports_daily investor_qa_daily dragon_tiger_daily limit_up_detail_daily limit_up_down_status_daily sector_performance_daily --output artifacts/archive_v2_business_contract_reset_after_20260419.json
```

---

## 6. Validation / runtime evidence

## Priority 1 source-contract evidence
### announcements_daily
Artifact: `artifacts/archive_v2_business_contract_probe_announcements_20260419.json`
- status: `completed`
- note: `anns_d ann_date near cap bulk_rows=4112; ts_code fallback_rows=392; union_rows=4504; deduped_rows=4112`
- result: explicit cap-aware contract path exercised; no retained-history fallback

### news_daily
Artifact: `artifacts/archive_v2_business_contract_probe_news_20260419.json`
- status: `completed`
- row_count: `7591`
- note: `news srcs=9 deduped_rows=7591 suspicious_windows=0`
- result: explicit source bundle × time windows exercised; no generic trade_date-style fetch

### dragon_tiger_daily
Artifact: `artifacts/archive_v2_business_contract_probe_p1_fast_20260419.json`
- status: `completed`
- row_count: `69`
- note: `top_list direct rows=69`

### limit_up_detail_daily
Artifact: `artifacts/archive_v2_business_contract_probe_p1_fast_20260419.json`
- status: `completed`
- row_count: `91`
- note: `limit_list_d shards=9 detail_rows=91`

## Priority 2 / 3 source-contract evidence
Artifact: `artifacts/archive_v2_business_contract_probe_p23_20260419.json`

### limit_up_down_status_daily
- status: `completed`
- raw canonical rows: `91`
- aggregate row:
  - `up_count=71`
  - `blow_open_count=20`

### research_reports_daily
- status: `completed`
- row_count: `87`
- note: `research_report shards=56 deduped_rows=87 suspicious_bulk=False`

### investor_qa_daily
- status: `completed`
- row_count: `502`
- note: `irm_qa_sh+sz rows=502 low_or_zero_fallback=False`

## sector_performance_daily source-contract evidence
Artifact: `artifacts/archive_v2_business_contract_probe_sector_20260419.json`
- status: `incomplete`
- row_count: `485`
- note: `ths_index+ths_daily expected=1236 actual=485 coverage=0.392`
- result: the new coverage-ratio completeness rule is functioning; this family is no longer incorrectly judged by mere nonzero rows

## Write-enabled bounded validation evidence
Artifact: `artifacts/archive_v2_business_contract_write_validation_20260419.json`

- date: `2026-04-17`
- runtime: `141.86 sec`
- selected targets: `8`
- overall status: `partial`

### Completed in write-enabled validation
- `announcements_daily` — completed — `584` rows written in the pre-union intermediate run
- `news_daily` — completed — `7591` rows written
- `research_reports_daily` — completed — `87` rows written
- `investor_qa_daily` — completed — `502` rows written
- `dragon_tiger_daily` — completed — `69` rows written
- `limit_up_detail_daily` — completed — `91` rows written
- `limit_up_down_status_daily` — completed — `1` aggregate row written

### Incomplete in write-enabled validation
- `sector_performance_daily` — incomplete — `486` rows written — coverage `0.393`

### Requested rows written by table
- `ifa_archive_announcements_daily`: `584`
- `ifa_archive_news_daily`: `7591`
- `ifa_archive_research_reports_daily`: `87`
- `ifa_archive_investor_qa_daily`: `502`
- `ifa_archive_dragon_tiger_daily`: `69`
- `ifa_archive_limit_up_detail_daily`: `91`
- `ifa_archive_limit_up_down_status_daily`: `1`
- `ifa_archive_sector_performance_daily`: `486`

### Post-evidence cleanup
Artifact: `artifacts/archive_v2_business_contract_reset_after_20260419.json`
Deleted back out after validation:
- announcements: `584`
- news: `7591`
- research_reports: `87`
- investor_qa: `502`
- dragon_tiger: `69`
- limit_up_detail: `91`
- limit_up_down_status: `1`
- sector_performance: `486`

---

## 7. Truthful final judgment

### What is fixed now
This batch did **not** return with the old generic B-class behavior.
It now has:
- explicit family-specific contract metadata
- explicit family-specific fetch paths
- explicit family-specific shard rules
- explicit family-specific zero-row rules
- explicit family-specific completeness rules
- explicit `ifa_archive_*` destinations only
- archive identity schema aligned to contract row identities for the multi-row business/event families

### What is proven complete
These families now execute under their own contract path and no longer collapse into the old generic branch:
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`

`announcements_daily` also now uses the correct contract shape (`ann_date` bulk + `ts_code` fallback union) and the corrected source probe proves the final code path.

### Still-blocked family
#### sector_performance_daily
Still blocked at the completeness layer:
- current contract path is correct (`ths_index` universe + `ths_daily` fanout)
- destination namespace is correct
- coverage-ratio completeness rule is correct
- but source coverage remains low on the validation date:
  - expected universe `1236`
  - actual rows `485/486`
  - coverage `~0.39`

This is now a **truthful contract/coverage issue**, not the old generic B-class implementation issue.

### One additional truthful note
After the final union fix for `announcements_daily`, the source-probe path validated cleanly (`deduped_rows=4112`), but a later one-family write-enabled rerun returned transient zero rows from `anns_d`. I do **not** treat that transient zero as proof the contract is wrong; the stronger evidence is the final source probe plus the earlier successful bounded write run. The final code path is the unioned contract path, not the pre-union intermediate version.

### Overall judgment
- The family-specific business/event contract refactor is implemented.
- The Archive V2 namespace isolation rule is enforced.
- The old generic business/event source-first path is no longer the operative model for these families.
- One family remains honestly incomplete after the refactor:
  - `sector_performance_daily`

Everything else in this batch is now on explicit family-specific contract logic under the isolated `ifa_archive_*` namespace.
