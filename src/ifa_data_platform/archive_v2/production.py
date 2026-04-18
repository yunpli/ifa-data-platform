from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Any

from ifa_data_platform.archive_v2.profile import ArchiveProfile
from ifa_data_platform.archive_v2.runner import ArchiveV2Runner
from ifa_data_platform.runtime.trading_calendar import TradingCalendarService, BJ_TZ

PRODUCTION_NIGHTLY_FAMILIES = [
    'equity_daily',
    'index_daily',
    'etf_daily',
    'non_equity_daily',
    'macro_daily',
    'announcements_daily',
    'news_daily',
    'research_reports_daily',
    'investor_qa_daily',
    'dragon_tiger_daily',
    'limit_up_detail_daily',
    'limit_up_down_status_daily',
    'sector_performance_daily',
    'highfreq_event_stream_daily',
    'highfreq_limit_event_stream_daily',
    'highfreq_sector_breadth_daily',
    'highfreq_sector_heat_daily',
    'highfreq_leader_candidate_daily',
    'highfreq_intraday_signal_state_daily',
]

PRODUCTION_NIGHTLY_PROFILE_NAME = 'archive_v2_production_nightly_daily_final'
PRODUCTION_BACKFILL_PROFILE_NAME = 'archive_v2_production_manual_backfill'
PRODUCTION_REPAIR_PATH = 'scripts/archive_v2_operator_cli.py repair-batch ...'
PRODUCTION_MANUAL_BACKFILL_FAMILIES = [
    'index_daily',
    'macro_daily',
    'announcements_daily',
    'news_daily',
    'research_reports_daily',
    'investor_qa_daily',
    'dragon_tiger_daily',
    'limit_up_detail_daily',
    'limit_up_down_status_daily',
    'sector_performance_daily',
    'highfreq_event_stream_daily',
    'highfreq_limit_event_stream_daily',
    'highfreq_sector_breadth_daily',
    'highfreq_sector_heat_daily',
    'highfreq_leader_candidate_daily',
    'highfreq_intraday_signal_state_daily',
]


def _previous_trading_day(calendar: TradingCalendarService, target_date: date, max_days: int = 14) -> date:
    for offset in range(1, max_days + 1):
        cand = target_date - timedelta(days=offset)
        status = calendar.get_day_status(cand)
        if status.is_trading_day:
            return cand
    return target_date


def resolve_production_business_date(current_time_utc: datetime | None = None) -> str:
    now = current_time_utc or datetime.now(timezone.utc)
    calendar = TradingCalendarService()
    bj_now = now.astimezone(BJ_TZ)
    status = calendar.get_day_status(bj_now.date())
    if status.is_trading_day:
        return bj_now.date().isoformat()
    if status.pretrade_date:
        return status.pretrade_date.isoformat()
    return _previous_trading_day(calendar, bj_now.date()).isoformat()


def build_nightly_profile(business_date: str) -> ArchiveProfile:
    return ArchiveProfile(
        profile_name=PRODUCTION_NIGHTLY_PROFILE_NAME,
        mode='single_day',
        include_daily=True,
        include_60m=False,
        include_15m=False,
        include_1m=False,
        include_business_families=True,
        include_tradable_families=True,
        include_signal_families=True,
        broad_market=True,
        family_groups=list(PRODUCTION_NIGHTLY_FAMILIES),
        start_date=business_date,
        repair_incomplete=False,
        dry_run=False,
        write_enabled=True,
        notes='Archive V2 steady-state nightly production daily/final run',
    )


def build_backfill_profile(start_date: str | None = None, end_date: str | None = None, backfill_days: int | None = None) -> ArchiveProfile:
    if start_date and end_date:
        mode = 'date_range'
    else:
        mode = 'backfill'
    return ArchiveProfile(
        profile_name=PRODUCTION_BACKFILL_PROFILE_NAME,
        mode=mode,
        include_daily=True,
        include_60m=False,
        include_15m=False,
        include_1m=False,
        include_business_families=True,
        include_tradable_families=True,
        include_signal_families=True,
        broad_market=True,
        family_groups=list(PRODUCTION_MANUAL_BACKFILL_FAMILIES),
        start_date=start_date,
        end_date=end_date,
        backfill_days=backfill_days,
        repair_incomplete=False,
        dry_run=False,
        write_enabled=True,
        notes='Archive V2 manual bounded backfill / replay path',
    )


def _write_temp_profile(profile: ArchiveProfile) -> str:
    temp_dir = Path(tempfile.gettempdir()) / 'ifa_archive_v2_profiles'
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / f"{profile.profile_name}_{profile.start_date or profile.end_date or 'window'}.json"
    path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2))
    return str(path)


def run_nightly_production(business_date: str | None = None, trigger_source: str = 'production_nightly_archive_v2') -> dict[str, Any]:
    business_date = business_date or resolve_production_business_date()
    profile = build_nightly_profile(business_date)
    profile_path = _write_temp_profile(profile)
    runner = ArchiveV2Runner(profile_path)
    result = runner.run_with_context(trigger_source=trigger_source, notes=f'Archive V2 nightly production run for {business_date}')
    return {
        'business_date': business_date,
        'profile_name': profile.profile_name,
        'profile_path': profile_path,
        **result,
    }


def run_manual_backfill(start_date: str | None = None, end_date: str | None = None, backfill_days: int | None = None) -> dict[str, Any]:
    profile = build_backfill_profile(start_date=start_date, end_date=end_date, backfill_days=backfill_days)
    profile_path = _write_temp_profile(profile)
    runner = ArchiveV2Runner(profile_path)
    result = runner.run_with_context(trigger_source='manual_archive_v2_backfill', notes='Archive V2 manual bounded backfill/replay')
    return {
        'profile_name': profile.profile_name,
        'profile_path': profile_path,
        **result,
    }
