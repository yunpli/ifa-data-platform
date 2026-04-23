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

    WORKFLOW_VERSION = "v2"

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
        selected_handoff = self._build_selected_handoff(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
            effective_action=effective_action,
        )
        send_manifest = self._build_send_manifest(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
            effective_action=effective_action,
            selected_handoff=selected_handoff,
        )
        review_manifest = self._build_review_manifest(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
            effective_action=effective_action,
            selected_handoff=selected_handoff,
        )
        operator_summary = self._build_operator_summary(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
            effective_action=effective_action,
            selected_handoff=selected_handoff,
        )
        operator_review_bundle = self._build_operator_review_bundle(
            published=published,
            dispatch_decision=dispatch_decision,
            selected_is_current=selected_is_current,
            effective_action=effective_action,
            selected_handoff=selected_handoff,
            send_manifest=send_manifest,
            review_manifest=review_manifest,
        )
        operator_review_readme = self._build_operator_review_readme(operator_review_bundle)

        send_manifest_path = package_dir / "send_manifest.json"
        review_manifest_path = package_dir / "review_manifest.json"
        operator_summary_path = package_dir / "operator_summary.txt"
        operator_review_bundle_path = package_dir / "operator_review_bundle.json"
        operator_review_readme_path = package_dir / "OPERATOR_REVIEW.md"
        workflow_manifest_path = package_dir / "workflow_manifest.json"

        send_manifest_path.write_text(json.dumps(send_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        review_manifest_path.write_text(json.dumps(review_manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        operator_summary_path.write_text(operator_summary, encoding="utf-8")
        operator_review_bundle_path.write_text(json.dumps(operator_review_bundle, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        operator_review_readme_path.write_text(operator_review_readme, encoding="utf-8")

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
            "selected_handoff": selected_handoff,
            "package_artifacts": {
                "delivery_manifest": str(Path(published["delivery_manifest_path"]).resolve()),
                "send_manifest": str(send_manifest_path.resolve()),
                "review_manifest": str(review_manifest_path.resolve()),
                "operator_summary": str(operator_summary_path.resolve()),
                "operator_review_bundle": str(operator_review_bundle_path.resolve()),
                "operator_review_readme": str(operator_review_readme_path.resolve()),
                "package_index": str(Path(published["package_index_path"]).resolve()),
                "package_browse_readme": str(Path(published["package_browse_readme_path"]).resolve()),
                "delivery_zip": str(Path(published["delivery_zip_path"]).resolve()),
                "telegram_caption": str(Path(published["telegram_caption_path"]).resolve()),
            },
            "quality_gate": delivery_manifest.get("quality_gate") or {},
            "slot_evaluation": delivery_manifest.get("slot_evaluation") or {},
            "support_summary_aggregate": delivery_manifest.get("support_summary_aggregate") or {},
            "lineage": delivery_manifest.get("lineage") or {},
            "dispatch_decision": dispatch_decision,
            "review_manifest": review_manifest,
            "send_manifest": send_manifest,
            "operator_review_bundle": operator_review_bundle,
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
            "operator_review_bundle": operator_review_bundle,
            "operator_review_bundle_path": str(operator_review_bundle_path.resolve()),
            "operator_review_readme": operator_review_readme,
            "operator_review_readme_path": str(operator_review_readme_path.resolve()),
            "dispatch_decision": dispatch_decision,
            "selected_handoff": selected_handoff,
        }

    def _build_send_manifest(
        self,
        *,
        published: dict[str, Any],
        dispatch_decision: dict[str, Any],
        selected_is_current: bool,
        effective_action: str,
        selected_handoff: dict[str, Any],
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
        send_blockers = self._send_blockers(
            effective_action=effective_action,
            selected_is_current=selected_is_current,
            ready_for_delivery=current_candidate.ready_for_delivery,
        )
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
            "selected_handoff": selected_handoff,
            "send_blockers": send_blockers,
            "next_step": self._next_step_text(effective_action, selected_is_current, bool(send_blockers)),
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
        selected_handoff: dict[str, Any],
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
        blocking_items = [item for item in checklist if item["status"] == "fail"]
        warning_items = [item for item in checklist if item["status"] == "warn"]
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
            "selected_handoff": selected_handoff,
            "next_step": self._next_step_text(effective_action, selected_is_current, bool(blocking_items)),
            "checklist": checklist,
            "blocking_items": blocking_items,
            "warning_items": warning_items,
        }

    def _build_operator_summary(
        self,
        *,
        published: dict[str, Any],
        dispatch_decision: dict[str, Any],
        selected_is_current: bool,
        effective_action: str,
        selected_handoff: dict[str, Any],
    ) -> str:
        delivery_manifest = dict(published.get("delivery_manifest") or {})
        quality_gate = dict(delivery_manifest.get("quality_gate") or {})
        selected = dict(dispatch_decision.get("selected") or {})
        support_summary = dict(delivery_manifest.get("support_summary_aggregate") or {})
        lines = [
            f"MAIN morning delivery workflow｜{delivery_manifest.get('business_date')}",
            f"recommended_action={effective_action}｜dispatch_action={dispatch_decision.get('recommended_action')}｜selected_is_current={selected_is_current}",
            f"next_step={self._next_step_text(effective_action, selected_is_current, not bool(delivery_manifest.get('ready_for_delivery')))}",
            f"current_artifact_id={delivery_manifest.get('artifact_id')}",
            f"selected_artifact_id={selected.get('artifact_id')}",
            f"selection_reason={dispatch_decision.get('selection_reason')}",
            f"quality_gate score={quality_gate.get('score')} blockers={quality_gate.get('blocker_count')} warnings={quality_gate.get('warning_count')} late_contract_mode={quality_gate.get('late_contract_mode')}",
            f"support_summary domains={','.join(support_summary.get('domains') or []) or '-'} bundles={len(support_summary.get('bundle_ids') or [])} strongest_slot={support_summary.get('strongest_slot') or '-'}",
            f"selected_package_dir={selected_handoff.get('delivery_package_dir')}",
            f"selected_delivery_manifest={selected_handoff.get('delivery_manifest_path')}",
            f"selected_delivery_zip={selected_handoff.get('delivery_zip_path')}",
            f"selected_telegram_caption={selected_handoff.get('telegram_caption_path')}",
            f"delivery_zip={published.get('delivery_zip_path')}",
            f"caption={published.get('telegram_caption_path')}",
            f"package_index={published.get('package_index_path')}",
            f"package_browse_readme={published.get('package_browse_readme_path')}",
        ]
        return "\n".join(str(line) for line in lines) + "\n"

    def _build_operator_review_bundle(
        self,
        *,
        published: dict[str, Any],
        dispatch_decision: dict[str, Any],
        selected_is_current: bool,
        effective_action: str,
        selected_handoff: dict[str, Any],
        send_manifest: dict[str, Any],
        review_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        delivery_manifest = dict(published.get("delivery_manifest") or {})
        current_candidate = self.dispatch_helper.candidate_from_published(published).as_dict()
        alternatives = list(dispatch_decision.get("alternatives") or [])
        package_artifacts = {
            "delivery_package_dir": published.get("delivery_package_dir"),
            "html": published.get("html_path"),
            "delivery_manifest": published.get("delivery_manifest_path"),
            "qa": published.get("qa_path"),
            "evaluation": published.get("eval_path"),
            "report_manifest": published.get("manifest_path"),
            "delivery_zip": published.get("delivery_zip_path"),
            "telegram_caption": published.get("telegram_caption_path"),
            "package_index": published.get("package_index_path"),
            "package_browse_readme": published.get("package_browse_readme_path"),
        }
        artifact_checks = self._build_artifact_checks(package_artifacts)
        return {
            "artifact_type": "fsj_main_report_operator_review_bundle",
            "artifact_version": self.WORKFLOW_VERSION,
            "business_date": delivery_manifest.get("business_date"),
            "report_run_id": delivery_manifest.get("report_run_id"),
            "artifact_id": delivery_manifest.get("artifact_id"),
            "recommended_action": effective_action,
            "workflow_state": send_manifest.get("workflow_state"),
            "selection_reason": dispatch_decision.get("selection_reason"),
            "selected_is_current": selected_is_current,
            "selected_handoff": selected_handoff,
            "dispatch_decision": dispatch_decision,
            "current_candidate": current_candidate,
            "candidate_overview": {
                "candidate_count": dispatch_decision.get("candidate_count"),
                "ready_candidate_count": dispatch_decision.get("ready_candidate_count"),
                "selected_artifact_id": (dispatch_decision.get("selected") or {}).get("artifact_id"),
                "alternative_artifact_ids": [item.get("artifact_id") for item in alternatives],
            },
            "quality_gate": delivery_manifest.get("quality_gate") or {},
            "slot_evaluation": delivery_manifest.get("slot_evaluation") or {},
            "support_summary_aggregate": delivery_manifest.get("support_summary_aggregate") or {},
            "send_manifest": send_manifest,
            "review_manifest": review_manifest,
            "artifact_checks": artifact_checks,
            "operator_go_no_go": self._build_operator_go_no_go(
                selected_is_current=selected_is_current,
                effective_action=effective_action,
                send_manifest=send_manifest,
                review_manifest=review_manifest,
                artifact_checks=artifact_checks,
            ),
            "package_artifacts": package_artifacts,
        }

    def _build_operator_review_readme(self, bundle: dict[str, Any]) -> str:
        selected = dict((bundle.get("dispatch_decision") or {}).get("selected") or {})
        current = dict(bundle.get("current_candidate") or {})
        quality_gate = dict(bundle.get("quality_gate") or {})
        slot_evaluation = dict(bundle.get("slot_evaluation") or {})
        support_summary = dict(bundle.get("support_summary_aggregate") or {})
        send_manifest = dict(bundle.get("send_manifest") or {})
        review_manifest = dict(bundle.get("review_manifest") or {})
        handoff = dict(bundle.get("selected_handoff") or {})
        checklist = list(review_manifest.get("checklist") or [])
        artifact_paths = dict(bundle.get("package_artifacts") or {})
        artifact_checks = list(bundle.get("artifact_checks") or [])
        operator_go_no_go = dict(bundle.get("operator_go_no_go") or {})

        lines = [
            f"# MAIN Operator Review｜{bundle.get('business_date')}",
            "",
            "## Decision",
            f"- recommended_action: `{bundle.get('recommended_action')}`",
            f"- workflow_state: `{bundle.get('workflow_state')}`",
            f"- selection_reason: `{bundle.get('selection_reason')}`",
            f"- selected_is_current: `{bundle.get('selected_is_current')}`",
            f"- current_artifact_id: `{current.get('artifact_id') or '-'}`",
            f"- selected_artifact_id: `{selected.get('artifact_id') or '-'}`",
            "",
            "## Quality Gate",
            f"- score: `{quality_gate.get('score')}`",
            f"- blockers: `{quality_gate.get('blocker_count')}`",
            f"- warnings: `{quality_gate.get('warning_count')}`",
            f"- late_contract_mode: `{quality_gate.get('late_contract_mode') or '-'}`",
            f"- strongest_slot: `{slot_evaluation.get('strongest_slot') or '-'}`",
            f"- weakest_slot: `{slot_evaluation.get('weakest_slot') or '-'}`",
            f"- average_slot_score: `{slot_evaluation.get('average_slot_score')}`",
            "",
            "## Support Summary Aggregate",
            f"- domains: `{', '.join(support_summary.get('domains') or []) or '-'}`",
            f"- bundle_ids: `{', '.join(support_summary.get('bundle_ids') or []) or '-'}`",
            f"- support_summary_count: `{support_summary.get('support_summary_count')}`",
            f"- support_report_link_count: `{support_summary.get('report_link_count')}`",
            "",
            "## Immediate Next Step",
            f"- send_manifest.next_step: `{send_manifest.get('next_step')}`",
            f"- review_manifest.next_step: `{review_manifest.get('next_step')}`",
            f"- send_blockers: `{', '.join(send_manifest.get('send_blockers') or []) or '-'}`",
            "",
            "## Operator Go / No-Go",
            f"- decision: `{operator_go_no_go.get('decision') or '-'}`",
            f"- rationale: `{operator_go_no_go.get('rationale') or '-'}`",
            f"- artifact_integrity_ok: `{operator_go_no_go.get('artifact_integrity_ok')}`",
            f"- missing_artifacts: `{', '.join(operator_go_no_go.get('missing_artifacts') or []) or '-'}`",
            "",
            "## Review Checklist",
        ]
        for item in checklist:
            lines.append(f"- [{item.get('status')}] {item.get('item')}: {item.get('detail')}")

        if artifact_checks:
            lines.extend(["", "## Artifact Integrity"])
            for item in artifact_checks:
                lines.append(
                    f"- [{item.get('status')}] {item.get('artifact')}: exists=`{item.get('exists')}` path=`{item.get('path') or '-'}`"
                )

        lines.extend([
            "",
            "## Selected Handoff",
            f"- delivery_package_dir: `{handoff.get('delivery_package_dir') or '-'}`",
            f"- delivery_manifest_path: `{handoff.get('delivery_manifest_path') or '-'}`",
            f"- delivery_zip_path: `{handoff.get('delivery_zip_path') or '-'}`",
            f"- telegram_caption_path: `{handoff.get('telegram_caption_path') or '-'}`",
            "",
            "## Package Artifacts",
        ])
        for key, value in artifact_paths.items():
            lines.append(f"- {key}: `{value or '-'}`")

        alternatives = list(((bundle.get("dispatch_decision") or {}).get("alternatives") or []))
        if alternatives:
            lines.extend(["", "## Alternative Candidates"])
            for item in alternatives:
                lines.append(
                    "- "
                    f"artifact_id=`{item.get('artifact_id')}` "
                    f"ready=`{item.get('ready_for_delivery')}` "
                    f"qa=`{item.get('qa_score')}` "
                    f"slot=`{item.get('strongest_slot') or '-'}` "
                    f"package=`{item.get('delivery_package_dir') or '-'}`"
                )

        lines.append("")
        return "\n".join(lines)

    def _build_artifact_checks(self, package_artifacts: dict[str, Any]) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        for name, value in package_artifacts.items():
            if name == "delivery_package_dir":
                continue
            path = str(value or "").strip()
            exists = bool(path) and Path(path).exists()
            checks.append({
                "artifact": name,
                "path": path or None,
                "exists": exists,
                "status": "pass" if exists else "fail",
            })
        return checks

    def _build_operator_go_no_go(
        self,
        *,
        selected_is_current: bool,
        effective_action: str,
        send_manifest: dict[str, Any],
        review_manifest: dict[str, Any],
        artifact_checks: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        missing_artifacts = [item["artifact"] for item in artifact_checks if not item.get("exists")]
        artifact_integrity_ok = not missing_artifacts
        review_blocked = bool(review_manifest.get("blocking_items"))
        send_blocked = bool(send_manifest.get("send_blockers"))
        if not selected_is_current:
            decision = "NO_GO"
            rationale = "current package is not the selected dispatch candidate"
        elif not artifact_integrity_ok:
            decision = "NO_GO"
            rationale = "required delivery artifacts are missing"
        elif review_blocked:
            decision = "NO_GO"
            rationale = "review manifest contains blocking items"
        elif effective_action == "send_review" or send_blocked:
            decision = "REVIEW"
            rationale = "manual review is required before sending"
        elif effective_action == "send":
            decision = "GO"
            rationale = "quality gate and artifact integrity both pass"
        else:
            decision = "NO_GO"
            rationale = "workflow recommends hold"
        return {
            "decision": decision,
            "rationale": rationale,
            "artifact_integrity_ok": artifact_integrity_ok,
            "missing_artifacts": missing_artifacts,
        }

    def _build_selected_handoff(
        self,
        *,
        published: dict[str, Any],
        dispatch_decision: dict[str, Any],
        selected_is_current: bool,
        effective_action: str,
    ) -> dict[str, Any]:
        current_delivery_manifest = dict(published.get("delivery_manifest") or {})
        selected = dict(dispatch_decision.get("selected") or {})
        selected_dir = selected.get("delivery_package_dir") or published.get("delivery_package_dir")
        selected_manifest = selected.get("delivery_manifest_path") or published.get("delivery_manifest_path")
        selected_zip = selected.get("delivery_zip_path") or published.get("delivery_zip_path")
        if selected_is_current:
            selected_caption = published.get("telegram_caption_path")
        else:
            selected_caption = None
            if selected_dir:
                candidate = Path(str(selected_dir)) / "telegram_caption.txt"
                if candidate.exists():
                    selected_caption = str(candidate.resolve())
        return {
            "selected_is_current": selected_is_current,
            "effective_action": effective_action,
            "selected_artifact_id": selected.get("artifact_id") or current_delivery_manifest.get("artifact_id"),
            "selected_report_run_id": selected.get("report_run_id") or current_delivery_manifest.get("report_run_id"),
            "selected_business_date": selected.get("business_date") or current_delivery_manifest.get("business_date"),
            "delivery_package_dir": selected_dir,
            "delivery_manifest_path": selected_manifest,
            "delivery_zip_path": selected_zip,
            "telegram_caption_path": selected_caption,
        }

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

    def _send_blockers(self, *, effective_action: str, selected_is_current: bool, ready_for_delivery: bool) -> list[str]:
        blockers: list[str] = []
        if not selected_is_current:
            blockers.append("current_package_not_selected")
        if effective_action == "hold":
            blockers.append("recommended_action_hold")
        if effective_action == "send_review":
            blockers.append("manual_review_required")
        if not ready_for_delivery:
            blockers.append("quality_gate_not_ready")
        return blockers

    def _next_step_text(self, effective_action: str, selected_is_current: bool, has_blockers: bool) -> str:
        if effective_action == "send" and selected_is_current and not has_blockers:
            return "send_selected_package_to_primary_channel"
        if effective_action == "send_review" and selected_is_current:
            return "review_current_package_then_send_if_accepted"
        if not selected_is_current:
            return "switch_to_selected_package_and_do_not_send_current"
        return "hold_and_fix_quality_gate_before_send"

    def _workflow_state(self, recommended_action: str, selected_is_current: bool) -> str:
        if recommended_action == "send" and selected_is_current:
            return "ready_to_send"
        if recommended_action == "send_review" and selected_is_current:
            return "review_required"
        if not selected_is_current:
            return "superseded_by_better_candidate"
        return "hold"
