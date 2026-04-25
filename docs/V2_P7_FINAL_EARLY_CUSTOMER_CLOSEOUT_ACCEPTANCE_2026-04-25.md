# V2 P7 Final Early Customer Closeout Acceptance — 2026-04-25

## Scope

Bounded closeout acceptance for the EARLY customer main report only, focused on four points:

1. early slot-specific labels are clean and early-only
2. core judgment is more specific / honest
3. watchlist rationale is not mostly identical
4. chart wording is customer-readable and raw internal chart-degrade strings are absent
5. customer leakage remains clean

## Fresh Sample

- HTML sample:
  - `artifacts/post_p7_final_early_customer_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T112055Z.html`

## Commands Run

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_rendering.py tests/unit/test_fsj_main_report_publish_script.py
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_rendering.py -k 'slot_requests or focus_evidence or customer_profile_surfaces_chart_assets_without_internal_ids or polishes_section_level_contract_shaped_prose or emits_customer_profile_without_engineering_metadata_in_html'
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/post_p7_final_early_customer_001 --report-run-id-prefix post-p7-final-early-customer
rg -n "bundle_id|producer_version|slot_run_id|replay_id|report_links|file:///|artifact_id|renderer version|action=|confidence=|evidence=|chart_degrade_status=|ready_chart_count=|insufficient focus bars" artifacts/post_p7_final_early_customer_001/main_early_2026-04-23_dry_run/publish/*.html -S
```

## Acceptance Findings

### 1) Early slot-specific labeling cleanup

Pass.

Observed in fresh sample:
- `iFA A股盘前策略简报`
- `版本定位：早报 / 盘前客户主报告`
- `盘前重点解读`
- `开盘前关注`

Not observed in customer HTML:
- `早报 / 中报 / 晚报客户主报告`
- `早报 / 中报 / 晚报分时段解读`

### 2) Core judgment specificity / honesty

Pass.

Observed in fresh sample:
- `当前尚未形成单一强主线，盘前更适合围绕 ... 做开盘验证，再决定是否提升判断强度。`

Assessment:
- no unsupported single-mainline claim was forced into the early customer report
- wording now matches the available evidence posture for pre-open output

### 3) Watchlist rationale differentiation

Pass.

Observed differentiation in the fresh sample:
- `万科Ａ（000002.SZ）` uses market+text style wording
- `*ST国华（000004.SZ）` uses text-led / 基础观察项 wording
- `深振业Ａ（000006.SZ）` uses sector-tag / 待提升优先级 wording
- `全新好（000007.SZ）` uses market+text style wording
- `神州高铁（000008.SZ）` and `中国宝安（000009.SZ）` no longer all collapse to the same sentence family as地产/ST/区域地产

Residual note:
- some symbols still share the same fallback family when evidence depth is genuinely the same; this is acceptable for this bounded closeout because the report is no longer mostly identical across heterogeneous names and thin-evidence cases are stated as observation / validation items rather than fake theses.

### 4) Chart customer wording cleanup

Pass.

Observed in fresh sample:
- `部分图表因连续行情样本不足暂不展示涨跌幅对比，本期保留指数与 Key Focus 窗口图作为主要参考。`

Not observed in customer HTML:
- `chart_degrade_status=partial`
- `ready_chart_count=2/3`
- `insufficient focus bars`

Assessment:
- customer wording is readable and natural
- raw internal chart telemetry remains internal/review-only

### 5) Leakage check

Pass.

Leakage grep over the generated customer HTML returned no matches for:
- internal bundle/runtime identifiers
- internal artifact/report link fields
- raw chart-degrade telemetry strings

## Result

P7 bounded early-customer closeout acceptance passes for the requested four fixes.
