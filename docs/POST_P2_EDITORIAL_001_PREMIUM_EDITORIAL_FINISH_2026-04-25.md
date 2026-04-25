# POST-P2-EDITORIAL-001 — Premium Editorial Finish and Advisory Language Upgrade

## 1. Current editorial surface audit

Bounded audit focused on the customer-facing MAIN report presentation seam in `src/ifa_data_platform/fsj/report_rendering.py`.

### Before this task
- Customer main already had brand / disclaimer / risk / next-step blocks, but the prose still read like a light wrapper around engineering payloads.
- Top judgment was structurally correct but often too literal: `headline + validate X` pattern, which still felt templated.
- Risk / next-step blocks were mostly raw signal carry-through rather than advisory-note language.
- Early / mid / late summary cards lacked a stronger “advisor interpretation” layer.
- Focus / Key Focus was leakage-clean, but still rendered mostly as raw symbol lists with limited business framing.
- Internal / review output surfaces were already correct and must not be disturbed.

### Specific editorial gaps observed
- Repetitive “当前/继续/观察” sentence skeletons.
- Weak distinction between:
  - pre-open candidate framing,
  - intraday adjustment framing,
  - close-package / next-day carry framing.
- Risk language lacked business-tone conversion (“what this means for decision pacing”).
- Summary cards lacked formal advisory-note texture.

## 2. Minimal implementation path

Kept scope intentionally narrow:
- **Do change** only customer presentation wording / structure in renderer helpers.
- **Do not change** collector/data paths, main producer contracts, internal/review renderer, or create new report family.
- Add a small customer-only advisory interpretation layer:
  - stronger top judgment phrasing,
  - slot-aware advisory notes for early/mid/late,
  - business-language risk block,
  - cleaner next-step wording,
  - focus rendering framed as tracked names/objects rather than bare skeletal lists.

## 3. Concrete files changed

### Data-platform
- `src/ifa_data_platform/fsj/report_rendering.py`
  - strengthened customer-only top judgment
  - added slot-aware advisory-note generation
  - upgraded risk / next-step business language
  - added advisory text to summary cards and section bodies
  - made focus bucket labels more advisory-facing while keeping leakage clean
- `src/ifa_data_platform/fsj/chart_pack.py`
  - trivial syntax repair (`return note` stray brace removal) required only to restore import/testability; no intended behavior change
- `tests/unit/test_fsj_report_rendering.py`
  - no test logic changes required; existing focused rendering suite remained green after patch
- `docs/POST_P2_EDITORIAL_001_PREMIUM_EDITORIAL_FINISH_2026-04-25.md`
  - task audit + delivery record
- `docs/IFA_Execution_Progress_Monitor.md`
  - updated lane/task completion state and evidence

## 4. Focused tests / validation

### Compile
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m py_compile src/ifa_data_platform/fsj/report_rendering.py src/ifa_data_platform/fsj/chart_pack.py`

### Focused unit test
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_rendering.py`
- Result: `29 passed`

### Fresh runnable generation
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/post_p2_editorial_001 --report-run-id-prefix post-p2-editorial-main-early`

### Leakage recheck on fresh customer HTML
- `rg -n "bundle_id|producer_version|slot_run_id|replay_id|report_links|file:///|artifact_id|renderer version|action=|confidence=|evidence=" artifacts/post_p2_editorial_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T040057Z.html -S`
- Result: no matches

## 5. Updated golden sample / runnable generation command

### Fresh sample
- `artifacts/post_p2_editorial_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T040057Z.html`

### Re-run command
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate \
  --subject main \
  --business-date 2026-04-23 \
  --slot early \
  --mode dry-run \
  --output-profile customer \
  --output-root artifacts/post_p2_editorial_001 \
  --report-run-id-prefix post-p2-editorial-main-early
```

## 6. Exact evidence paths

- Code:
  - `src/ifa_data_platform/fsj/report_rendering.py`
  - `src/ifa_data_platform/fsj/chart_pack.py`
- Focused test:
  - `tests/unit/test_fsj_report_rendering.py`
- Fresh sample:
  - `artifacts/post_p2_editorial_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T040057Z.html`
- Fresh summary:
  - `artifacts/post_p2_editorial_001/main_early_2026-04-23_dry_run/main_early_publish_summary.json`
- Delivery package index:
  - `artifacts/post_p2_editorial_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_delivery_2026-04-23_20260425T040057Z_0260425T040057Z-afd888fc/package_index.json`
- Task doc:
  - `docs/POST_P2_EDITORIAL_001_PREMIUM_EDITORIAL_FINISH_2026-04-25.md`

## 7. Residual gaps

This bounded task improved the **presentation layer**, not upstream deterministic / producer text.

Residual non-blocking gaps:
- Some raw upstream phrasing still appears in customer HTML, e.g.:
  - `high+reference`
  - `same-day stable/final`
- Focus objects are still shown as tickers because this task did not add a symbol-to-name enrichment layer.
- A few sentences remain verbose/repetitive when the upstream summary/judgment text is already long.
- Full premium editorial finish would benefit from a next step that upgrades producer-side canonical summary wording, not just renderer-side advisory framing.

## 8. Bounded acceptance verdict

**Met for bounded scope.**

Why:
- customer-facing main is more advisory-note-like
- top judgment is stronger and less skeletal
- risk / next-step language now reflects business interpretation rather than raw signal dump
- early / mid / late surfaces now have slot-aware advisory notes
- customer leakage remains clean
- internal / review surfaces were not changed

Not claimed:
- full producer-side editorial normalization
- ticker-to-name enrichment
- full elimination of raw contract-adjacent wording
