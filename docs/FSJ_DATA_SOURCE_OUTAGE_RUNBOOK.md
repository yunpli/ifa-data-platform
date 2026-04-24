# FSJ Data-Source Outage Runbook

Date: 2026-04-24  
Owner: Developer Lindenwood  
Scope: operator handling for FSJ source-health outage / degraded-source posture across MAIN + support scopes

---

## 1. Current truth

This runbook covers the already-landed source-health truth that FSJ emits today:

- source-health is derived from persisted bundle degrade metadata during QA / packaging
- MAIN can distinguish **blocked** vs **degraded** source-health posture by slot
- support reports currently surface source-health as **degraded** attention, not hard-blocking delivery
- operator surfaces already expose source-health through:
  - `scripts/fsj_main_delivery_status.py`
  - `scripts/fsj_support_delivery_status.py`
  - `scripts/fsj_operator_board.py`
- focused fleet/subject summary for this runbook:
  - `scripts/fsj_source_health_status.py`
- canonical source-health evaluation logic:
  - `src/ifa_data_platform/fsj/report_quality.py`
- canonical projection into operator/read surfaces:
  - `src/ifa_data_platform/fsj/store.py`

Important boundary:

- this runbook is grounded in **report-level source-health truth already persisted into QA / review surfaces**
- it is **not** a collector-runtime debugging manual for every upstream daemon/adaptor
- if source-health is already healthy on FSJ operator truth, but a collector team reports an outage elsewhere, treat that as an adjacent runtime investigation, not as a justified FSJ delivery hold by itself

This keeps the runbook honest: operators act on the truth the delivery system actually projects.

---

## 2. When to use this runbook

Use this runbook when any of the following is true:

- operator asks “is this a real source outage or just a review/dispatch issue?”
- `source_health_status` is `blocked` or `degraded`
- operator board shows source-health attention subjects
- MAIN late package is held because same-day required structure is missing
- support package is review-held/degraded because upstream background support is incomplete
- you need to decide between:
  - hold / do not send
  - bounded degraded send
  - rerun after upstream recovery

Do **not** use this runbook as proof that a collector process is currently down. This runbook answers whether the **report package** is source-health blocked/degraded.

---

## 3. Canonical operator commands

### 3.1 Focused fleet/subject source-health attention

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_source_health_status.py
```

Optional explicit business date:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_source_health_status.py --business-date 2026-04-23
```

Optional JSON:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_source_health_status.py --format json
```

Optional full visibility including clean subjects:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_source_health_status.py --include-healthy
```

Key fields:

- `fleet_summary`
- `fleet_status_counts`
- `attention_subjects`
- `blocked_subjects`
- `degraded_subjects`
- per-subject `summary_line`

### 3.2 Full MAIN status for source-health context

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest
```

Focus fields:

- `source_health_status`
- `source_health_blocking_slot_count`
- `source_health_degraded_slot_count`
- `recommended_action`
- `workflow_state`
- `review_required`
- `send_ready`

### 3.3 Full support status for one domain

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain commodities --latest
```

Also useful for:

```bash
--agent-domain macro
--agent-domain ai_tech
```

### 3.4 Fleet board for cross-checking other holds

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_operator_board.py
```

Use this when you need to confirm whether source-health attention is the primary blocker, versus LLM lineage, governance, selection mismatch, or dispatch posture.

---

## 4. Current source-health semantics in code

### 4.1 MAIN source-health: blocked vs degraded

Current evaluator truth from `src/ifa_data_platform/fsj/report_quality.py`:

**Blocked reasons**

- `same_day_final_structure_missing`

Meaning:

- a required same-day source family for MAIN is missing
- the package must not be treated as clean sendable truth for the affected slot
- on late MAIN this is the strong outage family already represented in current QA truth

**Degraded reasons**

- `missing_preopen_high_layer`
- `missing_intraday_structure`
- any other non-empty MAIN degrade reason not in the explicit blocking set

Meaning:

- package is still grounded, but upstream completeness is reduced
- operator may still see bounded delivery posture depending on workflow / governance
- do not silently treat degraded as healthy

### 4.2 Support source-health: degraded attention

Current evaluator truth from `src/ifa_data_platform/fsj/report_quality.py`:

Support currently projects source-health degradation for reasons such as:

- `missing_background_support`
- `missing_macro_snapshot`
- `missing_ai_tech_snapshot`
- any other non-empty support degrade reason

Meaning:

- support package evidence is thinner than ideal
- this is operator-visible policy attention
- current code does **not** promote these support reasons into the MAIN-style blocked set

This distinction matters: do not invent a system-wide outage classification broader than current code truth.

---

## 5. Triage checklist

Run these in order.

### Step 1 — get focused source-health attention summary

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_source_health_status.py
```

This tells you whether the current incident is:

- fleet healthy
- one or more subjects degraded
- one or more subjects blocked

### Step 2 — identify whether the affected subject is MAIN or support

Interpretation:

- `main` → usually strongest send/governance consequence
- `support:<domain>` → support-only degraded posture unless broader package truth says otherwise

### Step 3 — inspect the full subject status

For MAIN:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest
```

For support:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain <macro|commodities|ai_tech> --latest
```

Focus on:

- `source_health_status`
- `recommended_action`
- `workflow_state`
- `review_required`
- `send_ready`
- `go_no_go_decision`

### Step 4 — classify the incident

#### Class A — MAIN required-source outage (`blocked`)

Indicators:

- `source_health_status=blocked`
- usually `source_health_blocking_slot_count>0`
- often reason `same_day_final_structure_missing`
- package is held / not truthfully send-ready

Action:

1. do **not** send the affected MAIN package as if it were complete
2. treat this as a real report-level source outage
3. recover upstream required source family or rerun when it is available
4. only resume send path once operator truth stops reporting blocked source-health

#### Class B — bounded degraded MAIN package

Indicators:

- `source_health_status=degraded`
- no blocked slots
- workflow/governance may still allow send or review

Action:

1. keep degraded posture explicit in operator notes
2. check whether package is still `send_ready=True` or `review_required=True`
3. if sendable, send only under the bounded degraded interpretation already projected by the system
4. do not overstate certainty or silently relabel it healthy

#### Class C — support-only degraded source posture

Indicators:

- `subject=support:<domain>`
- `source_health_status=degraded`
- reasons such as `missing_background_support`, `missing_macro_snapshot`, `missing_ai_tech_snapshot`

Action:

1. treat as support evidence degradation
2. inspect whether support package is review-held or still sendable on its own surface
3. if MAIN is otherwise healthy, do not escalate this into a fictitious whole-system outage
4. if rerun is cheap and upstream source recovers quickly, rerun the support package rather than hand-editing content

#### Class D — no source-health attention; issue belongs elsewhere

Indicators:

- `scripts/fsj_source_health_status.py` shows clean fleet or no affected subject
- but operator still reports a problem

Action:

- move to the correct runbook/seam:
  - dispatch/send issue → `docs/FSJ_SEND_DISPATCH_FAILURE_RUNBOOK.md`
  - LLM fallback/degrade issue → `docs/FSJ_LLM_FALLBACK_RUNBOOK.md`
  - broader collector/runtime issue → collection/runtime operator docs outside FSJ delivery posture

---

## 6. Rerun discipline for source outages

Before rerunning because of a source outage, confirm all are true:

- the problematic posture is genuinely `source_health_status=blocked` or `degraded`
- the missing/degraded reason is source-related, not dispatch/governance/selection mismatch
- upstream source family has actually recovered, or the rerun is intentionally meant to produce a truthful degraded replacement
- the new package will supersede the old one through the normal operator path

Do **not**:

- hand-edit HTML to hide the degraded reason
- relabel a blocked package as sendable without a rerun/new package truth
- confuse LLM fallback with source-health outage

---

## 7. Truthful operator language

Use language like:

- “MAIN package is source-health blocked; same-day required structure is missing, so do not send yet.”
- “Support package is source-health degraded; bounded delivery/review posture remains operator-visible.”
- “This looks clean on source-health; the incident belongs to dispatch/governance, not source outage handling.”
- “Rerun should happen after upstream source recovery or to produce a truthful degraded replacement package.”

Do **not** say:

- “all upstream data is down” unless you independently verified the runtime side
- “the package is healthy now” when source-health still says `blocked` or `degraded`
- “just resend the same report” when the real issue is missing required source family truth

---

## 8. Verification commands

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest \
  tests/unit/test_fsj_source_health_status_script.py \
  tests/unit/test_fsj_report_rendering.py \
  tests/unit/test_fsj_operator_board_script.py \
  -q
```

These checks verify:

- focused source-health status summary formatting/projection
- QA source-health blocked/degraded semantics
- operator-board source-health exposure remains intact

---

## 9. Thin operator summary

If someone says “data source outage,” first answer this:

- is the **report package** actually source-health blocked or degraded on operator truth?

Use:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_source_health_status.py
```

Then act by posture:

- `blocked` on MAIN → hold / recover source / rerun
- `degraded` on MAIN → bounded degraded send/review decision
- `degraded` on support → support-specific review/rerun judgment
- no source-health attention → wrong runbook; inspect dispatch, governance, or runtime instead
