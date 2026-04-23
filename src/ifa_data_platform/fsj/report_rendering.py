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

from .report_assembly import MainReportAssemblyService, SupportReportAssemblyService
from .report_dispatch import MainReportDeliveryDispatchHelper
from .report_evaluation import MainReportEvaluationHarness
from .report_quality import MainReportQAEvaluator, SupportReportQAEvaluator
from .store import FSJStore

RENDERER_NAME = "ifa_data_platform.fsj.report_rendering.MainReportHTMLRenderer"
RENDERER_VERSION = "v3"

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
            "support_summary_domains": list(assembled.get("support_summary_domains") or []),
            "support_summary_bundle_ids": [item.get("bundle_id") for section in sections for item in (section.get("support_summaries") or []) if item.get("bundle_id")],
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
    ) -> str:
        executive = self._build_executive_summary(sections)
        institutional_panel = self._build_institutional_panel(assembled, sections)
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


class MainReportArtifactPublishingService:
    ARTIFACT_FAMILY = "main_final_report"
    DELIVERY_PACKAGE_VERSION = "v1"

    def __init__(
        self,
        rendering_service: MainReportRenderingService,
        store: FSJStore,
        qa_evaluator: MainReportQAEvaluator | None = None,
        evaluation_harness: MainReportEvaluationHarness | None = None,
    ) -> None:
        self.rendering_service = rendering_service
        self.store = store
        self.qa_evaluator = qa_evaluator or MainReportQAEvaluator()
        self.evaluation_harness = evaluation_harness or MainReportEvaluationHarness()
        self.dispatch_helper = MainReportDeliveryDispatchHelper()

    def publish_main_report_html(
        self,
        *,
        business_date: str,
        output_dir: str | Path,
        include_empty: bool = False,
        report_run_id: str | None = None,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
        artifact_id = f"fsj-main-report:{business_date}:{stamp}:{uuid4().hex[:8]}"
        html_path = output_path / f"a_share_main_report_{business_date}_{stamp}.html"
        artifact_uri = html_path.resolve().as_uri()
        effective_report_run_id = report_run_id or artifact_id

        rendered = self.rendering_service.render_main_report_html(
            business_date=business_date,
            include_empty=include_empty,
            report_run_id=effective_report_run_id,
            artifact_uri=artifact_uri,
        )
        html_path.write_text(rendered["content"], encoding="utf-8")

        assembled = self.rendering_service.assembly_service.assemble_main_sections(
            business_date=business_date,
            include_empty=include_empty,
        )
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
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        return {
            "artifact": artifact_record,
            "html_path": str(html_path.resolve()),
            "qa_path": str(qa_path.resolve()),
            "eval_path": str(eval_path.resolve()),
            "manifest_path": str(manifest_path.resolve()),
            "rendered": rendered,
            "evaluation": evaluation,
            "report_evaluation": report_eval,
            "persisted_report_links": persisted_links,
        }

    def publish_delivery_package(
        self,
        *,
        business_date: str,
        output_dir: str | Path,
        include_empty: bool = False,
        report_run_id: str | None = None,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        published = self.publish_main_report_html(
            business_date=business_date,
            output_dir=output_dir,
            include_empty=include_empty,
            report_run_id=report_run_id,
            generated_at=generated_at,
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
        support_summary_aggregate = self._build_support_summary_aggregate(
            rendered=rendered,
            evaluation=evaluation,
            report_eval=report_eval,
        )

        package_slug = self._delivery_package_slug(
            business_date=business_date,
            generated_at=generated_at,
            artifact_id=str(artifact["artifact_id"]),
        )
        root_output_dir = Path(output_dir)
        package_dir = root_output_dir / package_slug
        package_dir.mkdir(parents=True, exist_ok=True)

        package_html_path = package_dir / html_path.name
        package_qa_path = package_dir / qa_path.name
        package_eval_path = package_dir / eval_path.name
        package_manifest_path = package_dir / manifest_path.name
        shutil.copy2(html_path, package_html_path)
        shutil.copy2(qa_path, package_qa_path)
        shutil.copy2(eval_path, package_eval_path)
        shutil.copy2(manifest_path, package_manifest_path)

        caption_text = self._build_delivery_caption(
            business_date=business_date,
            artifact=artifact,
            evaluation=evaluation,
            rendered=rendered,
            support_summary_aggregate=support_summary_aggregate,
        )
        caption_path = package_dir / "telegram_caption.txt"
        caption_path.write_text(caption_text, encoding="utf-8")

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
                "late_contract_mode": (evaluation.get("summary") or {}).get("late_contract_mode"),
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
            "artifacts": {
                "html": package_html_path.name,
                "qa": package_qa_path.name,
                "evaluation": package_eval_path.name,
                "manifest": package_manifest_path.name,
                "telegram_caption": caption_path.name,
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
            "browse_priority": ["html", "telegram_caption", "delivery_manifest", "evaluation", "qa", "manifest"],
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
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        domain = str(assembled.get("agent_domain") or "support")
        slot = str(assembled.get("slot") or "")
        title = f"A股{SUPPORT_DOMAIN_LABELS.get(domain, domain)} support 报告｜{SUPPORT_SLOT_LABELS.get(slot, slot)}｜{assembled.get('business_date') or '-'}"
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
        )


class SupportReportArtifactPublishingService:
    ARTIFACT_FAMILY = "support_domain_report"
    DELIVERY_PACKAGE_VERSION = "v1"

    def __init__(
        self,
        rendering_service: SupportReportRenderingService,
        store: FSJStore,
        qa_evaluator: SupportReportQAEvaluator | None = None,
    ) -> None:
        self.rendering_service = rendering_service
        self.store = store
        self.qa_evaluator = qa_evaluator or SupportReportQAEvaluator()

    def publish_support_report_html(
        self,
        *,
        business_date: str,
        agent_domain: str,
        slot: str,
        output_dir: str | Path,
        report_run_id: str | None = None,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        output_path = Path(output_dir)
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
    ) -> dict[str, Any]:
        published = self.publish_support_report_html(
            business_date=business_date,
            agent_domain=agent_domain,
            slot=slot,
            output_dir=output_dir,
            report_run_id=report_run_id,
            generated_at=generated_at,
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
        qa_path = Path(output_dir) / f"a_share_support_{agent_domain}_{slot}_{business_date}_{generated_at.strftime('%Y%m%dT%H%M%SZ')}.qa.json"
        qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        package_slug = self._delivery_package_slug(
            business_date=business_date,
            agent_domain=agent_domain,
            slot=slot,
            generated_at=generated_at,
            artifact_id=str(artifact["artifact_id"]),
        )
        root_output_dir = Path(output_dir)
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
