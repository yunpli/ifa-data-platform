from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Sequence


EXPECTED_SLOTS: tuple[str, ...] = ("early", "mid", "late")
EXPECTED_SUPPORT_SLOTS: tuple[str, ...] = ("early", "late")
VALID_SUPPORT_DOMAINS: set[str] = {"macro", "commodities", "ai_tech"}
VALID_LATE_CONTRACT_MODES: set[str] = {
    "full_close_package",
    "provisional_close_only",
    "historical_only",
}
MAIN_SOURCE_HEALTH_BLOCKING_REASONS: set[str] = {
    "same_day_final_structure_missing",
}
MAIN_SOURCE_HEALTH_WARNING_REASONS: set[str] = {
    "missing_preopen_high_layer",
    "missing_intraday_structure",
}
SUPPORT_SOURCE_HEALTH_WARNING_REASONS: set[str] = {
    "missing_background_support",
    "missing_macro_snapshot",
    "missing_ai_tech_snapshot",
}
CUSTOMER_LEAK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("customer_internal_field_leak", r"bundle-[a-z0-9_-]+"),
    ("customer_internal_field_leak", r"slot-run-[a-z0-9_-]+"),
    ("customer_internal_field_leak", r"replay-[a-z0-9_-]+"),
    ("customer_internal_field_leak", r"phase\d-[a-z0-9-]+-v\d+"),
    ("customer_internal_field_leak", r"file:///"),
    ("customer_internal_field_leak", r"report_links="),
    ("customer_internal_field_leak", r"renderer(?:_version)?="),
    ("customer_internal_field_leak", r"action="),
    ("customer_internal_field_leak", r"confidence="),
    ("customer_internal_field_leak", r"evidence="),
)


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
        source_health = self._source_health_summary(sections, issues)

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
        qa_axes = self._build_qa_axes(issues)
        customer_report_readiness = self._build_customer_report_readiness(
            rendered=rendered,
            ready_for_delivery=ready_for_delivery,
            source_health=source_health,
            qa_axes=qa_axes,
            issues=issues,
        )

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
                "source_health": source_health,
                "report_link_count": len(rendered_links),
                "existing_report_link_count": len(metadata.get("existing_report_links") or []),
                "html_bytes": len(html.encode("utf-8")),
                "blocker_count": blockers,
                "warning_count": warnings,
                "qa_axes": qa_axes,
                "customer_report_readiness": customer_report_readiness,
                "golden_sample_regression_hooks": self._golden_sample_regression_hooks(subject="main"),
            },
            "issues": [issue.as_dict() for issue in issues],
        }

    def _build_qa_axes(self, issues: Sequence[QualityIssue]) -> dict[str, Any]:
        axis_codes = {
            "structural": {
                "market_not_a_share",
                "agent_not_main",
                "render_format_invalid",
                "missing_doctype",
                "html_shell_incomplete",
                "html_too_small",
                "html_placeholder_leak",
                "slot_missing",
                "section_not_ready",
                "bundle_id_missing",
                "summary_missing",
                "section_empty_body",
                "report_link_missing",
                "support_domain_unknown",
                "support_summary_missing",
                "late_not_ready",
                "late_close_signal_missing",
            },
            "lineage": {"lineage_ids_missing"},
            "policy": {
                "late_contract_mode_invalid",
                "late_provisional_close",
                "late_historical_only",
                "source_health_blocked",
                "source_health_degraded",
            },
            "editorial": {
                "html_too_small",
                "summary_missing",
                "section_empty_body",
                "support_summary_missing",
            },
            "leakage": {
                "html_placeholder_leak",
                "customer_internal_field_leak",
            },
            "time_window": {
                "late_not_ready",
                "late_close_signal_missing",
                "late_contract_mode_invalid",
                "late_provisional_close",
                "late_historical_only",
                "source_health_blocked",
            },
            "customer_readiness": {
                "late_not_ready",
                "late_historical_only",
                "source_health_blocked",
                "customer_internal_field_leak",
            },
        }
        axes: dict[str, Any] = {}
        for axis, codes in axis_codes.items():
            axis_issues = [issue for issue in issues if issue.code in codes]
            blocker_count = sum(1 for issue in axis_issues if issue.severity == "error")
            warning_count = sum(1 for issue in axis_issues if issue.severity == "warning")
            axes[axis] = {
                "ready": blocker_count == 0,
                "score": max(0, 100 - blocker_count * 25 - warning_count * 8),
                "blocker_count": blocker_count,
                "warning_count": warning_count,
                "issue_codes": [issue.code for issue in axis_issues],
            }
        return axes

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
        if str((rendered.get("metadata") or {}).get("output_profile") or "") == "customer":
            for code, pattern in CUSTOMER_LEAK_PATTERNS:
                if re.search(pattern, html, re.IGNORECASE):
                    issues.append(QualityIssue("error", code, f"customer HTML 出现内部字段泄漏: {pattern}"))
                    break

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

    def _build_customer_report_readiness(
        self,
        *,
        rendered: dict[str, Any],
        ready_for_delivery: bool,
        source_health: dict[str, Any],
        qa_axes: dict[str, Any],
        issues: Sequence[QualityIssue],
    ) -> dict[str, Any]:
        output_profile = str((rendered.get("metadata") or {}).get("output_profile") or "internal")
        readiness_reasons: list[str] = []
        if not ready_for_delivery:
            readiness_reasons.append("delivery_gate_not_ready")
        if source_health.get("overall_status") == "blocked":
            readiness_reasons.append("source_health_blocked")
        for code in ("customer_internal_field_leak", "html_placeholder_leak", "late_historical_only"):
            if any(issue.code == code for issue in issues):
                readiness_reasons.append(code)
        leakage_axis = dict(qa_axes.get("leakage") or {})
        customer_axis = dict(qa_axes.get("customer_readiness") or {})
        return {
            "output_profile": output_profile,
            "customer_safe": output_profile != "customer" or not readiness_reasons,
            "ready": ready_for_delivery and not readiness_reasons,
            "blocking_reasons": readiness_reasons,
            "leakage_blocker_count": int(leakage_axis.get("blocker_count") or 0),
            "customer_readiness_axis_ready": customer_axis.get("ready"),
        }

    def _golden_sample_regression_hooks(self, *, subject: str) -> dict[str, Any]:
        tests = {
            "main": [
                "tests/integration/test_fsj_main_slot_golden_cases.py",
                "tests/integration/test_fsj_main_early_golden_case_family.py",
                "tests/integration/test_fsj_main_mid_golden_case_family.py",
                "tests/integration/test_fsj_main_late_golden_case_family.py",
                "tests/integration/test_fsj_main_llm_resilience_golden_case_family.py",
                "tests/integration/test_fsj_main_degraded_data_golden_case_family.py",
            ],
            "support": ["tests/unit/test_fsj_report_rendering.py"],
        }
        return {
            "subject": subject,
            "hook_family": "fsj_golden_regression",
            "recommended_tests": tests.get(subject, []),
        }

    def _source_health_summary(self, sections: Sequence[dict[str, Any]], issues: list[QualityIssue]) -> dict[str, Any]:
        slot_items: list[dict[str, Any]] = []
        blocked_slots = 0
        degraded_slots = 0

        for section in sections:
            slot = str(section.get("slot") or "")
            lineage = dict(section.get("lineage") or {})
            raw_bundle = dict(lineage.get("bundle") or {})
            payload = dict(raw_bundle.get("payload_json") or {})
            degrade = dict(payload.get("degrade") or {})
            degrade_reason = str(degrade.get("degrade_reason") or degrade.get("reason") or "")
            contract_mode = str(degrade.get("contract_mode") or payload.get("contract_mode") or "")
            completeness_label = str(degrade.get("completeness_label") or "")

            severity = "healthy"
            if degrade_reason in MAIN_SOURCE_HEALTH_BLOCKING_REASONS:
                severity = "blocked"
            elif degrade_reason in MAIN_SOURCE_HEALTH_WARNING_REASONS or degrade_reason:
                severity = "degraded"

            if severity == "blocked":
                blocked_slots += 1
                issues.append(QualityIssue("error", "source_health_blocked", f"{slot} slot required source family missing: {degrade_reason}", slot=slot or None, section_render_key=str(section.get("section_render_key") or "") or None))
            elif severity == "degraded":
                degraded_slots += 1
                issues.append(QualityIssue("warning", "source_health_degraded", f"{slot} slot source health degraded: {degrade_reason}", slot=slot or None, section_render_key=str(section.get("section_render_key") or "") or None))

            if slot:
                slot_items.append(
                    {
                        "slot": slot,
                        "status": severity,
                        "degrade_reason": degrade_reason or None,
                        "contract_mode": contract_mode or None,
                        "completeness_label": completeness_label or None,
                    }
                )

        overall_status = "healthy"
        if blocked_slots:
            overall_status = "blocked"
        elif degraded_slots:
            overall_status = "degraded"
        return {
            "overall_status": overall_status,
            "blocking_slot_count": blocked_slots,
            "degraded_slot_count": degraded_slots,
            "slots": slot_items,
        }


class SupportReportQAEvaluator:
    """Deterministic QA gate for standalone support HTML artifacts."""

    def evaluate(self, assembled: dict[str, Any], rendered: dict[str, Any]) -> dict[str, Any]:
        issues: list[QualityIssue] = []
        html = str(rendered.get("content") or "")
        metadata = dict(rendered.get("metadata") or {})
        report_links = list(rendered.get("report_links") or [])

        self._check_top_level(assembled, rendered, html, issues)
        self._check_section(assembled, report_links, issues)
        source_health = self._source_health_summary(assembled, issues)

        blockers = sum(1 for issue in issues if issue.severity == "error")
        warnings = sum(1 for issue in issues if issue.severity == "warning")
        ready_for_delivery = blockers == 0 and str(assembled.get("status") or "") == "ready"
        score = max(0, 100 - blockers * 25 - warnings * 8)
        qa_axes = self._build_qa_axes(issues)
        customer_report_readiness = self._build_customer_report_readiness(
            rendered=rendered,
            ready_for_delivery=ready_for_delivery,
            source_health=source_health,
            qa_axes=qa_axes,
            issues=issues,
        )

        return {
            "artifact_type": "fsj_support_report_qa",
            "artifact_version": "v1",
            "ready_for_delivery": ready_for_delivery,
            "score": score,
            "summary": {
                "business_date": assembled.get("business_date"),
                "market": assembled.get("market"),
                "agent_domain": assembled.get("agent_domain"),
                "slot": assembled.get("slot"),
                "section_key": assembled.get("section_key"),
                "section_render_key": assembled.get("section_render_key"),
                "status": assembled.get("status"),
                "source_health": source_health,
                "report_link_count": len(report_links),
                "existing_report_link_count": len(metadata.get("existing_report_links") or []),
                "evidence_link_count": int(metadata.get("evidence_link_count") or 0),
                "html_bytes": len(html.encode("utf-8")),
                "blocker_count": blockers,
                "warning_count": warnings,
                "qa_axes": qa_axes,
                "customer_report_readiness": customer_report_readiness,
                "golden_sample_regression_hooks": self._golden_sample_regression_hooks(subject="support"),
            },
            "issues": [issue.as_dict() for issue in issues],
        }

    def _build_qa_axes(self, issues: Sequence[QualityIssue]) -> dict[str, Any]:
        axis_codes = {
            "structural": {
                "market_not_a_share",
                "support_domain_invalid",
                "support_slot_invalid",
                "render_format_invalid",
                "missing_doctype",
                "html_shell_incomplete",
                "html_too_small",
                "html_placeholder_leak",
                "support_section_not_ready",
                "bundle_id_missing",
                "summary_missing",
                "section_empty_body",
                "report_link_missing",
            },
            "lineage": {"lineage_ids_missing"},
            "policy": {"support_source_health_degraded"},
            "editorial": {"html_too_small", "summary_missing", "section_empty_body"},
            "leakage": {"html_placeholder_leak", "customer_internal_field_leak"},
            "time_window": {"support_slot_invalid"},
            "customer_readiness": {"support_section_not_ready", "customer_internal_field_leak"},
        }
        axes: dict[str, Any] = {}
        for axis, codes in axis_codes.items():
            axis_issues = [issue for issue in issues if issue.code in codes]
            blocker_count = sum(1 for issue in axis_issues if issue.severity == "error")
            warning_count = sum(1 for issue in axis_issues if issue.severity == "warning")
            axes[axis] = {
                "ready": blocker_count == 0,
                "score": max(0, 100 - blocker_count * 25 - warning_count * 8),
                "blocker_count": blocker_count,
                "warning_count": warning_count,
                "issue_codes": [issue.code for issue in axis_issues],
            }
        return axes

    def _check_top_level(self, assembled: dict[str, Any], rendered: dict[str, Any], html: str, issues: list[QualityIssue]) -> None:
        if assembled.get("market") != "a_share":
            issues.append(QualityIssue("error", "market_not_a_share", "assembled.market 必须为 a_share"))
        domain = str(assembled.get("agent_domain") or "")
        if domain not in VALID_SUPPORT_DOMAINS:
            issues.append(QualityIssue("error", "support_domain_invalid", f"assembled.agent_domain 非法: {domain or '-'}"))
        slot = str(assembled.get("slot") or "")
        if slot not in EXPECTED_SUPPORT_SLOTS:
            issues.append(QualityIssue("error", "support_slot_invalid", f"assembled.slot 非法: {slot or '-'}", slot=slot or None))
        if rendered.get("render_format") != "html" or rendered.get("content_type") != "text/html":
            issues.append(QualityIssue("error", "render_format_invalid", "support rendered artifact 必须是 text/html", slot=slot or None))
        lowered = html.lower()
        if "<!doctype html>" not in lowered:
            issues.append(QualityIssue("error", "missing_doctype", "HTML 缺少 <!DOCTYPE html>", slot=slot or None))
        if "<html" not in lowered or "<body" not in lowered or "</html>" not in lowered:
            issues.append(QualityIssue("error", "html_shell_incomplete", "HTML 壳不完整，缺少 html/body 包裹", slot=slot or None))
        if len(html.encode("utf-8")) < 800:
            issues.append(QualityIssue("warning", "html_too_small", "HTML 体积过小，可能不是完整 support 报告", slot=slot or None))
        if any(token in html for token in (">None<", " undefined", "null</", "[object Object]")):
            issues.append(QualityIssue("error", "html_placeholder_leak", "HTML 中出现 None/undefined/null 等占位泄漏", slot=slot or None))
        if str((rendered.get("metadata") or {}).get("output_profile") or "") == "customer":
            for code, pattern in CUSTOMER_LEAK_PATTERNS:
                if re.search(pattern, html, re.IGNORECASE):
                    issues.append(QualityIssue("error", code, f"customer HTML 出现内部字段泄漏: {pattern}", slot=slot or None))
                    break

    def _check_section(self, assembled: dict[str, Any], report_links: Sequence[dict[str, Any]], issues: list[QualityIssue]) -> None:
        slot = str(assembled.get("slot") or "")
        section_render_key = str(assembled.get("section_render_key") or "")
        status = str(assembled.get("status") or "unknown")
        bundle = dict(assembled.get("bundle") or {})
        if status != "ready":
            issues.append(QualityIssue("error", "support_section_not_ready", "support section 未 ready", slot=slot or None, section_render_key=section_render_key or None))
            return
        bundle_id = str(bundle.get("bundle_id") or "")
        if not bundle_id:
            issues.append(QualityIssue("error", "bundle_id_missing", "ready support section 缺少 bundle_id", slot=slot or None, section_render_key=section_render_key or None))
        if not str(assembled.get("summary") or "").strip():
            issues.append(QualityIssue("error", "summary_missing", "ready support section 缺少 summary", slot=slot or None, section_render_key=section_render_key or None))
        if not bundle.get("slot_run_id") or not bundle.get("replay_id"):
            issues.append(QualityIssue("error", "lineage_ids_missing", "ready support section 缺少 slot_run_id/replay_id", slot=slot or None, section_render_key=section_render_key or None))
        if not ((assembled.get("judgments") or []) or (assembled.get("signals") or []) or (assembled.get("facts") or [])):
            issues.append(QualityIssue("warning", "section_empty_body", "ready support section 没有 judgments/signals/facts，业务含量偏弱", slot=slot or None, section_render_key=section_render_key or None))
        if bundle_id and not any(str(link.get("bundle_id") or "") == bundle_id for link in report_links):
            issues.append(QualityIssue("error", "report_link_missing", "ready support section 未生成 report_link", slot=slot or None, section_render_key=section_render_key or None))

    def _build_customer_report_readiness(
        self,
        *,
        rendered: dict[str, Any],
        ready_for_delivery: bool,
        source_health: dict[str, Any],
        qa_axes: dict[str, Any],
        issues: Sequence[QualityIssue],
    ) -> dict[str, Any]:
        output_profile = str((rendered.get("metadata") or {}).get("output_profile") or "internal")
        readiness_reasons: list[str] = []
        if not ready_for_delivery:
            readiness_reasons.append("delivery_gate_not_ready")
        if source_health.get("overall_status") == "blocked":
            readiness_reasons.append("source_health_blocked")
        for code in ("customer_internal_field_leak", "html_placeholder_leak"):
            if any(issue.code == code for issue in issues):
                readiness_reasons.append(code)
        leakage_axis = dict(qa_axes.get("leakage") or {})
        customer_axis = dict(qa_axes.get("customer_readiness") or {})
        return {
            "output_profile": output_profile,
            "customer_safe": output_profile != "customer" or not readiness_reasons,
            "ready": ready_for_delivery and not readiness_reasons,
            "blocking_reasons": readiness_reasons,
            "leakage_blocker_count": int(leakage_axis.get("blocker_count") or 0),
            "customer_readiness_axis_ready": customer_axis.get("ready"),
        }

    def _golden_sample_regression_hooks(self, *, subject: str) -> dict[str, Any]:
        return {
            "subject": subject,
            "hook_family": "fsj_golden_regression",
            "recommended_tests": ["tests/unit/test_fsj_report_rendering.py"],
        }

    def _source_health_summary(self, assembled: dict[str, Any], issues: list[QualityIssue]) -> dict[str, Any]:
        lineage = dict(assembled.get("lineage") or {})
        raw_bundle = dict(lineage.get("bundle") or {})
        payload = dict(raw_bundle.get("payload_json") or {})
        degrade = dict(payload.get("degrade") or {})
        degrade_reason = str(degrade.get("degrade_reason") or degrade.get("reason") or "")

        status = "healthy"
        if degrade_reason in SUPPORT_SOURCE_HEALTH_WARNING_REASONS or degrade_reason:
            status = "degraded"
            issues.append(
                QualityIssue(
                    "warning",
                    "support_source_health_degraded",
                    f"support source health degraded: {degrade_reason}",
                    slot=str(assembled.get("slot") or "") or None,
                    section_render_key=str(assembled.get("section_render_key") or "") or None,
                )
            )

        return {
            "overall_status": status,
            "degrade_reason": degrade_reason or None,
        }
