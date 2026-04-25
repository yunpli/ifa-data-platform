# V2 P3 Editorial and Chart/Focus Acceptance — 2026-04-25

- Task ID: `ACCEPT-P3-001`
- Acceptance lane: Premium Editorial and Chart/Focus Quality Acceptance
- Reviewer: Acceptance Lane
- Review date: 2026-04-25
- Scope anchor:
  - premium editorial / advisory-note quality
  - top judgment less templated
  - facts less raw / noisy
  - risk / next-step more advisor-quality
  - chart partial improved or customer-facing explanation improved enough
  - focus / key-focus more like a professional advisory watchlist
  - customer leakage recheck
- Terminology note: any historical `FCJ` mention is treated as an `FSJ` wording error; no separate FCJ family is assumed here.

## 1. Samples reviewed

### Primary acceptance samples
1. Baseline pre-P2 customer-tightened sample
   - `artifacts/post_p1_customer_report_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T034424Z.html`
2. Post editorial finish sample
   - `artifacts/post_p2_editorial_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T040057Z.html`
3. Post chart/focus polish sample
   - `artifacts/post_p2_chart_focus_probe_v2/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T040459Z.html`
4. Latest post sanitize sample used as final customer-facing acceptance target
   - `artifacts/post_p2_customer_sanitize_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T040821Z.html`

### Chart evidence reviewed
1. Baseline chart manifest
   - `artifacts/post_p1_customer_report_001/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`
2. Post chart/focus polish chart manifest
   - `artifacts/post_p2_chart_focus_probe_v2/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`
3. Final customer-facing acceptance target chart manifest
   - `artifacts/post_p2_customer_sanitize_001/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`

### Prior acceptance references consulted
- `docs/V2_P1_GOLDEN_SAMPLE_ACCEPTANCE_2026-04-25.md`
- `docs/V2_P2_CUSTOMER_GRADE_ACCEPTANCE_2026-04-25.md`
- `docs/POST_P2_EDITORIAL_001_PREMIUM_EDITORIAL_FINISH_2026-04-25.md`

## 2. Editorial / advisory quality findings

### 2.1 What clearly improved
Compared with the `POST-P1-CUSTOMER-REPORT-001` baseline, the current customer main is materially better in five visible ways:

1. **Top judgment is less flat and more advisory-framed**
   - Baseline wording was closer to a stitched summary:
     - `已基于盘前 high+reference 形成待开盘验证的主线候选`
   - Current wording adds a client-facing decision posture:
     - `现阶段更适合把交易与沟通重心放在……的验证质量上，而不是过早放大为无条件确认`
   - Acceptance view: this is a real upgrade from template summary toward advisory framing.

2. **Risk / next-step is more like a briefing than a raw bucket dump**
   - The old version mainly repeated raw status lines.
   - The newer version introduces explicit observation points such as:
     - `开盘后第一观察位`
     - `收盘后复核位`
     - `重点跟踪名单`
   - Acceptance view: clearly better, more operator-to-client translation.

3. **Section-level advisory language improved**
   - New `顾问提示` blocks create the intended “what should the client do with this section” feel.
   - The early / mid / late slot treatment is visibly more differentiated.
   - Acceptance view: good directional improvement and customer-facing intent is now obvious.

4. **The page now reads more like a client note than a raw engineering package**
   - Branding, attribution, disclaimer, and structured briefing blocks remain present.
   - The page no longer fails on the obvious “engineering artifact” bar.

5. **Customer sanitization removed several upstream/internal phrases**
   - Replaced or cleaned customer-facing occurrences of terms like:
     - `high+reference`
     - `same-day stable/final`
     - `close package`
   - Acceptance view: this reduces internal-contract leakage in the top-level customer narrative.

### 2.2 What still fails premium editorial acceptance
Despite the above gains, the current customer main still does **not** read consistently like a premium iFA advisory note for a high-net-worth / family-office audience.

#### A. Facts remain too raw and noisy in customer-facing sections
The strongest blocker is not the headline layer; it is the evidence/fact carry-through still visible in customer HTML.

Examples from the latest customer sample:
- `盘前市场侧输入覆盖：竞价样本 0 条，事件流 8 条，候选龙头 0 个，信号状态 0 条。`
- `盘中结构层覆盖：1m 样本 0 条，广度 0 条，热度 0 条，信号状态 0 条；最新 validation=unknown，emotion=unknown。`
- `隔夜/近期文本催化共 8 条，最新线索包括：...` followed by raw, noisy text fragments including investor-QA style strings.

Acceptance judgment:
- This is still closer to an internal evidence packet or analyst scratchpad than a premium customer brief.
- It is especially weak for a supposed premium customer because zero-count telemetry and raw text fragments dominate reading attention without enough curation.
- `validation=unknown` / `emotion=unknown` is internal-ish wording and should not survive into premium customer prose.

#### B. Top judgment is improved, but still mechanically repetitive
The current top judgment is better than before, but still not yet premium.

Why:
- It repeats the same underlying sentence multiple times across headline, section summary, advisor hint, and tracking bullets.
- The phrasing remains structurally templated rather than decisively synthesized.
- It still feels like “producer statement + wrapper sentence” rather than a true top-down client judgment.

Acceptance judgment:
- **Improved:** yes.
- **Less templated:** partially yes.
- **Premium-quality top judgment:** not yet.

#### C. Risk / next-step now has the right shape, but not yet enough investment-advisor polish
The structure is stronger, but the language still leans on quoted raw system-derived clauses, for example:
- `围绕“盘前 high layer 与 reference seed 已足以形成待开盘验证的主线候选，但仍不应视为已确认。”确认主线是否具备继续强化的交易条件。`
- `以“收盘口径已确认 市场表与同日文本事实已足以形成收盘 收盘确认依据，可以做晚报主线结论。”核对当日结论能否顺延到次日跟踪框架。`

Acceptance judgment:
- The block now looks like a briefing section.
- But the actual sentence quality still depends too heavily on raw upstream text that has been lightly wrapped, not fully editorialized.

#### D. Some awkward customer-visible phrasing remains
Examples in the latest sample:
- `盘前 盘前高频与参考信息`
- `收盘口径已确认 市场表`
- `收盘 收盘确认依据`
- double punctuation / duplicated sentence rhythm in some `顾问提示` lines

Acceptance judgment:
- These are not catastrophic leakage issues.
- But they are still below the expected standard for a premium advisory product.

## 3. Chart / focus quality findings

### 3.1 Chart quality — materially improved and acceptable for this slice
This lane improved the chart state in a meaningful, customer-visible way.

#### Baseline
From `post_p1_customer_report_001` chart manifest:
- `ready_chart_count = 1`
- `degrade_status = partial`
- missing:
  - `key_focus_window`
  - `key_focus_return_bar`

#### Current
From `post_p2_chart_focus_probe_v2` and `post_p2_customer_sanitize_001` chart manifests:
- `ready_chart_count = 2`
- `degrade_status = partial`
- ready:
  - `market_index_window`
  - `key_focus_window`
- still missing:
  - `key_focus_return_bar`
- customer-facing explanation improved to:
  - `观察池标的缺少足够的连续行情，暂时无法计算日度涨跌幅，保留清单与纳入理由供跟踪。`

Acceptance judgment:
- This portion **passes** for the intended scope.
- The chart pack is still partial, but it is now honest, more useful, and more customer-readable.
- The key acceptance test here was “partial improved or customer explanation improved enough”; current evidence satisfies that bar.

### 3.2 Focus / key-focus quality — improved, but not yet premium watchlist quality
The focus section is better than the baseline in two ways:
1. It now uses a more professional watchlist frame:
   - `Tier 1 / Key Focus`
   - `Tier 2 / Focus Watchlist`
2. It adds an intended rationale line:
   - `优先用于验证强度、节奏与是否具备继续跟踪价值`

However, it still falls short of a true premium advisory watchlist.

Why:
- The section is still dominated by raw tickers (`000001.SZ`, `000002.SZ`, etc.) with no company names, sector labels, strategy tags, or concise rationale per name.
- `Tier 2 / Focus Watchlist` currently renders `暂无 Focus Watchlist`, which weakens the professionalism of the module.
- `重点跟踪名单` in the risk/next-step block is still a bare ticker list rather than a curated watchlist sentence.

Acceptance judgment:
- **Improved:** yes.
- **Professional advisory watchlist quality:** only partial.
- Good enough to show progress; not good enough to close premium focus quality fully.

## 4. Leakage findings

### 4.1 Customer leakage recheck result
I rechecked the latest customer-facing sample against the required leakage patterns.

Patterns checked:
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
- prior upstream phrasing targets:
  - `high+reference`
  - `same-day stable/final`
  - `candidate_with_open_validation`
  - `watchlist_only`
  - `close package`
  - `final market packet ready`

### 4.2 Leakage verdict
- **Pass on classic engineering-field leakage.**
- **Pass on explicit FCJ leakage.**
- **Pass on the main targeted customer sanitization phrases.**

### 4.3 Important nuance: not a leakage failure, but still a customer-quality problem
The current sample still contains customer-visible raw/internal-ish phrasing such as:
- `validation=unknown`
- `emotion=unknown`
- zero-count telemetry lines
- raw investor-QA / text-fragment carry-through

Acceptance judgment:
- I do **not** classify these as hard leakage in the narrow contract sense.
- I **do** classify them as a premium editorial quality blocker.

## 5. Pass / fail against premium editorial + chart/focus criteria

### Criterion-by-criterion verdict
1. **Customer main reads more like a premium iFA advisory note**
   - **Fail**
   - Reason: headline/risk framing improved, but factual blocks remain too raw/noisy for premium advisory delivery.

2. **Top judgment is less templated**
   - **Pass (partial / milestone pass)**
   - Reason: clearly less flat than baseline, but still repetitive and not fully premium.

3. **Facts are less raw / noisy**
   - **Fail**
   - Reason: raw text fragments, zero-count telemetry, and internal-ish state labels remain visible in customer HTML.

4. **Risk / next-step reads more like advisor-quality briefing**
   - **Pass (partial / milestone pass)**
   - Reason: shape and intent are much stronger, but phrasing still leans too heavily on quoted raw system lines.

5. **Chart partial improved or customer-facing explanation improved enough**
   - **Pass**
   - Reason: readiness improved from `1/3` to `2/3`; remaining partial state is honestly and customer-readably explained.

6. **Focus / key-focus reads more like a professional advisory watchlist**
   - **Fail (close to partial pass, but not enough)**
   - Reason: tiering is better, but the module still reads like a ticker dump with minimal curation.

7. **Customer leakage recheck**
   - **Pass**
   - Reason: no blocking customer leakage found in the latest sample.

### Overall verdict
## FAIL for `ACCEPT-P3-001`

Reason:
- The delivered work **materially improves** the customer report and clearly advances chart/focus presentation.
- But the combined target was **premium editorial and chart/focus quality acceptance**.
- Current state still falls short on the premium editorial bar and on the “professional advisory watchlist” bar.
- This is an honest near-pass / fail-with-precise-residuals, not a rejection of the progress already landed.

## 6. Residual gaps and whether blocking

### Blocking residual gaps
1. **Raw/noisy fact carry-through in customer HTML**
   - Blocking: **yes**
   - Why: premium customer note cannot surface raw telemetry, `unknown` state labels, or uncured text-fragment dumps in this form.

2. **Customer-facing section evidence needs one more editorial compression layer**
   - Blocking: **yes**
   - Why: the current customer report still wraps upstream content rather than consistently transforming it into premium advisory prose.

3. **Focus/watchlist module needs richer professional packaging**
   - Blocking: **yes**
   - Why: tiering exists, but bare tickers + empty Tier 2 is not sufficient for a professional advisory watchlist closeout.

### Non-blocking residual gaps
1. **One chart remains partial (`key_focus_return_bar`)**
   - Blocking: **no**
   - Why: the current degrade explanation is acceptable and honest.

2. **Some awkward sanitized phrasing remains**
   - Blocking: **secondary / folded into editorial blocker**
   - Why: not a leakage failure, but should be cleaned as part of the next editorial pass.

## 7. Exact paths, tests / checks, commits

### Code / doc changes evaluated
- `src/ifa_data_platform/fsj/report_rendering.py`
- `tests/unit/test_fsj_report_rendering.py`
- `docs/POST_P2_EDITORIAL_001_PREMIUM_EDITORIAL_FINISH_2026-04-25.md`
- `docs/IFA_Execution_Progress_Monitor.md`

### Commits inspected
- `f8eb951` — `Polish customer advisory editorial finish`
- `3a7b938` — `Sanitize customer-facing upstream phrasing`
- `c67994d` — `Polish chart degrade messaging and focus watchlist`

### Checks run for this acceptance
1. Repo state / recent commit verification
   - `git status --short`
   - `git log -n 8 --oneline`
2. Renderer seam validation
   - `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_rendering.py`
   - result: `31 passed`
3. Compile seam validation
   - `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m py_compile src/ifa_data_platform/fsj/report_rendering.py`
4. Leakage / phrase recheck on sampled customer HTML
   - targeted `rg` over the four sampled HTML files for:
     - engineering leakage fields
     - FCJ
     - sanitized upstream phrases
5. Chart quality recheck
   - direct inspection of chart manifests listed above
6. Sample-to-sample editorial comparison
   - direct text extraction / comparison across:
     - baseline post-P1 sample
     - post editorial finish sample
     - post chart/focus sample
     - latest post sanitize sample

## Final acceptance conclusion
The current output is **better, safer, and more client-shaped** than the earlier accepted P2 milestone, and the chart/focus lane delivered meaningful value. But on an honest premium-quality bar, the customer report still exposes too much raw evidence texture and too little curated advisory synthesis. The right closure status for `ACCEPT-P3-001` is therefore:

- **overall: FAIL**
- **chart partial / customer explanation: PASS**
- **leakage: PASS**
- **premium editorial / professional watchlist finish: NOT YET ACCEPTED**
