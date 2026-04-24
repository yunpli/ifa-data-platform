from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .store import FSJStore

OPENCLAW_NODE = "/opt/homebrew/opt/node@24/bin/node"
OPENCLAW_CLI = "/opt/homebrew/lib/node_modules/openclaw/openclaw.mjs"


@dataclass(frozen=True)
class DispatchTarget:
    target: str
    account: str = "main"
    channel: str = "telegram"
    force_document: bool = True
    silent: bool = False


@dataclass(frozen=True)
class DispatchSendResult:
    receipt: dict[str, Any]
    command: list[str]
    raw_stdout: str
    raw_stderr: str
    return_code: int


class OpenClawTelegramDispatchSender:
    """Thin external sender backed by the local OpenClaw CLI."""

    def __init__(
        self,
        *,
        subprocess_run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._subprocess_run = subprocess_run

    def build_send_command(self, *, media_path: str, caption: str, dispatch_target: DispatchTarget) -> list[str]:
        cmd = [
            OPENCLAW_NODE,
            OPENCLAW_CLI,
            "message",
            "send",
            "--channel",
            dispatch_target.channel,
            "--account",
            dispatch_target.account,
            "--target",
            dispatch_target.target,
            "--media",
            media_path,
            "--message",
            caption,
            "--json",
        ]
        if dispatch_target.force_document:
            cmd.append("--force-document")
        if dispatch_target.silent:
            cmd.append("--silent")
        return cmd

    def send_delivery_package(
        self,
        *,
        media_path: str,
        caption: str,
        dispatch_target: DispatchTarget,
    ) -> DispatchSendResult:
        cmd = self.build_send_command(
            media_path=media_path,
            caption=caption,
            dispatch_target=dispatch_target,
        )
        completed = self._subprocess_run(cmd, capture_output=True, text=True, check=False)
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        payload = _loads_json(stdout)
        receipt = self._build_receipt(
            payload=payload,
            dispatch_target=dispatch_target,
            media_path=media_path,
            return_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
        )
        if completed.returncode != 0:
            error_message = receipt.get("error_message") or stderr or stdout or f"openclaw send exited with code {completed.returncode}"
            raise ReportDispatchSendError(
                error_message,
                receipt=receipt,
                command=cmd,
                return_code=completed.returncode,
                stdout=stdout,
                stderr=stderr,
            )
        return DispatchSendResult(
            receipt=receipt,
            command=cmd,
            raw_stdout=stdout,
            raw_stderr=stderr,
            return_code=completed.returncode,
        )

    def _build_receipt(
        self,
        *,
        payload: dict[str, Any] | None,
        dispatch_target: DispatchTarget,
        media_path: str,
        return_code: int,
        stdout: str,
        stderr: str,
    ) -> dict[str, Any]:
        payload = dict(payload or {})
        message_id = _extract_first(payload, ("messageId", "message_id", "id"))
        provider_send_id = _extract_first(payload, ("sendId", "send_id", "messageId", "message_id", "id"))
        error_message = _extract_first(payload, ("error", "message", "detail")) if return_code != 0 else None
        return {
            "provider": "openclaw",
            "provider_channel": dispatch_target.channel,
            "channel": "telegram_document",
            "provider_account": dispatch_target.account,
            "provider_target": dispatch_target.target,
            "provider_message_id": _string_or_none(message_id),
            "provider_send_id": _string_or_none(provider_send_id),
            "provider_return_code": return_code,
            "media_path": media_path,
            "provider_response": payload or None,
            "provider_stdout": stdout or None,
            "provider_stderr": stderr or None,
            "error_message": _string_or_none(error_message),
        }


class ReportDispatchSendError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        receipt: dict[str, Any],
        command: list[str],
        return_code: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(message)
        self.receipt = receipt
        self.command = command
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


class FSJMainReportDispatchService:
    def __init__(
        self,
        *,
        store: FSJStore | None = None,
        sender: OpenClawTelegramDispatchSender | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store or FSJStore()
        self.sender = sender or OpenClawTelegramDispatchSender()
        self.now_factory = now_factory or (lambda: datetime.now(timezone.utc))

    def dispatch_latest_ready_report(
        self,
        *,
        dispatch_target: DispatchTarget,
        strongest_slot: str | None = None,
        max_business_date: str | None = None,
    ) -> dict[str, Any]:
        surface = self.store.get_latest_active_report_operator_review_surface(
            agent_domain="main",
            artifact_family="main_final_report",
            strongest_slot=strongest_slot,
            max_business_date=max_business_date,
        )
        if not surface:
            raise ValueError("no active MAIN report operator review surface found")
        return self.dispatch_surface(surface=surface, dispatch_target=dispatch_target)

    def dispatch_business_date_report(
        self,
        *,
        business_date: str,
        dispatch_target: DispatchTarget,
    ) -> dict[str, Any]:
        surface = self.store.get_active_report_operator_review_surface(
            business_date=business_date,
            agent_domain="main",
            artifact_family="main_final_report",
        )
        if not surface:
            raise ValueError(f"no active MAIN report operator review surface found for business_date={business_date}")
        return self.dispatch_surface(surface=surface, dispatch_target=dispatch_target)

    def dispatch_surface(self, *, surface: dict[str, Any], dispatch_target: DispatchTarget) -> dict[str, Any]:
        artifact = dict(surface.get("artifact") or {})
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        if not artifact_id:
            raise ValueError("surface is missing artifact_id")

        state = dict(surface.get("state") or {})
        selected_handoff = dict(surface.get("selected_handoff") or {})
        go_no_go = dict(surface.get("operator_go_no_go") or {})
        package_paths = dict(surface.get("package_paths") or surface.get("manifest_pointers") or {})

        if selected_handoff.get("selected_is_current") is False:
            raise ValueError("refusing dispatch: current package is not the selected dispatch candidate")
        if state.get("recommended_action") != "send":
            raise ValueError(f"refusing dispatch: recommended_action={state.get('recommended_action')}")
        if not state.get("send_ready"):
            raise ValueError("refusing dispatch: send_ready is false")
        if go_no_go.get("decision") not in {None, "GO"}:
            raise ValueError(f"refusing dispatch: operator_go_no_go={go_no_go.get('decision')}")

        delivery_zip_path = str(package_paths.get("delivery_zip_path") or selected_handoff.get("delivery_zip_path") or "").strip()
        if not delivery_zip_path:
            raise ValueError("surface is missing delivery_zip_path")
        caption_path = str(package_paths.get("telegram_caption_path") or selected_handoff.get("telegram_caption_path") or "").strip()
        if not caption_path:
            raise ValueError("surface is missing telegram_caption_path")

        zip_file = Path(delivery_zip_path)
        caption_file = Path(caption_path)
        if not zip_file.exists():
            raise ValueError(f"delivery zip does not exist: {delivery_zip_path}")
        if not caption_file.exists():
            raise ValueError(f"telegram caption does not exist: {caption_path}")
        caption = caption_file.read_text(encoding="utf-8").strip()

        attempted_at = self.now_factory().astimezone(timezone.utc).isoformat()
        attempted_receipt = {
            "dispatch_state": "dispatch_attempted",
            "attempted_at_utc": attempted_at,
            "provider": "openclaw",
            "provider_channel": dispatch_target.channel,
            "channel": "telegram_document",
            "provider_account": dispatch_target.account,
            "provider_target": dispatch_target.target,
            "delivery_zip_path": str(zip_file.resolve()),
            "telegram_caption_path": str(caption_file.resolve()),
        }
        self.store.persist_report_dispatch_receipt(artifact_id, attempted_receipt)

        try:
            send_result = self.sender.send_delivery_package(
                media_path=str(zip_file.resolve()),
                caption=caption,
                dispatch_target=dispatch_target,
            )
        except ReportDispatchSendError as exc:
            failed_at = self.now_factory().astimezone(timezone.utc).isoformat()
            failed_receipt = {
                **dict(exc.receipt or {}),
                "dispatch_state": "dispatch_failed",
                "attempted_at_utc": attempted_at,
                "failed_at_utc": failed_at,
                "error_class": type(exc).__name__,
                "error_message": str(exc),
                "send_command": exc.command,
            }
            self.store.persist_report_dispatch_receipt(artifact_id, failed_receipt)
            raise

        succeeded_at = self.now_factory().astimezone(timezone.utc).isoformat()
        success_receipt = {
            **dict(send_result.receipt or {}),
            "dispatch_state": "dispatch_succeeded",
            "attempted_at_utc": attempted_at,
            "succeeded_at_utc": succeeded_at,
            "send_command": send_result.command,
        }
        persisted = self.store.persist_report_dispatch_receipt(artifact_id, success_receipt)
        return {
            "artifact_id": artifact_id,
            "business_date": artifact.get("business_date"),
            "dispatch_receipt": success_receipt,
            "persisted_surface": persisted,
        }


def _loads_json(value: str) -> dict[str, Any] | None:
    payload = str(value or "").strip()
    if not payload:
        return None
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else {"value": loaded}


def _extract_first(payload: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(payload, dict):
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        for value in payload.values():
            candidate = _extract_first(value, keys)
            if candidate not in (None, ""):
                return candidate
    elif isinstance(payload, list):
        for item in payload:
            candidate = _extract_first(item, keys)
            if candidate not in (None, ""):
                return candidate
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
