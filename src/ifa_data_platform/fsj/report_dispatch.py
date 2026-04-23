from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


SLOT_PRIORITY: dict[str, int] = {"late": 30, "mid": 20, "early": 10}


@dataclass(frozen=True)
class DeliveryDispatchCandidate:
    artifact_id: str
    report_run_id: str | None
    business_date: str | None
    package_state: str
    ready_for_delivery: bool
    qa_score: int
    blocker_count: int
    warning_count: int
    strongest_slot: str | None
    weakest_slot: str | None
    average_slot_score: float
    slot_score_span: int
    late_contract_mode: str | None
    delivery_package_dir: str | None
    delivery_manifest_path: str | None
    delivery_zip_path: str | None

    def rank_tuple(self) -> tuple[int, int, int, float, int, str]:
        return (
            1 if self.ready_for_delivery else 0,
            SLOT_PRIORITY.get(self.strongest_slot or "", 0),
            self.qa_score,
            self.average_slot_score,
            -self.warning_count,
            self.artifact_id,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "report_run_id": self.report_run_id,
            "business_date": self.business_date,
            "package_state": self.package_state,
            "ready_for_delivery": self.ready_for_delivery,
            "qa_score": self.qa_score,
            "blocker_count": self.blocker_count,
            "warning_count": self.warning_count,
            "strongest_slot": self.strongest_slot,
            "weakest_slot": self.weakest_slot,
            "average_slot_score": self.average_slot_score,
            "slot_score_span": self.slot_score_span,
            "late_contract_mode": self.late_contract_mode,
            "delivery_package_dir": self.delivery_package_dir,
            "delivery_manifest_path": self.delivery_manifest_path,
            "delivery_zip_path": self.delivery_zip_path,
        }


class MainReportDeliveryDispatchHelper:
    """Select the best MAIN delivery package for send / send-review orchestration."""

    def candidate_from_published(self, published: dict[str, Any]) -> DeliveryDispatchCandidate:
        delivery_manifest = dict(published.get("delivery_manifest") or {})
        quality_gate = dict(delivery_manifest.get("quality_gate") or {})
        slot_eval = dict(delivery_manifest.get("slot_evaluation") or {})
        summary = dict((published.get("report_evaluation") or {}).get("summary") or {})
        artifact = dict(published.get("artifact") or {})
        slot_scores = dict(slot_eval.get("slot_scores") or summary.get("slot_scores") or {})
        return DeliveryDispatchCandidate(
            artifact_id=str(delivery_manifest.get("artifact_id") or artifact.get("artifact_id") or "-"),
            report_run_id=(delivery_manifest.get("report_run_id") or artifact.get("report_run_id")),
            business_date=delivery_manifest.get("business_date") or artifact.get("business_date"),
            package_state=str(delivery_manifest.get("package_state") or ("ready" if delivery_manifest.get("ready_for_delivery") else "blocked")),
            ready_for_delivery=bool(delivery_manifest.get("ready_for_delivery")),
            qa_score=int(quality_gate.get("score") or 0),
            blocker_count=int(quality_gate.get("blocker_count") or 0),
            warning_count=int(quality_gate.get("warning_count") or 0),
            strongest_slot=slot_eval.get("strongest_slot") or summary.get("strongest_slot"),
            weakest_slot=slot_eval.get("weakest_slot") or summary.get("weakest_slot"),
            average_slot_score=float(summary.get("average_slot_score") or self._average_slot_score(slot_scores)),
            slot_score_span=int(summary.get("slot_score_span") or self._slot_score_span(slot_scores)),
            late_contract_mode=quality_gate.get("late_contract_mode"),
            delivery_package_dir=published.get("delivery_package_dir"),
            delivery_manifest_path=published.get("delivery_manifest_path"),
            delivery_zip_path=published.get("delivery_zip_path"),
        )

    def summarize_candidate(self, published: dict[str, Any]) -> dict[str, Any]:
        candidate = self.candidate_from_published(published)
        return {
            **candidate.as_dict(),
            "recommended_action": self._recommended_action(candidate),
            "selection_reason": self._selection_reason(candidate),
        }

    def choose_best(self, published_candidates: Sequence[dict[str, Any]]) -> dict[str, Any]:
        candidates = [self.candidate_from_published(item) for item in published_candidates]
        if not candidates:
            return {
                "artifact_type": "fsj_main_report_dispatch_decision",
                "artifact_version": "v1",
                "candidate_count": 0,
                "recommended_action": "hold",
                "selected": None,
                "alternatives": [],
                "selection_reason": "no_candidates",
            }

        ready = [candidate for candidate in candidates if candidate.ready_for_delivery]
        pool = ready or list(candidates)
        selected = max(pool, key=lambda item: item.rank_tuple())
        alternatives = [candidate for candidate in sorted(candidates, key=lambda item: item.rank_tuple(), reverse=True) if candidate.artifact_id != selected.artifact_id]
        recommended_action = self._recommended_action(selected)
        return {
            "artifact_type": "fsj_main_report_dispatch_decision",
            "artifact_version": "v1",
            "business_date": selected.business_date,
            "candidate_count": len(candidates),
            "ready_candidate_count": len(ready),
            "recommended_action": recommended_action,
            "selection_reason": self._selection_reason(selected),
            "selected": selected.as_dict(),
            "alternatives": [candidate.as_dict() for candidate in alternatives],
        }

    def _recommended_action(self, candidate: DeliveryDispatchCandidate) -> str:
        if candidate.ready_for_delivery:
            return "send"
        if candidate.late_contract_mode == "historical_only":
            return "hold"
        if candidate.late_contract_mode == "provisional_close_only" or candidate.blocker_count <= 1:
            return "send_review"
        return "hold"

    def _selection_reason(self, candidate: DeliveryDispatchCandidate) -> str:
        if candidate.ready_for_delivery:
            return f"best_ready_candidate strongest_slot={candidate.strongest_slot or '-'} qa_score={candidate.qa_score}"
        if candidate.late_contract_mode == "provisional_close_only":
            return "best_available_candidate provisional_close_only_requires_review"
        return "best_available_candidate blocked_requires_hold"

    def _average_slot_score(self, slot_scores: dict[str, Any]) -> float:
        values = [float(value) for value in slot_scores.values() if value is not None]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 1)

    def _slot_score_span(self, slot_scores: dict[str, Any]) -> int:
        values = [int(value) for value in slot_scores.values() if value is not None]
        if not values:
            return 0
        return max(values) - min(values)
