"""Business Layer selector reader and normalized target manifest support.

This module is the runtime-side contract between the Business Layer focus lists
and the H/M/L/archive workers.

Execution rules implemented here:
- highfreq collects only key-focus scope
- midfreq and lowfreq collect focus scope
- archive scope is frequency-aware and driven by focus/key-focus families
- futures / commodity / precious-metal families keep their own list namespaces
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine

RUNTIME_LANES = {"lowfreq", "midfreq", "archive", "highfreq"}
KEY_FOCUS_LIST_TYPES = {
    "key_focus",
    "tech_key_focus",
    "futures_key_focus",
    "commodity_key_focus",
    "precious_metal_key_focus",
    "metal_key_focus",
    "black_chain_key_focus",
    "chemical_key_focus",
    "agri_key_focus",
}
FOCUS_LIST_TYPES = {
    "focus",
    "tech_focus",
    "futures_focus",
    "commodity_focus",
    "precious_metal_focus",
    "metal_focus",
    "black_chain_focus",
    "chemical_focus",
    "agri_focus",
}
ARCHIVE_MINUTE_FREQUENCIES = {"1min", "15min", "60min", "daily"}


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
    lane_reason: str


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
    def __init__(self) -> None:
        self.engine = make_engine()

    def fetch_selector_rows(self, scope: SelectorScope) -> list[dict[str, Any]]:
        filters = ["fl.owner_type = :owner_type", "fl.owner_id = :owner_id"]
        params: dict[str, Any] = {"owner_type": scope.owner_type, "owner_id": scope.owner_id}

        if not scope.include_inactive:
            filters.extend(["fl.is_active = TRUE", "fli.is_active = TRUE"])

        if scope.list_names:
            filters.append("fl.name = ANY(:list_names)")
            params["list_names"] = list(scope.list_names)

        if scope.list_types:
            filters.append("fl.list_type = ANY(:list_types)")
            params["list_types"] = list(scope.list_types)

        sql_templates = [
            f"""
            WITH list_rules AS (
                SELECT list_id, jsonb_object_agg(rule_key, rule_value) AS rule_map
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
                COALESCE(fli.symbol_or_series_id, fli.symbol) AS symbol,
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
            ORDER BY fl.list_type, fl.name, fl.frequency_type, fli.priority, COALESCE(fli.symbol_or_series_id, fli.symbol)
            """,
            f"""
            WITH list_rules AS (
                SELECT list_id, jsonb_object_agg(rule_key, rule_value) AS rule_map
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
                fli.symbol AS symbol,
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
            """,
        ]

        last_error = None
        for sql in sql_templates:
            try:
                with self.engine.begin() as conn:
                    rows = conn.execute(text(sql), params).mappings().all()
                    return [dict(r) for r in rows]
            except Exception as exc:  # schema compatibility fallback
                last_error = exc
        raise last_error


class TargetManifestBuilder:
    def __init__(self) -> None:
        self.reader = BusinessLayerSelectorReader()

    def build(self, scope: Optional[SelectorScope] = None) -> TargetManifest:
        scope = scope or SelectorScope()
        rows = self.reader.fetch_selector_rows(scope)
        generated_at = datetime.now(timezone.utc).isoformat()
        items: list[TargetManifestItem] = []
        for row in rows:
            items.extend(self._row_to_items(row, generated_at))
        deduped = self._collapse_duplicates(items)
        ordered = sorted(
            deduped,
            key=lambda i: (i.resolved_lane, i.source_list_type, i.source_list_name, i.priority, i.symbol_or_series_id),
        )
        manifest_hash = self._compute_manifest_hash(scope, ordered)
        return TargetManifest(
            manifest_id=manifest_hash[:16],
            manifest_hash=manifest_hash,
            generated_at=generated_at,
            selector_scope={
                "owner_type": scope.owner_type,
                "owner_id": scope.owner_id,
                "list_names": list(scope.list_names),
                "list_types": list(scope.list_types),
                "include_inactive": scope.include_inactive,
            },
            items=ordered,
        )

    def _row_to_items(self, row: dict[str, Any], generated_at: str) -> list[TargetManifestItem]:
        theme_tags = self._resolve_theme_tags(row)
        validation_status = self._resolve_validation_status(row)
        items: list[TargetManifestItem] = []
        for lane, lane_reason in self._resolve_lanes(row):
            granularity = self._resolve_granularity(row, lane)
            worker_type = self._resolve_worker_type(row, lane)
            adapter_policy = self._resolve_adapter_policy(row, lane, granularity)
            items.append(
                TargetManifestItem(
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
                    asset_category=row["asset_category"] or row["asset_type"] or "unknown",
                    priority=int(row["priority"] or 100),
                    theme_tags=theme_tags,
                    resolved_lane=lane,
                    resolved_worker_type=worker_type,
                    resolved_granularity=granularity,
                    source_adapter_policy=adapter_policy,
                    is_active=bool(row["list_is_active"] and row["item_is_active"]),
                    dedupe_key=self._dedupe_key(row, lane, granularity),
                    selection_reason=self._selection_reason(row, lane, lane_reason),
                    validation_status=validation_status,
                    lane_reason=lane_reason,
                )
            )
        return items

    def _resolve_theme_tags(self, row: dict[str, Any]) -> tuple[str, ...]:
        tags = []
        rule_map = dict(row["rule_map"] or {})
        if rule_map.get("theme"):
            tags.append(rule_map["theme"])
        if str(row["list_name"]).startswith("tech_") and "technology" not in tags:
            tags.append("technology")
        return tuple(tags)

    def _resolve_lanes(self, row: dict[str, Any]) -> list[tuple[str, str]]:
        list_type = str(row.get("list_type") or "")
        freq = str(row.get("frequency_type") or "none")
        asset = str(row.get("asset_category") or row.get("asset_type") or "unknown")

        lanes: list[tuple[str, str]] = []
        if list_type in FOCUS_LIST_TYPES or list_type in KEY_FOCUS_LIST_TYPES:
            lanes.append(("lowfreq", "focus_scope_lowfreq"))
            lanes.append(("midfreq", "focus_scope_midfreq"))
        if list_type in KEY_FOCUS_LIST_TYPES:
            lanes.append(("highfreq", "key_focus_scope_highfreq"))
        if freq in ARCHIVE_MINUTE_FREQUENCIES and (list_type in FOCUS_LIST_TYPES or list_type in KEY_FOCUS_LIST_TYPES):
            lanes.append(("archive", f"focus_scope_archive_{freq}"))
        if list_type == "archive_targets":
            lanes.append(("archive", "archive_targets_frequency_mapping"))

        if not lanes:
            return [("lowfreq", "default_fallback_lowfreq")]

        out: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for lane, reason in lanes:
            if lane in {"midfreq", "highfreq"} and asset not in {"stock", "index", "etf", "futures", "commodity", "precious_metal", "metal", "black_chain", "chemical", "agri", "agricultural", "base_metal"}:
                continue
            key = (lane, reason)
            if key not in seen:
                seen.add(key)
                out.append(key)
        return out

    def _resolve_granularity(self, row: dict[str, Any], lane: str) -> str:
        freq = row["frequency_type"] or "none"
        if lane in {"archive", "highfreq"}:
            return freq
        return "none"

    def _resolve_worker_type(self, row: dict[str, Any], lane: str) -> str:
        asset = row["asset_category"] or row["asset_type"] or "unknown"
        return f"{lane}_{asset}_worker"

    def _resolve_adapter_policy(self, row: dict[str, Any], lane: str, granularity: str) -> str:
        asset = str(row["asset_category"] or row["asset_type"] or "unknown")
        if lane == "midfreq":
            return f"tushare_midfreq_{asset}"
        if lane == "highfreq":
            if asset in {"stock", "index", "etf"}:
                return "tushare_stk_mins"
            return "tushare_ft_mins"
        if lane == "archive":
            if granularity in {"1min", "15min", "60min"}:
                return "tushare_intraday_archive"
            return "tushare_daily_archive"
        return f"tushare_lowfreq_{asset}"

    def _resolve_validation_status(self, row: dict[str, Any]) -> str:
        symbol = str(row.get("symbol") or "")
        asset = str(row.get("asset_category") or row.get("asset_type") or "")
        if asset == "stock" and (symbol.endswith(".SZ") or symbol.endswith(".SH")):
            return "eligible_stock_symbol"
        if asset in {"index", "etf"} and "." in symbol:
            return "eligible_exchange_symbol"
        if asset in {"futures", "commodity", "precious_metal", "metal", "black_chain", "chemical", "agri", "agricultural", "base_metal"}:
            return "eligible_contract_alias_or_code"
        return "unchecked"

    def _selection_reason(self, row: dict[str, Any], lane: str, lane_reason: str) -> str:
        return f"business_layer:{row['list_name']}:{row['list_type']}->{lane}:{row['asset_category']}:{lane_reason}"

    def _collapse_duplicates(self, items: list[TargetManifestItem]) -> list[TargetManifestItem]:
        chosen: dict[str, TargetManifestItem] = {}
        for item in items:
            current = chosen.get(item.dedupe_key)
            if current is None or self._item_preference(item) < self._item_preference(current):
                chosen[item.dedupe_key] = item
        return list(chosen.values())

    def _item_preference(self, item: TargetManifestItem) -> tuple[int, int, int, str, str]:
        list_type_rank = 0 if item.source_list_type in KEY_FOCUS_LIST_TYPES else 1
        lane_rank = 0 if item.resolved_lane in {"lowfreq", "midfreq"} else 1
        return (
            lane_rank,
            list_type_rank,
            int(item.priority),
            item.source_list_name,
            item.symbol_or_series_id,
        )

    def _dedupe_key(self, row: dict[str, Any], lane: str, granularity: str) -> str:
        return f"{lane}|{granularity}|{row['asset_category']}|{row['symbol']}"

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
