# Archive V2 Runtime Orchestration Closure

Generated: 2026-04-19 04:18 PDT
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Short summary

This batch closed the runtime orchestration problems around Archive V2 nightly execution:

1. nightly family selection evidence was mismatched / polluted
2. production nightly trigger evidence was duplicated
3. operator-visible archive_v2 nightly evidence was therefore not trustworthy

This batch fixed the runtime entry/trigger path, cleaned the wrong nightly residue, and ran one clean single nightly simulation through the official production nightly trigger.

---

## 2. Before-state runtime orchestration mismatch

## A. Nightly family selection mismatch
Accepted nightly model was:
- daily/final tradable
- daily/final business/event
- no highfreq C-class derived daily families
- no proxy families
- no 1m / 15m / 60m later-enable families

But recent run evidence showed:

### `production_nightly_archive_v2` recent families
- `equity_daily`
- `index_daily`
- `etf_daily`
- `non_equity_daily`
- `macro_daily`
- plus disallowed highfreq C-class families:
  - `highfreq_event_stream_daily`
  - `highfreq_limit_event_stream_daily`
  - `highfreq_sector_breadth_daily`
  - `highfreq_sector_heat_daily`
  - `highfreq_leader_candidate_daily`
  - `highfreq_intraday_signal_state_daily`

### `runtime_archive_v2_nightly` recent families
- correct business/event families were present
- but the same disallowed highfreq C-class families were still mixed in

This proved the runtime/operator evidence was not clean.

## B. Duplicate trigger mismatch
Two production-looking nightly trigger sources existed in `ifa_archive_runs`:
- `production_nightly_archive_v2`
- `runtime_archive_v2_nightly`

This was not a single run producing two cosmetic evidence rows.
It was two distinct trigger labels being written into run history.

---

## 3. Nightly family selection root cause

## Official family selection entrypoint
The real nightly family selection should be determined by:
- file: `src/ifa_data_platform/archive_v2/production.py`
- function: `build_nightly_profile()`
- consumed by:
  - `run_nightly_production()`
  - `ArchiveV2Runner._resolve_requested_families()` in `src/ifa_data_platform/archive_v2/runner.py`

The profile-level mechanism is:
- `ArchiveProfile.family_groups = PRODUCTION_NIGHTLY_FAMILIES`
- runner resolves exactly that list when `family_groups` is present

## Why operator evidence still looked wrong
There were two real causes:

### Cause 1 — polluted historical nightly evidence
The DB still contained pre-fix nightly simulation rows whose `ifa_archive_run_items` mixed in highfreq C-class families.
That wrong residue was still being read as if it represented the current accepted nightly model.

### Cause 2 — unified runtime summary was not reporting the actual Archive V2 nightly family set
File:
- `src/ifa_data_platform/runtime/unified_runtime.py`

Function:
- archive_v2 lane runtime summary block in `_run_archive_v2_lane()`

Problem:
- it used `manifest.items if resolved_lane == "archive"` as a preview/snapshot for the archive_v2 lane summary
- that manifest view is not the authoritative Archive V2 nightly family list
- it therefore polluted operator-visible nightly family evidence

## Exact conclusion
The authoritative nightly family selector is:
- `src/ifa_data_platform/archive_v2/production.py::build_nightly_profile()`
- using `PRODUCTION_NIGHTLY_FAMILIES`

The operator-visible mismatch came from:
- stale wrong nightly residue in DB
- plus runtime summary using the wrong evidence surface

---

## 4. Duplicate trigger root cause

## Real root cause
Both of these were being written as production-looking nightly trigger sources:
- `production_nightly_archive_v2`
- `runtime_archive_v2_nightly`

### File/function level
- `src/ifa_data_platform/archive_v2/production.py::run_nightly_production()`
  - previously defaulted to `production_nightly_archive_v2`
- `src/ifa_data_platform/runtime/unified_runtime.py`
  - archive_v2 runtime lane explicitly called `run_nightly_production(trigger_source="runtime_archive_v2_nightly")`
- `scripts/archive_v2_production_cli.py`
  - nightly CLI path called `run_nightly_production(...)` and inherited the production-looking default trigger source unless explicitly overridden

## Exact conclusion
Duplicate trigger evidence happened because:
- runtime lane had one formal nightly trigger label
- CLI / direct production wrapper path had another production-looking nightly trigger label
- both produced real `ifa_archive_runs` rows

This was a true duplicate-trigger design problem, not a single-run double-log illusion.

---

## 5. Exact fixes applied

## Fix 1 — single official production nightly trigger
Official production nightly trigger retained:
- `runtime_archive_v2_nightly`

File:
- `src/ifa_data_platform/archive_v2/production.py`

Changes:
- added `OFFICIAL_RUNTIME_NIGHTLY_TRIGGER = 'runtime_archive_v2_nightly'`
- added `MANUAL_CLI_NIGHTLY_TRIGGER = 'manual_archive_v2_nightly_cli'`
- changed `run_nightly_production()` default trigger source to `runtime_archive_v2_nightly`

File:
- `scripts/archive_v2_production_cli.py`

Changes:
- CLI nightly now defaults to `manual_archive_v2_nightly_cli`
- CLI no longer pretends to be a second formal production nightly trigger
- CLI can still override trigger source explicitly for controlled simulation/testing

## Fix 2 — hard nightly family-set guard
File:
- `src/ifa_data_platform/archive_v2/production.py`

Added explicit nightly guard:
- `DISALLOWED_NIGHTLY_FAMILIES`

This guard blocks any of these from entering default nightly:
- `highfreq_event_stream_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`
- `proxy_1m`
- `proxy_15m`
- `proxy_60m`
- all 1m/15m/60m later-enable families

If any disallowed family enters `PRODUCTION_NIGHTLY_FAMILIES`, the code now raises immediately.

## Fix 3 — unified runtime archive_v2 summary now records the real nightly family set
File:
- `src/ifa_data_platform/runtime/unified_runtime.py`

Changes:
- stopped using legacy/manifest preview as the authoritative archive_v2 nightly family snapshot
- archive_v2 runtime summary now records:
  - `nightly_family_set`
- `manifest_item_count` for archive_v2 now reflects the actual nightly family set size

This removes the operator-visible family preview pollution.

## Fix 4 — stable docs updated
File:
- `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`

Added explicit truth:
- only formal production nightly trigger = `runtime_archive_v2_nightly`
- CLI nightly = operator/manual path

---

## 6. Cleanup/reset scope

## Goal
Clean only the wrong nightly simulation residue that polluted operator/runtime evidence.

## Scope cleaned
Dates:
- `2026-04-17`
- `2026-04-18`

Families cleaned:
- accepted nightly daily/final families
- plus the wrongly mixed highfreq C-class daily families

Artifact:
- `artifacts/archive_v2_nightly_orchestration_cleanup_20260419.json`

## Deleted rows
- `ifa_archive_equity_daily`: `5497`
- `ifa_archive_index_daily`: `8`
- `ifa_archive_etf_daily`: `1946`
- `ifa_archive_non_equity_daily`: `1076`
- `ifa_archive_macro_daily`: `6`
- `ifa_archive_announcements_daily`: `5030`
- `ifa_archive_news_daily`: `429`
- `ifa_archive_completeness`: `22`
- `ifa_archive_repair_queue`: `16`
- `ifa_archive_run_items`: `213`
- `ifa_archive_runs`: `15`

Truthful note:
- no broad cleanup was done
- no Business Layer truth touched
- no trading/calendar truth touched
- no runtime schedule truth touched
- no canonical retained source truth touched

---

## 7. Post-fix single nightly simulation evidence

## Command path used
Formal nightly production path was simulated via:
- `scripts/archive_v2_production_cli.py nightly --business-date 2026-04-18 --trigger-source runtime_archive_v2_nightly`

This used the official production nightly trigger label.

## Simulation artifact
- `artifacts/archive_v2_clean_nightly_simulation_20260419.json`

## Final family set actually executed
Exactly these 13 families:
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

### Explicitly not present
No highfreq C-class families mixed in:
- `highfreq_event_stream_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

No proxy family mixed in.
No 1m/15m/60m later-enable family mixed in.

## Trigger evidence after fix
Direct DB verification for the last 2 hours:
- `runtime_archive_v2_nightly`: `1`
- `production_nightly_archive_v2`: `0`

So after the fix and cleanup:
- no duplicate nightly production evidence reappeared

## Run result
- run_id: `a235533d-f4a3-4e6a-b1d6-0b908c8b8c70`
- trigger_source: `runtime_archive_v2_nightly`
- profile: `archive_v2_production_nightly_daily_final`
- status: `partial`
- business_date: `2026-04-18`

## item_status_counts
- `completed`: `5`
- `incomplete`: `8`

## touched tables
Rows written > 0 went to:
- `ifa_archive_announcements_daily`: `5064`
- `ifa_archive_limit_up_down_status_daily`: `1`
- `ifa_archive_macro_daily`: `3`
- `ifa_archive_news_daily`: `2271`
- `ifa_archive_research_reports_daily`: `11`

## Per-family statuses
- `announcements_daily` — completed — `5064`
- `dragon_tiger_daily` — incomplete — `0`
- `equity_daily` — incomplete — `0`
- `etf_daily` — incomplete — `0`
- `index_daily` — incomplete — `0`
- `investor_qa_daily` — completed — `0`
- `limit_up_detail_daily` — incomplete — `0`
- `limit_up_down_status_daily` — incomplete — `1`
- `macro_daily` — completed — `3`
- `news_daily` — completed — `2271`
- `non_equity_daily` — incomplete — `0`
- `research_reports_daily` — completed — `11`
- `sector_performance_daily` — incomplete — `0`

Truthful note:
- the simulation being `partial` is acceptable here because this batch’s target was orchestration correctness, not to force all nightly families complete on that chosen business date
- the orchestration success criteria were:
  - correct family set
  - single official trigger
  - no duplicate evidence

Those criteria were satisfied.

---

## 8. Truthful final judgment

### Nightly family selection before-state root cause
- authoritative selector should have been `build_nightly_profile() -> PRODUCTION_NIGHTLY_FAMILIES`
- operator/runtime evidence was polluted by:
  - stale wrong nightly residue in DB
  - runtime summary using non-authoritative manifest preview

### Duplicate trigger before-state root cause
- both `production_nightly_archive_v2` and `runtime_archive_v2_nightly` were writing real run evidence
- CLI/manual nightly path was masquerading as a second production nightly trigger

### Post-fix final state
- official production nightly trigger kept: `runtime_archive_v2_nightly`
- CLI nightly is now manual/operator only
- nightly default family set is guarded in code and excludes all disallowed signal/proxy/later-enable intraday families
- one clean nightly simulation ran with exactly the accepted 13-family nightly set
- no duplicate nightly production evidence reappeared

### Final closure result
This runtime orchestration batch is **closed**.
