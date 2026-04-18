# Archive V2 Milestone 6 — Operator Observability / Broader Validation / Repair Policy Hardening

_Date: 2026-04-18 05:32 America/Los_Angeles_

## 1. Summary

Milestone 6 makes Archive V2 more production-operable.

This batch implemented:
- broader bounded replay/backfill validation across more already-implemented families
- stronger repair queue / retry policy surface
- operator-visible DB reporting surfaces
- an operator CLI for gap / backlog / run / family-health inspection
- better alignment between completeness truth, repair queue truth, and operator-facing visibility

This batch did **not** broaden into unrelated runtime work and did **not** make 60m / 15m / 1m the main scope.

---

## 2. Exact Milestone 6 scope implemented

### A. Broader bounded replay/backfill validation
Broader bounded validation now covers more already-implemented daily/final families, including:

#### Multi-day history/business-range validation (`2026-04-15 .. 2026-04-17`)
- `index_daily`
- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`

#### Broader mixed-family single-day validation (`2026-04-17`)
Tradable + business/final families:
- `equity_daily`
- `index_daily`
- `etf_daily`
- `non_equity_daily`
- `macro_daily`
- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `sector_performance_daily`

#### Selected highfreq daily/final validation (`2026-04-15`)
- `highfreq_event_stream_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

#### Broader bounded backfill validation
Backfill was validated over the broader history/business set, not just the tiny Milestone 5 sample.

### B. Repair queue / retry policy hardening
Repair queue is now materially richer for operators.

Added queue policy fields:
- `reason_code`
- `priority`
- `urgency`
- `retry_count`
- `first_seen_at`
- `last_attempt_at`
- `last_observed_status`
- `escalation_level`
- `last_error`

Added queue indexing:
- target identity unique index kept
- priority/next-retry index added for backlog-style operator reads

Policy behavior added:
- explicit reason-code inference (`source_empty`, `retry_needed`, `not_archive_worthy`, etc.)
- retry priority scoring
- urgency classification
- retry aging/escalation via `retry_count` + `escalation_level`
- throttled next retry scheduling via increasing `retry_after`
- legacy queue rows backfilled with operator-readable reason codes in the reporting layer / DDL migration step

### C. Operator-visible reporting surfaces
Added DB views:
- `ifa2.ifa_archive_operator_gap_summary_v`
- `ifa2.ifa_archive_operator_repair_backlog_v`
- `ifa2.ifa_archive_operator_recent_runs_v`
- `ifa2.ifa_archive_operator_family_health_v`
- `ifa2.ifa_archive_operator_date_health_v`

Added operator CLI:
- `scripts/archive_v2_operator_cli.py`

CLI commands:
- `summary`
- `gaps`
- `repair-backlog`
- `recent-runs`
- `family-health`
- `date-health`

These surfaces are DB-truth-based, not hand-maintained notes.

### D. Identity / completeness / reporting alignment
Milestone 5 identity/dedup policy was kept intact.
Milestone 6 aligned operator surfaces with that truth by ensuring:
- completeness drives gap visibility
- repair queue reflects queueable non-complete states
- recent runs summarize actual run-items
- reruns/backfills do not create contradictory operator signals

---

## 3. Code / schema / tooling changes

### 3.1 `src/ifa_data_platform/archive_v2/db.py`
Added / changed:
- repair queue columns for policy + observability
- operator-facing views for:
  - gaps
  - repair backlog
  - recent runs
  - family health
  - date health
- legacy repair queue metadata backfill for `reason_code` / `last_observed_status`

### 3.2 `src/ifa_data_platform/archive_v2/operator.py`
New module with:
- reason-code inference
- retry priority / urgency / escalation policy
- next-retry scheduling policy
- DB-backed reporting queries
- JSON serialization helpers for operator CLI

### 3.3 `src/ifa_data_platform/archive_v2/runner.py`
Changed:
- repair queue sync now computes policy state using the new operator/policy helper
- completeness `retry_after` is aligned to queue retry timing
- completed repairs now clear retry timing and mark queue rows `completed`

### 3.4 New CLI
- `scripts/archive_v2_operator_cli.py`

### 3.5 New validation profiles
- `profiles/archive_v2_milestone6_broad_range_history_write_sample.json`
- `profiles/archive_v2_milestone6_broad_backfill_write_sample.json`
- `profiles/archive_v2_milestone6_highfreq_selected_write_sample.json`
- `profiles/archive_v2_milestone6_broad_single_day_full_write_sample.json`
- `profiles/archive_v2_milestone6_incomplete_policy_sample.json`

### 3.6 Focused test
- `tests/integration/test_archive_v2_milestone6.py`

---

## 4. Broader bounded validation summary

### 4.1 Broader multi-day replay validation
Profile:
- `archive_v2_milestone6_broad_range_history_write_sample`

Observed direct run:
```json
{
  "ok": true,
  "run_id": "384e80e7-dfdf-4c05-902a-fcebc5c5d0f0",
  "status": "completed",
  "notes": "Archive V2 multi-date execution completed for the eligible requested scope; dates=3 executed_targets=24 skipped_targets=0 target_policy=all"
}
```

This is materially broader than Milestone 5:
- 8 already-implemented families
- 3 business dates
- 24 family/date targets

### 4.2 Broader mixed-family single-day validation
Profile:
- `archive_v2_milestone6_broad_single_day_full_write_sample`

Observed direct run:
```json
{
  "ok": true,
  "run_id": "a2dd684e-ff63-47d5-b538-b300cb11b5fe",
  "status": "completed",
  "notes": "Archive V2 multi-date execution completed for the eligible requested scope; dates=1 executed_targets=13 skipped_targets=0 target_policy=all"
}
```

This proves bounded replay across a broader tradable + business/final mixed set.

### 4.3 Selected highfreq validation
Highfreq source refresh run:
- `dff08601-2f41-4e3d-a41c-ab1bafefe1bf`
- `event_time_stream+derived_signal_state` succeeded with `410`

Archive V2 highfreq profile:
- `archive_v2_milestone6_highfreq_selected_write_sample`

Observed direct run:
```json
{
  "ok": true,
  "run_id": "a7c07e82-0307-4328-b5e7-a17a542a3fd2",
  "status": "completed",
  "notes": "Archive V2 multi-date execution completed for the eligible requested scope; dates=1 executed_targets=6 skipped_targets=0 target_policy=all"
}
```

### 4.4 Broader bounded backfill validation
Profile:
- `archive_v2_milestone6_broad_backfill_write_sample`

Observed recent run from focused validation:
- run id: `592bf2cf-96d1-47dd-917b-1420487852ca`
- status: `completed`
- notes: `dates=3 executed_targets=2 skipped_targets=22 target_policy=gaps`

This proves the broader bounded backfill path is still selective and state-aware at larger family coverage.

---

## 5. Repair queue / retry policy improvements

### 5.1 What changed operationally
Queue rows now answer much more of the operator question set:
- what needs repair
- why
- how urgent it is
- how many times it has been retried
- when it should retry next
- what status was last observed
- what the last error/reason was

### 5.2 Example: truthful unresolved item
To validate backlog policy, I intentionally used a truthful unresolved scenario:
- profile: `archive_v2_milestone6_incomplete_policy_sample`
- family: `sector_performance_daily`
- date: `2026-04-15`
- source truth: no rows available for that date

Repeated direct runs:
```json
{"run_id": "8cc693bd-23ec-4e96-ac45-7a7e3f171039", "status": "partial"}
{"run_id": "ef5d10f4-13d4-4603-9381-ffc38e21cc0f", "status": "partial"}
```

Resulting queue/backlog truth:
- `reason_code = source_empty`
- `priority = 73`
- `urgency = high`
- `retry_count = 4`
- `escalation_level = 2`
- `repair_status = pending`
- `completeness_status = incomplete`

This is materially better than the pre-Milestone-6 minimal queue.

### 5.3 Legacy/non-actionable backlog clarity
Preexisting intentional non-actionable item:
- `generic_structured_output_daily`
- now surfaces with:
  - `reason_code = not_archive_worthy`
  - `priority = 50`
  - `urgency = normal`

This makes the operator signal more coherent than a null/opaque backlog entry.

---

## 6. New operator/reporting surfaces

### 6.1 CLI examples
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py summary --days 14 --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py gaps --days 14
.venv/bin/python scripts/archive_v2_operator_cli.py repair-backlog --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py recent-runs --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py family-health --limit 20
.venv/bin/python scripts/archive_v2_operator_cli.py date-health --days 14
```

### 6.2 What operators can now answer directly
From DB truth, operators can now answer:
- which business dates are incomplete
- which families are incomplete on those dates
- which repair items are queued
- which retries are pending
- what recent archive-v2 runs did
- which families are healthy vs lagging
- which dates have non-complete coverage counts

### 6.3 Example operator summary output
Observed `summary` highlights:
- `incomplete_dates`: `2026-04-17`, `2026-04-15`
- `gap_item_count`: `3`
- `repair_backlog_count`: `2`
- `retry_due_count`: `1`

Observed date health:
- `2026-04-17` → `families_observed=14`, `completed_families=13`, `non_completed_families=1`
- `2026-04-16` → `families_observed=9`, `completed_families=9`, `non_completed_families=0`
- `2026-04-15` → `families_observed=16`, `completed_families=14`, `non_completed_families=2`

Observed lagging families excerpt:
- `highfreq_signal_daily` → `0%` completion, legacy placeholder
- `sector_performance_daily` → `66.67%` completion due truthful missing `2026-04-15`
- `generic_structured_output_daily` → `0%`, not archive-worthy by design

---

## 7. Validation commands used

### 7.1 Compile / syntax
```bash
.venv/bin/python -m py_compile \
  src/ifa_data_platform/archive_v2/db.py \
  src/ifa_data_platform/archive_v2/operator.py \
  src/ifa_data_platform/archive_v2/runner.py \
  scripts/archive_v2_operator_cli.py \
  tests/integration/test_archive_v2_milestone6.py
```

### 7.2 Focused tests
```bash
.venv/bin/pytest tests/integration/test_archive_v2_milestone6.py -q
```

Observed result:
- `3 passed in 61.41s`

### 7.3 Direct broader replay / highfreq / operator runs
```bash
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone6_broad_range_history_write_sample.json
.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane highfreq --owner-type default --owner-id default
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone6_broad_single_day_full_write_sample.json
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone6_highfreq_selected_write_sample.json
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone6_incomplete_policy_sample.json
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone6_incomplete_policy_sample.json
.venv/bin/python scripts/archive_v2_operator_cli.py summary --days 14 --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py repair-backlog --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py recent-runs --limit 10
```

---

## 8. DB / runtime evidence

### 8.1 Broader range archive row counts (`2026-04-15 .. 2026-04-17`)
Representative retained counts:

- `announcements_daily`
  - `2026-04-15` → `3961`
  - `2026-04-16` → `3036`
  - `2026-04-17` → `3834`
- `dragon_tiger_daily`
  - `2026-04-15` → `71`
  - `2026-04-16` → `59`
  - `2026-04-17` → `68`
- `index_daily`
  - `2026-04-15` → `8`
  - `2026-04-16` → `8`
  - `2026-04-17` → `8`
- `investor_qa_daily`
  - `2026-04-15` → `336`
  - `2026-04-16` → `167`
  - `2026-04-17` → `171`
- `limit_up_detail_daily`
  - `2026-04-15` → `7542`
  - `2026-04-16` → `7545`
  - `2026-04-17` → `7549`
- `limit_up_down_status_daily`
  - `2026-04-15` → `1`
  - `2026-04-16` → `1`
  - `2026-04-17` → `1`
- `news_daily`
  - `2026-04-15` → `1114`
  - `2026-04-16` → `2461`
  - `2026-04-17` → `1595`
- `research_reports_daily`
  - `2026-04-15` → `54`
  - `2026-04-16` → `54`
  - `2026-04-17` → `71`

### 8.2 Broader mixed-family single-day counts (`2026-04-17`)
- `equity_daily` → `5497`
- `etf_daily` → `1946`
- `non_equity_daily` → `1076`
- `macro_daily` → `3`
- `sector_performance_daily` → `394`

### 8.3 Selected highfreq retained counts (`2026-04-15`)
- `highfreq_event_stream_daily` → `183`
- `highfreq_limit_event_stream_daily` → `1`
- `highfreq_sector_breadth_daily` → `1`
- `highfreq_sector_heat_daily` → `1`
- `highfreq_leader_candidate_daily` → `1`
- `highfreq_intraday_signal_state_daily` → `1`

### 8.4 Recent-runs operator surface
Observed recent runs included:
- `archive_v2_milestone6_broad_range_history_write_sample` → `completed`, `item_count=24`
- `archive_v2_milestone6_broad_single_day_full_write_sample` → `completed`, `item_count=13`
- `archive_v2_milestone6_highfreq_selected_write_sample` → `completed`, `item_count=6`
- `archive_v2_milestone6_incomplete_policy_sample` → `partial`, `item_count=1`

### 8.5 Repair backlog operator surface
Observed backlog view:
- `sector_performance_daily @ 2026-04-15`
  - `reason_code=source_empty`
  - `priority=73`
  - `urgency=high`
  - `retry_count=4`
  - `escalation_level=2`
  - `repair_status=pending`
  - `completeness_status=incomplete`
- `generic_structured_output_daily @ 2026-04-15`
  - `reason_code=not_archive_worthy`
  - `priority=50`
  - `urgency=normal`
  - `repair_status=pending`
  - `completeness_status=incomplete`

This is a much clearer operator signal than Milestone 5.

---

## 9. Truthful judgment

### 9.1 What is now materially real
Milestone 6 makes Archive V2 materially more operable:
- broader bounded validation is real
- operator gap/backlog/run/health inspection is real
- repair queue policy is richer and more readable
- completeness, repair state, and operator outputs now tell a more coherent story

### 9.2 What is still not finished
Archive V2 is still not “finished forever.”
Remaining next-step work includes:
- richer queue actions / retry orchestration beyond policy surfacing
- operator suppression or separate classification for intentional non-actionable backlog items
- broader family coverage in operator-health policy decisions
- stronger immutable-key upgrades where better source-native IDs are available
- future 60m / 15m / 1m work if/when explicitly requested

---

## 10. What remains for the next milestone

Most natural next milestone work:
1. turn repair policy surface into stronger repair execution control:
   - queue picking
   - retry batching
   - operator-selectable repair scopes
2. separate actionable backlog from intentional/non-actionable backlog more explicitly
3. broaden operator summary/report surfaces for larger family sets and longer bounded windows
4. continue tightening source-native identity where practical
5. only after that, consider broader frequency-layer expansion if requested

---

## 11. Bottom line

Milestone 6 makes Archive V2 more trustworthy to operate:
- broader bounded runs prove it is not a tiny-sample-only system
- repair backlog is now prioritized and readable
- operators now have direct DB-backed visibility into gaps, backlog, recent runs, family health, and date health.
