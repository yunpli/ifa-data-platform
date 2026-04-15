"""Archive target manifest snapshot and delta support.

First implementation batch focuses on detection and planning, not full catch-up execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from ifa_data_platform.runtime.target_manifest import SelectorScope, TargetManifest, TargetManifestItem, build_target_manifest


@dataclass(frozen=True)
class ArchiveDeltaItem:
    change_type: str
    dedupe_key: str
    symbol_or_series_id: str
    asset_category: str
    granularity: str
    source_list_name: str
    suggested_backfill_start: str
    suggested_backfill_end: str
    backlog_priority: str
    reason: str


def build_archive_manifest(scope: Optional[SelectorScope] = None) -> TargetManifest:
    scope = scope or SelectorScope(list_types=("archive_targets",))
    return build_target_manifest(scope)


def diff_archive_manifests(previous: TargetManifest, current: TargetManifest) -> list[ArchiveDeltaItem]:
    prev_map = {i.dedupe_key: i for i in previous.items if i.resolved_lane == "archive"}
    cur_map = {i.dedupe_key: i for i in current.items if i.resolved_lane == "archive"}
    deltas: list[ArchiveDeltaItem] = []

    for key, item in cur_map.items():
        if key not in prev_map:
            deltas.append(_new_target_delta(item))
            continue
        prev = prev_map[key]
        if prev.display_name != item.display_name or prev.priority != item.priority or prev.theme_tags != item.theme_tags:
            deltas.append(
                ArchiveDeltaItem(
                    change_type="metadata_changed",
                    dedupe_key=item.dedupe_key,
                    symbol_or_series_id=item.symbol_or_series_id,
                    asset_category=item.asset_category,
                    granularity=item.resolved_granularity,
                    source_list_name=item.source_list_name,
                    suggested_backfill_start="",
                    suggested_backfill_end="",
                    backlog_priority="none",
                    reason="metadata changed without identity removal",
                )
            )

    for key, prev in prev_map.items():
        if key not in cur_map:
            deltas.append(
                ArchiveDeltaItem(
                    change_type="removed",
                    dedupe_key=prev.dedupe_key,
                    symbol_or_series_id=prev.symbol_or_series_id,
                    asset_category=prev.asset_category,
                    granularity=prev.resolved_granularity,
                    source_list_name=prev.source_list_name,
                    suggested_backfill_start="",
                    suggested_backfill_end="",
                    backlog_priority="none",
                    reason="target removed from archive membership; preserve history, stop future incremental work",
                )
            )

    return sorted(deltas, key=lambda d: (d.change_type, d.granularity, d.symbol_or_series_id))


def _new_target_delta(item: TargetManifestItem) -> ArchiveDeltaItem:
    end = datetime.now(timezone.utc).date()
    if item.resolved_granularity == "daily":
        start = end - timedelta(days=365)
        priority = "medium_high"
    elif item.resolved_granularity == "15min":
        start = end - timedelta(days=90)
        priority = "medium"
    else:
        start = end - timedelta(days=30)
        priority = "guarded_medium_low"
    return ArchiveDeltaItem(
        change_type="added",
        dedupe_key=item.dedupe_key,
        symbol_or_series_id=item.symbol_or_series_id,
        asset_category=item.asset_category,
        granularity=item.resolved_granularity,
        source_list_name=item.source_list_name,
        suggested_backfill_start=start.isoformat(),
        suggested_backfill_end=end.isoformat(),
        backlog_priority=priority,
        reason=f"new archive target -> create {item.resolved_granularity} catch-up intent",
    )
