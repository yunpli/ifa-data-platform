from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from typing import Any, Sequence

from .report_assembly import MainReportAssemblyService

RENDERER_NAME = "ifa_data_platform.fsj.report_rendering.MainReportHTMLRenderer"
RENDERER_VERSION = "v1"

SLOT_LABELS: dict[str, str] = {
    "early": "早报 / 盘前",
    "mid": "中报 / 盘中",
    "late": "晚报 / 收盘后",
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
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        title = f"A股主报告｜{assembled.get('business_date') or '-'}"
        sections = list(assembled.get("sections") or [])
        html = self._render_html(title=title, assembled=assembled, sections=sections, generated_at=generated_at)
        report_links = self._build_report_links(
            sections,
            report_run_id=report_run_id,
            artifact_uri=artifact_uri,
        )
        metadata = {
            "market": assembled.get("market"),
            "business_date": assembled.get("business_date"),
            "agent_domain": assembled.get("agent_domain"),
            "source_artifact_type": assembled.get("artifact_type"),
            "source_artifact_version": assembled.get("artifact_version"),
            "renderer": RENDERER_NAME,
            "renderer_version": RENDERER_VERSION,
            "generated_at": generated_at.isoformat(),
            "section_count": len(sections),
            "bundle_ids": [section.get("bundle", {}).get("bundle_id") for section in sections if section.get("bundle")],
            "producer_versions": [section.get("bundle", {}).get("producer_version") for section in sections if section.get("bundle")],
            "artifact_uri": artifact_uri,
            "existing_report_links": [
                link
                for section in sections
                for link in ((section.get("lineage") or {}).get("report_links") or [])
            ],
        }
        return RenderedFSJArtifact(
            artifact_type="fsj_main_report_html",
            artifact_version="v1",
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
    ) -> str:
        executive = self._build_executive_summary(sections)
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
      <div class=\"footnote\">
        本报告由 FSJ section assembly 直接渲染，保留 bundle / producer_version / replay_id / report_link 钩子，适合作为首个可发送 HTML 成品。
      </div>
    </section>

    <section class=\"card\">
      <h2>主体内容</h2>
      {section_html}
    </section>
  </div>
</body>
</html>
"""

    def _build_executive_summary(self, sections: Sequence[dict[str, Any]]) -> str:
        boxes: list[str] = []
        for section in sections:
            label = SLOT_LABELS.get(str(section.get("slot") or ""), str(section.get("slot") or "未命名时段"))
            headline = section.get("summary") or "暂无摘要"
            boxes.append(
                f"<div class=\"summary-box\"><div class=\"slot\">{escape(label)}</div><div class=\"headline\">{escape(str(headline))}</div></div>"
            )
        if not boxes:
            boxes.append("<div class=\"summary-box\"><div class=\"slot\">EMPTY</div><div class=\"headline\">暂无可渲染章节</div></div>")
        return "".join(boxes)

    def _render_section(self, section: dict[str, Any]) -> str:
        bundle = section.get("bundle") or {}
        lineage = section.get("lineage") or {}
        slot_label = SLOT_LABELS.get(str(section.get("slot") or ""), str(section.get("slot") or "未命名时段"))
        status = str(section.get("status") or "unknown")
        pill_class = "pill missing" if status != "ready" else "pill"
        judgments = self._render_items(section.get("judgments") or [], fallback="暂无主判断")
        signals = self._render_items(section.get("signals") or [], fallback="暂无关键验证信号")
        facts = self._render_items(section.get("facts") or [], fallback="暂无事实锚点")
        evidence_keys = [str(item.get("ref_key")) for item in (lineage.get("evidence_links") or []) if item.get("ref_key")]
        report_uris = [str(item.get("artifact_uri")) for item in (lineage.get("report_links") or []) if item.get("artifact_uri")]
        lineage_note = "；".join(
            part for part in [
                f"evidence={', '.join(evidence_keys[:3])}" if evidence_keys else "",
                f"report_links={', '.join(report_uris[:2])}" if report_uris else "",
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
          <div class=\"bucket\"><strong>主判断</strong>{judgments}</div>
          <div class=\"bucket\"><strong>关键验证 / 信号</strong>{signals}</div>
          <div class=\"bucket\"><strong>事实锚点</strong>{facts}</div>
          <div class=\"footnote\">
            lineage：slot_run_id=<span class=\"mono\">{escape(str(bundle.get('slot_run_id') or '-'))}</span> · replay_id=<span class=\"mono\">{escape(str(bundle.get('replay_id') or '-'))}</span> · {escape(lineage_note)}
          </div>
        </div>
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
    ) -> dict[str, Any]:
        assembled = self.assembly_service.assemble_main_sections(
            business_date=business_date,
            include_empty=include_empty,
        )
        return self.renderer.render(
            assembled,
            report_run_id=report_run_id,
            artifact_uri=artifact_uri,
        )
