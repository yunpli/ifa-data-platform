from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Any

from ifa_data_platform.archive_v2.operator import build_repair_batch_notes, select_repair_targets
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
]

PRODUCTION_NIGHTLY_PROFILE_NAME = 'archive_v2_production_nightly_daily_final'
PRODUCTION_BACKFILL_PROFILE_NAME = 'archive_v2_production_manual_backfill'
PRODUCTION_REPAIR_PATH = 'scripts/archive_v2_operator_cli.py repair-batch ...'
OFFICIAL_RUNTIME_NIGHTLY_TRIGGER = 'runtime_archive_v2_nightly'
MANUAL_CLI_NIGHTLY_TRIGGER = 'manual_archive_v2_nightly_cli'
WEEKEND_CATCHUP_TOTAL_BACKFILL_DAYS = 30
WEEKEND_CATCHUP_CHUNK_DAYS = 10
WEEKEND_REPAIR_TARGET_LIMIT = 50
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
]
DISALLOWED_NIGHTLY_FAMILIES = {
    'highfreq_event_stream_daily',
    'highfreq_limit_event_stream_daily',
    'highfreq_sector_breadth_daily',
    'highfreq_sector_heat_daily',
    'highfreq_leader_candidate_daily',
    'highfreq_intraday_signal_state_daily',
    'proxy_1m',
    'proxy_15m',
    'proxy_60m',
    'equity_60m', 'etf_60m', 'index_60m', 'futures_60m', 'commodity_60m', 'precious_metal_60m',
    'equity_15m', 'etf_15m', 'index_15m', 'futures_15m', 'commodity_15m', 'precious_metal_15m',
    'equity_1m', 'etf_1m', 'index_1m', 'futures_1m', 'commodity_1m', 'precious_metal_1m',
}


if DISALLOWED_NIGHTLY_FAMILIES & set(PRODUCTION_NIGHTLY_FAMILIES):
    raise ValueError(f"PRODUCTION_NIGHTLY_FAMILIES contains disallowed entries: {sorted(DISALLOWED_NIGHTLY_FAMILIES & set(PRODUCTION_NIGHTLY_FAMILIES))}")


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


def is_runtime_trading_day(current_time_utc: datetime | None = None) -> bool:
    now = current_time_utc or datetime.now(timezone.utc)
    calendar = TradingCalendarService()
    bj_now = now.astimezone(BJ_TZ)
    return calendar.get_day_status(bj_now.date()).is_trading_day


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
        include_signal_families=False,
        broad_market=True,
        family_groups=list(PRODUCTION_NIGHTLY_FAMILIES),
        start_date=business_date,
        repair_incomplete=False,
        dry_run=False,
        write_enabled=True,
        notes='Archive V2 steady-state nightly production daily/final run without derived highfreq daily families in the primary truth model',
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
        include_signal_families=False,
        broad_market=True,
        family_groups=list(PRODUCTION_MANUAL_BACKFILL_FAMILIES),
        start_date=start_date,
        end_date=end_date,
        backfill_days=backfill_days,
        repair_incomplete=False,
        dry_run=False,
        write_enabled=True,
        notes='Archive V2 manual bounded backfill / replay path without derived highfreq daily families in the primary truth model',
    )


def _write_temp_profile(profile: ArchiveProfile) -> str:
    temp_dir = Path(tempfile.gettempdir()) / 'ifa_archive_v2_profiles'
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / f"{profile.profile_name}_{profile.start_date or profile.end_date or 'window'}.json"
    path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2))
    return str(path)


def run_nightly_production(business_date: str | None = None, trigger_source: str = OFFICIAL_RUNTIME_NIGHTLY_TRIGGER) -> dict[str, Any]:
    explicit_business_date = business_date is not None
    if not explicit_business_date and not is_runtime_trading_day():
        resolved_business_date = resolve_production_business_date()
        return {
            'ok': True,
            'skipped': True,
            'status': 'skipped',
            'business_date': resolved_business_date,
            'profile_name': PRODUCTION_NIGHTLY_PROFILE_NAME,
            'profile_path': None,
            'families': list(PRODUCTION_NIGHTLY_FAMILIES),
            'official_trigger_source': OFFICIAL_RUNTIME_NIGHTLY_TRIGGER,
            'notes': (
                'Archive V2 implicit nightly production skips on Beijing non-trading days; '
                'use manual backfill/catch-up paths instead of replaying the previous trading day as a same-day nightly run'
            ),
        }
    business_date = business_date or resolve_production_business_date()
    profile = build_nightly_profile(business_date)
    profile_path = _write_temp_profile(profile)
    runner = ArchiveV2Runner(profile_path)
    result = runner.run_with_context(trigger_source=trigger_source, notes=f'Archive V2 nightly production run for {business_date}')
    return {
        'business_date': business_date,
        'profile_name': profile.profile_name,
        'profile_path': profile_path,
        'families': list(PRODUCTION_NIGHTLY_FAMILIES),
        'official_trigger_source': OFFICIAL_RUNTIME_NIGHTLY_TRIGGER,
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


def run_weekend_catchup(current_time_utc: datetime | None = None, trigger_source: str = 'runtime_archive_v2_weekend_catchup') -> dict[str, Any]:
    business_date = resolve_production_business_date(current_time_utc)
    remaining_days = WEEKEND_CATCHUP_TOTAL_BACKFILL_DAYS
    backfill_chunks: list[dict[str, Any]] = []
    while remaining_days > 0:
        chunk_days = min(WEEKEND_CATCHUP_CHUNK_DAYS, remaining_days)
        chunk = run_manual_backfill(end_date=business_date, backfill_days=chunk_days)
        backfill_chunks.append({
            'chunk_backfill_days': chunk_days,
            **chunk,
        })
        remaining_days -= chunk_days

    backfill_statuses = {chunk.get('status') for chunk in backfill_chunks}
    backfill = {
        'status': 'completed' if backfill_statuses == {'completed'} else 'partial',
        'chunk_count': len(backfill_chunks),
        'total_backfill_days': WEEKEND_CATCHUP_TOTAL_BACKFILL_DAYS,
        'chunk_backfill_days': WEEKEND_CATCHUP_CHUNK_DAYS,
        'chunks': backfill_chunks,
    }

    profile = build_nightly_profile(business_date)
    profile_path = _write_temp_profile(profile)
    runner = ArchiveV2Runner(profile_path)
    repair_targets = select_repair_targets(limit=WEEKEND_REPAIR_TARGET_LIMIT, actionable_only=True, include_non_actionable=False, include_suppressed=False, include_claimed=False)
    repair_notes = build_repair_batch_notes(repair_targets, {'limit': WEEKEND_REPAIR_TARGET_LIMIT, 'weekend_catchup': True}) if repair_targets else 'weekend catch-up found no actionable repair targets'
    repair_result = runner.run_selected_targets(repair_targets, trigger_source='operator_repair_batch', notes=repair_notes) if repair_targets else {'status': 'completed', 'selected_targets': 0, 'notes': repair_notes}

    final_status = 'completed'
    if backfill.get('status') != 'completed' or repair_result.get('status') not in {'completed', 'success'}:
        final_status = 'partial'
    return {
        'business_date': business_date,
        'profile_name': profile.profile_name,
        'profile_path': profile_path,
        'status': final_status,
        'backfill': backfill,
        'repair': repair_result,
        'notes': (
            f"weekend catch-up total_backfill_days={WEEKEND_CATCHUP_TOTAL_BACKFILL_DAYS} "
            f"chunk_backfill_days={WEEKEND_CATCHUP_CHUNK_DAYS} "
            f"repair_targets={repair_result.get('selected_targets', 0)}"
        ),
    }
