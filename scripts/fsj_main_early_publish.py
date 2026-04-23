#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj import EarlyMainFSJProducer
from ifa_data_platform.fsj.store import FSJStore


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_canonical_publish_surface(*, business_date: str, store: FSJStore | None = None) -> dict | None:
    store = store or FSJStore()
    surface = store.get_active_report_delivery_surface(
        business_date=business_date,
        agent_domain="main",
        artifact_family="main_final_report",
    )
    if not surface:
        return None
    return store.report_workflow_handoff_from_surface(surface)


def _build_operator_summary(*, business_date: str, generated_at: datetime, persist: dict, publish: dict | None) -> str:
    lines = [
        f"FSJ MAIN early publish｜{business_date}｜early",
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
        manifest_pointers = dict(workflow_handoff.get("manifest_pointers") or {})
        selected_handoff = dict(workflow_handoff.get("selected_handoff") or {})
        state = dict(workflow_handoff.get("state") or {})
        artifact = dict(workflow_handoff.get("artifact") or publish.get("artifact") or {})
        lines.append(
            f"- publish: workflow_state={state.get('workflow_state') or '-'} recommended_action={state.get('recommended_action') or '-'} "
            f"dispatch_recommended_action={state.get('dispatch_recommended_action') or '-'} selected_is_current={selected_handoff.get('selected_is_current')} "
            f"package_state={state.get('package_state') or '-'} artifact_id={artifact.get('artifact_id') or '-'} "
            f"selected_artifact_id={selected_handoff.get('selected_artifact_id') or '-'} dispatch_selected_artifact_id={state.get('dispatch_selected_artifact_id') or '-'} output_dir={publish.get('output_dir') or '-'}"
        )
        lines.append(
            f"  next_step={state.get('next_step') or '-'} selection_reason={state.get('selection_reason') or '-'}"
        )
        lines.append(
            f"  delivery_manifest_path={manifest_pointers.get('delivery_manifest_path') or '-'} send_manifest_path={manifest_pointers.get('send_manifest_path') or '-'}"
        )
        if publish.get("reason"):
            lines.append(f"  reason={publish['reason']}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist + publish A-share FSJ early MAIN report through one canonical operator command.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--generated-at", help="ISO8601 timestamp; defaults to current UTC time")
    parser.add_argument("--report-run-id-prefix", default="fsj-main-early")
    parser.add_argument("--include-empty", action="store_true")
    args = parser.parse_args()

    generated_at = _parse_generated_at(args.generated_at) or datetime.now(timezone.utc)
    root = Path(args.output_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")

    persist: dict
    publish: dict | None = None
    blocked = False

    try:
        persisted = EarlyMainFSJProducer().produce_and_persist(business_date=args.business_date)
        bundle = dict(persisted.get("bundle") or {})
        persist = {
            "status": "persisted",
            "business_date": args.business_date,
            "slot": "early",
            "section_key": bundle.get("section_key"),
            "bundle_id": bundle.get("bundle_id"),
            "bundle_status": bundle.get("status"),
            "object_count": len(persisted.get("objects") or []),
            "edge_count": len(persisted.get("edges") or []),
            "evidence_link_count": len(persisted.get("evidence_links") or []),
            "observed_record_count": len(persisted.get("observed_records") or []),
        }
    except Exception as exc:  # pragma: no cover - exercised by script tests
        blocked = True
        persist = {
            "status": "blocked",
            "business_date": args.business_date,
            "slot": "early",
            "reason": f"{type(exc).__name__}: {exc}",
        }

    if not blocked:
        publish_script = Path(__file__).with_name("fsj_main_report_publish.py")
        cmd = [
            sys.executable,
            str(publish_script),
            "--business-date", args.business_date,
            "--output-dir", str(root / "publish"),
            "--generated-at", generated_at.isoformat(),
            "--report-run-id", f"{args.report_run_id_prefix}:{args.business_date}:early:{stamp}",
        ]
        if args.include_empty:
            cmd.append("--include-empty")
        completed = subprocess.run(cmd, capture_output=True, text=True)
        stdout = completed.stdout.strip()
        parsed = json.loads(stdout) if stdout else {}
        publish = {
            **parsed,
            "status": "ready" if completed.returncode == 0 else "blocked",
            "output_dir": str((root / "publish").resolve()),
            "exit_code": completed.returncode,
        }
        canonical_workflow_handoff = _resolve_canonical_publish_surface(business_date=args.business_date)
        if canonical_workflow_handoff:
            publish["workflow_handoff"] = canonical_workflow_handoff
        if completed.returncode != 0 and not publish.get("reason"):
            publish["reason"] = completed.stderr.strip() or "publish_command_failed"
        blocked = completed.returncode != 0

    summary = {
        "artifact_type": "fsj_main_early_publish_summary",
        "artifact_version": "v1",
        "business_date": args.business_date,
        "slot": "early",
        "generated_at_utc": generated_at.isoformat(),
        "persist": persist,
        "publish": publish,
        "status": "blocked" if blocked else "ready",
    }
    summary_path = root / "main_early_publish_summary.json"
    operator_summary_path = root / "operator_summary.txt"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    operator_summary_path.write_text(
        _build_operator_summary(business_date=args.business_date, generated_at=generated_at, persist=persist, publish=publish),
        encoding="utf-8",
    )
    print(json.dumps({**summary, "summary_path": str(summary_path.resolve()), "operator_summary_path": str(operator_summary_path.resolve())}, ensure_ascii=False, indent=2, default=str))
    if blocked:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
