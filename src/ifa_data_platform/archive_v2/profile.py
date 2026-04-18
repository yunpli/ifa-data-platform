from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


VALID_MODES = {'single_day', 'date_range', 'backfill', 'delete'}
VALID_STATUSES = {'completed', 'partial', 'incomplete', 'missing', 'retry_needed', 'superseded', 'deleted'}


@dataclass
class ArchiveProfile:
    profile_name: str
    mode: str
    include_daily: bool = True
    include_60m: bool = False
    include_15m: bool = False
    include_1m: bool = False
    include_business_families: bool = True
    include_tradable_families: bool = True
    include_signal_families: bool = False
    broad_market: bool = True
    family_groups: list[str] = field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    backfill_days: int | None = None
    repair_incomplete: bool = False
    delete_scope: dict[str, Any] | None = None
    dry_run: bool = False
    write_enabled: bool = False
    notes: str | None = None


def load_profile(path: str | Path) -> ArchiveProfile:
    raw = json.loads(Path(path).read_text())
    return ArchiveProfile(**raw)


def validate_profile(profile: ArchiveProfile) -> list[str]:
    errors: list[str] = []
    if not profile.profile_name:
        errors.append('profile_name is required')
    if profile.mode not in VALID_MODES:
        errors.append(f'mode must be one of {sorted(VALID_MODES)}')
    if profile.mode == 'single_day' and not profile.start_date:
        errors.append('single_day requires start_date')
    if profile.mode == 'date_range' and (not profile.start_date or not profile.end_date):
        errors.append('date_range requires start_date and end_date')
    if profile.mode == 'backfill' and not profile.backfill_days:
        errors.append('backfill requires backfill_days')
    if profile.mode == 'delete' and not profile.delete_scope:
        errors.append('delete requires delete_scope')
    if not any([profile.include_daily, profile.include_60m, profile.include_15m, profile.include_1m]):
        errors.append('at least one frequency layer must be enabled')
    return errors
