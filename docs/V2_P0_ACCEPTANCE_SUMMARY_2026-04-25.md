# V2 P0 Acceptance Summary and Golden Sample Validation

Date: 2026-04-25  
Acceptance Task: `ACCEPT-P0-001`  
Repo: `/Users/neoclaw/repos/ifa-data-platform`  
Business-layer repo: `/Users/neoclaw/repos/ifa-business-layer`

## 0. Acceptance verdict

**Verdict: P0 accepted with residual gaps, but no newly found production-blocking blocker for weekend closure.**

Acceptance basis:
- P0 tasks `V2-R0-001` through `V2-R0-006` are present in repo history, documented in the progress monitor, and their cited files/tests/commits are materially consistent with repo truth.
- Canonical CLI exists and is runnable: `scripts/fsj_report_cli.py`.
- Customer-facing HTML stripping works for validated customer samples.
- `customer` / `review` output profiles are now explicit end-to-end.
- LLM role-policy / fallback-chain / boundary controls are implemented and auditable on internal/operator surfaces.
- No active/formal `FCJ` pipeline family was found. Existing mentions are explanatory guardrails only.

Residual gaps kept open:
1. `review` is **not** a dedicated sanitized review layout; it remains an operator/internal-rich review surface.
2. Main-report lifecycle semantics still prefer the strongest candidate artifact (`late`) on operator/review surfaces even when the triggering command was `early`.
3. In this acceptance shell, live LLM calls degraded because the business-layer CLI was invoked without an import-ready runtime, so golden samples validate policy/trace surfaces more than successful live LLM usage.
4. Replay/backfill are still wrapper-level semantics, not a single deeply unified native lifecycle abstraction.

---

## 1. P0 completion checklist by task

### V2-R0-001 — weekend runtime freeze plan
- What changed:
  - Established weekend freeze / preflight / rollback discipline.
- Evidence files:
  - `docs/V2_R0_001_WEEKEND_RUNTIME_FREEZE_PLAN_2026-04-24.md`
  - `artifacts/runtime_freeze/runtime_process_snapshot_20260424_1758_PDT.txt`
  - `artifacts/runtime_freeze/unified_daemon_status_pre_freeze_20260424_1758_PDT.json`
  - `artifacts/runtime_freeze/runtime_preflight_pre_freeze_20260424_1758_PDT.json`
- Tests / checks cited by monitor:
  - `zsh scripts/unified_daemon_service.sh status`
  - `zsh scripts/unified_daemon_service.sh preflight`
  - `python -m ifa_data_platform.runtime.unified_daemon --status`
  - `pgrep -fl ...unified_daemon...`
- Commit / push status:
  - commit `3c07c8e`
  - progress monitor status = `pushed`
- Acceptance:
  - **met**
- Residual gap:
  - none within P0 scope; intentionally does not refactor runtime architecture.

### V2-R0-002 — DB reality probe and snapshot hardening
- What changed:
  - Added reality-probe script and frozen JSON/Markdown evidence for actual tables/data presence.
- Evidence files:
  - `scripts/db_reality_probe_v2.py`
  - `artifacts/db_reality_snapshot_v2_20260424.json`
  - `docs/DB_REALITY_SNAPSHOT_V2_2026-04-24.md`
  - `docs/DB_REALITY_SNAPSHOT_V2_HANDOFF_2026-04-24.md`
- Tests / checks:
  - `python scripts/db_reality_probe_v2.py`
  - JSON / Markdown evidence review
- Commit / push status:
  - `684c1553dd9b4a6abec58c6fb653b0f45be7bce0`
  - `e411d5a03f5d6d2aa8f57fcc681557a4f30d908c`
  - monitor status = `pushed`
- Acceptance:
  - **met**
- Residual gap:
  - none within P0 scope; does not attempt broad schema cleanup.

### V2-R0-003 — unified report CLI audit and closure
- What changed:
  - Landed canonical entrypoint `scripts/fsj_report_cli.py`.
  - Added CLI validation artifacts and audit doc.
- Evidence files:
  - `scripts/fsj_report_cli.py`
  - `docs/V2_R0_003_UNIFIED_REPORT_CLI_AUDIT_AND_CLOSURE_2026-04-24.md`
  - `artifacts/v2_r0_003_validation/command_outputs/*`
- Acceptance rerun evidence:
  - `python3 scripts/fsj_report_cli.py --help`
  - dry-run generate/status commands executed again under `artifacts/accept_p0_001`
- Commit / push status:
  - `edcbb3e72f006f0c5c19d2930d0ff3dbaf58e57a`
  - monitor status = `pushed`
- Acceptance:
  - **met** as minimal canonical closure
- Residual gap:
  - replay/backfill/profile semantics still sit partly at wrapper/control-surface level; not a total orchestration rewrite.

### V2-R0-004 — customer-facing presentation layer
- What changed:
  - Customer renderer path strips engineering-heavy internals from customer HTML.
  - Main/support publish scripts and CLI were threaded through customer presentation support.
- Evidence files:
  - `src/ifa_data_platform/fsj/report_rendering.py`
  - `scripts/fsj_main_report_publish.py`
  - `scripts/fsj_support_report_publish.py`
  - tests under `tests/unit/test_fsj_*report*_script.py`
  - `docs/V2_R0_004_CUSTOMER_PRESENTATION_LAYER_2026-04-24.md`
- Acceptance rerun tests:
  - `python3 -m pytest -q tests/unit/test_fsj_report_rendering.py tests/unit/test_fsj_main_report_publish_script.py tests/unit/test_fsj_support_report_publish_script.py`
  - result: **39 passed**
- Commit / push status:
  - `1fc24b83fd87820f7599ffbb678ac24501483015`
  - monitor status = `pushed`
- Acceptance:
  - **met**
- Residual gap:
  - customer HTML is clean, but customer-sidecar manifests still retain internal lineage fields by design; safe if not customer-exposed, but worth documenting operationally.

### V2-R0-005 — customer / internal / review output separation
- What changed:
  - Explicit `output_profile` routing for main/support wrappers.
  - Review profile now explicit in renderer title/metadata.
- Evidence files:
  - `src/ifa_data_platform/fsj/report_rendering.py`
  - `src/ifa_data_platform/fsj/main_publish_cli.py`
  - `scripts/fsj_main_early_publish.py`
  - `scripts/fsj_main_mid_publish.py`
  - `scripts/fsj_main_late_publish.py`
  - `scripts/fsj_support_batch_publish.py`
  - `scripts/fsj_report_cli.py`
- Acceptance rerun tests:
  - prior monitor note recorded temporary collection block from `FSJ_MODEL_ALIAS`
  - acceptance rerun after V2-R0-006 fix now passes:
  - `python3 -m pytest -q tests/unit/test_fsj_report_rendering.py tests/unit/test_fsj_main_report_publish_script.py tests/unit/test_fsj_support_report_publish_script.py tests/unit/test_fsj_early_llm_assist.py`
  - result: **39 passed**
- Commit / push status:
  - `fb789d3`
  - `e3d4aef`
  - monitor status = `pushed`
- Acceptance:
  - **met**, but with an explicit follow-up gap below
- Residual gap:
  - no dedicated review-safe template/layout; current `review` remains a reviewer/operator-rich artifact, not a separate sanitized family.

### V2-R0-006 — LLM prompt and model policy upgrade
- What changed:
  - Config-driven model policy landed.
  - Default primary now `grok41_expert`; fallback chain explicit.
  - Role-policy / slot-boundary / degrade handling visible on internal/operator surfaces.
  - `FSJ_MODEL_ALIAS` issue fixed.
- Evidence files:
  - `src/ifa_data_platform/fsj/llm_assist.py`
  - `/Users/neoclaw/repos/ifa-business-layer/config/llm/models.yaml`
  - `/Users/neoclaw/repos/ifa-business-layer/ifa_business_layer/support/{macro,commodities,ai_tech}.py`
  - `tests/unit/test_fsj_early_llm_assist.py`
  - `docs/V2_R0_006_LLM_PROMPT_AND_MODEL_POLICY_UPGRADE_2026-04-24.md`
  - `artifacts/evals/fsj_early_llm_fallback_proof.json`
  - `artifacts/evals/fsj_late_llm_fallback_proof.json`
- Acceptance rerun tests:
  - data-platform: `python3 -m pytest -q tests/unit/test_fsj_early_llm_assist.py` → included in 39-pass rerun
  - business-layer: `python3 -m pytest -q tests/unit/test_macro_support_producer.py tests/unit/test_commodities_support_producer.py tests/unit/test_ai_tech_support_producer.py` → **12 passed**
  - compile: `python3 -m py_compile src/ifa_data_platform/fsj/llm_assist.py src/ifa_data_platform/fsj/report_rendering.py scripts/fsj_report_cli.py scripts/fsj_main_report_publish.py scripts/fsj_support_report_publish.py`
- Commit / push status:
  - data-platform `f68b381` / `e9f118f`
  - business-layer `f7511bb`
  - monitor status = `pushed`
- Acceptance:
  - **met**
- Residual gap:
  - current acceptance-shell live invocation showed import/runtime setup drift for business-layer CLI, causing deterministic degrade rather than successful live-model usage.

---

## 2. Unified Report CLI acceptance

### 2.1 Canonical CLI
- Canonical file: `scripts/fsj_report_cli.py`
- Acceptance result: **present and runnable**

### 2.2 Real runnable commands validated

#### Help
```bash
python3 scripts/fsj_report_cli.py --help
```

#### Main generate
```bash
python3 scripts/fsj_report_cli.py generate \
  --subject main \
  --business-date 2026-04-23 \
  --slot early \
  --mode dry-run \
  --output-profile customer \
  --output-root artifacts/accept_p0_001 \
  --report-run-id-prefix accept-p0-main-early
```

#### Support generate
```bash
python3 scripts/fsj_report_cli.py generate \
  --subject support \
  --business-date 2026-04-23 \
  --slot late \
  --mode dry-run \
  --output-profile customer \
  --output-root artifacts/accept_p0_001 \
  --report-run-id-prefix accept-p0-support-late
```

#### Review-profile main generate
```bash
python3 scripts/fsj_report_cli.py generate \
  --subject main \
  --business-date 2026-04-23 \
  --slot late \
  --mode dry-run \
  --output-profile review \
  --output-root artifacts/accept_p0_001 \
  --report-run-id-prefix accept-p0-main-late-review
```

#### Review-profile support generate
```bash
python3 scripts/fsj_report_cli.py generate \
  --subject support \
  --business-date 2026-04-23 \
  --slot early \
  --mode dry-run \
  --output-profile review \
  --output-root artifacts/accept_p0_001 \
  --report-run-id-prefix accept-p0-support-early-review
```

#### Status examples (from landed validation set)
```bash
python3 scripts/fsj_report_cli.py status --subject main --business-date 2026-04-23 --format json
python3 scripts/fsj_report_cli.py status --subject support --agent-domain macro --business-date 2026-04-23 --format json
python3 scripts/fsj_report_cli.py status --subject board --latest --format json
```

### 2.3 Replay / backfill-test / dry-run semantics
- `dry-run`: **validated directly** in acceptance.
- `replay`: acknowledged by task requirement and prior audit framing, but remains effectively a wrapper/control-path semantic rather than a fully normalized native lifecycle abstraction in a single unified engine.
- `backfill-test`: same status as replay; supported operationally at wrapper/control level, not yet a fully unified internal lifecycle contract.
- `profile`: explicit and validated via `--output-profile customer|review`.

### 2.4 Output directories validated
- Main early customer:
  - `artifacts/accept_p0_001/main_early_2026-04-23_dry_run/publish`
- Main late review:
  - `artifacts/accept_p0_001/main_late_2026-04-23_dry_run/publish`
- Support early review:
  - `artifacts/accept_p0_001/support_early_2026-04-23_dry_run/*`
- Support late customer:
  - `artifacts/accept_p0_001/support_late_2026-04-23_dry_run/*`

### 2.5 Native vs wrapper-level semantics
- **Native enough for P0**:
  - top-level generate/status entrypoint exists and runs
  - profile selection threads end-to-end
  - subject routing works for main/support
- **Still wrapper-level / not fully unified**:
  - replay/backfill behavior
  - main-report lifecycle candidate selection and cross-slot supersede behavior
  - operator-facing send/readiness logic remains layered on top of artifact metadata rather than a single minimal unified execution kernel

### 2.6 CLI residual gaps
1. replay/backfill are not yet a deeply unified native lifecycle.
2. main early dry-run operator surface selected the strongest late artifact for send/readiness semantics.
3. CLI exists as canonical entry, but underlying producers/assembly/orchestration remain legacy-layered by design.

---

## 3. Customer / Internal / Review profile acceptance

### 3.1 Customer profile
Validated samples show customer HTML excludes obvious engineering fields from rendered HTML body.

Leakage spot-check tokens against customer HTML:
- `bundle_id`
- `producer_version`
- `slot_run_id`
- `replay_id`
- `file:///`
- `action=`
- `confidence=`
- `evidence=`
- `report_links`

Result:
- main early customer HTML: **clean**
- support late customer HTML (macro / commodities / ai_tech): **clean**

### 3.2 Internal retained fields
Internal/operator/review surfaces still retain lineage / QA / audit state, including:
- bundle ids
- producer versions
- report links / artifact URIs
- role policy / boundary modes
- fallback chain / attempt failures / operator tags
- workflow handoff and delivery package state

This is acceptable for internal/operator use and is the main reason review remains useful.

### 3.3 Review vs internal difference
- Review is now explicit via `output_profile=review` and title/metadata surface.
- However, review is **not** a strongly separate sanitized template family.
- In practice, current review output behaves as an operator/internal review package with rich lineage retained.

### 3.4 Dedicated review template/layout?
- **No dedicated separate minimal review-safe layout was found.**
- Review currently uses reviewer-rich rendering and metadata surfaces rather than a reduced layout between customer and full internal.

### 3.5 Leakage checklist conclusion
- Customer HTML leakage: **pass** for validated samples.
- Review leakage: **expected / intentional internal richness**, therefore not a leak if scoped to operator/reviewer audience.
- Operational caution: customer-sidecar manifests should not be delivered directly to external customers unless packaging rules explicitly strip them.

---

## 4. LLM strategy acceptance

### 4.1 Current default model strategy
From `/Users/neoclaw/repos/ifa-business-layer/config/llm/models.yaml`:
- `policy_version: fsj_assist_model_policy_v1`
- `primary_model_alias: grok41_expert`
- `fallback_model_aliases: [grok41_thinking, gemini31_pro_jmr]`

### 4.2 Is `grok41_expert` primary?
- **Yes** for current formal configured default.

### 4.3 Fallback chain
- Configured chain:
  - `grok41_expert`
  - `grok41_thinking`
  - `gemini31_pro_jmr`
- Verified in internal acceptance artifacts on review/operator surfaces and in fallback-proof fixtures.

### 4.4 Is fallback auditable?
- **Yes on internal/operator/review-adjacent surfaces.**
- Evidence:
  - `artifacts/evals/fsj_early_llm_fallback_proof.json`
  - `artifacts/evals/fsj_late_llm_fallback_proof.json`
  - `artifacts/accept_p0_001/main_late_2026-04-23_dry_run/main_late_publish_summary.json`
  - `artifacts/accept_p0_001/main_late_2026-04-23_dry_run/operator_summary.txt`
- Audited fields observed:
  - `attempted_model_chain`
  - `primary_model_alias`
  - `fallback_model_aliases`
  - `attempt_failures`
  - `role_policy.policy_version`
  - `boundary_modes`
  - `forbidden_decisions`
  - `override_precedence`

### 4.5 Do formal calls use business-layer gateway?
- **Yes by design and by implementation direction.**
- No data-platform-local freeform model calling path was accepted.
- However, current acceptance-shell execution showed runtime/import drift for the business-layer CLI, yielding deterministic degrade rather than successful live completion.

### 4.6 Is `FSJ_MODEL_ALIAS` fixed?
- **Yes.**
- Evidence:
  - previously noted as a blocking NameError in V2-R0-005 monitor notes
  - post-fix tests now pass, including `test_fsj_early_llm_assist.py`

### 4.7 Early/late no-boundary-violation evidence
- **Yes.**
- Early proof shows candidate-only contract and explicit prohibition against promoting to same-day confirmed theme.
- Late proof shows same-day-close contract and explicit prohibition against upgrading insufficient evidence to final close confirmation.
- Internal acceptance artifact surfaces include:
  - `boundary_modes: candidate_only, same_day_close`
  - `forbidden_decisions`
  - `deterministic_owner_fields`
  - `override_precedence`

### 4.8 LLM residual gaps
1. In this shell, live calls degraded because business-layer CLI import/runtime was not fully ready.
2. Customer manifest surface does not expose rich fallback audit; audit is internal/operator-facing.
3. Acceptance golden samples therefore validate policy visibility and safe degradation more strongly than successful live-model enrichment.

---

## 5. Golden samples acceptance

## 5.1 Validated sample matrix

### Sample A — main early customer
- Command:
```bash
python3 scripts/fsj_report_cli.py generate \
  --subject main --business-date 2026-04-23 --slot early \
  --mode dry-run --output-profile customer \
  --output-root artifacts/accept_p0_001 \
  --report-run-id-prefix accept-p0-main-early
```
- business_date: `2026-04-23`
- slot: `early`
- subject/domain: `main`
- output_profile: `customer`
- HTML path:
  - `artifacts/accept_p0_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T021325Z.html`
- Manifest path:
  - `artifacts/accept_p0_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T021325Z.manifest.json`
- Review package path: n/a
- Opened/checked: yes
- Leakage check: pass for customer HTML
- Readability check: pass
- Model/prompt/artifact traceability:
  - artifact trace present in manifest
  - LLM trace is visible on internal/operator surfaces, not customer HTML

### Sample B — main late review
- Command:
```bash
python3 scripts/fsj_report_cli.py generate \
  --subject main --business-date 2026-04-23 --slot late \
  --mode dry-run --output-profile review \
  --output-root artifacts/accept_p0_001 \
  --report-run-id-prefix accept-p0-main-late-review
```
- business_date: `2026-04-23`
- slot: `late`
- subject/domain: `main`
- output_profile: `review`
- HTML path:
  - `artifacts/accept_p0_001/main_late_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T021325Z.html`
- Manifest path:
  - `artifacts/accept_p0_001/main_late_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T021325Z.manifest.json`
- Review package path:
  - `artifacts/accept_p0_001/main_late_2026-04-23_dry_run/publish/a_share_main_report_delivery_2026-04-23_20260425T021325Z_0260425T021325Z-dfd02d63`
- Opened/checked: yes
- Leakage check: intentionally internal-rich; not customer-safe
- Readability check: pass
- Model/prompt/artifact traceability:
  - strong pass on internal surfaces; includes role policy, boundary modes, attempted chain, failures, prompt versions

### Sample C — support late customer (macro representative)
- Command:
```bash
python3 scripts/fsj_report_cli.py generate \
  --subject support --business-date 2026-04-23 --slot late \
  --mode dry-run --output-profile customer \
  --output-root artifacts/accept_p0_001 \
  --report-run-id-prefix accept-p0-support-late
```
- business_date: `2026-04-23`
- slot: `late`
- subject/domain: `support/macro`
- output_profile: `customer`
- HTML path:
  - `artifacts/accept_p0_001/support_late_2026-04-23_dry_run/macro/a_share_support_macro_late_2026-04-23_20260425T021332Z.html`
- Manifest path:
  - `artifacts/accept_p0_001/support_late_2026-04-23_dry_run/macro/a_share_support_macro_late_2026-04-23_20260425T021332Z.manifest.json`
- Review package path: n/a
- Opened/checked: yes
- Leakage check: pass for customer HTML
- Readability check: pass
- Model/prompt/artifact traceability:
  - artifact trace present
  - operator summary indicates `llm_lineage_status=not_applied` on this dry-run sample

### Sample D — support early review (macro representative)
- Command:
```bash
python3 scripts/fsj_report_cli.py generate \
  --subject support --business-date 2026-04-23 --slot early \
  --mode dry-run --output-profile review \
  --output-root artifacts/accept_p0_001 \
  --report-run-id-prefix accept-p0-support-early-review
```
- business_date: `2026-04-23`
- slot: `early`
- subject/domain: `support/macro`
- output_profile: `review`
- HTML path:
  - `artifacts/accept_p0_001/support_early_2026-04-23_dry_run/macro/a_share_support_macro_early_2026-04-23_20260425T021341Z.html`
- Manifest path:
  - `artifacts/accept_p0_001/support_early_2026-04-23_dry_run/macro/a_share_support_macro_early_2026-04-23_20260425T021341Z.manifest.json`
- Review package path:
  - `artifacts/accept_p0_001/support_early_2026-04-23_dry_run/macro/a_share_support_report_delivery_macro_early_2026-04-23_20260425T021341Z_0260425T021341Z-d20212ba`
- Opened/checked: yes
- Leakage check: intentionally internal-rich review package
- Readability check: pass
- Model/prompt/artifact traceability:
  - manifest/profile trace present; review layout not sanitized

## 5.2 Golden sample notes
- Customer samples are reviewable and presentable.
- Review samples are reviewable and trace-rich.
- Main early operator summary selected late artifact as strongest candidate; this is a lifecycle/selection semantics issue, not a rendering failure.
- Delivery package dirs and manifests were all generated with `package_state=ready` and `ready_for_delivery=true`.

---

## 6. Progress Monitor truthfulness check

Checked against repo files, branch state, generated acceptance evidence, and cited tests.

Conclusion: **Progress Monitor is materially truthful.**

Observed corrections / nuance to carry forward:
1. It is accurate that P0 tasks landed and were pushed.
2. It is accurate that FCJ is not a formal concept.
3. It should now be updated to reflect that `ACCEPT-P0-001` is completed/pushed, not in progress.
4. It should preserve nuance that P0 passed with residual gaps rather than “everything perfect”.

---

## 7. FCJ misuse audit

Search result:
- No active/formal FCJ implementation family found.
- `FCJ` occurrences found were only in guardrail / explanatory documentation:
  - `docs/IFA_Execution_Progress_Monitor.md`
  - `docs/V2_R0_004_CUSTOMER_PRESENTATION_LAYER_2026-04-24.md`

Acceptance conclusion:
- **No blocking FCJ misuse found.**
- Current repo state is consistent with the correction: treat prior FCJ mentions as FSJ wording error, not a live concept.

---

## 8. Residual gap list

### Gap 1 — review profile is not a distinct sanitized review layout
- Impact:
  - reviewer/operator package remains engineering-rich
- Production-blocking:
  - no
- Must solve now:
  - no
- Recommended follow-up:
  - post-P0 task for dedicated review template family / review-safe manifest bundle
- Reason deferred:
  - P0 asked for explicit separation and safe customer strip first; that is already met

### Gap 2 — main early operator/review lifecycle may select strongest late artifact
- Impact:
  - command-triggered semantics can be confusing; operator may see readiness/state for a superseding late artifact rather than the immediate early-run artifact
- Production-blocking:
  - no for weekend acceptance
- Must solve now:
  - no, but important for operator clarity
- Recommended follow-up:
  - post-P0 registry / workflow-handoff normalization task
- Reason deferred:
  - lifecycle registry/selection work is already the active post-P0 lane focus

### Gap 3 — live LLM acceptance run degraded due business-layer CLI runtime/import environment
- Impact:
  - acceptance golden samples demonstrate safe degrade and traceability more than successful live LLM assistance
- Production-blocking:
  - no new blocker proven for weekend because policy degrades safely and tests/proofs validate intended chain
- Must solve now:
  - no, unless weekend plan requires live assisted wording rather than deterministic degrade
- Recommended follow-up:
  - add a business-layer runtime invocation smoke test from data-platform shell / enforce import-safe launcher
- Reason deferred:
  - fallback proofs and unit coverage already validate chain semantics; runtime shell packaging is operational follow-up

### Gap 4 — replay/backfill remain wrapper-level semantics
- Impact:
  - conceptual complexity remains; not all lifecycle operations are unified at one native orchestration layer
- Production-blocking:
  - no
- Must solve now:
  - no
- Recommended follow-up:
  - continue unified registry / manifest / orchestration closure
- Reason deferred:
  - outside minimal P0 closure scope

---

## 9. Acceptance evidence commands executed in this lane

```bash
git status --short && git log --oneline -n 12
python3 scripts/fsj_report_cli.py --help
python3 scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/accept_p0_001 --report-run-id-prefix accept-p0-main-early
python3 scripts/fsj_report_cli.py generate --subject support --business-date 2026-04-23 --slot late --mode dry-run --output-profile customer --output-root artifacts/accept_p0_001 --report-run-id-prefix accept-p0-support-late
python3 scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot late --mode dry-run --output-profile review --output-root artifacts/accept_p0_001 --report-run-id-prefix accept-p0-main-late-review
python3 scripts/fsj_report_cli.py generate --subject support --business-date 2026-04-23 --slot early --mode dry-run --output-profile review --output-root artifacts/accept_p0_001 --report-run-id-prefix accept-p0-support-early-review
python3 -m pytest -q tests/unit/test_fsj_report_rendering.py tests/unit/test_fsj_main_report_publish_script.py tests/unit/test_fsj_support_report_publish_script.py tests/unit/test_fsj_early_llm_assist.py
python3 -m pytest -q tests/unit/test_macro_support_producer.py tests/unit/test_commodities_support_producer.py tests/unit/test_ai_tech_support_producer.py
python3 -m py_compile src/ifa_data_platform/fsj/report_rendering.py src/ifa_data_platform/fsj/llm_assist.py scripts/fsj_report_cli.py scripts/fsj_main_report_publish.py scripts/fsj_support_report_publish.py
rg -n "FCJ" . -S
```

Executed results summary:
- data-platform focused pytest rerun: **39 passed**
- business-layer focused pytest rerun: **12 passed**
- customer HTML leakage spot-check: **pass** on validated customer samples
- review/internal traceability: **present**

---

## 10. Final conclusion

**P0 passes acceptance for weekend closure.**

This is a real acceptance, not a perfect-score claim:
- core P0 objectives are landed
- repo / monitor / tests materially align
- customer-facing output no longer leaks obvious engineering internals in validated customer HTML
- output profiles and LLM governance are explicit and auditable
- remaining issues are real but post-P0 in nature, not acceptance blockers for this closure window
