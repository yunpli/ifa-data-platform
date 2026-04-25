# DB Reality Snapshot V2 — 2026-04-24

Task: `V2-R0-002 DB reality probe 复核与快照固化`

Evidence JSON: `artifacts/db_reality_snapshot_v2_20260424.json`

## Executive Summary

- `highfreq / midfreq / lowfreq / archive_v2 / focus` probe completed against live `ifa2` schema.
- News-related families non-empty status: announcements=168542, news=67249, research_reports=2737, investor_qa=19970
- Focus/key-focus list counts: [{"list_type": "focus", "list_count": 4}, {"list_type": "key_focus", "list_count": 4}]

## highfreq

| Table | Exists | Row Count | Non-empty | Earliest | Latest |
|---|---:|---:|---:|---|---|
| `highfreq_stock_1m_working` | yes | 6 | yes | 2026-04-15 09:30:00 | 2026-04-15 09:35:00 |
| `highfreq_open_auction_working` | yes | 1 | yes | 2026-04-15 | 2026-04-15 |
| `highfreq_event_stream_working` | yes | 22954 | yes | 2026-04-15 22:52:38 | 2026-04-24 15:33:56 |
| `highfreq_sector_breadth_working` | yes | 1 | yes | 2026-04-15 09:35:00 | 2026-04-15 09:35:00 |
| `highfreq_sector_heat_working` | yes | 1 | yes | 2026-04-15 09:35:00 | 2026-04-15 09:35:00 |
| `highfreq_leader_candidate_working` | yes | 6 | yes | 2026-04-15 09:35:00 | 2026-04-15 09:35:00 |
| `highfreq_intraday_signal_state_working` | yes | 1 | yes | 2026-04-15 09:35:00 | 2026-04-15 09:35:00 |

## midfreq

| Table | Exists | Row Count | Non-empty | Earliest | Latest |
|---|---:|---:|---:|---|---|
| `limit_up_detail_history` | yes | 113419 | yes | 2026-04-15 | 2026-04-23 |
| `dragon_tiger_list_history` | yes | 2584 | yes | 2025-04-09 | 2026-04-23 |
| `sector_performance_history` | yes | 3263 | yes | 2026-04-16 | 2026-04-23 |
| `northbound_flow_history` | yes | 21 | yes | 2026-04-14 | 2026-04-23 |
| `equity_daily_bar_history` | yes | 562 | yes | 2025-04-10 | 2026-04-24 |
| `etf_daily_bar_history` | yes | 444 | yes | 2026-04-14 | 2026-04-24 |
| `midfreq_datasets` | yes | 12 | yes | - | - |

## lowfreq

| Table | Exists | Row Count | Non-empty | Earliest | Latest |
|---|---:|---:|---:|---|---|
| `announcements_history` | yes | 168542 | yes | 2026-04-10 | 2026-04-24 |
| `news_history` | yes | 67249 | yes | 2026-04-10 17:50:14 | 2026-04-24 21:59:43 |
| `research_reports_history` | yes | 2737 | yes | 2026-04-10 | 2026-04-23 |
| `investor_qa_history` | yes | 19970 | yes | 2026-04-10 | 2026-04-23 |
| `trade_cal_history` | yes | 154951 | yes | 2020-01-01 | 2026-12-31 |
| `stock_basic_history` | yes | 451426 | yes | 2026-04-10 04:36:16.442710 | 2026-04-24 07:00:08.678764 |
| `lowfreq_datasets` | yes | 69 | yes | - | - |

## archive_v2

| Table | Exists | Row Count | Non-empty | Earliest | Latest |
|---|---:|---:|---:|---|---|
| `ifa_archive_announcements_daily` | yes | 34853 | yes | 2026-04-07 | 2026-04-24 |
| `ifa_archive_news_daily` | yes | 97820 | yes | 2026-04-07 | 2026-04-24 |
| `ifa_archive_research_reports_daily` | yes | 1303 | yes | 2026-04-07 | 2026-04-24 |
| `ifa_archive_investor_qa_daily` | yes | 11275 | yes | 2026-04-07 | 2026-04-24 |
| `ifa_archive_equity_daily_daily` | no | 0 | no | - | - |
| `ifa_archive_runs` | yes | 4 | yes | - | - |
| `ifa_archive_run_items` | yes | 52 | yes | 2026-04-22 | 2026-04-24 |
| `ifa_archive_completeness` | yes | 186 | yes | 2022-11-01 | 2026-04-24 |

## focus

| Table | Exists | Row Count | Non-empty | Earliest | Latest |
|---|---:|---:|---:|---|---|
| `focus_lists` | yes | 11 | yes | 2026-04-22 22:29:26.630278-07:00 | 2026-04-22 22:29:26.675758-07:00 |
| `focus_list_items` | yes | 442 | yes | 2026-04-22 22:29:26.635145-07:00 | 2026-04-22 22:29:26.676264-07:00 |
| `focus_list_rules` | yes | 32 | yes | 2026-04-22 22:29:26.633037-07:00 | 2026-04-22 22:29:26.675970-07:00 |

## Focus / Key-Focus Named Examples

```json
[
  {
    "name": "default_asset_focus",
    "list_type": "focus",
    "asset_type": "asset",
    "is_active": true
  },
  {
    "name": "default_asset_key_focus",
    "list_type": "key_focus",
    "asset_type": "asset",
    "is_active": true
  },
  {
    "name": "default_tech_focus",
    "list_type": "focus",
    "asset_type": "tech",
    "is_active": true
  },
  {
    "name": "default_tech_key_focus",
    "list_type": "key_focus",
    "asset_type": "tech",
    "is_active": true
  },
  {
    "name": "default_macro_focus",
    "list_type": "focus",
    "asset_type": "macro",
    "is_active": true
  },
  {
    "name": "default_macro_key_focus",
    "list_type": "key_focus",
    "asset_type": "macro",
    "is_active": true
  },
  {
    "name": "default_stock_focus",
    "list_type": "focus",
    "asset_type": "stock",
    "is_active": true
  },
  {
    "name": "default_stock_key_focus",
    "list_type": "key_focus",
    "asset_type": "stock",
    "is_active": true
  }
]
```

## Notes

- This is a read-only reality probe; no collector expansion and no collection-layer refactor were performed.
- `exists=yes` means physical table exists in `ifa2`; `non-empty=yes` means row count > 0 at probe time.
