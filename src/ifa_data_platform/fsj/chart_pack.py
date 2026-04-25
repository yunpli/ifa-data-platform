from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any, Iterable, Sequence
import json
import math

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine

DEFAULT_INDEX_SYMBOLS: tuple[tuple[str, str], ...] = (
    ("000001.SH", "上证指数"),
    ("399001.SZ", "深证成指"),
    ("399006.SZ", "创业板指"),
)
DEFAULT_INDEX_WINDOW_DAYS = 20
DEFAULT_FOCUS_WINDOW_DAYS = 20
DEFAULT_FOCUS_LIMIT = 3


@dataclass(frozen=True)
class ChartAsset:
    chart_key: str
    chart_class: str
    title: str
    filename: str
    relative_path: str
    source_window: dict[str, Any]
    status: str
    note: str | None = None
    series_count: int = 0
    symbol_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "chart_key": self.chart_key,
            "chart_class": self.chart_class,
            "title": self.title,
            "filename": self.filename,
            "relative_path": self.relative_path,
            "source_window": self.source_window,
            "status": self.status,
            "note": self.note,
            "series_count": self.series_count,
            "symbol_count": self.symbol_count,
        }


class FSJChartPackBuilder:
    VERSION = "v1"

    def __init__(self, *, engine=None) -> None:
        self.engine = engine or make_engine()

    def build_main_chart_pack(
        self,
        *,
        business_date: str,
        assembled: dict[str, Any],
        package_dir: str | Path,
    ) -> dict[str, Any]:
        package_dir = Path(package_dir)
        charts_dir = package_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)

        assets: list[ChartAsset] = []
        degraded_reasons: list[str] = []

        index_asset = self._build_market_index_chart(business_date=business_date, charts_dir=charts_dir)
        assets.append(index_asset)
        if index_asset.status != "ready":
            degraded_reasons.append(f"{index_asset.chart_key}:{index_asset.note or 'missing'}")

        focus_symbols = self._resolve_focus_symbols(assembled=assembled, limit=DEFAULT_FOCUS_LIMIT)
        focus_line_asset = self._build_focus_line_chart(
            business_date=business_date,
            charts_dir=charts_dir,
            focus_symbols=focus_symbols,
        )
        assets.append(focus_line_asset)
        if focus_line_asset.status != "ready":
            degraded_reasons.append(f"{focus_line_asset.chart_key}:{focus_line_asset.note or 'missing'}")

        focus_bar_asset = self._build_focus_return_bar_chart(
            business_date=business_date,
            charts_dir=charts_dir,
            focus_symbols=focus_symbols,
        )
        assets.append(focus_bar_asset)
        if focus_bar_asset.status != "ready":
            degraded_reasons.append(f"{focus_bar_asset.chart_key}:{focus_bar_asset.note or 'missing'}")

        ready_assets = [asset for asset in assets if asset.status == "ready"]
        manifest = {
            "artifact_type": "fsj_main_chart_pack",
            "artifact_version": self.VERSION,
            "business_date": business_date,
            "chart_count": len(assets),
            "ready_chart_count": len(ready_assets),
            "degrade_status": "ready" if len(ready_assets) == len(assets) else ("partial" if ready_assets else "missing"),
            "degrade_reason": degraded_reasons or None,
            "chart_classes": sorted({asset.chart_class for asset in assets}),
            "assets": [asset.as_dict() for asset in assets],
            "html_embed_blocks": [self._asset_embed_block(asset) for asset in assets],
        }
        manifest_path = charts_dir / "chart_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        manifest["manifest_path"] = str(manifest_path.resolve())
        manifest["relative_manifest_path"] = f"charts/{manifest_path.name}"
        return manifest

    def _resolve_focus_symbols(self, *, assembled: dict[str, Any], limit: int) -> list[str]:
        symbols: list[str] = []
        seen: set[str] = set()
        for section in assembled.get("sections") or []:
            for item in (section.get("lineage") or {}).get("evidence_links") or []:
                ref = str(item.get("ref_key") or "")
                if self._looks_like_symbol(ref) and ref not in seen:
                    seen.add(ref)
                    symbols.append(ref)
            payload = dict(((section.get("lineage") or {}).get("bundle") or {}).get("payload_json") or {})
            degrade = dict(payload.get("degrade") or {})
            for key in ("focus_symbols", "symbols"):
                for symbol in payload.get(key) or degrade.get(key) or []:
                    symbol = str(symbol or "").strip()
                    if self._looks_like_symbol(symbol) and symbol not in seen:
                        seen.add(symbol)
                        symbols.append(symbol)
        if len(symbols) >= limit:
            return symbols[:limit]
        query = text(
            """
            select distinct fi.symbol
            from ifa2.focus_lists fl
            join ifa2.focus_list_items fi on fi.list_id = fl.id
            where fl.is_active = true
              and fi.is_active = true
              and fl.list_type in ('key_focus','focus','tech_key_focus','tech_focus')
              and fi.symbol is not null
            order by case when fl.list_type like '%key_focus' then 0 else 1 end, fi.priority nulls last, fi.symbol
            limit :limit
            """
        )
        try:
            with self.engine.begin() as conn:
                rows = conn.execute(query, {"limit": max(limit * 3, limit)}).scalars().all()
            for symbol in rows:
                symbol = str(symbol or "").strip()
                if self._looks_like_symbol(symbol) and symbol not in seen:
                    seen.add(symbol)
                    symbols.append(symbol)
                if len(symbols) >= limit:
                    break
        except Exception:
            pass
        return symbols[:limit]

    def _build_market_index_chart(self, *, business_date: str, charts_dir: Path) -> ChartAsset:
        rows = self._fetch_daily_rows(
            table="ifa2.index_daily_bar_history",
            symbols=[item[0] for item in DEFAULT_INDEX_SYMBOLS],
            business_date=business_date,
            limit_per_symbol=DEFAULT_INDEX_WINDOW_DAYS,
        )
        series = []
        for symbol, label in DEFAULT_INDEX_SYMBOLS:
            points = rows.get(symbol, [])
            if points:
                series.append({"symbol": symbol, "label": label, "points": points})
        filename = "market_index_window.svg"
        asset_path = charts_dir / filename
        if not series:
            return self._write_missing_svg(
                asset_path=asset_path,
                chart_key="market_index_window",
                chart_class="market_index_line",
                title="市场/指数窗口图",
                source_window={
                    "source_table": "ifa2.index_daily_bar_history",
                    "frequency": "daily",
                    "lookback_bars": DEFAULT_INDEX_WINDOW_DAYS,
                    "end_business_date": business_date,
                    "symbols": [item[0] for item in DEFAULT_INDEX_SYMBOLS],
                },
                note="index_daily_bar_history missing for requested window",
            )
        svg = _line_chart_svg(title="市场/指数窗口图", subtitle=f"source=index_daily_bar_history | window={DEFAULT_INDEX_WINDOW_DAYS}d", series=series)
        asset_path.write_text(svg, encoding="utf-8")
        return ChartAsset(
            chart_key="market_index_window",
            chart_class="market_index_line",
            title="市场/指数窗口图",
            filename=filename,
            relative_path=f"charts/{filename}",
            source_window={
                "source_table": "ifa2.index_daily_bar_history",
                "frequency": "daily",
                "lookback_bars": DEFAULT_INDEX_WINDOW_DAYS,
                "end_business_date": business_date,
                "symbols": [item[0] for item in DEFAULT_INDEX_SYMBOLS],
            },
            status="ready",
            series_count=len(series),
            symbol_count=len(series),
        )

    def _build_focus_line_chart(self, *, business_date: str, charts_dir: Path, focus_symbols: Sequence[str]) -> ChartAsset:
        filename = "key_focus_window.svg"
        asset_path = charts_dir / filename
        rows = self._fetch_daily_rows(
            table="ifa2.equity_daily_bar_history",
            symbols=focus_symbols,
            business_date=business_date,
            limit_per_symbol=DEFAULT_FOCUS_WINDOW_DAYS,
        )
        series = []
        for symbol in focus_symbols:
            points = rows.get(symbol, [])
            if points:
                series.append({"symbol": symbol, "label": symbol, "points": points})
        if not series:
            return self._write_missing_svg(
                asset_path=asset_path,
                chart_key="key_focus_window",
                chart_class="key_focus_line",
                title="Key Focus 窗口图",
                source_window={
                    "source_table": "ifa2.equity_daily_bar_history",
                    "frequency": "daily",
                    "lookback_bars": DEFAULT_FOCUS_WINDOW_DAYS,
                    "end_business_date": business_date,
                    "symbols": list(focus_symbols),
                },
                note="focus/equity daily bars missing for requested window",
            )
        svg = _line_chart_svg(title="Key Focus 窗口图", subtitle=f"source=equity_daily_bar_history | window={DEFAULT_FOCUS_WINDOW_DAYS}d", series=series)
        asset_path.write_text(svg, encoding="utf-8")
        return ChartAsset(
            chart_key="key_focus_window",
            chart_class="key_focus_line",
            title="Key Focus 窗口图",
            filename=filename,
            relative_path=f"charts/{filename}",
            source_window={
                "source_table": "ifa2.equity_daily_bar_history",
                "frequency": "daily",
                "lookback_bars": DEFAULT_FOCUS_WINDOW_DAYS,
                "end_business_date": business_date,
                "symbols": list(focus_symbols),
            },
            status="ready",
            series_count=len(series),
            symbol_count=len(series),
        )

    def _build_focus_return_bar_chart(self, *, business_date: str, charts_dir: Path, focus_symbols: Sequence[str]) -> ChartAsset:
        filename = "key_focus_return_bar.svg"
        asset_path = charts_dir / filename
        rows = self._fetch_daily_rows(
            table="ifa2.equity_daily_bar_history",
            symbols=focus_symbols,
            business_date=business_date,
            limit_per_symbol=2,
        )
        bars = []
        for symbol in focus_symbols:
            points = rows.get(symbol, [])
            if len(points) >= 2:
                start = float(points[0]["close"] or 0)
                end = float(points[-1]["close"] or 0)
                if start:
                    bars.append({"label": symbol, "value": round((end - start) / start * 100.0, 2)})
        if not bars:
            return self._write_missing_svg(
                asset_path=asset_path,
                chart_key="key_focus_return_bar",
                chart_class="key_focus_return_bar",
                title="Key Focus 日度涨跌幅",
                source_window={
                    "source_table": "ifa2.equity_daily_bar_history",
                    "frequency": "daily",
                    "lookback_bars": 2,
                    "end_business_date": business_date,
                    "symbols": list(focus_symbols),
                },
                note="insufficient focus bars to calculate day-over-day return",
            )
        svg = _bar_chart_svg(title="Key Focus 日度涨跌幅", subtitle="source=equity_daily_bar_history | 2-bar delta", bars=bars)
        asset_path.write_text(svg, encoding="utf-8")
        return ChartAsset(
            chart_key="key_focus_return_bar",
            chart_class="key_focus_return_bar",
            title="Key Focus 日度涨跌幅",
            filename=filename,
            relative_path=f"charts/{filename}",
            source_window={
                "source_table": "ifa2.equity_daily_bar_history",
                "frequency": "daily",
                "lookback_bars": 2,
                "end_business_date": business_date,
                "symbols": list(focus_symbols),
            },
            status="ready",
            series_count=len(bars),
            symbol_count=len(bars),
        )

    def _fetch_daily_rows(self, *, table: str, symbols: Sequence[str], business_date: str, limit_per_symbol: int) -> dict[str, list[dict[str, Any]]]:
        symbols = [str(symbol).strip() for symbol in symbols if str(symbol).strip()]
        if not symbols:
            return {}
        sql = text(
            f"""
            with ranked as (
                select ts_code, trade_date, close,
                       row_number() over (partition by ts_code order by trade_date desc) as rn
                from {table}
                where ts_code = any(:symbols)
                  and trade_date <= cast(:business_date as date)
                  and close is not null
            )
            select ts_code, trade_date, close
            from ranked
            where rn <= :limit_per_symbol
            order by ts_code, trade_date
            """
        )
        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, {"symbols": list(symbols), "business_date": business_date, "limit_per_symbol": int(limit_per_symbol)}).mappings().all()
        except Exception:
            return {}
        grouped: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
        for row in result:
            grouped[str(row["ts_code"])].append({"trade_date": str(row["trade_date"]), "close": float(row["close"])})
        return {k: v for k, v in grouped.items() if v}

    def _write_missing_svg(
        self,
        *,
        asset_path: Path,
        chart_key: str,
        chart_class: str,
        title: str,
        source_window: dict[str, Any],
        note: str,
    ) -> ChartAsset:
        asset_path.write_text(_missing_chart_svg(title=title, note=note), encoding="utf-8")
        return ChartAsset(
            chart_key=chart_key,
            chart_class=chart_class,
            title=title,
            filename=asset_path.name,
            relative_path=f"charts/{asset_path.name}",
            source_window=source_window,
            status="missing",
            note=note,
        )

    def _asset_embed_block(self, asset: ChartAsset) -> dict[str, Any]:
        return {
            "chart_key": asset.chart_key,
            "title": asset.title,
            "status": asset.status,
            "relative_path": asset.relative_path,
            "source_window": asset.source_window,
            "caption": asset.note or f"window={asset.source_window.get('lookback_bars')} {asset.source_window.get('frequency')} bars",
        }

    @staticmethod
    def _looks_like_symbol(value: str) -> bool:
        value = str(value or "").strip().upper()
        return value.endswith((".SZ", ".SH")) and len(value) >= 9


COLORS = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#ea580c"]


def _line_chart_svg(*, title: str, subtitle: str, series: Sequence[dict[str, Any]], width: int = 920, height: int = 340) -> str:
    left, right, top, bottom = 56, 20, 46, 34
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [float(point["close"]) for item in series for point in item.get("points") or []]
    min_v = min(values)
    max_v = max(values)
    if math.isclose(min_v, max_v):
        max_v = min_v + 1.0
    y_of = lambda v: top + (max_v - v) / (max_v - min_v) * plot_h
    max_points = max(len(item.get("points") or []) for item in series)
    x_of = lambda idx, count: left + (idx / max(count - 1, 1)) * plot_w
    paths = []
    legends = []
    for idx, item in enumerate(series):
        color = COLORS[idx % len(COLORS)]
        points = item.get("points") or []
        coords = [f"{x_of(i, len(points)):.1f},{y_of(float(point['close'])):.1f}" for i, point in enumerate(points)]
        paths.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{" ".join(coords)}" />')
        legends.append(f'<text x="{left + idx*150}" y="{height-10}" font-size="12" fill="{color}">{escape(str(item.get("label") or item.get("symbol") or "series"))}</text>')
    grid = []
    for i in range(5):
        y = top + plot_h * i / 4
        value = max_v - (max_v - min_v) * i / 4
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" stroke="#e2e8f0" />')
        grid.append(f'<text x="8" y="{y+4:.1f}" font-size="11" fill="#64748b">{value:.2f}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff" rx="18" />
  <text x="20" y="24" font-size="18" font-weight="700" fill="#0f172a">{escape(title)}</text>
  <text x="20" y="40" font-size="12" fill="#64748b">{escape(subtitle)}</text>
  <rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#f8fafc" stroke="#cbd5e1" rx="12" />
  {''.join(grid)}
  {''.join(paths)}
  {''.join(legends)}
</svg>'''


def _bar_chart_svg(*, title: str, subtitle: str, bars: Sequence[dict[str, Any]], width: int = 920, height: int = 340) -> str:
    left, right, top, bottom = 56, 20, 46, 50
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [float(item["value"]) for item in bars]
    max_abs = max(max(abs(v) for v in values), 1.0)
    zero_y = top + plot_h / 2
    parts = []
    bar_w = max(plot_w / max(len(bars) * 1.8, 1), 40)
    for idx, item in enumerate(bars):
        value = float(item["value"])
        height_px = abs(value) / max_abs * (plot_h / 2 - 10)
        x = left + idx * (bar_w + 24) + 20
        y = zero_y - height_px if value >= 0 else zero_y
        color = "#16a34a" if value >= 0 else "#dc2626"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{height_px:.1f}" fill="{color}" rx="8" />')
        parts.append(f'<text x="{x + bar_w/2:.1f}" y="{zero_y + 18:.1f}" text-anchor="middle" font-size="11" fill="#334155">{escape(str(item["label"]))}</text>')
        parts.append(f'<text x="{x + bar_w/2:.1f}" y="{(y - 6) if value >= 0 else (y + height_px + 14):.1f}" text-anchor="middle" font-size="11" fill="#475569">{value:+.2f}%</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff" rx="18" />
  <text x="20" y="24" font-size="18" font-weight="700" fill="#0f172a">{escape(title)}</text>
  <text x="20" y="40" font-size="12" fill="#64748b">{escape(subtitle)}</text>
  <rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#f8fafc" stroke="#cbd5e1" rx="12" />
  <line x1="{left}" y1="{zero_y:.1f}" x2="{left+plot_w}" y2="{zero_y:.1f}" stroke="#94a3b8" stroke-dasharray="4 4" />
  {''.join(parts)}
</svg>'''


def _missing_chart_svg(*, title: str, note: str, width: int = 920, height: int = 220) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#fff7ed" stroke="#fdba74" rx="18" />
  <text x="20" y="36" font-size="18" font-weight="700" fill="#9a3412">{escape(title)}</text>
  <text x="20" y="70" font-size="14" fill="#9a3412">chart unavailable</text>
  <text x="20" y="96" font-size="13" fill="#7c2d12">{escape(note)}</text>
</svg>'''
