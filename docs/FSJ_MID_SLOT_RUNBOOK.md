# FSJ Mid-Slot Production Runbook

Date: 2026-04-24
Owner: Developer Lindenwood
Scope: operator handling for normal mid-slot production posture across MAIN mid package truth

---

## 1. Current truth

This runbook covers the already-landed operator path for the **mid slot** in A-share FSJ.

Canonical mid-slot operator commands now exist:

- MAIN mid persist + publish path:
  - `scripts/fsj_main_mid_publish.py`
- current operator truth / cross-check surfaces:
  - `scripts/fsj_operator_board.py`
  - `scripts/fsj_main_delivery_status.py`
- focused incident helpers already landed and reused here:
  - `scripts/fsj_source_health_status.py`
  - `scripts/fsj_send_dispatch_failure_status.py`
  - `scripts/fsj_llm_fallback_status.py`

Important boundary:

- this is a **slot-operations runbook**, not a new orchestration framework
- it tells operators how to run and verify the mid slot using the truth surfaces that already exist
- it does **not** redefine QA policy, dispatch receipts, or collector-runtime debugging
- when mid-slot truth goes red/yellow, this runbook routes the operator to the already-landed focused runbooks instead of inventing new failure taxonomy

This keeps `P2-4` honest: one bounded runbook for the real mid production path.

---

## 2. When to use this runbook

Use this runbook when any of the following is true:

- you are producing the normal **mid slot** package for a business date
- you need the canonical operator sequence for mid MAIN only
- you need to decide whether mid MAIN is clean, review-held, degraded, or blocked
- you want to know which command to run first vs which status surface to inspect next
- someone asks “what is the actual mid-slot operator path right now?”

Do **not** use this runbook for:

- early-slot only handling
- late-slot only handling
- deep collector/runtime outage debugging
- downstream channel receipt confirmation beyond current DB/operator truth

---

## 3. Mid-slot canonical operator sequence

Run the mid slot in this order.

### Step 1 — produce mid MAIN through the canonical combined path

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_mid_publish.py \
  --business-date YYYY-MM-DD \
  --output-root artifacts/fsj_main_mid_YYYYMMDD
```

Why this path is canonical:

- it persists the mid MAIN FSJ bundle first
- it publishes the MAIN package second
- it keeps persistence and publish version-linked in one operator seam
- it writes one combined operator summary / machine-readable summary

### Step 2 — inspect fleet/operator board truth

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_operator_board.py
```

Use this to confirm:

- mid-slot subjects exist on the board
- current semantic status is truthful (`ready`, `review`, `held`, etc.)
- the likely blocker belongs to source-health, governance, selection mismatch, missing bundle, or dispatch posture

### Step 3 — inspect full mid delivery status surface

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest --slot mid
```

This is the canonical truth surface for:

- `recommended_action`
- `workflow_state`
- `send_ready`
- `review_required`
- `go_no_go_decision`
- `promotion_authority_*`
- `source_health_status`
- lineage / bundle completeness / selection alignment

---

## 4. Expected artifacts and evidence

### 4.1 Mid MAIN path

Under the mid output root, expect:

- `publish/`
- `main_mid_publish_summary.json`
- `operator_summary.txt`

Minimum operator checks before claiming readiness:

- mid MAIN publish summary exists
- board/status surfaces point to the current active artifact you just produced
- `selected_is_current=True` on the intended package
- no contradictory `hold` / `review_required` / blocked source-health posture remains

Do **not** treat HTML existence alone as proof that the mid package is operationally ready.

---

## 5. Normal mid-slot triage flow

### 5.1 If everything looks normal

Expected posture:

- mid MAIN output exists
- board shows truthful ready/review state without hidden contradictions
- status surfaces show the intended active artifact

Operator action:

1. archive the output-root evidence paths
2. record the board/status snapshot if needed for acceptance/proof
3. continue only according to the current `send_ready` / `review_required` posture

### 5.2 If the board says `review` or `held`

First answer:

- is this source-health?
- candidate/selection mismatch?
- governance/promotion authority?
- missing delivery artifacts?
- LLM fallback/degraded lineage?

Use:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_operator_board.py
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest --slot mid
```

Then route to the right focused runbook instead of improvising.

---

## 6. Routing to focused incident runbooks

### 6.1 Source-health issue

Indicators:

- `source_health_status=blocked` or `degraded`
- board/source-health attention summary points to mid-slot subjects

Use:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_source_health_status.py
```

Then follow:

- `docs/FSJ_DATA_SOURCE_OUTAGE_RUNBOOK.md`

### 6.2 Send/dispatch posture issue

Indicators:

- `send_ready=False`
- `selected_is_current=False`
- missing manifests / package artifacts
- `review_required=True`
- package looks built but not truthfully dispatchable

Use MAIN helper:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_send_dispatch_failure_status.py --latest --slot mid
```

Then follow:

- `docs/FSJ_SEND_DISPATCH_FAILURE_RUNBOOK.md`

### 6.3 LLM fallback / deterministic degrade issue

Indicators:

- `llm_fallback_count>0`
- `llm_lineage_status=degraded`
- `llm_operator_tags` shows timeout / malformed / boundary / missing-bundle attention

Use:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_llm_fallback_status.py --days 3
```

Then follow:

- `docs/FSJ_LLM_FALLBACK_RUNBOOK.md`

---

## 7. Truthful mid-slot operator language

Use language like:

- “Mid MAIN was produced through the canonical persist+publish seam.”
- “Mid MAIN exists, but operator truth is still review-held, so this is not yet a clean send-ready package.”
- “This mid-slot issue is source-health related; route to the source-outage runbook rather than treating it as a generic send failure.”
- “The package exists, but selected/current mismatch means we should switch package rather than resend blindly.”

Do **not** say:

- “mid slot is green” based only on files in the output directory
- “dispatch failed” when the real issue is review hold or package mismatch
- “data outage” when source-health is clean and the issue belongs to governance or dispatch posture
- “fallback means failure” when the bounded deterministic posture is still operator-acceptable

---

## 8. Verification commands

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest \
  tests/unit/test_fsj_main_mid_publish_script.py \
  tests/unit/test_fsj_main_mid_producer.py \
  tests/unit/test_fsj_main_delivery_status_script.py \
  tests/unit/test_fsj_operator_board_script.py \
  -q
```

These checks verify the concrete mid-slot operator surfaces named in this runbook still exist and remain covered.

---

## 9. Thin operator summary

For the mid slot, do this in order:

1. publish mid MAIN through `scripts/fsj_main_mid_publish.py`
2. inspect `scripts/fsj_operator_board.py`
3. inspect `scripts/fsj_main_delivery_status.py --latest --slot mid`
4. if blocked, route by failure family:
   - source-health → `FSJ_DATA_SOURCE_OUTAGE_RUNBOOK.md`
   - dispatch/package mismatch → `FSJ_SEND_DISPATCH_FAILURE_RUNBOOK.md`
   - fallback/degrade → `FSJ_LLM_FALLBACK_RUNBOOK.md`

That is the bounded, production-grade mid-slot operating path that exists today.
