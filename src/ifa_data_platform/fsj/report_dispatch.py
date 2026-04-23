from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
import json

from .store import FSJStore


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

    def load_active_published_candidate(
        self,
        *,
        business_date: str,
        store: FSJStore | None = None,
    ) -> dict[str, Any] | None:
        store = store or FSJStore()
        surface = store.get_active_report_delivery_surface(
            business_date=business_date,
            agent_domain="main",
            artifact_family="main_final_report",
        )
        if not surface:
            return None
        artifact = dict(surface.get("artifact") or {})
        delivery_package = dict(surface.get("delivery_package") or {})
        if not delivery_package:
            return None
        return {
            "artifact": artifact,
            "delivery_package_dir": delivery_package.get("delivery_package_dir"),
            "delivery_manifest_path": delivery_package.get("delivery_manifest_path"),
            "delivery_zip_path": delivery_package.get("delivery_zip_path"),
            "telegram_caption_path": delivery_package.get("telegram_caption_path"),
            "package_index_path": delivery_package.get("package_index_path"),
            "package_browse_readme_path": delivery_package.get("package_browse_readme_path"),
            "delivery_manifest": {
                "artifact_id": artifact.get("artifact_id"),
                "report_run_id": artifact.get("report_run_id"),
                "business_date": artifact.get("business_date"),
                "artifact_family": artifact.get("artifact_family"),
                "package_state": delivery_package.get("package_state"),
                "ready_for_delivery": delivery_package.get("ready_for_delivery"),
                "quality_gate": dict(delivery_package.get("quality_gate") or {}),
                "slot_evaluation": dict(delivery_package.get("slot_evaluation") or {}),
                "support_summary_aggregate": dict(delivery_package.get("support_summary_aggregate") or {}),
                "dispatch_advice": dict(delivery_package.get("dispatch_advice") or {}),
                "artifacts": dict(delivery_package.get("artifacts") or {}),
            },
            "report_evaluation": {},
            "package_index": {},
            "source": "db_active_delivery_surface",
        }

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

    def load_published_candidate(self, path: str | Path) -> dict[str, Any]:
        input_path = Path(path)
        manifest_path = input_path / "delivery_manifest.json" if input_path.is_dir() else input_path
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        package_dir = manifest_path.parent
        artifact = {
            "artifact_id": payload.get("artifact_id"),
            "report_run_id": payload.get("report_run_id"),
            "business_date": payload.get("business_date"),
            "artifact_family": payload.get("artifact_family"),
        }
        eval_name = str((payload.get("artifacts") or {}).get("evaluation") or "").strip()
        report_evaluation: dict[str, Any] = {}
        if eval_name:
            report_eval_path = package_dir / eval_name
            try:
                report_evaluation = json.loads(report_eval_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                report_evaluation = {}
        caption_path = package_dir / str((payload.get("artifacts") or {}).get("telegram_caption") or "telegram_caption.txt")
        package_index_path = package_dir / str((payload.get("artifacts") or {}).get("package_index") or "package_index.json")
        browse_readme_path = package_dir / str((payload.get("artifacts") or {}).get("browse_readme") or "BROWSE_PACKAGE.md")
        package_index: dict[str, Any] = {}
        if package_index_path.exists():
            try:
                package_index = json.loads(package_index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                package_index = {}
        zip_candidates = sorted(package_dir.parent.glob(f"{package_dir.name}.zip"))
        return {
            "artifact": artifact,
            "delivery_package_dir": str(package_dir.resolve()),
            "delivery_manifest_path": str(manifest_path.resolve()),
            "delivery_zip_path": str(zip_candidates[0].resolve()) if zip_candidates else None,
            "telegram_caption_path": str(caption_path.resolve()) if caption_path.exists() else None,
            "package_index_path": str(package_index_path.resolve()) if package_index_path.exists() else None,
            "package_browse_readme_path": str(browse_readme_path.resolve()) if browse_readme_path.exists() else None,
            "delivery_manifest": payload,
            "report_evaluation": report_evaluation,
            "package_index": package_index,
        }

    def discover_published_candidates(
        self,
        root_dir: str | Path,
        *,
        business_date: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        root = Path(root_dir)
        if not root.exists():
            return []
        manifests = sorted(root.glob("a_share_main_report_delivery_*/delivery_manifest.json"), reverse=True)
        results: list[dict[str, Any]] = []
        for manifest_path in manifests:
            published = self.load_published_candidate(manifest_path)
            candidate_date = (published.get("delivery_manifest") or {}).get("business_date")
            if business_date and candidate_date != business_date:
                continue
            results.append(published)
            if limit is not None and len(results) >= limit:
                break
        return results

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
                "ranked_candidates": [],
                "selection_reason": "no_candidates",
            }

        ready = [candidate for candidate in candidates if candidate.ready_for_delivery]
        pool = ready or list(candidates)
        selected = max(pool, key=lambda item: item.rank_tuple())
        ranked = sorted(candidates, key=lambda item: item.rank_tuple(), reverse=True)
        alternatives = [candidate for candidate in ranked if candidate.artifact_id != selected.artifact_id]
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
            "ranked_candidates": [
                {
                    **candidate.as_dict(),
                    "rank": index,
                    "recommended_action": self._recommended_action(candidate),
                    "selection_reason": self._selection_reason(candidate),
                    "delta_vs_selected": self._delta_vs_selected(selected, candidate),
                }
                for index, candidate in enumerate(ranked, start=1)
            ],
        }

    def build_candidate_comparison(
        self,
        published_candidates: Sequence[dict[str, Any]],
        *,
        selected_artifact_id: str | None = None,
        current_artifact_id: str | None = None,
    ) -> dict[str, Any]:
        decision = self.choose_best(published_candidates)
        ranked = list(decision.get("ranked_candidates") or [])
        selected = dict(decision.get("selected") or {})
        if selected_artifact_id and selected.get("artifact_id") != selected_artifact_id:
            selected = next((item for item in ranked if item.get("artifact_id") == selected_artifact_id), selected)
        current = next((item for item in ranked if item.get("artifact_id") == current_artifact_id), None) if current_artifact_id else None
        current_vs_selected = None
        if current and selected:
            current_vs_selected = {
                "current_artifact_id": current.get("artifact_id"),
                "selected_artifact_id": selected.get("artifact_id"),
                "current_rank": current.get("rank"),
                "selected_rank": selected.get("rank"),
                "delta_current_vs_selected": self._dict_delta(current, selected),
                "delta_selected_vs_current": self._dict_delta(selected, current),
            }
        return {
            "artifact_type": "fsj_main_report_candidate_comparison",
            "artifact_version": "v1",
            "business_date": decision.get("business_date"),
            "candidate_count": decision.get("candidate_count"),
            "ready_candidate_count": decision.get("ready_candidate_count"),
            "selected_artifact_id": selected.get("artifact_id") if selected else None,
            "current_artifact_id": current_artifact_id,
            "ranked_candidates": ranked,
            "current_vs_selected": current_vs_selected,
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

    def _delta_vs_selected(self, selected: DeliveryDispatchCandidate, candidate: DeliveryDispatchCandidate) -> dict[str, Any]:
        if candidate.artifact_id == selected.artifact_id:
            return {
                "selected": True,
                "qa_score_delta": 0,
                "average_slot_score_delta": 0.0,
                "warning_count_delta": 0,
                "blocker_count_delta": 0,
                "slot_score_span_delta": 0,
                "ready_state_change": "same",
                "late_contract_mode_change": "same",
                "strongest_slot_change": "same",
            }
        return {
            "selected": False,
            "qa_score_delta": candidate.qa_score - selected.qa_score,
            "average_slot_score_delta": round(candidate.average_slot_score - selected.average_slot_score, 1),
            "warning_count_delta": candidate.warning_count - selected.warning_count,
            "blocker_count_delta": candidate.blocker_count - selected.blocker_count,
            "slot_score_span_delta": candidate.slot_score_span - selected.slot_score_span,
            "ready_state_change": self._change_label(candidate.ready_for_delivery, selected.ready_for_delivery),
            "late_contract_mode_change": self._change_label(candidate.late_contract_mode, selected.late_contract_mode),
            "strongest_slot_change": self._change_label(candidate.strongest_slot, selected.strongest_slot),
        }

    def _dict_delta(self, baseline: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
        return {
            "qa_score_delta": int(baseline.get("qa_score") or 0) - int(reference.get("qa_score") or 0),
            "average_slot_score_delta": round(float(baseline.get("average_slot_score") or 0.0) - float(reference.get("average_slot_score") or 0.0), 1),
            "warning_count_delta": int(baseline.get("warning_count") or 0) - int(reference.get("warning_count") or 0),
            "blocker_count_delta": int(baseline.get("blocker_count") or 0) - int(reference.get("blocker_count") or 0),
            "slot_score_span_delta": int(baseline.get("slot_score_span") or 0) - int(reference.get("slot_score_span") or 0),
            "ready_for_delivery_change": self._change_label(baseline.get("ready_for_delivery"), reference.get("ready_for_delivery")),
            "late_contract_mode_change": self._change_label(baseline.get("late_contract_mode"), reference.get("late_contract_mode")),
            "strongest_slot_change": self._change_label(baseline.get("strongest_slot"), reference.get("strongest_slot")),
        }

    def _change_label(self, value: Any, reference: Any) -> str:
        return "same" if value == reference else f"{value}->{reference}"
