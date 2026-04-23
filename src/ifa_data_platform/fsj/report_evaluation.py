from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .report_quality import EXPECTED_SLOTS


@dataclass(frozen=True)
class SlotEvaluation:
    slot: str
    status: str
    score: int
    evidence_density: int
    support_summary_count: int
    issue_codes: tuple[str, ...]
    strengths: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "status": self.status,
            "score": self.score,
            "evidence_density": self.evidence_density,
            "support_summary_count": self.support_summary_count,
            "issue_codes": list(self.issue_codes),
            "strengths": list(self.strengths),
        }


class MainReportEvaluationHarness:
    """Report-level slot comparison harness for assembled MAIN output.

    This is complementary to the hard QA gate: QA decides send/no-send; this harness
    explains comparative slot quality and progression across early/mid/late.
    """

    def evaluate(
        self,
        assembled: dict[str, Any],
        rendered: dict[str, Any],
        qa: dict[str, Any],
    ) -> dict[str, Any]:
        sections = {str(section.get("slot") or ""): section for section in (assembled.get("sections") or [])}
        qa_issues = list(qa.get("issues") or [])
        issue_codes_by_slot: dict[str, list[str]] = {}
        for issue in qa_issues:
            slot = issue.get("slot")
            if slot:
                issue_codes_by_slot.setdefault(str(slot), []).append(str(issue.get("code") or "unknown_issue"))

        slot_evals = [
            self._evaluate_slot(slot, sections.get(slot), issue_codes_by_slot.get(slot, []))
            for slot in EXPECTED_SLOTS
        ]
        slot_scores = {item.slot: item.score for item in slot_evals}
        progression = self._evaluate_progression(sections)
        delivery_readiness = {
            "qa_ready": bool(qa.get("ready_for_delivery")),
            "qa_score": int(qa.get("score") or 0),
            "late_contract_mode": (qa.get("summary") or {}).get("late_contract_mode"),
        }
        strongest_slot = max(slot_evals, key=lambda item: (item.score, item.evidence_density, item.slot)).slot if slot_evals else None
        weakest_slot = min(slot_evals, key=lambda item: (item.score, item.evidence_density, item.slot)).slot if slot_evals else None

        return {
            "artifact_type": "fsj_main_report_evaluation",
            "artifact_version": "v1",
            "business_date": assembled.get("business_date"),
            "market": assembled.get("market"),
            "agent_domain": assembled.get("agent_domain"),
            "renderer_version": (rendered.get("metadata") or {}).get("renderer_version"),
            "delivery_readiness": delivery_readiness,
            "summary": {
                "slot_scores": slot_scores,
                "strongest_slot": strongest_slot,
                "weakest_slot": weakest_slot,
                "slot_score_span": (max(slot_scores.values()) - min(slot_scores.values())) if slot_scores else 0,
                "average_slot_score": round(sum(slot_scores.values()) / len(slot_scores), 1) if slot_scores else 0,
                "progression": progression,
            },
            "slots": [item.as_dict() for item in slot_evals],
        }

    def _evaluate_slot(self, slot: str, section: dict[str, Any] | None, issue_codes: Sequence[str]) -> SlotEvaluation:
        if not section:
            return SlotEvaluation(
                slot=slot,
                status="missing",
                score=0,
                evidence_density=0,
                support_summary_count=0,
                issue_codes=tuple(sorted(set(issue_codes or ["slot_missing"]))),
                strengths=(),
            )

        status = str(section.get("status") or "unknown")
        bundle = dict(section.get("bundle") or {})
        judgments = list(section.get("judgments") or [])
        signals = list(section.get("signals") or [])
        facts = list(section.get("facts") or [])
        support_summaries = list(section.get("support_summaries") or [])
        lineage = dict(section.get("lineage") or {})
        evidence_links = list(lineage.get("evidence_links") or [])
        observed_records = list(lineage.get("observed_records") or [])
        report_links = list(lineage.get("report_links") or [])
        evidence_density = len(judgments) + len(signals) + len(facts) + len(evidence_links) + len(observed_records)

        score = 0
        strengths: list[str] = []
        if status == "ready":
            score += 35
            strengths.append("ready")
        if bundle.get("slot_run_id") and bundle.get("replay_id"):
            score += 15
            strengths.append("lineage_complete")
        if judgments:
            score += 15
            strengths.append("has_judgment")
        if signals:
            score += 10
            strengths.append("has_signal")
        if facts:
            score += 10
            strengths.append("has_fact")
        if evidence_links:
            score += 5
            strengths.append("has_evidence")
        if report_links:
            score += 5
            strengths.append("has_existing_report_link")
        if support_summaries:
            score += min(5, len(support_summaries) * 2)
            strengths.append("support_context_present")

        if evidence_density >= 6:
            score += 5
            strengths.append("dense")

        for code in set(issue_codes):
            if code in {"slot_missing", "late_not_ready", "late_historical_only", "report_link_missing", "summary_missing", "bundle_id_missing", "lineage_ids_missing", "late_close_signal_missing", "late_contract_mode_invalid"}:
                score -= 20
            elif code in {"section_not_ready", "section_empty_body", "support_summary_missing", "support_domain_unknown", "late_provisional_close"}:
                score -= 8

        return SlotEvaluation(
            slot=slot,
            status=status,
            score=max(0, min(100, score)),
            evidence_density=evidence_density,
            support_summary_count=len(support_summaries),
            issue_codes=tuple(sorted(set(issue_codes))),
            strengths=tuple(strengths),
        )

    def _evaluate_progression(self, sections: dict[str, dict[str, Any]]) -> dict[str, Any]:
        observed_slots = [slot for slot in EXPECTED_SLOTS if sections.get(slot)]
        summaries = {
            slot: str((sections.get(slot) or {}).get("summary") or "").strip()
            for slot in EXPECTED_SLOTS
            if sections.get(slot)
        }
        duplicates = []
        seen: dict[str, str] = {}
        for slot, summary in summaries.items():
            if not summary:
                continue
            prior = seen.get(summary)
            if prior:
                duplicates.append({"summary": summary, "slots": [prior, slot]})
            else:
                seen[summary] = slot

        late_section = sections.get("late") or {}
        late_close_signal = next(
            (obj for obj in (late_section.get("signals") or []) if obj.get("object_key") == "signal:late:close_package_state"),
            None,
        )
        late_contract_mode = ((late_close_signal or {}).get("attributes_json") or {}).get("contract_mode")
        progression_state = "complete" if observed_slots == list(EXPECTED_SLOTS) else "partial"
        if duplicates:
            progression_state = "stale_repetition"

        return {
            "state": progression_state,
            "observed_slots": observed_slots,
            "missing_slots": [slot for slot in EXPECTED_SLOTS if slot not in observed_slots],
            "duplicate_summary_count": len(duplicates),
            "duplicate_summaries": duplicates,
            "late_contract_mode": late_contract_mode,
        }
