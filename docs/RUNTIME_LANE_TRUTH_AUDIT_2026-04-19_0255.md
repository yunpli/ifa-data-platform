# Runtime Lane Truth Audit

Generated: 2026-04-19 02:55 PDT
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## Summary

This document records the **current real runtime truth** for the four lanes the operator asked about:
- `lowfreq`
- `midfreq`
- `highfreq`
- `archive_v2`

Source of truth used:
- live DB `ifa2.runtime_worker_schedules`
- repo runtime code / runbook
- live recent DB run evidence

Artifacts:
- sample daily report: `docs/RUNTIME_DAILY_REPORT_SAMPLE_2026-04-19_0245.md`

---

## 1. lowfreq

### Is it in formal runtime/daemon?
Yes.

### Schedule truth (Asia/Shanghai)
- trading day: `07:20`
- non-trading weekday: `08:30`
- Saturday: `09:00`
- Sunday: `09:00`

### UTC reference
- `07:20 CST` = `23:20 UTC` previous day
- `08:30 CST` = `00:30 UTC`
- `09:00 CST` = `01:00 UTC`

### What it runs
- trading day premarket slow/reference refresh
  - calendar/reference/fundamental support before early report
- non-trading weekday reference refresh
- Saturday weekly review / past-week recap support
- Sunday next-week preview / setup support

### Auto vs manual
- these schedule entries are enabled and part of the formal daemon/runtime schedule

---

## 2. midfreq

### Is it in formal runtime/daemon?
Yes.

### Schedule truth (Asia/Shanghai)
- trading day: `11:45`
- trading day: `15:20`
- non-trading weekday: disabled (`12:00 skip` entry exists but `enabled=false`)
- Saturday: `10:30`
- Sunday: `10:30`

### UTC reference
- `11:45 CST` = `03:45 UTC`
- `15:20 CST` = `07:20 UTC`
- `10:30 CST` = `02:30 UTC`

### What it runs
- trading day midday report support after morning session
- trading day post-close / late report support
- Saturday weekly review dataset refresh
- Sunday preview / swing-close support for next week

### Auto vs manual
- trading-day + weekend review/preview entries are formal runtime schedule entries
- non-trading weekday regular cadence is not automatic

---

## 3. highfreq

### Is it in formal runtime/daemon?
Yes, but only on trading days.

### Schedule truth (Asia/Shanghai)
- trading day: `09:15`
- trading day: `11:25`
- trading day: `14:57`
- non-trading weekday: disabled (`12:00 skip`)
- Saturday: disabled (`12:00 skip`)
- Sunday: disabled (`12:00 skip`)

### UTC reference
- `09:15 CST` = `01:15 UTC`
- `11:25 CST` = `03:25 UTC`
- `14:57 CST` = `06:57 UTC`

### What it runs
- `09:15`: pre-open / auction support for trading-day early report
- `11:25`: intraday support approaching midday report
- `14:57`: close / auction support for late report

### Auto vs manual
- trading-day entries are enabled and formal
- offday/weekend schedule entries are explicit skips

### Truthful note
Highfreq is in the formal runtime schedule, but in the last 24h sample window the observed highfreq runs were manual `manual_once` runs, not scheduled daemon firings.

---

## 4. archive_v2

### Is it in formal runtime/daemon?
Yes.

### Schedule truth (Asia/Shanghai)
- trading day: `21:40`
- non-trading weekday: disabled (`21:40 skip`)
- Saturday: disabled (`21:40 skip`)
- Sunday: disabled (`21:40 skip`)

### UTC reference
- `21:40 CST` = `13:40 UTC`

### What it runs
Trading-day nightly daily/final Archive V2 production path.
Current nightly production family set in code:
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

### Auto vs manual
- trading-day nightly path is enabled and formal
- offday catch-up / replay remains manual/backfill

### Truthful note about legacy archive lane
There is still a legacy `archive` lane in the DB schedule at `21:30`, but all of its entries are `enabled=false`.
So the current default nightly production path is **Archive V2**, not legacy archive.

---

## 5. Direct lane schedule summary table

| lane | trading day | non-trading weekday | Saturday | Sunday | formal runtime? | main content |
|---|---|---|---|---|---|---|
| lowfreq | 07:20 | 08:30 | 09:00 | 09:00 | yes | calendar/reference/fundamental refresh, weekly review/preview support |
| midfreq | 11:45, 15:20 | disabled | 10:30 | 10:30 | yes | midday/post-close support, weekly review/preview |
| highfreq | 09:15, 11:25, 14:57 | disabled | disabled | disabled | yes | pre-open, intraday midday, close/auction support |
| archive_v2 | 21:40 | disabled | disabled | disabled | yes | nightly daily/final Archive V2 production |

---

## 6. Daily runtime report capability check

### Existing script found
- existing script: `scripts/runtime_24h_report.py`

### Why it is not enough
It is not enough for the requested production operator use because:
- it does not treat `archive_v2` as a first-class lane report surface
- it does not directly report four-lane truth in one place
- it is not sufficient for the requested per-run operator-readable daily summary structure

### New formal script added
- new script: `scripts/runtime_daily_report.py`

### What it does now
- reports a configurable time window (default `24h`)
- covers:
  - `lowfreq`
  - `midfreq`
  - `highfreq`
  - `archive_v2`
- shows per-run:
  - start
  - end
  - duration
  - status
  - trigger source / trigger mode
  - touched tables
  - rows by table where reliable from DB/runtime evidence
- shows Archive V2 backlog / repair queue summary
- ends with operator-readable health conclusion

### Sample output path
- `docs/RUNTIME_DAILY_REPORT_SAMPLE_2026-04-19_0245.md`

---

## Final judgment

- the four-lane schedule truth is now explicitly audited against live DB schedule truth
- `archive_v2` is the formal nightly production lane
- legacy `archive` remains in schedule truth only as disabled/manual fallback
- a formal daily runtime report script now exists and has been run successfully on real DB/runtime evidence
