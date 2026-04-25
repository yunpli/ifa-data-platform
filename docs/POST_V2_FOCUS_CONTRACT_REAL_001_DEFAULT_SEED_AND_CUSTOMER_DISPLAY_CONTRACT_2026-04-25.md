# POST-V2-FOCUS-CONTRACT-REAL-001 — Default Seed / Collection Scope / Customer Display Contract

- Date: 2026-04-25
- Repo: `/Users/neoclaw/repos/ifa-data-platform`
- Scope: no collector changes, no schema changes, minimal code/doc fix only

## 1. Contract clarification

Current system truth must be separated into distinct layers:

1. `default/default`
   - current live owner scope used by the business-layer canonical seed
   - this is the current source of seeded `focus` / `key_focus` lists consumed by A-share main reporting

2. `system/default`
   - reserved/system semantic scope name for infrastructure-owned defaults
   - **not** currently the live DB owner pair for the A-share main path
   - retained in contract language so downstream code/docs do not blur `default/default` and hypothetical system-owned defaults

3. `archive_targets`
   - persistence / retention / collection-target scope
   - not a customer-facing focus truth source

4. `focus`
   - product-layer watchlist scope
   - broader than top-priority symbols

5. `key_focus`
   - product-layer higher-priority watchlist scope
   - still product/internal watchlist truth, not automatically customer-display truth

6. product-facing display list
   - report-consumable projection of product watchlists
   - may use `focus` / `key_focus`, but still requires explicit display semantics

7. customer-facing display list
   - what the client actually sees as `核心关注` / `关注`
   - must not silently upgrade the canonical default seed into formal client focus truth

## 2. Interpretation of the current `000001.SZ` onward sequence

The current stock sequence beginning with `000001.SZ` is treated as:

- **default seed**: yes
- **development/test seed**: no, not primarily; it is a real business-layer canonical default seed
- **collection scope**: yes, it functions as baseline operational coverage / observation scope
- **formal customer list**: no

So the sequence is a canonical default observation pool / coverage seed, not a formal client-specific focus pool.

## 3. Customer report contract

Customer-facing reports now follow this honesty rule:

- keep official CN product labels as `核心关注` / `关注`
- but when the only available upstream scope is the canonical default seed and no formal customer focus list exists:
  - do **not** present it as formal client focus truth
  - explicitly label the surface as a **default observation-pool sample / internal observation-pool summary**
  - leave the same seam reusable for support-report customer surfaces later

## 4. Minimal implementation landed

Producer (`early_main_producer.py`) now emits explicit focus-scope contract metadata:

- `default_scope = default/default`
- `system_scope = system/default`
- `archive_target_scope = archive_targets`
- `product_focus_scope = [focus, key_focus]`
- `customer_display_scope = default_observation_pool_sample`
- `formal_customer_list_present = false`
- `formal_customer_focus_truth = false`
- explicit interpretation for the current `000001.SZ` onward seed

Renderer (`report_rendering.py`) now:

- consumes this contract metadata
- preserves customer-visible labels `核心关注` / `关注`
- rewrites the explanation block so default-seed-only output is disclosed as a default observation-pool sample rather than a formal customer focus pool

## 5. Fresh validation sample

Generated customer dry-run sample:

- `artifacts/post_v2_focus_contract_real_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T124218Z.html`

Generated via:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate \
  --subject main \
  --business-date 2026-04-23 \
  --slot early \
  --mode dry-run \
  --output-profile customer \
  --output-root artifacts/post_v2_focus_contract_real_001 \
  --report-run-id-prefix post-v2-focus-contract-real-001
```

## 6. Focused tests

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q \
  tests/unit/test_fsj_main_early_producer.py \
  tests/unit/test_fsj_report_rendering.py
```

Result: `47 passed`
