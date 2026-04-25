#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
VALID_MAIN_SLOTS = ("early", "mid", "late")
VALID_SUPPORT_SLOTS = ("early", "late")
VALID_SUPPORT_DOMAINS = ("macro", "commodities", "ai_tech")
VALID_MODES = ("realtime", "replay", "backfill-test", "dry-run")
VALID_OUTPUT_PROFILES = ("internal", "review", "customer")


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _run_json(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, capture_output=True, text=True)
    stdout = completed.stdout.strip()
    payload: dict[str, Any]
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = {"raw_stdout": stdout}
    else:
        payload = {}
    if completed.returncode != 0:
        payload.setdefault("reason", completed.stderr.strip() or "command_failed")
    return {
        "command": cmd,
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": completed.stderr.strip(),
        "payload": payload,
    }


def _mode_output_root(output_root: str, *, business_date: str, slot: str, subject: str, mode: str) -> Path:
    root = Path(output_root)
    if mode == "realtime":
        return root
    safe_mode = mode.replace("-", "_")
    return root / f"{subject}_{slot}_{business_date}_{safe_mode}"


def _validate_mode_and_profile(*, mode: str, output_profile: str) -> list[str]:
    notes: list[str] = []
    if mode != "realtime":
        notes.append(
            "current_chain_has_no_native_mode_switch; canonical CLI treats mode as operator intent + isolated output-root routing only"
        )
    if output_profile == "review":
        notes.append(
            "review profile currently resolves to existing package/operator-review surfaces; no dedicated alternate renderer is introduced here"
        )
    if output_profile == "customer":
        notes.append(
            "customer profile now uses a presentation-layer projection that strips engineering-visible fields from rendered HTML while preserving the underlying assembly/orchestration chain"
        )
    return notes


def cmd_generate(args: argparse.Namespace) -> None:
    notes = _validate_mode_and_profile(mode=args.mode, output_profile=args.output_profile)
    generated_at = _parse_generated_at(args.generated_at) or datetime.now(timezone.utc)
    effective_output_root = _mode_output_root(
        args.output_root,
        business_date=args.business_date,
        slot=args.slot,
        subject=args.subject,
        mode=args.mode,
    )
    effective_output_root.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any]
    if args.subject == "main":
        if args.slot not in VALID_MAIN_SLOTS:
            raise SystemExit(f"main slot must be one of {', '.join(VALID_MAIN_SLOTS)}")
        if args.main_flow == "morning-delivery":
            cmd = [
                sys.executable,
                str(ROOT / "fsj_main_report_morning_delivery.py"),
                "--business-date", args.business_date,
                "--output-dir", str(effective_output_root),
                "--generated-at", generated_at.isoformat(),
            ]
            if args.report_run_id_prefix:
                cmd.extend([
                    "--report-run-id",
                    f"{args.report_run_id_prefix}:{args.business_date}:{args.slot}:{generated_at.strftime('%Y%m%dT%H%M%SZ')}",
                ])
            if args.include_empty:
                cmd.append("--include-empty")
            notes.append("main_flow=morning-delivery uses existing morning delivery orchestrator; slot is recorded for operator intent only")
            result = _run_json(cmd)
        else:
            script_name = {
                "early": "fsj_main_early_publish.py",
                "mid": "fsj_main_mid_publish.py",
                "late": "fsj_main_late_publish.py",
            }[args.slot]
            cmd = [
                sys.executable,
                str(ROOT / script_name),
                "--business-date", args.business_date,
                "--output-root", str(effective_output_root),
                "--generated-at", generated_at.isoformat(),
            ]
            if args.report_run_id_prefix:
                cmd.extend(["--report-run-id-prefix", args.report_run_id_prefix])
            if args.include_empty:
                cmd.append("--include-empty")
            cmd.extend(["--output-profile", args.output_profile])
            result = _run_json(cmd)
    else:
        if args.slot not in VALID_SUPPORT_SLOTS:
            raise SystemExit(f"support slot must be one of {', '.join(VALID_SUPPORT_SLOTS)}")
        cmd = [
            sys.executable,
            str(ROOT / "fsj_support_batch_publish.py"),
            "--business-date", args.business_date,
            "--slot", args.slot,
            "--output-root", str(effective_output_root),
            "--generated-at", generated_at.isoformat(),
        ]
        if args.report_run_id_prefix:
            cmd.extend(["--report-run-id-prefix", args.report_run_id_prefix])
        cmd.extend(["--output-profile", args.output_profile])
        domains = args.agent_domain or list(VALID_SUPPORT_DOMAINS)
        for domain in domains:
            cmd.extend(["--agent-domain", domain])
        if args.require_ready:
            cmd.append("--require-ready")
        if args.html_only:
            raise SystemExit("support batch wrapper does not support --html-only; use scripts/fsj_support_report_publish.py directly for single-domain HTML-only output")
        result = _run_json(cmd)

    payload = {
        "artifact_type": "fsj_report_cli_result",
        "artifact_version": "v1",
        "command_group": "generate",
        "subject": args.subject,
        "business_date": args.business_date,
        "slot": args.slot,
        "mode": args.mode,
        "output_profile": args.output_profile,
        "main_flow": args.main_flow if args.subject == "main" else None,
        "agent_domains": args.agent_domain if args.subject == "support" else None,
        "generated_at_utc": generated_at.isoformat(),
        "effective_output_root": str(effective_output_root.resolve()),
        "notes": notes,
        "wrapped_result": result,
        "status": "ready" if result["exit_code"] == 0 else "blocked",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    if result["exit_code"] != 0:
        raise SystemExit(result["exit_code"])


def cmd_status(args: argparse.Namespace) -> None:
    if args.subject == "main":
        cmd = [sys.executable, str(ROOT / "fsj_main_delivery_status.py")]
        if args.latest:
            cmd.append("--latest")
        else:
            cmd.extend(["--business-date", args.business_date])
        if args.slot:
            cmd.extend(["--slot", args.slot])
    elif args.subject == "support":
        cmd = [
            sys.executable,
            str(ROOT / "fsj_support_delivery_status.py"),
            "--agent-domain", args.agent_domain,
        ]
        if args.latest:
            cmd.append("--latest")
        else:
            cmd.extend(["--business-date", args.business_date])
        if args.slot:
            cmd.extend(["--slot", args.slot])
    else:
        cmd = [sys.executable, str(ROOT / "fsj_operator_board.py")]
        if args.latest:
            cmd.append("--latest")
        elif args.business_date:
            cmd.extend(["--business-date", args.business_date])
    cmd.extend(["--history-limit", str(args.history_limit), "--format", args.format])
    result = _run_json(cmd)
    payload = {
        "artifact_type": "fsj_report_cli_status_result",
        "artifact_version": "v1",
        "command_group": "status",
        "subject": args.subject,
        "business_date": args.business_date,
        "latest": bool(args.latest),
        "slot": args.slot,
        "agent_domain": args.agent_domain,
        "history_limit": args.history_limit,
        "format": args.format,
        "wrapped_result": result,
        "status": "ready" if result["exit_code"] == 0 else "blocked",
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        if result["stdout"]:
            print(result["stdout"])
    if result["exit_code"] != 0:
        raise SystemExit(result["exit_code"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Minimal canonical FSJ report control CLI wrapping existing publish/delivery/status entrypoints without rewriting the main chain."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate/publish main or support report artifacts through one canonical wrapper")
    generate.add_argument("--subject", required=True, choices=["main", "support"])
    generate.add_argument("--business-date", required=True)
    generate.add_argument("--slot", required=True, choices=sorted(set(VALID_MAIN_SLOTS) | set(VALID_SUPPORT_SLOTS)))
    generate.add_argument("--mode", default="realtime", choices=VALID_MODES)
    generate.add_argument("--output-profile", default="internal", choices=VALID_OUTPUT_PROFILES)
    generate.add_argument("--output-root", required=True)
    generate.add_argument("--generated-at")
    generate.add_argument("--report-run-id-prefix")
    generate.add_argument("--include-empty", action="store_true")
    generate.add_argument("--main-flow", default="publish", choices=["publish", "morning-delivery"])
    generate.add_argument("--agent-domain", action="append", choices=VALID_SUPPORT_DOMAINS, help="Repeat to limit support domains; default is all support domains")
    generate.add_argument("--require-ready", action="store_true", help="Support-only: fail if persisted support bundles are not ready")
    generate.add_argument("--html-only", action="store_true", help="Reserved for future single-domain support wrapper alignment; currently unsupported in batch mode")
    generate.set_defaults(func=cmd_generate)

    status = subparsers.add_parser("status", help="Read delivery/operator status through one canonical wrapper")
    status.add_argument("--subject", required=True, choices=["main", "support", "board"])
    target = status.add_mutually_exclusive_group(required=False)
    target.add_argument("--business-date")
    target.add_argument("--latest", action="store_true")
    status.add_argument("--slot", choices=sorted(set(VALID_MAIN_SLOTS) | set(VALID_SUPPORT_SLOTS)))
    status.add_argument("--agent-domain", choices=VALID_SUPPORT_DOMAINS)
    status.add_argument("--history-limit", type=int, default=5)
    status.add_argument("--format", choices=["text", "json"], default="json")
    status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "status":
        if args.subject == "support" and not args.agent_domain:
            raise SystemExit("--agent-domain is required when --subject support")
        if args.subject in {"main", "support"} and not args.latest and not args.business_date:
            raise SystemExit("provide --business-date or --latest")
    args.func(args)


if __name__ == "__main__":
    main()
