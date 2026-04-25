from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile
import json
import re
import shutil

from .chart_pack import FSJChartPackBuilder
from .report_assembly import MainReportAssemblyService, SupportReportAssemblyService
from .report_dispatch import MainReportDeliveryDispatchHelper
from .report_evaluation import MainReportEvaluationHarness
from .report_quality import MainReportQAEvaluator, SupportReportQAEvaluator
from .store import FSJStore
from .test_live_isolation import enforce_artifact_publish_root_contract, require_explicit_non_live_artifact_root

RENDERER_NAME = "ifa_data_platform.fsj.report_rendering.MainReportHTMLRenderer"
RENDERER_VERSION = "v3"
VALID_OUTPUT_PROFILES = {"internal", "review", "customer"}
CUSTOMER_PRESENTATION_SCHEMA_VERSION = "v1"
KEY_FOCUS_DISPLAY_LIMIT = 10
FOCUS_DISPLAY_LIMIT = 20
KEY_FOCUS_DISPLAY_LIMIT_CAP = 20
FOCUS_DISPLAY_LIMIT_CAP = 40
KEY_FOCUS_MODULE_LABEL = "核心关注"
FOCUS_MODULE_LABEL = "关注"
KEY_FOCUS_TIER_LABEL = "核心关注列表"
FOCUS_TIER_LABEL = "关注列表"

SLOT_LABELS: dict[str, str] = {
    "early": "早报 / 盘前",
    "mid": "中报 / 盘中",
    "late": "晚报 / 收盘后",
}
SUPPORT_DOMAIN_LABELS: dict[str, str] = {
    "macro": "宏观",
    "commodities": "商品",
    "ai_tech": "AI / 科技",
}
SUPPORT_SLOT_LABELS: dict[str, str] = {
    "early": "盘前",
    "late": "收盘后",
}


@dataclass(frozen=True)
class RenderedFSJArtifact:
    artifact_type: str
    artifact_version: str
    render_format: str
    content_type: str
    title: str
    content: str
    metadata: dict[str, Any]
    report_links: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": self.artifact_type,
            "artifact_version": self.artifact_version,
            "render_format": self.render_format,
            "content_type": self.content_type,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "report_links": self.report_links,
        }


class MainReportHTMLRenderer:
    def render(
        self,
        assembled: dict[str, Any],
        *,
        report_run_id: str | None = None,
        artifact_uri: str | None = None,
        generated_at: datetime | None = None,
        output_profile: str = "internal",
        chart_manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        profile = self._normalize_output_profile(output_profile)
        title = self._title_for_profile(assembled, output_profile=profile)
        sections = list(assembled.get("sections") or [])
        html = self._render_html(
            title=title,
            assembled=assembled,
            sections=sections,
            generated_at=generated_at,
            output_profile=profile,
            chart_manifest=chart_manifest,
        )
        report_links = self._build_report_links(
            sections,
            report_run_id=report_run_id,
            artifact_uri=artifact_uri,
        )
        focus_module = self._build_focus_module(assembled=assembled, sections=sections)
        metadata = {
            "market": assembled.get("market"),
            "business_date": assembled.get("business_date"),
            "agent_domain": assembled.get("agent_domain"),
            "source_artifact_type": assembled.get("artifact_type"),
            "source_artifact_version": assembled.get("artifact_version"),
            "renderer": RENDERER_NAME,
            "renderer_version": RENDERER_VERSION,
            "generated_at": generated_at.isoformat(),
            "output_profile": profile,
            "presentation_schema_version": CUSTOMER_PRESENTATION_SCHEMA_VERSION if profile == "customer" else None,
            "section_count": len(sections),
            "bundle_ids": [section.get("bundle", {}).get("bundle_id") for section in sections if section.get("bundle")],
            "producer_versions": [section.get("bundle", {}).get("producer_version") for section in sections if section.get("bundle")],
            "artifact_uri": artifact_uri,
            "support_summary_domains": list(assembled.get("support_summary_domains") or []),
            "support_summary_bundle_ids": [item.get("bundle_id") for section in sections for item in (section.get("support_summaries") or []) if item.get("bundle_id")],
            "focus_module": focus_module,
            "chart_pack": chart_manifest,
            "existing_report_links": [
                link
                for section in sections
                for link in ((section.get("lineage") or {}).get("report_links") or [])
            ] + [
                link
                for section in sections
                for item in (section.get("support_summaries") or [])
                for link in (((item.get("lineage") or {}).get("report_links") or []))
            ],
        }
        if profile == "customer":
            metadata["customer_presentation"] = self._build_customer_presentation(assembled=assembled, sections=sections, focus_module=focus_module, chart_manifest=chart_manifest)
        return RenderedFSJArtifact(
            artifact_type="fsj_main_report_html",
            artifact_version="v2",
            render_format="html",
            content_type="text/html",
            title=title,
            content=html,
            metadata=metadata,
            report_links=report_links,
        ).as_dict()

    def _render_html(
        self,
        *,
        title: str,
        assembled: dict[str, Any],
        sections: Sequence[dict[str, Any]],
        generated_at: datetime,
        output_profile: str,
        chart_manifest: dict[str, Any] | None,
    ) -> str:
        if output_profile == "customer":
            return self._render_customer_html(title=title, assembled=assembled, sections=sections, generated_at=generated_at, chart_manifest=chart_manifest)
        executive = self._build_executive_summary(sections)
        institutional_panel = self._build_institutional_panel(assembled, sections)
        focus_module = self._build_focus_module(assembled=assembled, sections=sections)
        focus_html = self._render_focus_module_html(focus_module)
        chart_html = self._render_chart_pack_html(chart_manifest)
        section_html = "\n".join(self._render_section(section) for section in sections)
        return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f4f6fb; color: #111827; }}
    .page {{ max-width: 1040px; margin: 0 auto; padding: 28px 24px 48px; }}
    .hero {{ background: linear-gradient(135deg, #0f172a, #1d4ed8); color: white; border-radius: 20px; padding: 28px 32px; box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18); }}
    .hero h1 {{ margin: 0 0 10px; font-size: 34px; }}
    .hero .meta {{ opacity: 0.88; font-size: 14px; line-height: 1.6; }}
    .card {{ background: white; border-radius: 18px; padding: 24px 26px; margin-top: 20px; box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08); }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    h3 {{ margin: 0 0 12px; font-size: 18px; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
    .summary-box {{ border: 1px solid #dbe3f1; border-radius: 14px; padding: 14px 16px; background: #f8fbff; }}
    .summary-box .slot {{ font-size: 12px; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; }}
    .summary-box .headline {{ margin-top: 8px; font-size: 15px; font-weight: 600; line-height: 1.5; }}
    .panel-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 16px; }}
    .panel-box {{ border-radius: 16px; padding: 16px 18px; background: linear-gradient(180deg, #ffffff, #f8fbff); border: 1px solid #dbe3f1; }}
    .panel-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; }}
    .panel-value {{ margin-top: 8px; font-size: 22px; font-weight: 700; color: #0f172a; }}
    .panel-detail {{ margin-top: 6px; font-size: 13px; color: #475569; line-height: 1.55; }}
    .support-inline {{ margin-top: 10px; font-size: 12px; color: #475569; line-height: 1.6; }}
    .support-block {{ margin-top: 16px; padding: 14px 16px; border: 1px dashed #cbd5e1; border-radius: 14px; background: #f8fafc; }}
    .support-item {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid #e2e8f0; }}
    .support-item:first-child {{ margin-top: 0; padding-top: 0; border-top: none; }}
    .support-domain {{ font-size: 12px; color: #334155; text-transform: uppercase; letter-spacing: 0.05em; }}
    .support-summary {{ margin-top: 6px; font-size: 14px; line-height: 1.6; }}
    .section {{ border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 20px; }}
    .section:first-child {{ border-top: none; padding-top: 0; margin-top: 0; }}
    .section-meta {{ color: #64748b; font-size: 13px; margin-bottom: 14px; }}
    .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #e0e7ff; color: #3730a3; font-size: 12px; margin-right: 8px; }}
    .missing {{ background: #fff7ed; color: #9a3412; }}
    ul {{ margin: 8px 0 0 18px; padding: 0; }}
    li {{ margin: 6px 0; line-height: 1.55; }}
    .bucket {{ margin-top: 16px; }}
    .footnote {{ font-size: 12px; color: #64748b; margin-top: 18px; line-height: 1.6; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  </style>
</head>
<body>
  <div class=\"page\">
    <section class=\"hero\">
      <h1>{escape(title)}</h1>
      <div class=\"meta\">
        市场：{escape(str(assembled.get('market') or '-'))} · 业务日期：{escape(str(assembled.get('business_date') or '-'))} · Agent：{escape(str(assembled.get('agent_domain') or '-'))}<br/>
        渲染器：<span class=\"mono\">{escape(RENDERER_VERSION)}</span> · 生成时间：{escape(generated_at.isoformat())}
      </div>
    </section>

    <section class=\"card\">
      <h2>执行摘要</h2>
      <div class=\"summary-grid\">{executive}</div>
      <div class=\"panel-grid\">{institutional_panel}</div>
      <div class=\"footnote\">
        本报告由 FSJ section assembly 直接渲染，保留 bundle / producer_version / replay_id / report_link 钩子；support 内容仅以 concise summary merge 进入主报告，不内联 support report 正文。
      </div>
    </section>

    <section class=\"card\">
      <h2>核心关注 / 关注 模块</h2>
      {focus_html}
    </section>

    {chart_html}

    <section class=\"card\">
      <h2>主体内容</h2>
      {section_html}
    </section>
  </div>
</body>
</html>
"""

    def _normalize_output_profile(self, output_profile: str) -> str:
        profile = str(output_profile or "internal").strip().lower()
        if profile not in VALID_OUTPUT_PROFILES:
            raise ValueError(f"unsupported output_profile={output_profile}")
        return profile

    def _title_for_profile(self, assembled: dict[str, Any], *, output_profile: str) -> str:
        business_date = assembled.get("business_date") or "-"
        if output_profile == "customer":
            return f"A股市场简报｜{business_date}"
        if output_profile == "review":
            return f"A股主报告审阅包｜{business_date}"
        return f"A股主报告｜{business_date}"

    def _resolve_customer_slot_views(
        self,
        *,
        assembled: dict[str, Any],
        sections: Sequence[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
        requested_slot = str(assembled.get("requested_customer_slot") or "").strip().lower() or None
        if requested_slot not in {"early", "mid", "late"}:
            return list(sections), list(sections), None

        section_by_slot = {str(section.get("slot") or "").strip().lower(): section for section in sections}
        context_order = {
            "early": ["early"],
            "mid": ["early", "mid"],
            "late": ["early", "mid", "late"],
        }
        full_order = {
            "early": ["early"],
            "mid": ["mid"],
            "late": ["late"],
        }
        context_sections = [section_by_slot[slot] for slot in context_order[requested_slot] if slot in section_by_slot]
        full_sections = [section_by_slot[slot] for slot in full_order[requested_slot] if slot in section_by_slot]
        return context_sections or list(sections), full_sections or list(sections), requested_slot

    def _build_customer_presentation(self, *, assembled: dict[str, Any], sections: Sequence[dict[str, Any]], focus_module: dict[str, Any] | None = None, chart_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
        context_sections, full_sections, requested_slot = self._resolve_customer_slot_views(assembled=assembled, sections=sections)
        customer_sections: list[dict[str, Any]] = []
        full_section_slots = {str(section.get("slot") or "") for section in full_sections}
        for section in context_sections:
            slot = str(section.get("slot") or "")
            slot_label = SLOT_LABELS.get(slot, slot or "未命名时段")
            support_items = [
                {
                    "domain": SUPPORT_DOMAIN_LABELS.get(str(item.get("agent_domain") or ""), str(item.get("agent_domain") or "support")),
                    "summary": self._refine_customer_summary(
                        self._sanitize_customer_text(str(item.get("summary") or "暂无摘要")),
                        slot=slot,
                        is_support=True,
                    ),
                }
                for item in (section.get("support_summaries") or [])
            ]
            section_summary = self._refine_customer_summary(
                self._sanitize_customer_text(str(section.get("summary") or "暂无摘要")),
                slot=slot,
            )
            highlights = self._customer_item_statements(section.get("judgments") or [], limit=3, slot=slot)
            signals = self._customer_item_statements(section.get("signals") or [], limit=3, slot=slot)
            facts = self._customer_item_statements(section.get("facts") or [], limit=3, slot=slot)
            customer_sections.append(
                {
                    "slot": slot,
                    "slot_label": slot_label,
                    "title": self._customer_section_title(slot, str(section.get("title") or slot_label)),
                    "summary": section_summary,
                    "status": str(section.get("status") or "unknown"),
                    "highlights": highlights,
                    "signals": signals,
                    "facts": facts,
                    "support_themes": support_items,
                    "advisory_note": self._customer_slot_advisory_note(
                        slot=slot,
                        summary=section_summary,
                        highlights=highlights,
                        signals=signals,
                        support_items=support_items,
                    ),
                }
            )
        display_sections = [section for section in customer_sections if str(section.get("slot") or "") in full_section_slots]
        focus_payload = focus_module or self._build_focus_module(assembled=assembled, sections=context_sections)
        top_judgment = self._customer_top_judgment(customer_sections)
        risk_block = self._customer_risk_block(customer_sections)
        next_steps = self._customer_next_steps(customer_sections, focus_payload)
        disclaimer = (
            "本报告仅供参考，不构成任何收益承诺或个股、行业、基金的确定性买卖建议。"
            "市场有风险，投资需结合自身目标、期限与风险承受能力独立判断。"
        )
        return {
            "schema_type": "fsj_customer_main_presentation",
            "schema_version": CUSTOMER_PRESENTATION_SCHEMA_VERSION,
            "brand": "iFA",
            "report_title": "iFA A股市场日报",
            "requested_slot": requested_slot,
            "created_by": "Created by Lindenwood Management LLC",
            "business_date": assembled.get("business_date"),
            "market": assembled.get("market") or "a_share",
            "top_judgment": top_judgment,
            "risk_block": risk_block,
            "next_steps": next_steps,
            "disclaimer": disclaimer,
            "focus_module": focus_payload,
            "chart_pack": chart_manifest,
            "summary_cards": [
                {
                    "slot": item["slot"],
                    "slot_label": item["slot_label"],
                    "headline": item["summary"],
                    "support_themes": item["support_themes"],
                    "advisory_note": item["advisory_note"],
                }
                for item in customer_sections
            ],
            "sections": display_sections,
        }

    def _build_focus_module(self, *, assembled: dict[str, Any], sections: Sequence[dict[str, Any]]) -> dict[str, Any]:
        focus_symbols: list[str] = []
        key_focus_symbols: list[str] = []
        focus_only_symbols: list[str] = []
        focus_list_types: list[str] = []
        focus_name_map: dict[str, str] = {}
        focus_item_list_type_map: dict[str, list[str]] = {}
        focus_item_metadata_map: dict[str, dict[str, Any]] = {}
        focus_item_order: list[str] = []
        reasons: list[str] = []
        source_sections: list[str] = []
        judgment_refs: list[str] = []
        symbol_context_map: dict[str, dict[str, Any]] = {}
        seen_focus: set[str] = set()
        seen_key_focus: set[str] = set()
        seen_focus_only: set[str] = set()
        seen_item_order: set[str] = set()
        seen_list_types: set[str] = set()
        seen_reasons: set[str] = set()
        for section in sections:
            slot = str(section.get("slot") or "")
            if slot:
                source_sections.append(slot)
            lineage = dict(section.get("lineage") or {})
            payload = dict((lineage.get("bundle") or {}).get("payload_json") or {})
            scope = dict(payload.get("focus_scope") or {})
            focus_name_map.update(self._extract_focus_name_map(scope))
            item_type_map = self._extract_focus_item_type_map(scope)
            for symbol, list_types in item_type_map.items():
                merged = focus_item_list_type_map.setdefault(symbol, [])
                for list_type in list_types:
                    if list_type not in merged:
                        merged.append(list_type)
            self._merge_focus_item_metadata_map(focus_item_metadata_map, scope)
            for focus_item in (scope.get("items") or scope.get("focus_items") or []):
                if not isinstance(focus_item, dict):
                    continue
                symbol = str(focus_item.get("symbol") or focus_item.get("code") or "").strip()
                if not symbol:
                    continue
                if symbol not in seen_item_order:
                    seen_item_order.add(symbol)
                    focus_item_order.append(symbol)
            section_list_types = {str(item or "").strip() for item in (scope.get("focus_list_types") or []) if str(item or "").strip()}
            for symbol in scope.get("focus_symbols") or []:
                symbol = str(symbol or "").strip()
                if not symbol:
                    continue
                if symbol not in seen_focus:
                    seen_focus.add(symbol)
                    focus_symbols.append(symbol)
                symbol_list_types = focus_item_list_type_map.get(symbol) or list(section_list_types)
                if any("key_focus" in list_type for list_type in symbol_list_types):
                    if symbol not in seen_key_focus:
                        seen_key_focus.add(symbol)
                        key_focus_symbols.append(symbol)
                elif any(list_type.endswith("focus") for list_type in symbol_list_types):
                    if symbol not in seen_focus_only:
                        seen_focus_only.add(symbol)
                        focus_only_symbols.append(symbol)
            for list_type in scope.get("focus_list_types") or []:
                list_type = str(list_type or "").strip()
                if list_type and list_type not in seen_list_types:
                    seen_list_types.add(list_type)
                    focus_list_types.append(list_type)
            for candidate in (
                scope.get("why_included"),
                next((fact.get("statement") for fact in (section.get("facts") or []) if "focus" in str(fact.get("statement") or "").lower()), None),
            ):
                reason = str(candidate or "").strip()
                if reason and reason not in seen_reasons:
                    seen_reasons.add(reason)
                    reasons.append(reason)
            for judgment in (section.get("judgments") or []):
                judgment_key = str(judgment.get("object_key") or "").strip()
                if judgment_key:
                    judgment_refs.append(judgment_key)
            self._merge_focus_symbol_context(symbol_context_map, section)
        ordered_focus_symbols = focus_item_order + [symbol for symbol in focus_symbols if symbol not in set(focus_item_order)]
        prioritized_item_symbols = [
            symbol for symbol in focus_item_order
            if any("key_focus" in list_type for list_type in (focus_item_list_type_map.get(symbol) or []))
        ]
        key_focus_limit = self._focus_display_limit(KEY_FOCUS_DISPLAY_LIMIT, cap=KEY_FOCUS_DISPLAY_LIMIT_CAP)
        focus_limit = self._focus_display_limit(FOCUS_DISPLAY_LIMIT, cap=FOCUS_DISPLAY_LIMIT_CAP)
        if prioritized_item_symbols:
            key_focus_symbols = prioritized_item_symbols[: min(key_focus_limit, len(prioritized_item_symbols))]
        elif not key_focus_symbols:
            prioritized_symbols = [
                symbol for symbol in ordered_focus_symbols
                if any("key_focus" in list_type for list_type in (focus_item_list_type_map.get(symbol) or []))
            ]
            key_focus_symbols = (prioritized_symbols or ordered_focus_symbols)[: min(key_focus_limit, len(ordered_focus_symbols))]
        focus_only_symbols = [symbol for symbol in ordered_focus_symbols if symbol not in set(key_focus_symbols)]
        key_focus_items = [
            self._build_focus_watch_item(
                symbol=symbol,
                tier="key_focus",
                display_name=focus_name_map.get(symbol),
                primary_reason=reasons[0] if reasons else "",
                list_types=focus_item_list_type_map.get(symbol) or [],
                symbol_context=self._compose_focus_symbol_context(
                    symbol=symbol,
                    symbol_context=symbol_context_map.get(symbol) or {},
                    item_metadata=focus_item_metadata_map.get(symbol) or {},
                    list_types=focus_item_list_type_map.get(symbol) or [],
                ),
                ordinal=index,
            )
            for index, symbol in enumerate(key_focus_symbols[:key_focus_limit], start=1)
        ]
        focus_watch_items = [
            self._build_focus_watch_item(
                symbol=symbol,
                tier="focus_watch",
                display_name=focus_name_map.get(symbol),
                primary_reason=reasons[0] if reasons else "",
                list_types=focus_item_list_type_map.get(symbol) or [],
                symbol_context=self._compose_focus_symbol_context(
                    symbol=symbol,
                    symbol_context=symbol_context_map.get(symbol) or {},
                    item_metadata=focus_item_metadata_map.get(symbol) or {},
                    list_types=focus_item_list_type_map.get(symbol) or [],
                ),
                ordinal=index,
            )
            for index, symbol in enumerate(focus_only_symbols[:focus_limit], start=1)
        ]
        if not focus_watch_items:
            focus_watch_items = [self._professional_empty_focus_item()]
        display_focus_symbols = [item["symbol"] for item in (key_focus_items + focus_watch_items) if item.get("symbol")][: key_focus_limit + focus_limit]
        return {
            "module_type": "fsj_focus_module",
            "business_date": assembled.get("business_date"),
            "list_types": focus_list_types,
            "focus_symbols": display_focus_symbols,
            "focus_symbol_count": len(focus_symbols),
            "key_focus_symbols": key_focus_symbols[:key_focus_limit],
            "key_focus_symbol_count": len(key_focus_symbols),
            "focus_watch_symbols": focus_only_symbols[:focus_limit],
            "focus_watch_symbol_count": len(focus_only_symbols),
            "focus_name_map": focus_name_map,
            "key_focus_items": key_focus_items,
            "focus_watch_items": focus_watch_items,
            "watchlist_tiers": [
                {"label": f"{KEY_FOCUS_MODULE_LABEL} / {KEY_FOCUS_TIER_LABEL}", "description": "核心观察名单，用于确认主线强弱、节奏与资金承接是否继续成立。", "symbols": key_focus_symbols[:key_focus_limit], "items": key_focus_items},
                {"label": f"{FOCUS_MODULE_LABEL} / {FOCUS_TIER_LABEL}", "description": "补充观察名单，用于跟踪扩散路径、板块分歧与主线外溢质量。", "symbols": focus_only_symbols[:focus_limit], "items": focus_watch_items},
            ],
            "why_included": reasons[0] if reasons else "核心关注 / 关注 作为正式观察池进入报告，用于界定优先跟踪对象与噪音过滤边界。",
            "reasons": self._focus_reasons(reasons=reasons, key_focus_symbols=key_focus_symbols, focus_only_symbols=focus_only_symbols, total_focus_count=len(focus_symbols)),
            "source_sections": source_sections,
            "chart_refs": [
                {"chart_key": "key_focus_window", "title": "核心关注 窗口图"},
                {"chart_key": "key_focus_return_bar", "title": "核心关注 日度涨跌幅"},
            ],
            "judgment_refs": judgment_refs[:8],
            "review_ready": bool(focus_symbols or focus_list_types),
        }

    def _extract_focus_name_map(self, scope: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        raw_maps = [scope.get("name_map"), scope.get("symbol_name_map"), scope.get("focus_name_map")]
        for raw in raw_maps:
            if not isinstance(raw, dict):
                continue
            for symbol, name in raw.items():
                symbol_text = str(symbol or "").strip()
                name_text = str(name or "").strip()
                if symbol_text and name_text:
                    result[symbol_text] = name_text
        for item in (scope.get("items") or scope.get("focus_items") or []):
            if not isinstance(item, dict):
                continue
            symbol_text = str(item.get("symbol") or item.get("code") or "").strip()
            name_text = str(item.get("name") or item.get("display_name") or item.get("company_name") or item.get("label") or "").strip()
            if symbol_text and name_text:
                result[symbol_text] = name_text
        return result

    def _extract_focus_item_type_map(self, scope: dict[str, Any]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for item in (scope.get("items") or scope.get("focus_items") or []):
            if not isinstance(item, dict):
                continue
            symbol_text = str(item.get("symbol") or item.get("code") or "").strip()
            if not symbol_text:
                continue
            list_types: list[str] = []
            for list_type in (item.get("list_types") or item.get("focus_list_types") or []):
                clean = str(list_type or "").strip()
                if clean and clean not in list_types:
                    list_types.append(clean)
            if list_types:
                result[symbol_text] = list_types
        return result

    def _merge_focus_item_metadata_map(self, focus_item_metadata_map: dict[str, dict[str, Any]], scope: dict[str, Any]) -> None:
        for item in (scope.get("items") or scope.get("focus_items") or []):
            if not isinstance(item, dict):
                continue
            symbol_text = str(item.get("symbol") or item.get("code") or "").strip()
            if not symbol_text:
                continue
            target = focus_item_metadata_map.setdefault(symbol_text, {})
            for field in ("name", "company_name", "list_type", "priority", "sector_or_theme", "key_focus"):
                if target.get(field) is None and item.get(field) is not None:
                    target[field] = item.get(field)
            for nested in ("market_evidence", "text_event_evidence"):
                nested_target = dict(target.get(nested) or {})
                nested_source = dict(item.get(nested) or {})
                for key, value in nested_source.items():
                    if nested_target.get(key) is None and value is not None:
                        nested_target[key] = value
                if nested_target:
                    target[nested] = nested_target

    def _compose_focus_symbol_context(self, *, symbol: str, symbol_context: dict[str, Any], item_metadata: dict[str, Any], list_types: Sequence[str]) -> dict[str, Any]:
        ctx = dict(symbol_context or {})
        item_metadata = dict(item_metadata or {})
        market_evidence = dict(item_metadata.get("market_evidence") or {})
        text_event_evidence = dict(item_metadata.get("text_event_evidence") or {})
        ctx["symbol"] = symbol
        ctx["list_type"] = item_metadata.get("list_type") or (list_types[0] if list_types else None)
        ctx["priority"] = item_metadata.get("priority")
        ctx["key_focus"] = bool(item_metadata.get("key_focus") or any("key_focus" in str(item) for item in list_types))
        ctx["company_name"] = item_metadata.get("company_name") or item_metadata.get("name")
        ctx["sector_or_theme"] = item_metadata.get("sector_or_theme")
        ctx["market_evidence"] = market_evidence
        ctx["text_event_evidence"] = text_event_evidence
        market_signal_count = 0
        if market_evidence.get("has_daily_bar"):
            market_signal_count += 1
        if market_evidence.get("recent_return_pct") is not None:
            market_signal_count += 1
        if market_evidence.get("latest_volume") is not None or market_evidence.get("latest_amount") is not None:
            market_signal_count += 1
        text_signal_count = sum(
            int(text_event_evidence.get(field) or 0)
            for field in ("announcement_count", "research_count", "investor_qa_count", "dragon_tiger_count", "limit_up_count", "event_count")
        )
        ctx["has_market_evidence"] = market_signal_count > 0
        ctx["has_text_evidence"] = text_signal_count > 0
        ctx["evidence_depth"] = self._classify_focus_evidence_depth(
            has_market_evidence=ctx["has_market_evidence"],
            has_text_evidence=ctx["has_text_evidence"],
            has_sector_theme=bool(ctx.get("sector_or_theme")),
            has_named_display=bool(ctx.get("company_name")),
        )
        ctx["evidence_score"] = max(
            int(ctx.get("evidence_score") or 0),
            min(4, market_signal_count + (1 if text_signal_count > 0 else 0) + (1 if ctx.get("sector_or_theme") else 0)),
        )
        return ctx

    def _classify_focus_evidence_depth(self, *, has_market_evidence: bool, has_text_evidence: bool, has_sector_theme: bool, has_named_display: bool) -> str:
        if has_market_evidence and has_text_evidence:
            return "market_and_text"
        if has_market_evidence:
            return "market_only"
        if has_text_evidence:
            return "text_only"
        if has_sector_theme or has_named_display:
            return "focus_list_only"
        return "data_thin"

    def _build_focus_watch_item(self, *, symbol: str, tier: str, display_name: str | None, primary_reason: str, list_types: Sequence[str] | None = None, symbol_context: dict[str, Any] | None = None, ordinal: int | None = None) -> dict[str, str]:
        clean_symbol = str(symbol or "").strip()
        clean_display_name = str(display_name or "").strip() or None
        display = self._format_focus_display_name(clean_symbol, clean_display_name, tier=tier, ordinal=ordinal)
        rationale_seed = self._sanitize_customer_text(primary_reason)
        symbol_context = dict(symbol_context or {})
        evidence_score = int(symbol_context.get("evidence_score") or 0)
        evidence_depth = str(symbol_context.get("evidence_depth") or "data_thin")
        has_named_display = bool(clean_display_name)
        if tier == "key_focus":
            fallback = self._fallback_key_focus_rationale(
                evidence_score=evidence_score,
                evidence_depth=evidence_depth,
                has_named_display=has_named_display,
                symbol_context=symbol_context,
            )
            rationale = self._polish_focus_reason(rationale_seed, fallback=fallback)
            validation_point = self._focus_validation_point(tier=tier, evidence_score=evidence_score)
            invalidation = self._focus_invalidation_point(tier=tier, evidence_score=evidence_score)
        else:
            fallback = self._fallback_focus_watch_rationale(
                evidence_score=evidence_score,
                evidence_depth=evidence_depth,
                has_named_display=has_named_display,
                symbol_context=symbol_context,
            )
            rationale = self._polish_focus_reason(rationale_seed, fallback=fallback)
            validation_point = self._focus_validation_point(tier=tier, evidence_score=evidence_score)
            invalidation = self._focus_invalidation_point(tier=tier, evidence_score=evidence_score)
        return {
            "symbol": clean_symbol,
            "code": clean_symbol,
            "display_name": display,
            "short_label": self._build_focus_short_label(display_name=display, symbol=clean_symbol),
            "observation_rationale": rationale,
            "today_validation_point": validation_point,
            "risk_invalidation": invalidation,
            "list_types": [str(item).strip() for item in (list_types or []) if str(item).strip()],
            "evidence_score": evidence_score,
            "evidence_depth": evidence_depth,
        }

    def _professional_empty_focus_item(self) -> dict[str, str]:
        return {
            "symbol": "",
            "display_name": "关注列表暂未展开",
            "short_label": "关注列表暂未展开",
            "observation_rationale": "当前报告把研究资源优先放在核心验证对象上，暂不额外铺开第二层观察名单。",
            "today_validation_point": "若盘中出现更明确的扩散线索、联动方向或分歧修复信号，再补充进入观察范围。",
            "risk_invalidation": "若没有新增确认依据，不为凑名单而机械扩展观察范围。",
        }

    def _format_focus_display_name(self, symbol: str, display_name: str | None, *, tier: str | None = None, ordinal: int | None = None) -> str:
        clean_name = str(display_name or "").strip()
        if clean_name:
            return clean_name
        clean_symbol = str(symbol or "").strip()
        if not clean_symbol:
            return "未命名观察对象"
        ordinal_suffix = self._focus_ordinal_label(ordinal)
        if tier == "key_focus" and ordinal_suffix:
            return f"核心观察标的{ordinal_suffix}"
        if tier == "focus_watch" and ordinal_suffix:
            return f"补充观察标的{ordinal_suffix}"
        if tier == "key_focus" and clean_symbol.endswith((".SH", ".SZ", ".BJ")):
            return f"A股核心观察对象 {clean_symbol}"
        if tier == "focus_watch" and clean_symbol.endswith((".SH", ".SZ", ".BJ")):
            return f"A股补充观察对象 {clean_symbol}"
        if tier == "key_focus":
            return f"核心观察对象{ordinal_suffix}" if ordinal_suffix else "核心观察对象"
        if tier == "focus_watch":
            return f"补充观察对象{ordinal_suffix}" if ordinal_suffix else "补充观察对象"
        if clean_symbol.endswith((".SH", ".SZ", ".BJ")):
            return f"观察对象 {clean_symbol}"
        return f"观察对象{ordinal_suffix}" if ordinal_suffix else "观察对象"

    def _build_focus_short_label(self, *, display_name: str, symbol: str) -> str:
        clean_display = str(display_name or "").strip()
        clean_symbol = str(symbol or "").strip()
        if clean_display and clean_symbol:
            return clean_display if clean_display.endswith(clean_symbol) else f"{clean_display}（{clean_symbol}）"
        return clean_display or clean_symbol

    def _focus_display_limit(self, value: int, *, cap: int) -> int:
        return max(1, min(int(value), int(cap)))

    def _focus_ordinal_label(self, ordinal: int | None) -> str:
        mapping = {
            1: "一",
            2: "二",
            3: "三",
            4: "四",
            5: "五",
            6: "六",
            7: "七",
            8: "八",
            9: "九",
            10: "十",
        }
        if ordinal is None:
            return ""
        return mapping.get(int(ordinal), str(int(ordinal)))

    def _polish_focus_reason(self, reason: str, *, fallback: str) -> str:
        clean_reason = str(reason or "").strip()
        if not clean_reason:
            return fallback
        lower_reason = clean_reason.lower()
        if "focus/key-focus" in lower_reason or "观察池覆盖" in clean_reason or "噪音过滤" in clean_reason:
            return fallback
        return clean_reason

    def _merge_focus_symbol_context(self, symbol_context_map: dict[str, dict[str, Any]], section: dict[str, Any]) -> None:
        containers = [
            (section.get("facts") or [], "fact_hits"),
            (section.get("signals") or [], "signal_hits"),
            (section.get("judgments") or [], "judgment_hits"),
        ]
        for objects, field in containers:
            for obj in objects:
                if not isinstance(obj, dict):
                    continue
                text_parts = [
                    str(obj.get("object_key") or ""),
                    str(obj.get("statement") or ""),
                    json.dumps(obj.get("attributes_json") or {}, ensure_ascii=False),
                ]
                haystack = " ".join(text_parts)
                for symbol in self._extract_symbols_from_text(haystack):
                    ctx = symbol_context_map.setdefault(symbol, {"fact_hits": 0, "signal_hits": 0, "judgment_hits": 0})
                    ctx[field] = int(ctx.get(field) or 0) + 1
        for symbol, ctx in symbol_context_map.items():
            ctx["evidence_score"] = min(3, sum(int(ctx.get(field) or 0) for field in ("fact_hits", "signal_hits", "judgment_hits")))

    def _extract_symbols_from_text(self, text: str) -> list[str]:
        return list(dict.fromkeys(re.findall(r"\b\d{6}\.(?:SZ|SH|BJ)\b", str(text or "").upper())))

    def _fallback_key_focus_rationale(self, *, evidence_score: int, evidence_depth: str, has_named_display: bool, symbol_context: dict[str, Any]) -> str:
        company = str(symbol_context.get("company_name") or "").strip()
        sector_or_theme = str(symbol_context.get("sector_or_theme") or "").strip()
        text_event_evidence = dict(symbol_context.get("text_event_evidence") or {})
        if evidence_depth == "market_and_text":
            return f"列入核心观察名单，当前已具备本地市场侧样本与文本/事件侧线索，{company or '该标的'}更适合继续核验强度、承接与主线带动性，而不是直接上升为确定性判断。"
        if evidence_depth == "market_only":
            return "列入核心观察名单，当前已有日线样本或量价记录可供观察，但文本/事件补证仍有限，先围绕盘面延续性做重点跟踪。"
        if evidence_depth == "text_only":
            text_count = sum(int(text_event_evidence.get(field) or 0) for field in ("announcement_count", "research_count", "investor_qa_count", "dragon_tiger_count", "limit_up_count", "event_count"))
            return f"列入核心观察名单，当前主要依据本地文本/事件线索（合计 {text_count} 条）进入重点观察，盘面验证仍待后续补齐，不宜提前强化结论。"
        if evidence_depth == "focus_list_only" and sector_or_theme:
            return f"列入核心观察名单，目前更多体现为名单内优先跟踪对象；本地可见行业/主题线索指向 {sector_or_theme}，但个股级市场证据仍偏薄，应先做基础验证。"
        if evidence_score >= 1:
            return "列入核心观察名单，当前已有初步线索，但证据仍偏早、偏单点，先按重点验证对象跟踪，不宜提前上调为确定性结论。"
        if has_named_display:
            return "列入核心观察名单，但当前可用证据仍偏薄，先按基础观察对象管理，并等待后续市场或事件材料补齐。"
        return "当前仅能确认其位于核心观察名单，本轮个股级证据仍有限，先按基础观察对象管理，不对其做超出证据的强化表述。"

    def _fallback_focus_watch_rationale(self, *, evidence_score: int, evidence_depth: str, has_named_display: bool, symbol_context: dict[str, Any]) -> str:
        sector_or_theme = str(symbol_context.get("sector_or_theme") or "").strip()
        text_event_evidence = dict(symbol_context.get("text_event_evidence") or {})
        if evidence_depth == "market_and_text":
            return "列入关注名单，当前已同时出现本地市场侧样本与文本/事件补证，可继续观察其是否由跟随线索发展为更明确的板块响应。"
        if evidence_depth == "market_only":
            return "列入关注名单，当前已有基础盘面样本可供跟踪，但缺少更完整的文本/事件确认，先维持观察级别。"
        if evidence_depth == "text_only":
            text_count = sum(int(text_event_evidence.get(field) or 0) for field in ("announcement_count", "research_count", "investor_qa_count", "dragon_tiger_count", "limit_up_count", "event_count"))
            return f"列入关注名单，当前主要依赖本地文本/事件线索（合计 {text_count} 条）进入观察范围；在盘面证据补出前，仍按基础关注项处理。"
        if evidence_depth == "focus_list_only" and sector_or_theme:
            return f"列入关注名单，目前更多承担扩散路径跟踪角色；本地仅有 {sector_or_theme} 方向的基础标签，尚不足以支持更高优先级。"
        if evidence_score >= 1:
            return "列入关注名单，已有初步异动或联动痕迹，但证据还不足以支持优先级上调，先保持关注。"
        if has_named_display:
            return "列入关注名单，当前更接近名单内基础关注项；若后续没有新增市场或事件证据，则继续保持关注而非强化表述。"
        return "当前仅能确认其在关注池内，个股级证据不足，因此按基础关注项处理，而不是给出过强判断。"

    def _focus_validation_point(self, *, tier: str, evidence_score: int) -> str:
        if tier == "key_focus":
            if evidence_score >= 2:
                return "盘中重点看已有线索能否继续扩展为更明确的量价配合、资金承接与板块共振确认。"
            if evidence_score == 1:
                return "盘中重点看早段线索能否获得后续成交、承接或板块联动补证，避免单点异动被误读。"
            return "盘中重点看是否补出更明确的成交、承接或联动证据；若没有新增确认，维持基础观察口径。"
        if evidence_score >= 2:
            return "盘中重点看是否继续形成跟随扩散、回流承接或更完整的联动结构。"
        if evidence_score == 1:
            return "盘中重点看初步异动能否发展为连续联动，而不是停留在零散波动。"
        return "盘中重点看是否出现新增扩散线索、回流承接或更清晰的板块联动，再决定是否提高关注级别。"

    def _focus_invalidation_point(self, *, tier: str, evidence_score: int) -> str:
        if tier == "key_focus":
            if evidence_score >= 2:
                return "若后续跟踪中量价配合转弱、承接不足或板块共振没有延续，应及时降回观察级别。"
            if evidence_score == 1:
                return "若后续没有补出更完整的量价或联动证据，说明当前仍停留在早期线索阶段，应维持观察而非强化结论。"
            return "若全天仍缺少新增个股证据，只保留名单观察属性，不把名单暴露误当作确定性信号。"
        if evidence_score >= 2:
            return "若联动扩散很快中断、回流承接不足或只剩孤立表现，则继续留在补充观察层。"
        if evidence_score == 1:
            return "若初步异动没有演化为更稳定的联动结构，则维持补充观察，不急于上调优先级。"
        return "若全天没有新增确认依据，则维持补充观察，不为凑名单而机械强化表述。"

    def _focus_reasons(self, *, reasons: Sequence[str], key_focus_symbols: Sequence[str], focus_only_symbols: Sequence[str], total_focus_count: int) -> list[str]:
        polished = [str(item).strip() for item in reasons if str(item).strip()]
        if key_focus_symbols:
            polished.append(f"核心关注 共 {len(key_focus_symbols)} 个，优先用于验证强度、节奏与是否具备继续跟踪价值。")
        if focus_only_symbols:
            polished.append(f"关注 共 {len(focus_only_symbols)} 个，作为扩散与分歧观察池，避免把临时噪音误判为主线。")
        if not polished:
            polished.append(f"当前观察池共覆盖 {total_focus_count} 个对象，用于界定优先跟踪范围与噪音过滤边界。")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in polished:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped[:3]

    def _render_focus_module_html(self, focus_module: dict[str, Any]) -> str:
        list_types = [str(item).replace("_", " ") for item in (focus_module.get("list_types") or [])]
        reasons = [str(item) for item in (focus_module.get("reasons") or []) if str(item).strip()]
        key_focus = [str(item) for item in (focus_module.get("key_focus_symbols") or []) if str(item).strip()]
        focus_watch = [str(item) for item in (focus_module.get("focus_watch_symbols") or []) if str(item).strip()]
        key_focus_items = list(focus_module.get("key_focus_items") or [])
        focus_watch_items = list(focus_module.get("focus_watch_items") or [])
        focus_symbols = [str(item) for item in (focus_module.get("focus_symbols") or []) if str(item).strip()]
        charts = focus_module.get("chart_refs") or []
        chart_text = "；".join(f"{item.get('title')}（{item.get('chart_key')}）" for item in charts if item.get("chart_key")) or "暂无图表关联"
        return (
            f'<div class="bucket"><h3>Why included</h3><ul>{"".join(f"<li>{escape(item)}</li>" for item in (reasons or [str(focus_module.get("why_included") or "暂无说明")]))}</ul></div>'
            f'<div class="bucket"><h3>Key Focus</h3><ul>{self._render_internal_focus_item_list(key_focus_items) or "".join(f"<li>{escape(item)}</li>" for item in key_focus) or "<li>暂无 Key Focus</li>"}</ul></div>'
            f'<div class="bucket"><h3>关注列表</h3><ul>{self._render_internal_focus_item_list(focus_watch_items) or "".join(f"<li>{escape(item)}</li>" for item in focus_watch) or "<li>暂无 关注列表</li>"}</ul></div>'
            f'<div class="bucket"><h3>Module coverage</h3><ul><li>total_focus_symbols：{escape(str(focus_module.get("focus_symbol_count") or len(focus_symbols)))}</li><li>displayed_symbols：{escape(", ".join(focus_symbols) or "-")}</li></ul></div>'
            f'<div class="bucket"><h3>Module wiring</h3><ul><li>list_types：{escape(", ".join(list_types) or "-")}</li><li>chart_refs：{escape(chart_text)}</li><li>judgment_refs：{escape(", ".join(focus_module.get("judgment_refs") or []) or "-")}</li></ul></div>'
        )

    def _render_internal_focus_item_list(self, items: Sequence[dict[str, Any]]) -> str:
        rendered: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("short_label") or item.get("display_name") or item.get("symbol") or "").strip()
            rationale = str(item.get("observation_rationale") or "").strip()
            validation = str(item.get("today_validation_point") or "").strip()
            risk = str(item.get("risk_invalidation") or "").strip()
            if not label:
                continue
            detail_parts = [part for part in (rationale, validation, risk) if part]
            if detail_parts:
                rendered.append(f"<li><strong>{escape(label)}</strong>：{escape(' / '.join(detail_parts))}</li>")
            else:
                rendered.append(f"<li>{escape(label)}</li>")
        return "".join(rendered)

    def _customer_section_title(self, slot: str, fallback: str) -> str:
        mapping = {
            "early": "开盘前关注",
            "mid": "盘中观察",
            "late": "收盘复盘",
        }
        return mapping.get(slot, fallback)

    def _customer_item_statements(self, items: Sequence[dict[str, Any]], *, limit: int, slot: str) -> list[str]:
        statements: list[str] = []
        for item in items:
            raw = str(item.get("statement") or "").strip()
            if not raw:
                continue
            sanitized = self._refine_customer_summary(self._sanitize_customer_text(raw), slot=slot)
            if not sanitized or self._customer_should_drop_statement(sanitized):
                continue
            if sanitized not in statements:
                statements.append(sanitized)
            if len(statements) >= limit:
                break
        return statements[:limit]

    def _sanitize_customer_text(self, text: str) -> str:
        sanitized = str(text or "").strip()
        if not sanitized:
            return sanitized
        replacements = [
            ("candidate_with_open_validation", "证据已具雏形，但仍需开盘验证"),
            ("watchlist_only", "暂列观察名单"),
            ("same-day stable/final", "收盘依据已完整"),
            ("same-day final market packet ready", "收盘依据已完整"),
            ("same-day final", "收盘依据已完整"),
            ("same-day", "当日"),
            ("high+reference", "盘前交易与资讯线索"),
            ("high layer", "盘中结构信号"),
            ("reference seed", "观察名单"),
            ("intraday retained", "盘中留存信息"),
            ("retained intraday", "盘中留存信息"),
            ("retained highfreq", "盘中过程信息"),
            ("close package", "收盘确认材料"),
            ("open validation", "开盘确认"),
            ("adjust 输入", "辅助校准"),
            ("observe/track-only", "观察/跟踪"),
        ]
        for old, new in replacements:
            sanitized = sanitized.replace(old, new)

        normalized = re.sub(r"\s+", " ", sanitized).strip(" ，；。")
        normalized = re.sub(r"盘前\s+盘中结构信号", "盘前结构线索", normalized)
        normalized = re.sub(r"盘中\s+盘中结构信号", "盘中结构信号", normalized)
        normalized = re.sub(r"收盘\s+收盘确认依据", "收盘确认依据", normalized)
        normalized = re.sub(r"收盘\s+收盘确认材料", "收盘确认材料", normalized)
        if normalized.startswith("盘前市场侧输入覆盖："):
            return self._rewrite_customer_telemetry_statement(normalized, stage="early_market")
        if normalized.startswith("盘中结构层覆盖："):
            return self._rewrite_customer_telemetry_statement(normalized, stage="mid_structure")
        if normalized.startswith("盘中领涨/事件层覆盖："):
            return self._rewrite_customer_telemetry_statement(normalized, stage="mid_leader")
        if normalized.startswith("隔夜/近期文本催化共") or normalized.startswith("盘中文本/事件解释线索") or normalized.startswith("same-day 可追溯文本/事件事实"):
            return self._rewrite_customer_telemetry_statement(normalized, stage="text_context")
        if normalized.startswith("same-day retained intraday context：") or normalized.startswith("当日 盘中留存信息 context："):
            return self._rewrite_customer_telemetry_statement(normalized, stage="late_intraday")
        if normalized.startswith("same-day 收盘稳定市场层覆盖：") or normalized.startswith("当日 收盘稳定市场层覆盖："):
            return self._rewrite_customer_telemetry_statement(normalized, stage="late_close_coverage")

        normalized = re.sub(r"validation=unknown[，,；;]?", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"emotion=unknown[，,；;]?", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"最新\s*[，,；;]?", "", normalized)
        normalized = re.sub(r"[，,；;]\s*[，,；;]+", "；", normalized)

        direct_rewrites = [
            (
                r"^盘前结构线索 与 观察名单 已足以形成待开盘验证的主线候选，但仍不应视为已确认$",
                "盘前线索与观察名单已经给出初步方向，但仍要等开盘后的量价与承接进一步确认。",
            ),
            (
                r"^午后继续验证点：等待盘中结构信号 刷新后再判断是否出现强化、扩散或分歧$",
                "午后继续观察盘中结构是否修复，并确认是否出现强化、扩散或分歧。",
            ),
            (
                r"^盘中锚点：A股盘中主线更新：盘中结构信号 证据不足或不够新鲜，仅保留跟踪/观察级更新$",
                "盘中锚点：当前结构证据仍不够扎实，更适合作为跟踪信号，而不是提前下收盘定论。",
            ),
            (
                r"^收盘依据已完整 市场表与同日文本事实已足以形成收盘确认材料，可以做晚报主线结论$",
                "收盘阶段的核心市场与文本证据已经基本到齐，足以支撑晚报对当日主线作出复盘判断。",
            ),
            (
                r"^日内 盘中过程信息 证据可用于解释从盘中到收盘的演化，但不能替代 收盘依据已完整 close 证据$",
                "盘中过程信息可用于解释日内演化，但不能替代收盘阶段的核心确认依据。",
            ),
            (
                r"^将当前 收盘依据已完整 事实作为晚报主线收盘结论依据；盘中留存信息 仅做演化解释，T-1 仅做历史对照$",
                "晚报结论应以当日收盘后的完整证据为基础；盘中过程信息仅用于解释演化，前一交易日内容仅作历史对照。",
            ),
        ]
        for pattern, replacement in direct_rewrites:
            if re.match(pattern, normalized):
                return replacement
        return normalized.strip(" ，；。")

    def _rewrite_customer_telemetry_statement(self, text: str, *, stage: str) -> str:
        numbers = {key: int(value) for key, value in re.findall(r"([\\w\\u4e00-\\u9fff/+-]+)\s(\d+)\s*[条个]?", text)}
        if stage == "early_market":
            event_count = numbers.get("事件流", 0)
            auction_count = numbers.get("竞价样本", 0)
            leader_count = numbers.get("候选龙头", 0)
            signal_count = numbers.get("信号状态", 0)
            if event_count <= 0 and auction_count <= 0 and leader_count <= 0 and signal_count <= 0:
                return "盘前市场侧确认仍然偏弱，当前更适合把相关方向视为待开盘验证的观察线索，而非直接上升为明确主线。"
            if auction_count <= 0 or leader_count <= 0 or signal_count <= 0:
                return "盘前已有部分事件与交易线索出现，但市场侧共振仍不完整，开盘后的量价承接与龙头确认仍是第一观察位。"
            return "盘前市场线索已开始形成共振，可将相关方向列为开盘后的优先验证对象，但仍不宜提前当作已确认结论。"
        if stage == "mid_structure":
            stock_1m = numbers.get("1m", 0)
            breadth = numbers.get("广度", 0)
            heat = numbers.get("热度", 0)
            signal_count = numbers.get("信号状态", 0)
            if stock_1m <= 0 and breadth <= 0 and heat <= 0 and signal_count <= 0:
                return "盘中结构验证尚不充分，当前更适合观察量价扩散、板块承接与情绪修复是否逐步形成。"
            return "盘中结构已有一定跟踪基础，但验证信号仍需继续观察，暂不宜把阶段性波动直接外推为全天定论。"
        if stage == "mid_leader":
            leader_count = numbers.get("龙头候选", 0)
            event_count = numbers.get("事件流", 0)
            if leader_count <= 0:
                return "盘中事件线索仍在演化，暂未形成足够清晰的领涨锚点，宜继续通过扩散与承接来确认主线强弱。"
            if event_count <= 0:
                return "盘中已有领涨观察对象浮现，但事件催化配合度仍需继续确认。"
            return "盘中领涨与事件线索可用于辅助判断强弱节奏，但是否能够升级为更强主线，仍需看扩散质量。"
        if stage == "text_context":
            return "相关文本与事件线索可作为背景参考，用于补充理解当日脉络，但不宜直接替代盘面与收盘口径确认。"
        if stage == "late_intraday":
            return "日内过程信号更适合用于解释盘中到收盘的演变，收盘结论仍应以稳定的收盘口径与次日延续性验证为准。"
        if stage == "late_close_coverage":
            return "收盘后的核心市场数据覆盖已经相对完整，可以支持对当日主线强弱与次日延续性做更稳健的复盘判断。"
        return text

    def _customer_should_drop_statement(self, text: str) -> bool:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return True
        noisy_patterns = [
            r"validation=unknown",
            r"emotion=unknown",
            r"(?:竞价样本|事件流|候选龙头|信号状态|1m 样本|广度|热度)\s*0\s*[条个]?",
            r"暂无标题样本",
        ]
        return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in noisy_patterns)

    def _customer_top_judgment(self, customer_sections: Sequence[dict[str, Any]]) -> str:
        early_section = next((section for section in customer_sections if section.get("slot") == "early"), None)
        mid_section = next((section for section in customer_sections if section.get("slot") == "mid"), None)
        late_section = next((section for section in customer_sections if section.get("slot") == "late"), None)
        anchor = early_section or mid_section or late_section or next(iter(customer_sections), {})
        headline = str(anchor.get("summary") or "").strip()
        highlights = [str(item).strip() for item in (anchor.get("highlights") or []) if str(item).strip()]
        early_headline = str((early_section or {}).get("summary") or "").strip()
        mid_headline = str((mid_section or {}).get("summary") or "").strip()
        late_headline = str((late_section or {}).get("summary") or "").strip()

        if early_section and not mid_section and not late_section:
            early_focuses = [
                str(item).strip("，。； ")
                for item in [early_headline, *highlights[:3]]
                if str(item).strip()
            ]
            deduped_focuses: list[str] = []
            for item in early_focuses:
                if item and item not in deduped_focuses:
                    deduped_focuses.append(item)
            if len(deduped_focuses) >= 2:
                return (
                    "当前尚未形成单一强主线，盘前更适合围绕"
                    + " / ".join(deduped_focuses[:3])
                    + "三类线索做开盘验证，再决定是否提升判断强度。"
                )
            if deduped_focuses:
                return f"盘前阶段更适合把“{deduped_focuses[0]}”视为优先验证方向，而不是直接下单一主线结论。"
            return "当前尚未形成单一强主线，盘前应先观察量价承接、领涨锚点与板块扩散是否同步出现。"

        if early_section and mid_section and late_section:
            clean_early = (early_headline or "盘前线索已给出方向").rstrip("，。； ")
            clean_mid = (mid_headline or "盘中仍在校准").rstrip("，。； ")
            clean_late = (late_headline or "收盘复核").rstrip("，。； ")
            return (
                f"今日判断更适合按“盘前预案—盘中修正—收盘复核”的顺序理解：盘前先围绕{clean_early}建立验证框架；"
                f"盘中阶段以确认节奏与强弱变化为主，{clean_mid}；"
                f"而晚报部分则用于回答当日结论是否真正站稳，{clean_late}。"
            )
        if early_section and late_section:
            clean_early = (early_headline or "盘前线索已给出方向").rstrip("，。； ")
            clean_late = (late_headline or "收盘复核").rstrip("，。； ")
            return f"当前更适合把盘前预案与收盘复核分开理解：盘前先围绕{clean_early}做验证，而收盘再用{clean_late}决定结论是否成立。"
        if mid_section and late_section:
            clean_mid = (mid_headline or "盘中仍在校准").rstrip("，。； ")
            clean_late = (late_headline or "收盘复核").rstrip("，。； ")
            return f"当前更适合先把盘中的强弱修正与节奏变化看清：{clean_mid}；待收盘证据闭合后，再以{clean_late}完成当日定性。"
        if early_section and mid_section:
            clean_early = (early_headline or "盘前线索已给出方向").rstrip("，。； ")
            clean_mid = (mid_headline or "盘中仍在校准").rstrip("，。； ")
            return f"当前判断仍处于日内验证链条中：盘前先围绕{clean_early}建立预案；进入盘中后，重点要回答的是{clean_mid}。"
        if late_section:
            clean_late = (late_headline or headline or "收盘复核").rstrip("，。； ")
            return f"晚报阶段更强调复盘而非追认：{clean_late} 当前宜把重心放在次日延续性与风险收益比，而不是把单日结果直接外推。"
        if mid_section:
            clean_mid = (mid_headline or headline or "盘中仍在校准").rstrip("，。； ")
            return f"盘中阶段更强调修正与校准：{clean_mid} 当前不宜提前替收盘结论定调。"
        if headline and highlights:
            return f"{headline} 当前更适合把重心放在验证质量与节奏把握，而不是提前把阶段性线索解读为无条件确认。"
        if headline:
            return f"{headline} 当前应沿着主线确认、风险控制与后续观察三条线并行推进。"
        if highlights:
            return f"当前更适合围绕“{highlights[0]}”安排观察顺序，并根据后续证据决定是否提高判断强度。"
        return "当前报告以主线确认、风险控制与次日观察三条线并行展开。"

    def _customer_slot_advisory_note(
        self,
        *,
        slot: str,
        summary: str,
        highlights: Sequence[str],
        signals: Sequence[str],
        support_items: Sequence[dict[str, Any]],
    ) -> str:
        support_domains = "、".join(str(item.get("domain") or "补充视角") for item in support_items[:2])
        headline = summary.strip()
        first_highlight = next((str(item).strip() for item in highlights if str(item).strip()), "")
        first_signal = next((str(item).strip() for item in signals if str(item).strip()), "")
        if slot == "early":
            return first_highlight or first_signal or "盘前更适合先确认是否出现可持续的量价与领涨共振，再决定是否提高判断强度。"
        if slot == "mid":
            return first_signal or "盘中阶段以校准节奏为主，重点观察结构是否继续修复，以及扩散质量与承接稳定度是否同步改善。"
        if slot == "late":
            overlay = f"，并结合{support_domains}的补充线索做交叉核对" if support_domains else ""
            return f"收盘判断宜回到全天证据框架中复核{overlay}；若次日缺少延续性，结论应及时回落为跟踪而非追认。"
        return headline or first_highlight or "当前判断应继续结合新增证据滚动更新。"

    def _customer_risk_block(self, customer_sections: Sequence[dict[str, Any]]) -> list[str]:
        slot_risks: list[str] = []
        support_risks: list[str] = []
        for section in customer_sections:
            slot = str(section.get("slot") or "")
            section_signals = [str(item).strip() for item in (section.get("signals") or []) if str(item).strip()]
            section_facts = [str(item).strip() for item in (section.get("facts") or []) if str(item).strip()]
            if slot == "early":
                if section_signals:
                    slot_risks.append("盘前最大的风险不在于线索不足，而在于开盘后承接与扩散不能接住预期；一旦验证落空，应把判断及时降回观察层。")
                elif section_facts:
                    slot_risks.append("盘前线索仍需等待开盘后的价格、量能与领涨反馈共同确认，单一消息面不足以支持追认。")
            elif slot == "mid":
                if section_signals:
                    slot_risks.append("盘中最容易出现的问题，是把阶段性修复或局部异动误读为全天定论；若扩散、承接和强弱排序没有同步改善，判断仍应维持校准口径。")
                elif section_facts:
                    slot_risks.append("盘中看到的结构变化更多用于修正节奏，而不是替收盘定性；若午后确认链条没有补齐，应继续把相关方向视为跟踪对象。")
            elif slot == "late":
                if section_signals:
                    slot_risks.append("收盘结论只能说明当日证据框架已经闭合，不代表次日延续性已经自动成立；隔夜若缺少增量催化，强度判断需要重新评估。")
                elif section_facts:
                    slot_risks.append("收盘复盘仍需与次日资金回流、板块扩散和核心标的承接情况交叉验证，避免把单日结果外推过度。")
            for support in section.get("support_themes") or []:
                summary = str(support.get("summary") or "").strip()
                if summary:
                    support_risks.append(f"补充视角更适合用来修正主判断的边界，不能单独替代主线结论；当前尤其要防止把“{summary}”直接上升为核心交易依据。")
        deduped: list[str] = []
        for item in [*slot_risks, *support_risks]:
            if item and item not in deduped:
                deduped.append(item)
        if not deduped:
            deduped.append("若量价确认、板块扩散或风险偏好数据未跟上，主线判断需要快速降级为观察而非追价。")
        return deduped[:3]

    def _customer_next_steps(self, customer_sections: Sequence[dict[str, Any]], focus_module: dict[str, Any]) -> list[str]:
        next_steps: list[str] = []
        early_section = next((section for section in customer_sections if section.get("slot") == "early"), None)
        mid_section = next((section for section in customer_sections if section.get("slot") == "mid"), None)
        late_section = next((section for section in customer_sections if section.get("slot") == "late"), None)
        if early_section:
            next_steps.append("开盘后先看核心主线是否出现量价共振、板块扩散与领涨锚点同步改善，再决定是否提升当天判断强度。")
        if mid_section:
            next_steps.append("午后优先核对盘中修复能否扩展到板块层与核心标的层；若确认链条仍不完整，应继续把仓位与表述都保持在校准档。")
        if late_section:
            next_steps.append("收盘后重点复核当日强势是否具备次日延续条件，尤其关注资金回流、板块承接与核心标的分化是否仍然健康。")
        key_focus_items = [item for item in (focus_module.get("key_focus_items") or []) if isinstance(item, dict)]
        if key_focus_items:
            labels = [self._customer_focus_label(item) for item in key_focus_items[:3]]
            labels = [item for item in labels if item]
            if labels:
                next_steps.append(f"重点跟踪名单建议继续围绕 {'、'.join(labels)} 展开，优先比较强弱排序、承接质量与是否继续得到主线验证。")
        if not next_steps:
            next_steps.append("明日观察：继续围绕主线确认、风险约束与重点标的强弱分化来更新判断。")
        return next_steps[:3]

    def _render_customer_html(
        self,
        *,
        title: str,
        assembled: dict[str, Any],
        sections: Sequence[dict[str, Any]],
        generated_at: datetime,
        chart_manifest: dict[str, Any] | None,
    ) -> str:
        presentation = self._build_customer_presentation(assembled=assembled, sections=sections, chart_manifest=chart_manifest)
        summary_cards = "".join(self._render_customer_summary_card(card) for card in presentation["summary_cards"])
        focus_module_html = self._render_customer_focus_module(presentation.get("focus_module") or {})
        chart_pack_html = self._render_customer_chart_pack(presentation.get("chart_pack") or {})
        section_html = "".join(self._render_customer_section(section) for section in presentation["sections"])
        risk_block_html = self._render_customer_bucket("风险提示", presentation.get("risk_block") or [], fallback="暂无明确风险提示")
        next_steps_html = self._render_customer_bucket("明日观察 / 下一步", presentation.get("next_steps") or [], fallback="暂无下一步观察")
        disclaimer_html = self._render_customer_bucket("免责声明", [str(presentation.get("disclaimer") or "")], fallback="暂无免责声明")
        return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f7f8fc; color: #0f172a; }}
    .page {{ max-width: 960px; margin: 0 auto; padding: 28px 20px 44px; }}
    .hero {{ background: linear-gradient(135deg, #1d4ed8, #4338ca); color: #fff; border-radius: 20px; padding: 28px 28px 24px; }}
    .eyebrow {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.85; }}
    .hero h1 {{ margin: 8px 0 10px; font-size: 32px; }}
    .hero .meta {{ font-size: 14px; line-height: 1.6; opacity: 0.92; }}
    .hero .judgment {{ margin-top: 14px; padding: 14px 16px; border-radius: 14px; background: rgba(255,255,255,0.14); font-size: 16px; line-height: 1.65; }}
    .card {{ background: #fff; border-radius: 18px; padding: 22px 22px; margin-top: 18px; box-shadow: 0 10px 26px rgba(15, 23, 42, 0.07); }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
    .summary-box {{ border: 1px solid #dbe3f1; border-radius: 14px; padding: 14px 16px; background: #f8fbff; }}
    .summary-slot {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; }}
    .summary-headline {{ margin-top: 8px; font-size: 15px; line-height: 1.6; font-weight: 600; }}
    .support-line {{ margin-top: 10px; font-size: 13px; color: #475569; line-height: 1.6; }}
    .product-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    .section {{ border-top: 1px solid #e2e8f0; padding-top: 18px; margin-top: 18px; }}
    .section:first-child {{ border-top: none; padding-top: 0; margin-top: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    h3 {{ margin: 0 0 10px; font-size: 19px; }}
    .section-summary {{ font-size: 15px; line-height: 1.65; color: #1e293b; }}
    .bucket {{ margin-top: 14px; }}
    .bucket-title {{ font-size: 13px; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.04em; }}
    ul {{ margin: 8px 0 0 18px; padding: 0; }}
    li {{ margin: 6px 0; line-height: 1.6; }}
    .footnote {{ margin-top: 16px; font-size: 12px; color: #64748b; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class=\"page\">
    <section class=\"hero\">
      <div class=\"eyebrow\">{escape(str(presentation.get('brand') or 'iFA'))}</div>
      <h1>{escape(self._customer_report_title(str(presentation.get('requested_slot') or '')))}｜{escape(str(assembled.get('business_date') or '-'))}</h1>
      <div class=\"meta\">{escape(str(presentation.get('created_by') or ''))}<br/>业务日期：{escape(str(assembled.get('business_date') or '-'))} · 市场：A股 · 版本定位：{escape(self._customer_version_position(str(presentation.get('requested_slot') or '')))}<br/>这是面向客户的简版展示层，仅展示结论、跟踪重点与补充视角，不展示内部运行对象。</div>
      <div class=\"judgment\"><strong>核心判断：</strong>{escape(str(presentation.get('top_judgment') or '暂无核心判断'))}</div>
    </section>
    <section class=\"card\">
      <h2>今日节奏</h2>
      <div class=\"summary-grid\">{summary_cards}</div>
      <div class=\"footnote\">生成时间：{escape(generated_at.isoformat())} · 展示层 schema：{escape(CUSTOMER_PRESENTATION_SCHEMA_VERSION)}</div>
    </section>
    <section class=\"card\">
      <h2>风险与下一步</h2>
      <div class=\"product-grid\">
        <div>{risk_block_html}</div>
        <div>{next_steps_html}</div>
      </div>
    </section>
    <section class=\"card\">
      <h2>今日 核心关注 / 关注</h2>
      {focus_module_html}
    </section>
    {chart_pack_html}
    <section class=\"card\">
      <h2>{escape(self._customer_section_group_title(str(presentation.get('requested_slot') or '')))}</h2>
      {section_html}
    </section>
    <section class=\"card\">
      <h2>免责声明</h2>
      {disclaimer_html}
    </section>
  </div>
</body>
</html>
"""

    def _render_customer_summary_card(self, card: dict[str, Any]) -> str:
        support_line = ""
        if card.get("support_themes"):
            support_text = " · ".join(f"{item['domain']}：{item['summary']}" for item in card.get("support_themes") or [])
            support_line = f"<div class=\"support-line\"><strong>补充视角：</strong>{escape(support_text)}</div>"
        advisory_note = str(card.get("advisory_note") or "").strip()
        advisory_html = f"<div class=\"support-line\"><strong>顾问提示：</strong>{escape(advisory_note)}</div>" if advisory_note else ""
        slot = str(card.get("slot") or "").strip().lower()
        product_position = {
            "early": "早报 / 盘前客户主报告",
            "mid": "中报 / 盘中客户主报告",
            "late": "晚报 / 收盘客户主报告",
        }.get(slot, f"{str(card.get('slot_label') or '-')}客户主报告摘要")
        return f"<div class=\"summary-box\"><div class=\"summary-slot\">{escape(str(card.get('slot_label') or '-'))}</div><div class=\"summary-headline\">{escape(str(card.get('headline') or '暂无摘要'))}</div><div class=\"support-line\"><strong>产品定位：</strong>{escape(product_position)}</div>{advisory_html}{support_line}</div>"

    def _customer_report_title(self, requested_slot: str) -> str:
        return {
            "early": "iFA A股盘前策略简报",
            "mid": "iFA A股盘中策略简报",
            "late": "iFA A股收盘策略简报",
        }.get(requested_slot, "iFA A股市场日报")

    def _customer_version_position(self, requested_slot: str) -> str:
        return {
            "early": "早报 / 盘前客户主报告",
            "mid": "中报 / 盘中客户主报告",
            "late": "晚报 / 收盘客户主报告",
        }.get(requested_slot, "客户主报告")

    def _customer_section_group_title(self, requested_slot: str) -> str:
        return {
            "early": "盘前重点解读",
            "mid": "盘中重点解读",
            "late": "收盘重点解读",
        }.get(requested_slot, "分时段重点解读")

    def _customer_focus_label(self, item: dict[str, Any]) -> str:
        label = str(item.get("short_label") or item.get("display_name") or item.get("symbol") or "").strip()
        code = str(item.get("code") or item.get("symbol") or "").strip()
        if not code:
            return label
        if label.endswith(code):
            return label
        if label in {"核心观察标的", "补充观察标的", "观察标的", "观察对象"}:
            return f"{label}（{code}）"
        return label

    def _render_customer_focus_module(self, focus_module: dict[str, Any]) -> str:
        reasons = [str(item) for item in (focus_module.get("reasons") or []) if str(item).strip()]
        if not reasons:
            reasons = [str(focus_module.get("why_included") or "将今日核心关注池直接前置展示，帮助理解为什么这些对象值得跟踪。")]
        key_focus_items = list(focus_module.get("key_focus_items") or [])
        focus_watch_items = list(focus_module.get("focus_watch_items") or [])
        chart_refs = [str(item.get("title") or item.get("chart_key") or "") for item in (focus_module.get("chart_refs") or []) if str(item.get("title") or item.get("chart_key") or "").strip()]
        return (
            self._render_customer_bucket("为什么纳入", reasons, fallback="暂无纳入说明")
            + self._render_customer_watchlist_bucket("核心关注", key_focus_items, fallback="核心关注列表暂未生成")
            + self._render_customer_watchlist_bucket("关注", focus_watch_items, fallback="关注列表暂未展开")
            + self._render_customer_bucket("关联图表", chart_refs, fallback="暂无关联图表")
        )

    def _render_customer_watchlist_bucket(self, title: str, items: Sequence[dict[str, Any]], *, fallback: str) -> str:
        rows: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            label = self._customer_focus_label(item)
            rationale = self._sanitize_customer_text(str(item.get("observation_rationale") or "").strip())
            validation = self._sanitize_customer_text(str(item.get("today_validation_point") or "").strip())
            risk = self._sanitize_customer_text(str(item.get("risk_invalidation") or "").strip())
            if not label:
                continue
            detail_parts = []
            if rationale:
                detail_parts.append(f"纳入原因：{rationale}")
            if validation:
                detail_parts.append(f"盘中观察要点：{validation}")
            if risk:
                detail_parts.append(f"需要下调关注的情形：{risk}")
            rows.append(f"<li><strong>{escape(label)}</strong><br/>{'<br/>'.join(escape(part) for part in detail_parts) if detail_parts else escape(fallback)}</li>")
        if not rows:
            rows = [f"<li>{escape(fallback)}</li>"]
        return f"<div class=\"bucket\"><div class=\"bucket-title\">{escape(title)}</div><ul>{''.join(rows)}</ul></div>"

    def _render_customer_chart_pack(self, chart_pack: dict[str, Any]) -> str:
        assets = list(chart_pack.get("assets") or [])
        if not assets:
            return ""
        items = []
        for asset in assets:
            source_window = dict(asset.get("source_window") or {})
            note = self._customer_chart_note(str(asset.get("note") or "").strip())
            note_html = f" · 说明={escape(note)}" if note else ""
            items.append(
                f"<li>{escape(str(asset.get('title') or '-'))} · 状态={escape(self._customer_chart_status(str(asset.get('status') or '-')))} · 观察窗口={escape(str(source_window.get('lookback_bars') or '-'))} 根{escape(str(source_window.get('frequency') or '-'))}样本{note_html}</li>"
            )
        return f"<section class=\"card\"><h2>关键图表</h2><div class=\"footnote\">{escape(self._customer_chart_pack_summary(chart_pack))}</div><ul>{''.join(items)}</ul></section>"

    def _customer_chart_status(self, status: str) -> str:
        return {
            "ready": "已展示",
            "missing": "暂未展示",
            "partial": "部分展示",
        }.get(status, status or "-")

    def _customer_chart_note(self, note: str) -> str:
        if note == "insufficient focus bars to calculate day-over-day return":
            return "连续行情样本不足，暂不展示对应涨跌幅对比。"
        if note == "focus/equity daily bars missing for requested window":
            return "连续行情样本不足，当前保留窗口图作为主要参考。"
        return note

    def _customer_chart_pack_summary(self, chart_pack: dict[str, Any]) -> str:
        ready_count = int(chart_pack.get("ready_chart_count") or 0)
        chart_count = int(chart_pack.get("chart_count") or 0)
        if chart_count and ready_count < chart_count:
            return "部分图表因连续行情样本不足暂不展示涨跌幅对比，本期保留指数与核心关注窗口图作为主要参考。"
        if chart_count:
            return "本期关键图表样本完整，可结合指数与核心关注对象窗口变化一并阅读。"
        return "本期未生成可展示图表。"

    def _refine_customer_summary(self, text: str, *, slot: str, is_support: bool = False) -> str:
        summary = str(text or "").strip(" ，；。")
        if not summary:
            return summary
        summary = re.sub(r"^A股", "", summary)
        summary = re.sub(r"\s+", " ", summary).strip()
        if is_support:
            support_rewrites = [
                (r"^盘前 AI-tech 有新催化/板块强弱变化，应作为主判断的 辅助校准$", "AI / 科技线索有增量变化，可作为盘前主判断的辅助校准。"),
                (r"^盘前商品链有新变化，应作为主判断的 辅助校准$", "商品方向出现新变化，可作为盘前主判断的辅助校准。"),
                (r"^盘前宏观背景有新变化，应先作为主判断的 辅助校准，而不是直接当作已验证主线$", "宏观背景出现新变化，更适合用于校准主判断边界，而不是直接上升为已验证主线。"),
                (r"^晚报 AI-tech 催化存在但板块承接偏弱，更适合作为次日降权/防伪强信号$", "AI / 科技方向有催化，但板块承接仍偏弱，更适合作为次日强弱甄别的辅助线索。"),
                (r"^晚报商品链形成可追溯变化，应沉淀为次日优先验证链条$", "商品方向已出现可跟踪变化，值得列入次日优先验证名单。"),
                (r"^晚报宏观更像放大器/修正项，应沉淀为次日优先监控变量$", "宏观因素更像放大器与修正项，适合列入次日重点监控变量。"),
            ]
            for pattern, replacement in support_rewrites:
                if re.match(pattern, summary):
                    return replacement
            return summary
        rewrites = {
            "early": [
                (r"^盘前主线预案：已基于盘前 盘前交易与资讯线索 形成待开盘验证的主线候选$", "盘前线索已初步指向主线方向，但是否值得提高仓位或预期，仍要等开盘后的量价与承接确认。"),
            ],
            "mid": [
                (r"^盘中主线更新：盘中 盘中结构信号 证据不足或不够新鲜，仅保留跟踪/观察级更新$", "盘中证据仍偏谨慎，当前更适合把市场理解为跟踪与校准阶段，而不是提前下收盘定论。"),
                (r"^盘中主线更新：盘中结构信号 证据不足或不够新鲜，仅保留跟踪/观察级更新$", "盘中证据仍偏谨慎，当前更适合把市场理解为跟踪与校准阶段，而不是提前下收盘定论。"),
            ],
            "late": [
                (r"^收盘主线复盘：已基于 收盘依据已完整 市场表与 当日 文本事实形成收盘结论$", "收盘复盘显示，当日主线已经具备较完整的确认基础，但是否能自然延续到下一交易日，仍需观察后续承接。"),
            ],
        }
        for pattern, replacement in rewrites.get(slot, []):
            if re.match(pattern, summary):
                return replacement
        return summary

    def _render_customer_section(self, section: dict[str, Any]) -> str:
        support_items = section.get("support_themes") or []
        support_html = ""
        if support_items:
            support_html = self._render_customer_bucket(
                "补充视角",
                [f"{item.get('domain')}：{item.get('summary')}" for item in support_items if item.get('summary')],
                fallback="暂无补充视角",
            )
        next_step_title = {
            "early": "开盘后验证点",
            "mid": "午后观察点",
            "late": "次日跟踪点",
        }.get(str(section.get("slot") or ""), "后续观察点")
        next_step_items = (section.get('signals') or [])[:2] or (section.get('highlights') or [])[:2]
        advisory_note_html = self._render_customer_bucket(
            '顾问提示',
            [str(section.get('advisory_note') or '').strip()],
            fallback='暂无顾问提示',
        )
        return f"""
        <div class=\"section\">
          <h3>{escape(str(section.get('title') or '-'))}</h3>
          <div class=\"section-summary\">{escape(str(section.get('summary') or '暂无摘要'))}</div>
          {advisory_note_html}
          {self._render_customer_bucket('重点结论', section.get('highlights') or [], fallback='暂无重点结论')}
          {self._render_customer_bucket('跟踪信号', section.get('signals') or [], fallback='暂无跟踪信号')}
          {self._render_customer_bucket('已知事实', section.get('facts') or [], fallback='暂无已知事实')}
          {self._render_customer_bucket(next_step_title, next_step_items, fallback='暂无后续观察点')}
          {support_html}
        </div>
        """

    def _render_customer_bucket(self, title: str, items: Sequence[str], *, fallback: str) -> str:
        values = [str(item).strip() for item in items if str(item).strip()]
        if not values:
            values = [fallback]
        return f"<div class=\"bucket\"><div class=\"bucket-title\">{escape(title)}</div><ul>{''.join(f'<li>{escape(item)}</li>' for item in values)}</ul></div>"

    def _render_chart_pack_html(self, chart_manifest: dict[str, Any] | None) -> str:
        manifest = dict(chart_manifest or {})
        assets = list(manifest.get("assets") or [])
        if not assets:
            return ""
        cards = []
        for asset in assets:
            source_window = dict(asset.get("source_window") or {})
            cards.append(
                f"<div class=\"section\"><h3>{escape(str(asset.get('title') or '-'))}</h3><div class=\"section-meta\"><span class=\"{'pill' if asset.get('status') == 'ready' else 'pill missing'}\">{escape(str(asset.get('status') or '-'))}</span>chart_class={escape(str(asset.get('chart_class') or '-'))} · source_window={escape(str(source_window.get('lookback_bars') or '-'))} {escape(str(source_window.get('frequency') or '-'))} bars · asset={escape(str(asset.get('relative_path') or '-'))}</div><img src=\"{escape(str(asset.get('relative_path') or ''))}\" alt=\"{escape(str(asset.get('title') or 'chart'))}\" style=\"width:100%;border:1px solid #dbe3f1;border-radius:16px;background:#fff;margin-top:12px;\" /><div class=\"footnote\">{escape(str(asset.get('note') or ''))}</div></div>"
            )
        return f"<section class=\"card\"><h2>关键图表包</h2><div class=\"footnote\">chart_degrade_status={escape(str(manifest.get('degrade_status') or '-'))} · ready_chart_count={escape(str(manifest.get('ready_chart_count') or '-'))}/{escape(str(manifest.get('chart_count') or '-'))}</div>{''.join(cards)}</section>"

    def _build_executive_summary(self, sections: Sequence[dict[str, Any]]) -> str:
        boxes: list[str] = []
        for section in sections:
            label = SLOT_LABELS.get(str(section.get("slot") or ""), str(section.get("slot") or "未命名时段"))
            headline = section.get("summary") or "暂无摘要"
            support_line = self._render_support_inline(section.get("support_summaries") or [])
            boxes.append(
                f"<div class=\"summary-box\"><div class=\"slot\">{escape(label)}</div><div class=\"headline\">{escape(str(headline))}</div>{support_line}</div>"
            )
        if not boxes:
            boxes.append("<div class=\"summary-box\"><div class=\"slot\">EMPTY</div><div class=\"headline\">暂无可渲染章节</div></div>")
        return "".join(boxes)

    def _build_institutional_panel(self, assembled: dict[str, Any], sections: Sequence[dict[str, Any]]) -> str:
        ready_sections = [section for section in sections if str(section.get("status") or "") == "ready"]
        support_summaries = [item for section in sections for item in (section.get("support_summaries") or [])]
        support_domains = sorted({
            SUPPORT_DOMAIN_LABELS.get(str(item.get("agent_domain") or ""), str(item.get("agent_domain") or "support"))
            for item in support_summaries
        })
        late_mode = self._late_contract_mode(sections)
        slot_labels = [SLOT_LABELS.get(str(section.get("slot") or ""), str(section.get("slot") or "-")) for section in ready_sections]
        strongest_slot = max(
            sections,
            key=lambda section: (
                1 if str(section.get("status") or "") == "ready" else 0,
                len(section.get("judgments") or []) + len(section.get("signals") or []) + len(section.get("facts") or []),
            ),
            default=None,
        )
        strongest_slot_label = SLOT_LABELS.get(str((strongest_slot or {}).get("slot") or ""), str((strongest_slot or {}).get("slot") or "-"))
        panel_items = [
            {
                "label": "执行覆盖",
                "value": f"{len(ready_sections)}/{len(sections) or 0}",
                "detail": f"ready 时段：{', '.join(slot_labels) if slot_labels else '暂无 ready section'}",
            },
            {
                "label": "晚报合同口径",
                "value": self._late_mode_label(late_mode),
                "detail": "full_close_package 才是标准送达口径；provisional_close_only 需人工复核。",
            },
            {
                "label": "Support 覆盖",
                "value": str(len(support_summaries)),
                "detail": f"域：{', '.join(support_domains) if support_domains else '无 support summary merge'}",
            },
            {
                "label": "主强时段",
                "value": strongest_slot_label,
                "detail": f"section_count={assembled.get('section_count') or len(sections)} · support_domains={len(support_domains)}",
            },
        ]
        return "".join(
            f"<div class=\"panel-box\"><div class=\"panel-label\">{escape(item['label'])}</div><div class=\"panel-value\">{escape(item['value'])}</div><div class=\"panel-detail\">{escape(item['detail'])}</div></div>"
            for item in panel_items
        )

    def _late_contract_mode(self, sections: Sequence[dict[str, Any]]) -> str | None:
        for section in sections:
            if str(section.get("slot") or "") != "late":
                continue
            for signal in section.get("signals") or []:
                attrs = dict(signal.get("attributes_json") or {})
                mode = attrs.get("contract_mode")
                if mode:
                    return str(mode)
        return None

    def _late_mode_label(self, mode: str | None) -> str:
        mapping = {
            "full_close_package": "正式收盘口径",
            "provisional_close_only": "临时收盘口径",
            "historical_only": "历史回放口径",
        }
        return mapping.get(str(mode or ""), str(mode or "未声明"))

    def _render_support_inline(self, support_summaries: Sequence[dict[str, Any]]) -> str:
        if not support_summaries:
            return ""
        text = " · ".join(
            f"{SUPPORT_DOMAIN_LABELS.get(str(item.get('agent_domain') or ''), str(item.get('agent_domain') or 'support'))}：{str(item.get('summary') or '暂无摘要')}"
            for item in support_summaries
        )
        return f"<div class=\"support-inline\"><strong>support 摘要：</strong>{escape(text)}</div>"

    def _render_section(self, section: dict[str, Any]) -> str:
        bundle = section.get("bundle") or {}
        lineage = section.get("lineage") or {}
        slot_label = SLOT_LABELS.get(str(section.get("slot") or ""), str(section.get("slot") or "未命名时段"))
        status = str(section.get("status") or "unknown")
        pill_class = "pill missing" if status != "ready" else "pill"
        judgments = self._render_items(section.get("judgments") or [], fallback="暂无主判断")
        signals = self._render_items(section.get("signals") or [], fallback="暂无关键验证信号")
        facts = self._render_items(section.get("facts") or [], fallback="暂无事实锚点")
        support_block = self._render_support_block(section.get("support_summaries") or [])
        evidence_keys = [str(item.get("ref_key")) for item in (lineage.get("evidence_links") or []) if item.get("ref_key")]
        report_uris = [str(item.get("artifact_uri")) for item in (lineage.get("report_links") or []) if item.get("artifact_uri")]
        lineage_note = "；".join(
            part for part in [
                f"evidence={', '.join(evidence_keys[:3])}" if evidence_keys else "",
                f"report_links={', '.join(report_uris[:2])}" if report_uris else "",
                f"support_bundle_ids={', '.join(lineage.get('support_bundle_ids') or [])}" if (lineage.get('support_bundle_ids') or []) else "",
            ] if part
        ) or "无既有 report link"
        return f"""
        <div class=\"section\">
          <h3>{escape(str(section.get('title') or slot_label))}</h3>
          <div class=\"section-meta\">
            <span class=\"{pill_class}\">{escape(status)}</span>
            时段：{escape(slot_label)} · bundle：<span class=\"mono\">{escape(str(bundle.get('bundle_id') or '-'))}</span> · producer_version：<span class=\"mono\">{escape(str(bundle.get('producer_version') or '-'))}</span>
          </div>
          <div><strong>摘要：</strong>{escape(str(section.get('summary') or '暂无摘要'))}</div>
          {support_block}
          <div class=\"bucket\"><strong>主判断</strong>{judgments}</div>
          <div class=\"bucket\"><strong>关键验证 / 信号</strong>{signals}</div>
          <div class=\"bucket\"><strong>事实锚点</strong>{facts}</div>
          <div class=\"footnote\">
            lineage：slot_run_id=<span class=\"mono\">{escape(str(bundle.get('slot_run_id') or '-'))}</span> · replay_id=<span class=\"mono\">{escape(str(bundle.get('replay_id') or '-'))}</span> · {escape(lineage_note)}
          </div>
        </div>
        """

    def _render_support_block(self, support_summaries: Sequence[dict[str, Any]]) -> str:
        if not support_summaries:
            return ""
        items: list[str] = []
        for item in support_summaries:
            domain_label = SUPPORT_DOMAIN_LABELS.get(str(item.get("agent_domain") or ""), str(item.get("agent_domain") or "support"))
            report_uris = [str(link.get("artifact_uri")) for link in (((item.get("lineage") or {}).get("report_links") or [])) if link.get("artifact_uri")]
            evidence_keys = [str(link.get("ref_key")) for link in (((item.get("lineage") or {}).get("evidence_links") or [])) if link.get("ref_key")]
            foot = "；".join(
                part for part in [
                    f"bundle_id={item.get('bundle_id')}" if item.get("bundle_id") else "",
                    f"producer_version={item.get('producer_version')}" if item.get("producer_version") else "",
                    f"report_links={', '.join(report_uris[:2])}" if report_uris else "",
                    f"evidence={', '.join(evidence_keys[:2])}" if evidence_keys else "",
                ] if part
            )
            items.append(
                f"<div class=\"support-item\"><div class=\"support-domain\">{escape(domain_label)}</div><div class=\"support-summary\">{escape(str(item.get('summary') or '暂无摘要'))}</div><div class=\"footnote\">{escape(foot or '仅注入 concise support summary')}</div></div>"
            )
        return f"<div class=\"support-block\"><strong>Support 摘要（非全文）</strong>{''.join(items)}</div>"

    def _render_items(self, items: Sequence[dict[str, Any]], *, fallback: str) -> str:
        if not items:
            return f"<ul><li>{escape(fallback)}</li></ul>"
        rendered: list[str] = []
        for item in items:
            statement = escape(str(item.get("statement") or "-"))
            attrs: list[str] = []
            if item.get("judgment_action"):
                attrs.append(f"action={item['judgment_action']}")
            if item.get("signal_strength"):
                attrs.append(f"strength={item['signal_strength']}")
            if item.get("confidence"):
                attrs.append(f"confidence={item['confidence']}")
            if item.get("evidence_level"):
                attrs.append(f"evidence={item['evidence_level']}")
            suffix = f" <span class=\"mono\">[{escape(', '.join(attrs))}]</span>" if attrs else ""
            rendered.append(f"<li>{statement}{suffix}</li>")
        return f"<ul>{''.join(rendered)}</ul>"

    def _build_report_links(
        self,
        sections: Sequence[dict[str, Any]],
        *,
        report_run_id: str | None,
        artifact_uri: str | None,
    ) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []
        for section in sections:
            bundle = section.get("bundle") or {}
            bundle_id = bundle.get("bundle_id")
            if not bundle_id:
                continue
            links.append(
                {
                    "bundle_id": bundle_id,
                    "report_run_id": report_run_id,
                    "artifact_type": "html",
                    "artifact_uri": artifact_uri,
                    "artifact_locator_json": {"renderer": RENDERER_NAME, "artifact_uri": artifact_uri},
                    "section_render_key": section.get("section_render_key"),
                }
            )
        return links


class MainReportRenderingService:
    def __init__(
        self,
        assembly_service: MainReportAssemblyService,
        renderer: MainReportHTMLRenderer | None = None,
    ) -> None:
        self.assembly_service = assembly_service
        self.renderer = renderer or MainReportHTMLRenderer()

    def render_main_report_html(
        self,
        *,
        business_date: str,
        include_empty: bool = False,
        report_run_id: str | None = None,
        artifact_uri: str | None = None,
        output_profile: str = "internal",
    ) -> dict[str, Any]:
        assembled = self.assembly_service.assemble_main_sections(
            business_date=business_date,
            include_empty=include_empty,
        )
        return self.renderer.render(
            assembled,
            report_run_id=report_run_id,
            artifact_uri=artifact_uri,
            output_profile=output_profile,
        )


class MainReportArtifactPublishingService:
    ARTIFACT_FAMILY = "main_final_report"
    DELIVERY_PACKAGE_VERSION = "v1"

    def __init__(
        self,
        rendering_service: MainReportRenderingService,
        store: FSJStore,
        qa_evaluator: MainReportQAEvaluator | None = None,
        evaluation_harness: MainReportEvaluationHarness | None = None,
        artifact_root: str | Path | None = None,
        chart_pack_builder: FSJChartPackBuilder | None = None,
    ) -> None:
        self.rendering_service = rendering_service
        self.store = store
        self.qa_evaluator = qa_evaluator or MainReportQAEvaluator()
        self.evaluation_harness = evaluation_harness or MainReportEvaluationHarness()
        self.dispatch_helper = MainReportDeliveryDispatchHelper()
        self.chart_pack_builder = chart_pack_builder or FSJChartPackBuilder()
        self.artifact_root = require_explicit_non_live_artifact_root(
            flow_name=f"{self.__class__.__name__}.__init__",
            artifact_root=artifact_root,
        )

    def publish_main_report_html(
        self,
        *,
        business_date: str,
        output_dir: str | Path,
        include_empty: bool = False,
        report_run_id: str | None = None,
        generated_at: datetime | None = None,
        output_profile: str = "internal",
        requested_customer_slot: str | None = None,
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        output_path = enforce_artifact_publish_root_contract(
            flow_name=f"{self.__class__.__name__}.publish_main_report_html",
            artifact_root=self.artifact_root,
            output_path=output_dir,
        )
        output_path.mkdir(parents=True, exist_ok=True)
        stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
        artifact_id = f"fsj-main-report:{business_date}:{stamp}:{uuid4().hex[:8]}"
        html_path = output_path / f"a_share_main_report_{business_date}_{stamp}.html"
        artifact_uri = html_path.resolve().as_uri()
        effective_report_run_id = report_run_id or artifact_id

        assembled = self.rendering_service.assembly_service.assemble_main_sections(
            business_date=business_date,
            include_empty=include_empty,
        )
        if output_profile == "customer" and requested_customer_slot:
            assembled = {**assembled, "requested_customer_slot": requested_customer_slot}
        chart_manifest = self.chart_pack_builder.build_main_chart_pack(
            business_date=business_date,
            assembled=assembled,
            package_dir=output_path,
        )
        rendered = self.rendering_service.renderer.render(
            assembled,
            report_run_id=effective_report_run_id,
            artifact_uri=artifact_uri,
            output_profile=output_profile,
            chart_manifest=chart_manifest,
        )
        html_path.write_text(rendered["content"], encoding="utf-8")
        evaluation = self.qa_evaluator.evaluate(assembled, rendered)
        report_eval = self.evaluation_harness.evaluate(assembled, rendered, evaluation)

        artifact_record = self.store.register_report_artifact(
            {
                "artifact_id": artifact_id,
                "artifact_family": self.ARTIFACT_FAMILY,
                "market": str(rendered["metadata"].get("market") or "a_share"),
                "business_date": business_date,
                "agent_domain": str(rendered["metadata"].get("agent_domain") or "main"),
                "render_format": rendered["render_format"],
                "artifact_type": rendered["artifact_type"],
                "content_type": rendered["content_type"],
                "title": rendered["title"],
                "report_run_id": effective_report_run_id,
                "artifact_uri": artifact_uri,
                "status": "active",
                "metadata_json": {
                    **dict(rendered["metadata"]),
                    "artifact_file_path": str(html_path.resolve()),
                    "bundle_ids": list(rendered["metadata"].get("bundle_ids") or []),
                    "quality_gate": {
                        "ready_for_delivery": evaluation["ready_for_delivery"],
                        "score": evaluation["score"],
                        "blocker_count": evaluation["summary"]["blocker_count"],
                        "warning_count": evaluation["summary"]["warning_count"],
                        "late_contract_mode": evaluation["summary"].get("late_contract_mode"),
                    },
                    "slot_evaluation": {
                        "strongest_slot": report_eval["summary"].get("strongest_slot"),
                        "weakest_slot": report_eval["summary"].get("weakest_slot"),
                        "slot_scores": report_eval["summary"].get("slot_scores"),
                        "progression": report_eval["summary"].get("progression"),
                    },
                    "chart_pack": chart_manifest,
                },
            }
        )

        persisted_links: list[dict[str, Any]] = []
        for link in rendered["report_links"]:
            locator = dict(link.get("artifact_locator_json") or {})
            locator.update(
                {
                    "report_artifact_id": artifact_record["artifact_id"],
                    "artifact_file_path": str(html_path.resolve()),
                }
            )
            persisted_links.extend(
                self.store.attach_report_links(
                    str(link["bundle_id"]),
                    [
                        {
                            **link,
                            "report_run_id": effective_report_run_id,
                            "artifact_uri": artifact_uri,
                            "artifact_locator_json": locator,
                        }
                    ],
                )
            )

        qa_path = output_path / f"a_share_main_report_{business_date}_{stamp}.qa.json"
        qa_path.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        eval_path = output_path / f"a_share_main_report_{business_date}_{stamp}.eval.json"
        eval_path.write_text(json.dumps(report_eval, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        manifest_path = output_path / f"a_share_main_report_{business_date}_{stamp}.manifest.json"
        manifest = {
            "artifact": artifact_record,
            "assembled": assembled,
            "rendered": {
                "artifact_type": rendered["artifact_type"],
                "artifact_version": rendered["artifact_version"],
                "render_format": rendered["render_format"],
                "content_type": rendered["content_type"],
                "title": rendered["title"],
                "metadata": rendered["metadata"],
            },
            "qa": evaluation,
            "evaluation": report_eval,
            "report_links": rendered["report_links"],
            "persisted_report_links": persisted_links,
            "chart_pack": chart_manifest,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        return {
            "artifact": artifact_record,
            "assembled": assembled,
            "html_path": str(html_path.resolve()),
            "qa_path": str(qa_path.resolve()),
            "eval_path": str(eval_path.resolve()),
            "manifest_path": str(manifest_path.resolve()),
            "rendered": rendered,
            "evaluation": evaluation,
            "report_evaluation": report_eval,
            "persisted_report_links": persisted_links,
            "chart_pack": chart_manifest,
        }

    def publish_delivery_package(
        self,
        *,
        business_date: str,
        output_dir: str | Path,
        include_empty: bool = False,
        report_run_id: str | None = None,
        generated_at: datetime | None = None,
        output_profile: str = "internal",
        requested_customer_slot: str | None = None,
    ) -> dict[str, Any]:
        published = self.publish_main_report_html(
            business_date=business_date,
            output_dir=output_dir,
            include_empty=include_empty,
            report_run_id=report_run_id,
            generated_at=generated_at,
            output_profile=output_profile,
            requested_customer_slot=requested_customer_slot,
        )
        generated_at = generated_at or datetime.now(timezone.utc)
        html_path = Path(published["html_path"])
        qa_path = Path(published["qa_path"])
        eval_path = Path(published["eval_path"])
        manifest_path = Path(published["manifest_path"])
        evaluation = dict(published["evaluation"])
        report_eval = dict(published["report_evaluation"])
        artifact = dict(published["artifact"])
        rendered = dict(published["rendered"])
        assembled = dict(published.get("assembled") or {})
        support_summary_aggregate = self._build_support_summary_aggregate(
            rendered=rendered,
            evaluation=evaluation,
            report_eval=report_eval,
        )
        focus_module = dict((rendered.get("metadata") or {}).get("focus_module") or MainReportHTMLRenderer()._build_focus_module(assembled=assembled, sections=list(assembled.get("sections") or [])))
        judgment_review_surface = self._build_judgment_review_surface(assembled=assembled)
        judgment_mapping_ledger = self._build_judgment_mapping_ledger(
            assembled=assembled,
            rendered=rendered,
            judgment_review_surface=judgment_review_surface,
        )

        package_slug = self._delivery_package_slug(
            business_date=business_date,
            generated_at=generated_at,
            artifact_id=str(artifact["artifact_id"]),
        )
        root_output_dir = enforce_artifact_publish_root_contract(
            flow_name=f"{self.__class__.__name__}.publish_delivery_package",
            artifact_root=self.artifact_root,
            output_path=output_dir,
        )
        package_dir = root_output_dir / package_slug
        package_dir.mkdir(parents=True, exist_ok=True)

        package_html_path = package_dir / html_path.name
        package_qa_path = package_dir / qa_path.name
        package_eval_path = package_dir / eval_path.name
        package_manifest_path = package_dir / manifest_path.name
        chart_pack = dict(published.get("chart_pack") or {})
        chart_source_dir = html_path.parent / "charts"
        package_chart_dir = package_dir / "charts"
        shutil.copy2(html_path, package_html_path)
        shutil.copy2(qa_path, package_qa_path)
        shutil.copy2(eval_path, package_eval_path)
        shutil.copy2(manifest_path, package_manifest_path)
        if chart_source_dir.exists():
            shutil.copytree(chart_source_dir, package_chart_dir, dirs_exist_ok=True)

        caption_text = self._build_delivery_caption(
            business_date=business_date,
            artifact=artifact,
            evaluation=evaluation,
            rendered=rendered,
            support_summary_aggregate=support_summary_aggregate,
        )
        caption_path = package_dir / "telegram_caption.txt"
        caption_path.write_text(caption_text, encoding="utf-8")
        judgment_review_surface_path = package_dir / "judgment_review_surface.json"
        judgment_review_surface_path.write_text(json.dumps(judgment_review_surface, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        judgment_mapping_ledger_path = package_dir / "judgment_mapping_ledger.json"
        judgment_mapping_ledger_path.write_text(json.dumps(judgment_mapping_ledger, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        delivery_manifest = {
            "artifact_type": "fsj_main_report_delivery_package",
            "artifact_version": self.DELIVERY_PACKAGE_VERSION,
            "business_date": business_date,
            "generated_at_utc": generated_at.isoformat(),
            "report_run_id": artifact.get("report_run_id"),
            "artifact_id": artifact.get("artifact_id"),
            "artifact_family": artifact.get("artifact_family"),
            "package_state": "ready" if evaluation.get("ready_for_delivery") else "blocked",
            "ready_for_delivery": bool(evaluation.get("ready_for_delivery")),
            "quality_gate": {
                "score": evaluation.get("score"),
                "blocker_count": (evaluation.get("summary") or {}).get("blocker_count"),
                "warning_count": (evaluation.get("summary") or {}).get("warning_count"),
                "qa_axes": (evaluation.get("summary") or {}).get("qa_axes") or {},
                "late_contract_mode": (evaluation.get("summary") or {}).get("late_contract_mode"),
                "source_health": (evaluation.get("summary") or {}).get("source_health") or {},
            },
            "lineage": {
                "bundle_ids": list((rendered.get("metadata") or {}).get("bundle_ids") or []),
                "producer_versions": list((rendered.get("metadata") or {}).get("producer_versions") or []),
                "support_summary_bundle_ids": list((rendered.get("metadata") or {}).get("support_summary_bundle_ids") or []),
                "report_link_count": (evaluation.get("summary") or {}).get("report_link_count"),
                "persisted_report_link_count": len(published.get("persisted_report_links") or []),
            },
            "slot_evaluation": {
                "strongest_slot": (report_eval.get("summary") or {}).get("strongest_slot"),
                "weakest_slot": (report_eval.get("summary") or {}).get("weakest_slot"),
                "slot_scores": (report_eval.get("summary") or {}).get("slot_scores"),
                "progression": (report_eval.get("summary") or {}).get("progression"),
                "average_slot_score": (report_eval.get("summary") or {}).get("average_slot_score"),
                "slot_score_span": (report_eval.get("summary") or {}).get("slot_score_span"),
            },
            "support_summary_aggregate": support_summary_aggregate,
            "chart_pack": {
                "manifest_path": str((package_chart_dir / "chart_manifest.json").resolve()) if (package_chart_dir / "chart_manifest.json").exists() else chart_pack.get("manifest_path"),
                "relative_manifest_path": "charts/chart_manifest.json" if (package_chart_dir / "chart_manifest.json").exists() else chart_pack.get("relative_manifest_path"),
                "chart_count": chart_pack.get("chart_count"),
                "ready_chart_count": chart_pack.get("ready_chart_count"),
                "degrade_status": chart_pack.get("degrade_status"),
                "degrade_reason": chart_pack.get("degrade_reason"),
                "chart_classes": chart_pack.get("chart_classes"),
                "assets": chart_pack.get("assets"),
                "html_embed_blocks": chart_pack.get("html_embed_blocks"),
            },
            "focus_module": {
                "why_included": focus_module.get("why_included"),
                "focus_symbol_count": focus_module.get("focus_symbol_count"),
                "key_focus_symbol_count": focus_module.get("key_focus_symbol_count"),
                "list_types": list(focus_module.get("list_types") or []),
                "chart_refs": list(focus_module.get("chart_refs") or []),
            },
            "judgment_review_surface": {
                "path": str(judgment_review_surface_path.resolve()),
                "judgment_item_count": judgment_review_surface.get("judgment_item_count"),
                "review_slot_count": judgment_review_surface.get("review_slot_count"),
                "review_status": judgment_review_surface.get("review_status"),
            },
            "judgment_mapping_ledger": {
                "path": str(judgment_mapping_ledger_path.resolve()),
                "mapping_count": judgment_mapping_ledger.get("mapping_count"),
                "retrospective_link_count": judgment_mapping_ledger.get("retrospective_link_count"),
                "learning_asset_candidate_count": judgment_mapping_ledger.get("learning_asset_candidate_count"),
            },
            "artifacts": {
                "html": package_html_path.name,
                "qa": package_qa_path.name,
                "evaluation": package_eval_path.name,
                "manifest": package_manifest_path.name,
                "telegram_caption": caption_path.name,
                "charts_dir": "charts" if package_chart_dir.exists() else None,
                "chart_manifest": "charts/chart_manifest.json" if (package_chart_dir / "chart_manifest.json").exists() else None,
                "judgment_review_surface": judgment_review_surface_path.name,
                "judgment_mapping_ledger": judgment_mapping_ledger_path.name,
            },
        }
        preview_payload = {
            **published,
            "delivery_package_dir": str(package_dir.resolve()),
            "delivery_manifest_path": str((package_dir / 'delivery_manifest.json').resolve()),
            "telegram_caption_path": str(caption_path.resolve()),
            "delivery_zip_path": str((root_output_dir / f"{package_slug}.zip").resolve()),
            "delivery_manifest": delivery_manifest,
            "delivery_eval_path": str(package_eval_path.resolve()),
            "chart_pack_dir": str(package_chart_dir.resolve()) if package_chart_dir.exists() else None,
        }
        delivery_manifest["dispatch_advice"] = self.dispatch_helper.summarize_candidate(preview_payload)
        delivery_manifest_path = package_dir / "delivery_manifest.json"
        delivery_manifest_path.write_text(json.dumps(delivery_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        package_index = self._build_delivery_package_index(
            package_dir=package_dir,
            artifact=artifact,
            delivery_manifest=delivery_manifest,
            package_artifacts={
                "html": package_html_path,
                "qa": package_qa_path,
                "evaluation": package_eval_path,
                "manifest": package_manifest_path,
                "telegram_caption": caption_path,
                "charts_dir": package_chart_dir,
                "judgment_review_surface": judgment_review_surface_path,
                "judgment_mapping_ledger": judgment_mapping_ledger_path,
                "delivery_manifest": delivery_manifest_path,
            },
        )
        package_index_path = package_dir / "package_index.json"
        package_index_path.write_text(json.dumps(package_index, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        browse_readme_path = package_dir / "BROWSE_PACKAGE.md"
        browse_readme_path.write_text(self._build_delivery_package_browse_readme(package_index), encoding="utf-8")

        delivery_manifest["artifacts"]["delivery_manifest"] = delivery_manifest_path.name
        delivery_manifest["artifacts"]["package_index"] = package_index_path.name
        delivery_manifest["artifacts"]["browse_readme"] = browse_readme_path.name
        delivery_manifest_path.write_text(json.dumps(delivery_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        zip_path = root_output_dir / f"{package_slug}.zip"
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
            for path in sorted(package_dir.iterdir()):
                zf.write(path, arcname=f"{package_dir.name}/{path.name}")

        published_artifact = self.store.register_report_artifact(
            {
                "artifact_id": artifact["artifact_id"],
                "artifact_family": artifact["artifact_family"],
                "market": artifact["market"],
                "business_date": artifact["business_date"],
                "agent_domain": artifact["agent_domain"],
                "render_format": artifact["render_format"],
                "artifact_type": artifact["artifact_type"],
                "content_type": artifact["content_type"],
                "title": artifact["title"],
                "report_run_id": artifact.get("report_run_id"),
                "artifact_uri": artifact.get("artifact_uri"),
                "status": artifact["status"],
                "supersedes_artifact_id": artifact.get("supersedes_artifact_id"),
                "metadata_json": {
                    **dict(artifact.get("metadata_json") or {}),
                    "delivery_package": {
                        "delivery_package_dir": str(package_dir.resolve()),
                        "delivery_manifest_path": str(delivery_manifest_path.resolve()),
                        "delivery_zip_path": str(zip_path.resolve()),
                        "telegram_caption_path": str(caption_path.resolve()),
                        "package_index_path": str(package_index_path.resolve()),
                        "package_browse_readme_path": str(browse_readme_path.resolve()),
                        "delivery_eval_path": str(package_eval_path.resolve()),
                        "generated_at_utc": generated_at.isoformat(),
                        "package_state": delivery_manifest.get("package_state"),
                        "ready_for_delivery": delivery_manifest.get("ready_for_delivery"),
                        "quality_gate": dict(delivery_manifest.get("quality_gate") or {}),
                        "slot_evaluation": dict(delivery_manifest.get("slot_evaluation") or {}),
                        "support_summary_aggregate": dict(delivery_manifest.get("support_summary_aggregate") or {}),
                        "chart_pack": dict(delivery_manifest.get("chart_pack") or {}),
                        "focus_module": dict(delivery_manifest.get("focus_module") or {}),
                        "judgment_review_surface": dict(delivery_manifest.get("judgment_review_surface") or {}),
                        "judgment_mapping_ledger": dict(delivery_manifest.get("judgment_mapping_ledger") or {}),
                        "dispatch_advice": dict(delivery_manifest.get("dispatch_advice") or {}),
                        "artifacts": dict(delivery_manifest.get("artifacts") or {}),
                        "workflow": {
                            "recommended_action": dict(delivery_manifest.get("dispatch_advice") or {}).get("recommended_action"),
                            "selection_reason": dict(delivery_manifest.get("dispatch_advice") or {}).get("selection_reason"),
                        },
                    },
                },
            }
        )

        return {
            **published,
            "artifact": published_artifact,
            "delivery_package_dir": str(package_dir.resolve()),
            "delivery_manifest_path": str(delivery_manifest_path.resolve()),
            "telegram_caption_path": str(caption_path.resolve()),
            "delivery_zip_path": str(zip_path.resolve()),
            "delivery_manifest": delivery_manifest,
            "delivery_eval_path": str(package_eval_path.resolve()),
            "dispatch_advice": delivery_manifest.get("dispatch_advice"),
            "package_index_path": str(package_index_path.resolve()),
            "package_browse_readme_path": str(browse_readme_path.resolve()),
            "package_index": package_index,
        }

    def _delivery_package_slug(self, *, business_date: str, generated_at: datetime, artifact_id: str) -> str:
        stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
        safe_artifact_id = re.sub(r"[^A-Za-z0-9._-]+", "-", artifact_id).strip("-")
        return f"a_share_main_report_delivery_{business_date}_{stamp}_{safe_artifact_id[-24:]}"

    def _build_delivery_caption(
        self,
        *,
        business_date: str,
        artifact: dict[str, Any],
        evaluation: dict[str, Any],
        rendered: dict[str, Any],
        support_summary_aggregate: dict[str, Any],
    ) -> str:
        summary = dict(evaluation.get("summary") or {})
        quality_state = "READY" if evaluation.get("ready_for_delivery") else "BLOCKED"
        lines = [
            f"A股主报告交付包｜{business_date}",
            f"状态：{quality_state}｜score={evaluation.get('score', '-')}",
            f"artifact_id：{artifact.get('artifact_id')}",
            f"report_run_id：{artifact.get('report_run_id') or '-'}",
            f"late_contract_mode：{summary.get('late_contract_mode') or '-'}",
            f"blockers={summary.get('blocker_count', 0)}｜warnings={summary.get('warning_count', 0)}",
            f"sections={summary.get('ready_section_count', 0)}/{summary.get('section_count', 0)} ready",
            f"support_summaries={summary.get('support_summary_count', 0)}｜report_links={summary.get('report_link_count', 0)}",
            f"support_domains={','.join(support_summary_aggregate.get('domains') or []) or '-'}｜support_slots={','.join(support_summary_aggregate.get('slots') or []) or '-'}",
            f"renderer={((rendered.get('metadata') or {}).get('renderer_version') or '-')}",
        ]
        return "\n".join(lines) + "\n"

    def _build_support_summary_aggregate(
        self,
        *,
        rendered: dict[str, Any],
        evaluation: dict[str, Any],
        report_eval: dict[str, Any],
    ) -> dict[str, Any]:
        metadata = dict(rendered.get("metadata") or {})
        existing_report_links = list(metadata.get("existing_report_links") or [])
        support_links = [link for link in existing_report_links if link.get("bundle_id") in set(metadata.get("support_summary_bundle_ids") or [])]
        domains = sorted({str(domain) for domain in (metadata.get("support_summary_domains") or []) if domain})
        slots = sorted({str(link.get("slot") or "") for link in support_links if link.get("slot")})
        return {
            "support_summary_count": int((evaluation.get("summary") or {}).get("support_summary_count") or 0),
            "bundle_ids": list(metadata.get("support_summary_bundle_ids") or []),
            "domains": domains,
            "slots": slots,
            "report_link_count": len(support_links),
            "section_count": len(list(metadata.get("bundle_ids") or [])),
            "ready_section_count": int((evaluation.get("summary") or {}).get("ready_section_count") or 0),
            "strongest_slot": (report_eval.get("summary") or {}).get("strongest_slot"),
        }

    def _build_judgment_review_surface(self, *, assembled: dict[str, Any]) -> dict[str, Any]:
        sections = list(assembled.get("sections") or [])
        items: list[dict[str, Any]] = []
        for section in sections:
            slot = str(section.get("slot") or "")
            section_key = str(section.get("section_key") or "")
            lineage = dict(section.get("lineage") or {})
            degrade_payload = dict((lineage.get("bundle") or {}).get("payload_json") or {}).get("degrade") or {}
            evidence_links = list(lineage.get("evidence_links") or [])
            support_bundle_ids = list(lineage.get("support_bundle_ids") or [])
            section_title = str(section.get("title") or section_key or slot)
            for index, judgment in enumerate(section.get("judgments") or [], start=1):
                attributes = dict(judgment.get("attributes_json") or {})
                item_key = str(judgment.get("object_key") or f"{slot}:{section_key}:judgment:{index}")
                items.append(
                    {
                        "judgment_key": item_key,
                        "slot": slot,
                        "section_key": section_key,
                        "section_title": section_title,
                        "statement": str(judgment.get("statement") or ""),
                        "judgment_action": judgment.get("judgment_action"),
                        "confidence": judgment.get("confidence"),
                        "evidence_level": judgment.get("evidence_level"),
                        "contract_mode": attributes.get("contract_mode") or degrade_payload.get("contract_mode"),
                        "completeness_label": attributes.get("completeness_label") or degrade_payload.get("completeness_label"),
                        "degrade_reason": attributes.get("degrade_reason") or degrade_payload.get("degrade_reason"),
                        "support_bundle_ids": support_bundle_ids,
                        "evidence_refs": [
                            {
                                "ref_key": link.get("ref_key"),
                                "ref_system": link.get("ref_system"),
                                "evidence_role": link.get("evidence_role"),
                            }
                            for link in evidence_links
                        ],
                        "focus_module_refs": MainReportHTMLRenderer()._build_focus_module(assembled=assembled, sections=[section]),
                        "review": {
                            "status": "pending",
                            "allowed_actions": ["approve", "needs_edit", "reject", "monitor"],
                            "operator_comment": None,
                            "review_focus": [
                                "evidence_chain_complete",
                                "slot_wording_within_boundary",
                                "support_merge_is_truthful",
                                "focus_scope_alignment",
                            ],
                        },
                    }
                )
        return {
            "artifact_type": "fsj_main_report_judgment_review_surface",
            "artifact_version": self.DELIVERY_PACKAGE_VERSION,
            "business_date": assembled.get("business_date"),
            "judgment_item_count": len(items),
            "review_slot_count": len({item["slot"] for item in items if item.get("slot")}),
            "review_status": "pending_operator_item_review" if items else "no_judgments_found",
            "items": items,
        }

    def _build_judgment_mapping_ledger(
        self,
        *,
        assembled: dict[str, Any],
        rendered: dict[str, Any],
        judgment_review_surface: dict[str, Any],
    ) -> dict[str, Any]:
        sections = list(assembled.get("sections") or [])
        customer_sections = {
            str(item.get("slot") or ""): item
            for item in ((rendered.get("metadata") or {}).get("customer_presentation") or {}).get("sections", [])
        }
        section_positions = {str(section.get("slot") or ""): idx for idx, section in enumerate(sections)}
        mapping_rows: list[dict[str, Any]] = []
        retrospective_links: list[dict[str, Any]] = []
        learning_assets: list[dict[str, Any]] = []
        prior_rows: list[dict[str, Any]] = []
        review_items = {str(item.get("judgment_key") or ""): item for item in (judgment_review_surface.get("items") or [])}

        for section in sections:
            slot = str(section.get("slot") or "")
            customer = dict(customer_sections.get(slot) or {})
            support_items = list(section.get("support_summaries") or [])
            if slot == "late" and prior_rows and not list(section.get("judgments") or []):
                retrospective_links.extend(
                    {
                        "late_judgment_key": None,
                        "late_slot": slot,
                        "linked_prior_judgment_key": prior.get("judgment_key"),
                        "linked_prior_slot": prior.get("slot"),
                        "link_type": "late_retrospective_slot_anchor",
                    }
                    for prior in prior_rows
                )
            support_bundle_ids = [str(item.get("bundle_id") or "") for item in support_items if item.get("bundle_id")]
            support_statements = [str(item.get("summary") or "") for item in support_items if item.get("summary")]
            highlights = list(customer.get("highlights") or [])
            section_position = int(section_positions.get(slot, 0))
            for judgment in section.get("judgments") or []:
                judgment_key = str(judgment.get("object_key") or "")
                signal_statements = [str(item.get("statement") or "") for item in (section.get("signals") or []) if item.get("statement")][:3]
                fact_statements = [str(item.get("statement") or "") for item in (section.get("facts") or []) if item.get("statement")][:3]
                customer_wording = highlights[0] if highlights else str(customer.get("summary") or judgment.get("statement") or section.get("summary") or "")
                section_focus = MainReportHTMLRenderer()._build_focus_module(assembled=assembled, sections=[section])
                row = {
                    "judgment_key": judgment_key,
                    "slot": slot,
                    "section_key": section.get("section_key"),
                    "section_position": section_position,
                    "main_judgment_statement": str(judgment.get("statement") or ""),
                    "support_bundle_ids": support_bundle_ids,
                    "support_statements": support_statements,
                    "signal_statements": signal_statements,
                    "fact_statements": fact_statements,
                    "focus_symbols": list(section_focus.get("focus_symbols") or []),
                    "focus_why_included": section_focus.get("why_included"),
                    "chart_refs": list(section_focus.get("chart_refs") or []),
                    "customer_wording": customer_wording,
                    "customer_slot_title": customer.get("title"),
                    "review_surface_ref": review_items.get(judgment_key, {}).get("judgment_key"),
                    "retrospective_anchor": f"{assembled.get('business_date')}:{slot}:{judgment_key}",
                }
                mapping_rows.append(row)
                if slot == "late":
                    for prior in prior_rows:
                        retrospective_links.append(
                            {
                                "late_judgment_key": judgment_key,
                                "late_slot": slot,
                                "linked_prior_judgment_key": prior.get("judgment_key"),
                                "linked_prior_slot": prior.get("slot"),
                                "link_type": "late_retrospective_to_prior_judgment_surface",
                            }
                        )
                learning_assets.append(
                    {
                        "judgment_key": judgment_key,
                        "slot": slot,
                        "customer_wording": customer_wording,
                        "main_judgment_statement": row["main_judgment_statement"],
                        "support_bundle_ids": support_bundle_ids,
                        "outcome_label": None,
                        "learning_status": "ready_for_outcome_tagging" if slot == "late" else "await_late_retrospective",
                    }
                )
                prior_rows.append(row)

        slot_links: list[dict[str, Any]] = []
        ordered_slots = [str(section.get("slot") or "") for section in sections if section.get("slot")]
        for prev, curr in zip(ordered_slots, ordered_slots[1:]):
            slot_links.append(
                {
                    "from_slot": prev,
                    "to_slot": curr,
                    "link_type": "judgment_surface_progression",
                }
            )

        return {
            "artifact_type": "fsj_main_report_judgment_mapping_ledger",
            "artifact_version": self.DELIVERY_PACKAGE_VERSION,
            "business_date": assembled.get("business_date"),
            "mapping_count": len(mapping_rows),
            "retrospective_link_count": len(retrospective_links),
            "learning_asset_candidate_count": len(learning_assets),
            "slot_progression_links": slot_links,
            "mappings": mapping_rows,
            "retrospective_links": retrospective_links,
            "learning_asset_candidates": learning_assets,
        }

    def _build_delivery_package_index(
        self,
        *,
        package_dir: Path,
        artifact: dict[str, Any],
        delivery_manifest: dict[str, Any],
        package_artifacts: dict[str, Path],
    ) -> dict[str, Any]:
        file_index: list[dict[str, Any]] = []
        for role, path in package_artifacts.items():
            file_index.append({
                "role": role,
                "filename": path.name,
                "path": str(path.resolve()),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
            })
        return {
            "artifact_type": "fsj_main_report_delivery_package_index",
            "artifact_version": self.DELIVERY_PACKAGE_VERSION,
            "artifact_id": artifact.get("artifact_id"),
            "business_date": delivery_manifest.get("business_date"),
            "report_run_id": delivery_manifest.get("report_run_id"),
            "delivery_package_dir": str(package_dir.resolve()),
            "package_state": delivery_manifest.get("package_state"),
            "ready_for_delivery": delivery_manifest.get("ready_for_delivery"),
            "quality_gate": dict(delivery_manifest.get("quality_gate") or {}),
            "slot_evaluation": dict(delivery_manifest.get("slot_evaluation") or {}),
            "support_summary_aggregate": dict(delivery_manifest.get("support_summary_aggregate") or {}),
            "chart_pack": dict(delivery_manifest.get("chart_pack") or {}),
            "focus_module": dict(delivery_manifest.get("focus_module") or {}),
            "judgment_review_surface": dict(delivery_manifest.get("judgment_review_surface") or {}),
            "judgment_mapping_ledger": dict(delivery_manifest.get("judgment_mapping_ledger") or {}),
            "browse_priority": ["html", "telegram_caption", "charts_dir", "delivery_manifest", "judgment_review_surface", "judgment_mapping_ledger", "evaluation", "qa", "manifest"],
            "files": file_index,
        }

    def _build_delivery_package_browse_readme(self, package_index: dict[str, Any]) -> str:
        support_summary = dict(package_index.get("support_summary_aggregate") or {})
        lines = [
            f"# MAIN Delivery Package Browse｜{package_index.get('business_date')}",
            "",
            "## Snapshot",
            f"- artifact_id: `{package_index.get('artifact_id') or '-'}`",
            f"- package_state: `{package_index.get('package_state') or '-'}`",
            f"- ready_for_delivery: `{package_index.get('ready_for_delivery')}`",
            f"- strongest_slot: `{(package_index.get('slot_evaluation') or {}).get('strongest_slot') or '-'}`",
            f"- support_domains: `{', '.join(support_summary.get('domains') or []) or '-'}`",
            f"- support_bundle_count: `{len(support_summary.get('bundle_ids') or [])}`",
            f"- focus_symbol_count: `{(package_index.get('focus_module') or {}).get('focus_symbol_count')}`",
            f"- judgment_item_count: `{(package_index.get('judgment_review_surface') or {}).get('judgment_item_count')}`",
            f"- judgment_mapping_count: `{(package_index.get('judgment_mapping_ledger') or {}).get('mapping_count')}`",
            "",
            "## Files",
        ]
        for item in package_index.get("files") or []:
            lines.append(
                f"- {item.get('role')}: `{item.get('filename')}` exists=`{item.get('exists')}` size_bytes=`{item.get('size_bytes')}`"
            )
        lines.append("")
        return "\n".join(lines) + "\n"


class SupportReportHTMLRenderer:
    def render(
        self,
        assembled: dict[str, Any],
        *,
        report_run_id: str | None = None,
        artifact_uri: str | None = None,
        generated_at: datetime | None = None,
        output_profile: str = "internal",
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        profile = str(output_profile or "internal").strip().lower()
        if profile not in VALID_OUTPUT_PROFILES:
            raise ValueError(f"unsupported output_profile={output_profile}")
        domain = str(assembled.get("agent_domain") or "support")
        slot = str(assembled.get("slot") or "")
        if profile == "customer":
            title = f"A股{SUPPORT_DOMAIN_LABELS.get(domain, domain)}简报｜{SUPPORT_SLOT_LABELS.get(slot, slot)}｜{assembled.get('business_date') or '-'}"
            html = self._render_customer_html(title=title, assembled=assembled, generated_at=generated_at)
        else:
            profile_label = "审阅包" if profile == "review" else "support 报告"
            spacer = "" if profile == "review" else " "
            title = f"A股{SUPPORT_DOMAIN_LABELS.get(domain, domain)}{spacer}{profile_label}｜{SUPPORT_SLOT_LABELS.get(slot, slot)}｜{assembled.get('business_date') or '-'}"
            html = self._render_html(title=title, assembled=assembled, generated_at=generated_at)
        bundle = dict(assembled.get("bundle") or {})
        report_links = []
        if bundle.get("bundle_id"):
            report_links.append(
                {
                    "bundle_id": bundle.get("bundle_id"),
                    "report_run_id": report_run_id,
                    "artifact_type": "html",
                    "artifact_uri": artifact_uri,
                    "artifact_locator_json": {"renderer": "ifa_data_platform.fsj.report_rendering.SupportReportHTMLRenderer", "artifact_uri": artifact_uri},
                    "section_render_key": assembled.get("section_render_key"),
                }
            )
        metadata = {
            "market": assembled.get("market"),
            "business_date": assembled.get("business_date"),
            "agent_domain": domain,
            "slot": slot,
            "section_key": assembled.get("section_key"),
            "section_render_key": assembled.get("section_render_key"),
            "source_artifact_type": assembled.get("artifact_type"),
            "source_artifact_version": assembled.get("artifact_version"),
            "renderer": "ifa_data_platform.fsj.report_rendering.SupportReportHTMLRenderer",
            "renderer_version": "v1",
            "generated_at": generated_at.isoformat(),
            "output_profile": profile,
            "presentation_schema_version": CUSTOMER_PRESENTATION_SCHEMA_VERSION if profile == "customer" else None,
            "bundle_id": bundle.get("bundle_id"),
            "producer_version": bundle.get("producer_version"),
            "artifact_uri": artifact_uri,
            "existing_report_links": list(((assembled.get("lineage") or {}).get("report_links") or [])),
            "evidence_link_count": len(((assembled.get("lineage") or {}).get("evidence_links") or [])),
        }
        return RenderedFSJArtifact(
            artifact_type="fsj_support_report_html",
            artifact_version="v1",
            render_format="html",
            content_type="text/html",
            title=title,
            content=html,
            metadata=metadata,
            report_links=report_links,
        ).as_dict()

    def _render_html(self, *, title: str, assembled: dict[str, Any], generated_at: datetime) -> str:
        bundle = dict(assembled.get("bundle") or {})
        lineage = dict(assembled.get("lineage") or {})
        evidence_keys = [str(item.get("ref_key")) for item in (lineage.get("evidence_links") or []) if item.get("ref_key")]
        report_uris = [str(item.get("artifact_uri")) for item in (lineage.get("report_links") or []) if item.get("artifact_uri")]
        return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f4f6fb; color: #111827; }}
    .page {{ max-width: 960px; margin: 0 auto; padding: 28px 24px 48px; }}
    .hero {{ background: linear-gradient(135deg, #172554, #2563eb); color: white; border-radius: 20px; padding: 28px 32px; }}
    .card {{ background: white; border-radius: 18px; padding: 24px 26px; margin-top: 20px; box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08); }}
    .meta {{ opacity: 0.9; font-size: 14px; line-height: 1.6; }}
    .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #e0e7ff; color: #3730a3; font-size: 12px; margin-right: 8px; }}
    .bucket {{ margin-top: 16px; }}
    ul {{ margin: 8px 0 0 18px; padding: 0; }}
    li {{ margin: 6px 0; line-height: 1.55; }}
    .footnote {{ font-size: 12px; color: #64748b; margin-top: 18px; line-height: 1.6; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  </style>
</head>
<body>
  <div class=\"page\">
    <section class=\"hero\">
      <h1>{escape(title)}</h1>
      <div class=\"meta\">
        业务日期：{escape(str(assembled.get('business_date') or '-'))} · 域：{escape(SUPPORT_DOMAIN_LABELS.get(str(assembled.get('agent_domain') or ''), str(assembled.get('agent_domain') or '-')))} · 时段：{escape(SUPPORT_SLOT_LABELS.get(str(assembled.get('slot') or ''), str(assembled.get('slot') or '-')))}<br/>
        bundle：<span class=\"mono\">{escape(str(bundle.get('bundle_id') or '-'))}</span> · producer_version：<span class=\"mono\">{escape(str(bundle.get('producer_version') or '-'))}</span> · 生成时间：{escape(generated_at.isoformat())}
      </div>
    </section>

    <section class=\"card\">
      <span class=\"pill\">{escape(str(assembled.get('status') or 'unknown'))}</span>
      <strong>support 摘要：</strong>{escape(str(assembled.get('summary') or '暂无摘要'))}
      <div class=\"footnote\">本报告保持 support 独立成文，供审计 / 复核 / 回放使用；MAIN 仅消费 concise support summary，不内联 support 正文。</div>
    </section>

    <section class=\"card\">
      <h2>Support 判断</h2>
      {self._render_items(assembled.get('judgments') or [], fallback='暂无 support 判断')}
      <div class=\"bucket\"><strong>Support 信号</strong>{self._render_items(assembled.get('signals') or [], fallback='暂无 support 信号')}</div>
      <div class=\"bucket\"><strong>事实锚点</strong>{self._render_items(assembled.get('facts') or [], fallback='暂无事实锚点')}</div>
      <div class=\"footnote\">lineage：slot_run_id=<span class=\"mono\">{escape(str(bundle.get('slot_run_id') or '-'))}</span> · replay_id=<span class=\"mono\">{escape(str(bundle.get('replay_id') or '-'))}</span> · evidence={escape(', '.join(evidence_keys[:4]) if evidence_keys else '-')} · prior_report_links={escape(', '.join(report_uris[:2]) if report_uris else '-')}</div>
    </section>
  </div>
</body>
</html>
"""

    def _render_customer_html(self, *, title: str, assembled: dict[str, Any], generated_at: datetime) -> str:
        domain = SUPPORT_DOMAIN_LABELS.get(str(assembled.get("agent_domain") or ""), str(assembled.get("agent_domain") or "-"))
        slot = SUPPORT_SLOT_LABELS.get(str(assembled.get("slot") or ""), str(assembled.get("slot") or "-"))
        highlights = [str(item.get("statement") or "").strip() for item in (assembled.get("judgments") or []) if str(item.get("statement") or "").strip()][:3]
        signals = [str(item.get("statement") or "").strip() for item in (assembled.get("signals") or []) if str(item.get("statement") or "").strip()][:3]
        facts = [str(item.get("statement") or "").strip() for item in (assembled.get("facts") or []) if str(item.get("statement") or "").strip()][:3]
        return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f7f8fc; color: #0f172a; }}
    .page {{ max-width: 900px; margin: 0 auto; padding: 28px 20px 44px; }}
    .hero {{ background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff; border-radius: 20px; padding: 26px 28px; }}
    .card {{ background: #fff; border-radius: 18px; padding: 22px; margin-top: 18px; box-shadow: 0 10px 26px rgba(15, 23, 42, 0.07); }}
    h1, h2 {{ margin-top: 0; }}
    ul {{ margin: 8px 0 0 18px; padding: 0; }}
    li {{ margin: 6px 0; line-height: 1.6; }}
    .meta, .footnote {{ font-size: 13px; line-height: 1.6; color: #475569; }}
  </style>
</head>
<body>
  <div class=\"page\">
    <section class=\"hero\"><h1>{escape(title)}</h1><div class=\"meta\">业务日期：{escape(str(assembled.get('business_date') or '-'))} · 领域：{escape(domain)} · 时段：{escape(slot)}<br/>客户展示层仅保留摘要、关键信号与已知事实。</div></section>
    <section class=\"card\"><h2>一句话摘要</h2><div>{escape(str(assembled.get('summary') or '暂无摘要'))}</div><div class=\"footnote\">生成时间：{escape(generated_at.isoformat())} · schema：{escape(CUSTOMER_PRESENTATION_SCHEMA_VERSION)}</div></section>
    <section class=\"card\"><h2>重点结论</h2><ul>{''.join(f'<li>{escape(item)}</li>' for item in (highlights or ['暂无重点结论']))}</ul></section>
    <section class=\"card\"><h2>跟踪信号</h2><ul>{''.join(f'<li>{escape(item)}</li>' for item in (signals or ['暂无跟踪信号']))}</ul></section>
    <section class=\"card\"><h2>已知事实</h2><ul>{''.join(f'<li>{escape(item)}</li>' for item in (facts or ['暂无已知事实']))}</ul></section>
  </div>
</body>
</html>
"""

    def _render_items(self, items: Sequence[dict[str, Any]], *, fallback: str) -> str:
        if not items:
            return f"<ul><li>{escape(fallback)}</li></ul>"
        rendered: list[str] = []
        for item in items:
            statement = escape(str(item.get("statement") or "-"))
            attrs: list[str] = []
            if item.get("judgment_action"):
                attrs.append(f"action={item['judgment_action']}")
            if item.get("signal_strength"):
                attrs.append(f"strength={item['signal_strength']}")
            if item.get("confidence"):
                attrs.append(f"confidence={item['confidence']}")
            if item.get("evidence_level"):
                attrs.append(f"evidence={item['evidence_level']}")
            suffix = f" <span class=\"mono\">[{escape(', '.join(attrs))}]</span>" if attrs else ""
            rendered.append(f"<li>{statement}{suffix}</li>")
        return f"<ul>{''.join(rendered)}</ul>"


class SupportReportRenderingService:
    def __init__(
        self,
        assembly_service: SupportReportAssemblyService,
        renderer: SupportReportHTMLRenderer | None = None,
    ) -> None:
        self.assembly_service = assembly_service
        self.renderer = renderer or SupportReportHTMLRenderer()

    def render_support_report_html(
        self,
        *,
        business_date: str,
        agent_domain: str,
        slot: str,
        report_run_id: str | None = None,
        artifact_uri: str | None = None,
        output_profile: str = "internal",
    ) -> dict[str, Any]:
        assembled = self.assembly_service.assemble_support_section(
            business_date=business_date,
            agent_domain=agent_domain,
            slot=slot,
        )
        return self.renderer.render(
            assembled,
            report_run_id=report_run_id,
            artifact_uri=artifact_uri,
            output_profile=output_profile,
        )


class SupportReportArtifactPublishingService:
    ARTIFACT_FAMILY = "support_domain_report"
    DELIVERY_PACKAGE_VERSION = "v1"

    def __init__(
        self,
        rendering_service: SupportReportRenderingService,
        store: FSJStore,
        qa_evaluator: SupportReportQAEvaluator | None = None,
        artifact_root: str | Path | None = None,
    ) -> None:
        self.rendering_service = rendering_service
        self.store = store
        self.qa_evaluator = qa_evaluator or SupportReportQAEvaluator()
        self.artifact_root = require_explicit_non_live_artifact_root(
            flow_name=f"{self.__class__.__name__}.__init__",
            artifact_root=artifact_root,
        )

    def publish_support_report_html(
        self,
        *,
        business_date: str,
        agent_domain: str,
        slot: str,
        output_dir: str | Path,
        report_run_id: str | None = None,
        generated_at: datetime | None = None,
        output_profile: str = "internal",
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        output_path = enforce_artifact_publish_root_contract(
            flow_name=f"{self.__class__.__name__}.publish_support_report_html",
            artifact_root=self.artifact_root,
            output_path=output_dir,
        )
        output_path.mkdir(parents=True, exist_ok=True)
        stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
        artifact_id = f"fsj-support-report:{agent_domain}:{slot}:{business_date}:{stamp}:{uuid4().hex[:8]}"
        html_path = output_path / f"a_share_support_{agent_domain}_{slot}_{business_date}_{stamp}.html"
        artifact_uri = html_path.resolve().as_uri()
        effective_report_run_id = report_run_id or artifact_id

        rendered = self.rendering_service.render_support_report_html(
            business_date=business_date,
            agent_domain=agent_domain,
            slot=slot,
            report_run_id=effective_report_run_id,
            artifact_uri=artifact_uri,
            output_profile=output_profile,
        )
        html_path.write_text(rendered["content"], encoding="utf-8")

        artifact_record = self.store.register_report_artifact(
            {
                "artifact_id": artifact_id,
                "artifact_family": self.ARTIFACT_FAMILY,
                "market": str(rendered["metadata"].get("market") or "a_share"),
                "business_date": business_date,
                "agent_domain": agent_domain,
                "render_format": rendered["render_format"],
                "artifact_type": rendered["artifact_type"],
                "content_type": rendered["content_type"],
                "title": rendered["title"],
                "report_run_id": effective_report_run_id,
                "artifact_uri": artifact_uri,
                "status": "active",
                "metadata_json": {
                    **dict(rendered["metadata"]),
                    "artifact_file_path": str(html_path.resolve()),
                },
            }
        )

        persisted_links: list[dict[str, Any]] = []
        for link in rendered["report_links"]:
            locator = dict(link.get("artifact_locator_json") or {})
            locator.update(
                {
                    "report_artifact_id": artifact_record["artifact_id"],
                    "artifact_file_path": str(html_path.resolve()),
                }
            )
            persisted_links.extend(
                self.store.attach_report_links(
                    str(link["bundle_id"]),
                    [
                        {
                            **link,
                            "report_run_id": effective_report_run_id,
                            "artifact_uri": artifact_uri,
                            "artifact_locator_json": locator,
                        }
                    ],
                )
            )

        manifest_path = output_path / f"a_share_support_{agent_domain}_{slot}_{business_date}_{stamp}.manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "artifact": artifact_record,
                    "rendered": {
                        "artifact_type": rendered["artifact_type"],
                        "artifact_version": rendered["artifact_version"],
                        "render_format": rendered["render_format"],
                        "content_type": rendered["content_type"],
                        "title": rendered["title"],
                        "metadata": rendered["metadata"],
                    },
                    "report_links": rendered["report_links"],
                    "persisted_report_links": persisted_links,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        return {
            "artifact": artifact_record,
            "html_path": str(html_path.resolve()),
            "manifest_path": str(manifest_path.resolve()),
            "rendered": rendered,
            "persisted_report_links": persisted_links,
        }

    def publish_delivery_package(
        self,
        *,
        business_date: str,
        agent_domain: str,
        slot: str,
        output_dir: str | Path,
        report_run_id: str | None = None,
        generated_at: datetime | None = None,
        output_profile: str = "internal",
    ) -> dict[str, Any]:
        published = self.publish_support_report_html(
            business_date=business_date,
            agent_domain=agent_domain,
            slot=slot,
            output_dir=output_dir,
            report_run_id=report_run_id,
            generated_at=generated_at,
            output_profile=output_profile,
        )
        generated_at = generated_at or datetime.now(timezone.utc)
        html_path = Path(published["html_path"])
        manifest_path = Path(published["manifest_path"])
        rendered = dict(published["rendered"])
        artifact = dict(published["artifact"])
        assembled = self.rendering_service.assembly_service.assemble_support_section(
            business_date=business_date,
            agent_domain=agent_domain,
            slot=slot,
        )
        qa = self.qa_evaluator.evaluate(assembled, rendered)
        root_output_dir = enforce_artifact_publish_root_contract(
            flow_name=f"{self.__class__.__name__}.publish_delivery_package",
            artifact_root=self.artifact_root,
            output_path=output_dir,
        )
        qa_path = root_output_dir / f"a_share_support_{agent_domain}_{slot}_{business_date}_{generated_at.strftime('%Y%m%dT%H%M%SZ')}.qa.json"
        qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        package_slug = self._delivery_package_slug(
            business_date=business_date,
            agent_domain=agent_domain,
            slot=slot,
            generated_at=generated_at,
            artifact_id=str(artifact["artifact_id"]),
        )
        package_dir = root_output_dir / package_slug
        package_dir.mkdir(parents=True, exist_ok=True)

        package_html_path = package_dir / html_path.name
        package_qa_path = package_dir / qa_path.name
        package_manifest_path = package_dir / manifest_path.name
        shutil.copy2(html_path, package_html_path)
        shutil.copy2(qa_path, package_qa_path)
        shutil.copy2(manifest_path, package_manifest_path)

        operator_summary = self._build_operator_summary(
            business_date=business_date,
            agent_domain=agent_domain,
            slot=slot,
            artifact=artifact,
            qa=qa,
            rendered=rendered,
        )
        operator_summary_path = package_dir / "operator_summary.txt"
        operator_summary_path.write_text(operator_summary, encoding="utf-8")

        delivery_manifest = {
            "artifact_type": "fsj_support_report_delivery_package",
            "artifact_version": self.DELIVERY_PACKAGE_VERSION,
            "business_date": business_date,
            "agent_domain": agent_domain,
            "slot": slot,
            "generated_at_utc": generated_at.isoformat(),
            "report_run_id": artifact.get("report_run_id"),
            "artifact_id": artifact.get("artifact_id"),
            "artifact_family": artifact.get("artifact_family"),
            "package_state": "ready" if qa.get("ready_for_delivery") else "blocked",
            "ready_for_delivery": bool(qa.get("ready_for_delivery")),
            "quality_gate": {
                "score": qa.get("score"),
                "blocker_count": (qa.get("summary") or {}).get("blocker_count"),
                "warning_count": (qa.get("summary") or {}).get("warning_count"),
                "qa_axes": (qa.get("summary") or {}).get("qa_axes") or {},
                "source_health": (qa.get("summary") or {}).get("source_health") or {},
            },
            "lineage": {
                "bundle_id": (rendered.get("metadata") or {}).get("bundle_id"),
                "producer_version": (rendered.get("metadata") or {}).get("producer_version"),
                "section_render_key": (rendered.get("metadata") or {}).get("section_render_key"),
                "report_link_count": (qa.get("summary") or {}).get("report_link_count"),
                "persisted_report_link_count": len(published.get("persisted_report_links") or []),
                "evidence_link_count": (qa.get("summary") or {}).get("evidence_link_count"),
            },
            "artifacts": {
                "html": package_html_path.name,
                "qa": package_qa_path.name,
                "manifest": package_manifest_path.name,
                "operator_summary": operator_summary_path.name,
            },
        }
        delivery_manifest_path = package_dir / "delivery_manifest.json"
        delivery_manifest_path.write_text(json.dumps(delivery_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        package_index = self._build_delivery_package_index(
            package_dir=package_dir,
            artifact=artifact,
            delivery_manifest=delivery_manifest,
            package_artifacts={
                "html": package_html_path,
                "qa": package_qa_path,
                "manifest": package_manifest_path,
                "operator_summary": operator_summary_path,
                "delivery_manifest": delivery_manifest_path,
            },
        )
        package_index_path = package_dir / "package_index.json"
        package_index_path.write_text(json.dumps(package_index, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        browse_readme_path = package_dir / "BROWSE_PACKAGE.md"
        browse_readme_path.write_text(self._build_delivery_package_browse_readme(package_index), encoding="utf-8")

        delivery_manifest["artifacts"]["delivery_manifest"] = delivery_manifest_path.name
        delivery_manifest["artifacts"]["package_index"] = package_index_path.name
        delivery_manifest["artifacts"]["browse_readme"] = browse_readme_path.name
        delivery_manifest_path.write_text(json.dumps(delivery_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        zip_path = root_output_dir / f"{package_slug}.zip"
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
            for path in sorted(package_dir.iterdir()):
                zf.write(path, arcname=f"{package_dir.name}/{path.name}")

        return {
            **published,
            "qa": qa,
            "qa_path": str(package_qa_path.resolve()),
            "delivery_package_dir": str(package_dir.resolve()),
            "delivery_manifest_path": str(delivery_manifest_path.resolve()),
            "delivery_zip_path": str(zip_path.resolve()),
            "operator_summary": operator_summary,
            "operator_summary_path": str(operator_summary_path.resolve()),
            "delivery_manifest": delivery_manifest,
            "package_index": package_index,
            "package_index_path": str(package_index_path.resolve()),
            "package_browse_readme_path": str(browse_readme_path.resolve()),
        }

    def _delivery_package_slug(self, *, business_date: str, agent_domain: str, slot: str, generated_at: datetime, artifact_id: str) -> str:
        stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
        safe_artifact_id = re.sub(r"[^A-Za-z0-9._-]+", "-", artifact_id).strip("-")
        return f"a_share_support_report_delivery_{agent_domain}_{slot}_{business_date}_{stamp}_{safe_artifact_id[-24:]}"

    def _build_operator_summary(
        self,
        *,
        business_date: str,
        agent_domain: str,
        slot: str,
        artifact: dict[str, Any],
        qa: dict[str, Any],
        rendered: dict[str, Any],
    ) -> str:
        quality = dict(qa.get("summary") or {})
        metadata = dict(rendered.get("metadata") or {})
        lines = [
            f"Support delivery package｜{business_date}｜{agent_domain}｜{slot}",
            f"ready_for_delivery={qa.get('ready_for_delivery')}｜score={qa.get('score')}",
            f"artifact_id={artifact.get('artifact_id')}",
            f"report_run_id={artifact.get('report_run_id') or '-'}",
            f"bundle_id={metadata.get('bundle_id') or '-'}",
            f"section_render_key={metadata.get('section_render_key') or '-'}",
            f"producer_version={metadata.get('producer_version') or '-'}",
            f"blockers={quality.get('blocker_count', 0)}｜warnings={quality.get('warning_count', 0)}｜evidence_links={quality.get('evidence_link_count', 0)}",
        ]
        return "\n".join(lines) + "\n"

    def _build_delivery_package_index(
        self,
        *,
        package_dir: Path,
        artifact: dict[str, Any],
        delivery_manifest: dict[str, Any],
        package_artifacts: dict[str, Path],
    ) -> dict[str, Any]:
        file_index: list[dict[str, Any]] = []
        for role, path in package_artifacts.items():
            file_index.append({
                "role": role,
                "filename": path.name,
                "path": str(path.resolve()),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
            })
        return {
            "artifact_type": "fsj_support_report_delivery_package_index",
            "artifact_version": self.DELIVERY_PACKAGE_VERSION,
            "artifact_id": artifact.get("artifact_id"),
            "business_date": delivery_manifest.get("business_date"),
            "agent_domain": delivery_manifest.get("agent_domain"),
            "slot": delivery_manifest.get("slot"),
            "report_run_id": delivery_manifest.get("report_run_id"),
            "delivery_package_dir": str(package_dir.resolve()),
            "package_state": delivery_manifest.get("package_state"),
            "ready_for_delivery": delivery_manifest.get("ready_for_delivery"),
            "quality_gate": dict(delivery_manifest.get("quality_gate") or {}),
            "lineage": dict(delivery_manifest.get("lineage") or {}),
            "browse_priority": ["html", "operator_summary", "delivery_manifest", "qa", "manifest"],
            "files": file_index,
        }

    def _build_delivery_package_browse_readme(self, package_index: dict[str, Any]) -> str:
        lines = [
            f"# Support Delivery Package Browse｜{package_index.get('business_date')}",
            "",
            "## Snapshot",
            f"- artifact_id: `{package_index.get('artifact_id') or '-'}`",
            f"- agent_domain: `{package_index.get('agent_domain') or '-'}`",
            f"- slot: `{package_index.get('slot') or '-'}`",
            f"- package_state: `{package_index.get('package_state') or '-'}`",
            f"- ready_for_delivery: `{package_index.get('ready_for_delivery')}`",
            "",
            "## Files",
        ]
        for item in package_index.get("files") or []:
            lines.append(
                f"- {item.get('role')}: `{item.get('filename')}` exists=`{item.get('exists')}` size_bytes=`{item.get('size_bytes')}`"
            )
        lines.append("")
        return "\n".join(lines) + "\n"
