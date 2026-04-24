# FSJ Late-Slot Production Runbook

Date: 2026-04-24  
Owner: Developer Lindenwood  
Scope: operator handling for normal late-slot production posture across support standalone outputs + MAIN late package

---

## 1. Current truth

This runbook covers the already-landed operator path for the **late slot** in A-share FSJ.

Canonical late-slot operator commands already exist:

- support standalone late path:
  - `scripts/fsj_support_batch_publish.py`
- MAIN late persist + publish path:
  - `scripts/fsj_main_late_publish.py`
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
- it tells operators how to run and verify the late slot using the truth surfaces that already exist
- it does **not** redefine QA policy, dispatch receipts, or collector-runtime debugging
- when late-slot truth goes red/yellow, this runbook routes the operator to the already-landed focused runbooks instead of inventing a new failure taxonomy

This keeps `P2-4` honest: one bounded runbook for the real late production path.

---

## 2. When to use this runbook

Use this runbook when any of the following is true:

- you are producing the normal **late slot** package set for a business date
- you need the canonical operator sequence for late support + late MAIN
- you need to decide whether late MAIN is clean, review-held, degraded, or blocked
- you want to know which command to run first vs which status surface to inspect next
- someone asks “what is the actual late-slot operator path right now?”

Do **not** use this runbook for:

- early-slot only handling
- mid-slot only handling
- deep collector/runtime outage debugging
- downstream channel receipt confirmation beyond current DB/operator truth

---

## 3. Late-slot canonical operator sequence

Run the late slot in this order.

### Step 1 — produce standalone support artifacts first

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py \
  --business-date YYYY-MM-DD \
  --slot late \
  --output-root artifacts/fsj_support_batch_YYYYMMDD_late \
  --require-ready
```

Why first:

- support standalone outputs are independent operator-visible artifacts
- the support path already bakes in `persist-before-publish`
- late MAIN should consume bounded support summary truth, not replace support publication
- `--require-ready` is the truthful production posture for late support publication

### Step 2 — produce late MAIN through the canonical combined path

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_late_publish.py \
  --business-date YYYY-MM-DD \
  --output-root artifacts/fsj_main_late_YYYYMMDD
```

Why this path is canonical:

- it persists the late MAIN FSJ bundle first
- it publishes the MAIN package second
- it keeps persistence and publish version-linked in one operator seam
- it writes one combined operator summary / machine-readable summary

### Step 3 — inspect fleet/operator board truth

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_operator_board.py
```

Use this to confirm:

- late-slot subjects exist on the board
- current semantic status is truthful (`ready`, `review`, `held`, etc.)
- the likely blocker belongs to source-health, governance, selection mismatch, missing bundle, or dispatch posture

### Step 4 — inspect full delivery status surfaces

MAIN:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest --slot late
```

Support domains:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain macro --latest --slot late
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain commodities --latest --slot late
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain ai_tech --latest --slot late
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

### 4.1 Late support path

Under the support output root, expect the normal support publish outputs for the chosen business date and slot.

Operator truth should come from:

- support batch publish summary under the chosen output root
- `scripts/fsj_support_delivery_status.py --agent-domain <domain> --latest --slot late`

### 4.2 Late MAIN path

Under the MAIN output root, expect:

- `publish/`
- `main_late_publish_summary.json`
- `operator_summary.txt`

Minimum operator checks before claiming readiness:

- late MAIN publish summary exists
- board/status surfaces point to the current active artifact you just produced
- `selected_is_current=True` on the intended package
- no contradictory `hold` / `review_required` / blocked source-health posture remains

Do **not** treat HTML existence alone as proof that the late package is operationally ready.

---

## 5. Late-slot specific operator interpretation

Late MAIN has the strongest same-day completeness expectations in the current system.

That means operators should answer these questions explicitly before claiming a clean late outcome:

1. is late MAIN source-health `blocked` because same-day required structure is missing?
2. is the package merely `degraded`, which may still be operator-reviewable but is not equivalent to clean late truth?
3. is the package built but still not the selected/current dispatch candidate?
4. did bounded LLM fallback happen without changing the actual workflow/send posture?

This matters because late-slot issues are often misdescribed as generic “send failures” when the real posture is one of:

- source-health block
- review/governance hold
- selected/current mismatch
- bounded degraded package that still needs explicit operator language

Use the status surfaces first. Do not infer from the HTML alone.

---

## 6. Normal late-slot triage flow

### 6.1 If everything looks normal

Expected posture:

- support standalone late outputs exist
- late MAIN output exists
- board shows truthful ready/review state without hidden contradictions
- status surfaces show the intended active artifact

Operator action:

1. archive the output-root evidence paths
2. record the board/status snapshot if needed for acceptance/proof
3. continue only according to the current `send_ready` / `review_required` posture

### 6.2 If the board says `review` or `held`

First answer:

- is this source-health?
- candidate/selection mismatch?
- governance/promotion authority?
- missing delivery artifacts?
- LLM fallback/degraded lineage?

Use:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_operator_board.py
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest --slot late
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain <domain> --latest --slot late
```

Then route to the right focused runbook instead of improvising.

---

## 7. Routing to focused incident runbooks

### 7.1 Source-health issue

Indicators:

- `source_health_status=blocked` or `degraded`
- board/source-health attention summary points to late-slot subjects
- late MAIN same-day required structure is missing

Use:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_source_health_status.py
```

Then follow:

- `docs/FSJ_DATA_SOURCE_OUTAGE_RUNBOOK.md`

### 7.2 Send/dispatch posture issue

Indicators:

- `send_ready=False`
- `selected_is_current=False`
- missing manifests / package artifacts
- `review_required=True`
- package looks built but not truthfully dispatchable

Use MAIN helper:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_send_dispatch_failure_status.py --latest --slot late
```

Use support helper:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_dispatch_failure_status.py --latest --agent-domain <macro|commodities|ai_tech> --slot late
```

Then follow:

- `docs/FSJ_SEND_DISPATCH_FAILURE_RUNBOOK.md`

### 7.3 LLM fallback / deterministic degrade issue

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

## 8. Truthful late-slot operator language

Use language like:

- “Late support standalone artifacts were produced first; late MAIN was then produced through the canonical persist+publish seam.”
- “Late MAIN exists, but operator truth is still review-held, so this is not yet a clean send-ready package.”
- “This late-slot issue is source-health related; same-day required structure is missing, so do not treat it as a generic send failure.”
- “The package exists, but selected/current mismatch means we should switch package rather than resend blindly.”
- “Fallback happened, but the actual decision still belongs to workflow/governance posture, not to fallback presence alone.”

Do **not** say:

- “late slot is green” based only on files in the output directory
- “dispatch failed” when the real issue is review hold or package mismatch
- “data outage” when source-health is clean and the issue belongs to governance or dispatch posture
- “fallback means failure” when the bounded deterministic posture is still operator-acceptable

---

## 9. Verification commands

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest \
  tests/unit/test_fsj_main_late_publish_script.py \
  tests/unit/test_fsj_support_batch_publish_script.py \
  tests/unit/test_fsj_operator_board_script.py \
  tests/unit/test_fsj_main_delivery_status_script.py \
  tests/unit/test_fsj_support_delivery_status_script.py \
  tests/unit/test_fsj_source_health_status_script.py \
  tests/unit/test_fsj_send_dispatch_failure_status_script.py \
  tests/unit/test_fsj_support_dispatch_failure_status_script.py \
  tests/unit/test_fsj_llm_fallback_status_script.py \
  -q
```

These checks verify the concrete late-slot operator surfaces named in this runbook still exist and remain covered.

---

## 10. Thin operator summary

For the late slot, do this in order:

1. publish standalone support late artifacts with `--require-ready`
2. publish late MAIN through `scripts/fsj_main_late_publish.py`
3. inspect `scripts/fsj_operator_board.py`
4. inspect `scripts/fsj_main_delivery_status.py --latest --slot late`
5. inspect support status per domain
6. if blocked, route by failure family:
   - source-health → `FSJ_DATA_SOURCE_OUTAGE_RUNBOOK.md`
   - dispatch/package mismatch → `FSJ_SEND_DISPATCH_FAILURE_RUNBOOK.md`
   - fallback/degrade → `FSJ_LLM_FALLBACK_RUNBOOK.md`

That is the bounded, production-grade late-slot operating path that exists today.
