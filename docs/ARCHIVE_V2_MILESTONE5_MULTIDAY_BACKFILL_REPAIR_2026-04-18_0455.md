# Archive V2 Milestone 5 — Multi-Day Replay / Backfill / Repair / Dedup Hardening

_Date: 2026-04-18 04:55 America/Los_Angeles_

## 1. Summary

Milestone 5 makes Archive V2 materially usable beyond one-day proof runs.

This batch implemented:
- real bounded `date_range` execution across multiple dates
- real bounded `backfill` execution driven by archive/completeness state
- real repair/retry behavior using `ifa_archive_completeness` + `ifa_archive_repair_queue`
- explicit finalized-row identity / dedup policy in code
- truthful multi-date run-item / completeness evolution
- rerun stability for already archived dates

This batch **did not** broaden into 1m / 15m / 60m archive scope.
It stayed focused on the daily/final families already implemented in Milestones 2–4.

---

## 2. Exact Milestone 5 scope implemented

### A. Multi-day `date_range` execution
`date_range` is now materially usable for implemented daily/final families:
- inclusive date expansion from `start_date` to `end_date`
- run-item logging per `(business_date, family)`
- completeness updates per `(business_date, family)`
- truthful partial/incomplete handling preserved
- reruns remain stable because family-specific identity/upsert policy is now explicit

### B. Bounded `backfill` execution
`backfill` is now materially usable:
- resolves a bounded recent candidate date set from locally available family source dates
- respects `backfill_days`
- uses archive/completeness state to find targets that are:
  - missing
  - incomplete
  - partial
  - retry_needed
- skips already completed targets instead of blindly rerunning everything
- records skipped-complete targets truthfully as `superseded` run items in backfill mode

### C. Repair / retry flow
Repair is now real enough to matter:
- `repair_incomplete=true` activates repair-target selection
- repair mode looks at:
  - `ifa_archive_completeness`
  - `ifa_archive_repair_queue`
- only non-complete / queued targets are executed
- once repaired successfully:
  - completeness becomes `completed`
  - queue rows become `completed`
- if a family/date remains non-complete:
  - it is auto-enqueued / kept pending in `ifa_archive_repair_queue`

### D. Finalized-row identity / dedup policy
Identity policy is now explicit in runner code via `IDENTITY_POLICY_BY_FAMILY`.
Run-item notes also now include the identity policy for executed families.

### E. Truthful multi-date behavior
The runner now distinguishes between execution policies:
- `all` → normal date-range execution
- `gaps` → bounded backfill for missing/non-complete targets only
- `repair` → repair/retry targeting queued or non-complete targets only

This keeps multi-date runs truthful instead of conflating:
- replay
- gap fill
- repair
- already-complete reruns

---

## 3. Code changes

### 3.1 `src/ifa_data_platform/archive_v2/runner.py`
Major Milestone 5 changes:
- added explicit target execution policies:
  - `all`
  - `gaps`
  - `repair`
- added bounded backfill date resolution from real local source-date availability
- added completeness-aware target selection
- added repair-queue-aware target selection
- added `superseded` run items for skipped-complete or skipped-nonrepair targets
- added explicit identity policy map
- added repair queue synchronization from completeness truth
- strengthened event row key generation as an explicit stable identity function
- added richer multi-date run notes (`dates`, `executed_targets`, `skipped_targets`, `target_policy`)

### 3.2 `src/ifa_data_platform/archive_v2/db.py`
Added:
- unique index for repair queue target identity:
  - `uq_ifa_archive_repair_queue_target`

This makes repair queue upsert behavior deterministic for:
- `(business_date, family_name, frequency, coverage_scope)`

### 3.3 New validation profiles
Added:
- `profiles/archive_v2_milestone5_range_write_sample.json`
- `profiles/archive_v2_milestone5_backfill_write_sample.json`
- `profiles/archive_v2_milestone5_repair_retry_sample.json`

### 3.4 Focused test
Added:
- `tests/integration/test_archive_v2_milestone5.py`

---

## 4. Multi-day / backfill / repair behavior now implemented

### 4.1 Multi-day `date_range`
Validated bounded profile:
- `archive_v2_milestone5_range_write_sample`
- date range: `2026-04-15` → `2026-04-17`
- families:
  - `index_daily`
  - `announcements_daily`
  - `news_daily`

Observed direct run:
```json
{
  "ok": true,
  "run_id": "c667aac8-7d14-49c4-9855-ac479c4db04d",
  "status": "completed",
  "notes": "Archive V2 multi-date execution completed for the eligible requested scope; dates=3 executed_targets=9 skipped_targets=0 target_policy=all"
}
```

This proves:
- multi-date looping is real
- per-date/per-family writes are real
- per-date/per-family completeness is real
- bounded multi-day replay works on implemented families

### 4.2 Bounded `backfill`
Validated bounded profile:
- `archive_v2_milestone5_backfill_write_sample`
- `backfill_days=3`
- anchor date: `2026-04-17`

Controlled validation setup:
- deleted archive rows for:
  - `index_daily @ 2026-04-16`
  - `news_daily @ 2026-04-16`
- deleted matching completeness rows

Observed direct run:
```json
{
  "ok": true,
  "run_id": "8a28f341-673d-4328-9c68-d63bd6fdaa76",
  "status": "completed",
  "notes": "Archive V2 multi-date execution completed for the eligible requested scope; dates=3 executed_targets=2 skipped_targets=7 target_policy=gaps"
}
```

This proves:
- backfill looked at existing state
- only missing/non-complete targets were executed
- already-complete targets were skipped truthfully
- bounded backfill is real, not placeholder

### 4.3 Repair / retry
Validated bounded repair profile:
- `archive_v2_milestone5_repair_retry_sample`
- date range: `2026-04-15` → `2026-04-16`
- families:
  - `highfreq_event_stream_daily`
  - `highfreq_sector_breadth_daily`
- `repair_incomplete=true`

Controlled validation setup:
- deleted archive rows for `2026-04-15` in the two target families
- forced completeness to:
  - `retry_needed` for `highfreq_event_stream_daily`
  - `partial` for `highfreq_sector_breadth_daily`
- inserted matching pending repair-queue rows

Observed first repair run:
```json
{
  "ok": true,
  "run_id": "ddae8322-6400-4aeb-a2af-c4f6f4e069a3",
  "status": "completed",
  "notes": "Archive V2 multi-date execution completed for the eligible requested scope; dates=2 executed_targets=2 skipped_targets=2 target_policy=repair"
}
```

Observed second repair run over the same profile:
```json
{
  "ok": true,
  "run_id": "63b1009c-ecfe-49d5-861e-0cfb6cd501de",
  "status": "completed",
  "notes": "Archive V2 multi-date execution completed for the eligible requested scope; dates=2 executed_targets=0 skipped_targets=4 target_policy=repair"
}
```

This proves:
- repair/retry flow is real
- queued/non-complete targets get executed
- once repaired, they stop being re-executed in repair mode
- rerun stability holds after repair completes

---

## 5. Finalized-row identity / dedup policy summary

Identity policy is now explicit in implementation.

### 5.1 Tradable daily snapshot families
- `equity_daily` → `(business_date, ts_code)`
- `index_daily` → `(business_date, ts_code)`
- `etf_daily` → `(business_date, ts_code)`
- `non_equity_daily` → `(business_date, family_code, ts_code)`
- `macro_daily` → `(business_date, macro_series)`

### 5.2 Business / event daily families
- `announcements_daily` → `(business_date, ts_code, title)`
- `news_daily` → `(business_date, news_time, title)`
- `research_reports_daily` → `(business_date, ts_code, title)`
- `investor_qa_daily` → `(business_date, ts_code, pub_time)`
- `dragon_tiger_daily` → `(business_date, ts_code)`
- `limit_up_detail_daily` → `(business_date, ts_code)`
- `limit_up_down_status_daily` → `(business_date)`
- `sector_performance_daily` → `(business_date, sector_code)`

### 5.3 Highfreq finalized families
- `highfreq_event_stream_daily`
  - `(business_date, row_key)`
  - `row_key = event_time|event_type|symbol|source|title`
- `highfreq_limit_event_stream_daily`
  - `(business_date, row_key)`
  - `row_key = trade_time|event_type|symbol|source|title`
- `highfreq_sector_breadth_daily` → `(business_date, sector_code)`
- `highfreq_sector_heat_daily` → `(business_date, sector_code)`
- `highfreq_leader_candidate_daily` → `(business_date, symbol)`
- `highfreq_intraday_signal_state_daily` → `(business_date, scope_key)`

### 5.4 Practical effect
Repeated runs now stay sane because:
- every finalized table has a stable target identity
- writes use upsert semantics on that identity
- backfill skips already-complete targets
- repair only re-executes queued/non-complete targets
- rerunning a completed repair profile becomes a no-op (`executed_targets=0`)

---

## 6. Validation commands used

### 6.1 Compile / syntax
```bash
.venv/bin/python -m py_compile \
  src/ifa_data_platform/archive_v2/db.py \
  src/ifa_data_platform/archive_v2/runner.py \
  tests/integration/test_archive_v2_milestone5.py
```

### 6.2 Focused integration tests
```bash
.venv/bin/pytest tests/integration/test_archive_v2_milestone5.py -q
```

Observed result:
- `3 passed in 68.17s`

### 6.3 Direct bounded date-range run
```bash
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone5_range_write_sample.json
```

### 6.4 Direct highfreq source refresh for repair validation
```bash
.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane highfreq --owner-type default --owner-id default
```

### 6.5 Direct bounded backfill run
```bash
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone5_backfill_write_sample.json
```

### 6.6 Direct repair/retry runs
```bash
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone5_repair_retry_sample.json
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone5_repair_retry_sample.json
```

---

## 7. DB / runtime evidence

### 7.1 Date-range run evidence
Run:
- `c667aac8-7d14-49c4-9855-ac479c4db04d`
- profile: `archive_v2_milestone5_range_write_sample`
- mode: `date_range`
- status: `completed`

Archive row counts after bounded range run:

`ifa_archive_index_daily`
- `2026-04-15` → `8`
- `2026-04-16` → `8`
- `2026-04-17` → `8`

`ifa_archive_announcements_daily`
- `2026-04-15` → `3961`
- `2026-04-16` → `3036`
- `2026-04-17` → `3834`

`ifa_archive_news_daily`
- `2026-04-15` → `1114`
- `2026-04-16` → `2461`
- `2026-04-17` → `1595`

### 7.2 Backfill evidence
Run:
- `8a28f341-673d-4328-9c68-d63bd6fdaa76`
- profile: `archive_v2_milestone5_backfill_write_sample`
- mode: `backfill`
- status: `completed`

Observed run-item behavior:
- repaired:
  - `index_daily @ 2026-04-16` → `completed`, `rows_written=16`
  - `news_daily @ 2026-04-16` → `completed`, `rows_written=36966`
- skipped as already complete (`superseded`):
  - all other family/date targets in the bounded 3-day window

This is exactly the expected bounded gap-fill behavior.

### 7.3 Repair/retry evidence
First repair run:
- `ddae8322-6400-4aeb-a2af-c4f6f4e069a3`
- status: `completed`
- executed:
  - `highfreq_event_stream_daily @ 2026-04-15` → `completed`, `rows_written=1400`
  - `highfreq_sector_breadth_daily @ 2026-04-15` → `completed`, `rows_written=1`
- skipped:
  - non-targeted `2026-04-16` rows as `superseded`

Second repair run:
- `63b1009c-ecfe-49d5-861e-0cfb6cd501de`
- status: `completed`
- executed targets: `0`
- skipped targets: `4`

This proves repair no-op stability after successful repair.

### 7.4 Completeness truth after Milestone 5 validation
Representative completeness rows:
- `2026-04-15` / `announcements_daily` → `completed`
- `2026-04-15` / `index_daily` → `completed`
- `2026-04-15` / `news_daily` → `completed`
- `2026-04-15` / `highfreq_event_stream_daily` → `completed`
- `2026-04-15` / `highfreq_sector_breadth_daily` → `completed`
- `2026-04-16` / `announcements_daily` → `completed`
- `2026-04-16` / `index_daily` → `completed`
- `2026-04-16` / `news_daily` → `completed`
- `2026-04-17` / `announcements_daily` → `completed`
- `2026-04-17` / `index_daily` → `completed`
- `2026-04-17` / `news_daily` → `completed`

### 7.5 Repair queue truth after Milestone 5 validation
For the forced repair scenario on `2026-04-15`:
- `highfreq_event_stream_daily` → queue status `completed`
- `highfreq_sector_breadth_daily` → queue status `completed`
- last run id on queue rows points to the successful repair run:
  - `ddae8322-6400-4aeb-a2af-c4f6f4e069a3`

### 7.6 Rerun stability evidence
After successful repair, rerunning the same repair profile did not re-execute completed targets.

Representative retained row count remained sane:
- `ifa_archive_highfreq_event_stream_daily @ 2026-04-15` → `183`

This shows the retained finalized truth did not explode with duplicates on rerun.

Important truthful note:
- event-family `rows_written` in run items reflects processed source rows during the run
- retained archive table counts can be lower because Archive V2 upserts into stable finalized identities instead of storing repeated same-day working duplicates

---

## 8. Truthful judgment

### 8.1 What is now materially real
Archive V2 is now materially usable for:
- bounded multi-day replay
- bounded state-aware backfill
- bounded repair/retry over prior incomplete targets
- rerun-stable finalized writes for implemented daily/final families

Milestone 5 is therefore real, not a placeholder.

### 8.2 What is still not finished
This batch does **not** mean Archive V2 is fully production-complete in every dimension.
Still unfinished / next-step scope:
- broader multi-family/date-range coverage validation beyond the bounded sample families used here
- stronger business-object identity for certain business families if source-native immutable IDs become available
- richer repair prioritization / retry scheduling policy beyond the current minimal truthful queue
- broader replay/backfill hardening for all implemented families across larger date windows
- any future 60m / 15m / 1m scope (still out of scope here)

---

## 9. What remains for the next milestone

Most natural next milestone work:
1. broaden bounded replay/backfill validation across more implemented families
2. harden repair queue operations into a fuller production policy surface:
   - retry priority
   - retry throttling
   - retry aging / escalation
3. strengthen family-specific identity policy where source-native immutable keys are better than current practical keys
4. add richer operator/reporting surfaces for archive-v2 gap state and repair state
5. then, only if desired, move carefully toward larger-range production backfill or new frequency layers

---

## 10. Bottom line

Milestone 5 makes Archive V2 **operationally usable across multiple dates**:
- date-range replay is real
- bounded backfill is real
- repair/retry is real
- reruns stay sane because finalized-row identity is explicit and enforced through upsert + queue/completeness-aware targeting.
