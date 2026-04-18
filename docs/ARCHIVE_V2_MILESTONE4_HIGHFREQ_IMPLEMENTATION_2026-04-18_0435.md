# Archive V2 Milestone 4 — Highfreq / Structured-Output Expansion

_Date: 2026-04-18 04:35 America/Los_Angeles_

## 1. Summary

This batch moves Archive V2 into the next real highfreq/structured-output expansion lane.

Implemented in this round:
- real Archive V2 destinations for selected highfreq families
- family-level writer logic in `archive_v2/runner.py`
- run-item logging and completeness updates for those families
- direct validation via:
  - focused integration tests
  - real highfreq runtime run
  - real Archive V2 profile run against Postgres

Truthful judgment for this batch:
- **implemented as archive-worthy**
  - `highfreq_event_stream_daily`
  - `highfreq_limit_event_stream_daily`
  - `highfreq_sector_breadth_daily`
  - `highfreq_sector_heat_daily`
  - `highfreq_leader_candidate_daily`
  - `highfreq_intraday_signal_state_daily`
- **explicitly not implemented as Archive V2**
  - `generic_structured_output_daily`
    - reason: generic catch-all structured output is too semantically lossy for Archive V2 finalized truth
- **legacy placeholder not used as the Milestone 4 durable model**
  - `highfreq_signal_daily`
    - reason: Milestone 4 now lands explicit durable families instead of one vague umbrella family

---

## 2. Milestone 4 scope implemented

### 2.1 Implemented families and chosen durable semantics

#### A. `highfreq_event_stream_daily`
Durable representation:
- **event stream semantics**
- retain finalized same-day event rows in `ifa2.ifa_archive_highfreq_event_stream_daily`
- identity stored as `(business_date, row_key)`
- payload retains original source row

Rationale:
- this family is event-like, not latest-snapshot-like
- collapsing it into one daily blob would destroy useful time-order semantics

#### B. `highfreq_limit_event_stream_daily`
Durable representation:
- **event stream semantics**
- retain finalized same-day limit-event rows in `ifa2.ifa_archive_highfreq_limit_event_stream_daily`

Rationale:
- same reasoning as event stream
- events are meaningful end-of-day retained truth when deduped by stable event identity

#### C. `highfreq_sector_breadth_daily`
Durable representation:
- **daily finalized snapshot semantics**
- latest row per `(business_date, sector_code)` retained in `ifa2.ifa_archive_highfreq_sector_breadth_daily`
- payload keeps the source row, plus `snapshot_time`

Rationale:
- breadth is a state/snapshot object, not something that needs full intraday retention in Archive V2 for this first pass
- latest-per-sector is the practical finalized daily truth

#### D. `highfreq_sector_heat_daily`
Durable representation:
- **daily finalized snapshot semantics**
- latest row per `(business_date, sector_code)` retained in `ifa2.ifa_archive_highfreq_sector_heat_daily`

#### E. `highfreq_leader_candidate_daily`
Durable representation:
- **summarized signal semantics / latest state per symbol**
- latest row per `(business_date, symbol)` retained in `ifa2.ifa_archive_highfreq_leader_candidate_daily`

Rationale:
- archive-worthy if treated as the final same-day candidate state, not as every transient intermediate working row

#### F. `highfreq_intraday_signal_state_daily`
Durable representation:
- **daily finalized market state snapshot**
- latest row per `(business_date, scope_key)` retained in `ifa2.ifa_archive_highfreq_intraday_signal_state_daily`

Rationale:
- stable enough as a finalized state object
- not useful to archive as raw working churn for this milestone

---

## 3. Intentionally not implemented and why

### 3.1 `generic_structured_output_daily`
Status:
- **intentionally marked incomplete**

Why:
- Archive V2 is a finalized truth layer, not a generic dumping ground
- a catch-all structured-output table collapses unrelated semantics into one bucket
- this violates the accepted Archive V2 direction of family-specific finalized truth

Operational handling in this batch:
- the family is still surfaced in the profile/run path
- run-item logging records it explicitly as `incomplete`
- completeness records it explicitly as `incomplete`
- no fake destination is created for it

### 3.2 `highfreq_signal_daily`
Status:
- **not used as the Milestone 4 durable implementation target**

Why:
- it is too vague relative to the now-accepted explicit highfreq families
- Milestone 4 replaces the umbrella placeholder with concrete archive-worthy families

---

## 4. Code / table changes

### 4.1 New Archive V2 data tables
Added in `src/ifa_data_platform/archive_v2/db.py`:
- `ifa2.ifa_archive_highfreq_event_stream_daily`
- `ifa2.ifa_archive_highfreq_limit_event_stream_daily`
- `ifa2.ifa_archive_highfreq_sector_breadth_daily`
- `ifa2.ifa_archive_highfreq_sector_heat_daily`
- `ifa2.ifa_archive_highfreq_leader_candidate_daily`
- `ifa2.ifa_archive_highfreq_intraday_signal_state_daily`

### 4.2 Runner changes
Added in `src/ifa_data_platform/archive_v2/runner.py`:
- Milestone 4 family registration in `SUPPORTED_DAILY_FAMILIES`
- implemented-family registration in `IMPLEMENTED_FAMILIES`
- truthful non-implemented classification notes
- family execution branches for all selected Milestone 4 families
- latest-daily-row fetch path for finalized snapshot/state families
- event-row writer for event-semantics families
- snapshot writer for finalized-state families

### 4.3 Validation profile
Added:
- `profiles/archive_v2_milestone4_highfreq_write_sample.json`

### 4.4 Focused test
Added:
- `tests/integration/test_archive_v2_milestone4.py`

---

## 5. Validation commands used

### 5.1 Syntax / compile validation
```bash
.venv/bin/python -m py_compile \
  src/ifa_data_platform/archive_v2/db.py \
  src/ifa_data_platform/archive_v2/runner.py \
  tests/integration/test_archive_v2_milestone4.py
```

### 5.2 Focused integration tests
```bash
.venv/bin/pytest tests/integration/test_archive_v2_milestone4.py -q
.venv/bin/pytest tests/integration/test_archive_v2_milestone3.py tests/integration/test_archive_v2_milestone4.py -q
```

Observed result:
- `test_archive_v2_milestone4.py`: passed
- milestone3 + milestone4 focused set: `2 passed`

### 5.3 Direct runtime run to populate highfreq working truth
```bash
.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane highfreq --owner-type default --owner-id default
```

Observed result summary:
- `stock_1m_ohlcv`: succeeded, `6`
- `index_1m_ohlcv`: succeeded, `6`
- `etf_sector_style_1m_ohlcv`: succeeded, `1`
- `futures_commodity_pm_1m_ohlcv`: succeeded, `40`
- `open_auction_snapshot`: succeeded, `1`
- `close_auction_snapshot`: succeeded, `1`
- `event_time_stream+derived_signal_state`: succeeded, `410`

### 5.4 Direct Archive V2 profile run
```bash
.venv/bin/python scripts/archive_v2_run.py --profile profiles/archive_v2_milestone4_highfreq_write_sample.json
```

Observed result:
```json
{
  "ok": true,
  "run_id": "d99aaa7f-4ff2-4c58-a8db-9d189fe4fd27",
  "status": "partial",
  "notes": "Selected Archive V2 families ran, with truthful incomplete status preserved for intentionally unarchived or not-yet-worthy families"
}
```

The `partial` is **intentional and truthful** because `generic_structured_output_daily` is explicitly marked not archive-v2 worthy.

---

## 6. DB evidence

### 6.1 Archive row counts for business date `2026-04-15`

```text
ifa_archive_highfreq_event_stream_daily          183
ifa_archive_highfreq_limit_event_stream_daily      1
ifa_archive_highfreq_sector_breadth_daily         1
ifa_archive_highfreq_sector_heat_daily            1
ifa_archive_highfreq_leader_candidate_daily       1
ifa_archive_highfreq_intraday_signal_state_daily  1
```

Important truthful note:
- `ifa_archive_run_items.rows_written` for event families reflects processed source rows in the run path
- retained table row counts can be lower because Archive V2 uses stable daily identity/upsert semantics instead of keeping duplicate same-day working churn

### 6.2 Run-item evidence for run `d99aaa7f-4ff2-4c58-a8db-9d189fe4fd27`

```text
generic_structured_output_daily      incomplete  rows_written=0
highfreq_event_stream_daily          completed   rows_written=800
highfreq_intraday_signal_state_daily completed   rows_written=1
highfreq_leader_candidate_daily      completed   rows_written=1
highfreq_limit_event_stream_daily    completed   rows_written=4
highfreq_sector_breadth_daily        completed   rows_written=1
highfreq_sector_heat_daily           completed   rows_written=1
```

### 6.3 Completeness evidence

For `business_date = 2026-04-15`:
- `highfreq_event_stream_daily`: `completed`, `row_count=800`
- `highfreq_limit_event_stream_daily`: `completed`, `row_count=4`
- `highfreq_sector_breadth_daily`: `completed`, `row_count=1`
- `highfreq_sector_heat_daily`: `completed`, `row_count=1`
- `highfreq_leader_candidate_daily`: `completed`, `row_count=1`
- `highfreq_intraday_signal_state_daily`: `completed`, `row_count=1`
- `generic_structured_output_daily`: `incomplete`, `row_count=0`

Recorded reason for the incomplete family:
- `generic structured-output catch-all is not archive-v2 worthy because it collapses unrelated finalized truths into one lossy bucket`

### 6.4 Sample retained rows

Event-stream sample:
- `2026-04-15 23:59:27-07` / `major_news`
- `2026-04-15 23:59:15-07` / `major_news`
- `2026-04-15 23:59:09-07` / `major_news`

Signal-state sample:
- `snapshot_time=2026-04-15 09:35:00-07`
- `scope_key=market_scope`
- `emotion_stage=cool`
- `validation_state=challenged`

---

## 7. Truthful judgment

### 7.1 What is now materially real
Milestone 4 is now materially real for selected highfreq families.

Archive V2 now has a durable destination for:
- event-like highfreq families via event-stream retention
- latest-state highfreq families via finalized daily snapshot retention

This is not a placeholder interface anymore.

### 7.2 What is explicitly still not true
It is **not** true that all highfreq/structured outputs now belong in Archive V2.

Still not accepted as finalized Archive V2 truth in this batch:
- generic structured-output catch-all storage
- arbitrary transient working noise
- vague umbrella family storage without family-specific semantics

---

## 8. Remaining next milestone work

Most natural next step after this batch:
1. broaden highfreq archive coverage only where family semantics are stable enough
2. strengthen multi-day replay / backfill / repair semantics for the new Milestone 4 families
3. tighten finalized-row identity/dedup policy for highfreq event families if a stronger source-native event key becomes available
4. decide whether any additional highfreq state families deserve explicit Archive V2 tables rather than generic archive storage
5. integrate these new families into stronger production repair/backfill flows, not just single-day validation

---

## 9. Bottom line

Milestone 4 now lands **real Archive V2 durable truth** for the requested highfreq families, while also staying honest that a generic structured-output catch-all is **not** an acceptable Archive V2 finalized-truth model.
