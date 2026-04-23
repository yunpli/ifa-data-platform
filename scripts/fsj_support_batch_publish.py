#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ifa_data_platform.fsj.store import FSJStore

VALID_DOMAINS = ["macro", "commodities", "ai_tech"]


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resolve_canonical_publish_surface(*, business_date: str, agent_domain: str, store: FSJStore | None = None) -> dict | None:
    store = store or FSJStore()
    surface = store.get_active_report_delivery_surface(
        business_date=business_date,
        agent_domain=agent_domain,
        artifact_family="support_domain_report",
    )
    if not surface:
        return None
    return {
        "delivery_surface": surface,
        "workflow_handoff": store.report_workflow_handoff_from_surface(surface),
    }


def _build_operator_summary(*, business_date: str, slot: str, generated_at: datetime, results: list[dict]) -> str:
    ready = [item for item in results if item["status"] == "ready" and item.get("package_state", "ready") == "ready"]
    blocked = [item for item in results if item not in ready]
    lines = [
        f"FSJ support batch publish｜{business_date}｜{slot}",
        f"generated_at_utc={generated_at.isoformat()}",
        f"ready={len(ready)}｜blocked={len(blocked)}｜domains={len(results)}",
        "",
    ]
    for item in results:
        workflow_handoff = dict(item.get("workflow_handoff") or {})
        manifest_pointers = dict(workflow_handoff.get("manifest_pointers") or {})
        selected_handoff = dict(workflow_handoff.get("selected_handoff") or {})
        state = dict(workflow_handoff.get("state") or {})
        artifact = dict(workflow_handoff.get("artifact") or item.get("artifact") or {})
        lines.append(
            f"- {item['agent_domain']}: status={item['status']} bundle_id={item.get('bundle_id') or '-'} "
            f"package_state={item.get('package_state') or '-'} workflow_state={state.get('workflow_state') or '-'} "
            f"recommended_action={state.get('recommended_action') or '-'} dispatch_recommended_action={state.get('dispatch_recommended_action') or '-'} "
            f"selected_is_current={selected_handoff.get('selected_is_current')} artifact_id={artifact.get('artifact_id') or '-'} "
            f"selected_artifact_id={selected_handoff.get('selected_artifact_id') or '-'} dispatch_selected_artifact_id={state.get('dispatch_selected_artifact_id') or '-'} output_dir={item.get('output_dir') or '-'}"
        )
        lines.append(
            f"  next_step={state.get('next_step') or '-'} selection_reason={state.get('selection_reason') or '-'}"
        )
        if manifest_pointers:
            lines.append(
                f"  delivery_manifest_path={manifest_pointers.get('delivery_manifest_path') or '-'} send_manifest_path={manifest_pointers.get('send_manifest_path') or '-'}"
            )
        if item.get("reason"):
            lines.append(f"  reason={item['reason']}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-publish A-share FSJ support artifacts for one slot/date into one operator-facing output root.")
    parser.add_argument("--business-date", required=True)
    parser.add_argument("--slot", required=True, choices=["early", "late"])
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--agent-domain", action="append", dest="agent_domains", choices=VALID_DOMAINS, help="Repeat to limit domains; defaults to all three support domains")
    parser.add_argument("--generated-at", help="ISO8601 timestamp; defaults to current UTC time")
    parser.add_argument("--report-run-id-prefix", default="fsj-support-batch")
    parser.add_argument("--require-ready", action="store_true", help="Treat missing/non-ready persisted bundle as blocking")
    args = parser.parse_args()

    generated_at = _parse_generated_at(args.generated_at) or datetime.now(timezone.utc)
    domains = args.agent_domains or list(VALID_DOMAINS)
    root = Path(args.output_root)
    root.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    persist_script = Path(__file__).with_name("fsj_support_bundle_persist.py")
    publish_script = Path(__file__).with_name("fsj_support_report_publish.py")
    python_bin = sys.executable
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")

    persist_root = root / "persist"
    persist_cmd = [
        python_bin,
        str(persist_script),
        "--business-date", args.business_date,
        "--slot", args.slot,
        "--output-root", str(persist_root),
    ]
    for domain in domains:
        persist_cmd.extend(["--agent-domain", domain])
    persist_completed = subprocess.run(persist_cmd, capture_output=True, text=True)
    persist_stdout = persist_completed.stdout.strip()
    persist_summary = json.loads(persist_stdout) if persist_stdout else {}

    for domain in domains:
        domain_dir = root / domain
        cmd = [
            python_bin,
            str(publish_script),
            "--business-date", args.business_date,
            "--agent-domain", domain,
            "--slot", args.slot,
            "--output-dir", str(domain_dir),
            "--generated-at", generated_at.isoformat(),
            "--report-run-id", f"{args.report_run_id_prefix}:{args.business_date}:{args.slot}:{domain}:{stamp}",
        ]
        if args.require_ready:
            cmd.append("--require-ready")
        completed = subprocess.run(cmd, capture_output=True, text=True)
        stdout = completed.stdout.strip()
        parsed = json.loads(stdout) if stdout else {}
        item = {
            "agent_domain": domain,
            "output_dir": str(domain_dir.resolve()),
            "exit_code": completed.returncode,
        }
        item.update(parsed)
        item["status"] = parsed.get("status") or ("ready" if completed.returncode == 0 else "blocked")
        canonical_surface = _resolve_canonical_publish_surface(
            business_date=args.business_date,
            agent_domain=domain,
        )
        if canonical_surface:
            item.update(canonical_surface)
        delivery_surface = dict(item.get("delivery_surface") or {})
        delivery_package = dict(delivery_surface.get("delivery_package") or {})
        manifest_pointers = dict((item.get("workflow_handoff") or {}).get("manifest_pointers") or {})
        state = dict((item.get("workflow_handoff") or {}).get("state") or {})
        item["bundle_id"] = (
            dict(delivery_package.get("lineage") or {}).get("bundle_id")
            or ((parsed.get("bundle") or {}).get("bundle_id") if isinstance(parsed.get("bundle"), dict) else None)
            or ((parsed.get("delivery_manifest") or {}).get("lineage") or {}).get("bundle_id")
        )
        item["package_state"] = state.get("package_state") or delivery_package.get("package_state") or (parsed.get("delivery_manifest") or {}).get("package_state")
        item["delivery_manifest_path"] = manifest_pointers.get("delivery_manifest_path") or parsed.get("delivery_manifest_path")
        item["send_manifest_path"] = manifest_pointers.get("send_manifest_path")
        if completed.returncode != 0 and not item.get("reason"):
            item["reason"] = (completed.stderr.strip() or "publish_command_failed")
        results.append(item)

    summary = {
        "artifact_type": "fsj_support_batch_publish_summary",
        "artifact_version": "v2",
        "business_date": args.business_date,
        "slot": args.slot,
        "generated_at_utc": generated_at.isoformat(),
        "domains": domains,
        "require_ready": bool(args.require_ready),
        "persist": {
            **persist_summary,
            "exit_code": persist_completed.returncode,
        },
        "ready_count": sum(1 for item in results if item["status"] == "ready" and item.get("package_state", "ready") == "ready"),
        "blocked_count": sum(1 for item in results if item["status"] != "ready" or item.get("package_state") == "blocked"),
        "results": results,
    }
    summary_path = root / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    operator_summary = _build_operator_summary(business_date=args.business_date, slot=args.slot, generated_at=generated_at, results=results)
    operator_summary_path = root / "operator_summary.txt"
    operator_summary_path.write_text(operator_summary, encoding="utf-8")
    print(json.dumps({**summary, "summary_path": str(summary_path.resolve()), "operator_summary_path": str(operator_summary_path.resolve())}, ensure_ascii=False, indent=2, default=str))

    if summary["blocked_count"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
