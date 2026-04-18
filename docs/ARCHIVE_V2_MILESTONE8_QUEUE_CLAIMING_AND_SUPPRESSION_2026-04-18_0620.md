# Archive V2 Milestone 8 — Queue Claiming / Safer Repair Coordination / Suppression Controls

_Date: 2026-04-18 06:20 America/Los_Angeles_

## 1. Summary

Milestone 8 makes Archive V2 repair execution safer and cleaner under repeated operator actions and future multi-run use.

This batch implemented:
- real queue claiming / reservation semantics
- safer concurrency-aware bounded repair execution
- acknowledgement / suppression controls for intentional backlog
- richer repair history / claimed/suppressed reporting surfaces
- continued alignment between queue, completeness, run evidence, and operator views

This batch did **not** broaden into unrelated runtime work and did **not** make `60m / 15m / 1m` the main scope.

---

## 2. Exact Milestone 8 scope implemented

### A. Queue claiming / reservation semantics
Archive V2 now has a practical first-pass claim/lease model for repair queue targets.

Added queue fields:
- `claim_id`
- `claimed_at`
- `claimed_by`
- `claim_expires_at`

Behavior now implemented:
- repair targets can be claimed before execution
- claims are DB-visible
- target selection excludes actively claimed rows by default
- expired claims are claimable again
- successful repair clears claim fields and resolves queue state
- explicit release is supported for claimed rows

### B. Safer concurrency-aware repair batch behavior
Repair-batch execution now behaves more safely under repeated operator actions:
- claim selection uses `FOR UPDATE SKIP LOCKED`
- already-claimed active rows are not trivially double-selected
- claim expiry makes stale claims reopenable
- completed repair clears claims instead of leaving stale reservation state
- release command can manually return claims to pending state

This is not a full distributed scheduler, but it is a realistic production-safe first step.

### C. Operator acknowledgement / suppression controls
Intentional backlog is now operator-acknowledgeable and suppressible.

Added queue fields:
- `suppression_state`
- `acknowledged_at`
- `acknowledged_by`
- `acknowledgement_reason`
- `suppressed_until`

New operator behavior:
- non-actionable backlog can be acknowledged/suppressed
- suppressed backlog stays truthful in dedicated views
- suppressed backlog is excluded from default actionable repair selection
- operators can unsuppress backlog later

### D. Richer repair history / reporting surfaces
Added / extended operator-visible surfaces for:
- currently claimed targets
- suppressed backlog
- repair execution history
- actionable backlog after suppression
- recent repair executions through explicit run history

### E. Continued coherence with queue / completeness / run evidence
Milestone 8 keeps Archive V2 coherent by ensuring:
- claims live in queue truth
- repair execution still writes normal archive run / run-item evidence
- completeness is updated by actual repair execution outcome
- operator views reflect suppression + claim state consistently

---

## 3. Code / schema / tooling changes

### 3.1 `src/ifa_data_platform/archive_v2/db.py`
Added / changed:
- repair queue claim columns
- repair queue suppression/ack columns
- indexes for claim and suppression lookup
- operator views enriched with:
  - `claim_id`
  - `claimed_at`
  - `claimed_by`
  - `claim_expires_at`
  - `claim_state`
  - `suppression_state`
  - `suppression_active`
  - acknowledgement metadata
- new views:
  - `ifa_archive_operator_claimed_backlog_v`
  - `ifa_archive_operator_suppressed_backlog_v`
  - `ifa_archive_operator_repair_execution_history_v`

### 3.2 `src/ifa_data_platform/archive_v2/operator.py`
Added / changed:
- claim-aware target selection
- queue claiming with lease id / claimed_by / lease expiry
- claimed target loader
- claim release function
- acknowledgement / suppression functions
- claimed backlog / suppressed backlog / repair history reporting
- default actionable backlog and repair selection now exclude suppressed/non-actionable items unless explicitly requested

### 3.3 `src/ifa_data_platform/archive_v2/runner.py`
Added / changed:
- repair queue sync now clears claim fields on complete
- incomplete/pending requeue path clears stale claim fields
- existing `run_selected_targets(...)` continues to provide auditable repair execution runs

### 3.4 `scripts/archive_v2_operator_cli.py`
New / extended commands:
- `claimed-backlog`
- `repair-history`
- `suppressed-backlog`
- `acknowledge-backlog`
- `unsuppress-backlog`
- `release-claims`
- enhanced `repair-batch` with:
  - `--claim-only`
  - `--claim-id`
  - `--claimed-by`
  - `--lease-minutes`
  - scope filters preserved from Milestone 7

### 3.5 Focused test
Added:
- `tests/integration/test_archive_v2_milestone8.py`

---

## 4. Queue claiming / reservation model

### 4.1 Claim model
Claim lifecycle in this batch:
1. operator requests repair-batch with normal filters
2. queue rows are selected and **claimed first**
3. claim metadata is stored in DB
4. execution runs against claimed targets
5. on success:
   - queue row becomes `completed`
   - claim fields are cleared
6. on manual release:
   - claimed row returns to `pending`
   - claim fields are cleared
7. on stale claims:
   - expired claims become claimable again

### 4.2 Claiming command shapes
Claim only:
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py \
  repair-batch --claim-only --family dragon_tiger_daily --business-date 2026-04-17
```

Execute an existing claim:
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py \
  repair-batch --claim-id <uuid> --claimed-by <name>
```

Release an existing claim:
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py \
  release-claims --claim-id <uuid> --released-by <name>
```

### 4.3 Why this matters
This reduces easy double-pick behavior because the queue now has a real reservation layer, not just a best-effort selection query.

---

## 5. Concurrency-safety behavior

### 5.1 What improved
Repair selection now has a safer first-pass concurrency story:
- active claims are excluded from default repair selection
- claims use `FOR UPDATE SKIP LOCKED`
- expired claims can be reclaimed
- release path exists for manual cleanup
- execution clears claim fields on resolution

### 5.2 What this does **not** claim yet
This is **not** a perfect distributed scheduler.
Still not in scope yet:
- durable worker heartbeats
- hard claim renewal semantics
- full multi-run reservation arbitration across many workers
- operator/automation queue claiming policies with stronger fairness controls

But it is materially safer than Milestone 7.

---

## 6. Acknowledgement / suppression behavior

### 6.1 What changed
Operators can now explicitly quiet known non-actionable backlog while preserving truth.

Examples:
- `generic_structured_output_daily`
- `highfreq_signal_daily`
- known intentionally deferred backlog

### 6.2 Behavior
- suppressed/acknowledged items remain visible in dedicated reporting
- they are excluded from default actionable repair surfaces
- they no longer pollute the main “repair me now” path
- they can be unsuppressed later

### 6.3 Example command
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py \
  acknowledge-backlog \
  --business-date 2026-04-15 \
  --family generic_structured_output_daily \
  --reason "known intentional non-actionable backlog" \
  --acknowledged-by milestone8_direct \
  --suppress-hours 24
```

---

## 7. New operator/reporting surfaces

### 7.1 New CLI/report surfaces
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py claimed-backlog --limit 20
.venv/bin/python scripts/archive_v2_operator_cli.py suppressed-backlog --limit 20
.venv/bin/python scripts/archive_v2_operator_cli.py repair-history --limit 20
.venv/bin/python scripts/archive_v2_operator_cli.py acknowledge-backlog ...
.venv/bin/python scripts/archive_v2_operator_cli.py unsuppress-backlog ...
.venv/bin/python scripts/archive_v2_operator_cli.py release-claims --claim-id <uuid>
```

### 7.2 Questions operators can now answer
Operators can now answer:
- which repair targets are currently claimed
- who claimed them
- when those claims expire
- which repair executions completed recently
- which backlog items are suppressed/acknowledged
- what the actionable backlog is after suppression

---

## 8. Validation commands used

### 8.1 Compile / syntax
```bash
.venv/bin/python -m py_compile \
  src/ifa_data_platform/archive_v2/db.py \
  src/ifa_data_platform/archive_v2/operator.py \
  src/ifa_data_platform/archive_v2/runner.py \
  scripts/archive_v2_operator_cli.py \
  tests/integration/test_archive_v2_milestone8.py
```

### 8.2 Focused tests
```bash
.venv/bin/pytest tests/integration/test_archive_v2_milestone8.py -q
```

Observed result:
- `3 passed in 52.48s`

### 8.3 Direct operator validation commands
Representative direct commands used:
```bash
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone6_broad_range_history_write_sample.json
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch --claim-only --limit 1 --retry-due-only --family index_daily --family research_reports_daily --claimed-by milestone8_direct
.venv/bin/python scripts/archive_v2_operator_cli.py claimed-backlog --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch --claim-id <actual-claim-id> --claimed-by milestone8_direct
.venv/bin/python scripts/archive_v2_operator_cli.py acknowledge-backlog --business-date 2026-04-15 --family generic_structured_output_daily --reason "known intentional non-actionable backlog" --acknowledged-by milestone8_direct --suppress-hours 24
.venv/bin/python scripts/archive_v2_operator_cli.py suppressed-backlog --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py repair-history --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py summary --days 14 --limit 10
```

---

## 9. DB / runtime evidence

### 9.1 Clean claim-only / claimed-backlog / release proof
Direct claim-only demo:
- claim id: `80e08810-86c1-4c38-8f94-9e324c22f767`
- claimed by: `milestone8_claim_demo`
- target: `dragon_tiger_daily @ 2026-04-17`

Claimed backlog immediately showed:
- `repair_status = claimed`
- `claim_id = 80e08810-86c1-4c38-8f94-9e324c22f767`
- `claimed_by = milestone8_claim_demo`
- `claim_state = active`
- `claim_expires_at = 2026-04-18 06:32:10-07`

Manual release then returned it to:
- `status = pending`
- claim fields cleared

This proves reservation semantics are real and DB-visible.

### 9.2 Claim + execute proof
Direct actionable repair batch:
- claim selected the higher-priority target first (`index_daily @ 2026-04-16`)
- execution run id: `83322ce6-2816-4d9c-9024-a6f6d2124fa7`
- `trigger_source = operator_repair_batch`
- run item:
  - `family_name = index_daily`
  - `business_date = 2026-04-16`
  - `status = completed`
  - `rows_written = 16`

After execution:
- queue row became `completed`
- claim fields were cleared
- completeness row became `completed`
- `retry_after = null`

### 9.3 Suppression/acknowledgement proof
After acknowledgement/suppression:
- `generic_structured_output_daily @ 2026-04-15`
  - `actionability = non_actionable`
  - `suppression_state = suppressed`
  - `suppressed_until = 2026-04-19 06:16:15-07`
  - `acknowledged_by = milestone8_direct`
  - `acknowledgement_reason = known intentional non-actionable backlog`

Suppressed backlog view shows it.
Default actionable repair surfaces do not include it.

### 9.4 Repair history surface
Recent repair history includes explicit operator repair executions such as:
- `83322ce6-2816-4d9c-9024-a6f6d2124fa7`
  - `trigger_source = operator_repair_batch`
  - `family_name = index_daily`
  - `business_date = 2026-04-16`
  - `item_status = completed`
- older Milestone 7 repair runs continue to appear in repair history as expected

### 9.5 Coherent summary surface after suppression
Observed summary highlights:
- `repair_backlog_count = 2`
- `actionable_backlog_count = 2`
- `non_actionable_backlog_count = 1`
- `suppressed_backlog_count = 1`
- `claimed_backlog_count = 0`

The important coherence point:
- suppressed non-actionable backlog remains visible in dedicated surfaces
- it does not pollute the default actionable repair path
- currently claimed work is shown separately

---

## 10. Truthful judgment

### 10.1 What is now materially real
Milestone 8 makes Archive V2 repair execution materially safer and cleaner:
- queue reservation is real
- claim/release semantics are real
- claimed backlog is DB-visible
- default repair selection avoids active claims
- suppression/acknowledgement of intentional backlog is real
- repair history/reporting surfaces are richer and operator-usable

### 10.2 What is still not finished
This is still not a full-blown distributed repair scheduler.
Still unfinished / next-step scope includes:
- stronger claim renewal / heartbeat semantics
- explicit worker identity and richer automation lifecycle
- batch reservation fairness / larger queue orchestration policies
- richer suppression lifecycle controls (e.g. persistent policy/notes/escalation)
- family-specific repair heuristics where source behavior differs materially

---

## 11. What remains for the next milestone

Most natural next milestone work:
1. stronger queue claiming orchestration:
   - lease renewal / expiry handling
   - safer automation hooks
   - better multi-worker coordination
2. richer backlog lifecycle management:
   - persistent acknowledgement/suppression policies
   - operator notes / reason maintenance
3. stronger repair execution reporting:
   - grouped batch summaries
   - claim lifecycle summaries
   - failed/expired claim analytics
4. continue tightening family-specific repair heuristics where useful
5. only after that, consider broader frequency-layer expansion if explicitly requested

---

## 12. Bottom line

Milestone 8 makes Archive V2 repair execution **safer under repeated operator use**:
- targets can be claimed before repair
- claimed work is visible and not trivially double-picked
- claims can be released or resolved cleanly
- intentional backlog can be acknowledged/suppressed without losing truth
- operators now have clearer repair history and cleaner actionable backlog surfaces.
