# FSJ LLM Fallback Runbook

Date: 2026-04-23  
Owner: Developer Lindenwood  
Scope: operator handling for FSJ LLM fallback / deterministic degrade across MAIN + support scopes

---

## 1. Current truth

This runbook covers the already-landed bounded-LLM production behavior for A-share FSJ:

- primary model chain starts from `grok41_thinking`
- fallback chain is wired in code via resilient clients
- if the model path still fails, the system degrades deterministically instead of inventing output
- fallback / degrade / missing-lineage states are already exposed on operator read surfaces

Canonical truth surfaces already exist in repo code:

- LLM assist policy + fallback/degrade audit
  - `src/ifa_data_platform/fsj/llm_assist.py`
- operator review / lineage summary / workflow handoff projection
  - `src/ifa_data_platform/fsj/store.py`
- per-scope delivery/read status
  - `scripts/fsj_main_delivery_status.py`
  - `scripts/fsj_support_delivery_status.py`
- multi-day drift / fallback trend
  - `scripts/fsj_drift_monitor.py`
- fleet-level fallback attention summary for this runbook
  - `scripts/fsj_llm_fallback_status.py`

This is an **operator runbook**, not a policy-spec rewrite. It explains how to inspect the production truth that the system already emits.

---

## 2. When to use this runbook

Use this runbook when any of the following is true:

- operator review shows `llm_lineage_status=degraded`
- operator review shows `llm_fallback_count>0`
- operator review shows `llm_operator_tags` such as `llm_timeout`, `llm_malformed_output`, `llm_boundary_violation`, `missing_bundle`
- a report is `review_required` / `blocked` and you need to determine whether LLM fallback was merely informational or actually part of the hold posture
- you want the latest fleet view of fallback/degrade across MAIN + support domains

Do **not** use this runbook to re-litigate whether LLM should exist in the pipeline. That policy boundary is already frozen elsewhere; this runbook is about operating the current bounded system safely.

---

## 3. Canonical operator commands

### 3.1 Fleet-level fallback attention

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_llm_fallback_status.py --days 3
```

What it tells you:

- which scopes currently need attention
- whether attention is due to fallback, deterministic degrade, missing lineage, QA blocked, or selection mismatch
- compact scope-by-scope summary lines for triage

Optional:

```bash
--include-clean
--format json
--days 7
```

### 3.2 Latest MAIN operator truth

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest
```

Optional slot-specific resolution:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest --slot late
```

Focus fields:

- `recommended_action`
- `send_ready`
- `review_required`
- `llm_fallback_count`
- `llm_lineage_status`
- `llm_operator_tags`
- `llm_lineage_summary`
- `llm_models`
- `llm_slot_boundary_modes`

### 3.3 Latest support operator truth

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain macro --latest
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain commodities --latest
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain ai_tech --latest
```

Optional slot-specific resolution:

```bash
--slot early
--slot late
```

### 3.4 Multi-day drift / fallback trend

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_drift_monitor.py --scope main --days 7
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_drift_monitor.py --scope support:macro --days 7
```

Use this when you need trend context instead of a single latest snapshot.

---

## 4. How to interpret the surfaces

### 4.1 `llm_fallback_count > 0`

Meaning:

- primary model path did not win for at least one bundle
- a configured fallback model was used successfully
- this is **not automatically a failure**

Operator action:

1. inspect `llm_lineage_status`
2. inspect `recommended_action`, `send_ready`, and QA posture
3. if posture is still ready/sendable and no blocked axes exist, fallback is informational and should be recorded, not escalated by itself
4. if posture moved to review/hold, continue to the checklist below

### 4.2 `llm_lineage_status=degraded`

Meaning:

- the LLM path did not complete cleanly end-to-end for one or more bundles
- the system fell back to deterministic degrade behavior
- this is an expected bounded outcome, not a crash condition

Operator action:

1. read `llm_operator_tags`
2. read `llm_lineage_summary`
3. confirm whether the package is still `review_required` versus fully `blocked`
4. use QA + workflow state as the actual send decision owner

### 4.3 `missing_bundle`

Meaning:

- operator lineage is incomplete for at least one expected bundle
- this is stronger attention than ordinary fallback

Operator action:

1. treat as review/hold attention unless the operator surface explicitly says otherwise
2. inspect whether the problem is upstream production absence vs lineage projection gap
3. use delivery status history and package pointers before any resend/rerun decision

### 4.4 `llm_timeout` / `llm_malformed_output` / `llm_boundary_violation`

Meaning:

- `llm_timeout`: provider path did not return in time
- `llm_malformed_output`: returned structure was not acceptable
- `llm_boundary_violation`: output tried to cross deterministic/report-boundary rules

Operator action:

- do **not** hand-edit the report to “restore” missing LLM prose as if it were deterministic truth
- trust the bounded deterministic degrade already produced by the system
- escalate only if the resulting package posture is not acceptable for that slot/use case

---

## 5. Triage checklist

Run these in order.

### Step 1 — get fleet summary

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_llm_fallback_status.py --days 3
```

If the relevant scope is absent and you did not pass `--include-clean`, the scope is currently clean on this seam.

### Step 2 — inspect latest operator surface for the affected scope

MAIN:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest
```

Support:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_delivery_status.py --agent-domain <macro|commodities|ai_tech> --latest
```

### Step 3 — decide whether this is informational or blocking

Treat as **informational only** when all are true:

- `llm_fallback_count > 0` but no missing-lineage condition
- `send_ready=True` or the workflow is otherwise explicitly ready under operator policy
- QA posture is not blocked
- there is no selection mismatch requiring operator review

Treat as **review attention** when any are true:

- `llm_lineage_status=degraded`
- `review_required=True`
- `llm_operator_tags` present and package is not clearly ready
- selection mismatch exists

Treat as **hold / escalate** when any are true:

- `llm_missing_bundle_dates` / `missing_bundle` appears
- QA blocked axes exist
- workflow state is `blocked`
- selected candidate does not match current active artifact and the surface is already hold-oriented

### Step 4 — if trend context is needed, inspect drift

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_drift_monitor.py --scope main --days 7
```

Questions to answer:

- isolated one-day fallback or repeated pattern?
- one scope only or fleet-wide?
- did fallback still leave packages ready, or is quality posture deteriorating?

---

## 6. Normal operator responses

### Case A — fallback applied, package still ready

Example posture:

- `llm_fallback_count=1`
- `llm_lineage_status=degraded` or applied-with-fallback context
- `recommended_action=send`
- `send_ready=True`

Response:

- record fallback in the run log / operator note
- do not force rerun solely because fallback happened
- continue with the normal send path if all other gates are green

### Case B — fallback applied and package moved to review

Example posture:

- `recommended_action=send_review`
- `review_required=True`
- no hard missing bundle

Response:

- treat as a bounded review case
- inspect review manifest / workflow pointers from the delivery status output
- decide whether operator review is sufficient or whether a rerun is justified

### Case C — deterministic degrade plus missing lineage / blocked QA

Example posture:

- `llm_lineage_status=incomplete` or `degraded`
- `llm_operator_tags` includes `missing_bundle`
- QA blocked axes or `workflow_state=blocked`

Response:

- do not send
- treat as hold until lineage/truth is repaired or a truthful rerun supersedes it

---

## 7. What operators should not do

Do **not**:

- treat any LLM fallback as an automatic production incident
- manually rewrite report language to mimic the missing model output
- bypass the DB-backed operator surface and judge only from HTML existence
- claim the package is green if the workflow surface still says review/hold
- confuse “fallback happened” with “system failed”

The designed behavior is:

- bounded assist
- provider resilience when possible
- deterministic degrade when needed
- operator-visible audit either way

---

## 8. Verification commands

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest \
  tests/unit/test_fsj_main_mid_producer.py \
  tests/unit/test_fsj_late_llm_assist.py \
  tests/unit/test_fsj_drift_monitor_script.py \
  tests/unit/test_fsj_llm_fallback_status_script.py -q
```

These checks verify:

- fallback model chain behavior is still tested
- deterministic degrade tagging remains covered
- drift monitor operator surface remains covered
- fleet fallback status summary remains covered

---

## 9. Roadmap impact

This lands the thinnest honest `P2-4` runbook slice for LLM resilience because:

- the code path already existed and was tested
- operator truth surfaces already existed and were DB-backed
- this runbook now gives one canonical inspection path plus one fleet summary path
- no generic prose or aspirational UI was introduced

This does **not** mean broader `P4-2` governance is fully closed. It means the current production operator seam for fallback handling is now real, concise, and auditable.
