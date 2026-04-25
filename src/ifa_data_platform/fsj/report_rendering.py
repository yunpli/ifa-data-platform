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
      <h2>Key Focus / Focus 模块</h2>
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

    def _build_customer_presentation(self, *, assembled: dict[str, Any], sections: Sequence[dict[str, Any]], focus_module: dict[str, Any] | None = None, chart_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
        customer_sections: list[dict[str, Any]] = []
        for section in sections:
            slot = str(section.get("slot") or "")
            slot_label = SLOT_LABELS.get(slot, slot or "未命名时段")
            support_items = [
                {
                    "domain": SUPPORT_DOMAIN_LABELS.get(str(item.get("agent_domain") or ""), str(item.get("agent_domain") or "support")),
                    "summary": str(item.get("summary") or "暂无摘要"),
                }
                for item in (section.get("support_summaries") or [])
            ]
            customer_sections.append(
                {
                    "slot": slot,
                    "slot_label": slot_label,
                    "title": self._customer_section_title(slot, str(section.get("title") or slot_label)),
                    "summary": str(section.get("summary") or "暂无摘要"),
                    "status": str(section.get("status") or "unknown"),
                    "highlights": self._customer_item_statements(section.get("judgments") or [], limit=3),
                    "signals": self._customer_item_statements(section.get("signals") or [], limit=3),
                    "facts": self._customer_item_statements(section.get("facts") or [], limit=3),
                    "support_themes": support_items,
                }
            )
        return {
            "schema_type": "fsj_customer_main_presentation",
            "schema_version": CUSTOMER_PRESENTATION_SCHEMA_VERSION,
            "business_date": assembled.get("business_date"),
            "market": assembled.get("market") or "a_share",
            "focus_module": focus_module or self._build_focus_module(assembled=assembled, sections=sections),
            "chart_pack": chart_manifest,
            "summary_cards": [
                {
                    "slot": item["slot"],
                    "slot_label": item["slot_label"],
                    "headline": item["summary"],
                    "support_themes": item["support_themes"],
                }
                for item in customer_sections
            ],
            "sections": customer_sections,
        }

    def _build_focus_module(self, *, assembled: dict[str, Any], sections: Sequence[dict[str, Any]]) -> dict[str, Any]:
        focus_symbols: list[str] = []
        focus_list_types: list[str] = []
        reasons: list[str] = []
        source_sections: list[str] = []
        judgment_refs: list[str] = []
        seen_focus: set[str] = set()
        seen_list_types: set[str] = set()
        seen_reasons: set[str] = set()
        for section in sections:
            slot = str(section.get("slot") or "")
            if slot:
                source_sections.append(slot)
            lineage = dict(section.get("lineage") or {})
            payload = dict((lineage.get("bundle") or {}).get("payload_json") or {})
            scope = dict(payload.get("focus_scope") or {})
            for symbol in scope.get("focus_symbols") or []:
                symbol = str(symbol or "").strip()
                if symbol and symbol not in seen_focus:
                    seen_focus.add(symbol)
                    focus_symbols.append(symbol)
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
        key_focus_symbols = focus_symbols[: min(5, len(focus_symbols))]
        return {
            "module_type": "fsj_focus_module",
            "business_date": assembled.get("business_date"),
            "list_types": focus_list_types,
            "focus_symbols": focus_symbols[:12],
            "focus_symbol_count": len(focus_symbols),
            "key_focus_symbols": key_focus_symbols,
            "key_focus_symbol_count": len(key_focus_symbols),
            "why_included": reasons[0] if reasons else "focus / key-focus 作为正式观察池进入报告，用于界定优先跟踪对象与噪音过滤边界。",
            "reasons": reasons[:3],
            "source_sections": source_sections,
            "chart_refs": [
                {"chart_key": "key_focus_window", "title": "Key Focus 窗口图"},
                {"chart_key": "key_focus_return_bar", "title": "Key Focus 日度涨跌幅"},
            ],
            "judgment_refs": judgment_refs[:8],
            "review_ready": bool(focus_symbols or focus_list_types),
        }

    def _render_focus_module_html(self, focus_module: dict[str, Any]) -> str:
        list_types = [str(item).replace("_", " ") for item in (focus_module.get("list_types") or [])]
        reasons = [str(item) for item in (focus_module.get("reasons") or []) if str(item).strip()]
        key_focus = [str(item) for item in (focus_module.get("key_focus_symbols") or []) if str(item).strip()]
        focus_symbols = [str(item) for item in (focus_module.get("focus_symbols") or []) if str(item).strip()]
        charts = focus_module.get("chart_refs") or []
        chart_text = "；".join(f"{item.get('title')}（{item.get('chart_key')}）" for item in charts if item.get("chart_key")) or "暂无图表关联"
        return (
            f'<div class="bucket"><h3>Why included</h3><ul>{"".join(f"<li>{escape(item)}</li>" for item in (reasons or [str(focus_module.get("why_included") or "暂无说明")]))}</ul></div>'
            f'<div class="bucket"><h3>Key Focus</h3><ul>{"".join(f"<li>{escape(item)}</li>" for item in key_focus) or "<li>暂无 Key Focus</li>"}</ul></div>'
            f'<div class="bucket"><h3>Focus</h3><ul>{"".join(f"<li>{escape(item)}</li>" for item in focus_symbols) or "<li>暂无 Focus</li>"}</ul></div>'
            f'<div class="bucket"><h3>Module wiring</h3><ul><li>list_types：{escape(", ".join(list_types) or "-")}</li><li>chart_refs：{escape(chart_text)}</li><li>judgment_refs：{escape(", ".join(focus_module.get("judgment_refs") or []) or "-")}</li></ul></div>'
        )

    def _customer_section_title(self, slot: str, fallback: str) -> str:
        mapping = {
            "early": "开盘前关注",
            "mid": "盘中观察",
            "late": "收盘复盘",
        }
        return mapping.get(slot, fallback)

    def _customer_item_statements(self, items: Sequence[dict[str, Any]], *, limit: int) -> list[str]:
        statements = [str(item.get("statement") or "").strip() for item in items if str(item.get("statement") or "").strip()]
        return statements[:limit]

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
    .hero h1 {{ margin: 0 0 10px; font-size: 32px; }}
    .hero .meta {{ font-size: 14px; line-height: 1.6; opacity: 0.92; }}
    .card {{ background: #fff; border-radius: 18px; padding: 22px 22px; margin-top: 18px; box-shadow: 0 10px 26px rgba(15, 23, 42, 0.07); }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
    .summary-box {{ border: 1px solid #dbe3f1; border-radius: 14px; padding: 14px 16px; background: #f8fbff; }}
    .summary-slot {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; }}
    .summary-headline {{ margin-top: 8px; font-size: 15px; line-height: 1.6; font-weight: 600; }}
    .support-line {{ margin-top: 10px; font-size: 13px; color: #475569; line-height: 1.6; }}
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
      <h1>{escape(title)}</h1>
      <div class=\"meta\">业务日期：{escape(str(assembled.get('business_date') or '-'))} · 市场：A股<br/>这是面向客户的简版展示层，仅展示结论、跟踪重点与补充视角，不展示内部运行对象。</div>
    </section>
    <section class=\"card\">
      <h2>今日节奏</h2>
      <div class=\"summary-grid\">{summary_cards}</div>
      <div class=\"footnote\">生成时间：{escape(generated_at.isoformat())} · 展示层 schema：{escape(CUSTOMER_PRESENTATION_SCHEMA_VERSION)}</div>
    </section>
    <section class=\"card\">
      <h2>今日 Key Focus / Focus</h2>
      {focus_module_html}
    </section>
    {chart_pack_html}
    <section class=\"card\">
      <h2>分时段解读</h2>
      {section_html}
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
        return f"<div class=\"summary-box\"><div class=\"summary-slot\">{escape(str(card.get('slot_label') or '-'))}</div><div class=\"summary-headline\">{escape(str(card.get('headline') or '暂无摘要'))}</div>{support_line}</div>"

    def _render_customer_focus_module(self, focus_module: dict[str, Any]) -> str:
        reasons = [str(item) for item in (focus_module.get("reasons") or []) if str(item).strip()]
        if not reasons:
            reasons = [str(focus_module.get("why_included") or "将今日重点观察池直接前置展示，帮助理解为什么这些对象值得跟踪。")]
        key_focus = [str(item) for item in (focus_module.get("key_focus_symbols") or []) if str(item).strip()]
        focus_symbols = [str(item) for item in (focus_module.get("focus_symbols") or []) if str(item).strip()]
        chart_refs = [str(item.get("title") or item.get("chart_key") or "") for item in (focus_module.get("chart_refs") or []) if str(item.get("title") or item.get("chart_key") or "").strip()]
        return (
            self._render_customer_bucket("为什么纳入", reasons, fallback="暂无纳入说明")
            + self._render_customer_bucket("Key Focus", key_focus, fallback="暂无 Key Focus")
            + self._render_customer_bucket("Focus", focus_symbols, fallback="暂无 Focus")
            + self._render_customer_bucket("关联图表", chart_refs, fallback="暂无关联图表")
        )

    def _render_customer_chart_pack(self, chart_pack: dict[str, Any]) -> str:
        assets = list(chart_pack.get("assets") or [])
        if not assets:
            return ""
        items = []
        for asset in assets:
            source_window = dict(asset.get("source_window") or {})
            items.append(
                f"<li>{escape(str(asset.get('title') or '-'))} · 状态={escape(str(asset.get('status') or '-'))} · 窗口={escape(str(source_window.get('lookback_bars') or '-'))} {escape(str(source_window.get('frequency') or '-'))} bars · 资源={escape(str(asset.get('relative_path') or '-'))}</li>"
            )
        return f"<section class=\"card\"><h2>关键图表</h2><div class=\"footnote\">chart_degrade_status={escape(str(chart_pack.get('degrade_status') or '-'))} · ready_chart_count={escape(str(chart_pack.get('ready_chart_count') or '-'))}/{escape(str(chart_pack.get('chart_count') or '-'))}</div><ul>{''.join(items)}</ul></section>"

    def _render_customer_section(self, section: dict[str, Any]) -> str:
        support_items = section.get("support_themes") or []
        support_html = ""
        if support_items:
            support_html = self._render_customer_bucket(
                "补充视角",
                [f"{item.get('domain')}：{item.get('summary')}" for item in support_items if item.get('summary')],
                fallback="暂无补充视角",
            )
        return f"""
        <div class=\"section\">
          <h3>{escape(str(section.get('title') or '-'))}</h3>
          <div class=\"section-summary\">{escape(str(section.get('summary') or '暂无摘要'))}</div>
          {self._render_customer_bucket('重点结论', section.get('highlights') or [], fallback='暂无重点结论')}
          {self._render_customer_bucket('跟踪信号', section.get('signals') or [], fallback='暂无跟踪信号')}
          {self._render_customer_bucket('已知事实', section.get('facts') or [], fallback='暂无已知事实')}
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
    ) -> dict[str, Any]:
        published = self.publish_main_report_html(
            business_date=business_date,
            output_dir=output_dir,
            include_empty=include_empty,
            report_run_id=report_run_id,
            generated_at=generated_at,
            output_profile=output_profile,
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
