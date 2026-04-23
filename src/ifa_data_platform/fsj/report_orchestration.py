from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
import json

from .report_dispatch import MainReportDeliveryDispatchHelper
from .report_rendering import MainReportArtifactPublishingService


@dataclass(frozen=True)
class MainReportWorkflowCandidate:
    published: dict[str, Any]
    source: str


class MainReportMorningDeliveryOrchestrator:
    """Single-call workflow for MAIN package + eval + dispatch + review/send manifests."""

    WORKFLOW_VERSION = "v1"

    def __init__(
        self,
        publisher: MainReportArtifactPublishingService,
        dispatch_helper: MainReportDeliveryDispatchHelper | None = None,
    ) -> None:
        self.publisher = publisher
        self.dispatch_helper = dispatch_helper or MainReportDeliveryDispatchHelper()

    def run_workflow(
        self,
        *,
        business_date: str,
        output_dir: str | Path,
        include_empty: bool = False,
        report_run_id: str | None = None,
        generated_at: datetime | None = None,
        comparison_candidates: Sequence[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        published = self.publisher.publish_delivery_package(
            business_date=business_date,
            output_dir=output_dir,
            include_empty=include_empty,
            report_run_id=report_run_id,
            generated_at=generated_at,
        )
        candidates = [published, *(comparison_candidates or [])]
        dispatch_decision = self.dispatch_helper.choose_best(candidates)

        package_dir = Path(published["delivery_package_dir"])
        delivery_manifest = dict(published.get("delivery_manifest") or {})
        dispatch_selected = dict(dispatch_decision.get("selected") or {})
        selected_artifact_id = dispatch_selected.get("artifact_id")
        active_artifact_id = delivery_manifest.get("artifact_id")
        selected_is_current = bool(selected_artifact_id and selected_artifact_id == active_artifact_id)

        effective_action = self._effective_action(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
        )
        send_manifest = self._build_send_manifest(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
            effective_action=effective_action,
        )
        review_manifest = self._build_review_manifest(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
            effective_action=effective_action,
        )
        operator_summary = self._build_operator_summary(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
            effective_action=effective_action,
        )

        send_manifest_path = package_dir / "send_manifest.json"
        review_manifest_path = package_dir / "review_manifest.json"
        operator_summary_path = package_dir / "operator_summary.txt"
        workflow_manifest_path = package_dir / "workflow_manifest.json"

        send_manifest_path.write_text(json.dumps(send_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        review_manifest_path.write_text(json.dumps(review_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        operator_summary_path.write_text(operator_summary, encoding="utf-8")

        workflow_manifest = {
            "artifact_type": "fsj_main_report_delivery_workflow",
            "artifact_version": self.WORKFLOW_VERSION,
            "business_date": business_date,
            "generated_at_utc": generated_at.isoformat(),
            "workflow_state": send_manifest["workflow_state"],
            "recommended_action": effective_action,
            "dispatch_recommended_action": dispatch_decision.get("recommended_action"),
            "selected_candidate": dispatch_selected,
            "selected_is_current": selected_is_current,
            "current_candidate": self.dispatch_helper.candidate_from_published(published).as_dict(),
            "package_artifacts": {
                "delivery_manifest": str(Path(published["delivery_manifest_path"]).resolve()),
                "send_manifest": str(send_manifest_path.resolve()),
                "review_manifest": str(review_manifest_path.resolve()),
                "operator_summary": str(operator_summary_path.resolve()),
                "delivery_zip": str(Path(published["delivery_zip_path"]).resolve()),
                "telegram_caption": str(Path(published["telegram_caption_path"]).resolve()),
            },
            "quality_gate": delivery_manifest.get("quality_gate") or {},
            "slot_evaluation": delivery_manifest.get("slot_evaluation") or {},
            "lineage": delivery_manifest.get("lineage") or {},
            "dispatch_decision": dispatch_decision,
            "review_manifest": review_manifest,
            "send_manifest": send_manifest,
        }
        workflow_manifest_path.write_text(json.dumps(workflow_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        return {
            **published,
            "workflow_manifest": workflow_manifest,
            "workflow_manifest_path": str(workflow_manifest_path.resolve()),
            "send_manifest": send_manifest,
            "send_manifest_path": str(send_manifest_path.resolve()),
            "review_manifest": review_manifest,
            "review_manifest_path": str(review_manifest_path.resolve()),
            "operator_summary": operator_summary,
            "operator_summary_path": str(operator_summary_path.resolve()),
            "dispatch_decision": dispatch_decision,
        }

    def _build_send_manifest(
        self,
        *,
        published: dict[str, Any],
        dispatch_decision: dict[str, Any],
        selected_is_current: bool,
        effective_action: str,
    ) -> dict[str, Any]:
        delivery_manifest = dict(published.get("delivery_manifest") or {})
        dispatch_recommended_action = str(dispatch_decision.get("recommended_action") or "hold")
        current_candidate = self.dispatch_helper.candidate_from_published(published)
        attachments = {
            "html": published.get("html_path"),
            "delivery_zip": published.get("delivery_zip_path"),
            "delivery_manifest": published.get("delivery_manifest_path"),
            "review_manifest": str(Path(published["delivery_package_dir"]) / "review_manifest.json"),
            "telegram_caption": published.get("telegram_caption_path"),
        }
        return {
            "artifact_type": "fsj_main_report_send_manifest",
            "artifact_version": self.WORKFLOW_VERSION,
            "artifact_id": delivery_manifest.get("artifact_id"),
            "business_date": delivery_manifest.get("business_date"),
            "report_run_id": delivery_manifest.get("report_run_id"),
            "workflow_state": self._workflow_state(effective_action, selected_is_current),
            "recommended_action": effective_action,
            "dispatch_recommended_action": dispatch_recommended_action,
            "selected_is_current": selected_is_current,
            "ready_for_delivery": current_candidate.ready_for_delivery,
            "dispatch_selected_artifact_id": (dispatch_decision.get("selected") or {}).get("artifact_id"),
            "channel_plan": {
                "primary_channel": "telegram_document",
                "caption_path": published.get("telegram_caption_path"),
                "attachments": attachments,
            },
            "quality_gate": delivery_manifest.get("quality_gate") or {},
            "selection_reason": dispatch_decision.get("selection_reason"),
        }

    def _build_review_manifest(
        self,
        *,
        published: dict[str, Any],
        dispatch_decision: dict[str, Any],
        selected_is_current: bool,
        effective_action: str,
    ) -> dict[str, Any]:
        delivery_manifest = dict(published.get("delivery_manifest") or {})
        quality_gate = dict(delivery_manifest.get("quality_gate") or {})
        dispatch_recommended_action = str(dispatch_decision.get("recommended_action") or "hold")
        checklist = [
            {
                "item": "confirm_selected_candidate",
                "status": "pass" if selected_is_current else "warn",
                "detail": "current package is selected for dispatch" if selected_is_current else "dispatch helper selected a different candidate; do not auto-send current package",
            },
            {
                "item": "quality_gate_ready_for_delivery",
                "status": "pass" if delivery_manifest.get("ready_for_delivery") else "fail",
                "detail": f"package_state={delivery_manifest.get('package_state')} score={quality_gate.get('score')}",
            },
            {
                "item": "late_contract_mode",
                "status": "pass" if quality_gate.get("late_contract_mode") == "full_close_package" else "warn",
                "detail": f"late_contract_mode={quality_gate.get('late_contract_mode')}",
            },
            {
                "item": "dispatch_recommendation",
                "status": "pass" if effective_action == "send" and selected_is_current else "warn",
                "detail": f"effective_action={effective_action} dispatch_action={dispatch_recommended_action}",
            },
        ]
        return {
            "artifact_type": "fsj_main_report_review_manifest",
            "artifact_version": self.WORKFLOW_VERSION,
            "artifact_id": delivery_manifest.get("artifact_id"),
            "business_date": delivery_manifest.get("business_date"),
            "report_run_id": delivery_manifest.get("report_run_id"),
            "recommended_action": effective_action,
            "dispatch_recommended_action": dispatch_recommended_action,
            "selected_is_current": selected_is_current,
            "selection_reason": dispatch_decision.get("selection_reason"),
            "checklist": checklist,
            "blocking_items": [item for item in checklist if item["status"] == "fail"],
            "warning_items": [item for item in checklist if item["status"] == "warn"],
        }

    def _build_operator_summary(
        self,
        *,
        published: dict[str, Any],
        dispatch_decision: dict[str, Any],
        selected_is_current: bool,
        effective_action: str,
    ) -> str:
        delivery_manifest = dict(published.get("delivery_manifest") or {})
        quality_gate = dict(delivery_manifest.get("quality_gate") or {})
        selected = dict(dispatch_decision.get("selected") or {})
        lines = [
            f"MAIN morning delivery workflow｜{delivery_manifest.get('business_date')}",
            f"recommended_action={effective_action}｜dispatch_action={dispatch_decision.get('recommended_action')}｜selected_is_current={selected_is_current}",
            f"current_artifact_id={delivery_manifest.get('artifact_id')}",
            f"selected_artifact_id={selected.get('artifact_id')}",
            f"selection_reason={dispatch_decision.get('selection_reason')}",
            f"quality_gate score={quality_gate.get('score')} blockers={quality_gate.get('blocker_count')} warnings={quality_gate.get('warning_count')} late_contract_mode={quality_gate.get('late_contract_mode')}",
            f"delivery_zip={published.get('delivery_zip_path')}",
            f"caption={published.get('telegram_caption_path')}",
        ]
        return "\n".join(str(line) for line in lines) + "\n"

    def _effective_action(
        self,
        *,
        published: dict[str, Any],
        dispatch_decision: dict[str, Any],
        selected_is_current: bool,
    ) -> str:
        dispatch_action = str(dispatch_decision.get("recommended_action") or "hold")
        if not selected_is_current:
            return "hold"
        quality_gate = dict((published.get("delivery_manifest") or {}).get("quality_gate") or {})
        if quality_gate.get("late_contract_mode") == "provisional_close_only":
            return "send_review"
        return dispatch_action

    def _workflow_state(self, recommended_action: str, selected_is_current: bool) -> str:
        if recommended_action == "send" and selected_is_current:
            return "ready_to_send"
        if recommended_action == "send_review" and selected_is_current:
            return "review_required"
        if not selected_is_current:
            return "superseded_by_better_candidate"
        return "hold"
