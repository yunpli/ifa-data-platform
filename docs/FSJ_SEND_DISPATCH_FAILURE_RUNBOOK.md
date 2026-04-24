# FSJ Send / Dispatch Failure Runbook

Date: 2026-04-23  
Owner: Developer Lindenwood  
Scope: operator handling for MAIN send/dispatch failure posture on the already-landed FSJ delivery workflow

---

## 1. Current truth

This runbook covers the truthful seams that already exist for MAIN delivery packaging / review / dispatch selection:

- MAIN delivery status / operator review surface
  - `scripts/fsj_main_delivery_status.py`
- thin send/dispatch-failure operator helper for this runbook
  - `scripts/fsj_send_dispatch_failure_status.py`
- workflow / review / send manifest production
  - `src/ifa_data_platform/fsj/report_orchestration.py`
- DB-backed workflow handoff / package / operator review projection
  - `src/ifa_data_platform/fsj/store.py`

Important boundary:

- this seam tells you whether the selected package is truthfully dispatchable **before** channel send
- this seam does **not** yet model downstream Telegram/channel receipt or delivery acknowledgment
- therefore this runbook is for **pre-dispatch blockage, package mismatch, review hold, or missing-artifact recovery**
- if an operator claims “Telegram failed after we sent it”, that downstream failure is currently **outside DB truth on this seam**

This is intentional. The runbook stays honest instead of pretending we have send receipts that the system does not yet persist.

---

## 2. When to use this runbook

Use this runbook when any of the following is true:

- operator asks “why can’t we send this package?”
- `send_ready=False`
- `review_required=True`
- `selected_is_current=False`
- `go_no_go_decision` is `REVIEW` or `NO_GO`
- package artifacts appear missing or stale
- there is confusion between current package vs selected dispatch candidate
- a resend is being considered and you need to confirm the package truth first

Do **not** use this runbook to prove channel delivery success. That truth is not yet captured here.

---

## 3. Canonical operator commands

### 3.1 Focused send/dispatch-failure posture

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_send_dispatch_failure_status.py --latest
```

Optional slot-specific resolution:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_send_dispatch_failure_status.py --latest --slot late
```

Or explicit business date:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_send_dispatch_failure_status.py --business-date 2026-04-23
```

Useful flags:

```bash
--format json
--history-limit 8
```

Key fields:

- `dispatch_posture`
- `failure_reasons`
- `missing_required_artifacts`
- `action_summary`
- `selected_is_current`
- `go_no_go_decision`
- `next_step`
- artifact checks / manifest pointers
- `channel_delivery_truth`

### 3.2 Full MAIN operator surface

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_delivery_status.py --latest
```

Use this when you need the richer QA / lineage / package state context around the failure posture.

---

## 4. How to interpret `dispatch_posture`

### 4.1 `ready_to_dispatch`

Meaning:

- current package is selected
- required delivery artifacts exist
- operator surface is not holding the package on review/NO_GO

Operator action:

- package is green on the current seam
- if a human still says “dispatch failed”, treat that as **outside current DB truth** and investigate the external send lane separately
- do not rewrite DB/operator state to invent a failure that is not recorded

### 4.2 `artifact_integrity_failed`

Meaning:

- one or more required files for dispatch are missing
- required set currently includes:
  - `delivery_manifest_path`
  - `send_manifest_path`
  - `review_manifest_path`
  - `workflow_manifest_path`
  - `delivery_zip_path`

Operator action:

1. inspect the missing files from `missing_required_artifacts`
2. open the package directory referenced by the selected handoff
3. if the package is incomplete, rebuild/publish again instead of manually stitching files together
4. only retry send after all required files are present

### 4.3 `switch_package`

Meaning:

- current package is not the selected dispatch candidate
- a different artifact won the dispatch decision

Operator action:

1. do **not** send the current package
2. switch to the package identified by `dispatch_selected_artifact_id`
3. use the selected handoff / manifest pointers from the status surface
4. if the selected package is absent, treat it as artifact-integrity recovery, not as “send failed”

### 4.4 `review_required`

Meaning:

- workflow recommends `send_review`, or operator review bundle says `REVIEW`
- manual review is required before dispatch

Operator action:

1. inspect:
   - `review_manifest_path`
   - `operator_review_bundle_path`
   - `operator_review_readme_path`
2. verify why the package is held
3. only promote to actual send if the review outcome is accepted
4. do not bypass the review gate by sending the zip directly

### 4.5 `hold`

Meaning:

- workflow/package/QA truth is blocking dispatch
- typical causes: send blockers, failed QA posture, blocked review items, recommended action hold

Operator action:

1. inspect `failure_reasons`
2. inspect `next_step`
3. inspect full MAIN status for QA and package state
4. fix the underlying package truth first; resend is not the first move

### 4.6 `no_active_artifact`

Meaning:

- there is no active MAIN delivery artifact for the requested date/slot resolution

Operator action:

- resolve the correct business date or rerun the publish path
- do not claim send failure when no active package exists

---

## 5. Triage checklist

Run these in order.

### Step 1 — get focused dispatch posture

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_send_dispatch_failure_status.py --latest
```

If you already know the date, use `--business-date`.

### Step 2 — read the classification

Focus on:

- `dispatch_posture`
- `failure_reasons`
- `missing_required_artifacts`
- `go_no_go_decision`
- `next_step`

### Step 3 — inspect package pointers

Open the exact files pointed to by:

- `delivery_manifest_path`
- `send_manifest_path`
- `review_manifest_path`
- `workflow_manifest_path`
- `operator_review_bundle_path`
- `operator_review_readme_path`
- `delivery_zip_path`

These are the truthful operator artifacts. Prefer them over memory or chat claims.

### Step 4 — decide the class of incident

#### Class A — package not selected

Indicators:

- `dispatch_posture=switch_package`
- `selected_is_current=False`
- `current_package_not_selected` in `failure_reasons`

Action:

- switch to the selected package
- do not resend the stale/current package

#### Class B — package incomplete

Indicators:

- `dispatch_posture=artifact_integrity_failed`
- non-empty `missing_required_artifacts`

Action:

- rebuild/publish the package
- do not hand-create missing manifests unless you are intentionally repairing code and rerunning tests

#### Class C — review-held

Indicators:

- `dispatch_posture=review_required`
- `manual_review_required` in `failure_reasons`
- `go_no_go_decision=REVIEW`

Action:

- complete operator review first
- send only after explicit review acceptance

#### Class D — workflow hold

Indicators:

- `dispatch_posture=hold`
- `recommended_action_hold` or other send blockers present

Action:

- move upstream to QA/package truth
- do not frame this as a transport/send incident

#### Class E — ready on seam, external failure claim

Indicators:

- `dispatch_posture=ready_to_dispatch`
- `channel_delivery_truth=unknown_not_modeled`

Action:

- current seam cannot prove downstream send failure or success
- investigate the external send lane separately
- do not mutate the report artifact state to fake a delivery receipt

---

## 6. Resend discipline

Before any resend attempt, confirm all are true:

- `dispatch_posture=ready_to_dispatch`
- `selected_is_current=True`
- `go_no_go_decision=GO`
- `missing_required_artifacts` is empty
- the resend target package is the selected package, not merely the most recent one in chat memory

If any of those are false, fix the package truth first.

---

## 7. Truthful escalation language

Use language like:

- “package is review-held; dispatch should not proceed yet”
- “current package is not the selected candidate; switch package first”
- “required delivery artifacts are missing; rebuild before resend”
- “operator seam is ready-to-dispatch, but downstream channel delivery is not modeled here”

Do **not** say:

- “Telegram delivery definitely failed” unless you have truth from outside this seam
- “report was sent successfully” based only on package existence
- “we can just resend this zip” when the selected package differs from current

---

## 8. Nearby verification

Canonical verification for this slice:

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest \
  tests/unit/test_fsj_send_dispatch_failure_status_script.py \
  tests/unit/test_fsj_main_delivery_status_script.py \
  -q
```

---

## 9. Thin operator summary

If dispatch looks broken, first answer this:

- is the package actually sendable on DB/operator truth?

Use:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_send_dispatch_failure_status.py --latest
```

Then act by posture:

- `ready_to_dispatch` → external send lane investigation
- `artifact_integrity_failed` → rebuild/recover package
- `switch_package` → send selected package, not current
- `review_required` → operator review first
- `hold` → fix QA/package truth first
- `no_active_artifact` → resolve/rerun publish path
