# FSJ P0-4 Rerunnable Acceptance Recipe — 2026-04-23

## Scope

This is the thinnest honest **rerunnable command-based acceptance recipe** above:
- `docs/FSJ_SLA_PROOF_PACKAGE_2026-04-23.md`
- `docs/FSJ_P0_4_ACCEPTANCE_LEDGER_2026-04-23.md`
- `docs/PRODUCTION_GRADE_A_SHARE_SYSTEM_ROADMAP_2026-04-23.md`

It defines the practical operator recipe beneath the final closeout.

Final authoritative verdict:
- `docs/FSJ_P0_4_FINAL_CLOSEOUT_2026-04-23.md`

This recipe remains useful as the reproduce-on-demand layer for the acceptance surfaces, but it is no longer the top-level verdict doc.

---

## Current truth

As of the final 2026-04-23 closeout, the authoritative acceptance truth is:
- final MAIN package is green,
- `ready_for_delivery=true`,
- all three slots score 100,
- concise support-summary lineage remains intact across six support summaries.

This recipe still documents how to rerun the underlying operator seams, while the final verdict is carried by the final closeout doc.

---

## Canonical command surfaces verified live

The following commands were verified live with `--help` during packaging:

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py --help
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_late_publish.py --help
```

Verified command contracts:
- `scripts/fsj_support_batch_publish.py`
  - requires `--business-date`, `--slot {early,late}`, `--output-root`
  - supports `--agent-domain`, `--generated-at`, `--report-run-id-prefix`, `--require-ready`
- `scripts/fsj_main_late_publish.py`
  - requires `--business-date`, `--output-root`
  - supports `--generated-at`, `--report-run-id-prefix`, `--include-empty`

---

## One rerunnable operator recipe

Business date used for the currently proven evidence class:
- `2026-04-23`

Recommended isolated output roots for a fresh rerun:

```bash
artifacts/fsj_p0_4_acceptance_recipe_20260423/early_support
artifacts/fsj_p0_4_acceptance_recipe_20260423/late_support
artifacts/fsj_p0_4_acceptance_recipe_20260423/late_main
```

Already evidenced early MAIN acceptance package root for this revision:

```bash
artifacts/fsj_p0_4_early_main_acceptance_20260423_subA_20260423T140217Z
```

### Step 1 — regenerate early support standalone evidence

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py \
  --business-date 2026-04-23 \
  --slot early \
  --output-root artifacts/fsj_p0_4_acceptance_recipe_20260423/early_support \
  --require-ready
```

Expected acceptance reading:
- success path should produce:
  - `batch_summary.json`
  - `operator_summary.txt`
  - domain outputs under `macro/`, `commodities/`, `ai_tech/`
- acceptance pass condition for this seam:
  - `operator_summary.txt` shows `ready=3` and `blocked=0`

### Step 2 — validate the now-proven early MAIN acceptance package

Operator must confirm these already-evidenced paths exist:
- `artifacts/fsj_p0_4_early_main_acceptance_20260423_subA_20260423T140217Z/early_main_bundle.json`
- `artifacts/fsj_p0_4_early_main_acceptance_20260423_subA_20260423T140217Z/publish.json`
- `artifacts/fsj_p0_4_early_main_acceptance_20260423_subA_20260423T140217Z/publish/a_share_main_report_2026-04-23_20260423T140218Z.html`
- `artifacts/fsj_p0_4_early_main_acceptance_20260423_subA_20260423T140217Z/publish/a_share_main_report_2026-04-23_20260423T140218Z.qa.json`
- `artifacts/fsj_p0_4_early_main_acceptance_20260423_subA_20260423T140217Z/publish/a_share_main_report_2026-04-23_20260423T140218Z.eval.json`
- `artifacts/fsj_p0_4_early_main_acceptance_20260423_subA_20260423T140217Z/publish/a_share_main_report_delivery_2026-04-23_20260423T140218Z_0260423T140218Z-c3993a90/delivery_manifest.json`

Acceptance reading:
- early bundle shows slot `early`
- QA shows `section_count=3` and `ready_section_count=3`
- eval shows strongest slot `early`
- delivery package exists but may still be hold-blocked

Acceptance rule for this seam:
- **PASS (early MAIN acceptance evidenced)** if the package contains bundle + HTML + QA + eval + delivery manifest and the packaged evaluation shows strongest slot `early`
- this step is evidence-validation, not a requirement to regenerate a green dispatch package

### Step 3 — regenerate late support standalone evidence

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py \
  --business-date 2026-04-23 \
  --slot late \
  --output-root artifacts/fsj_p0_4_acceptance_recipe_20260423/late_support \
  --require-ready
```

Expected acceptance reading:
- this step is rerunnable, but its exact result may depend on whether the late macro support bundle is ready at rerun time,
- therefore the honest acceptance interpretation is:
  - if `ready=3`, late support convergence is directly reproduced,
  - if one domain is blocked, that still reproduces the known real seam shape and requires operator classification instead of false green claiming.

Acceptance rule for this seam:
- **PASS (late support seam reproduced)** if the run produces a truthful `operator_summary.txt` and per-domain outputs/statuses,
- **STRONG PASS (late support convergence reproduced)** only if `ready=3` and `blocked=0`.

### Step 4 — regenerate late MAIN canonical operator seam

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_late_publish.py \
  --business-date 2026-04-23 \
  --output-root artifacts/fsj_p0_4_acceptance_recipe_20260423/late_main
```

Expected acceptance reading:
- success path should produce:
  - `main_late_publish_summary.json`
  - `operator_summary.txt`
  - published artifacts under `publish/`
- seam-level pass condition for this recipe:
  - `operator_summary.txt` shows `persist_status=persisted`
  - `operator_summary.txt` shows `publish_status=ready`
  - `publish/` contains the delivery-package surface including `delivery_manifest.json`

Important honesty boundary:
- this step proves the canonical late MAIN operator seam exists and reruns,
- it does **not** require `ready_for_delivery=true`,
- blocked/hold remains a valid reproduced result for this partial acceptance recipe.

### Step 5 — inspect concise support-summary convergence from the late MAIN package

After Step 3, inspect the generated late MAIN summary and delivery manifest for:
- `support_summary_count = 6`
- domains including `ai_tech`, `commodities`, `macro`
- support-summary lineage containing both early and late support bundle IDs

Minimal inspection command:

```bash
cd /Users/neoclaw/repos/ifa-data-platform
python3 - <<'PY'
import json
from pathlib import Path
p = Path('artifacts/fsj_p0_4_acceptance_recipe_20260423/late_main/main_late_publish_summary.json')
j = json.loads(p.read_text())
dm = ((j.get('publish') or {}).get('delivery_manifest') or {})
agg = (dm.get('support_summary_aggregate') or {})
print({
    'package_state': dm.get('package_state'),
    'ready_for_delivery': dm.get('ready_for_delivery'),
    'recommended_action': ((dm.get('dispatch_advice') or {}).get('recommended_action')),
    'support_summary_count': agg.get('support_summary_count'),
    'domains': agg.get('domains'),
    'bundle_ids': agg.get('bundle_ids'),
})
PY
```

Acceptance rule for this seam:
- **PASS (narrow convergence reproduction)** if the generated late MAIN delivery manifest exposes six support-summary entries spanning early + late support bundle IDs,
- **FAIL** if support-summary lineage is absent or collapses below the currently proven six-summary evidence class.

---

## Rerun verdict mapping

Apply these outcome labels only:

### Allowed positive labels
- `early support reproduced`
- `late support seam reproduced`
- `late support convergence reproduced`
- `late MAIN canonical seam reproduced`
- `support-summary convergence reproduced`
- `partial P0-4 acceptance recipe rerun completed`

### Final labeling note
For the 2026-04-23 evidenced package, the final closeout now allows:
- `P0-4 acceptance closed`
- `all-slot acceptance complete`
- `dispatch-ready proven` **for the cited final package only**
- `P0-1 / P0-2 / P0-3 materially closed for current roadmap scope`

Do not extend that claim beyond the exact artifact root cited in `docs/FSJ_P0_4_FINAL_CLOSEOUT_2026-04-23.md` and the normalization captured in `docs/FSJ_P0_1_P0_2_P0_3_CLOSEOUT_2026-04-24.md`.

---

## What this recipe covers

This recipe covers only these currently evidenced classes:
1. the support standalone canonical operator command is rerunnable,
2. the late MAIN canonical operator command is rerunnable,
3. early support can be checked for 3/3-ready reproduction,
4. late support can be checked for truthful blocked-or-converged reproduction,
5. late MAIN can be checked for persist + publish surface generation,
6. concise support-summary lineage can be checked from the generated late MAIN package,
7. early MAIN evidence can be scored as present under the same publish + QA + eval standard even while final delivery remains blocked.

---

## What still requires new evidence

No additional evidence is required to uphold the authoritative 2026-04-23 `P0` acceptance closeout.

The items below are retained only as broader strengthening opportunities and must not be interpreted as blockers to the accepted closeout:

1. **Per-slot timing / deadline proof**
   - this recipe proves command surfaces and artifact outcomes, not slot-timing measurements against SLA deadlines

2. **Further rerun ergonomics / automation**
   - this recipe is intentionally thin and reproduce-on-demand; richer operator automation remains optional follow-on work

---

## Verification run used to package this recipe

During packaging, the following were verified live:
- both canonical command surfaces resolve with `--help`,
- the referenced proof docs exist,
- the cited artifact roots for early support, late support, late convergence, and late MAIN exist,
- operator summaries confirm:
  - early support `ready=3`, `blocked=0`,
  - early MAIN acceptance package exists with bundle + HTML + QA + eval + delivery-manifest artifacts,
  - late live proof `ready=2`, `blocked=1`,
  - late convergence `ready=3`, `blocked=0`,
  - late MAIN `persist_status=persisted`, `publish_status=ready`,
- the final authoritative closeout later upgraded the acceptance verdict to a delivery-ready green package for the cited 2026-04-23 artifact root.

This recipe document itself does **not** fabricate new evidence; it standardizes how an operator can rerun the already-proven seams on demand.

---

## Relationship to the ledger

Use this document for:
- **how to rerun** the currently proven acceptance seams.

Use `docs/FSJ_P0_4_FINAL_CLOSEOUT_2026-04-23.md` for:
- the final authoritative verdict.

Use `docs/FSJ_P0_4_ACCEPTANCE_LEDGER_2026-04-23.md` for:
- the historical pre-green scoring layer.
