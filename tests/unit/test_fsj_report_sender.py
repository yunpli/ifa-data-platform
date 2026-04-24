from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from ifa_data_platform.fsj.report_sender import (
    DispatchTarget,
    FSJMainReportDispatchService,
    OpenClawTelegramDispatchSender,
    ReportDispatchSendError,
)


class StubStore:
    def __init__(self, surface: dict[str, object]) -> None:
        self.surface = surface
        self.persist_calls: list[tuple[str, dict[str, object]]] = []

    def get_active_report_operator_review_surface(self, **_: object) -> dict[str, object]:
        return self.surface

    def get_latest_active_report_operator_review_surface(self, **_: object) -> dict[str, object]:
        return self.surface

    def persist_report_dispatch_receipt(self, artifact_id: str, dispatch_receipt: dict[str, object]) -> dict[str, object]:
        snapshot = dict(dispatch_receipt)
        self.persist_calls.append((artifact_id, snapshot))
        return {"artifact_id": artifact_id, "dispatch_receipt": snapshot}


def _surface(tmp_path: Path) -> dict[str, object]:
    zip_path = tmp_path / "pkg.zip"
    zip_path.write_text("zip", encoding="utf-8")
    caption_path = tmp_path / "telegram_caption.txt"
    caption_path.write_text("hello world", encoding="utf-8")
    return {
        "artifact": {
            "artifact_id": "artifact-123",
            "business_date": "2026-04-23",
        },
        "state": {
            "recommended_action": "send",
            "send_ready": True,
        },
        "selected_handoff": {
            "selected_is_current": True,
            "delivery_zip_path": str(zip_path),
            "telegram_caption_path": str(caption_path),
        },
        "operator_go_no_go": {"decision": "GO"},
        "package_paths": {
            "delivery_zip_path": str(zip_path),
            "telegram_caption_path": str(caption_path),
        },
    }


def test_dispatch_service_persists_attempt_then_success(tmp_path: Path) -> None:
    store = StubStore(_surface(tmp_path))

    class StubSender:
        def send_delivery_package(self, *, media_path: str, caption: str, dispatch_target: DispatchTarget):
            assert media_path.endswith("pkg.zip")
            assert caption == "hello world"
            assert dispatch_target.target == "1628724839"
            return type("SendResult", (), {
                "receipt": {
                    "provider": "openclaw",
                    "provider_channel": "telegram",
                    "channel": "telegram_document",
                    "provider_message_id": "msg-42",
                    "provider_send_id": "send-42",
                },
                "command": ["openclaw", "message", "send"],
                "raw_stdout": '{"messageId":"msg-42"}',
                "raw_stderr": "",
                "return_code": 0,
            })()

    service = FSJMainReportDispatchService(
        store=store,  # type: ignore[arg-type]
        sender=StubSender(),  # type: ignore[arg-type]
        now_factory=lambda: datetime(2026, 4, 24, 4, 0, tzinfo=timezone.utc),
    )

    result = service.dispatch_business_date_report(
        business_date="2026-04-23",
        dispatch_target=DispatchTarget(target="1628724839"),
    )

    assert result["artifact_id"] == "artifact-123"
    assert [call[1]["dispatch_state"] for call in store.persist_calls] == ["dispatch_attempted", "dispatch_succeeded"]
    assert store.persist_calls[0][1]["provider_target"] == "1628724839"
    assert store.persist_calls[1][1]["provider_message_id"] == "msg-42"
    assert store.persist_calls[1][1]["provider_send_id"] == "send-42"


def test_dispatch_service_persists_attempt_then_failure(tmp_path: Path) -> None:
    store = StubStore(_surface(tmp_path))

    class FailingSender:
        def send_delivery_package(self, *, media_path: str, caption: str, dispatch_target: DispatchTarget):
            raise ReportDispatchSendError(
                "429 rate limit",
                receipt={
                    "provider": "openclaw",
                    "provider_channel": "telegram",
                    "channel": "telegram_document",
                    "provider_return_code": 1,
                },
                command=["openclaw", "message", "send"],
                return_code=1,
                stdout="",
                stderr="rate limited",
            )

    service = FSJMainReportDispatchService(
        store=store,  # type: ignore[arg-type]
        sender=FailingSender(),  # type: ignore[arg-type]
        now_factory=lambda: datetime(2026, 4, 24, 4, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(ReportDispatchSendError):
        service.dispatch_business_date_report(
            business_date="2026-04-23",
            dispatch_target=DispatchTarget(target="1628724839"),
        )

    assert [call[1]["dispatch_state"] for call in store.persist_calls] == ["dispatch_attempted", "dispatch_failed"]
    assert store.persist_calls[1][1]["error_class"] == "ReportDispatchSendError"
    assert store.persist_calls[1][1]["error_message"] == "429 rate limit"


def test_openclaw_sender_parses_success_receipt() -> None:
    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"messageId":"12345","payload":{"to":"telegram:1628724839"}}',
            stderr="",
        )

    sender = OpenClawTelegramDispatchSender(subprocess_run=fake_run)
    result = sender.send_delivery_package(
        media_path="/tmp/pkg.zip",
        caption="caption",
        dispatch_target=DispatchTarget(target="1628724839"),
    )

    assert result.receipt["provider_message_id"] == "12345"
    assert result.receipt["channel"] == "telegram_document"
    assert result.receipt["provider_target"] == "1628724839"


def test_openclaw_sender_raises_with_failure_receipt() -> None:
    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=2,
            stdout='{"error":"permission denied"}',
            stderr="permission denied",
        )

    sender = OpenClawTelegramDispatchSender(subprocess_run=fake_run)

    with pytest.raises(ReportDispatchSendError) as excinfo:
        sender.send_delivery_package(
            media_path="/tmp/pkg.zip",
            caption="caption",
            dispatch_target=DispatchTarget(target="1628724839"),
        )

    assert excinfo.value.receipt["error_message"] == "permission denied"
    assert excinfo.value.receipt["provider_return_code"] == 2
