from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

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
        ArchivePolicyDecision("stock", "daily", "backfill_from_anchor", ("focus", "key_focus"), True, "daily archive for focus scope"),
        ArchivePolicyDecision("futures", "daily", "backfill_from_anchor", ("futures_focus", "futures_key_focus"), True, "daily archive for focus scope"),
        ArchivePolicyDecision("commodity", "daily", "backfill_from_anchor", ("commodity_focus", "commodity_key_focus", "chemical_focus", "chemical_key_focus", "agri_focus", "agri_key_focus", "black_chain_focus", "black_chain_key_focus", "metal_focus", "metal_key_focus"), True, "daily archive for focus scope"),
        ArchivePolicyDecision("precious_metal", "daily", "backfill_from_anchor", ("precious_metal_focus", "precious_metal_key_focus"), True, "daily archive for focus scope"),
        ArchivePolicyDecision("stock", "15min", "forward_only", ("focus", "key_focus"), True, "15min forward-only focus scope"),
        ArchivePolicyDecision("stock", "1min", "forward_only", ("key_focus",), True, "1min forward-only key focus scope"),
        ArchivePolicyDecision("futures", "15min", "forward_only", ("futures_focus", "futures_key_focus"), True, "15min forward-only focus scope"),
        ArchivePolicyDecision("futures", "1min", "forward_only", ("futures_key_focus",), True, "1min forward-only key focus scope"),
        ArchivePolicyDecision("commodity", "15min", "forward_only", ("commodity_focus", "commodity_key_focus", "chemical_focus", "chemical_key_focus", "agri_focus", "agri_key_focus", "black_chain_focus", "black_chain_key_focus", "metal_focus", "metal_key_focus"), True, "15min forward-only focus scope"),
        ArchivePolicyDecision("commodity", "1min", "forward_only", ("commodity_key_focus", "chemical_key_focus", "agri_key_focus", "black_chain_key_focus", "metal_key_focus"), True, "1min forward-only key focus scope"),
        ArchivePolicyDecision("precious_metal", "15min", "forward_only", ("precious_metal_focus", "precious_metal_key_focus"), True, "15min forward-only focus scope"),
        ArchivePolicyDecision("precious_metal", "1min", "forward_only", ("precious_metal_key_focus",), True, "1min forward-only key focus scope"),
        ArchivePolicyDecision("stock", "60min", "forward_aggregate", ("focus", "key_focus"), True, "60min derived from 15min history"),
        ArchivePolicyDecision("futures", "60min", "forward_aggregate", ("futures_focus", "futures_key_focus"), True, "60min derived from 15min history"),
        ArchivePolicyDecision("commodity", "60min", "forward_aggregate", ("commodity_focus", "commodity_key_focus", "chemical_focus", "chemical_key_focus", "agri_focus", "agri_key_focus", "black_chain_focus", "black_chain_key_focus", "metal_focus", "metal_key_focus"), True, "60min derived from 15min history"),
        ArchivePolicyDecision("precious_metal", "60min", "forward_aggregate", ("precious_metal_focus", "precious_metal_key_focus"), True, "60min derived from 15min history"),
    ]


def archive_scope_symbols(list_types: Iterable[str], *, asset_categories: Optional[set[str]] = None, frequency: Optional[str] = None) -> list[str]:
    manifest = build_target_manifest(SelectorScope(list_types=tuple(list_types)))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in manifest.items:
        if item.resolved_lane != "archive":
            continue
        if frequency and item.resolved_granularity != frequency:
            continue
        if asset_categories and item.asset_category not in asset_categories:
            continue
        if item.symbol_or_series_id not in seen:
            seen.add(item.symbol_or_series_id)
            deduped.append(item.symbol_or_series_id)
    return deduped
