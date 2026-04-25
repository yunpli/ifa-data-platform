# POST_V2_FSJ_REPORT_ARCH_001 FSJ→Report Consumption Audit (2026-04-25)

## 0. Scope / hard boundary

This is an **audit only** for `2026-04-23` FSJ reality and the current producer → assembly → rendering consumption chain.

Not in scope:
- no schema change
- no collector addition
- no HTML polish
- no renderer wording repair
- no implementation

Evidence sources used in this audit:
- live DB tables under schema `ifa2`
- code in `src/ifa_data_platform/fsj/*` and `scripts/*`
- rendered artifacts under `artifacts/post_v2_db_content_early_001/*`

---

## 1. Executive conclusions

### 1.1 Bottom line

The current stack **does persist real FSJ bundles/objects/evidence links** for `2026-04-23` across early / mid / late and main / support domains. So the problem is **not “FSJ is fake / empty”**.

The actual problem is architectural:

1. **Main FSJ objects are still coverage-contract-shaped, not PM briefing section-shaped.**
   - Example early main judgment is still: “将当前候选主线作为开盘首要验证对象；若竞价强度和事件延续性无法继续兑现，则立即降回观察项。”
   - This is honest, but abstract and meta-level.

2. **Support FSJ is real, but main only consumes support summaries, not support objects.**
   - `report_assembly.py` explicitly states main consumes only concise support summaries.

3. **Customer HTML is mostly assembled presentation text, plus renderer-generated/adapted copy, not direct FSJ object-native section consumption.**
   - `report_rendering.py` rewrites/sanitizes object statements and synthesizes top judgment / risk / next steps / focus watchlist narration.

4. **Raw counts reach customer output because the producers themselves encode coverage/corpus/watchlist telemetry as facts.**
   - Renderer mostly paraphrases them; it does not create them from nowhere.

5. **A middle layer is missing.**
   - There is no `market_briefing_sections`-like layer that converts FSJ Fact/Signal/Judgment + support evidence into formal PM-facing report sections such as:
     - 今日盘前核心判断
     - 昨收至今早发生了什么
     - 市场状态
     - 板块/题材候选
     - 资金与情绪
     - 重要新闻/公告/研报
     - 跨资产/宏观/科技补充
     - 核心关注/关注
     - 今日开盘验证点
     - 风险与失效条件

### 1.2 Direct contradiction to call out

Prior implementation direction emphasized “FSJ-driven report”. Current behavior is only partially true:
- **True:** assembly loads FSJ object rows for main.
- **False / incomplete if interpreted literally:** customer report is not a section-contract report rendered directly from FSJ intelligence objects. It is still a presentation-layer synthesis over:
  - section summary strings,
  - flat fact/signal/judgment lists,
  - support summaries only,
  - focus_scope metadata,
  - customer rewrite/fallback helpers.

That contradiction is the core architectural breakpoint.

---

## 2. DB reality: bundles present on 2026-04-23

### 2.1 Bundle inventory

Live query against `ifa2.ifa_fsj_bundles` for `business_date='2026-04-23'` shows **9 bundles**:

- main / early / `pre_open_main`
- main / mid / `midday_main`
- main / late / `post_close_main`
- macro / early / `support_macro`
- macro / late / `support_macro`
- commodities / early / `support_commodities`
- commodities / late / `support_commodities`
- ai_tech / early / `support_ai_tech`
- ai_tech / late / `support_ai_tech`

Representative bundle IDs used below:
- early main: `fsj:a_share:2026-04-23:early:main:pre_open_main:2ae1ab6e33c3e4bb`
- mid main: `fsj:a_share:2026-04-23:mid:main:midday_main:ba5e575821bdb56f`
- late main: `fsj:a_share:2026-04-23:late:main:post_close_main:b9ce5881ac3a45b9`
- early macro: `a_share:2026-04-23:early:macro:support_macro:143a4e15bdd3`
- early commodities: `a_share:2026-04-23:early:commodities:support_commodities:0cfeb8bec554`
- early ai_tech: `a_share:2026-04-23:early:ai_tech:support_ai_tech:8b9512842822`
- late macro: `a_share:2026-04-23:late:macro:support_macro:7846ec308c0c`
- late commodities: `a_share:2026-04-23:late:commodities:support_commodities:352ced72b914`
- late ai_tech: `a_share:2026-04-23:late:ai_tech:support_ai_tech:d48a4e501a47`

### 2.2 Object count shape

Observed object counts by bundle family from `ifa2.ifa_fsj_objects`:
- early main: 5 facts / 1 signal / 1 judgment
- mid main: 4 facts / 2 signals / 1 judgment
- late main: 4 facts / 2 signals / 1 judgment
- early support bundles: real facts/signals/judgments in all three domains
- late support bundles: real facts/signals/judgments in all three domains

Conclusion: **support FSJ bundles contain real content**, not empty placeholders.

---

## 3. Required table audit samples

### 3.1 `ifa2.ifa_fsj_bundles`

Sample row: early main bundle
- table: `ifa2.ifa_fsj_bundles`
- key: `bundle_id='fsj:a_share:2026-04-23:early:main:pre_open_main:2ae1ab6e33c3e4bb'`
- slot: `early`
- agent_domain: `main`
- section_key: `pre_open_main`
- summary:
  - `A股盘前主线预案：已基于盘前 high+reference 形成待开盘验证的主线候选。`

Sample row: early macro support
- summary:
  - `盘前宏观背景有新变化，应先作为主判断的 adjust 输入，而不是直接当作已验证主线。`

### 3.2 `ifa2.ifa_fsj_objects`

Sample early main objects:
- `fact:early:daily_market_backdrop`
- `fact:early:market_inputs`
- `fact:early:reference_scope`
- `fact:early:text_backdrop`
- `fact:early:text_catalysts`
- `signal:early:mainline_candidate_state`
- `judgment:early:mainline_plan`

Sample late main objects:
- `fact:late:same_day_final_market`
- `fact:late:same_day_text_evidence`
- `signal:late:close_package_state`
- `judgment:late:mainline_close`

Sample support objects:
- macro early judgment: `judgment:early:macro:open_bias`
- commodities early judgment: `judgment:early:commodities:chain_watch`
- ai_tech early judgment: `judgment:early:ai_tech:priority_watch`

### 3.3 `ifa2.ifa_fsj_edges`

The task required inspection. The bundle graphs loaded by `FSJStore.get_bundle_graph()` include edge lineage, and `report_assembly.py` carries them through into `lineage.edges`. In the 2026-04-23 audit, the customer report path does **not** visibly consume these edges for section generation. They are lineage material, not current presentation drivers.

### 3.4 `ifa2.ifa_fsj_evidence_links`

Representative early main evidence links:
- `fact:early:daily_market_backdrop` →
  - `ifa2.index_daily_bar_history`
  - `ifa2.northbound_flow_history`
  - `ifa2.limit_up_down_status_history`
  - `ifa2.dragon_tiger_list_history`
  - `ifa2.sector_performance_history`
- `fact:early:market_inputs` →
  - `ifa2.highfreq_event_stream_working`
  - `ifa2.highfreq_open_auction_working`
- `fact:early:reference_scope` → `ifa2.focus_lists`
- `fact:early:text_backdrop` / `fact:early:text_catalysts` → `ifa2.news_history`

Representative late main evidence links:
- `fact:late:same_day_final_market` →
  - `ifa2.equity_daily_bar_history`
  - `ifa2.northbound_flow_history`
  - `ifa2.limit_up_detail_history`
  - `ifa2.limit_up_down_status_history`
  - `ifa2.dragon_tiger_list_history`
  - `ifa2.sector_performance_history`
- `fact:late:same_day_text_evidence` → `ifa2.news_history`

### 3.5 `ifa2.ifa_fsj_observed_records`

Representative early main observed records:
- `盘前事件流覆盖` with `event_count=8`
- `盘前信号状态覆盖` with `signal_scope_count=0`
- `盘前候选龙头覆盖` with `leader_count=0`
- `盘前竞价快照覆盖` with `auction_count=0`
- `当前业务 seed/focus 覆盖` with `focus_symbols=[...]`, `focus_list_types=['focus','key_focus']`
- `隔夜/近期文本覆盖规模`
- `隔夜/近期文本催化`

Representative late main observed records:
- `same-day 日线 final 覆盖`
- `same-day 北向资金盘后稳定表`
- `same-day 涨停明细稳定表`
- `same-day 板块表现稳定表`
- `same-day 文本/事件事实`

### 3.6 `ifa2.ifa_fsj_report_artifacts`

The system is registering rendered HTML artifacts through `MainReportArtifactPublishingService.publish_main_report_html()` and support publishing services in `report_rendering.py`. For `2026-04-23`, report artifacts exist across multiple dry-run / validation output roots. The artifact family is current-rendered HTML, not a section-contract artifact beyond `fsj_main_report_html` / `fsj_support_report_html`.

### 3.7 `ifa2.ifa_fsj_report_links`

Joined query of `ifa2.ifa_fsj_report_links` + `ifa2.ifa_fsj_bundles` shows:
- support early bundles are linked to `support.ai_tech.early`, `support.commodities.early`, `support.macro.early`
- support late bundles are linked to `support.ai_tech.late`, `support.commodities.late`, `support.macro.late`
- main bundles are linked to `main.pre_open`, `main.midday`, `main.post_close`

Critical observation:
- the same main bundles are linked to many later-rendered HTML artifacts across multiple dry-runs.
- report links tell us artifacts exist and lineage is attached.
- they do **not** prove main consumed support objects structurally; only support bundle summaries are merged in current assembly.

---

## 4. 2026-04-23 early main bundle: exact facts / signals / judgments

Bundle:
- `fsj:a_share:2026-04-23:early:main:pre_open_main:2ae1ab6e33c3e4bb`

### 4.1 Facts

#### Fact 1
- object_key: `fact:early:daily_market_backdrop`
- object_type: `market`
- statement:
  - `盘前可回溯的日级市场背景仍可提供参考：指数样本 285 条，北向资金最近一日净额 353095.26，最近一日涨停 0 家、跌停 0 家，最近一日龙虎榜 2584 条；板块表现最新可见领涨方向为 中船系（1.95%）。`
- evidence shape:
  - daily history / stable tables
  - observed from `index_daily_bar_history`, `northbound_flow_history`, `limit_up_down_status_history`, `dragon_tiger_list_history`, `sector_performance_history`
- assessment:
  - **real DB-derived**, not renderer fallback
  - but it is a **coverage/count/backdrop fact**, not a PM-ready market-state sentence

#### Fact 2
- object_key: `fact:early:market_inputs`
- object_type: `market`
- statement:
  - `盘前市场侧输入覆盖：竞价样本 0 条，事件流 8 条，候选龙头 0 个，信号状态 0 条。`
- evidence shape:
  - highfreq working tables
  - `highfreq_event_stream_working`, `highfreq_open_auction_working`, `highfreq_intraday_signal_state_working`, `highfreq_leader_candidate_working`
- assessment:
  - **real DB-derived**, not renderer fallback
  - directly exposes telemetry / coverage counts to report chain

#### Fact 3
- object_key: `fact:early:reference_scope`
- object_type: `reference`
- statement:
  - `当前业务观察池覆盖 30 个 A 股 focus/key-focus 对象，可作为盘前主线验证与噪音过滤锚点。`
- evidence shape:
  - business seed / focus list metadata
  - `ifa2.focus_lists` + related list items
- assessment:
  - **real DB-derived**, but not market intelligence in client language
  - this is an internal scope-control fact presented as a report fact

#### Fact 4
- object_key: `fact:early:text_backdrop`
- object_type: `news`
- statement:
  - `隔夜/近期文本库可回溯规模：新闻 5134 条、公告 22098 条、研报 1447 条、投资者问答 6361 条，可用于开盘前做背景筛选与重点核对。`
- evidence shape:
  - counts over text/history tables
  - `news_history + announcements_history + research_reports_history + investor_qa_history`
- assessment:
  - **real DB-derived**, but again coverage telemetry rather than client-readable investment fact

#### Fact 5
- object_key: `fact:early:text_catalysts`
- object_type: `news`
- statement begins:
  - `隔夜/近期文本催化共 8 条，最新线索包括：...`
- evidence shape:
  - sampled titles from text/history tables
- assessment:
  - **real DB-derived**, but current sample is noisy and not curated into PM briefing language

### 4.2 Signal

#### Signal 1
- object_key: `signal:early:mainline_candidate_state`
- object_type: `confirmation`
- statement:
  - `盘前 high layer 与 reference seed 已足以形成待开盘验证的主线候选，但仍不应视为已确认。`
- based_on_fact_keys:
  - `fact:early:market_inputs`
  - `fact:early:reference_scope`
  - `fact:early:text_catalysts`
  - `fact:early:daily_market_backdrop`
  - `fact:early:text_backdrop`
- assessment:
  - generated from real facts
  - **not fallback logic**
  - but semantically still meta/contract language (`high layer`, `reference seed`) rather than PM-facing mainline thesis

### 4.3 Judgment

#### Judgment 1
- object_key: `judgment:early:mainline_plan`
- object_type: `thesis`
- statement:
  - `将当前候选主线作为开盘首要验证对象；若竞价强度和事件延续性无法继续兑现，则立即降回观察项。`
- judgment_action: `validate`
- priority: `p0`
- attributes_json:
  - `contract_mode='candidate_with_open_validation'`
  - `required_open_validation=true`
  - deferred includes `support-agent merge not yet implemented`
- assessment:
  - **real FSJ judgment derived from DB-backed facts/signals**
  - but still generic: it does not answer “which exact A-share mainline / sector / chain is today’s core pre-open thesis?”

### 4.4 Are early main facts/signals/judgments real or fallback?

Answer:
- **Real DB evidence exists and is linked.**
- But the **semantic level is weak**:
  - facts are dominated by coverage counts / corpus size / watchlist size / sample excerpts
  - the signal is a contract-state statement
  - the judgment is a validation policy statement
- Therefore current early main FSJ is **real but insufficiently translated**.

---

## 5. Mid / late main reality

### 5.1 Mid main

Bundle summary:
- `A股盘中主线更新：盘中 high layer 证据不足或不够新鲜，仅保留跟踪/观察级更新。`

Key facts/signals/judgment:
- `fact:mid:intraday_structure`:
  - `1m 样本 0 条，广度 0 条，热度 0 条，信号状态 0 条；最新 validation=unknown，emotion=unknown。`
- `fact:mid:leader_and_event_state`:
  - `龙头候选 0 个，事件流 8 条；当前优先观察对象包括：暂无龙头样本。`
- `signal:mid:plan_validation_state`:
  - `当前盘中结构证据不足或已明显断档，只能保留‘预案跟踪中/等待更新’的中性判断。`
- `judgment:mid:mainline_update`:
  - `当前仅输出 observe/track-only 的盘中更新，不输出‘强化/分歧/转强已确认’这类强结论。`

Conclusion:
- mid main is also **real DB-backed**, but dominated by insufficient intraday structure telemetry.
- It tells the truth that data is thin, but yields no PM-grade midday market structure section.

### 5.2 Late main

Bundle summary:
- `A股收盘主线复盘：已基于 same-day stable/final 市场表与 same-day 文本事实形成收盘结论。`

Key facts/signals/judgment:
- `fact:late:same_day_final_market`
  - `日线 20 条，北向资金 1 条，涨停明细 85 条，涨跌停状态 1 条，龙虎榜 61 条，板块表现 394 条。`
- `fact:late:same_day_text_evidence`
  - `same-day 可追溯文本/事件事实 8 条...`
- `signal:late:close_package_state`
  - `same-day stable/final 市场表与同日文本事实已足以形成收盘 close package，可以做晚报主线结论。`
- `judgment:late:mainline_close`
  - `将当前 same-day stable/final 事实作为晚报主线收盘结论依据；intraday retained 仅做演化解释，T-1 仅做历史对照。`

Conclusion:
- late main is also real, and stronger than early/mid in evidence contract terms.
- But it is still **closure-contract language**, not fund-manager-style recap language.

---

## 6. Support bundle reality and whether support enters main

## 6.1 Early support bundles contain real content

### Macro early
- judgment:
  - `盘前将宏观作为 adjust 输入：提示主 Agent 校准风险偏好与表述力度，但不把宏观背景直接写成 A股开盘结构已成立。`
- evidence includes:
  - `ifa2.macro_history`
  - `ifa2.ifa_archive_macro_daily`
  - `ifa2.news_history`
- issue:
  - CPI / PMI / PPI are stale (`2026-02-01`)

### Commodities early
- judgment:
  - `盘前将商品链作为 adjust 输入：提高黄金/有色/黑色链的监控优先级，但不把商品波动直接写成A股已验证主线。`
- evidence includes:
  - `commodity_15min_history`
  - `futures_history`
  - `news_history`
- issue:
  - futures sample is stale (`latest trade_date=2025-09-12`, snapshots `2025-06-16`)

### AI-tech early
- judgment:
  - `盘前将 AI-tech 作为 adjust 输入：提高主 Agent 对算力/半导体/机器人等子主题的监控优先级，但不把题材预判写成已确认主线。`
- evidence includes:
  - `sector_performance_history`
  - `ifa_archive_sector_performance_daily`
  - `news_history`
  - focus scaffold metadata

## 6.2 Late support bundles also contain real content

Examples:
- macro late judgment:
  - `晚报把宏观沉淀为 next-day watch...`
- commodities late judgment:
  - `晚报将商品链沉淀为 next-day watch...`
- ai_tech late judgment:
  - `晚报将 AI-tech 作为 counter/adjust 输入：提示主 Agent 下调次日优先级...`

## 6.3 Do support judgments enter the main report?

**Not structurally.**

Evidence:
- `src/ifa_data_platform/fsj/report_assembly.py`
  - `assemble_main_sections()` loads support graphs via `_load_support_graphs()`
  - `_build_support_summary()` returns only bundle-level summary + lineage pointers
  - `assemble_support_summary_aggregate()` business rule explicitly states:
    - `support_reports_remain_separate: True`
    - `main_consumes_only_concise_support_summaries: True`
- live assembled output for `2026-04-23`:
  - early section support summaries only:
    - ai_tech: `盘前 AI-tech 有新催化/板块强弱变化，应作为主判断的 adjust 输入。`
    - commodities: `盘前商品链有新变化，应作为主判断的 adjust 输入。`
    - macro: `盘前宏观背景有新变化，应先作为主判断的 adjust 输入，而不是直接当作已验证主线。`
  - late section support summaries only:
    - ai_tech / commodities / macro summary lines present
  - mid section: no support summaries

So:
- **support bundle existence: yes**
- **support summaries in main: yes**
- **support fact/signal/judgment structural merge into main judgment: no**

---

## 7. Producer → assembly → rendering chain audit

## 7.1 What are early_main_producer rules?

Evidence: `src/ifa_data_platform/fsj/early_main_producer.py`

Observed rule pattern from code + persisted objects:
- reads from multiple data layers:
  - daily market backdrop tables
  - highfreq working tables
  - text/history tables
  - focus list/reference scope
- builds a bundle with:
  - facts for backdrop / market_inputs / reference_scope / text coverage / text catalysts
  - one signal for candidate-state confirmation
  - one judgment for open validation plan
- contract mode is intentionally constrained:
  - early slot is `candidate_with_open_validation`
  - no implication of late/final confirmation
- deferred flags in judgment attributes include:
  - `support-agent merge not yet implemented`
  - `section-level multi-judgment expansion deferred`

Interpretation:
- the producer is optimized for **contract honesty**, not rich PM report structure.

## 7.2 Does `report_assembly` truly read FSJ objects?

Yes.

Evidence: `src/ifa_data_platform/fsj/report_assembly.py`
- `FSJReportAssemblyStore.list_bundle_graphs()` loads bundle graphs from FSJ tables.
- `_build_section()` injects into each section:
  - `judgments = self._project_objects(objects, 'judgment')`
  - `signals = self._project_objects(objects, 'signal')`
  - `facts = self._project_objects(objects, 'fact')`
- lineage also carries:
  - bundle
  - objects
  - edges
  - evidence_links
  - observed_records
  - report_links

So assembly is not skipping FSJ objects.

## 7.3 Does `report_rendering` consume FSJ objects or mostly assembled text?

Answer: **both, but customer output is mostly presentation-layer synthesis.**

Evidence: `src/ifa_data_platform/fsj/report_rendering.py`
- renderer receives `assembled['sections']`
- customer layer builds:
  - `_build_customer_presentation()`
  - `_customer_top_judgment()`
  - `_customer_risk_block()`
  - `_customer_next_steps()`
  - `_customer_item_statements()`
  - `_sanitize_customer_text()`
  - `_refine_customer_summary()`
- focus/watchlist block is built through:
  - `_build_focus_module()`
  - `_build_focus_watch_item()`
  - multiple fallback rationales / validation / invalidation functions

Meaning:
- raw FSJ objects are inputs
- but customer report wording is extensively rewritten / synthesized
- there is no direct “FSJ judgment 1 maps to customer section X paragraph 1” contract

## 7.4 In current customer HTML, what comes from FSJ?

From FSJ / assembly:
- section summaries
- flat judgment/signal/fact statements (after sanitation/refinement)
- support summaries
- focus_scope payload metadata from bundle payloads
- lineage metadata / report-link counts in internal mode

## 7.5 What comes from renderer fallback / synthesis?

Evidence from `report_rendering.py`:
- top-level core judgment (`_customer_top_judgment`)
- risk block (`_customer_risk_block`)
- next-step block (`_customer_next_steps`)
- watchlist display names if names are weak / missing (`_format_focus_display_name`)
- watchlist rationales / validation points / invalidation points
  - `_fallback_key_focus_rationale`
  - `_fallback_focus_watch_rationale`
  - `_focus_validation_point`
  - `_focus_invalidation_point`
- telemetry statement rewrites
  - `_rewrite_customer_telemetry_statement`
- summary rewrites
  - `_refine_customer_summary`

This is not “renderer fallback” in the narrow null-safe sense only; it is **substantive presentation generation**.

## 7.6 What comes from DB raw probes/counts?

Directly from producers and then passed through:
- `指数样本 285 条`
- `竞价样本 0 条`
- `事件流 8 条`
- `候选龙头 0 个`
- `信号状态 0 条`
- `观察池覆盖 30 个 A 股 focus/key-focus 对象`
- `新闻 5134 条、公告 22098 条、研报 1447 条、投资者问答 6361 条`
- late same-day coverage counts:
  - `日线 20 条`
  - `涨停明细 85 条`
  - `板块表现 394 条`

## 7.7 What was stuffed in to “make it look populated”?

Evidence-backed answer:
- not fake rows, but **internal coverage telemetry and watchlist scaffolding were promoted into customer-visible facts**.
- examples:
  - `reference_scope` fact based on focus list size
  - text corpus counts
  - zero-count intraday structure facts
  - focus-module generated rationale when symbol-specific intelligence is thin

So the report feels populated because it uses:
1. telemetry counts,
2. watchlist scaffolding,
3. renderer-generated professional prose,
4. support summary prose,
not because the system extracted a strong sector-thesis graph.

## 7.8 Why do raw counts reach customer report?

Because producers encode them as FSJ facts.

Evidence:
- early main persisted facts are themselves count statements.
- renderer only sanitizes/paraphrases them; it does not newly invent those counts.

Root cause:
- **producer fact contract is too close to data coverage audit language**.
- no middle layer filters “internal observability facts” from “client-facing market facts”.

## 7.9 Why are core judgments still abstract instead of fund-manager-style mainline judgments?

Because the FSJ judgment contract currently answers:
- “what evidence class is allowed at this slot?”
- “what action mode is allowed: validate / watch / confirm?”

It does **not** yet require:
- named mainline candidate(s)
- market state classification
- sector/theme ranking
- fund-flow / emotion framing
- explicit validation and invalidation sections in PM language

So the system outputs slot-contract judgments, not PM briefing judgments.

## 7.10 Is a `market_briefing_sections`-like middle layer missing?

**Yes. This is the core missing layer.**

Current chain:
- DB evidence → producer → FSJ objects → assembly(flat section lists) → renderer(customer synthesis)

Missing chain:
- DB evidence → producer → FSJ objects → **briefing section compiler** → renderer

That missing compiler should translate FSJ into formal report sections and separate:
- internal telemetry
- evidence summary
- customer-facing investment language

---

## 8. DB evidence → FSJ → report breakpoints

## 8.1 Which DB evidence enters FSJ?

Main:
- `index_daily_bar_history`
- `northbound_flow_history`
- `limit_up_down_status_history`
- `dragon_tiger_list_history`
- `sector_performance_history`
- `highfreq_event_stream_working`
- `highfreq_open_auction_working`
- `highfreq_intraday_signal_state_working`
- `highfreq_leader_candidate_working`
- `highfreq_stock_1m_working`
- `highfreq_sector_breadth_working`
- `highfreq_sector_heat_working`
- `equity_daily_bar_history`
- `limit_up_detail_history`
- `news_history`
- `announcements_history`
- `research_reports_history`
- `investor_qa_history`
- `focus_lists` / focus list items

Support:
- `macro_history`
- `ifa_archive_macro_daily`
- `futures_history`
- `commodity_15min_history`
- `ifa_archive_sector_performance_daily`
- `sector_performance_history`
- `news_history`

## 8.2 Which evidence enters FSJ but not report?

- support bundle objects (facts/signals/judgments) do not structurally enter main report
- edges are carried in lineage but not used to construct customer sections
- observed_records payload details are not section-compiled for customer use

## 8.3 Which enters report but is not translated into client-readable investment language?

Examples:
- `盘前市场侧输入覆盖：竞价样本 0 条，事件流 8 条，候选龙头 0 个，信号状态 0 条。`
- `当前业务观察池覆盖 30 个 A 股 focus/key-focus 对象...`
- `隔夜/近期文本库可回溯规模...`
- `same-day 收盘稳定市场层覆盖...`

These are truthful, but they remain operational telemetry rather than investment language.

## 8.4 Which content should remain internal coverage metrics only?

Should remain internal / QA / lineage only:
- corpus row counts
- focus scope counts
- raw sample counts (`竞价样本`, `1m样本`, `事件流`, `信号状态`)
- report link multiplicity
- archive row counts
- stale-data coverage counters

## 8.5 Which evidence should become Fact?

Client-facing Fact examples should be transformed from current evidence such as:
- sector performance → “昨日至今，涨幅居前方向为中船系/可燃冰/环氧丙烷”
- northbound flow → “北向最近一日净流入/流出显示风险偏好并未失真/仍偏谨慎”
- limit-up detail/history → “昨日连板与涨停扩散并未形成强势普遍共振”
- text evidence → “隔夜新增催化主要集中在AI链/资源链/个股问答，广泛度有限”

## 8.6 Which should become Signal?

- pre-open validation quality
- whether sector strength is forming common direction or only isolated names
- whether AI-tech is catalyst-only but no diffusion
- whether commodities/macros are adjust-only or should elevate mainline ranking
- whether intraday structure is broken / incomplete

## 8.7 Which should become Judgment?

- today’s pre-open core bias
- candidate sectors/themes to verify first
- what must be seen after open to upgrade thesis
- what invalidates thesis immediately
- next-day late-slot carryover priorities

## 8.8 Which should become customer-facing sections?

The report should expose formal sections, not telemetry facts.

---

## 9. What current customer HTML actually contains

Artifact inspected:
- `artifacts/post_v2_db_content_early_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T125500Z.html`

Observed behavior from code + assembly + rendered artifact family:
- customer title is generated by `_customer_report_title()`
- “核心判断” comes from `_customer_top_judgment()` synthesis
- summary cards come from refined section summaries + support summary lines
- focus/watchlist content comes from `focus_scope` payload plus renderer-generated rationale / validation / invalidation copy
- section bullets are selected / sanitized from flat FSJ facts/signals/judgments

Therefore:
- the customer HTML is **not empty-fallback fiction**
- but it is also **not a direct rendering of a formal FSJ investment briefing structure**

---

## 10. Current architecture breakpoints

### Breakpoint 1: producer fact contract is observability-heavy
Current facts are often counts / coverage / scope statements.

### Breakpoint 2: main judgment contract is slot-policy-heavy
Current judgments express validation mode, not concrete market thesis hierarchy.

### Breakpoint 3: support integration stops at summary merge
Support objects do not enrich main judgment graph.

### Breakpoint 4: no section compiler exists
No explicit transformation from FSJ graph to PM briefing section objects.

### Breakpoint 5: renderer is doing editorial synthesis
Renderer shoulders too much semantic responsibility:
- judgment summarization
- risk synthesis
- next-step synthesis
- watchlist narration synthesis

### Breakpoint 6: internal telemetry leaks into customer surface
Because there is no internal-vs-client fact split.

---

## 11. Minimal repair recommendations (architecture only)

### 11.1 Add a middle layer: `market_briefing_sections`
Minimal new artifact should sit between assembly and rendering.

Input:
- main FSJ objects
- support FSJ objects or support-compiled outputs
- selected evidence / observed records

Output:
- formal section objects for customer/internal/report use

### 11.2 Split facts into two classes
- internal telemetry facts
- customer-facing market facts

### 11.3 Upgrade early judgment contract
Require early main producer/translator layer to output:
- candidate mainline(s)
- why now
- what to verify at open
- what invalidates immediately

### 11.4 Support should not only merge as summaries
Main should consume at least support judgments/signals in structured form:
- adjust
- support
- counter
- next_day_watch

### 11.5 Move prose generation after section semantics are fixed
Renderer should render section contract, not invent investment logic.

---

## 12. Concrete next tasks (architecture fixes, not HTML polish)

1. **POST-V2-FSJ-REPORT-ARCH-002**
   - define `market_briefing_sections` schema/artifact
   - no HTML work

2. **POST-V2-FSJ-REPORT-ARCH-003**
   - build FSJ→briefing-section compiler for early slot
   - map Fact/Signal/Judgment + support relation types into section objects

3. **POST-V2-FSJ-REPORT-ARCH-004**
   - classify and suppress internal telemetry facts from customer section surface

4. **POST-V2-FSJ-REPORT-ARCH-005**
   - add structured support merge policy:
     - macro = adjust / amplifier
     - commodities = adjust / mapping chain
     - ai_tech = adjust / counter / priority signal

5. **POST-V2-FSJ-REPORT-ARCH-006**
   - make renderer consume briefing sections only
   - keep FSJ lineage in metadata, not as semantic author

---

## 13. Early report target section design (30-year A-share PM view)

Below is the formal section design that should exist for **early report**.

### 13.1 今日盘前核心判断
**Purpose**: one to three mainline judgments in plain PM language.
- source today: `judgment:early:mainline_plan` + `signal:early:mainline_candidate_state`
- required enrichment: support judgments + sector/theme ranking evidence
- current gap: missing named mainline / no ranking

### 13.2 昨收至今早发生了什么
**Purpose**: overnight event chain and market carryover.
- source evidence:
  - `fact:early:daily_market_backdrop`
  - `fact:early:text_catalysts`
  - support latest_text facts
- current gap: raw counts and noisy samples not curated into event chain

### 13.3 市场状态
**Purpose**: risk appetite / breadth / carryover / whether market is trendable or fragmented.
- source evidence:
  - `northbound_flow_history`
  - `limit_up_down_status_history`
  - sector performance
  - previous close stable tables
- current gap: counts exist; state classification layer missing

### 13.4 板块 / 题材候选
**Purpose**: rank candidate themes.
- source evidence:
  - early main text catalysts
  - ai_tech support facts/signals
  - commodities support facts/signals
  - sector performance top sectors
- current gap: support is not structurally merged; ranking absent

### 13.5 资金与情绪
**Purpose**: sentiment and flow framing.
- source evidence:
  - northbound flow
  - limit-up/down status
  - dragon tiger / leader candidate / auction / intraday state when present
- current gap: currently shown as counts, not sentiment interpretation

### 13.6 重要新闻 / 公告 / 研报
**Purpose**: curated catalysts, not corpus size.
- source evidence:
  - `text_catalysts`
  - support `latest_text`
- current gap: noisy title sampling, no curation/ranking

### 13.7 跨资产 / 宏观 / 科技补充
**Purpose**: adjust/counter/support overlay.
- source evidence:
  - macro/commodities/ai_tech support judgments + signals + top facts
- current gap: main only carries summary strings

### 13.8 核心关注 / 关注
**Purpose**: real watchlist with explicit reason and validation point.
- source evidence:
  - focus_scope payload
  - symbol-level evidence hits
  - support relation / text event support
- current gap: current watchlist block is heavily renderer-generated from scaffolding metadata

### 13.9 今日开盘验证点
**Purpose**: what market must show in first minutes.
- source evidence:
  - early main judgment contract already has required_open_validation
  - should combine with sector/theme candidate list and support overlays
- current gap: not sectionized

### 13.10 风险与失效条件
**Purpose**: explicit downgrade criteria.
- source evidence:
  - early main judgment invalidation condition
  - support counter signals
  - thin-data warnings
- current gap: currently synthesized by renderer, not explicit FSJ section contract

---

## 14. Final audit answer matrix

### A. FSJ data/object reality
1. Early main exact facts/signals/judgment: **documented above in §4**.
2. They do exist. 5 facts / 1 signal / 1 judgment.
3. Evidence source shape is concrete and table-backed.
4. They are DB-derived, not renderer fallback.
5. Support bundles contain real content: **yes**.
6. Macro / commodities / ai_tech support judgments enter main report: **only as concise summary strings, not as structured main judgment inputs**.

### B. Producer → assembly → rendering chain
1. early_main_producer rules: build honest candidate-with-open-validation FSJ from backdrop + highfreq inputs + text + focus scope.
2. report_assembly truly reads FSJ objects: **yes**.
3. report_rendering consumes assembled objects but customer output is mostly rewritten/synthesized presentation.
4. Customer HTML from FSJ: section summaries, bullet candidates, support summaries, focus metadata.
5. From renderer fallback/synthesis: top judgment, risk, next steps, watchlist prose, statement rewrites.
6. From raw DB counts: many current facts and section bullets.
7. Stuffed-in population: internal telemetry + focus scaffolding + synthesized prose.
8. Raw counts reach report because producers made them facts.
9. Core judgments remain abstract because contract is slot-policy-based, not PM-section-based.
10. `market_briefing_sections`-like layer is missing: **yes**.

### C. DB evidence → FSJ → report breakpoints
1. Evidence entering FSJ: documented in §8.1.
2. Evidence entering FSJ but not report: support objects, edges, observed-record detail.
3. Evidence entering report but not translated: coverage counts / watchlist counts / telemetry.
4. Internal-only content: telemetry counts and lineage metrics.
5. Fact / Signal / Judgment / customer section mapping: documented in §8 and §13.

### D. Early report target section design
Required formal sections and mappings: **documented in §13**.

---

## 15. Primary evidence appendix

### 15.1 Code references
- `src/ifa_data_platform/fsj/report_assembly.py`
  - `_project_objects()`
  - `_build_support_summary()`
  - `assemble_support_summary_aggregate()` business rules
- `src/ifa_data_platform/fsj/report_rendering.py`
  - `_build_customer_presentation()`
  - `_customer_top_judgment()`
  - `_customer_risk_block()`
  - `_customer_next_steps()`
  - `_build_focus_module()`
  - `_fallback_key_focus_rationale()`
  - `_fallback_focus_watch_rationale()`
  - `_rewrite_customer_telemetry_statement()`
  - `_refine_customer_summary()`
- `src/ifa_data_platform/fsj/main_publish_cli.py`
  - publish flow wraps producer persistence + report publish script
- `scripts/fsj_report_cli.py`
  - customer profile still routes through current publishing/rendering chain
- `scripts/fsj_main_early_publish.py`
  - early flow uses `EarlyMainFSJProducer`

### 15.2 Representative SQL / query evidence used
- bundle inventory from `ifa2.ifa_fsj_bundles`
- object extraction from `ifa2.ifa_fsj_objects`
- evidence link extraction from `ifa2.ifa_fsj_evidence_links`
- observed record extraction from `ifa2.ifa_fsj_observed_records`
- report-link join from `ifa2.ifa_fsj_report_links` + `ifa2.ifa_fsj_bundles`
- assembled section inspection through `MainReportAssemblyService.assemble_main_sections(business_date='2026-04-23')`

### 15.3 One-line verdict

**FSJ is real; report architecture is not.** The current system persists real FSJ evidence and judgments, but it still lacks the section-compiler layer that turns those objects into a true customer-grade A-share market briefing.