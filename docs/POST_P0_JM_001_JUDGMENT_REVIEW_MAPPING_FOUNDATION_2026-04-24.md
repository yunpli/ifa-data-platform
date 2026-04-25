# POST-P0-JM-001 Judgment Review / Mapping / Explainability Foundation

## Scope
- judgment item level review surfaces
- evidence -> support -> main -> customer wording mapping ledger foundation
- early -> mid -> late judgment progression foundation
- late report retrospective linkage back to earlier judgment surfaces
- learning-asset-ready structure for correct / wrong judgments

## Audit Summary

### Current surfaces before this change
1. **Package-level review existed**
   - Main delivery package already exposed package-level QA, slot evaluation, dispatch advice, package index, browse README.
   - Operator review surface could summarize package/send/review governance, but not individual judgment items.
2. **Lineage inputs already existed but were not normalized into judgment review artifacts**
   - Main assembled sections already contained `judgments`, `signals`, `facts`, `support_summaries`, `lineage.evidence_links`, `lineage.support_bundle_ids`, and late-slot contract context.
   - Customer presentation wording existed in renderer metadata for `customer` profile, but no ledger tied that wording back to judgment/support/evidence layers.
3. **Gap before this task**
   - No package-native judgment item review surface.
   - No compact mapping ledger from evidence/support/main judgment to customer wording.
   - No minimal retrospective linkage structure from late output back to prior-slot judgment surfaces.
   - No learning-asset-ready scaffold for later correct/wrong labeling.

## Minimal implementation path
- Keep current FSJ report chain intact.
- Do **not** add new DB tables or refactor collectors/data paths.
- Generate two new package artifacts inside canonical main delivery packaging:
  1. `judgment_review_surface.json`
  2. `judgment_mapping_ledger.json`
- Thread compact summaries + file paths into:
  - delivery manifest
  - package index / browse readme
  - persisted `metadata_json.delivery_package`
  - store package/operator review surfaces
- Extend focused tests only around existing main-report packaging seam.

## Concrete changes
- `src/ifa_data_platform/fsj/report_rendering.py`
  - persist assembled payload in main publish result/manifest
  - build judgment review surface artifact
  - build judgment mapping ledger artifact
  - add both artifacts to delivery manifest, package index, browse summary, and persisted delivery-package metadata
- `src/ifa_data_platform/fsj/store.py`
  - expose judgment review / mapping paths and summaries in package/operator review surfaces
- `scripts/fsj_main_report_publish.py`
  - emit package pointers for the new artifacts in JSON output
- `tests/unit/test_fsj_report_rendering.py`
  - assert new artifacts exist and contain the expected minimal structure
- `tests/unit/test_fsj_main_report_publish_script.py`
  - assert new publish-script keys are present

## Validation
- `python3 -m pytest -q tests/unit/test_fsj_report_rendering.py tests/unit/test_fsj_main_report_publish_script.py`
- Result: `27 passed`

## Exact evidence paths
- `docs/POST_P0_JM_001_JUDGMENT_REVIEW_MAPPING_FOUNDATION_2026-04-24.md`
- `src/ifa_data_platform/fsj/report_rendering.py`
- `src/ifa_data_platform/fsj/store.py`
- `scripts/fsj_main_report_publish.py`
- `tests/unit/test_fsj_report_rendering.py`
- `tests/unit/test_fsj_main_report_publish_script.py`
- `docs/IFA_Execution_Progress_Monitor.md`

## Residual gaps
- Item-level operator decisions are still package-file foundations, not a full DB-backed workflow table.
- Late retrospective linkage currently provides a minimal slot/judgment anchor, not full scored outcome attribution.
- Mapping ledger is package-native foundation only; no cross-day knowledge graph or heavy operator UI yet.
- Correct/wrong learning labels remain placeholders for later outcome tagging.

## Acceptance
- **Foundation acceptance: met** for the requested minimal safe closure.
- Why: item-level review surface, mapping ledger, early->late progression hooks, late retrospective anchor, and learning-asset-ready placeholders now exist without breaking the current FSJ pipeline or expanding into unrelated platform work.
