from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


EXPECTED_SLOTS: tuple[str, ...] = ("early", "mid", "late")
VALID_SUPPORT_DOMAINS: set[str] = {"macro", "commodities", "ai_tech"}
VALID_LATE_CONTRACT_MODES: set[str] = {
    "full_close_package",
    "provisional_close_only",
    "historical_only",
}


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    code: str
    message: str
    slot: str | None = None
    section_render_key: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.slot:
            payload["slot"] = self.slot
        if self.section_render_key:
            payload["section_render_key"] = self.section_render_key
        return payload


class MainReportQAEvaluator:
    """Deterministic report-level QA gate for sendable MAIN HTML artifacts."""

    def evaluate(self, assembled: dict[str, Any], rendered: dict[str, Any]) -> dict[str, Any]:
        issues: list[QualityIssue] = []
        sections = list(assembled.get("sections") or [])
        rendered_links = list(rendered.get("report_links") or [])
        metadata = dict(rendered.get("metadata") or {})
        html = str(rendered.get("content") or "")
        links_by_bundle = {
            str(link.get("bundle_id")): link
            for link in rendered_links
            if link.get("bundle_id")
        }

        self._check_top_level(assembled, rendered, html, issues)
        self._check_section_coverage(sections, issues)

        slot_status: dict[str, str] = {}
        late_contract_mode: str | None = None
        ready_section_count = 0
        support_summary_count = 0

        for section in sections:
            slot = str(section.get("slot") or "")
            section_render_key = str(section.get("section_render_key") or "")
            status = str(section.get("status") or "unknown")
            slot_status[slot] = status
            support_items = list(section.get("support_summaries") or [])
            support_summary_count += len(support_items)
            if status == "ready":
                ready_section_count += 1
            self._check_section(section, links_by_bundle, issues)
            self._check_support_summaries(section, issues)
            if slot == "late":
                late_contract_mode = self._check_late_section(section, issues)

        ready_for_delivery, blockers, warnings = self._decide_delivery_readiness(
            slot_status=slot_status,
            late_contract_mode=late_contract_mode,
            issues=issues,
        )
        score = max(0, 100 - blockers * 25 - warnings * 8)

        return {
            "artifact_type": "fsj_main_report_qa",
            "artifact_version": "v1",
            "ready_for_delivery": ready_for_delivery,
            "score": score,
            "summary": {
                "business_date": assembled.get("business_date"),
                "market": assembled.get("market"),
                "agent_domain": assembled.get("agent_domain"),
                "section_count": len(sections),
                "ready_section_count": ready_section_count,
                "support_summary_count": support_summary_count,
                "expected_slots": list(EXPECTED_SLOTS),
                "slot_status": slot_status,
                "late_contract_mode": late_contract_mode,
                "report_link_count": len(rendered_links),
                "existing_report_link_count": len(metadata.get("existing_report_links") or []),
                "html_bytes": len(html.encode("utf-8")),
                "blocker_count": blockers,
                "warning_count": warnings,
            },
            "issues": [issue.as_dict() for issue in issues],
        }

    def _check_top_level(self, assembled: dict[str, Any], rendered: dict[str, Any], html: str, issues: list[QualityIssue]) -> None:
        if assembled.get("market") != "a_share":
            issues.append(QualityIssue("error", "market_not_a_share", "assembled.market 必须为 a_share"))
        if assembled.get("agent_domain") != "main":
            issues.append(QualityIssue("error", "agent_not_main", "assembled.agent_domain 必须为 main"))
        if rendered.get("render_format") != "html" or rendered.get("content_type") != "text/html":
            issues.append(QualityIssue("error", "render_format_invalid", "rendered artifact 必须是 text/html"))
        lowered = html.lower()
        if "<!doctype html>" not in lowered:
            issues.append(QualityIssue("error", "missing_doctype", "HTML 缺少 <!DOCTYPE html>"))
        if "<html" not in lowered or "<body" not in lowered or "</html>" not in lowered:
            issues.append(QualityIssue("error", "html_shell_incomplete", "HTML 壳不完整，缺少 html/body 包裹"))
        if len(html.encode("utf-8")) < 1200:
            issues.append(QualityIssue("warning", "html_too_small", "HTML 体积过小，可能不是完整送达版报告"))
        if any(token in html for token in (">None<", " undefined", "null</", "[object Object]")):
            issues.append(QualityIssue("error", "html_placeholder_leak", "HTML 中出现 None/undefined/null 等占位泄漏"))

    def _check_section_coverage(self, sections: Sequence[dict[str, Any]], issues: list[QualityIssue]) -> None:
        seen_slots = {str(section.get("slot") or "") for section in sections}
        for slot in EXPECTED_SLOTS:
            if slot not in seen_slots:
                issues.append(QualityIssue("warning", "slot_missing", f"缺少 {slot} slot section", slot=slot))

    def _check_section(self, section: dict[str, Any], links_by_bundle: dict[str, dict[str, Any]], issues: list[QualityIssue]) -> None:
        slot = str(section.get("slot") or "")
        section_render_key = str(section.get("section_render_key") or "")
        status = str(section.get("status") or "unknown")
        bundle = dict(section.get("bundle") or {})
        if status != "ready":
            if slot == "late":
                issues.append(QualityIssue("error", "late_not_ready", "late slot 未 ready，不可视作送达版主报告", slot=slot, section_render_key=section_render_key))
            else:
                issues.append(QualityIssue("warning", "section_not_ready", f"{slot} slot 未 ready", slot=slot, section_render_key=section_render_key))
            return
        bundle_id = str(bundle.get("bundle_id") or "")
        if not bundle_id:
            issues.append(QualityIssue("error", "bundle_id_missing", "ready section 缺少 bundle_id", slot=slot, section_render_key=section_render_key))
        if not str(section.get("summary") or "").strip():
            issues.append(QualityIssue("error", "summary_missing", "ready section 缺少 summary", slot=slot, section_render_key=section_render_key))
        if not bundle.get("slot_run_id") or not bundle.get("replay_id"):
            issues.append(QualityIssue("error", "lineage_ids_missing", "ready section 缺少 slot_run_id/replay_id", slot=slot, section_render_key=section_render_key))
        if not ((section.get("judgments") or []) or (section.get("signals") or []) or (section.get("facts") or [])):
            issues.append(QualityIssue("warning", "section_empty_body", "ready section 没有 judgments/signals/facts，业务含量偏弱", slot=slot, section_render_key=section_render_key))
        if bundle_id and bundle_id not in links_by_bundle:
            issues.append(QualityIssue("error", "report_link_missing", "ready section 未生成 report_link", slot=slot, section_render_key=section_render_key))

    def _check_support_summaries(self, section: dict[str, Any], issues: list[QualityIssue]) -> None:
        slot = str(section.get("slot") or "")
        section_render_key = str(section.get("section_render_key") or "")
        for item in section.get("support_summaries") or []:
            domain = str(item.get("agent_domain") or "")
            if domain not in VALID_SUPPORT_DOMAINS:
                issues.append(QualityIssue("warning", "support_domain_unknown", f"未知 support 域: {domain}", slot=slot, section_render_key=section_render_key))
            if not str(item.get("summary") or "").strip():
                issues.append(QualityIssue("warning", "support_summary_missing", f"support summary 缺失: {domain or 'unknown'}", slot=slot, section_render_key=section_render_key))

    def _check_late_section(self, section: dict[str, Any], issues: list[QualityIssue]) -> str | None:
        slot = str(section.get("slot") or "late")
        section_render_key = str(section.get("section_render_key") or "")
        if str(section.get("status") or "") != "ready":
            return None
        close_signal = next(
            (obj for obj in (section.get("signals") or []) if obj.get("object_key") == "signal:late:close_package_state"),
            None,
        )
        if close_signal is None:
            issues.append(QualityIssue("error", "late_close_signal_missing", "late section 缺少 close_package_state 信号", slot=slot, section_render_key=section_render_key))
            return None
        attrs = dict(close_signal.get("attributes_json") or {})
        contract_mode = str(attrs.get("contract_mode") or "")
        if contract_mode not in VALID_LATE_CONTRACT_MODES:
            issues.append(QualityIssue("error", "late_contract_mode_invalid", f"late contract_mode 非法: {contract_mode or '-'}", slot=slot, section_render_key=section_render_key))
            return contract_mode or None
        if contract_mode == "provisional_close_only":
            issues.append(QualityIssue("warning", "late_provisional_close", "late 仅为 provisional_close_only；可发送但必须按降级口径理解", slot=slot, section_render_key=section_render_key))
        if contract_mode == "historical_only":
            issues.append(QualityIssue("error", "late_historical_only", "late 仅 historical_only，不应作为当日送达版晚报", slot=slot, section_render_key=section_render_key))
        return contract_mode

    def _decide_delivery_readiness(
        self,
        *,
        slot_status: dict[str, str],
        late_contract_mode: str | None,
        issues: Sequence[QualityIssue],
    ) -> tuple[bool, int, int]:
        blockers = sum(1 for issue in issues if issue.severity == "error")
        warnings = sum(1 for issue in issues if issue.severity == "warning")
        ready = blockers == 0
        if slot_status.get("late") != "ready":
            ready = False
        if late_contract_mode == "historical_only":
            ready = False
        return ready, blockers, warnings
