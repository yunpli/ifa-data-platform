# POST-P5-SECTION-PROSE-001 — Final Section-Level Customer Prose Polish

- Task ID: `POST-P5-SECTION-PROSE-001`
- Date: `2026-04-25`
- Owner: `Developer (direct exec)`
- Scope: `customer profile only`
- Status: `completed`

## Goal

Only remove the last residual blocker from `ACCEPT-P5-001`: section/body-level contract-shaped customer prose.

Kept unchanged by design:
- watchlist naming
- chart package behavior
- LLM gateway
- collector path
- internal/review contract-visible surfaces
- broader architecture

## What changed

Files changed:
- `src/ifa_data_platform/fsj/report_rendering.py`
- `tests/unit/test_fsj_report_rendering.py`

Bounded renderer-seam changes only:
1. Added customer-only cleanup for duplicated section labels such as:
   - `盘中 盘中结构信号` → natural customer wording
   - `收盘 收盘确认依据/材料` → natural customer wording
2. Added direct customer-only rewrites for section/body phrases that still read like contract/evidence packets.
3. Added customer-only rewrite for late close-coverage telemetry into advisory prose.
4. Kept review/internal output untouched.
5. Added focused regression test covering section/body contract-shaped phrasing cleanup while preserving raw wording in review profile.

## Focused validation

### Tests
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_rendering.py`
- Result: `35 passed`

### Fresh customer sample
- Command:
  - `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/post_p5_section_prose_001 --report-run-id-prefix post-p5-section-prose-main-early`
- Fresh HTML:
  - `artifacts/post_p5_section_prose_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T064752Z.html`
- Fresh chart manifest:
  - `artifacts/post_p5_section_prose_001/main_early_2026-04-23_dry_run/publish/charts/chart_manifest.json`

### Spot-check result
The fresh customer sample no longer shows the prior residual blockers:
- no `盘中 盘中结构信号`
- no `收盘 收盘确认依据`
- no `收盘 收盘确认材料`
- no `收盘依据已完整 市场表与同日文本事实已足以形成收盘 ...`

Representative new customer-facing prose now reads like advisory copy:
- `盘前线索与观察名单已经给出初步方向，但仍要等开盘后的量价与承接进一步确认。`
- `午后继续观察盘中结构是否修复，并确认是否出现强化、扩散或分歧。`
- `收盘阶段的核心市场与文本证据已经基本到齐，足以支撑晚报对当日主线作出复盘判断。`
- `晚报结论应以当日收盘后的完整证据为基础；盘中过程信息仅用于解释演化，前一交易日内容仅作历史对照。`

## Delivery note

This task intentionally stops at the renderer seam and hands off to `ACCEPT-P6-001` for final bounded editorial acceptance.
