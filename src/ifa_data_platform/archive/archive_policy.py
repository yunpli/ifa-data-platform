from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from ifa_data_platform.runtime.target_manifest import SelectorScope, build_target_manifest

BACKFILL_ANCHOR_DATE = date(2023, 1, 1)


@dataclass(frozen=True)
class ArchivePolicyDecision:
    category: str
    frequency: str
    mode: str
    list_types: tuple[str, ...]
    supported: bool
    reason: str


def archive_policy_matrix() -> list[ArchivePolicyDecision]:
    return [
        ArchivePolicyDecision('stock', 'daily', 'backfill_from_anchor', ('all',), True, 'daily archive for tradable objects'),
        ArchivePolicyDecision('futures', 'daily', 'backfill_from_anchor', ('all',), True, 'daily archive for tradable objects'),
        ArchivePolicyDecision('commodity', 'daily', 'backfill_from_anchor', ('all',), True, 'daily archive for tradable objects'),
        ArchivePolicyDecision('precious_metal', 'daily', 'backfill_from_anchor', ('all',), True, 'daily archive for tradable objects'),
        ArchivePolicyDecision('stock', '60min', 'backfill_from_anchor', ('all',), False, '60min source/storage path not implemented yet'),
        ArchivePolicyDecision('futures', '60min', 'backfill_from_anchor', ('all',), False, '60min source/storage path not implemented yet'),
        ArchivePolicyDecision('commodity', '60min', 'backfill_from_anchor', ('all',), False, '60min source/storage path not implemented yet'),
        ArchivePolicyDecision('precious_metal', '60min', 'backfill_from_anchor', ('all',), False, '60min source/storage path not implemented yet'),
        ArchivePolicyDecision('stock', '15min', 'forward_only', ('key_focus', 'focus'), True, '15min is forward archive only'),
        ArchivePolicyDecision('futures', '15min', 'forward_only', ('futures_key_focus', 'futures_focus'), True, '15min is forward archive only'),
        ArchivePolicyDecision('commodity', '15min', 'forward_only', ('commodity_key_focus', 'commodity_focus'), True, '15min is forward archive only'),
        ArchivePolicyDecision('precious_metal', '15min', 'forward_only', ('precious_metal_key_focus', 'precious_metal_focus'), True, '15min is forward archive only'),
        ArchivePolicyDecision('stock', '1min', 'forward_only', ('key_focus',), True, '1min is forward archive only for key focus'),
        ArchivePolicyDecision('futures', '1min', 'forward_only', ('futures_key_focus',), True, '1min is forward archive only for key focus'),
        ArchivePolicyDecision('commodity', '1min', 'forward_only', ('commodity_key_focus',), True, '1min is forward archive only for key focus'),
        ArchivePolicyDecision('precious_metal', '1min', 'forward_only', ('precious_metal_key_focus',), True, '1min is forward archive only for key focus'),
    ]


def archive_scope_symbols(list_types: Iterable[str]) -> list[str]:
    manifest = build_target_manifest(SelectorScope(list_types=tuple(list_types)))
    deduped = []
    seen = set()
    for item in manifest.items:
        if item.resolved_lane != 'archive':
            continue
        if item.symbol_or_series_id not in seen:
            seen.add(item.symbol_or_series_id)
            deduped.append(item.symbol_or_series_id)
    return deduped
