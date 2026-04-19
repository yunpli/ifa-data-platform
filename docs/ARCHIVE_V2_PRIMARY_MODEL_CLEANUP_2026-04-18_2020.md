# Archive V2 Primary Model Cleanup — Corrected Family Model

Generated: 2026-04-18 20:20 PDT  
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Exact correction scope implemented

This batch executed the corrected Archive V2 family-model cleanup directly in code and stable docs.

### Applied rules
1. **All current C-class highfreq-derived daily families were removed from the primary/default Archive V2 truth model**
2. **All proxy intraday families were removed from the valid Archive V2 family model**
3. **Only true source-side intraday families remain represented as supported later-enable / default-OFF families**
4. **ETF intraday is explicitly included in that valid later-enable family set**

This batch did **not** perform the larger source-first refactor yet.
It corrected the family model, metadata semantics, default profile semantics, and stable runbook truth.

---

## 2. Exact correction result

## 2.1 C-class family removal result
The following current highfreq-derived daily families are **no longer in the default Archive V2 primary truth model**:

- `highfreq_event_stream_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

### What changed in code
- `DAILY_SIGNAL_FAMILIES` is now:

```python
DAILY_SIGNAL_FAMILIES: list[str] = []
```

This means they are no longer selected by default archive family-set logic.

### Metadata semantics added
These C-class families still exist in metadata, but now carry explicit non-default semantics such as:
- `default_enabled: False`
- `support_status: 'derived_not_archived_by_default'`
- `raw_source_family: ...`

This makes the current state unambiguous:
- not primary/default archive truth
- only temporary derived retention semantics until raw-first refactor is done

---

## 2.2 Proxy family exclusion result
The following proxy intraday families were removed from the valid Archive V2 family model:

- `proxy_1m`
- `proxy_15m`
- `proxy_60m`

### What changed in code
They were removed from:
- `INTRADAY_TRADABLE_FAMILIES`
- `ALL_FAMILY_META`
- identity policy map
- supported family registry (indirectly via metadata removal)

### Practical meaning
These families are no longer treated as valid supported archive families at all.
They are explicitly excluded until a true source-side intraday path is proven.

---

## 2.3 Later-enable true intraday family set
The valid true source-side intraday family set now represented in the model is:

### Equity
- `equity_1m`
- `equity_15m`
- `equity_60m`
- source endpoint: `stk_mins`
- current status: `supported_later`, `default_enabled=False`

### ETF
- `etf_1m`
- `etf_15m`
- `etf_60m`
- source endpoint: `stk_mins`
- current status: `supported_later`, `default_enabled=False`
- implementation status: `intraday_source_pending`

### Index
- `index_1m`
- `index_15m`
- `index_60m`
- source endpoint: `idx_mins`
- current status: `supported_later`, `default_enabled=False`

### Futures
- `futures_1m`
- `futures_15m`
- `futures_60m`
- source endpoint: `ft_mins`
- current status: `supported_later`, `default_enabled=False`

### Commodity
- `commodity_1m`
- `commodity_15m`
- `commodity_60m`
- source endpoint: `ft_mins`
- current status: `supported_later`, `default_enabled=False`

### Precious metal
- `precious_metal_1m`
- `precious_metal_15m`
- `precious_metal_60m`
- source endpoint: `ft_mins`
- current status: `supported_later`, `default_enabled=False`

---

## 3. Updated default Archive V2 truth family set

After cleanup, the default primary truth model is represented by the nightly/backfill production family sets:

### Default nightly family set
- `equity_daily`
- `index_daily`
- `etf_daily`
- `non_equity_daily`
- `macro_daily`
- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `sector_performance_daily`

### Explicitly not in default nightly truth set anymore
- all current C-class highfreq-derived daily families
- all proxy intraday families
- all intraday families (they remain default-OFF)

---

## 4. Validation commands used

### 4.1 Syntax validation
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m py_compile \
  src/ifa_data_platform/archive_v2/runner.py \
  src/ifa_data_platform/archive_v2/production.py
```

### 4.2 Direct model inspection
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python - <<'PY'
from ifa_data_platform.archive_v2.runner import DAILY_SIGNAL_FAMILIES, INTRADAY_TRADABLE_FAMILIES, ALL_FAMILY_META, SUPPORTED_FAMILIES
from ifa_data_platform.archive_v2.production import PRODUCTION_NIGHTLY_FAMILIES, PRODUCTION_MANUAL_BACKFILL_FAMILIES, build_nightly_profile
print('DAILY_SIGNAL_FAMILIES', DAILY_SIGNAL_FAMILIES)
print('PRODUCTION_NIGHTLY_FAMILIES', PRODUCTION_NIGHTLY_FAMILIES)
print('PRODUCTION_MANUAL_BACKFILL_FAMILIES', PRODUCTION_MANUAL_BACKFILL_FAMILIES)
print('proxy_in_supported', [x for x in ['proxy_1m','proxy_15m','proxy_60m'] if x in SUPPORTED_FAMILIES])
print('intraday_map', INTRADAY_TRADABLE_FAMILIES)
for fam in ['etf_1m','etf_15m','etf_60m','equity_1m','index_1m','futures_1m','commodity_1m','precious_metal_1m','highfreq_event_stream_daily','highfreq_sector_breadth_daily']:
    print(fam, ALL_FAMILY_META.get(fam))
profile = build_nightly_profile('2026-04-15')
print('nightly_include_signal', profile.include_signal_families)
print('nightly_family_groups', profile.family_groups)
PY
```

### 4.3 Stable doc truth check
```bash
rg -n "selected highfreq finalized daily families|proxy_1m|proxy_15m|proxy_60m|highfreq_event_stream_daily|highfreq_sector_breadth_daily|etf_1m|etf_15m|etf_60m" \
  docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md \
  src/ifa_data_platform/archive_v2/{runner.py,production.py} -S
```

---

## 5. Model evidence

## 5.1 Evidence: C-class removed from default family model
Observed direct inspection output:

```text
DAILY_SIGNAL_FAMILIES []
PRODUCTION_NIGHTLY_FAMILIES ['equity_daily', 'index_daily', 'etf_daily', 'non_equity_daily', 'macro_daily', 'announcements_daily', 'news_daily', 'research_reports_daily', 'investor_qa_daily', 'dragon_tiger_daily', 'limit_up_detail_daily', 'limit_up_down_status_daily', 'sector_performance_daily']
nightly_include_signal False
```

This proves:
- current C-class derived daily families are no longer selected by the default family model
- production nightly profile no longer enables signal families
- default Archive V2 truth model is now cleaner and aligned with the corrected rule

## 5.2 Evidence: proxy families excluded
Observed direct inspection output:

```text
proxy_in_supported []
```

This proves:
- `proxy_1m`
- `proxy_15m`
- `proxy_60m`

are no longer in the supported family registry.

## 5.3 Evidence: true source-side intraday families retained as later-enable/default-OFF
Observed direct inspection output:

```text
intraday_map {
  '60m': ['equity_60m', 'etf_60m', 'index_60m', 'futures_60m', 'commodity_60m', 'precious_metal_60m'],
  '15m': ['equity_15m', 'etf_15m', 'index_15m', 'futures_15m', 'commodity_15m', 'precious_metal_15m'],
  '1m': ['equity_1m', 'etf_1m', 'index_1m', 'futures_1m', 'commodity_1m', 'precious_metal_1m']
}
```

Example metadata evidence:

```text
etf_1m  -> support_status='supported_later', default_enabled=False, source_endpoint='stk_mins'
equity_1m -> support_status='supported_later', default_enabled=False, source_endpoint='stk_mins'
index_1m -> support_status='supported_later', default_enabled=False, source_endpoint='idx_mins'
futures_1m -> support_status='supported_later', default_enabled=False, source_endpoint='ft_mins'
```

This proves:
- true source-side intraday families remain represented in the Archive V2 model
- they are supported later-enable/default-OFF
- ETF intraday is explicitly included in that valid set

---

## 6. Stable docs / runbook truth update

Updated stable runbook:
- `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`

Corrected stable runbook now says:
- no current C-class highfreq-derived daily families in default nightly scope
- no proxy intraday families in valid raw family set
- valid later-enable true intraday support remains for:
  - equity
  - ETF
  - index
  - futures
  - commodity
  - precious_metal

This removes the older interpretation that default nightly scope still included selected highfreq finalized daily families.

---

## 7. Truthful judgment

### What is now corrected cleanly
- C-class derived daily families are no longer treated as primary/default Archive V2 truth families
- proxy intraday families are no longer treated as valid archive families
- true source-side intraday families remain represented correctly as supported later-enable/default-OFF families
- ETF intraday is explicitly included in that true-family set
- code and stable docs now tell the same story

### What this batch intentionally did not do
- it did not implement the full source-first intraday fetch refactor yet
- it did not remove historical C-class metadata entirely; instead it marked them clearly as non-default/temporary derived retention semantics

### Final result
The default Archive V2 truth model is now materially cleaner and aligned with the corrected rule:
- **primary default truth = daily/final source-aligned archive families**
- **no current C-class derived daily families in default model**
- **no proxy pseudo-intraday families in valid model**
- **true intraday families remain supported later-enable/default-OFF**
