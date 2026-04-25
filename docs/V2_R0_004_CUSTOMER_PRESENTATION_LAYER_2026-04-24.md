# V2-R0-004 Customer-facing presentation layer｜2026-04-24

## 1. Current customer-visible rendering / assembly / orchestration chain

### 1.1 MAIN chain
1. `src/ifa_data_platform/fsj/report_assembly.py`
   - `MainReportAssemblyService.assemble_main_sections(...)`
   - Pulls assembled section objects for `early / mid / late`.
   - Each section currently carries both customer-usable business content and engineering/internal fields together:
     - customer-usable: `title`, `summary`, `judgments`, `signals`, `facts`, `support_summaries[].summary`
     - internal: `bundle.bundle_id`, `bundle.producer_version`, `bundle.slot_run_id`, `bundle.replay_id`, `lineage.*`, `support_summaries[].bundle_id`, `support_summaries[].producer_version`, `support_summaries[].lineage.*`

2. `src/ifa_data_platform/fsj/report_orchestration.py`
   - `build_main_report_delivery_publisher(...)`
   - `MainReportMorningDeliveryOrchestrator.run_workflow(...)`
   - Orchestration itself does not define a customer presentation object; it invokes publish/render services using the assembled engineering-shaped artifact.

3. `src/ifa_data_platform/fsj/report_rendering.py`
   - `MainReportRenderingService.render_main_report_html(...)`
   - `MainReportArtifactPublishingService.publish_main_report_html(...)`
   - `MainReportArtifactPublishingService.publish_delivery_package(...)`
   - Before this task, `MainReportHTMLRenderer._render_section(...)` directly exposed engineering fields into HTML:
     - `bundle_id`
     - `producer_version`
     - `slot_run_id`
     - `replay_id`
     - `lineage.evidence_links[].ref_key`
     - `lineage.report_links[].artifact_uri`
     - `lineage.support_bundle_ids`
   - Result: customer-visible HTML was effectively an engineering object dump with presentation styling.

### 1.2 SUPPORT chain
1. `src/ifa_data_platform/fsj/report_assembly.py`
   - `SupportReportAssemblyService.assemble_support_section(...)`
   - Produces one support section carrying `summary/judgments/signals/facts` plus internal `bundle` + `lineage` details.

2. `src/ifa_data_platform/fsj/report_rendering.py`
   - `SupportReportRenderingService.render_support_report_html(...)`
   - `SupportReportArtifactPublishingService.publish_support_report_html(...)`
   - `SupportReportArtifactPublishingService.publish_delivery_package(...)`
   - Before this task, support HTML directly exposed:
     - `bundle_id`
     - `producer_version`
     - `slot_run_id`
     - `replay_id`
     - evidence refs and prior report links

3. Current support summary merge logic
   - MAIN does **not** inline full support reports.
   - MAIN consumes only `support_summaries[]` concise summaries from assembly.
   - This merge boundary was already good; the leak was that MAIN still rendered internal support lineage metadata in the support summary block footnotes.

### 1.3 Existing reusable presentation object / schema audit result
- No dedicated customer-facing presentation schema existed.
- Existing reusable object was the **assembly artifact**, but it is an internal/business-engineering mixed object, not a customer-safe projection.
- Therefore the minimal safe move is: **add a renderer-layer projection object**, not refactor collector/data paths.

---

## 2. Customer-facing presentation schema recommendation

### 2.1 Minimal schema introduced in this task
`fsj_customer_main_presentation` / `v1`

```json
{
  "schema_type": "fsj_customer_main_presentation",
  "schema_version": "v1",
  "business_date": "2026-04-23",
  "market": "a_share",
  "summary_cards": [
    {
      "slot": "early",
      "slot_label": "早报 / 盘前",
      "headline": "一句话摘要",
      "support_themes": [
        {"domain": "宏观", "summary": "补充摘要"}
      ]
    }
  ],
  "sections": [
    {
      "slot": "early",
      "slot_label": "早报 / 盘前",
      "title": "开盘前关注",
      "summary": "时段摘要",
      "status": "ready",
      "highlights": ["重点结论 1", "重点结论 2"],
      "signals": ["跟踪信号 1"],
      "facts": ["已知事实 1"],
      "support_themes": [
        {"domain": "宏观", "summary": "补充摘要"}
      ]
    }
  ]
}
```

### 2.2 Design choice
- Keep projection in renderer layer.
- Preserve assembly/orchestration/publishing internals unchanged.
- Internal/review behavior stays on current renderer path.
- Customer profile switches to projection + customer HTML template.

---

## 3. Internal fields that must be excluded from customer profile

### 3.1 MAIN
Must not appear in customer HTML:
- `bundle.bundle_id`
- `bundle.producer_version`
- `bundle.slot_run_id`
- `bundle.replay_id`
- `lineage.evidence_links[].ref_key`
- `lineage.report_links[].artifact_uri`
- `lineage.support_bundle_ids[]`
- `signals[].attributes_json.contract_mode` raw engineering phrasing
- `judgment_action / signal_strength / confidence / evidence_level` bracket-style engineering attrs
- any raw `section_render_key`, `bundle_topic_key`, `report_run_id`

### 3.2 SUPPORT
Must not appear in customer HTML:
- `bundle.bundle_id`
- `bundle.producer_version`
- `bundle.slot_run_id`
- `bundle.replay_id`
- `lineage.evidence_links[].ref_key`
- `lineage.report_links[].artifact_uri`
- raw section keys / render keys / internal locator fields

### 3.3 What still belongs to internal/review profile
Internal/review should retain:
- lineage pointers
- bundle identifiers
- producer/version lineage
- slot replay/run pointers
- QA/package/operator review surfaces
- report-link persistence metadata

---

## 4. Minimal early / mid / late customer presentation structure

### early
- title: `开盘前关注`
- content blocks:
  - 一句话摘要
  - 重点结论
  - 跟踪信号
  - 已知事实
  - 补充视角（support concise summaries only）

### mid
- title: `盘中观察`
- content blocks:
  - 一句话摘要
  - 重点结论
  - 跟踪信号
  - 已知事实
  - 补充视角

### late
- title: `收盘复盘`
- content blocks:
  - 一句话摘要
  - 重点结论
  - 跟踪信号
  - 已知事实
  - 补充视角

### page-level customer structure
1. Hero / cover
2. 今日节奏（summary cards by slot）
3. 分时段解读（early/mid/late projected sections）

---

## 5. Concrete files involved

### changed in this task
- `src/ifa_data_platform/fsj/report_rendering.py`
- `scripts/fsj_main_report_publish.py`
- `scripts/fsj_support_report_publish.py`
- `scripts/fsj_report_cli.py`
- `tests/unit/test_fsj_report_rendering.py`
- `tests/unit/test_fsj_main_report_publish_script.py`
- `tests/unit/test_fsj_support_report_publish_script.py`
- `docs/V2_R0_004_CUSTOMER_PRESENTATION_LAYER_2026-04-24.md`
- `docs/IFA_Execution_Progress_Monitor.md`

### inspected for this task
- `src/ifa_data_platform/fsj/report_rendering.py`
- `src/ifa_data_platform/fsj/report_assembly.py`
- `src/ifa_data_platform/fsj/report_orchestration.py`
- current HTML artifacts under `artifacts/v2_r0_003_validation/...`

---

## 6. Minimal implementation path executed

### implemented
1. Added explicit `output_profile` handling in renderer/publishing services.
2. Added customer-only projection object in `MainReportHTMLRenderer` metadata:
   - `customer_presentation`
   - `presentation_schema_version=v1`
3. Added customer HTML template for MAIN:
   - renders only summary/highlights/signals/facts/support themes
   - no engineering lineage footer
4. Added customer HTML template for SUPPORT:
   - same principle, no engineering metadata exposure
5. Passed `--output-profile` through canonical publish scripts:
   - `scripts/fsj_main_report_publish.py`
   - `scripts/fsj_support_report_publish.py`
6. Removed old CLI hard-stop that rejected customer profile in `scripts/fsj_report_cli.py`.
7. Added unit coverage proving customer HTML strips engineering fields while internal/review behavior remains compatible.

### intentionally not changed
- no collector refactor
- no `highfreq/midfreq/lowfreq/archive_v2` data-path change
- no FCJ changes
- no dispatch redesign
- no chart platform
- no bypass of business-layer LLM gateway
- no runtime freeze conflict

---

## 7. Split needed?

No.

Reason:
- Minimal presentation layer could be implemented safely at renderer/publish-script boundary.
- No collector/orchestration refactor was required.
- Internal/review path remained backward-compatible.

---

## 8. Acceptance summary

Status: **completed**

Acceptance condition met:
- current chain audited
- customer-facing schema defined
- excluded internal fields enumerated
- early/mid/late presentation structure defined
- concrete files identified
- minimal implementation path executed in same task
- progress monitor updated
- validations executed
- commit recorded: `1fc24b83fd87820f7599ffbb678ac24501483015`
- push status: already pushed to `origin/a-lane-p4-3-llm-field-lineage`

## 9. Validation rerun evidence (replacement verification run)

Executed on replacement run:
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_rendering.py tests/unit/test_fsj_main_report_publish_script.py tests/unit/test_fsj_support_report_publish_script.py`
  - result: `28 passed in 0.33s`
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_orchestration.py tests/unit/test_fsj_report_evaluation.py`
  - result: `7 passed in 0.28s`
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m py_compile src/ifa_data_platform/fsj/report_rendering.py scripts/fsj_main_report_publish.py scripts/fsj_support_report_publish.py scripts/fsj_report_cli.py`
  - result: success
