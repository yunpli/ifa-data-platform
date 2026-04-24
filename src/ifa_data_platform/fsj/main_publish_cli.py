from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .store import FSJStore


@dataclass(frozen=True)
class MainPublishFlowConfig:
    slot: str
    producer_label: str
    summary_name: str
    artifact_type: str
    report_run_id_prefix_default: str
    flow_name: str

    @property
    def section_key(self) -> str:
        return self.slot


def parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_canonical_publish_surface(*, business_date: str, store: FSJStore | None = None) -> dict[str, Any] | None:
    store = store or FSJStore()
    surface = store.get_active_report_delivery_surface(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
    )
    if not surface:
        return None
    return {
        "workflow_handoff": store.report_workflow_handoff_from_surface(surface),
        "operator_review_surface": store.report_operator_review_surface_from_surface(surface),
    }


def build_operator_summary(*, config: MainPublishFlowConfig, business_date: str, generated_at: datetime, persist: dict[str, Any], publish: dict[str, Any] | None) -> str:
    lines = [
        f"FSJ MAIN {config.slot} publish｜{business_date}｜{config.slot}",
        f"generated_at_utc={generated_at.isoformat()}",
        f"persist_status={persist.get('status')}",
        f"publish_status={(publish or {}).get('status') or 'blocked'}",
        "",
        f"- persist: bundle_id={persist.get('bundle_id') or '-'} object_count={persist.get('object_count') or 0} evidence_link_count={persist.get('evidence_link_count') or 0}",
    ]
    if persist.get("reason"):
        lines.append(f"  reason={persist['reason']}")
    if publish:
        workflow_handoff = dict(publish.get("workflow_handoff") or {})
        operator_review_surface = dict(publish.get("operator_review_surface") or {})
        manifest_pointers = dict(workflow_handoff.get("manifest_pointers") or {})
        selected_handoff = dict(workflow_handoff.get("selected_handoff") or {})
        state = dict(workflow_handoff.get("state") or {})
        artifact = dict(workflow_handoff.get("artifact") or publish.get("artifact") or {})
        llm_role_policy = dict(operator_review_surface.get("llm_role_policy") or {})
        llm_lineage_summary = dict(operator_review_surface.get("llm_lineage_summary") or {})
        slot_boundary_modes = dict(llm_role_policy.get("slot_boundary_modes") or {})
        lines.append(
            f"- publish: workflow_state={state.get('workflow_state') or '-'} recommended_action={state.get('recommended_action') or '-'} "
            f"dispatch_recommended_action={state.get('dispatch_recommended_action') or '-'} selected_is_current={selected_handoff.get('selected_is_current')} "
            f"package_state={state.get('package_state') or '-'} artifact_id={artifact.get('artifact_id') or '-'} "
            f"selected_artifact_id={selected_handoff.get('selected_artifact_id') or '-'} dispatch_selected_artifact_id={state.get('dispatch_selected_artifact_id') or '-'} output_dir={publish.get('output_dir') or '-'}"
        )
        lines.append(f"  next_step={state.get('next_step') or '-'} selection_reason={state.get('selection_reason') or '-'}")
        lines.append(
            f"  delivery_manifest_path={manifest_pointers.get('delivery_manifest_path') or '-'} send_manifest_path={manifest_pointers.get('send_manifest_path') or '-'}"
        )
        lines.append(
            f"  llm_lineage_status={llm_lineage_summary.get('status') or '-'} llm_policy_versions={','.join(llm_role_policy.get('policy_versions') or []) or '-'}"
        )
        lines.append(
            f"  llm_boundary_modes={','.join(llm_role_policy.get('boundary_modes') or []) or '-'} llm_override_precedence={'>'.join(llm_role_policy.get('override_precedence') or []) or '-'}"
        )
        lines.append(
            f"  llm_slot_boundary_modes={','.join(f'{slot}:{slot_boundary_modes[slot]}' for slot in sorted(slot_boundary_modes)) or '-'} llm_forbidden_decision_count={len(llm_role_policy.get('forbidden_decisions') or [])}"
        )
        if publish.get("reason"):
            lines.append(f"  reason={publish['reason']}")
    lines.append("")
    return "\n".join(lines)


def build_persist_summary(*, business_date: str, slot: str, persisted: dict[str, Any]) -> dict[str, Any]:
    bundle = dict(persisted.get("bundle") or {})
    return {
        "status": "persisted",
        "business_date": business_date,
        "slot": slot,
        "section_key": bundle.get("section_key"),
        "bundle_id": bundle.get("bundle_id"),
        "bundle_status": bundle.get("status"),
        "object_count": len(persisted.get("objects") or []),
        "edge_count": len(persisted.get("edges") or []),
        "evidence_link_count": len(persisted.get("evidence_links") or []),
        "observed_record_count": len(persisted.get("observed_records") or []),
    }


def run_main_publish_flow(
    *,
    config: MainPublishFlowConfig,
    business_date: str,
    output_root: str | Path,
    generated_at: datetime,
    report_run_id_prefix: str,
    include_empty: bool,
    producer_factory: Callable[[], Any],
    resolve_canonical_surface: Callable[..., dict[str, Any] | None] = resolve_canonical_publish_surface,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")

    publish: dict[str, Any] | None = None
    blocked = False

    try:
        persisted = producer_factory().produce_and_persist(business_date=business_date)
        persist = build_persist_summary(business_date=business_date, slot=config.slot, persisted=persisted)
    except Exception as exc:  # pragma: no cover - exercised by script tests
        blocked = True
        persist = {
            "status": "blocked",
            "business_date": business_date,
            "slot": config.slot,
            "reason": f"{type(exc).__name__}: {exc}",
        }

    if not blocked:
        publish_script = Path(__file__).resolve().parents[3] / "scripts" / "fsj_main_report_publish.py"
        cmd = [
            sys.executable,
            str(publish_script),
            "--business-date", business_date,
            "--output-dir", str(root / "publish"),
            "--generated-at", generated_at.isoformat(),
            "--report-run-id", f"{report_run_id_prefix}:{business_date}:{config.slot}:{stamp}",
        ]
        if include_empty:
            cmd.append("--include-empty")
        completed = subprocess_run(cmd, capture_output=True, text=True)
        stdout = completed.stdout.strip()
        parsed = json.loads(stdout) if stdout else {}
        publish = {
            **parsed,
            "status": "ready" if completed.returncode == 0 else "blocked",
            "output_dir": str((root / "publish").resolve()),
            "exit_code": completed.returncode,
        }
        canonical_surface = resolve_canonical_surface(business_date=business_date)
        if canonical_surface:
            publish.update(canonical_surface)
        if completed.returncode != 0 and not publish.get("reason"):
            publish["reason"] = completed.stderr.strip() or "publish_command_failed"
        blocked = completed.returncode != 0

    summary = {
        "artifact_type": config.artifact_type,
        "artifact_version": "v1",
        "business_date": business_date,
        "slot": config.slot,
        "generated_at_utc": generated_at.isoformat(),
        "persist": persist,
        "publish": publish,
        "status": "blocked" if blocked else "ready",
    }
    summary_path = root / config.summary_name
    operator_summary_path = root / "operator_summary.txt"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    operator_summary_path.write_text(
        build_operator_summary(
            config=config,
            business_date=business_date,
            generated_at=generated_at,
            persist=persist,
            publish=publish,
        ),
        encoding="utf-8",
    )
    return {
        **summary,
        "summary_path": str(summary_path.resolve()),
        "operator_summary_path": str(operator_summary_path.resolve()),
    }
