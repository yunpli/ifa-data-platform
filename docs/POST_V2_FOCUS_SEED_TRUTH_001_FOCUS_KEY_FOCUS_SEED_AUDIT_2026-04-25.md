# POST-V2-FOCUS-SEED-TRUTH-001 — Focus / Key-Focus Seed and Customer Display Truth Audit

- Date: 2026-04-25
- Scope: audit only; no schema change, no collector additions, no renderer/presentation repair in this task
- Repos:
  - data-platform: `/Users/neoclaw/repos/ifa-data-platform`
  - business-layer: `/Users/neoclaw/repos/ifa-business-layer`
- DB schema inspected: `ifa2`
- Required context read:
  - `docs/IFA_Execution_Context_and_Behavior.md`
  - `docs/IFA_Execution_Progress_Monitor.md`
  - `IFA_Implementation_Enhancement_Task_List_V2.md`
  - `docs/V2_FEATURE_COMPLETION_AUDIT_2026-04-25.md`
  - `docs/POST_P6_DB_TRUTH_001_DB_TABLE_TRUTH_AND_REPORT_DATA_CONTRACT_AUDIT_2026-04-25.md`

---

## 1. Executive conclusion

Bottom line:

1. Live DB currently contains **only `owner_type=default`, `owner_id=default`** focus families. There is **no live `system/default` pair** in `ifa2.focus_lists`.
2. The current `000001.SZ` onward sequence is created by **business-layer Python defaults**, not a SQL seed file. Source is `ifa_business_layer/defaults.py` via `scripts/focus_cli.py seed-default`.
3. The same business-layer default seed also creates the current stock / tech / macro / asset focus and key_focus families, plus archive target families.
4. The A-share main producer currently reads **`default/default` stock-ish focus rows directly**. The renderer then presents that payload on the customer surface. So the current customer report is still consuming **default seed scope** as its visible watchlist base.
5. The default seed is best interpreted as **business-layer canonical default observation / coverage / collection-support scope**, not as a formal client-owned display list. Therefore the current customer report still has a **contract misuse problem** even after recent honesty metadata improvements.
6. Multi-domain seeds do exist in DB today: stock, tech, macro, asset focus/key_focus; archive targets daily/15min/minute also exist.
7. Support-report reality is uneven:
   - AI/tech support uses tech focus lists.
   - Macro and asset/commodities support do **not** currently consume their respective focus/key_focus families as first-class report inputs.

---

## 2. Evidence base

### 2.1 Repo files inspected

Business-layer seed / defaults / CLI:
- `/Users/neoclaw/repos/ifa-business-layer/ifa_business_layer/defaults.py`
- `/Users/neoclaw/repos/ifa-business-layer/scripts/focus_cli.py`
- `/Users/neoclaw/repos/ifa-business-layer/README.md`

Data-platform current consumers:
- `/Users/neoclaw/repos/ifa-data-platform/src/ifa_data_platform/fsj/early_main_producer.py`
- `/Users/neoclaw/repos/ifa-data-platform/src/ifa_data_platform/fsj/report_rendering.py`
- `/Users/neoclaw/repos/ifa-data-platform/src/ifa_data_platform/fsj/chart_pack.py`
- `/Users/neoclaw/repos/ifa-data-platform/src/ifa_data_platform/fsj/ai_tech_support_producer.py`
- `/Users/neoclaw/repos/ifa-data-platform/src/ifa_data_platform/fsj/macro_support_producer.py`
- `/Users/neoclaw/repos/ifa-data-platform/src/ifa_data_platform/fsj/commodities_support_producer.py`

### 2.2 DB tables inspected

Required tables inspected directly:
- `ifa2.focus_lists`
- `ifa2.focus_list_items`
- `ifa2.focus_list_rules`
- `ifa2.symbol_universe`
- `ifa2.stock_basic_history`

Related archive/target truth inspected via DB contents + seed source:
- archive target families inside `ifa2.focus_lists` / `ifa2.focus_list_items` / `ifa2.focus_list_rules`

---

## 3. A. Focus list inventory

### 3.1 Owner-pair truth

SQL result summary:

```sql
select owner_type, owner_id, count(*)
from ifa2.focus_lists
group by 1,2
order by 1,2;
```

Result:
- `default | default | 11`

So live DB currently has exactly one owner pair: **`default/default`**.

### 3.2 focus_lists master table

```sql
select fl.id, fl.owner_type, fl.owner_id, fl.list_type, fl.name, fl.asset_type,
       fl.frequency_type, fl.is_active, fl.created_at, fl.updated_at,
       count(fi.*) filter (where fi.is_active) as active_item_count
from ifa2.focus_lists fl
left join ifa2.focus_list_items fi on fi.list_id = fl.id
group by fl.id, fl.owner_type, fl.owner_id, fl.list_type, fl.name, fl.asset_type,
         fl.frequency_type, fl.is_active, fl.created_at, fl.updated_at
order by fl.owner_type, fl.owner_id, fl.list_type, fl.asset_type, fl.frequency_type, fl.name;
```

| name | owner_type | owner_id | list_type | asset_type | frequency_type | active | item count | created_at | updated_at |
|---|---|---|---|---|---|---:|---:|---|---|
| `default_archive_targets_15min` | default | default | archive_targets | multi_asset | 15min | true | 36 | 2026-04-22 22:29:26.672049-07 | 2026-04-22 22:29:26.672049-07 |
| `default_archive_targets_daily` | default | default | archive_targets | multi_asset | daily | true | 170 | 2026-04-22 22:29:26.675758-07 | 2026-04-22 22:29:26.675758-07 |
| `default_archive_targets_minute` | default | default | archive_targets | multi_asset | minute | true | 19 | 2026-04-22 22:29:26.669602-07 | 2026-04-22 22:29:26.669602-07 |
| `default_asset_focus` | default | default | focus | asset | none | true | 20 | 2026-04-22 22:29:26.666898-07 | 2026-04-22 22:29:26.666898-07 |
| `default_macro_focus` | default | default | focus | macro | none | true | 10 | 2026-04-22 22:29:26.655385-07 | 2026-04-22 22:29:26.655385-07 |
| `default_stock_focus` | default | default | focus | stock | none | true | 80 | 2026-04-22 22:29:26.641132-07 | 2026-04-22 22:29:26.641132-07 |
| `default_tech_focus` | default | default | focus | tech | none | true | 50 | 2026-04-22 22:29:26.660245-07 | 2026-04-22 22:29:26.660245-07 |
| `default_asset_key_focus` | default | default | key_focus | asset | none | true | 12 | 2026-04-22 22:29:26.665107-07 | 2026-04-22 22:29:26.665107-07 |
| `default_macro_key_focus` | default | default | key_focus | macro | none | true | 5 | 2026-04-22 22:29:26.653938-07 | 2026-04-22 22:29:26.653938-07 |
| `default_stock_key_focus` | default | default | key_focus | stock | none | true | 20 | 2026-04-22 22:29:26.630278-07 | 2026-04-22 22:29:26.630278-07 |
| `default_tech_key_focus` | default | default | key_focus | tech | none | true | 20 | 2026-04-22 22:29:26.656974-07 | 2026-04-22 22:29:26.656974-07 |

### 3.3 Item counts per list family

- Stock: `key_focus=20`, `focus=80`
- Macro: `key_focus=5`, `focus=10`
- Tech: `key_focus=20`, `focus=50`
- Asset: `key_focus=12`, `focus=20`
- Archive targets: `minute=19`, `15min=36`, `daily=170`

### 3.4 Sample rows per category

Sample DB rows from `focus_list_items`:

#### Stock key_focus
- `000001.SZ | 平安银行 | priority=1`
- `000333.SZ | 美的集团 | priority=2`
- `000651.SZ | 格力电器 | priority=3`
- `000977.SZ | 浪潮信息 | priority=4`
- `002230.SZ | 科大讯飞 | priority=5`

#### Stock focus (proof of 000001-sequence extension into broader canonical pool)
- `000002.SZ | 万科Ａ`
- `000004.SZ | *ST国华`
- `000006.SZ | 深振业Ａ`
- `000007.SZ | 全新好`
- `000008.SZ | 神州高铁`

#### Tech key_focus / focus
- `000063.SZ | 中兴通讯`
- `000725.SZ | 京东方A`
- `000938.SZ | 紫光股份`
- `002049.SZ | 紫光国微`
- `688981.SH | 中芯国际`

#### Macro
- `CN_CPI | 中国CPI`
- `CN_PPI | 中国PPI`
- `CN_PMI | 中国制造业PMI`
- `US_CPI | 美国CPI`
- `US_NFP | 美国非农`

#### Asset
- `AU0 | 沪金主连`
- `AG0 | 沪银主连`
- `CU0 | 沪铜主连`
- `SC0 | 原油主连`
- `RB0 | 螺纹钢主连`

#### Archive targets
Minute / 15min / daily lists all exist and contain mixed stock + tech + macro + asset symbols. Example daily rows:
- `000001.SZ | 平安银行`
- `000333.SZ | 美的集团`
- `688981.SH | 中芯国际`
- `CN_CPI | 中国CPI`
- `AU0 | 沪金主连`

---

## 4. Seed source files

### 4.1 Formal seed entrypoint

Business-layer README documents the canonical seed path:
- `scripts/focus_cli.py seed-default`
- canonical owner scope is explicitly `owner_type=default`, `owner_id=default`

Evidence:
- `/Users/neoclaw/repos/ifa-business-layer/README.md`
- `/Users/neoclaw/repos/ifa-business-layer/scripts/focus_cli.py`

### 4.2 Actual seed implementation

Actual seeded lists are defined in Python, not SQL:
- `/Users/neoclaw/repos/ifa-business-layer/ifa_business_layer/defaults.py`

Key evidence:
- `stock_key_focus_items = _items_with_priority(stocks[:20])`
- `stock_focus_items = _items_with_priority(stocks[:80])`
- `macro_key_focus_items = _items_with_priority(macros[:5])`
- `macro_focus_items = _items_with_priority(macros[:10])`
- `tech_key_focus_items = _items_with_priority(tech_stocks[:20])`
- `tech_focus_items = _items_with_priority(tech_stocks[:50])`
- `asset_key_focus_items = _items_with_priority(assets[:12])`
- `asset_focus_items = _items_with_priority(assets)`
- `minute_items = _items_with_priority(stocks[:8] + tech_stocks[:6] + assets[:6])`
- `m15_items = _items_with_priority(stocks[:16] + tech_stocks[:12] + assets[:12])`
- `daily_items = _items_with_priority(stocks[:120] + tech_stocks[:30] + macros[:10] + assets)`

Then `ListSpec(...)` emits:
- `default_stock_key_focus`
- `default_stock_focus`
- `default_macro_key_focus`
- `default_macro_focus`
- `default_tech_key_focus`
- `default_tech_focus`
- `default_asset_key_focus`
- `default_asset_focus`
- `default_archive_targets_minute`
- `default_archive_targets_15min`
- `default_archive_targets_daily`

### 4.3 Seed rule evidence

Rule rows from `ifa2.focus_list_rules` confirm seed intent:
- `default_stock_focus.seed_origin = a_share_only_tushare_supported`
- `default_stock_key_focus.seed_origin = a_share_only_tushare_supported`
- `default_asset_focus.identity_strategy = rolling_canonical_contract`
- `default_asset_key_focus.identity_strategy = rolling_canonical_contract`
- archive targets carry `granularity = minute|15min|daily`

---

## 5. B. `default/default` vs `system/default`

### 5.1 Do both exist?

**No.** Live DB shows only `default/default`.

Evidence:
- `select owner_type, owner_id, count(*) from ifa2.focus_lists group by 1,2;`
- result: only `default | default | 11`

### 5.2 Are they duplicates?

In live DB: **not applicable**, because `system/default` does not exist as rows.

### 5.3 Which does report/producer read?

Current A-share main producer reads **`default/default`**.

Evidence from `/Users/neoclaw/repos/ifa-data-platform/src/ifa_data_platform/fsj/early_main_producer.py`:

```sql
where fl.owner_type='default' and fl.owner_id='default'
  and fl.list_type in ('key_focus','focus','tech_key_focus','tech_focus')
  and coalesce(fi.asset_category, 'stock') = 'stock'
```

### 5.4 Is the other ignored?

Yes in practice: `system/default` is only present as **contract metadata / comparison concept**, not as live DB rows currently consumed.

Evidence:
- `early_main_producer.py` payload metadata explicitly records:
  - `default_scope: default/default`
  - `system_scope: system/default`
- but the SQL query itself reads only `default/default`

### 5.5 Duplication or historical residue?

Judgment: **there is no active live-row duplication between `default/default` and `system/default` right now**. What exists is **conceptual residue / naming residue** in contract metadata, not duplicate DB content.

---

## 6. C. Current `000001.SZ` onward sequence source

### 6.1 Which seed/default file creates it?

Source file:
- `/Users/neoclaw/repos/ifa-business-layer/ifa_business_layer/defaults.py`

Specifically:
- `_preferred_stock_symbols()` begins with canonical A-share names such as `000001.SZ`, `000333.SZ`, `000651.SZ`, etc.
- `build_stock_pool()` appends DB-fetched stock candidates after the preferred list.
- `stock_focus_items = _items_with_priority(stocks[:80])`
- archive target daily also extends deeper via `stocks[:120]`

### 6.2 Is it SQL seed or Python defaults?

**Python defaults.** No evidence found that the current canonical sequence is created by a dedicated SQL seed file.

### 6.3 Is it formal customer focus pool?

**No.** Evidence points to a canonical default business-layer seed, not a client-owned profile/list.

### 6.4 Is it collection coverage seed?

**Partly yes.** It is used as baseline coverage / observation scope and also feeds archive target seeds. Evidence:
- early-main payload contract says `collection_scope_class = business_layer_canonical_default_seed`
- payload contract says `000001_sequence_interpretation.is_collection_scope = True`

### 6.5 Is it dev/test seed?

Best judgment: **not primarily dev/test seed**.

Evidence:
- README calls it canonical default owner scope.
- payload contract marks `is_development_test_seed = False`.
- `seed-default` is formal CLI behavior, not an ad-hoc fixture script.

### 6.6 Is it archive target seed?

**Yes, in part.** The same stock pool also feeds:
- `default_archive_targets_minute`
- `default_archive_targets_15min`
- `default_archive_targets_daily`

So the `000001` onward sequence is reused into archive target families as well.

### 6.7 Why is it appearing in customer report?

Because the main producer currently reads `default/default` focus rows directly, and the renderer/customer surface presents that scope as the visible watchlist base.

Evidence:
- producer SQL reads `default/default`
- producer payload advertises source `ifa2.focus_lists+ifa2.focus_list_items`
- renderer consumes `payload.focus_scope`
- customer surface does not switch to a separate client-owned list source

---

## 7. D. Multi-domain seeds existence

### 7.1 A-share stock focus/key_focus

Exists: **yes**
- `default_stock_key_focus = 20`
- `default_stock_focus = 80`

### 7.2 Asset focus/key_focus

Exists: **yes**
- `default_asset_key_focus = 12`
- `default_asset_focus = 20`

### 7.3 Tech / Tech Stock focus/key_focus

Exists: **yes**
- `default_tech_key_focus = 20`
- `default_tech_focus = 50`

### 7.4 Macro focus/key_focus

Exists: **yes**
- `default_macro_key_focus = 5`
- `default_macro_focus = 10`

### 7.5 Archive targets daily / 15min / minute

Exists: **yes**
- `default_archive_targets_daily = 170`
- `default_archive_targets_15min = 36`
- `default_archive_targets_minute = 19`

### 7.6 If absent, never implemented vs overwritten vs confused?

Not applicable for these families: all required families are present in live DB and defined in business-layer defaults.

Judgment: current problem is **not absence**. It is **scope confusion / misuse** between default seed, archive coverage, and customer display semantics.

---

## 8. Current report usage contract

### 8.1 Main A-share producer

Current data-platform main producer contract:
- reads `default/default`
- reads `list_type in ('key_focus','focus','tech_key_focus','tech_focus')`
- filters to stock-ish rows with `coalesce(fi.asset_category, 'stock') = 'stock'`

So current customer-visible main focus scope is really:
- default seed stock focus
- plus any tech rows marked stock/tech that pass the stock-ish filter

### 8.2 Renderer

`report_rendering.py` consumes `payload.focus_scope`; it does not independently resolve a customer-owned display list contract.

### 8.3 Chart pack

`chart_pack.py` first uses `payload.focus_scope`, then falls back to DB query:

```sql
select distinct fi.symbol
from ifa2.focus_lists fl
join ifa2.focus_list_items fi on fi.list_id = fl.id
where fl.is_active = true
  and fi.is_active = true
  and fl.list_type in ('key_focus','focus','tech_key_focus','tech_focus')
```

Important weakness:
- chart fallback is **not owner-scoped**.
- today this is harmless only because live DB has only `default/default`.
- structurally it would become ambiguous once other owner scopes appear.

---

## 9. E. Customer report misuse judgment

### 9.1 Should default seed appear in customer-facing report?

**Not as the formal customer watchlist truth.**

It may appear only if explicitly disclosed as default observation pool / baseline coverage sample.

### 9.2 If it is only default coverage / collection scope, should it be hidden or only summarized?

Judgment:
- **hidden** as raw full list by default
- if surfaced, it should be **summarized or clearly labeled** as default observation / system baseline scope, not as client-authorized focus pool

### 9.3 What should formal customer-facing display list contract be?

Minimum formal contract should distinguish these classes:
1. `collection_scope`
2. `analysis_universe`
3. `focus/key_focus` product list
4. `archive_target`
5. `customer_display_list`
6. `internal_observation_pool`

A proper customer display contract should specify at least:
- owner/profile identity
- list purpose
- whether it is client-facing or internal-only
- display ranking policy
- allowed domains (stock / asset / tech / macro)
- slot/report applicability

### 9.4 Is a customer-facing list owner/profile/display contract missing?

**Yes.** That is the central contract gap.

Current system has:
- canonical default seed
- archive target families
- some renderer honesty metadata

But it still lacks a distinct, authoritative **customer-facing owner/profile/display list contract** in live use.

### 9.5 Should we distinguish the six scopes listed in the task?

**Yes, explicitly.**

Required separation:
- `collection scope` → what system collects / keeps operationally ready
- `analysis universe` → what producers may analyze
- `focus/key_focus` → product/business-layer watchlist objects
- `archive target` → retention/backfill/write targets
- `customer display list` → what can be shown to the client as recommended focus
- `internal observation pool` → default/default seed or other non-client scopes

Current implementation still partially collapses these together.

---

## 10. F. Support reports

### 10.1 Does Asset have its own focus/key_focus?

**Yes in DB**, but current support-report usage is not first-class.

Evidence:
- `default_asset_key_focus`
- `default_asset_focus`

### 10.2 Does Tech/Tech Stock have its own focus/key_focus?

**Yes**, and current AI/tech support already uses them.

Evidence from `ai_tech_support_producer.py`:

```sql
where fl.owner_type='default' and fl.owner_id='default'
  and fl.name in ('default_tech_focus', 'default_tech_key_focus')
```

### 10.3 Does Macro have its own focus/key_focus?

**Yes in DB**, but macro support does not currently appear to consume those lists as first-class report scope.

### 10.4 Do current customer-facing support reports use those lists?

- Asset support: **No clear first-class usage found** for `default_asset_focus` / `default_asset_key_focus`
- Tech support: **Yes**
- Macro support: **No clear first-class usage found** for `default_macro_focus` / `default_macro_key_focus`

### 10.5 If not, what is the minimum future hookup path?

Minimum future hookup path:
1. keep business-layer seed as source-of-truth object store
2. add explicit per-support-domain producer contract for focus family selection
3. wire only the support producer payload; do not let renderer infer domain lists on its own
4. add separate customer-display gating so support lists are not auto-promoted to client-visible focus without domain-specific display approval

---

## 11. `default/default` vs current customer report truth

### 11.1 Direct judgment

Current customer report still **misuses default seed** if interpreted as a formal customer focus pool.

Why:
- default/default is the only live seed scope
- main producer reads it directly
- renderer/customer surface uses it directly
- no separate customer-owned display list exists in active use

### 11.2 What is true today?

What is true today is narrower:
- current display scope is a **default observation pool sample** sourced from business-layer canonical default seed
- it is not formal client-owned focus truth

That is consistent with the newer producer payload contract metadata, but still means the underlying display contract is incomplete.

---

## 12. Minimal repair recommendations

Audit-only recommendations; no implementation in this task.

1. **Create an explicit customer-display list contract**
   - separate from `default/default`
   - separate from archive targets
   - separate from general collection scope

2. **Do not let renderer/customer profile implicitly upgrade default seed into customer truth**
   - customer surface should consume a dedicated display scope
   - default seed can remain fallback/internal observation pool only

3. **Owner-scope chart fallback**
   - if chart pack keeps DB fallback, it must become owner/profile scoped, not only list-type scoped

4. **Support-domain focus hookup should be explicit**
   - macro support should deliberately choose whether to use macro focus lists
   - asset/commodities support should deliberately choose whether to use asset focus lists
   - no implicit promotion from existence-in-DB to report-display usage

5. **Document the six-scope taxonomy in the business contract**
   - collection scope
   - analysis universe
   - focus/key_focus
   - archive target
   - customer display list
   - internal observation pool

---

## 13. Next-task recommendations

Recommended next tasks, in order:

1. **Define and land a formal customer display list contract**
   - owner/profile/display semantics
   - source-of-truth path
   - report-domain applicability

2. **Make main/support producers read customer display scope explicitly**
   - no renderer-side inference
   - no auto-upgrade from `default/default`

3. **Tighten chart-pack fallback contract**
   - owner/profile/domain-aware fallback only

4. **Decide support-domain adoption plan**
   - macro support: use macro focus or keep current non-focus mode explicitly
   - asset support: use asset focus or keep current non-focus mode explicitly

5. **Backfill documentation to match actual truth**
   - current seed is canonical default seed
   - not formal customer focus pool

---

## 14. Required clear answers summary

### A. Focus list inventory
- Live DB has 11 lists, all under `default/default`.
- Full inventory and counts are listed in Section 3.

### B. `default/default` vs `system/default`
1. Do both exist? **No**
2. Are they duplicates? **No live duplicate rows**
3. Which does report/producer read? **`default/default`**
4. Is the other ignored? **Yes in practice; only appears as metadata concept**
5. Duplication or residue? **Conceptual residue, not live-row duplication**

### C. Current `000001.SZ` onward sequence source
1. Which file creates it? **`ifa_business_layer/defaults.py`**
2. SQL seed or Python defaults? **Python defaults**
3. Formal customer focus pool? **No**
4. Collection coverage seed? **Yes, partly**
5. Dev/test seed? **No, not primarily**
6. Archive target seed? **Yes, partly**
7. Why appearing in report? **Because main producer reads `default/default` directly**

### D. Multi-domain seeds existence
- Stock focus/key_focus: **exists**
- Asset focus/key_focus: **exists**
- Tech focus/key_focus: **exists**
- Macro focus/key_focus: **exists**
- Archive daily/15min/minute: **exists**
- Problem is **scope confusion**, not absence

### E. Customer report misuse judgment
1. Should default seed appear in customer report? **Not as formal customer truth**
2. If only default coverage/collection scope, hide or summarize? **Hide or summarize with explicit label**
3. What should formal customer-facing display contract be? **Dedicated owner/profile/display contract with six-scope separation**
4. Is customer-facing list owner/profile/display contract missing? **Yes**
5. Should six scopes be distinguished? **Yes, explicitly**

### F. Support reports
1. Asset has own focus/key_focus? **Yes**
2. Tech has own focus/key_focus? **Yes**
3. Macro has own focus/key_focus? **Yes**
4. Do current support reports use them? **Tech yes; asset/macro not clearly as first-class focus inputs**
5. Minimum future hookup path? **Producer-level explicit domain selection + customer-display gating**
