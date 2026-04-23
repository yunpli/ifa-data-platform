# FSJ P0-4 Rerunnable Acceptance Recipe — 2026-04-23

## Scope

This is the thinnest honest **rerunnable command-based acceptance recipe** above:
- `docs/FSJ_SLA_PROOF_PACKAGE_2026-04-23.md`
- `docs/FSJ_P0_4_ACCEPTANCE_LEDGER_2026-04-23.md`
- `docs/PRODUCTION_GRADE_A_SHARE_SYSTEM_ROADMAP_2026-04-23.md`

It defines one practical operator recipe that can be rerun to regenerate the **currently proven** evidence classes:
1. early support standalone publish,
2. late support standalone publish,
3. late MAIN canonical operator seam,
4. concise early/late support-summary linkage as seen from late MAIN artifacts.

It does **not** claim full `P0-4` closure.
It does **not** claim `mid` coverage.
It does **not** require a green delivery-ready late MAIN outcome.

---

## Current truth

As of `2026-04-23`, the currently evidenced and rerunnable seams are:
- early support standalone: **proven green** (`ready=3`, `blocked=0`),
- late support standalone: **proven as a real seam with honest blocked-first then converged evidence**,
- late MAIN canonical operator seam: **proven for persist + publish surface generation**,
- late MAIN delivery posture: **still blocked / hold**, not SLA-green,
- concise support-summary convergence: **proven narrowly** via six lineage-traceable support-summary bundle IDs across early + late.

Therefore this recipe can honestly reproduce only a **partial acceptance package**, not full `P0-4 done`.

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

### Step 2 — regenerate late support standalone evidence

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

### Step 3 — regenerate late MAIN canonical operator seam

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

### Step 4 — inspect concise support-summary convergence from the late MAIN package

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

### Forbidden over-claims
Do **not** label the rerun as:
- `P0-4 done`
- `full SLA closure`
- `all-slot acceptance complete`
- `dispatch-ready proven`

---

## What this recipe covers

This recipe covers only these currently evidenced classes:
1. the support standalone canonical operator command is rerunnable,
2. the late MAIN canonical operator command is rerunnable,
3. early support can be checked for 3/3-ready reproduction,
4. late support can be checked for truthful blocked-or-converged reproduction,
5. late MAIN can be checked for persist + publish surface generation,
6. concise support-summary lineage can be checked from the generated late MAIN package.

---

## What still requires new evidence

1. **Mid slot acceptance evidence**
   - this recipe does not regenerate or validate `mid`

2. **One all-slot SLA package**
   - this recipe does not close `early + mid + late` under one final acceptance bar

3. **Green dispatch-ready late MAIN outcome**
   - current proven state is still blocked/hold
   - a future package must prove non-blocked send-readiness

4. **Per-slot timing / deadline proof**
   - this recipe proves command surfaces and artifact outcomes, not slot-timing measurements against SLA deadlines

5. **Final P0-4 acceptance artifact**
   - this recipe is a thin reproduce-on-demand layer, not the final closure document

---

## Verification run used to package this recipe

During packaging, the following were verified live:
- both canonical command surfaces resolve with `--help`,
- the referenced proof docs exist,
- the cited artifact roots for early support, late support, late convergence, and late MAIN exist,
- operator summaries confirm:
  - early support `ready=3`, `blocked=0`,
  - late live proof `ready=2`, `blocked=1`,
  - late convergence `ready=3`, `blocked=0`,
  - late MAIN `persist_status=persisted`, `publish_status=ready`,
- late MAIN packaged delivery surface still shows blocked/hold rather than delivery-ready green.

This recipe document itself does **not** fabricate new evidence; it standardizes how an operator can rerun the already-proven seams on demand.

---

## Relationship to the ledger

Use this document for:
- **how to rerun** the currently proven acceptance seams.

Use `docs/FSJ_P0_4_ACCEPTANCE_LEDGER_2026-04-23.md` for:
- **how to score** the resulting evidence honestly.
