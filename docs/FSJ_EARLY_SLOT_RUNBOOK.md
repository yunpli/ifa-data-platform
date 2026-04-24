# FSJ Early-Slot Production Runbook

Date: 2026-04-24  
Owner: Developer Lindenwood  
Scope: operator handling for normal early-slot production posture across support standalone outputs + MAIN early package

---

## 1. Current truth

This runbook covers the already-landed operator path for the **early slot** in A-share FSJ.

Canonical early-slot operator commands already exist:

- support standalone early path:
  - `scripts/fsj_support_batch_publish.py`
- MAIN early persist + publish path:
  - `scripts/fsj_main_early_publish.py`
- current operator truth / cross-check surfaces:
  - `scripts/fsj_operator_board.py`
  - `scripts/fsj_main_delivery_status.py`
  - `scripts/fsj_support_delivery_status.py`
- focused incident helpers already landed and reused here:
  - `scripts/fsj_source_health_status.py`
  - `scripts/fsj_send_dispatch_failure_status.py`
  - `scripts/fsj_support_dispatch_failure_status.py`
  - `scripts/fsj_llm_fallback_status.py`

Important boundary:

- this is a **slot-operations runbook**, not a new orchestration framework
- it tells operators how to run and verify the early slot using the truth surfaces that already exist
- it does **not** redefine QA policy, dispatch receipts, or collector-runtime debugging
- when early-slot truth goes red/yellow, this runbook routes the operator to the already-landed focused runbooks instead of inventing a new failure taxonomy

This keeps `P2-4` honest: one bounded runbook for the real early production path.

---

## 2. When to use this runbook

Use this runbook when any of the following is true:

- you are producing the normal **early slot** package set for a business date
- you need the canonical operator sequence for early support + early MAIN
- you need to decide whether early MAIN is clean, review-held, degraded, or blocked
- you want to know which command to run first vs which status surface to inspect next
- someone asks “what is the actual early-slot operator path right now?”

Do **not** use this runbook for:

- mid-slot only handling
- late-slot only handling
- deep collector/runtime outage debugging
- downstream channel receipt confirmation beyond current DB/operator truth

---

## 3. Early-slot canonical operator sequence

Run the early slot in this order.

### Step 1 — produce standalone support artifacts first

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py \
  --business-date YYYY-MM-DD \
  --slot early \
  --output-root artifacts/fsj_support_batch_YYYYMMDD_early
```

Why first:

- support standalone outputs are independent operator-visible artifacts
- the support path already bakes in `persist-before-publish`
- early MAIN should consume bounded support summary truth, not replace support publication

### Step 2 — produce early MAIN through the canonical combined path

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_early_publish.py \
  --business-date YYYY-MM-DD \
  --output-root artifacts/fsj_main_early_YYYYMMDD
```

Why this path is canonical:

- it persists the early MAIN FSJ bundle first
- it publishes the MAIN package second
- it keeps persistence and publish version-linked in one operator seam
- it writes one combined operator summary / machine-readable summary

### Step 3 — inspect fleet/operator board truth

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_operator_board.py
```

Use this to confirm:

- early-slot subjects exist on the board
- current semantic status is truthful (`ready`, `review`, `held`, etc.)
- the likely blocker belongs to source-health, governance, selection mismatch, missing bundle, or dispatch posture

### Step 4 — inspect full delivery status surfaces

MAIN:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest --slot early
```

Support domains:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain macro --latest --slot early
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain commodities --latest --slot early
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain ai_tech --latest --slot early
```

These are the canonical truth surfaces for:

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

### 4.1 Early support path

Under the support output root, expect the normal support publish outputs for the chosen business date and slot.

Operator truth should come from:

- support batch publish summary under the chosen output root
- `scripts/fsj_support_delivery_status.py --agent-domain <domain> --latest --slot early`

### 4.2 Early MAIN path

Under the MAIN output root, expect:

- `publish/`
- `main_early_publish_summary.json`
- `operator_summary.txt`

Minimum operator checks before claiming readiness:

- early MAIN publish summary exists
- board/status surfaces point to the current active artifact you just produced
- `selected_is_current=True` on the intended package
- no contradictory `hold` / `review_required` / blocked source-health posture remains

Do **not** treat HTML existence alone as proof that the early package is operationally ready.

---

## 5. Normal early-slot triage flow

### 5.1 If everything looks normal

Expected posture:

- support standalone early outputs exist
- early MAIN output exists
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
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest --slot early
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain <domain> --latest --slot early
```

Then route to the right focused runbook instead of improvising.

---

## 6. Routing to focused incident runbooks

### 6.1 Source-health issue

Indicators:

- `source_health_status=blocked` or `degraded`
- board/source-health attention summary points to early-slot subjects

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
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_send_dispatch_failure_status.py --latest --slot early
```

Use support helper:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_dispatch_failure_status.py --latest --agent-domain <macro|commodities|ai_tech> --slot early
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

## 7. Truthful early-slot operator language

Use language like:

- “Early support standalone artifacts were produced first; early MAIN was then produced through the canonical persist+publish seam.”
- “Early MAIN exists, but operator truth is still review-held, so this is not yet a clean send-ready package.”
- “This early-slot issue is source-health related; route to the source-outage runbook rather than treating it as a generic send failure.”
- “The package exists, but selected/current mismatch means we should switch package rather than resend blindly.”

Do **not** say:

- “early slot is green” based only on files in the output directory
- “dispatch failed” when the real issue is review hold or package mismatch
- “data outage” when source-health is clean and the issue belongs to governance or dispatch posture
- “fallback means failure” when the bounded deterministic posture is still operator-acceptable

---

## 8. Verification commands

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest \
  tests/unit/test_fsj_main_early_publish_script.py \
  tests/unit/test_fsj_support_batch_publish_script.py \
  tests/unit/test_fsj_operator_board_script.py \
  tests/unit/test_fsj_main_delivery_status_script.py \
  tests/unit/test_fsj_support_delivery_status_script.py \
  tests/unit/test_fsj_source_health_status_script.py \
  tests/unit/test_fsj_send_dispatch_failure_status_script.py \
  tests/unit/test_fsj_support_dispatch_failure_status_script.py \
  -q
```

These checks verify the concrete early-slot operator surfaces named in this runbook still exist and remain covered.

---

## 9. Thin operator summary

For the early slot, do this in order:

1. publish standalone support early artifacts
2. publish early MAIN through `scripts/fsj_main_early_publish.py`
3. inspect `scripts/fsj_operator_board.py`
4. inspect `scripts/fsj_main_delivery_status.py --latest --slot early`
5. inspect support status per domain
6. if blocked, route by failure family:
   - source-health → `FSJ_DATA_SOURCE_OUTAGE_RUNBOOK.md`
   - dispatch/package mismatch → `FSJ_SEND_DISPATCH_FAILURE_RUNBOOK.md`
   - fallback/degrade → `FSJ_LLM_FALLBACK_RUNBOOK.md`

That is the bounded, production-grade early-slot operating path that exists today.
