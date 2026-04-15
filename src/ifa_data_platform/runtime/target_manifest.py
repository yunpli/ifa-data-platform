"""Business Layer selector reader and normalized target manifest support.

This module is the first concrete implementation step of the approved
Trailblazer upgrade path:
- read Business Layer selector inputs from ifa2.focus_* tables (read-only)
- resolve them into a normalized target manifest
- map business-layer list semantics into execution lanes
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine

RUNTIME_LANES = {"lowfreq", "midfreq", "archive", "highfreq"}


@dataclass(frozen=True)
class SelectorScope:
    owner_type: str = "default"
    owner_id: str = "default"
    list_names: tuple[str, ...] = ()
    list_types: tuple[str, ...] = ()
    include_inactive: bool = False


@dataclass(frozen=True)
class TargetManifestItem:
    generated_at: str
    source_owner_type: str
    source_owner_id: str
    source_list_name: str
    source_list_type: str
    source_frequency_type: str
    source_asset_type: str
    source_rule_map: dict[str, str]
    symbol_or_series_id: str
    display_name: str
    asset_category: str
    priority: int
    theme_tags: tuple[str, ...]
    resolved_lane: str
    resolved_worker_type: str
    resolved_granularity: str
    source_adapter_policy: str
    is_active: bool
    dedupe_key: str
    selection_reason: str
    validation_status: str


@dataclass(frozen=True)
class TargetManifest:
    manifest_id: str
    manifest_hash: str
    generated_at: str
    selector_scope: dict[str, Any]
    items: list[TargetManifestItem]

    @property
    def item_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "manifest_hash": self.manifest_hash,
            "generated_at": self.generated_at,
            "selector_scope": self.selector_scope,
            "items": [asdict(i) for i in self.items],
            "item_count": len(self.items),
        }


class BusinessLayerSelectorReader:
    """Read-only reader over Business Layer selector tables."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def fetch_selector_rows(self, scope: SelectorScope) -> list[dict[str, Any]]:
        filters = [
            "fl.owner_type = :owner_type",
            "fl.owner_id = :owner_id",
        ]
        params: dict[str, Any] = {
            "owner_type": scope.owner_type,
            "owner_id": scope.owner_id,
        }

        if not scope.include_inactive:
            filters.extend(["fl.is_active = TRUE", "fli.is_active = TRUE"])

        if scope.list_names:
            filters.append("fl.name = ANY(:list_names)")
            params["list_names"] = list(scope.list_names)

        if scope.list_types:
            filters.append("fl.list_type = ANY(:list_types)")
            params["list_types"] = list(scope.list_types)

        sql = f"""
        WITH list_rules AS (
            SELECT
                list_id,
                jsonb_object_agg(rule_key, rule_value) AS rule_map
            FROM ifa2.focus_list_rules
            GROUP BY list_id
        )
        SELECT
            fl.id AS list_id,
            fl.owner_type,
            fl.owner_id,
            fl.list_type,
            fl.name AS list_name,
            fl.asset_type,
            fl.frequency_type,
            fl.is_active AS list_is_active,
            COALESCE(lr.rule_map, '{{}}'::jsonb) AS rule_map,
            fli.id AS item_id,
            fli.symbol,
            fli.name AS item_name,
            fli.asset_category,
            fli.priority,
            fli.source,
            fli.notes,
            fli.is_active AS item_is_active
        FROM ifa2.focus_lists fl
        JOIN ifa2.focus_list_items fli ON fli.list_id = fl.id
        LEFT JOIN list_rules lr ON lr.list_id = fl.id
        WHERE {' AND '.join(filters)}
        ORDER BY fl.list_type, fl.name, fl.frequency_type, fli.priority, fli.symbol
        """

        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
            return [dict(r) for r in rows]


class TargetManifestBuilder:
    """Build a normalized target manifest from Business Layer selector rows."""

    def __init__(self) -> None:
        self.reader = BusinessLayerSelectorReader()

    def build(self, scope: Optional[SelectorScope] = None) -> TargetManifest:
        scope = scope or SelectorScope()
        rows = self.reader.fetch_selector_rows(scope)
        generated_at = datetime.now(timezone.utc).isoformat()
        items = [self._row_to_item(row, generated_at) for row in rows]
        deduped = self._dedupe_items(items)
        manifest_hash = self._compute_manifest_hash(scope, deduped)
        manifest_id = manifest_hash[:16]
        return TargetManifest(
            manifest_id=manifest_id,
            manifest_hash=manifest_hash,
            generated_at=generated_at,
            selector_scope={
                "owner_type": scope.owner_type,
                "owner_id": scope.owner_id,
                "list_names": list(scope.list_names),
                "list_types": list(scope.list_types),
                "include_inactive": scope.include_inactive,
            },
            items=deduped,
        )

    def _row_to_item(self, row: dict[str, Any], generated_at: str) -> TargetManifestItem:
        theme_tags = self._resolve_theme_tags(row)
        lane = self._resolve_lane(row)
        granularity = self._resolve_granularity(row, lane)
        worker_type = self._resolve_worker_type(row, lane)
        adapter_policy = self._resolve_adapter_policy(row, lane)
        validation_status = self._resolve_validation_status(row)
        reason = self._selection_reason(row, lane)
        dedupe_key = self._dedupe_key(row, lane, granularity)
        return TargetManifestItem(
            generated_at=generated_at,
            source_owner_type=row["owner_type"],
            source_owner_id=row["owner_id"],
            source_list_name=row["list_name"],
            source_list_type=row["list_type"],
            source_frequency_type=row["frequency_type"] or "none",
            source_asset_type=row["asset_type"],
            source_rule_map=dict(row["rule_map"] or {}),
            symbol_or_series_id=row["symbol"],
            display_name=row["item_name"],
            asset_category=row["asset_category"],
            priority=int(row["priority"] or 100),
            theme_tags=theme_tags,
            resolved_lane=lane,
            resolved_worker_type=worker_type,
            resolved_granularity=granularity,
            source_adapter_policy=adapter_policy,
            is_active=bool(row["list_is_active"] and row["item_is_active"]),
            dedupe_key=dedupe_key,
            selection_reason=reason,
            validation_status=validation_status,
        )

    def _resolve_theme_tags(self, row: dict[str, Any]) -> tuple[str, ...]:
        tags = []
        rule_map = dict(row["rule_map"] or {})
        if rule_map.get("theme"):
            tags.append(rule_map["theme"])
        if str(row["list_name"]).startswith("tech_") and "technology" not in tags:
            tags.append("technology")
        return tuple(tags)

    def _resolve_lane(self, row: dict[str, Any]) -> str:
        if row["list_type"] == "archive_targets":
            return "archive"
        if row["list_type"] in {"key_focus", "focus"}:
            # conservative first implementation:
            # focus-family lists resolve to lowfreq production lane by default,
            # with downstream room for future multi-lane expansion.
            return "lowfreq"
        return "lowfreq"

    def _resolve_granularity(self, row: dict[str, Any], lane: str) -> str:
        freq = row["frequency_type"] or "none"
        if lane == "archive":
            return freq
        return "none"

    def _resolve_worker_type(self, row: dict[str, Any], lane: str) -> str:
        asset = row["asset_category"]
        if lane == "archive":
            return f"archive_{asset}_worker"
        return f"{lane}_{asset}_worker"

    def _resolve_adapter_policy(self, row: dict[str, Any], lane: str) -> str:
        asset = row["asset_category"]
        if asset == "stock":
            return "tushare_stock"
        if asset == "macro":
            return "tushare_macro"
        if asset in {"futures", "commodity", "precious_metal"}:
            return "tushare_futures"
        return f"default_{lane}"

    def _resolve_validation_status(self, row: dict[str, Any]) -> str:
        # First implementation keeps validation cheap and deterministic.
        if row["asset_category"] == "stock" and (row["symbol"].endswith('.SZ') or row["symbol"].endswith('.SH')):
            return "eligible_stock_symbol"
        return "unchecked"

    def _selection_reason(self, row: dict[str, Any], lane: str) -> str:
        return (
            f"business_layer:{row['list_name']}:{row['list_type']}"
            f"->{lane}:{row['asset_category']}"
        )

    def _dedupe_key(self, row: dict[str, Any], lane: str, granularity: str) -> str:
        return f"{lane}|{granularity}|{row['asset_category']}|{row['symbol']}"

    def _dedupe_items(self, items: Iterable[TargetManifestItem]) -> list[TargetManifestItem]:
        best: dict[str, TargetManifestItem] = {}
        for item in items:
            current = best.get(item.dedupe_key)
            if current is None or item.priority < current.priority:
                best[item.dedupe_key] = item
        return sorted(
            best.values(),
            key=lambda i: (i.resolved_lane, i.source_list_type, i.source_list_name, i.priority, i.symbol_or_series_id),
        )

    def _compute_manifest_hash(self, scope: SelectorScope, items: list[TargetManifestItem]) -> str:
        payload = {
            "scope": {
                "owner_type": scope.owner_type,
                "owner_id": scope.owner_id,
                "list_names": list(scope.list_names),
                "list_types": list(scope.list_types),
                "include_inactive": scope.include_inactive,
            },
            "items": [asdict(i) for i in items],
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def build_target_manifest(scope: Optional[SelectorScope] = None) -> TargetManifest:
    return TargetManifestBuilder().build(scope)
