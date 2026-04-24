from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_support_report_publish.py"
spec = importlib.util.spec_from_file_location("fsj_support_report_publish", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_support_publish_prefers_canonical_db_delivery_surface_for_operator_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            agent_domain="macro",
            slot="early",
            output_dir=str(tmp_path),
            report_run_id="fsj-support:2026-04-23:early:macro",
            generated_at="2026-04-23T11:50:24+00:00",
            html_only=False,
            require_ready=False,
        ),
    )

    class _DummyAssemblyService:
        def assemble_support_section(self, **_: object) -> dict:
            return {"status": "ready", "bundle": {"bundle_id": "bundle-support-macro-early"}}

    class _DummyPublisher:
        def __init__(self, *, rendering_service, store) -> None:
            self.rendering_service = rendering_service
            self.store = store

        def publish_delivery_package(self, **_: object) -> dict:
            return {
                "artifact": {"artifact_id": "artifact-raw", "report_run_id": "run-raw"},
                "html_path": str(tmp_path / "support.html"),
                "qa_path": str(tmp_path / "qa.json"),
                "manifest_path": str(tmp_path / "raw.manifest.json"),
                "delivery_package_dir": str(tmp_path / "raw-pkg"),
                "delivery_manifest_path": str(tmp_path / "raw-pkg" / "delivery_manifest.json"),
                "delivery_zip_path": str(tmp_path / "raw-pkg.zip"),
                "operator_summary_path": str(tmp_path / "raw-pkg" / "operator_summary.txt"),
                "package_index_path": str(tmp_path / "raw-pkg" / "package_index.json"),
                "delivery_manifest": {"package_state": "ready", "lineage": {"bundle_id": "bundle-support-macro-early"}},
            }

    monkeypatch.setattr(module, "FSJReportAssemblyStore", lambda: object())
    monkeypatch.setattr(module, "SupportReportAssemblyService", lambda store: _DummyAssemblyService())
    monkeypatch.setattr(module, "build_support_report_delivery_publisher", lambda **kwargs: _DummyPublisher(rendering_service=None, store=kwargs["store"]))
    monkeypatch.setattr(
        module,
        "_resolve_canonical_publish_surface",
        lambda **_: {
            "delivery_surface": {
                "delivery_package": {
                    "package_state": "ready",
                    "delivery_package_dir": "/tmp/db/pkg",
                    "lineage": {"bundle_id": "bundle-db-macro"},
                }
            },
            "workflow_handoff": {
                "artifact": {"artifact_id": "artifact-db", "report_run_id": "run-db"},
                "selected_handoff": {
                    "selected_artifact_id": "artifact-db",
                    "selected_delivery_package_dir": "/tmp/db/pkg",
                },
                "state": {
                    "workflow_state": "ready_to_send",
                    "recommended_action": "send",
                    "dispatch_recommended_action": "send",
                    "package_state": "ready",
                    "next_step": "dispatch_send_manifest",
                    "selection_reason": "support_ready_candidate domain=macro",
                    "dispatch_selected_artifact_id": "artifact-db",
                },
                "manifest_pointers": {
                    "delivery_manifest_path": "/tmp/db/pkg/delivery_manifest.json",
                    "delivery_zip_path": "/tmp/db/pkg.zip",
                    "operator_review_readme_path": "/tmp/db/pkg/OPERATOR_REVIEW.md",
                    "package_index_path": "/tmp/db/pkg/package_index.json",
                },
            },
        },
    )

    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["artifact"]["artifact_id"] == "artifact-raw"
    assert payload["workflow_handoff"]["artifact"]["artifact_id"] == "artifact-db"
    assert payload["workflow_handoff"]["state"]["dispatch_recommended_action"] == "send"
    assert payload["workflow_handoff"]["state"]["next_step"] == "dispatch_send_manifest"
    assert payload["workflow_handoff"]["state"]["selection_reason"] == "support_ready_candidate domain=macro"
    assert payload["workflow_handoff"]["state"]["dispatch_selected_artifact_id"] == "artifact-db"
    assert payload["delivery_package_dir"] == "/tmp/db/pkg"
    assert payload["delivery_manifest_path"] == "/tmp/db/pkg/delivery_manifest.json"
    assert payload["delivery_zip_path"] == "/tmp/db/pkg.zip"
    assert payload["operator_summary_path"] == "/tmp/db/pkg/OPERATOR_REVIEW.md"
    assert payload["package_index_path"] == "/tmp/db/pkg/package_index.json"


def test_support_publish_require_ready_blocks_without_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            agent_domain="macro",
            slot="early",
            output_dir=str(tmp_path),
            report_run_id=None,
            generated_at=None,
            html_only=False,
            require_ready=True,
        ),
    )

    class _DummyAssemblyService:
        def assemble_support_section(self, **_: object) -> dict:
            return {"status": "missing", "section_render_key": "support.macro.early", "bundle": None}

    class _UnexpectedPublisher:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def publish_delivery_package(self, **_: object) -> dict:
            raise AssertionError("publish_delivery_package should not run when require-ready blocks early")

        def publish_support_report_html(self, **_: object) -> dict:
            raise AssertionError("publish_support_report_html should not run when require-ready blocks early")

    monkeypatch.setattr(module, "FSJReportAssemblyStore", lambda: object())
    monkeypatch.setattr(module, "SupportReportAssemblyService", lambda store: _DummyAssemblyService())
    monkeypatch.setattr(module, "build_support_report_delivery_publisher", lambda **kwargs: _UnexpectedPublisher())

    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "missing"
    assert payload["reason"] == "persisted_support_bundle_not_ready"


def test_support_publish_blocks_pytest_flow_on_canonical_live_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_artifacts_root = Path(__file__).resolve().parents[2] / "artifacts" / "pytest-should-block"
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp")
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            agent_domain="macro",
            slot="early",
            output_dir=str(live_artifacts_root),
            report_run_id=None,
            generated_at=None,
            html_only=False,
            require_ready=False,
        ),
    )

    with pytest.raises(module.TestLiveIsolationError, match="canonical/live DB"):
        module.main()
