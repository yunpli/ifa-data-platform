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
    SchedulePolicyRow("lowfreq", "trading_day", "lowfreq:trade_day_0400", "04:00", "trading-day lowfreq refresh window", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_0600", "06:00", "trading-day midfreq support window", True, 1800, max_retries=1, group_name="early_support"),
    SchedulePolicyRow("lowfreq", "trading_day", "lowfreq:trade_day_0700", "07:00", "trading-day lowfreq refresh window", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_0830", "08:30", "trading-day midfreq support window", True, 1800, max_retries=1, group_name="early_support"),
    SchedulePolicyRow("lowfreq", "trading_day", "lowfreq:trade_day_0850", "08:50", "trading-day lowfreq refresh window", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_0908", "09:08", "trading-day highfreq support window", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_0905", "09:05", "trading-day midfreq support window", True, 1800, max_retries=1, group_name="early_support"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_0917", "09:17", "trading-day highfreq support window", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_0927", "09:27", "trading-day highfreq support window", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_1000", "10:00", "trading-day highfreq support window", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_1100", "11:00", "trading-day highfreq support window", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_1105", "11:05", "trading-day midfreq support window", True, 1800, max_retries=1, group_name="midday_final"),
    SchedulePolicyRow("lowfreq", "trading_day", "lowfreq:trade_day_1135", "11:35", "trading-day lowfreq refresh window", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_1200", "12:00", "trading-day highfreq support window", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_1305", "13:05", "trading-day highfreq support window", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_1330", "13:30", "trading-day midfreq support window", True, 1800, max_retries=1, group_name="midday_final"),
    SchedulePolicyRow("lowfreq", "trading_day", "lowfreq:trade_day_1400", "14:00", "trading-day lowfreq refresh window", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_1405", "14:05", "trading-day highfreq support window", True, 900, max_retries=1, group_name="intraday_core"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_1430", "14:30", "trading-day midfreq support window", True, 1800, max_retries=1, group_name="post_close_final"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_1505", "15:05", "trading-day highfreq support window", True, 900, max_retries=1, group_name="close_core"),
    SchedulePolicyRow("highfreq", "trading_day", "highfreq:trade_day_1545", "15:45", "trading-day highfreq support window", True, 900, max_retries=1, group_name="close_core"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_1600", "16:00", "trading-day midfreq support window", True, 2400, max_retries=2, group_name="post_close_final"),
    SchedulePolicyRow("lowfreq", "trading_day", "lowfreq:trade_day_1700", "17:00", "trading-day lowfreq refresh window", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("midfreq", "trading_day", "midfreq:trade_day_1715", "17:15", "trading-day midfreq support window", True, 2400, max_retries=2, group_name="post_close_final"),
    SchedulePolicyRow("lowfreq", "trading_day", "lowfreq:trade_day_2200", "22:00", "trading-day lowfreq refresh window", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("archive", "trading_day", "archive:trade_day_evening_archive", "21:30", "legacy archive path retained for coexistence/manual fallback; no longer default nightly production path", False, 3600, max_retries=1, group_name="archive_legacy"),
    SchedulePolicyRow("archive_v2", "trading_day", "archive_v2:trade_day_nightly_daily_final", "21:40", "Archive V2 steady-state nightly daily/final truth production", True, 5400, max_retries=1, group_name="archive_v2_main"),
    # non-trading weekday
    SchedulePolicyRow("lowfreq", "non_trading_weekday", "lowfreq:offday_0730", "07:30", "non-trading weekday lowfreq refresh", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("midfreq", "non_trading_weekday", "midfreq:offday_0930", "09:30", "non-trading weekday midfreq support", True, 1800, max_retries=1, group_name="offday_support"),
    SchedulePolicyRow("midfreq", "non_trading_weekday", "midfreq:offday_1100", "11:00", "non-trading weekday midfreq support", True, 1800, max_retries=1, group_name="offday_support"),
    SchedulePolicyRow("highfreq", "non_trading_weekday", "highfreq:offday_skip", "12:00", "no highfreq market session on non-trading weekday", False, 900),
    SchedulePolicyRow("lowfreq", "non_trading_weekday", "lowfreq:offday_1200", "12:00", "non-trading weekday lowfreq refresh", True, 1800, max_retries=1, group_name="daily_light"),
    SchedulePolicyRow("archive", "non_trading_weekday", "archive:offday_archive", "21:30", "legacy archive path retained for coexistence/manual fallback on non-trading weekdays", False, 3600, max_retries=1, group_name="archive_legacy"),
    SchedulePolicyRow("archive_v2", "non_trading_weekday", "archive_v2:offday_skip", "21:40", "Archive V2 nightly production is trading-day scoped; offday catch-up remains manual/backfill", False, 5400, max_retries=1, group_name="archive_v2_main"),
    SchedulePolicyRow("lowfreq", "non_trading_weekday", "lowfreq:offday_2200", "22:00", "non-trading weekday lowfreq refresh", True, 1800, max_retries=1, group_name="daily_light"),
    # saturday
    SchedulePolicyRow("lowfreq", "saturday", "lowfreq:saturday_1030", "10:30", "support Saturday weekly review / past-week recap", True, 2400, max_retries=1, group_name="weekly_deep"),
    SchedulePolicyRow("midfreq", "saturday", "midfreq:saturday_0900", "09:00", "support weekly review dataset refresh", True, 1800, max_retries=1, group_name="weekly_review"),
    SchedulePolicyRow("midfreq", "saturday", "midfreq:saturday_1100", "11:00", "support weekly review dataset refresh", True, 1800, max_retries=1, group_name="weekly_review"),
    SchedulePolicyRow("highfreq", "saturday", "highfreq:saturday_skip", "12:00", "no highfreq weekend session", False, 900),
    SchedulePolicyRow("archive", "saturday", "archive:saturday_archive", "21:30", "legacy archive path retained for coexistence/manual fallback on Saturday", False, 3600, max_retries=1, group_name="archive_legacy"),
    SchedulePolicyRow("archive_v2", "saturday", "archive_v2:saturday_catchup_window", "10:30", "Archive V2 controlled weekend catch-up window: bounded backfill + completeness catch-up + actionable repair drain", True, 7200, max_retries=1, group_name="archive_v2_catchup"),
    SchedulePolicyRow("lowfreq", "saturday", "lowfreq:saturday_2200", "22:00", "support Saturday weekly review / past-week recap", True, 2400, max_retries=1, group_name="weekly_deep"),
    # sunday
    SchedulePolicyRow("lowfreq", "sunday", "lowfreq:sunday_1030", "10:30", "support Sunday next-week preview/setup", True, 2400, max_retries=1, group_name="weekly_deep"),
    SchedulePolicyRow("midfreq", "sunday", "midfreq:sunday_1030", "10:30", "refresh swing/close-support data for next-week preview", True, 1800, max_retries=1, group_name="weekly_preview"),
    SchedulePolicyRow("midfreq", "sunday", "midfreq:sunday_1130", "11:30", "refresh swing/close-support data for next-week preview", True, 1800, max_retries=1, group_name="weekly_preview"),
    SchedulePolicyRow("highfreq", "sunday", "highfreq:sunday_skip", "12:00", "no highfreq weekend session", False, 900),
    SchedulePolicyRow("archive", "sunday", "archive:sunday_archive", "21:30", "legacy archive path retained for coexistence/manual fallback on Sunday", False, 3600, max_retries=1, group_name="archive_legacy"),
    SchedulePolicyRow("archive_v2", "sunday", "archive_v2:sunday_catchup_window", "10:30", "Archive V2 controlled weekend catch-up window: bounded backfill + completeness catch-up + actionable repair drain", True, 7200, max_retries=1, group_name="archive_v2_catchup"),
    SchedulePolicyRow("lowfreq", "sunday", "lowfreq:sunday_2200", "22:00", "support Sunday next-week preview/setup", True, 2400, max_retries=1, group_name="weekly_deep"),
]
