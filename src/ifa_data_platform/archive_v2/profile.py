from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArchiveProfile:
    profile_name: str
    mode: str = 'single_day'
    include_daily: bool = True
    include_60m: bool = False
    include_15m: bool = False
    include_1m: bool = False
    include_business_families: bool = True
    include_tradable_families: bool = True
    include_signal_families: bool = True
    broad_market: bool = True
    family_groups: list[str] = field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    backfill_days: int | None = None
    repair_incomplete: bool = False
    dry_run: bool = False
    write_enabled: bool = True
    notes: str | None = None
    symbol_allowlist: list[str] | None = None
    symbol_limit: int | None = None


def load_profile(path: str | Path) -> ArchiveProfile:
    payload = json.loads(Path(path).read_text())
    return ArchiveProfile(**payload)


def validate_profile(profile: ArchiveProfile) -> list[str]:
    errors: list[str] = []
    if not profile.profile_name:
        errors.append('profile_name is required')
    if profile.mode not in {'single_day', 'date_range', 'backfill', 'delete'}:
        errors.append(f'unsupported mode {profile.mode}')
    if profile.mode == 'single_day' and not profile.start_date:
        errors.append('single_day mode requires start_date')
    if profile.mode == 'date_range' and (not profile.start_date or not profile.end_date):
        errors.append('date_range mode requires start_date and end_date')
    if profile.mode == 'backfill' and not (profile.backfill_days or (profile.start_date and profile.end_date)):
        errors.append('backfill mode requires backfill_days or start_date/end_date')
    if not any([profile.include_daily, profile.include_60m, profile.include_15m, profile.include_1m]) and not profile.family_groups:
        errors.append('at least one frequency layer must be enabled or explicit family_groups must be provided')
    if profile.symbol_allowlist is not None and len(profile.symbol_allowlist) == 0:
        errors.append('symbol_allowlist cannot be empty when provided')
    if profile.symbol_limit is not None and profile.symbol_limit <= 0:
        errors.append('symbol_limit must be > 0 when provided')
    return errors
