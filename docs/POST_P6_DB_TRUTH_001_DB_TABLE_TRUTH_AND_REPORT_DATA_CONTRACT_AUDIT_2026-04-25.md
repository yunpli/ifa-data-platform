# POST-P6-DB-TRUTH-001 — DB Table Truth and Report Data Contract Audit

- Date: 2026-04-25
- Repo: `/Users/neoclaw/repos/ifa-data-platform`
- Scope: read-only DB + code audit only
- DB env: repo `.env` + unified venv `/Users/neoclaw/repos/ifa-data-platform/.venv`
- Target chain reviewed: `early_main_producer` → assembly/rendering → `chart_pack` → `scripts/fsj_report_cli.py`

---

## 1. Executive Summary

### Verdict
Current customer-surface watchlist/name/chart defects are **not** caused by one single missing table. They are the result of **three separate contract gaps**:

1. **Name-lookup contract mismatch** in `early_main_producer`:
   - focus symbols are stored as suffixed codes like `000002.SZ`
   - `stock_basic_history.symbol` stores bare codes like `000002`
   - current SQL joins `sbh.symbol = fi.symbol`, so stock-basic fallback misses most A-share rows
   - only sources already storing suffixed symbols or explicit `focus_list_items.name` survive

2. **Renderer rationale fallback dominates when symbol-specific evidence is thin**:
   - `report_rendering.py` builds watchlist prose from a shared section reason plus light `evidence_score`
   - when per-symbol facts/signals/judgments are sparse, multiple symbols collapse to near-identical canned rationale

3. **Chart completeness is structurally limited by current market-data reality**:
   - `chart_pack.py` only reads `ifa2.equity_daily_bar_history`
   - `ifa_archive_equity_60m` is empty
   - `stock_60min_history` and highfreq working tables are extremely sparse and do not cover 2026-04-20 / 2026-04-22 / 2026-04-23
   - so chart layer can only be partial even if rendering is correct

### Recommended golden sample date
**`2026-04-23`**

Reason:
- `equity_daily_bar_history` has a clean single-day slice (`20 rows / 20 symbols`) on 2026-04-23, unlike 2026-04-20 which shows duplicate density (`40 rows / 20 symbols`)
- text/event tables are materially populated on 2026-04-23
- it is already the existing acceptance/golden probe date in the report pipeline
- 2026-04-24 is still an in-flight day in several tables; 2026-04-22 is richer for some text tables but 2026-04-23 is the better balance for stable replay + current acceptance continuity

---

## 2. Table Inventory and Key Row Counts

| Table | Rows | Time range / notes |
|---|---:|---|
| `ifa2.focus_lists` | 11 | config table |
| `ifa2.focus_list_items` | 442 | config table |
| `ifa2.focus_list_rules` | 32 | config table |
| `ifa2.stock_basic_history` | 456,936 | created_at `2026-04-10` → present snapshots |
| `ifa2.stock_basic_current` | 5,513 | current equity master |
| `ifa2.symbol_universe` | 85 | manually curated universe table |
| `ifa2.equity_daily_bar_history` | 562 | `2025-04-10` → `2026-04-24` |
| `ifa2.stock_60min_history` | 60 | `2026-04-14 14:00:00` → `2026-04-15 15:00:00` |
| `ifa2.ifa_archive_equity_60m` | 0 | empty |
| `ifa2.highfreq_stock_1m_working` | 6 | `2026-04-15 09:30:00` → `2026-04-15 09:35:00` |
| `ifa2.highfreq_open_auction_working` | 1 | only `2026-04-15` |
| `ifa2.highfreq_event_stream_working` | 22,954 | `2026-04-15 22:52:38` → `2026-04-24 15:33:56` |
| `ifa2.highfreq_leader_candidate_working` | 6 | only `2026-04-15 09:35:00` |
| `ifa2.highfreq_intraday_signal_state_working` | 1 | only `2026-04-15 09:35:00` |
| `ifa2.announcements_history` | 168,727 | created_at `2026-04-10` → `2026-04-24` |
| `ifa2.news_history` | 67,849 | created_at `2026-04-10` → `2026-04-24` |
| `ifa2.research_reports_history` | 2,875 | `2026-04-10` → `2026-04-24` |
| `ifa2.investor_qa_history` | 20,593 | `2026-04-10` → `2026-04-24` |
| `ifa2.dragon_tiger_list_history` | 2,660 | `2025-04-09` → `2026-04-24` |
| `ifa2.limit_up_detail_history` | 113,518 | `2026-04-15` → `2026-04-24` |
| `ifa2.limit_up_down_status_history` | 27 | `2026-04-12` → `2026-04-24` |
| `ifa2.sector_performance_history` | 3,657 | `2026-04-16` → `2026-04-24` |
| `ifa2.ifa_fsj_bundles` | 9 | current FSJ bundle store |

---

## 3. Focus / Key-Focus Truth

### 3.1 Real owner/list truth
Observed `focus_lists` groupings:

| owner_type | owner_id | list_type | asset_type | frequency_type | list_count |
|---|---|---|---|---|---:|
| `default` | `default` | `key_focus` | `stock` | `none` | 1 |
| `default` | `default` | `focus` | `stock` | `none` | 1 |
| `default` | `default` | `key_focus` | `tech` | `none` | 1 |
| `default` | `default` | `focus` | `tech` | `none` | 1 |
| `default` | `default` | `key_focus` | `macro` | `none` | 1 |
| `default` | `default` | `focus` | `macro` | `none` | 1 |
| `default` | `default` | `key_focus` | `asset` | `none` | 1 |
| `default` | `default` | `focus` | `asset` | `none` | 1 |
| `default` | `default` | `archive_targets` | `multi_asset` | `daily/minute/15min` | 3 |

### 3.2 Important schema truth
- `focus_lists` has `name` and `metadata`, **does not have `display_name`**
- `focus_list_items` has `name` and `metadata`, **does not have `display_name`**
- `focus_list_rules` carries `rule_key / rule_value`

So the audit answer to “does `name / display_name / metadata` already exist?” is:
- `name`: **yes** (`focus_lists`, `focus_list_items`)
- `metadata`: **yes** (`focus_lists`, `focus_list_items`)
- `display_name`: **no physical column found** in these three focus tables

### 3.3 Real stock focus/key-focus sample
Example SQL:

```sql
select fl.id as list_id,
       fl.list_type,
       fl.asset_type,
       fl.name as list_name,
       fi.symbol,
       fi.name as item_name,
       fi.priority
from ifa2.focus_lists fl
join ifa2.focus_list_items fi on fi.list_id = fl.id
where fl.owner_type='default'
  and fl.owner_id='default'
  and fl.asset_type='stock'
  and fl.list_type in ('key_focus','focus')
  and fi.is_active = true
order by fl.list_type, fi.priority nulls last, fi.symbol;
```

Example result sample:

| list_type | symbol | item_name | priority |
|---|---|---|---:|
| `key_focus` | `000001.SZ` | 平安银行 | 1 |
| `key_focus` | `000063.SZ` | 中兴通讯 | 1 |
| `key_focus` | `000333.SZ` | 美的集团 | 2 |
| `key_focus` | `000725.SZ` | 京东方A | 2 |
| `key_focus` | `000651.SZ` | 格力电器 | 3 |
| `focus` | `000002.SZ` | 万科A | 1 |
| `focus` | `000004.SZ` | 国华网安 | 2 |
| `focus` | `000006.SZ` | 深振业A | 3 |
| `focus` | `000007.SZ` | 全新好 | 4 |

### 3.4 Audit conclusion on focus truth
For A-share report generation, the **real truth source** is:
- primary config source: `ifa2.focus_lists` + `ifa2.focus_list_items`
- effective stock filter in code: `coalesce(fi.asset_category, 'stock') = 'stock'`
- effective owner/list filter in code: `owner_type='default' and owner_id='default' and list_type in ('key_focus','focus','tech_key_focus','tech_focus')`

This means the report chain is not reading customer-specific focus tables right now. It is reading the **default/default** pool only.

---

## 4. Stock Basic / Symbol Universe / Equity Metadata Truth

### 4.1 Candidate local symbol→name sources
Observed plausible local sources:
- `ifa2.stock_basic_history`
- `ifa2.stock_basic_current`
- `ifa2.symbol_universe`
- `ifa2.focus_list_items.name` (only for items already configured into focus)

### 4.2 Physical key-field truth
- `stock_basic_history.ts_code` = suffixed symbol like `000002.SZ`
- `stock_basic_history.symbol` = bare code like `000002`
- `stock_basic_current.ts_code` = suffixed symbol like `000002.SZ`
- `stock_basic_current.symbol` = bare code like `000002`
- `symbol_universe.symbol` = suffixed symbol like `000007.SZ`

### 4.3 Required mapping verification
Verified in `stock_basic_history.ts_code`:

| ts_code | symbol | real name |
|---|---|---|
| `000001.SZ` | `000001` | 平安银行 |
| `000002.SZ` | `000002` | 万科Ａ |
| `000004.SZ` | `000004` | *ST国华 |
| `000006.SZ` | `000006` | 深振业Ａ |
| `000007.SZ` | `000007` | 全新好 |

Notes:
- `symbol_universe` only contains a subset; among the required names, only `000007.SZ` was directly present there during probe.
- `stock_basic_history` is the broadest reliable local source for A-share name lookup.

### 4.4 Most reliable local source
**Recommended local truth source for symbol→company name: `ifa2.stock_basic_history.ts_code`**

Why:
- broadest coverage
- stores official suffixed code (`ts_code`) that matches focus/watchlist/report symbols
- already contains the verified names for all required test symbols

`stock_basic_current` is a usable fallback, but `stock_basic_history` is the stronger audit source because it is broader and historically versioned.

---

## 5. Market Data Truth

### 5.1 Key table truth

| Category | Actual table | Key fields | Reality |
|---|---|---|---|
| Daily bars | `ifa2.equity_daily_bar_history` | `ts_code`, `trade_date`, `open/high/low/close` | populated, but small and partially duplicate |
| 60m bars | `ifa2.stock_60min_history` | `ts_code`, `trade_time`, `open/high/low/close` | only 60 rows total, only 2026-04-14/15 |
| archive_v2 60m | `ifa2.ifa_archive_equity_60m` | `business_date`, `ts_code`, `bar_time`, `payload` | empty |
| stock 1m working | `ifa2.highfreq_stock_1m_working` | `ts_code`, `trade_time`, OHLCV | 6 rows total, only one symbol on 2026-04-15 |
| open auction | `ifa2.highfreq_open_auction_working` | `ts_code`, `trade_date`, OHLCV | 1 row total |
| event stream | `ifa2.highfreq_event_stream_working` | `symbol`, `event_time`, `event_type`, `title` | materially populated |
| leader candidate | `ifa2.highfreq_leader_candidate_working` | `symbol`, `trade_time`, `candidate_score` | only 6 rows total |
| signal state | `ifa2.highfreq_intraday_signal_state_working` | `scope_key`, `trade_time`, state fields | only 1 row total |

### 5.2 Date completeness comparison

#### Daily bars / highfreq / archive comparison for 2026-04-20 / 2026-04-22 / 2026-04-23

| Table | 2026-04-20 | 2026-04-22 | 2026-04-23 |
|---|---:|---:|---:|
| `equity_daily_bar_history` rows / symbols | `40 / 20` | `20 / 20` | `20 / 20` |
| `stock_60min_history` | `0` | `0` | `0` |
| `ifa_archive_equity_60m` | `0` | `0` | `0` |
| `highfreq_stock_1m_working` | `0` | `0` | `0` |
| `highfreq_open_auction_working` | `0` | `0` | `0` |
| `highfreq_event_stream_working` rows / symbols | `0` | `1256 / 256` | `3954 / 101` |
| `highfreq_leader_candidate_working` | `0` | `0` | `0` |
| `highfreq_intraday_signal_state_working` | `0` | `0` | `0` |

### 5.3 Market-data audit conclusion
- **Daily**: usable enough for basic line/bar charting, but limited in breadth and appears duplicated on 2026-04-20.
- **Minute / 60m / archive_v2**: effectively not available for the target acceptance dates.
- **Highfreq event stream**: present and useful for qualitative/event evidence.
- **Highfreq price/state tables**: mostly absent for target dates.

So current chart incompleteness is a **real data-availability problem**, not just a renderer bug.

---

## 6. Text / Event Data Truth and Joinability

### 6.1 Key tables

| Table | Rows | Date field | Symbol field | Join to focus symbols? |
|---|---:|---|---|---|
| `news_history` | 67,849 | `datetime` / `created_at` | none | not directly; requires NLP/tagging layer |
| `announcements_history` | 168,727 | `ann_date` / `created_at` | `ts_code` | yes |
| `research_reports_history` | 2,875 | `trade_date` | `ts_code` | yes |
| `investor_qa_history` | 20,593 | `trade_date` | `ts_code` | yes |
| `dragon_tiger_list_history` | 2,660 | `trade_date` | `ts_code` | yes |
| `limit_up_detail_history` | 113,518 | `trade_date` | `ts_code` | yes |
| `limit_up_down_status_history` | 27 | `trade_date` | none | market-level only |
| `sector_performance_history` | 3,657 | `trade_date` | `sector_code` | not directly to stock symbols |

### 6.2 Example date density

| Table | 2026-04-20 | 2026-04-22 | 2026-04-23 |
|---|---:|---:|---:|
| `announcements_history` | 1,228 | 20,163 | 1,935 |
| `research_reports_history` | 110 | 792 | 655 |
| `investor_qa_history` | 1,565 | 4,344 | 2,017 |
| `dragon_tiger_list_history` | 138 | 68 | 61 |
| `limit_up_detail_history` | 15,102 | 79 | 85 |
| `limit_up_down_status_history` | 2 | 1 | 1 |
| `sector_performance_history` | 788 | 394 | 394 |
| `news_history` | 1,056 | 2,570 | 2,564 |

### 6.3 Focus-symbol join sample
For required symbols:
- `announcements_history` joined for `000002.SZ`, `000004.SZ`, `000007.SZ`
- `investor_qa_history` joined for `000002.SZ`, `000004.SZ`
- `dragon_tiger_list_history` joined for `000004.SZ`
- `limit_up_detail_history` joined for all five test symbols
- `news_history` has no physical stock symbol key, so direct join is **not** available
- `sector_performance_history` is sector-level and needs an external stock→sector bridge to become symbol-joinable

### 6.4 Text/event audit conclusion
The report chain has enough stock-keyed structured text/event tables to support differentiated per-symbol evidence **if it explicitly joins them**. The current near-generic watchlist prose is therefore **not because all text/event data is missing**. It is mostly because the watchlist renderer currently uses lightweight symbol-context extraction instead of a dedicated per-symbol evidence assembly.

---

## 7. Current Report Generation Actual Table Usage

### 7.1 `early_main_producer`
Observed reads in `src/ifa_data_platform/fsj/early_main_producer.py`:
- `ifa2.focus_lists`
- `ifa2.focus_list_items`
- `ifa2.stock_basic_history` (fallback name lookup)
- `ifa2.symbol_universe` (fallback name lookup)
- `ifa2.highfreq_open_auction_working`
- `ifa2.highfreq_event_stream_working`
- `ifa2.highfreq_leader_candidate_working`
- `ifa2.highfreq_intraday_signal_state_working`
- recent lowfreq text catalysts via:
  - `ifa2.news_history`
  - `ifa2.announcements_history`
  - `ifa2.research_reports_history`
  - `ifa2.investor_qa_history`

Critical code seam:

```sql
left join lateral (
    select min(nullif(trim(sbh.name), '')) as name
    from ifa2.stock_basic_history sbh
    where sbh.symbol = fi.symbol
) stock_basic_history_name on true
```

This is wrong for suffixed A-share symbols because:
- `fi.symbol = '000002.SZ'`
- `sbh.symbol = '000002'`
- correct comparable key is `sbh.ts_code`

### 7.2 Report assembly / rendering
Observed in `src/ifa_data_platform/fsj/report_rendering.py`:
- rendering **does not re-query DB** for watchlist names
- it consumes `focus_scope` from bundle payload
- `focus_name_map` is extracted from:
  - `scope.name_map`
  - `scope.items[*].name/display_name/company_name/label`
- if no display name is available, renderer falls back to generic labels like:
  - `A股核心观察对象 000002.SZ`
  - `A股补充观察对象 000006.SZ`
  - or ordinalized generic names

### 7.3 Chart pack
Observed in `src/ifa_data_platform/fsj/chart_pack.py`:
- focus charts read only from `ifa2.equity_daily_bar_history`
- query key is `ts_code`
- no fallback to `stock_60min_history`, `highfreq_stock_1m_working`, or archive_v2 60m tables
- missing data returns an explicit `missing` SVG/chart asset

### 7.4 `scripts/fsj_report_cli.py`
Observed role:
- wrapper/entry CLI only
- delegates to existing publish scripts
- **does not own** the data-join logic or watchlist naming logic

### 7.5 Actual current contract summary
- DB truth → mostly fine for focus config and multiple event tables
- producer contract → broken in stock-basic fallback join
- renderer contract → depends on bundle payload quality; no DB repair path
- chart contract → limited by sparse daily bars and empty intraday/archive tables
- CLI contract → orchestration only

---

## 8. Root-Cause Analysis of Current Failures

### 8.1 Why only `000001.SZ` showed `平安银行`
Root cause:
- `000001.SZ` already has explicit `focus_list_items.name = 平安银行`
- renderer can therefore surface the name even if stock-basic fallback join is wrong
- this is not proof that stock-basic join works; it is proof that focus config itself carried the name for that row

### 8.2 Why `000002.SZ` / `000004.SZ` / `000006.SZ` / `000007.SZ` can fall back to placeholders
Primary cause:
- producer fallback SQL joins `stock_basic_history.symbol` to suffixed focus symbol
- mismatch causes fallback name lookup miss
- when payload `focus_scope.items[*].name` is absent/stale/not carried through for some artifact, renderer has no recovery path and emits generic watchlist labels

Contributing cause:
- renderer intentionally avoids direct DB access, so once bundle payload loses the name, customer surface cannot self-heal

### 8.3 Why rationale is almost identical
Root cause:
- watchlist item prose is generated from a shared section reason plus low-cardinality `evidence_score`
- `_fallback_key_focus_rationale()` / `_fallback_focus_watch_rationale()` contain only a few canned branches
- when per-symbol fact/signal/judgment hits are sparse, multiple symbols take the same fallback branch

So this is mainly a **missing per-symbol evidence assembly problem**, not a missing text/event-table problem.

### 8.4 Why chart is still partial
Root cause:
- chart pack only queries `equity_daily_bar_history`
- `ifa_archive_equity_60m` is empty
- `stock_60min_history` does not cover target dates
- highfreq price working tables are essentially empty outside `2026-04-15`

So chart partiality is primarily **real data sparsity / source selection limitation**, not just HTML/render defects.

### 8.5 Missing data vs missing join vs wrong owner/list_type lookup?
Audit answer:
- **Wrong owner/list_type lookup**: not the main issue. Current code consistently reads `default/default` focus lists.
- **Missing join**: yes, this is the primary watchlist naming defect (`sbh.symbol` vs suffixed `fi.symbol`).
- **Missing data**: yes, but mainly for chart/intraday completeness, not for stock naming.
- **Missing join to symbol-keyed event evidence**: yes, this explains generic rationale despite event tables being populated.

---

## 9. Example SQL and Example Results

### 9.1 Focus truth
```sql
select owner_type, owner_id, list_type, asset_type, frequency_type, count(*) as list_count
from ifa2.focus_lists
group by 1,2,3,4,5
order by 1,2,3,4,5;
```

Example result: only `default/default` owners exist; stock `key_focus` and `focus` each have one active list.

### 9.2 Stock name truth
```sql
select ts_code, symbol, name, industry, market, list_date
from ifa2.stock_basic_history
where ts_code in ('000001.SZ','000002.SZ','000004.SZ','000006.SZ','000007.SZ')
order by ts_code;
```

Example result: names resolve to `平安银行 / 万科Ａ / *ST国华 / 深振业Ａ / 全新好`.

### 9.3 Daily-bar completeness
```sql
select trade_date::text as d, count(*) as rows, count(distinct ts_code) as symbols
from ifa2.equity_daily_bar_history
where trade_date in ('2026-04-20','2026-04-22','2026-04-23')
group by 1
order by 1;
```

Example result:
- `2026-04-20`: `40 rows / 20 symbols`
- `2026-04-22`: `20 rows / 20 symbols`
- `2026-04-23`: `20 rows / 20 symbols`

### 9.4 Event-stream completeness
```sql
select event_time::date::text as d, count(*) as rows, count(distinct symbol) as symbols
from ifa2.highfreq_event_stream_working
where event_time::date in ('2026-04-20','2026-04-22','2026-04-23')
group by 1
order by 1;
```

Example result:
- `2026-04-22`: `1256 rows / 256 symbols`
- `2026-04-23`: `3954 rows / 101 symbols`

---

## 10. Current Report-Generation Missing Joins

### Missing join / wrong key #1 — stock basic fallback
Current:
```sql
where sbh.symbol = fi.symbol
```
Should conceptually match by suffixed symbol key:
```sql
where sbh.ts_code = fi.symbol
```

### Missing join #2 — current table fallback not used in producer path
`stock_basic_current` is not the effective truth source in this producer path, and there is no robust fallback chain like:
1. `focus_list_items.name`
2. `stock_basic_history.ts_code`
3. `stock_basic_current.ts_code`
4. `symbol_universe.symbol`

### Missing join #3 — symbol-level rationale evidence pack
Current watchlist prose does not materialize a dedicated per-symbol evidence join across:
- `announcements_history`
- `research_reports_history`
- `investor_qa_history`
- `dragon_tiger_list_history`
- `limit_up_detail_history`

It mostly relies on sparse object-key text extraction after bundle assembly.

### Missing bridge #4 — sector-level enrichment
`sector_performance_history` cannot directly enrich a focus symbol without a stock→sector bridge.

---

## 11. Minimal Fix Recommendations

Strictly minimal, aligned to this audit only:

1. **Fix the producer name-lookup key contract**
   - change stock-basic fallback from `stock_basic_history.symbol = fi.symbol` to `stock_basic_history.ts_code = fi.symbol`
   - keep `symbol_universe.symbol = fi.symbol` as tertiary fallback
   - optionally add `stock_basic_current.ts_code = fi.symbol` into the fallback chain

2. **Formalize a deterministic symbol-name fallback chain in producer payload**
   - output one canonical `focus_scope.items[*].name`
   - never leave naming repair to renderer

3. **Add a dedicated per-symbol evidence aggregation seam for watchlist rationale**
   - join stock-keyed event tables directly by `ts_code`
   - emit per-symbol rationale inputs into bundle payload
   - keep renderer presentation-only

4. **Do not treat chart partiality as a presentation bug**
   - current chart limits are data-contract limits
   - if richer charts are required, data source coverage must be expanded first

5. **Use 2026-04-23 as the regression/golden sample date**
   - stable enough for replay
   - already integrated into acceptance path
   - better than 2026-04-20 duplicate daily slice

---

## 12. Final Audit Conclusion

### Truth source summary
- Focus truth: `ifa2.focus_lists` + `ifa2.focus_list_items`
- Stock-name truth: `ifa2.stock_basic_history.ts_code`
- Daily-chart truth: `ifa2.equity_daily_bar_history`
- Intraday/archive_v2 truth for target dates: effectively absent for charts
- Symbol-keyed event evidence truth: announcements / research / investor_qa / dragon_tiger / limit_up tables are usable

### Final RCA summary
- **Only 000001.SZ showed 平安银行** because explicit focus item naming survived; not because stock-basic fallback was healthy.
- **Other symbols fell to placeholders** because the producer stock-basic fallback compares the wrong key shape.
- **Rationales converged** because renderer is operating on weak per-symbol evidence and shared fallback prose.
- **Charts are partial** because the only chart source with target-date coverage is sparse daily-bar history, while 60m/archive/highfreq price tables are missing for those dates.

This is therefore a **producer contract + evidence assembly problem for naming/rationale**, and a **real upstream data sparsity problem for charts**.
