# Archive V2 Milestone 7 — Repair Execution Control / Batching / Actionable Backlog Separation

_Date: 2026-04-18 05:59 America/Los_Angeles_

## 1. Summary

Milestone 7 turns Archive V2 repair/backfill from visible into genuinely actionable.

This batch implemented:
- real queue-picking / repair execution control
- bounded retry batching
- operator-selectable repair scopes
- clearer actionable vs non-actionable backlog separation
- operator repair commands for repair execution, not just inspection
- continued alignment between repair queue, completeness truth, and run evidence

This batch did **not** broaden into unrelated runtime work and did **not** make `60m / 15m / 1m` the main scope.

---

## 2. Exact Milestone 7 scope implemented

### A. Queue-picking / repair execution control
Archive V2 can now:
- select repair targets directly from the repair queue / operator backlog surface
- order them by actionable-first, then priority, then retry timing, then recency
- execute a bounded repair batch through an operator CLI command
- update queue/completeness/run truth based on the repair outcome

This is no longer just "inspect queue, then hand-edit a broad profile and rerun".

### B. Retry batching / bounded repair execution
Implemented bounded repair execution behavior via operator CLI filters such as:
- `--limit N`
- `--business-date YYYY-MM-DD`
- `--start-date / --end-date`
- `--family <family>` (repeatable)
- `--status <repair_status>`
- `--urgency <urgency>`
- `--min-priority <n>`
- `--retry-due-only`

This makes repair work intentionally batchable rather than broad rerun guessing.

### C. Operator-selectable repair scopes
Operators can now choose repair scope by:
- one business date
- one family or several families
- one date range
- one status subset
- one urgency subset
- minimum priority threshold
- retry-due-only
- default actionable-only behavior
- optional inclusion of non-actionable backlog

### D. Actionable vs non-actionable backlog separation
This batch added explicit actionability classification.

Backlog is now separated between:
- **actionable**
  - examples: `retry_needed`, missing archive coverage for archive-worthy families, partial/incomplete retryable items
- **non_actionable**
  - examples: `generic_structured_output_daily`, `highfreq_signal_daily`, `not_archive_worthy`, legacy placeholder families

This distinction now affects:
- queue state (`actionability` column)
- operator reports / views
- repair selection defaults

### E. Better operator repair commands / reporting
Extended operator CLI:
- `summary`
- `gaps`
- `repair-backlog`
- `recent-runs`
- `family-health`
- `date-health`
- `actionable-backlog`
- `nonactionable-backlog`
- `repair-batch`

`repair-batch` supports:
- dry-run selection preview
- actual bounded repair execution
- operator-controlled scope filters
- actionability-aware default selection

### F. Continued alignment with completeness truth
Milestone 7 keeps the Milestone 5/6 identity + completeness logic intact and aligns repair execution with it:
- completed repair batch items clear retry timing and mark queue rows `completed`
- still-unresolved items remain `pending` with retry metadata
- run evidence is written via normal archive run / run-items tables
- operator repair runs are explicitly tagged as `trigger_source='operator_repair_batch'`

---

## 3. Code / schema / tooling changes

### 3.1 `src/ifa_data_platform/archive_v2/db.py`
Added / changed:
- repair queue column:
  - `actionability`
- operator views now surface:
  - `actionability`
  - `actionability_sort`
- legacy queue normalization now backfills:
  - `reason_code`
  - `actionability`
  - `last_observed_status`
- operator views are dropped/recreated cleanly so shape changes are safe

### 3.2 `src/ifa_data_platform/archive_v2/operator.py`
Added / changed:
- reason-code inference now considers family-specific intentional backlog
- explicit `classify_actionability(...)`
- queue policy now returns `actionability`
- actionable/non-actionable backlog accessors
- repair-target selector with scope filters and ordering
- repair-batch note builder for operator-visible execution context

### 3.3 `src/ifa_data_platform/archive_v2/runner.py`
Added / changed:
- `run_selected_targets(...)` for operator-triggered bounded repair execution
- repair queue sync now persists `actionability`
- operator repair runs create normal archive run / run-item evidence
- completed repairs resolve queue rows cleanly while preserving coherent state

### 3.4 `scripts/archive_v2_operator_cli.py`
Extended with:
- `actionable-backlog`
- `nonactionable-backlog`
- `repair-batch`

### 3.5 New operator repair executor profile
Added:
- `profiles/archive_v2_milestone7_repair_executor.json`

### 3.6 Focused test
Added:
- `tests/integration/test_archive_v2_milestone7.py`

---

## 4. Queue-picking / repair execution control changes

### 4.1 Repair target ordering
Repair selection now orders targets by:
1. actionable backlog before non-actionable backlog
2. higher priority first
3. earlier `retry_after` first
4. older `updated_at` first
5. stable date/family ordering afterward

This gives real queue-picking behavior instead of ad hoc rerun choice.

### 4.2 Repair execution command
Actual operator repair command:
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch ...
```

The command:
- selects targets from DB truth
- can dry-run preview selection
- can execute a bounded repair batch
- records run evidence in `ifa_archive_runs`
- records family/date execution in `ifa_archive_run_items`
- updates completeness + repair queue rows

### 4.3 Repair execution run identity
Repair batches now create explicit Archive V2 runs with:
- `profile_name = archive_v2_milestone7_repair_executor`
- `trigger_source = operator_repair_batch`

This makes operator-triggered recovery work auditable and distinct from generic profile runs.

---

## 5. Retry batching behavior

### 5.1 Bounded repair selection examples
Supported batching patterns now include:
- top `N` repair targets
- one business date
- one date range
- one family or several families
- only retry-due items
- min-priority subset
- urgency subset
- default actionable-only subset

### 5.2 Direct bounded batch proof
I seeded two actionable repair targets:
- `index_daily @ 2026-04-16` with `priority=95`, `urgency=critical`
- `research_reports_daily @ 2026-04-17` with `priority=70`, `urgency=normal`

Then ran:
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py \
  repair-batch --limit 1 --retry-due-only \
  --family index_daily --family research_reports_daily
```

Observed direct result:
```json
{
  "run_id": "6ecff065-6c41-4b90-8503-898c9db9f290",
  "status": "completed",
  "selected_count": 1,
  "selected_targets": 1,
  "target": "index_daily @ 2026-04-16"
}
```

This proves:
- queue picking honors policy ordering
- bounded limit execution works
- only one target was selected/repaired
- the lower-priority target remained pending until separately selected

### 5.3 Direct scoped family/date repair proof
Then ran:
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py \
  repair-batch --business-date 2026-04-17 \
  --family research_reports_daily --limit 5
```

Observed direct result:
```json
{
  "run_id": "53229960-00c9-4f6d-8d6c-ae0f5f829760",
  "status": "completed",
  "selected_count": 1,
  "selected_targets": 1,
  "target": "research_reports_daily @ 2026-04-17"
}
```

This proves:
- operator-selectable repair scope is real
- family/date filtering works
- repair can be intentional and narrow, not broad rerun guessing

---

## 6. Actionable vs non-actionable backlog separation

### 6.1 What changed
Backlog now clearly separates:
- **actionable backlog**
- **non_actionable backlog**

This is visible in:
- queue rows (`actionability`)
- operator backlog views
- operator CLI commands
- repair-batch default selection logic

### 6.2 Direct operator evidence
Observed actionable backlog excerpt:
- `sector_performance_daily @ 2026-04-15`
  - `reason_code=source_empty`
  - `actionability=actionable`
  - `priority=77`
  - `urgency=critical`
  - `retry_count=6`

Observed non-actionable backlog excerpt:
- `generic_structured_output_daily @ 2026-04-15`
  - `reason_code=not_archive_worthy`
  - `actionability=non_actionable`
  - `priority=50`
  - `urgency=deferred`

### 6.3 Practical effect on repair selection
Default repair-batch selection now excludes non-actionable backlog.
So `generic_structured_output_daily` no longer surfaces like a normal repair target in the default operator repair path.

---

## 7. Better operator repair commands / reporting

### 7.1 New commands
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py actionable-backlog --limit 20
.venv/bin/python scripts/archive_v2_operator_cli.py nonactionable-backlog --limit 20
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch --limit 10 --dry-run
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch --business-date 2026-04-17 --family research_reports_daily
```

### 7.2 What operators can do now
Operators can now:
- preview actionable repair targets
- inspect intentional/non-actionable backlog separately
- run bounded repair batches by scope
- see which targets were selected in a repair execution
- inspect repair execution results via recent runs and run items

### 7.3 Example operator-visible repair execution evidence
Recent runs now show explicit operator repair executions:
- `6ecff065-6c41-4b90-8503-898c9db9f290`
  - `profile_name=archive_v2_milestone7_repair_executor`
  - `trigger_source=operator_repair_batch`
  - `item_count=1`
  - `completed_items=1`
- `53229960-00c9-4f6d-8d6c-ae0f5f829760`
  - same repair-executor profile
  - same operator repair trigger path
  - `item_count=1`
  - `completed_items=1`

---

## 8. Validation commands used

### 8.1 Compile / syntax
```bash
.venv/bin/python -m py_compile \
  src/ifa_data_platform/archive_v2/db.py \
  src/ifa_data_platform/archive_v2/operator.py \
  src/ifa_data_platform/archive_v2/runner.py \
  scripts/archive_v2_operator_cli.py \
  tests/integration/test_archive_v2_milestone7.py
```

### 8.2 Focused tests
```bash
.venv/bin/pytest tests/integration/test_archive_v2_milestone7.py -q
```

Observed result:
- `3 passed in 50.99s`

### 8.3 Direct repair-batch validation commands
```bash
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone6_broad_range_history_write_sample.json
.venv/bin/python scripts/archive_v2_operator_cli.py actionable-backlog --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py nonactionable-backlog --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch --limit 1 --retry-due-only --family index_daily --family research_reports_daily
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch --business-date 2026-04-17 --family research_reports_daily --limit 5
.venv/bin/python scripts/archive_v2_operator_cli.py summary --days 14 --limit 10
```

---

## 9. DB / runtime evidence

### 9.1 Repair queue evidence after bounded repair execution
Observed queue rows:
- `index_daily @ 2026-04-16`
  - `status=completed`
  - `actionability=actionable`
  - `priority=95`
  - `urgency=low`
  - `reason_code=resolved`
  - `last_run_id=6ecff065-6c41-4b90-8503-898c9db9f290`
- `research_reports_daily @ 2026-04-17`
  - `status=completed`
  - `actionability=actionable`
  - `priority=70`
  - `urgency=low`
  - `reason_code=resolved`
  - `last_run_id=53229960-00c9-4f6d-8d6c-ae0f5f829760`
- `sector_performance_daily @ 2026-04-15`
  - `status=pending`
  - `actionability=actionable`
  - `reason_code=source_empty`
- `generic_structured_output_daily @ 2026-04-15`
  - `status=pending`
  - `actionability=non_actionable`
  - `reason_code=not_archive_worthy`

### 9.2 Completeness evidence after repair batch
Observed completeness rows:
- `index_daily @ 2026-04-16`
  - `status=completed`
  - `row_count=16`
  - `retry_after=null`
  - `last_run_id=6ecff065-6c41-4b90-8503-898c9db9f290`
- `research_reports_daily @ 2026-04-17`
  - `status=completed`
  - `row_count=71`
  - `retry_after=null`
  - `last_run_id=53229960-00c9-4f6d-8d6c-ae0f5f829760`
- `sector_performance_daily @ 2026-04-15`
  - `status=incomplete`
  - `retry_after` still populated
  - actionable backlog remains truthful
- `generic_structured_output_daily @ 2026-04-15`
  - `status=incomplete`
  - remains non-actionable backlog

### 9.3 Repair batch run-item evidence
Observed run items:
- run `6ecff065-6c41-4b90-8503-898c9db9f290`
  - `index_daily @ 2026-04-16`
  - `status=completed`
  - `rows_written=16`
  - note includes repair-batch selection context:
    - `priority=95`
    - `urgency=critical`
    - `actionability=actionable`
    - `reason_code=retry_needed`
- run `53229960-00c9-4f6d-8d6c-ae0f5f829760`
  - `research_reports_daily @ 2026-04-17`
  - `status=completed`
  - `rows_written=71`
  - note includes repair-batch selection context

### 9.4 Operator summary alignment
Observed operator summary:
- `repair_backlog_count = 2`
- `actionable_backlog_count = 1`
- `non_actionable_backlog_count = 1`

This is the intended coherent story:
- one real actionable unresolved item (`sector_performance_daily`)
- one intentional non-actionable backlog item (`generic_structured_output_daily`)
- repaired items no longer pollute actionable backlog

---

## 10. Truthful judgment

### 10.1 What is now materially real
Milestone 7 makes Archive V2 repair work materially operator-controllable:
- queue selection is real
- bounded repair batching is real
- scope-filtered repair execution is real
- actionable vs non-actionable backlog separation is real
- repair execution leaves auditable run/completeness/queue evidence

### 10.2 What is still not finished
Archive V2 repair is now controlled, but not yet fully “ops platform complete.”
Still unfinished / next-step scope includes:
- richer repair-batch orchestration policies across larger queues
- batch reservation / concurrency-safe claim semantics if multiple operators/processes exist later
- richer suppression/acknowledgement flows for non-actionable backlog
- stronger family-specific repair heuristics where source behavior differs materially
- any future `60m / 15m / 1m` expansion if explicitly requested later

---

## 11. What remains for the next milestone

Most natural next milestone work:
1. make repair execution more orchestration-aware:
   - queue claiming / reservation
   - safer batch concurrency semantics
   - richer retry scheduling controls
2. add stronger operator acknowledgement / suppression controls for non-actionable backlog
3. broaden repair-batch reporting/history surfaces
4. continue tightening family-specific repair semantics where source behavior warrants it
5. only after that, consider larger frequency-layer expansion if requested

---

## 12. Bottom line

Milestone 7 turns Archive V2 repair from “visible and policy-rich” into **actually controllable**:
- operators can pick bounded repair batches intentionally
- queue policy affects execution selection in a real way
- actionable backlog is separated from intentional/non-actionable backlog
- repair work now leaves a clean, coherent audit trail in queue state, completeness state, and archive run evidence.
