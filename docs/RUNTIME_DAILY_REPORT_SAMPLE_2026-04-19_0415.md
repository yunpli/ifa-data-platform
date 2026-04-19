# Runtime Daily Report

- Window: last 6 hours
- Generated: 2026-04-19 19:12:45 CST

## Schedule truth

- archive | non_trading_weekday | 21:30 | enabled=False | trigger=daily_time | archive:offday_archive | legacy archive path retained for coexistence/manual fallback on non-trading weekdays
- archive | saturday | 21:30 | enabled=False | trigger=daily_time | archive:saturday_archive | legacy archive path retained for coexistence/manual fallback on Saturday
- archive | sunday | 21:30 | enabled=False | trigger=daily_time | archive:sunday_archive | legacy archive path retained for coexistence/manual fallback on Sunday
- archive | trading_day | 21:30 | enabled=False | trigger=daily_time | archive:trade_day_evening_archive | legacy archive path retained for coexistence/manual fallback; no longer default nightly production path
- archive_v2 | non_trading_weekday | 21:40 | enabled=False | trigger=daily_time | archive_v2:offday_skip | Archive V2 nightly production is trading-day scoped; offday catch-up remains manual/backfill
- archive_v2 | saturday | 10:30 | enabled=True | trigger=daily_time | archive_v2:saturday_catchup_window | Archive V2 controlled weekend catch-up window: bounded backfill + completeness catch-up + actionable repair drain
- archive_v2 | sunday | 10:30 | enabled=True | trigger=daily_time | archive_v2:sunday_catchup_window | Archive V2 controlled weekend catch-up window: bounded backfill + completeness catch-up + actionable repair drain
- archive_v2 | trading_day | 21:40 | enabled=True | trigger=daily_time | archive_v2:trade_day_nightly_daily_final | Archive V2 steady-state nightly daily/final truth production
- highfreq | non_trading_weekday | 12:00 | enabled=False | trigger=daily_time | highfreq:offday_skip | no highfreq market session on non-trading weekday
- highfreq | saturday | 12:00 | enabled=False | trigger=daily_time | highfreq:saturday_skip | no highfreq weekend session
- highfreq | sunday | 12:00 | enabled=False | trigger=daily_time | highfreq:sunday_skip | no highfreq weekend session
- highfreq | trading_day | 09:15 | enabled=True | trigger=daily_time | highfreq:trade_day_pre_open | coarse pre-open / auction support for trading-day early report
- highfreq | trading_day | 09:27 | enabled=True | trigger=daily_time | highfreq:trade_day_final_pre_open_snapshot | final post-auction / near-open snapshot for the 09:29-style pre-open briefing
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
- no runs in window

### archive_v2
- start=2026-04-19 19:08:16 CST | end=2026-04-19 19:12:02 CST | duration=226s | status=partial | trigger=runtime_archive_v2_nightly | profile=archive_v2_production_nightly_daily_final
  - touched_tables: ifa_archive_announcements_daily, ifa_archive_limit_up_down_status_daily, ifa_archive_macro_daily, ifa_archive_news_daily, ifa_archive_research_reports_daily
  - rows_by_table: {"ifa_archive_announcements_daily": 5064, "ifa_archive_dragon_tiger_daily": 0, "ifa_archive_equity_daily": 0, "ifa_archive_etf_daily": 0, "ifa_archive_index_daily": 0, "ifa_archive_investor_qa_daily": 0, "ifa_archive_limit_up_detail_daily": 0, "ifa_archive_limit_up_down_status_daily": 1, "ifa_archive_macro_daily": 3, "ifa_archive_news_daily": 2271, "ifa_archive_non_equity_daily": 0, "ifa_archive_research_reports_daily": 11, "ifa_archive_sector_performance_daily": 0}
  - item_status_counts: {"completed": 5, "incomplete": 8}

## Archive backlog / repair summary

- incomplete_or_partial_count: 8
- repair_queue_count: 8
- incomplete sample:
  - 2026-04-18 | dragon_tiger_daily | incomplete
  - 2026-04-18 | equity_daily | incomplete
  - 2026-04-18 | etf_daily | incomplete
  - 2026-04-18 | index_daily | incomplete
  - 2026-04-18 | limit_up_detail_daily | incomplete
  - 2026-04-18 | limit_up_down_status_daily | incomplete
  - 2026-04-18 | non_equity_daily | incomplete
  - 2026-04-18 | sector_performance_daily | incomplete
- repair queue sample:
  - 2026-04-18 | dragon_tiger_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | equity_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | etf_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | index_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | limit_up_detail_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | limit_up_down_status_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | non_equity_daily | pending | claimed_by=None | suppressed_until=None
  - 2026-04-18 | sector_performance_daily | pending | claimed_by=None | suppressed_until=None

## Operator-readable conclusion

- Non-healthy runs detected: unified=0, archive_v2=1.
- archive_v2 notable issues:
  - 2026-04-19 19:08:16 CST | runtime_archive_v2_nightly | partial | archive_v2_production_nightly_daily_final
