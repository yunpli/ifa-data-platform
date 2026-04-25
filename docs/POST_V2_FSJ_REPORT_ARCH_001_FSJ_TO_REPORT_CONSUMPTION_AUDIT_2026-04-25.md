# POST-V2-FSJ-REPORT-ARCH-001 — FSJ → Report Consumption Audit (2026-04-25)

## Scope / conclusion in one screen

This is an audit-first report of the **real** `DB raw evidence -> FSJ -> report_assembly -> report_rendering -> customer HTML` chain in `ifa-data-platform`.

### Executive verdict

1. **FSJ currently has real content.**
   - `ifa2.ifa_fsj_bundles`, `ifa2.ifa_fsj_objects`, `ifa2.ifa_fsj_edges`, `ifa2.ifa_fsj_evidence_links`, `ifa2.ifa_fsj_observed_records`, `ifa2.ifa_fsj_report_links`, `ifa2.ifa_fsj_report_artifacts` are live and populated.
   - For `2026-04-23`, main + support bundles exist with non-empty fact / signal / judgment objects.

2. **FSJ is only partially sufficient for an early report.**
   - It is sufficient for an **honest “pre-open candidate / validation plan” report**.
   - It is **not sufficient** for a strong named mainline thesis because the early main bundle does not yet materialize **concrete named market mainlines / chain winners / anchor names** as structured judgments.

3. **The report is not truly consuming FSJ in a section-semantic way.**
   - `report_assembly` does load FSJ bundles and objects correctly.
   - But `report_rendering` mostly rephrases `bundle.summary` + generic fact/signal/judgment statements into customer prose, instead of rendering a structured `market_briefing_sections` object model.

4. **The main break is not “DB can’t reach FSJ”. The break is later.**
   - The real breakpoints are:
     1. DB evidence is aggregated into **coverage/count/probe-style facts** instead of **market facts for report sections**.
     2. Early main FSJ creates only **one abstract judgment** (`mainline_plan`) rather than named mainline sections.
     3. Support FSJ is **not merged structurally** into main-report judgment; only concise summaries are passed through.
     4. Renderer builds customer output from **editorial transforms** over summary/fact/signal text, not from a formal section contract.

5. **Raw counts appear because they were already promoted into FSJ fact objects.**
   - The renderer is not inventing those counts from DB directly at final step.
   - The producer already converts DB coverage probes into customer-visible FSJ facts, and renderer then sanitizes/paraphrases them.

6. **A middle layer is missing.**
   - There is currently no formal `market_briefing_sections`-style artifact between FSJ graph and customer presentation.
   - That missing layer is exactly why support judgments do not become main judgment, why core thesis stays abstract, and why coverage metrics leak into customer sections.

---

## Method / evidence sources

Inspected:

- Docs:
  - `docs/IFA_Execution_Context_and_Behavior.md`
  - `docs/IFA_Execution_Progress_Monitor.md`
  - `IFA_Implementation_Enhancement_Task_List_V2.md`
  - `docs/V2_FEATURE_COMPLETION_AUDIT_2026-04-25.md`
  - `docs/POST_P6_DB_TRUTH_001_DB_TABLE_TRUTH_AND_REPORT_DATA_CONTRACT_AUDIT_2026-04-25.md`
- Code:
  - `src/ifa_data_platform/fsj/store.py`
  - `src/ifa_data_platform/fsj/early_main_producer.py`
  - `src/ifa_data_platform/fsj/report_assembly.py`
  - `src/ifa_data_platform/fsj/report_rendering.py`
- DB rows in live schema `ifa2.*`
- Generated sample artifact:
  - `artifacts/post_p6_symbol_evidence_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T084056Z.html`
  - manifest: `artifacts/post_p6_symbol_evidence_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T084056Z.manifest.json`

No HTML polish or collector work was performed in this task.

---

## 1. What FSJ tables / artifacts / bundles currently exist

### 1.1 Live FSJ schema objects

From `src/ifa_data_platform/fsj/store.py`:

- `ifa2.ifa_fsj_bundles`
- `ifa2.ifa_fsj_objects`
- `ifa2.ifa_fsj_edges`
- `ifa2.ifa_fsj_evidence_links`
- `ifa2.ifa_fsj_observed_records`
- `ifa2.ifa_fsj_report_links`
- `ifa2.ifa_fsj_report_artifacts`

This means the platform already has:
- bundle-level FSJ persistence,
- object graph persistence,
- evidence lineage,
- report linkage.

### 1.2 Live bundles for `2026-04-23`

Observed bundles in DB:

- Main:
  - `fsj:a_share:2026-04-23:early:main:pre_open_main:2ae1ab6e33c3e4bb`
  - `fsj:a_share:2026-04-23:mid:main:midday_main:ba5e575821bdb56f`
  - `fsj:a_share:2026-04-23:late:main:post_close_main:b9ce5881ac3a45b9`
- Support:
  - `a_share:2026-04-23:early:macro:support_macro:143a4e15bdd3`
  - `a_share:2026-04-23:late:macro:support_macro:7846ec308c0c`
  - `a_share:2026-04-23:early:commodities:support_commodities:0cfeb8bec554`
  - `a_share:2026-04-23:late:commodities:support_commodities:352ced72b914`
  - `a_share:2026-04-23:early:ai_tech:support_ai_tech:8b9512842822`
  - `a_share:2026-04-23:late:ai_tech:support_ai_tech:d48a4e501a47`

### 1.3 What objects they contain

#### Main early bundle contains real FSJ objects

Bundle:
- `fsj:a_share:2026-04-23:early:main:pre_open_main:2ae1ab6e33c3e4bb`

Objects found:

Facts:
- `fact:early:daily_market_backdrop`
- `fact:early:market_inputs`
- `fact:early:reference_scope`
- `fact:early:text_backdrop`
- `fact:early:text_catalysts`

Signal:
- `signal:early:mainline_candidate_state`

Judgment:
- `judgment:early:mainline_plan`

Lineage counts:
- `ifa_fsj_evidence_links = 12`
- `ifa_fsj_observed_records = 12`
- `ifa_fsj_edges = 6`

So FSJ is not empty / mocked; it is materially populated.

#### Support early bundles also contain real FSJ objects

Macro early:
- facts for archive background, CPI, PMI, PPI, latest text
- signal: `signal:early:macro:risk_appetite`
- judgment: `judgment:early:macro:open_bias`

Commodities early:
- facts for futures background, text, AL/CU/PB contracts
- signal: `signal:early:commodities:mapping_quality`
- judgment: `judgment:early:commodities:chain_watch`

AI-tech early:
- facts for themes (`先进封装`, `存储芯片`, `第三代半导体`, etc.), archive background, focus scaffold, latest text
- signal: `signal:early:ai_tech:mainline_candidacy`
- judgment: `judgment:early:ai_tech:priority_watch`

So support FSJ is also real, not placeholder-only.

---

## 2. Exact FSJ bundle contents for `2026-04-23` early main

Bundle summary:

> `A股盘前主线预案：已基于盘前 high+reference 形成待开盘验证的主线候选。`

### 2.1 Facts

1. `fact:early:daily_market_backdrop`
   - Statement:
   - `盘前可回溯的日级市场背景仍可提供参考：指数样本 285 条，北向资金最近一日净额 353095.26，最近一日涨停 0 家、跌停 0 家，最近一日龙虎榜 2584 条；板块表现最新可见领涨方向为 中船系（1.95%）。`

2. `fact:early:market_inputs`
   - Statement:
   - `盘前市场侧输入覆盖：竞价样本 0 条，事件流 8 条，候选龙头 0 个，信号状态 0 条。`

3. `fact:early:reference_scope`
   - Statement:
   - `当前业务观察池覆盖 30 个 A 股 focus/key-focus 对象，可作为盘前主线验证与噪音过滤锚点。`

4. `fact:early:text_backdrop`
   - Statement:
   - `隔夜/近期文本库可回溯规模：新闻 5134 条、公告 22098 条、研报 1447 条、投资者问答 6361 条，可用于开盘前做背景筛选与重点核对。`

5. `fact:early:text_catalysts`
   - Statement is a count + long preview of text entries.

### 2.2 Signal

- `signal:early:mainline_candidate_state`
- Statement:
  - `盘前 high layer 与 reference seed 已足以形成待开盘验证的主线候选，但仍不应视为已确认。`

### 2.3 Judgment

- `judgment:early:mainline_plan`
- Statement:
  - `将当前候选主线作为开盘首要验证对象；若竞价强度和事件延续性无法继续兑现，则立即降回观察项。`

### 2.4 Payload-level truth that matters

Bundle `payload_json` also shows:

- `contract_mode = candidate_with_open_validation`
- `completeness_label = complete`
- `has_high_evidence = true`
- `has_low_evidence = true`
- focus scope contract explicitly says current display is **default observation pool sample**, not formal customer truth:
  - `formal_customer_focus_truth = false`
  - `display_honesty_mode = default_observation_pool_sample`

This is important: the system already knows the focus/watchlist is not formal customer truth, but the report still uses that scaffold heavily.

---

## 3. Does `report_assembly` actually consume FSJ objects?

## Answer: **Yes, mechanically yes. Semantically not enough.**

### Evidence

From `src/ifa_data_platform/fsj/report_assembly.py`:

- `MainReportAssemblyService.assemble_main_sections()` loads main bundle graphs from `ifa_fsj_bundles`.
- `MainReportSectionAssembler._build_section()` projects:
  - `summary = bundle.get("summary")`
  - `judgments = _project_objects(..., "judgment")`
  - `signals = _project_objects(..., "signal")`
  - `facts = _project_objects(..., "fact")`
  - plus full lineage.

So assembly **does** consume FSJ bundle + FSJ objects.

### But the semantic contract is too shallow

The assembled section shape is still only:
- one section summary,
- flat facts/signals/judgments lists,
- support summaries,
- lineage.

It is **not** a domain-specific market briefing structure like:
- mainline thesis,
- confirming evidence,
- named chain leaders / breadth,
- invalidation / risk,
- support overlays merged into thesis,
- explicit next-session observation points.

So the assembler is structurally correct, but still too generic to support a customer-grade market report without renderer improvisation.

---

## 4. Does `report_rendering` mostly consume assembled text instead of structured FSJ objects?

## Answer: **Yes.**

### Evidence

From `src/ifa_data_platform/fsj/report_rendering.py`:

Customer presentation path:
- `_build_customer_presentation()`
- `_customer_item_statements()`
- `_sanitize_customer_text()`
- `_rewrite_customer_telemetry_statement()`
- `_customer_top_judgment()`
- `_customer_risk_block()`
- `_customer_next_steps()`
- `_render_customer_html()`

### What it really uses

Renderer consumes:
- `section.summary`
- statement strings from `section.judgments / signals / facts`
- `support_summaries[].summary`
- focus/watchlist payload from `bundle.payload_json.focus_scope`

Then it rewrites them into customer prose.

### Proof of editorial transform

Examples from code:

- `_customer_item_statements()` sorts and picks statements by object key.
- `_sanitize_customer_text()` replaces internal phrases like:
  - `high+reference`
  - `high layer`
  - `reference seed`
  - `candidate_with_open_validation`
- `_rewrite_customer_telemetry_statement()` converts raw telemetry/count statements into softer prose.
- `_customer_top_judgment()` composes a new headline from summary + highlights instead of rendering a structured thesis object.
- `_customer_risk_block()` and `_customer_next_steps()` are mostly heuristic prose generators.

This means rendering is **text-transform-driven**, not **section-contract-driven**.

---

## 5. In current customer HTML, which parts come from FSJ vs renderer fallback vs DB raw probe/counts?

Using sample artifact:
- HTML: `artifacts/post_p6_symbol_evidence_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T084056Z.html`
- Manifest: matching `.manifest.json`

## 5.1 Directly derived from FSJ main bundle

These are FSJ-derived, though often paraphrased:

- Section summary:
  - HTML: `盘前线索已初步指向主线方向，但是否值得提高仓位或预期，仍要等开盘后的量价与承接确认。`
  - Derived from FSJ early summary + signal/judgment editorial rewrite.

- Core judgment / 顾问提示 / 重点结论:
  - Derived from `judgment:early:mainline_plan`

- 跟踪信号:
  - Derived from `signal:early:mainline_candidate_state`

- 已知事实:
  - Derived from FSJ fact statements, then sanitized.

## 5.2 Derived from support FSJ, but only as summary overlay

HTML support line:
- `AI / 科技：AI / 科技线索有增量变化，可作为盘前主判断的辅助校准。`
- `商品：商品方向出现新变化，可作为盘前主判断的辅助校准。`
- `宏观：宏观背景出现新变化，更适合用于校准主判断边界，而不是直接上升为已验证主线。`

These come from support bundle `summary` fields only, **not from support facts/signals/judgments rendered structurally**.

## 5.3 Derived from raw DB probes/counts promoted into FSJ facts

These customer facts are DB-probe-driven in origin:

- `盘前市场侧确认仍然偏弱...`
  - This is a paraphrase of FSJ fact `fact:early:market_inputs` whose original statement is count-based:
  - `竞价样本 0 条，事件流 8 条，候选龙头 0 个，信号状态 0 条。`

- `当前业务观察池覆盖 30 个 A 股 focus/key-focus 对象...`
  - This is directly from `fact:early:reference_scope`, itself sourced from focus list counts.

- `相关文本与事件线索可作为背景参考...`
  - This is a paraphrase of `fact:early:text_backdrop` and/or `fact:early:text_catalysts`, both count/probe style.

So although the final HTML does not literally print all raw integers anymore, the facts are still **coverage/probe-derived** rather than **market thesis facts**.

## 5.4 Renderer fallback / heuristic prose

These are mostly renderer-composed, not first-class FSJ objects:

- Hero `核心判断`
- `风险提示`
- `明日观察 / 下一步`
- much of slot advisory phrasing
- some watchlist rationale language

These are produced by renderer helpers, not persisted FSJ section objects.

---

## 6. Why raw counts appear instead of real market facts

## Root cause

Raw counts appear because the producer is currently elevating **coverage telemetry** into **customer-visible fact objects**.

### Evidence in producer

From `early_main_producer.py`:

- `_market_fact_statement()` returns:
  - `盘前市场侧输入覆盖：竞价样本 {auction_count} 条，事件流 {event_count} 条，候选龙头 {leader_count} 个，信号状态 {signal_scope_count} 条。`

- `_reference_fact_statement()` returns:
  - `当前业务观察池覆盖 {len(focus_symbols)} 个 A 股 focus/key-focus 对象...`

- `_text_fact_statement()` returns text catalyst count + preview.
- `_daily_market_backdrop_statement()` still includes sample counts such as `指数样本 285 条`, `龙虎榜 2584 条`.
- `_text_backdrop_statement()` includes total counts of news/announcements/research/investor QA.

These are not renderer accidents. They are **producer-level design choices**.

### Why this is wrong for customer report

These fields are valid for:
- internal completeness checks,
- operator diagnostics,
- lineage / audit,
- “why confidence is low/high” metadata.

They are **not** valid as primary customer-facing market facts.

Customer-facing facts should instead say things like:
- which mainline / chain is being observed,
- which concrete market structures are confirming or not confirming,
- which anchor names / sectors / breadth features matter,
- what invalidates the candidate.

---

## 7. Why core judgment remains abstract instead of naming concrete mainline(s)

## Root cause

Because the early main producer creates only a **generic candidate-state signal** plus **generic validate judgment**, but does not create structured **named mainline judgments**.

### Evidence

Current early main judgment:
- `judgment:early:mainline_plan`
- Statement:
  - `将当前候选主线作为开盘首要验证对象；若竞价强度和事件延续性无法继续兑现，则立即降回观察项。`

This says **how to behave**, not **what the mainline is**.

Current early signal:
- `signal:early:mainline_candidate_state`
- Statement:
  - `...形成待开盘验证的主线候选...`

Again, this says candidate status, not named thesis.

### Missing structured objects

What is missing is something like:
- `judgment:early:mainline:ai_compute`
- `judgment:early:mainline:shipbuilding`
- `judgment:early:mainline:gold_resources`

or at least a structured section payload:
- `core_mainline = {...}`
- `secondary_mainlines = [...]`
- `anchor_symbols = [...]`
- `confirming_facts = [...]`
- `invalidators = [...]`

Without that, renderer can only write abstract honesty language.

---

## 8. Why support macro / asset / tech are not truly becoming main-report judgment

## Root cause

Because support bundles are loaded, but main assembly only consumes **support summaries**, and main rendering only displays those summaries as overlays.

### Evidence in assembly

In `report_assembly.py`:

- support bundles are loaded via `_load_support_graphs()`.
- `assemble_support_summary_aggregate()` explicitly documents:
  - `support_reports_remain_separate = True`
  - `main_consumes_only_concise_support_summaries = True`

This is the smoking gun.

### What this means in practice

Support domains do have real FSJ facts/signals/judgments, e.g.:
- macro `judgment:early:macro:open_bias`
- commodities `judgment:early:commodities:chain_watch`
- ai_tech `judgment:early:ai_tech:priority_watch`

But main report does **not** structurally absorb those judgments into:
- mainline ranking,
- mainline confidence adjustment,
- risk boundary definition,
- alternative scenario sections.

It only shows their one-line summaries.

So support is present in system, but **not consumed as judgment logic**.

---

## 9. Is a `market_briefing_sections` middle layer missing?

## Answer: **Yes, this middle layer is missing and is the minimum conceptual repair.**

### Evidence by absence

No code path currently materializes a structured artifact representing market report semantics such as:
- core judgment,
- evidence buckets,
- support overlays,
- risk / invalidation,
- observation list,
- named mainline candidates,
- section-level provenance.

Current artifacts are:
- generic FSJ graph,
- generic assembled sections,
- renderer-built customer presentation.

That gap is exactly where a `market_briefing_sections`-style middle contract should exist.

---

## 10. Does FSJ currently have real content?

## Answer: **Yes.**

Evidence:
- real bundles exist for main + support,
- real object rows exist,
- real edges/evidence/observed-records exist,
- real report links exist,
- sample HTML is linked back to these bundle IDs.

So the problem is **not “FSJ empty / fake.”**

---

## 11. Is FSJ sufficient to support an early report?

## Answer: **Partially sufficient.**

### Sufficient for
- an honest early/pre-open note saying:
  - what level of evidence exists,
  - what needs open validation,
  - what focus/watchlist is relevant,
  - what support domains adjust risk boundaries.

### Not sufficient for
- a convincing customer main report with named investable mainline(s), because the early main FSJ lacks:
  - explicit named mainline judgments,
  - sectioned market facts,
  - main/support fusion logic,
  - internal-vs-customer fact separation.

So: **FSJ is real but not yet report-semantic enough.**

---

## 12. Is the report truly consuming FSJ?

## Answer: **Mechanically yes, semantically no.**

- **Yes**: assembly pulls bundle summaries and FSJ fact/signal/judgment lists.
- **No**: renderer does not render a structured FSJ market model; it mostly editorializes flat statements and support summaries.

So “FSJ-backed” is true in data lineage sense, but “FSJ-native report semantics” is not true yet.

---

## 13. Where exactly is the DB raw evidence -> FSJ -> report chain broken?

### Breakpoint A — producer level: wrong thing promoted to customer fact

DB probe/coverage metrics are being promoted into FSJ facts:
- market input coverage counts,
- text corpus counts,
- watchlist counts,
- sample counts.

This should mostly remain internal metadata / confidence diagnostics.

### Breakpoint B — FSJ object model level: no section-semantic thesis objects

Early main bundle has only:
- 5 generic facts,
- 1 generic candidate-state signal,
- 1 generic plan judgment.

It lacks:
- named mainline judgments,
- confirmers / invalidators bucketed by thesis,
- explicit chain/sector/anchor objects.

### Breakpoint C — main/support integration level: support judgments not fused

Support domains are only passed via `support_summaries`.
No structural consumption of support FSJ judgments into main thesis confidence or alternative scenario tree.

### Breakpoint D — rendering level: renderer composes prose instead of rendering contract

Customer HTML is produced through editorial helper functions, not a formal section artifact.
That makes the output honest-but-abstract and heavily dependent on paraphrase logic.

---

## 14. Which content should remain internal coverage metrics and must not enter customer report?

These should remain internal / audit / QA / lineage only:

1. **Coverage counts / table sample counts**
   - `竞价样本 X 条`
   - `事件流 X 条`
   - `候选龙头 X 个`
   - `信号状态 X 条`
   - `指数样本 X 条`
   - `龙虎榜 X 条`
   - `新闻/公告/研报/问答 总量 X 条`

2. **Archive row counts / freshness telemetry**
   - `archive_rows=39`
   - `rows=778`
   - raw `freshness=stale/fresh` wording

3. **Observation pool / watchlist scale as a headline fact**
   - `覆盖 30 个 A 股 focus/key-focus 对象`
   - valid as internal scope note, but not a core customer market fact

4. **Product / system honesty metadata**
   - `default observation pool sample`
   - `formal_customer_focus_truth = false`
   - should be governance metadata, not section substance

These can stay in:
- lineage,
- QA payload,
- reviewer/internal report,
- confidence diagnostics.

They should not be the main “已知事实” of the customer report.

---

## 15. What formal sections should an early main report have?

Minimum recommended early-report section contract:

1. **盘前主判断 / Core pre-open thesis**
   - What the most likely mainline candidate is
   - Whether it is confirmed / candidate / only watchlist

2. **主判断依据 / Confirming evidence**
   - Market structure facts supporting the candidate
   - Text/event facts supporting the candidate

3. **尚未确认 / Missing confirmation**
   - What still needs to happen after open
   - e.g. breadth, continuation, anchor confirmation, auction strength

4. **风险与失效条件 / Risk & invalidators**
   - What would downgrade the thesis immediately

5. **辅助视角校准 / Support overlays**
   - Macro / commodities / AI-tech only as confidence/risk modifiers
   - not as separate detached summaries

6. **重点跟踪对象 / Named anchors & watchlist**
   - Named anchors linked to thesis
   - why each is tracked
   - what validates / invalidates it

This is much closer to what customer HTML is trying to say, but today that structure lives only in renderer heuristics.

---

## 16. Which FSJ objects / DB evidence should feed each early-report section?

## 16.1 Core pre-open thesis

Should be fed by:
- main FSJ judgment(s): **named mainline candidate judgment objects**
- support-adjusted confidence
- direct linked signals

Not by:
- generic `mainline_plan` alone
- watchlist count

## 16.2 Confirming evidence

Should be fed by:
- market facts tied to the candidate thesis
- text/event facts tied to same thesis
- explicit fact->signal->judgment lineage

Not by:
- DB table coverage counts

## 16.3 Missing confirmation

Should be fed by:
- signal gaps / unconfirmed evidence nodes
- required validation fields from judgment attributes

## 16.4 Risk & invalidators

Should be fed by:
- `judgment.invalidators`
- support-domain negative adjustments
- explicit scenario downgrade conditions

## 16.5 Support overlays

Should be fed by:
- support domain judgments + signals + key facts
- fused into main judgment confidence / risk boundaries

Not by:
- support `summary` only

## 16.6 Named anchors / watchlist

Should be fed by:
- focus items only when attached to a thesis
- evidence-backed symbol / theme relevance
- section-specific validation points

Not by:
- default observation pool size as a headline customer fact

---

## 17. Minimum architecture repair plan

This is the **minimum** repair plan. No collector additions, no big rewrite.

### Repair 1 — stop promoting coverage telemetry as customer facts

At FSJ producer level:
- move count/probe/coverage statements out of `customer-visible fact` role
- keep them in:
  - bundle payload metadata,
  - QA metadata,
  - lineage / audit objects,
  - internal profile only

### Repair 2 — add a section-semantic middle artifact

Add a new middle-layer artifact, e.g.:
- `market_briefing_sections` or `fsj_market_briefing_sections`

For early slot it should produce structured sections like:
- `core_thesis`
- `confirming_evidence`
- `missing_confirmation`
- `risk_invalidators`
- `support_overlays`
- `named_tracking_list`

This should be built from FSJ graph + support graph, not in renderer.

### Repair 3 — make support domains structurally consumable by main

Instead of `main_consumes_only_concise_support_summaries = True`, main assembly should:
- ingest support judgments/signals/facts,
- classify them as confidence modifiers / alternative scenarios / risk boundaries,
- write that into the middle-layer briefing sections.

### Repair 4 — require named thesis objects for early main when available

Early main producer should emit, when evidence exists:
- named thesis candidate(s),
- linked confirming facts/signals,
- linked anchor symbols/themes,
- explicit invalidators.

If not enough evidence, emit an explicit honest null-thesis section:
- `no_single_confirmable_mainline_yet`
- but still structured.

### Repair 5 — renderer becomes a thin presenter

Customer renderer should render the middle-layer section contract, not synthesize investment prose from flat text lists.

The renderer should become:
- layout + style + compression,
- not thesis construction.

---

## 18. Final answers to the required questions

### 1) Does FSJ currently have real content?
**Yes.** Main and support bundles are live and populated with real fact/signal/judgment objects plus evidence lineage.

### 2) Is FSJ sufficient to support an early report?
**Partially.** Sufficient for an honest pre-open candidate/validation report; insufficient for a strong named mainline customer report.

### 3) Is the report truly consuming FSJ?
**Mechanically yes; semantically not enough.** Assembly consumes FSJ objects, but renderer still mostly consumes text summaries/statements and rewrites them.

### 4) Where exactly is the DB raw evidence -> FSJ -> report sections chain broken?
At four points:
- producer promotes coverage telemetry into customer-visible FSJ facts,
- FSJ lacks named section-semantic thesis objects,
- support is only summary-overlay not structural input,
- renderer composes customer meaning from text instead of rendering a formal report-section contract.

### 5) Which content should remain internal coverage metrics and must not enter customer report?
Coverage/sample counts, archive row counts, freshness telemetry, corpus totals, watchlist-size facts, and default-observation-pool governance metadata.

### 6) What formal sections should an early main report have?
- Core pre-open thesis
- Confirming evidence
- Missing confirmation
- Risk / invalidators
- Support overlays
- Named anchors / tracking list

### 7) Which FSJ objects / DB evidence should feed each section?
- Thesis -> named judgment objects
- Confirming evidence -> thesis-linked facts/signals
- Missing confirmation -> required validation/gap objects
- Risk -> invalidators + negative support modifiers
- Support overlays -> support judgments/signals/facts fused into main thesis
- Tracking list -> thesis-linked anchors/watchlist items

### 8) What is the minimum architecture repair plan?
- stop exposing coverage telemetry as report facts,
- add a `market_briefing_sections` middle layer,
- structurally merge support FSJ into main sections,
- produce named thesis objects when evidence exists,
- reduce renderer to thin presentation.

---

## Appendix A — concrete artifact inspected

Customer HTML sample:
- `artifacts/post_p6_symbol_evidence_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T084056Z.html`

Manifest:
- `artifacts/post_p6_symbol_evidence_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T084056Z.manifest.json`

No new artifact generation was required for this audit.
