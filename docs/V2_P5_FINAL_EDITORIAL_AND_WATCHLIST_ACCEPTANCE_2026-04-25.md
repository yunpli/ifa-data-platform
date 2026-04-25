# V2 P5 Final Editorial and Watchlist Acceptance — 2026-04-25

- Task ID: `ACCEPT-P5-001`
- Acceptance lane: Final Premium Editorial and Watchlist Naming Acceptance
- Reviewer: Acceptance Lane
- Review date: 2026-04-25
- Scope anchor:
  - verify premium editorial phrasing now clears the bar
  - verify premium watchlist naming now clears the bar
  - verify customer leakage remains clean
  - verify chart degrade explanation remains acceptable
- Terminology note: any historical `FCJ` mention is treated as an `FSJ` wording error; no separate FCJ family is assumed here.

## 1. Samples reviewed

### Primary acceptance samples
1. Prior acceptance-fail reference
   - `artifacts/accept_p4_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T045613Z.html`
2. Post final editorial phrasing sample
   - `artifacts/post_p4_editorial_phrasing_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T063056Z.html`
3. Post final watchlist naming sample
   - `artifacts/post_p4_watchlist_naming_001_v2/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T063022Z.html`
4. Fresh acceptance regeneration target
   - `artifacts/accept_p5_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T063530Z.html`

### Chart evidence reviewed
1. Fresh chart manifest
   - `artifacts/accept_p5_001/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`
2. Prior comparison reference
   - `artifacts/accept_p4_001/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`

### Prior acceptance / task references consulted
- `docs/V2_P4_EDITORIAL_AND_WATCHLIST_ACCEPTANCE_2026-04-25.md`
- `docs/POST_P4_EDITORIAL_PHRASING_001_HANDOFF_2026-04-25.md`
- `docs/IFA_Execution_Progress_Monitor.md`
- commits:
  - `2a9ccca` — watchlist naming and rationale polish
  - `e4107f6` — final editorial phrasing pass
  - `bfa67e6` — editorial phrasing push receipt

## 2. Premium editorial phrasing findings

### 2.1 What clearly improved versus P4

1. **Top-of-report briefing quality is better than the prior fail state**
   - The hero judgment now reads more like a customer-facing advisory briefing and less like an upstream contract splice.
   - The summary-card `顾问提示` blocks are shorter, more intentional, and less producer-shaped.
   - `风险提示` / `明日观察 / 下一步` still hold the correct client-briefing structure.

2. **The visible P4 contract-shaped headline phrases are no longer the dominant customer impression**
   - The P4-style blockers such as:
     - `盘前 盘前高频与参考信息`
     - `收盘口径已确认 市场表`
     - `收盘 收盘确认依据`
   - are no longer surfacing in the same crude way at the page-entry level.

3. **The customer page remains materially more readable than the P4 fail sample**
   - The page now opens credibly for a customer.
   - The first-screen experience no longer blocks acceptance by itself.

### 2.2 Why editorial still does not fully clear the premium bar

The final editorial pass improves the page materially, but the deeper section/body copy still does **not** consistently clear a premium family-office / HNW advisory standard.

Examples from the fresh acceptance sample:
- `午后继续验证点：等待盘中 盘中结构信号 刷新后再判断是否出现强化、扩散或分歧`
- `盘前 盘中结构信号 与 观察名单 已足以形成待开盘验证的主线候选，但仍不应视为已确认`
- `将当前 收盘依据已完整 事实作为晚报主线收盘结论依据；盘中留存信息 仅做演化解释，T-1 仅做历史对照`
- `收盘依据已完整 市场表与同日文本事实已足以形成收盘 收盘确认材料，可以做晚报主线结论`

Acceptance judgment:
- the **hero / summary-card / risk-next-step** phrasing is now close to acceptable;
- the **deeper section bullets and repeated body phrasing** still carry obvious contract-derived structure and repetition;
- therefore this does **not** yet qualify as final premium editorial closeout.

### 2.3 Editorial verdict
- `more natural than P4`: **pass**
- `customer-readable at first screen`: **pass**
- `final premium editorial phrasing`: **fail**

The remaining problem is narrow but real: section-level detailed copy still reads like sanitized upstream logic, not fully polished editorial prose.

## 3. Premium watchlist naming findings

### 3.1 What changed versus P4

1. **Customer-visible item names are no longer placeholder-grade**
   - The prior blocker `待补全名称标的（000001.SZ）` style naming is gone from the sampled customer HTML.
   - The fresh sample now uses structured professional fallback labels such as:
     - `核心观察标的一（000001.SZ）`
     - `核心观察标的二（000002.SZ）`
     - `核心观察标的三（000004.SZ）`

2. **Per-item rationale now reads like an advisory watchlist, not metadata leakage**
   - Each item carries:
     - `纳入原因`
     - `盘中观察要点`
     - `需要下调关注的情形`
   - This is materially closer to how a professional watchlist should read.

3. **The empty-state wording is now professional enough**
   - `补充观察名单暂未展开` is acceptable as a bounded customer-facing empty-state.
   - It no longer reads like a missing data placeholder or renderer fallback accident.

### 3.2 Watchlist quality judgment

This is still not ideal long-term naming, because real company names would be better than ordinal labels.

However, for the specific acceptance criterion in scope — **premium watchlist naming and rationale no longer failing on placeholder-grade customer wording** — the bar is now cleared.

Acceptance judgment:
- `no raw ticker-primary / placeholder-grade naming`: **pass**
- `customer-visible watchlist module reads professionally enough`: **pass**
- `long-term ideal naming completeness`: **still improvable, but non-blocking for this acceptance**

### 3.3 Watchlist verdict
## PASS

The remaining naming improvement path is enhancement-grade, not blocking-grade.

## 4. Leakage findings

### 4.1 Leakage recheck scope
I rechecked the fresh customer acceptance output against the standard customer-surface leakage patterns:
- `bundle_id`
- `producer_version`
- `slot_run_id`
- `replay_id`
- `report_links`
- `file:///`
- `artifact_id`
- `renderer version`
- `action=`
- `confidence=`
- `evidence=`
- `FCJ`
- prior telemetry/editorial blockers:
  - `validation=unknown`
  - `emotion=unknown`
  - `样本 0 条`
  - `待补全名称标的`
  - `暂无 Focus Watchlist`

### 4.2 Leakage verdict
- **Pass on classic engineering-field leakage** in the customer HTML.
- **Pass on `FCJ` leakage**.
- **Pass on prior telemetry/noise blockers**.
- **Pass on prior customer-visible placeholder watchlist naming blockers**.

### 4.3 Important nuance
The delivery package still contains internal manifest/package materials with internal fields by design. That is not a customer-surface regression.

Acceptance judgment:
- customer leakage remains clean
- no new customer-surface leakage regression observed

## 5. Final pass/fail against the two remaining premium criteria

### Criterion 1 — premium editorial phrasing
**FAIL**

Reason:
- the top-level reading experience is improved and mostly acceptable;
- but section-level body phrasing still exposes sanitized contract logic, repeated wording, and upstream-shaped sentence structure;
- therefore the report does not yet fully clear a true premium editorial standard.

### Criterion 2 — premium watchlist naming
**PASS**

Reason:
- the prior blocking placeholder naming is gone from the customer sample;
- customer-visible watchlist items and empty-state wording now read professionally enough for this milestone;
- remaining ideal-name enhancement work is not blocking this criterion anymore.

### Overall verdict
## FAIL for `ACCEPT-P5-001`

Reason:
- one of the two remaining premium criteria is now genuinely closed (`premium watchlist naming`);
- the other one (`premium editorial phrasing`) remains a narrow but honest blocker;
- leakage remains clean and chart degrade explanation remains acceptable.

This is a **single-residual narrow fail**, not a broad fail.

## 6. Residual gaps and whether blocking

### Residual gap 1 — section-level editorial phrasing is still too upstream-shaped
Examples:
- `盘中 盘中结构信号`
- `收盘依据已完整 市场表与同日文本事实已足以形成收盘 收盘确认材料`
- repeated “验证 / 形成 / 确认” logic chains that read like sanitized contract output rather than editorial prose

Blocking status:
- **Blocking** for final premium editorial closeout
- this is the only remaining blocking gap in scope

### Residual gap 2 — watchlist still uses ordinal fallback names instead of real company names
Blocking status:
- **Non-blocking** for this acceptance
- worth improving later, but no longer a failure-grade customer wording issue

### Residual gap 3 — chart pack remains partial (`2/3 ready`)
Blocking status:
- **Non-blocking**
- customer degrade explanation remains acceptable and unchanged from prior accepted reasoning

## 7. Exact paths, tests/checks, commits

### Exact paths reviewed
- `docs/V2_P4_EDITORIAL_AND_WATCHLIST_ACCEPTANCE_2026-04-25.md`
- `docs/POST_P4_EDITORIAL_PHRASING_001_HANDOFF_2026-04-25.md`
- `docs/IFA_Execution_Progress_Monitor.md`
- `artifacts/accept_p4_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T045613Z.html`
- `artifacts/post_p4_editorial_phrasing_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T063056Z.html`
- `artifacts/post_p4_watchlist_naming_001_v2/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T063022Z.html`
- `artifacts/accept_p5_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T063530Z.html`
- `artifacts/accept_p5_001/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`
- `src/ifa_data_platform/fsj/report_rendering.py`
- `tests/unit/test_fsj_report_rendering.py`

### Tests / checks run
1. Unit validation
   - `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_rendering.py`
   - Result: `34 passed`

2. Fresh customer-sample generation
   - `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/accept_p5_001 --report-run-id-prefix accept-p5-main-early`
   - Result: succeeded; fresh acceptance sample generated under `artifacts/accept_p5_001/...`

3. Targeted customer-surface recheck
   - Check patterns reviewed:
     - `盘前高频与参考信息`
     - `收盘口径已确认`
     - `收盘确认依据`
     - `待补全名称标的`
     - `暂无 Focus Watchlist`
     - `补充观察名单暂未展开`
     - `核心观察标的一`
     - `核心观察标的二`
     - `bundle_id|producer_version|slot_run_id|replay_id|report_links|file:///|artifact_id|renderer version|action=|confidence=|evidence=`
     - `FCJ`
     - `validation=unknown|emotion=unknown|样本 0 条`
   - Result summary:
     - customer HTML remained clean for leakage/noise blockers
     - watchlist naming blocker from P4 no longer appeared in customer HTML
     - section-level editorial phrasing still showed premium-quality residual stiffness

### Commits reviewed as implementation evidence
- `2a9ccca` — `Polish premium watchlist naming and rationale`
- `04a38e5` — `Update progress monitor for watchlist naming task`
- `e4107f6` — `Document final premium editorial phrasing pass`
- `bfa67e6` — `Record editorial phrasing push receipt`

### Acceptance conclusion for monitor truth
- `ACCEPT-P5-001` verdict: **honest FAIL**
- closed criterion:
  1. premium watchlist naming — closed
- remaining blocker:
  1. premium editorial phrasing — still blocking
