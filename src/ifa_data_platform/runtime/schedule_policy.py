from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SchedulePolicyRow:
    worker_type: str
    day_type: str
    schedule_key: str
    beijing_time_hm: str
    purpose: str
    should_run: bool
    runtime_budget_sec: int
    overlap_policy: str = "skip"
    retry_policy: str = "degrade"
    max_retries: int = 0
    group_name: Optional[str] = None


DEFAULT_SCHEDULE_POLICY: list[SchedulePolicyRow] = [
    # trading day
    SchedulePolicyRow("lowfreq", "trading_day", "lowfreq:trade_day_premarket_refresh", "22:00", "refresh calendar/reference/fundamental support before early report", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_midday_report_support", "11:45", "support midday report snapshot after morning session", True, 1800, max_retries=1, group_name="midday_final"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_post_close_report_support", "15:20", "support late report and close data", True, 2400, max_retries=2, group_name="post_close_final"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_pre_open", "09:15", "coarse pre-open / auction support for trading-day early report", True, 900, max_retries=1, group_name="pre_open_core"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_final_pre_open_snapshot", "09:27", "final post-auction / near-open snapshot for the 09:29-style pre-open briefing", True, 900, max_retries=1, group_name="pre_open_core"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_intraday_midday", "11:25", "intraday support approaching midday report", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_close", "14:57", "close/auction support for late report", True, 900, max_retries=1, group_name="close_core"),
    SchedulePolicyRow("archive", "trading_day", "archive:trade_day_evening_archive", "21:30", "legacy archive path retained for coexistence/manual fallback; no longer default nightly production path", False, 3600, max_retries=1, group_name="archive_legacy"),
    SchedulePolicyRow("archive_v2", "trading_day", "archive_v2:trade_day_nightly_daily_final", "21:40", "Archive V2 steady-state nightly daily/final truth production", True, 5400, max_retries=1, group_name="archive_v2_main"),
    # non-trading weekday
    SchedulePolicyRow("lowfreq", "non_trading_weekday", "lowfreq:offday_reference_refresh", "08:30", "refresh slow/reference data on non-trading weekday", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("midfreq", "non_trading_weekday", "midfreq:offday_skip", "12:00", "no regular midfreq reporting cadence on non-trading weekday", False, 1800),
    SchedulePolicyRow("highfreq", "non_trading_weekday", "highfreq:offday_skip", "12:00", "no highfreq market session on non-trading weekday", False, 900),
    SchedulePolicyRow("archive", "non_trading_weekday", "archive:offday_archive", "21:30", "legacy archive path retained for coexistence/manual fallback on non-trading weekdays", False, 3600, max_retries=1, group_name="archive_legacy"),
    SchedulePolicyRow("archive_v2", "non_trading_weekday", "archive_v2:offday_skip", "21:40", "Archive V2 nightly production is trading-day scoped; offday catch-up remains manual/backfill", False, 5400, max_retries=1, group_name="archive_v2_main"),
    # saturday
    SchedulePolicyRow("lowfreq", "saturday", "lowfreq:saturday_weekly_review_support", "09:00", "support Saturday weekly review / past-week recap", True, 2400, max_retries=1, group_name="weekly_deep"),
    SchedulePolicyRow("midfreq", "saturday", "midfreq:saturday_weekly_review_support", "10:30", "support weekly review dataset refresh", True, 1800, max_retries=1, group_name="post_close_final"),
    SchedulePolicyRow("highfreq", "saturday", "highfreq:saturday_skip", "12:00", "no highfreq weekend session", False, 900),
    SchedulePolicyRow("archive", "saturday", "archive:saturday_archive", "21:30", "legacy archive path retained for coexistence/manual fallback on Saturday", False, 3600, max_retries=1, group_name="archive_legacy"),
    SchedulePolicyRow("archive_v2", "saturday", "archive_v2:saturday_catchup_window", "10:30", "Archive V2 controlled weekend catch-up window: bounded backfill + completeness catch-up + actionable repair drain", True, 7200, max_retries=1, group_name="archive_v2_catchup"),
    # sunday
    SchedulePolicyRow("lowfreq", "sunday", "lowfreq:sunday_next_week_preview_support", "09:00", "support Sunday next-week preview/setup", True, 2400, max_retries=1, group_name="weekly_deep"),
    SchedulePolicyRow("midfreq", "sunday", "midfreq:sunday_preview_support", "10:30", "refresh swing/close-support data for next-week preview", True, 1800, max_retries=1, group_name="post_close_final"),
    SchedulePolicyRow("highfreq", "sunday", "highfreq:sunday_skip", "12:00", "no highfreq weekend session", False, 900),
    SchedulePolicyRow("archive", "sunday", "archive:sunday_archive", "21:30", "legacy archive path retained for coexistence/manual fallback on Sunday", False, 3600, max_retries=1, group_name="archive_legacy"),
    SchedulePolicyRow("archive_v2", "sunday", "archive_v2:sunday_catchup_window", "10:30", "Archive V2 controlled weekend catch-up window: bounded backfill + completeness catch-up + actionable repair drain", True, 7200, max_retries=1, group_name="archive_v2_catchup"),
]
