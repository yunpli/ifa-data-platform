# V2 P4 Editorial and Watchlist Acceptance — 2026-04-25

- Task ID: `ACCEPT-P4-001`
- Acceptance lane: Premium Customer Editorial and Watchlist Acceptance
- Reviewer: Acceptance Lane
- Review date: 2026-04-25
- Scope anchor:
  - verify customer facts are no longer raw / noisy
  - verify `validation=unknown` / `emotion=unknown` / `样本 0 条` style telemetry is gone from customer surface
  - verify top judgment is more natural
  - verify risk / next-step reads like advisor briefing
  - verify focus / key-focus reads more like a professional advisory watchlist
  - verify customer leakage remains clean
  - verify chart degrade explanation remains acceptable
- Terminology note: any historical `FCJ` mention is treated as an `FSJ` wording error; no separate FCJ family is assumed here.

## 1. Samples reviewed

### Primary acceptance samples
1. Prior fail reference from `ACCEPT-P3-001`
   - `artifacts/post_p2_customer_sanitize_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T040821Z.html`
2. Post editorial compression sample
   - `artifacts/post_p3_editorial_compression_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T044216Z.html`
3. Post professional watchlist wording sample
   - `artifacts/post_p3_watchlist_pro_001/main_early_2026-04-23_dry_run/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T044415Z.html`
4. Post watchlist metadata quality sample
   - `artifacts/post_p3_watchlist_quality_002/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T045318Z.html`
5. Fresh acceptance regeneration target
   - `artifacts/accept_p4_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T045613Z.html`

### Chart evidence reviewed
1. Fresh chart manifest
   - `artifacts/accept_p4_001/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`
2. Prior P3 comparison reference
   - `artifacts/post_p2_chart_focus_probe_v2/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`

### Prior acceptance / progress references consulted
- `docs/V2_P3_EDITORIAL_AND_CHART_FOCUS_ACCEPTANCE_2026-04-25.md`
- `docs/IFA_Execution_Progress_Monitor.md`
- commits:
  - `f330af3` — watchlist metadata quality hardening
  - `4ebedb4` — professional watchlist wording upgrade
  - `8d0c4da` — watchlist quality receipt update

## 2. Editorial quality findings

### 2.1 Clear improvements versus the P3 fail state

1. **Raw/noisy customer facts are materially compressed now**
   - In the fresh customer sample, the obvious P3 blockers no longer appear on the customer page:
     - `validation=unknown`
     - `emotion=unknown`
     - `竞价样本 0 条`
     - `1m 样本 0 条`
     - `广度 0 条`
     - `热度 0 条`
     - `信号状态 0 条`
   - Customer-facing fact blocks now read as compressed advisory prose such as:
     - `盘前市场侧确认仍然偏弱，当前更适合把相关方向视为待开盘验证的观察线索，而非直接上升为明确主线。`
     - `盘中结构验证尚不充分，当前更适合观察量价扩散、板块承接与情绪修复是否逐步形成。`
   - Acceptance judgment: this specific P3 blocker is fixed on the customer surface.

2. **Top judgment is more natural than the earlier fail state**
   - It is still upstream-shaped, but it now reads more like a human briefing and less like raw telemetry wrapping.
   - The top line now frames a decision posture rather than exposing `validation` / `emotion` style state.
   - Acceptance judgment: improved and directionally correct.

3. **Risk / next-step now has the right advisor-briefing structure**
   - The page still uses explicit `风险提示` and `明日观察 / 下一步` blocks.
   - The content is now easier to read than the prior raw-fact-heavy form and is organized around observation points rather than engineering fields.
   - Acceptance judgment: structurally acceptable and materially better than P3.

4. **Section-level customer narrative is cleaner**
   - `顾问提示` and `补充视角` remain customer-shaped.
   - The page no longer looks like an internal evidence packet with a thin customer shell.
   - Acceptance judgment: meaningful upgrade from the P3 fail state.

### 2.2 Residual editorial weakness that still blocks premium acceptance

Despite the above, the current customer main still does **not** consistently clear a premium advisory/editorial bar.

#### A. Customer prose still feels too upstream-shaped and repetitive
Examples from the fresh sample:
- `A股盘前主线预案：已基于盘前 盘前高频与参考信息 形成待开盘验证的主线候选`
- `A股收盘主线复盘：已基于 收盘口径已确认 市场表与 当日 文本事实形成收盘结论`
- `收盘口径已确认 市场表`
- `收盘 收盘确认依据`

Acceptance judgment:
- This is better than P3, but still not premium editorial finish.
- The language remains recognizably contract-adjacent and mechanically transformed rather than fully written as a polished client note.

#### B. Top judgment passes the “more natural” check but not the “premium natural” bar
The top judgment is now acceptable as a milestone improvement, but still repeats its own producer-derived clause and over-relies on the same sentence structure used elsewhere on the page.

Acceptance judgment:
- `more natural`: **pass**
- `premium customer editorial quality`: **fail**

#### C. Risk / next-step reads like a briefing, but still not at family-office polish level
The block now has briefing shape, but key lines still depend too heavily on raw upstream phrasing embedded inside quotation-like framing.

Acceptance judgment:
- `advisor briefing shape`: **pass**
- `premium advisory finish`: **partial / below closeout bar**

## 3. Watchlist quality findings

### 3.1 What improved and should be credited

1. **Focus/key-focus now renders as an advisory watchlist module instead of a raw dump**
   - The structure is now clearly professionalized:
     - `Tier 1 / Key Focus`
     - `Tier 2 / Focus Watchlist`
     - each item includes:
       - `观察逻辑`
       - `今日验证点`
       - `风险/失效条件`
   - Acceptance judgment: this is materially better than the P3 fail state.

2. **The empty Tier 2 fallback is professional enough**
   - It now reads:
     - `补充观察池暂未扩展`
     - with rationale, validation trigger, and invalidation logic.
   - Acceptance judgment: this specific prior weakness is fixed.

3. **The duplicated raw ticker naming failure is gone**
   - The earlier ugly pattern like `A股标的 000001.SZ（000001.SZ）` is no longer the customer-facing output.
   - Acceptance judgment: fixed.

### 3.2 Residual watchlist blocker

The module still fails the final premium watchlist bar because the visible names are still placeholder-grade.

Examples from the fresh sample:
- `待补全名称标的（000001.SZ）`
- `待补全名称标的（000002.SZ）`
- `待补全名称标的（000004.SZ）`

Acceptance judgment:
- This is cleaner than a duplicated raw ticker dump.
- But it still does **not** read like a real professional advisory watchlist for a premium customer.
- A premium watchlist needs actual company/strategy naming, or at minimum a more curated human-readable label than repeated placeholder stubs.

### 3.3 Overall watchlist verdict
- `reads more like a professional advisory watchlist`: **partial pass for structure, fail for final-quality naming**
- The module is no longer embarrassing.
- The module is not yet attach-to-client premium watchlist quality.

## 4. Leakage findings

### 4.1 Leakage recheck scope
I rechecked the fresh customer sample against the standard customer-surface leakage patterns:
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
- prior editorial telemetry blockers:
  - `validation=unknown`
  - `emotion=unknown`
  - `样本 0 条`

### 4.2 Leakage verdict
- **Pass on classic engineering-field leakage** in the customer HTML.
- **Pass on `FCJ` leakage**.
- **Pass on the previously failing telemetry strings** on the customer surface.

### 4.3 Important nuance
The delivery package still contains internal/review JSON and captions with internal fields such as `artifact_id` and `candidate_with_open_validation`, but those are inside the package internals rather than the customer HTML surface.

Acceptance judgment:
- customer leakage remains clean
- no new customer-surface leakage regression observed

## 5. Pass / fail against premium customer editorial + watchlist criteria

### Criterion-by-criterion verdict
1. **Customer facts are no longer raw / noisy**
   - **Pass**
   - Reason: the previous raw telemetry and `validation=unknown` / `emotion=unknown` customer-surface problem is no longer present in the sampled customer HTML.

2. **`validation=unknown` / `emotion=unknown` / `样本 0 条` telemetry is gone from customer surface**
   - **Pass**
   - Reason: targeted recheck on the fresh customer output did not find those strings in the customer HTML.

3. **Top judgment is more natural**
   - **Pass**
   - Reason: it is visibly more natural than the P3 fail sample, even though it is still not premium-polished.

4. **Risk / next-step reads like an advisor briefing**
   - **Pass (qualified)**
   - Reason: the section shape and customer intent are right; wording quality still has residual upstream stiffness.

5. **Focus / key-focus now reads more like a professional advisory watchlist**
   - **Fail**
   - Reason: structure is improved, but placeholder item naming (`待补全名称标的`) keeps it below premium professional-watchlist quality.

6. **Customer leakage remains clean**
   - **Pass**
   - Reason: no customer-surface engineering leakage regression found.

7. **Chart degrade explanation remains acceptable**
   - **Pass**
   - Reason: chart pack remains `2/3 ready`, and the remaining missing chart is still explained in acceptable customer language.

### Overall verdict
## FAIL for `ACCEPT-P4-001`

Reason:
- The P3 acceptance blockers around raw/noisy customer telemetry are genuinely fixed.
- Leakage remains clean.
- Chart degrade explanation remains acceptable.
- But the combined premium customer editorial + watchlist acceptance bar is still not met because:
  1. editorial language remains too close to upstream contract phrasing, and
  2. watchlist item naming is still placeholder-grade rather than premium advisory-grade.

This is an **honest narrow fail with reduced residual scope**, not a broad fail.

## 6. Residual gaps and whether blocking

### Residual gap 1 — upstream-shaped editorial phrasing still visible
Examples:
- `盘前 盘前高频与参考信息`
- `收盘口径已确认 市场表`
- `收盘 收盘确认依据`

Blocking status:
- **Blocking for premium editorial closeout**
- **Not blocking for milestone proof that raw/noisy telemetry has been suppressed**

### Residual gap 2 — placeholder watchlist names remain on customer surface
Examples:
- `待补全名称标的（000001.SZ）`
- `待补全名称标的（000002.SZ）`
- `待补全名称标的（000004.SZ）`

Blocking status:
- **Blocking for premium watchlist closeout**
- This is now the clearest remaining watchlist-quality blocker.

### Residual gap 3 — advisor language still repeats producer-derived clauses too often
Blocking status:
- **Blocking for premium editorial finish**
- **Non-blocking for customer-surface cleanliness / telemetry suppression acceptance**

## 7. Exact paths, tests/checks, commits

### Exact paths reviewed
- `docs/V2_P3_EDITORIAL_AND_CHART_FOCUS_ACCEPTANCE_2026-04-25.md`
- `docs/IFA_Execution_Progress_Monitor.md`
- `artifacts/post_p2_customer_sanitize_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T040821Z.html`
- `artifacts/post_p3_editorial_compression_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T044216Z.html`
- `artifacts/post_p3_watchlist_pro_001/main_early_2026-04-23_dry_run/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T044415Z.html`
- `artifacts/post_p3_watchlist_quality_002/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T045318Z.html`
- `artifacts/accept_p4_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T045613Z.html`
- `artifacts/accept_p4_001/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`
- `src/ifa_data_platform/fsj/report_rendering.py`
- `tests/unit/test_fsj_report_rendering.py`

### Tests / checks run
1. Unit validation
   - `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_rendering.py`
   - Result: `34 passed`

2. Fresh customer-sample generation
   - `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/accept_p4_001 --report-run-id-prefix accept-p4-main-early`
   - Result: succeeded; fresh acceptance sample generated under `artifacts/accept_p4_001/...`

3. Customer-surface leakage / telemetry targeted recheck
   - `rg -n "validation=unknown|emotion=unknown|样本 0 条|竞价样本 0 条|候选龙头 0 个|信号状态 0 条|1m 样本 0 条|广度 0 条|热度 0 条|A股标的 000001\.SZ（000001\.SZ）|待补全名称标的（000001\.SZ）|high\+reference|same-day stable/final|candidate_with_open_validation|watchlist_only|close package|final market packet ready|bundle_id|producer_version|slot_run_id|replay_id|report_links|file:///|artifact_id|renderer version|action=|confidence=|evidence=|FCJ" -S artifacts/accept_p4_001`
   - Result summary:
     - customer HTML remained clean for classic leakage and removed telemetry blockers
     - internal package files still contain internal fields by design
     - placeholder watchlist names remain visible in customer HTML

### Commits reviewed as implementation evidence
- `f330af3` — `Harden watchlist metadata quality and sample readability`
- `4ebedb4` — `Professionalize customer focus watchlist wording`
- `8d0c4da` — `Record watchlist quality receipt`

### Acceptance conclusion for monitor truth
- `ACCEPT-P4-001` verdict: **honest FAIL**
- Narrow remaining blockers:
  1. premium editorial finish still incomplete
  2. premium watchlist naming still incomplete
