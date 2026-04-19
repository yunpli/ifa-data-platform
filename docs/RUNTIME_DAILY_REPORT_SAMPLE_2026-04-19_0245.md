# Runtime Daily Report

- Window: last 24 hours
- Generated: 2026-04-19 17:50:29 CST

## Schedule truth

- archive | non_trading_weekday | 21:30 | enabled=False | trigger=daily_time | archive:offday_archive | legacy archive path retained for coexistence/manual fallback on non-trading weekdays
- archive | saturday | 21:30 | enabled=False | trigger=daily_time | archive:saturday_archive | legacy archive path retained for coexistence/manual fallback on Saturday
- archive | sunday | 21:30 | enabled=False | trigger=daily_time | archive:sunday_archive | legacy archive path retained for coexistence/manual fallback on Sunday
- archive | trading_day | 21:30 | enabled=False | trigger=daily_time | archive:trade_day_evening_archive | legacy archive path retained for coexistence/manual fallback; no longer default nightly production path
- archive_v2 | non_trading_weekday | 21:40 | enabled=False | trigger=daily_time | archive_v2:offday_skip | Archive V2 nightly production is trading-day scoped; offday catch-up remains manual/backfill
- archive_v2 | saturday | 21:40 | enabled=False | trigger=daily_time | archive_v2:saturday_skip | Archive V2 steady-state nightly run is not automatic on Saturday; use manual backfill if needed
- archive_v2 | sunday | 21:40 | enabled=False | trigger=daily_time | archive_v2:sunday_skip | Archive V2 steady-state nightly run is not automatic on Sunday; use manual backfill if needed
- archive_v2 | trading_day | 21:40 | enabled=True | trigger=daily_time | archive_v2:trade_day_nightly_daily_final | Archive V2 steady-state nightly daily/final truth production
- highfreq | non_trading_weekday | 12:00 | enabled=False | trigger=daily_time | highfreq:offday_skip | no highfreq market session on non-trading weekday
- highfreq | saturday | 12:00 | enabled=False | trigger=daily_time | highfreq:saturday_skip | no highfreq weekend session
- highfreq | sunday | 12:00 | enabled=False | trigger=daily_time | highfreq:sunday_skip | no highfreq weekend session
- highfreq | trading_day | 09:15 | enabled=True | trigger=daily_time | highfreq:trade_day_pre_open | pre-open/auction support for trading-day early report
- highfreq | trading_day | 11:25 | enabled=True | trigger=daily_time | highfreq:trade_day_intraday_midday | intraday support approaching midday report
- highfreq | trading_day | 14:57 | enabled=True | trigger=daily_time | highfreq:trade_day_close | close/auction support for late report
- lowfreq | non_trading_weekday | 08:30 | enabled=True | trigger=daily_time | lowfreq:offday_reference_refresh | refresh slow/reference data on non-trading weekday
- lowfreq | saturday | 09:00 | enabled=True | trigger=daily_time | lowfreq:saturday_weekly_review_support | support Saturday weekly review / past-week recap
- lowfreq | sunday | 09:00 | enabled=True | trigger=daily_time | lowfreq:sunday_next_week_preview_support | support Sunday next-week preview/setup
- lowfreq | trading_day | 07:20 | enabled=True | trigger=daily_time | lowfreq:trade_day_premarket_refresh | refresh calendar/reference/fundamental support before early report
- midfreq | non_trading_weekday | 12:00 | enabled=False | trigger=daily_time | midfreq:offday_skip | no regular midfreq reporting cadence on non-trading weekday
- midfreq | saturday | 10:30 | enabled=True | trigger=daily_time | midfreq:saturday_weekly_review_support | support weekly review dataset refresh
- midfreq | sunday | 10:30 | enabled=True | trigger=daily_time | midfreq:sunday_preview_support | refresh swing/close-support data for next-week preview
- midfreq | trading_day | 11:45 | enabled=True | trigger=daily_time | midfreq:trade_day_midday_report_support | support midday report snapshot after morning session
- midfreq | trading_day | 15:20 | enabled=True | trigger=daily_time | midfreq:trade_day_post_close_report_support | support late report and close data

## Lane run overview

### lowfreq
- no runs in window

### midfreq
- no runs in window

### highfreq
- start=2026-04-18 20:28:36 CST | end=2026-04-18 20:28:48 CST | duration=11s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 20:24:22 CST | end=2026-04-18 20:24:37 CST | duration=15s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 20:23:29 CST | end=2026-04-18 20:23:38 CST | duration=8s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 19:51:16 CST | end=2026-04-18 19:51:28 CST | duration=11s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 19:50:55 CST | end=2026-04-18 19:51:05 CST | duration=9s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 19:48:26 CST | end=2026-04-18 19:48:44 CST | duration=18s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 19:30:07 CST | end=2026-04-18 19:30:16 CST | duration=8s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 19:30:02 CST | end=2026-04-18 19:30:13 CST | duration=10s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 19:29:40 CST | end=2026-04-18 19:29:49 CST | duration=8s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}
- start=2026-04-18 19:28:56 CST | end=2026-04-18 19:29:08 CST | duration=12s | status=succeeded | trigger=manual_once | records=465
  - main_tables: -
  - table_rows: {}

### archive_v2
- start=2026-04-18 21:38:27 CST | end=2026-04-18 21:38:29 CST | duration=2s | status=partial | trigger=runtime_archive_v2_nightly | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_announcements_daily, ifa_archive_macro_daily, ifa_archive_news_daily
  - rows_by_table: {"ifa_archive_announcements_daily": 5036, "ifa_archive_dragon_tiger_daily": 0, "ifa_archive_equity_daily": 0, "ifa_archive_etf_daily": 0, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 0, "ifa_archive_investor_qa_daily": 0, "ifa_archive_limit_up_detail_daily": 0, "ifa_archive_limit_up_down_status_daily": 0, "ifa_archive_macro_daily": 3, "ifa_archive_news_daily": 629, "ifa_archive_non_equity_daily": 0, "ifa_archive_research_reports_daily": 0, "ifa_archive_sector_performance_daily": 0}
  - item_status_counts: {"completed": 3, "incomplete": 16}
- start=2026-04-18 21:38:22 CST | end=2026-04-18 21:38:27 CST | duration=4s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}
- start=2026-04-18 21:38:04 CST | end=2026-04-18 21:38:09 CST | duration=4s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}
- start=2026-04-18 21:37:37 CST | end=2026-04-18 21:37:40 CST | duration=2s | status=partial | trigger=runtime_archive_v2_nightly | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_announcements_daily, ifa_archive_macro_daily, ifa_archive_news_daily
  - rows_by_table: {"ifa_archive_announcements_daily": 5036, "ifa_archive_dragon_tiger_daily": 0, "ifa_archive_equity_daily": 0, "ifa_archive_etf_daily": 0, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 0, "ifa_archive_investor_qa_daily": 0, "ifa_archive_limit_up_detail_daily": 0, "ifa_archive_limit_up_down_status_daily": 0, "ifa_archive_macro_daily": 3, "ifa_archive_news_daily": 629, "ifa_archive_non_equity_daily": 0, "ifa_archive_research_reports_daily": 0, "ifa_archive_sector_performance_daily": 0}
  - item_status_counts: {"completed": 3, "incomplete": 16}
- start=2026-04-18 21:37:30 CST | end=2026-04-18 21:37:37 CST | duration=6s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}
- start=2026-04-18 21:36:09 CST | end=2026-04-18 21:36:24 CST | duration=15s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}
- start=2026-04-18 21:35:04 CST | end=2026-04-18 21:35:06 CST | duration=2s | status=partial | trigger=runtime_archive_v2_nightly | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_announcements_daily, ifa_archive_macro_daily, ifa_archive_news_daily
  - rows_by_table: {"ifa_archive_announcements_daily": 5036, "ifa_archive_dragon_tiger_daily": 0, "ifa_archive_equity_daily": 0, "ifa_archive_etf_daily": 0, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 0, "ifa_archive_investor_qa_daily": 0, "ifa_archive_limit_up_detail_daily": 0, "ifa_archive_limit_up_down_status_daily": 0, "ifa_archive_macro_daily": 3, "ifa_archive_news_daily": 629, "ifa_archive_non_equity_daily": 0, "ifa_archive_research_reports_daily": 0, "ifa_archive_sector_performance_daily": 0}
  - item_status_counts: {"completed": 3, "incomplete": 16}
- start=2026-04-18 21:34:59 CST | end=2026-04-18 21:35:03 CST | duration=4s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}
- start=2026-04-18 21:34:38 CST | end=2026-04-18 21:34:41 CST | duration=2s | status=partial | trigger=runtime_archive_v2_nightly | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_announcements_daily, ifa_archive_macro_daily, ifa_archive_news_daily
  - rows_by_table: {"ifa_archive_announcements_daily": 5036, "ifa_archive_dragon_tiger_daily": 0, "ifa_archive_equity_daily": 0, "ifa_archive_etf_daily": 0, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 0, "ifa_archive_investor_qa_daily": 0, "ifa_archive_limit_up_detail_daily": 0, "ifa_archive_limit_up_down_status_daily": 0, "ifa_archive_macro_daily": 3, "ifa_archive_news_daily": 629, "ifa_archive_non_equity_daily": 0, "ifa_archive_research_reports_daily": 0, "ifa_archive_sector_performance_daily": 0}
  - item_status_counts: {"completed": 3, "incomplete": 16}
- start=2026-04-18 21:34:20 CST | end=2026-04-18 21:34:26 CST | duration=5s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}
- start=2026-04-18 21:34:17 CST | end=2026-04-18 21:34:20 CST | duration=2s | status=partial | trigger=runtime_archive_v2_nightly | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_announcements_daily, ifa_archive_macro_daily, ifa_archive_news_daily
  - rows_by_table: {"ifa_archive_announcements_daily": 5036, "ifa_archive_dragon_tiger_daily": 0, "ifa_archive_equity_daily": 0, "ifa_archive_etf_daily": 0, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 0, "ifa_archive_investor_qa_daily": 0, "ifa_archive_limit_up_detail_daily": 0, "ifa_archive_limit_up_down_status_daily": 0, "ifa_archive_macro_daily": 3, "ifa_archive_news_daily": 629, "ifa_archive_non_equity_daily": 0, "ifa_archive_research_reports_daily": 0, "ifa_archive_sector_performance_daily": 0}
  - item_status_counts: {"completed": 3, "incomplete": 16}
- start=2026-04-18 21:34:11 CST | end=2026-04-18 21:34:17 CST | duration=5s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}
- start=2026-04-18 21:32:49 CST | end=2026-04-18 21:33:24 CST | duration=35s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}
- start=2026-04-18 21:32:47 CST | end=2026-04-18 21:32:49 CST | duration=1s | status=partial | trigger=runtime_archive_v2_nightly | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_announcements_daily, ifa_archive_macro_daily, ifa_archive_news_daily
  - rows_by_table: {"ifa_archive_announcements_daily": 5036, "ifa_archive_dragon_tiger_daily": 0, "ifa_archive_equity_daily": 0, "ifa_archive_etf_daily": 0, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 0, "ifa_archive_investor_qa_daily": 0, "ifa_archive_limit_up_detail_daily": 0, "ifa_archive_limit_up_down_status_daily": 0, "ifa_archive_macro_daily": 3, "ifa_archive_news_daily": 629, "ifa_archive_non_equity_daily": 0, "ifa_archive_research_reports_daily": 0, "ifa_archive_sector_performance_daily": 0}
  - item_status_counts: {"completed": 3, "incomplete": 16}
- start=2026-04-18 21:32:39 CST | end=2026-04-18 21:32:46 CST | duration=7s | status=partial | trigger=production_nightly_archive_v2 | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_equity_daily, ifa_archive_etf_daily, ifa_archive_index_daily, ifa_archive_macro_daily, ifa_archive_non_equity_daily
  - rows_by_table: {"ifa_archive_equity_daily": 5497, "ifa_archive_etf_daily": 1946, "ifa_archive_highfreq_event_stream_daily": 0, "ifa_archive_highfreq_intraday_signal_state_daily": 0, "ifa_archive_highfreq_leader_candidate_daily": 0, "ifa_archive_highfreq_limit_event_stream_daily": 0, "ifa_archive_highfreq_sector_breadth_daily": 0, "ifa_archive_highfreq_sector_heat_daily": 0, "ifa_archive_index_daily": 8, "ifa_archive_macro_daily": 3, "ifa_archive_non_equity_daily": 1076}
  - item_status_counts: {"completed": 5, "incomplete": 6}

## Archive backlog / repair summary

- incomplete_or_partial_count: 16
- repair_queue_count: 16
- incomplete sample:
  - 2026-04-18 | dragon_tiger_daily | incomplete
  - 2026-04-18 | equity_daily | incomplete
  - 2026-04-18 | etf_daily | incomplete
  - 2026-04-18 | highfreq_event_stream_daily | incomplete
  - 2026-04-18 | highfreq_intraday_signal_state_daily | incomplete
  - 2026-04-18 | highfreq_leader_candidate_daily | incomplete
  - 2026-04-18 | highfreq_limit_event_stream_daily | incomplete
  - 2026-04-18 | highfreq_sector_breadth_daily | incomplete
  - 2026-04-18 | highfreq_sector_heat_daily | incomplete
  - 2026-04-18 | index_daily | incomplete
  - 2026-04-18 | investor_qa_daily | incomplete
  - 2026-04-18 | limit_up_detail_daily | incomplete
  - 2026-04-18 | limit_up_down_status_daily | incomplete
  - 2026-04-18 | non_equity_daily | incomplete
  - 2026-04-18 | research_reports_daily | incomplete
  - 2026-04-18 | sector_performance_daily | incomplete
- repair queue sample:
  - 2026-04-18 | dragon_tiger_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | equity_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | etf_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | highfreq_event_stream_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | highfreq_intraday_signal_state_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | highfreq_leader_candidate_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | highfreq_limit_event_stream_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | highfreq_sector_breadth_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | highfreq_sector_heat_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | index_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | investor_qa_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | limit_up_detail_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | limit_up_down_status_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | non_equity_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | research_reports_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | sector_performance_daily | pending | claimed_by=None | suppressed_until=None

## Operator-readable conclusion

- Non-healthy runs detected: unified=16, archive_v2=15.
- archive_v2 notable issues:
  - 2026-04-18 21:38:27 CST | runtime_archive_v2_nightly | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:38:22 CST | production_nightly_archive_v2 | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:38:04 CST | production_nightly_archive_v2 | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:37:37 CST | runtime_archive_v2_nightly | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:37:30 CST | production_nightly_archive_v2 | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:36:09 CST | production_nightly_archive_v2 | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:35:04 CST | runtime_archive_v2_nightly | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:34:59 CST | production_nightly_archive_v2 | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:34:38 CST | runtime_archive_v2_nightly | partial | archive_v2_production_nightly_daily_final
  - 2026-04-18 21:34:20 CST | production_nightly_archive_v2 | partial | archive_v2_production_nightly_daily_final
