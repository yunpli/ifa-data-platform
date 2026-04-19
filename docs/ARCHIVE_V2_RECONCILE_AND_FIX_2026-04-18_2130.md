# Archive V2 Reconcile-and-Fix Batch

Generated: 2026-04-18 21:30 PDT  
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Before-state mismatch summary

Before this batch, the remaining meaningful mismatch against the accepted final Archive V2 rules was:

### B-class daily/final families were still retained-history-first in the runner
Even after the family-model cleanup, these families were still practically wrong in execution because Archive V2 still defaulted to local retained-history upstream for them instead of direct source-side truth:
- `index_daily`
- `macro_daily`
- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `sector_performance_daily`

### Already-corrected areas that needed re-validation, not re-debate
These were already accepted and needed to be validated as still true after the batch:
- current C-class derived daily families removed from primary/default Archive V2 truth model
- proxy intraday families excluded from valid Archive V2 family model
- true source-side intraday families retained as supported later-enable / default-OFF
- ETF intraday included in the valid later-enable set
- archive_v2 already live as scheduled nightly production lane

This batch therefore did both:
- reconcile the remaining mismatch list
- fix what was still wrong immediately

---

## 2. Exact corrections completed in this batch

## 2.1 B-class source-first correction in runner
Implemented in:
- `src/ifa_data_platform/archive_v2/runner.py`

### Added explicit source-first family override set
Added:

```python
SOURCE_FIRST_DAILY_FAMILIES = {
    'index_daily',
    'macro_daily',
    'announcements_daily',
    'news_daily',
    'research_reports_daily',
    'investor_qa_daily',
    'dragon_tiger_daily',
    'limit_up_detail_daily',
    'limit_up_down_status_daily',
    'sector_performance_daily',
}
```

### Added direct source-side fetch dispatch
Added runner helper dispatch:
- `_fetch_source_first_daily_rows(...)`
- `_fetch_index_daily_direct(...)`
- `_fetch_macro_daily_direct(...)`
- `_fetch_announcements_daily_direct(...)`
- `_fetch_news_daily_direct(...)`
- `_fetch_research_reports_daily_direct(...)`
- `_fetch_investor_qa_daily_direct(...)`
- `_fetch_dragon_tiger_daily_direct(...)`
- `_fetch_limit_up_detail_daily_direct(...)`
- `_fetch_limit_up_down_status_daily_direct(...)`
- `_fetch_sector_performance_daily_direct(...)`

### Added source-first execution branch
`_execute_family(...)` now checks B-class family membership first and routes those families to direct source-side fetch instead of retained-history-first fetch.

### Corrected source endpoints used
- `index_daily` -> `index_daily`
- `macro_daily` -> `cn_cpi`, `cn_ppi`, `cn_pmi`, `cn_gdp`
- `announcements_daily` -> `anns_d`
- `news_daily` -> `news(start_date,end_date)`
- `research_reports_daily` -> `research_report`
- `investor_qa_daily` -> `irm_qa_sh`, `irm_qa_sz`
- `dragon_tiger_daily` -> `top_list`
- `limit_up_detail_daily` -> `stk_limit`
- `limit_up_down_status_daily` -> `stk_limit` with in-run aggregation to summary row
- `sector_performance_daily` -> `ths_index` + `ths_daily`

This is the main substantive implementation fix in this batch.

---

## 2.2 C-class default-model removal re-validated
Already-corrected default-model cleanup remains true after this batch:
- `DAILY_SIGNAL_FAMILIES = []`
- nightly production profile still has `include_signal_families=False`
- no current C-class derived daily families are part of `PRODUCTION_NIGHTLY_FAMILIES`

No rollback occurred.
No stale default activation reappeared.

---

## 2.3 Proxy exclusion re-validated
Still true after this batch:
- `proxy_1m`
- `proxy_15m`
- `proxy_60m`

remain excluded from:
- valid intraday tradable family map
- supported family registry
- primary Archive V2 truth model

No proxy family was reintroduced.

---

## 2.4 Later-enable intraday truth re-validated
Still true after this batch:

### Valid later-enable/default-OFF intraday groups
- equity `1m / 15m / 60m`
- ETF `1m / 15m / 60m`
- index `1m / 15m / 60m`
- futures `1m / 15m / 60m`
- commodity `1m / 15m / 60m`
- precious_metal `1m / 15m / 60m`

### Correct source endpoint metadata remains aligned
- equity -> `stk_mins`
- ETF -> `stk_mins`
- index -> `idx_mins`
- futures/commodity/precious_metal -> `ft_mins`

### ETF remains included correctly
ETF intraday remains represented in the model as valid later-enable support.

---

## 2.5 Stable doc/runbook correction
Updated stable doc:
- `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`

Added explicit stable truth that:
- daily/final B-class families now use source-first fetch semantics where direct source truth exists
- no current C-class derived daily families are in default nightly scope
- no proxy intraday families are valid raw archive families
- valid later-enable intraday families remain represented consistently

---

## 3. Validation commands used

## 3.1 Syntax validation
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m py_compile \
  src/ifa_data_platform/archive_v2/runner.py \
  scripts/archive_v2_bclass_validation.py
```

## 3.2 Model / family-map validation
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_bclass_validation.py
```

This emits artifact:
- `artifacts/archive_v2_bclass_validation_20260418.json`

It validates:
- source-first family set
- default nightly family set
- proxy exclusion
- intraday later-enable family map
- nightly profile signal-family exclusion
- direct fetch behavior for B-class families

## 3.3 Focused execution-path validation
```bash
python3 - <<'PY'
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner
runner=ArchiveV2Runner('profiles/archive_v2_milestone10_daily_index_only.json')
runner.profile.write_enabled=False
for fam in ['index_daily','announcements_daily','dragon_tiger_daily','sector_performance_daily']:
    rows_written, tables, status, notes, err = runner._execute_family(fam, '2026-04-15')
    print(fam, status, rows_written, tables, err)
PY
```

This validates that `_execute_family()` itself now takes the corrected source-first path for representative B-class families.

## 3.4 Stable doc truth check
```bash
rg -n "source-first fetch semantics|no current C-class highfreq-derived daily families|no proxy intraday families|equity `1m / 15m / 60m`|ETF `1m / 15m / 60m`" \
  docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md \
  src/ifa_data_platform/archive_v2/runner.py \
  src/ifa_data_platform/archive_v2/production.py -S
```

---

## 4. Validation evidence summary

## 4.1 Family model truth
Validated:
- `DAILY_SIGNAL_FAMILIES` remains empty
- default nightly production family set does not include current C-class derived daily families

## 4.2 Source-first correction truth
Validated via direct runner helper and execution path:
- B-class families now have direct source fetch implementations
- runner now routes those families through the source-first path before the old retained-history handlers

## 4.3 Default production scope truth
Validated:
- default nightly scope remains the cleaned primary truth model only
- no current C-class derived daily families are active by default

## 4.4 Later-enable intraday truth
Validated:
- valid intraday family map still includes only:
  - equity
  - ETF
  - index
  - futures
  - commodity
  - precious_metal
- all represented as later-enable/default-OFF

## 4.5 Proxy exclusion truth
Validated:
- proxy families remain excluded from supported family registry and active family map

## 4.6 Production/runbook alignment truth
Validated:
- stable runbook now reflects both:
  - source-first B-class daily/final correction
  - already-corrected family-model cleanup

---

## 5. Truly blocked items

No concrete blocker prevented the corrections in this batch.

Notes:
- this batch did **not** implement the larger full intraday source-first refactor yet
- but that was not a blocker to fixing the remaining B-class daily/final retained-history-first mismatch now

So the truthful status is:
- **no blocked correction item in this batch**

---

## 6. Truthful final judgment

This batch did not stop at a checklist.
It reconciled, fixed, validated, and finished the remaining practical mismatch that was still present.

### Corrected now
- B-class daily/final families are no longer only theoretical “should be source-first” cases; the Archive V2 runner now has source-first execution for them
- default model cleanup remains intact
- proxy exclusion remains intact
- later-enable intraday truth remains intact
- stable runbook now matches corrected code/model truth

### Result
Archive V2 is now materially closer to the accepted final rules across:
- family model truth
- upstream dependency truth
- production profile/default scope truth
- runtime/production path truth
- docs/runbook truth

This batch is complete.
