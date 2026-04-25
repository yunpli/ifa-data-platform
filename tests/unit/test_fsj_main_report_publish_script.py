from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_main_report_publish.py"
spec = importlib.util.spec_from_file_location("fsj_main_report_publish", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class _DummyPublisher:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def publish_delivery_package(self, **kwargs: object) -> dict:
        self.calls.append(dict(kwargs))
        output_dir = Path(str(kwargs["output_dir"]))
        return {
            "artifact": {"artifact_id": "artifact-main", "report_run_id": kwargs.get("report_run_id")},
            "html_path": str(output_dir / "main.html"),
            "qa_path": str(output_dir / "qa.json"),
            "manifest_path": str(output_dir / "report_manifest.json"),
            "delivery_package_dir": str(output_dir / "pkg"),
            "delivery_manifest_path": str(output_dir / "pkg" / "delivery_manifest.json"),
            "telegram_caption_path": str(output_dir / "pkg" / "telegram_caption.txt"),
            "delivery_zip_path": str(output_dir / "pkg.zip"),
            "delivery_manifest": {"artifact_id": "artifact-main", "business_date": kwargs["business_date"]},
        }



def test_main_report_publish_script_uses_canonical_main_delivery_factory(
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
            output_dir=str(tmp_path),
            report_run_id="fsj-main:2026-04-23",
            generated_at="2026-04-23T11:50:24+00:00",
            include_empty=False,
            output_profile="customer",
            package_only=False,
        ),
    )

    dummy_publisher = _DummyPublisher()
    captured_factory_kwargs: dict[str, object] = {}

    monkeypatch.setattr(module, "FSJReportAssemblyStore", lambda: object())
    monkeypatch.setattr(module, "MainReportAssemblyService", lambda store: {"assembly_store": store})

    def _factory(**kwargs: object) -> _DummyPublisher:
        captured_factory_kwargs.update(kwargs)
        return dummy_publisher

    monkeypatch.setattr(module, "build_main_report_delivery_publisher", _factory)

    monkeypatch.setattr(
        module,
        "_resolve_canonical_publish_surface",
        lambda **_: {
            "workflow_handoff": {
                "artifact": {"artifact_id": "artifact-db", "report_run_id": "run-db"},
                "selected_handoff": {"selected_artifact_id": "artifact-db", "selected_delivery_package_dir": "/tmp/db/pkg"},
                "manifest_pointers": {
                    "delivery_manifest_path": "/tmp/db/pkg/delivery_manifest.json",
                    "telegram_caption_path": "/tmp/db/pkg/telegram_caption.txt",
                    "delivery_zip_path": "/tmp/db/pkg.zip",
                },
            },
            "operator_review_surface": {
                "package_paths": {
                    "operator_review_readme_path": "/tmp/db/pkg/OPERATOR_REVIEW.md",
                    "package_index_path": "/tmp/db/pkg/package_index.json",
                },
                "llm_role_policy": {"policy_versions": ["fsj_llm_role_policy_v1"]},
            },
        },
    )

    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert captured_factory_kwargs["store"].__class__.__name__ == "FSJStore"
    assert captured_factory_kwargs["artifact_root"] == tmp_path
    assert captured_factory_kwargs["assembly_service"] == {"assembly_store": captured_factory_kwargs["assembly_service"]["assembly_store"]}
    assert dummy_publisher.calls[0]["business_date"] == "2026-04-23"
    assert dummy_publisher.calls[0]["output_dir"] == tmp_path
    assert dummy_publisher.calls[0]["output_profile"] == "customer"
    assert payload["artifact"]["artifact_id"] == "artifact-main"
    assert payload["output_profile"] == "customer"
    assert payload["delivery_manifest"]["business_date"] == "2026-04-23"
    assert payload["judgment_review_surface_path"] is None
    assert payload["judgment_mapping_ledger_path"] is None
    assert payload["workflow_handoff"]["artifact"]["artifact_id"] == "artifact-db"
    assert payload["operator_review_surface"]["llm_role_policy"]["policy_versions"] == ["fsj_llm_role_policy_v1"]
    assert payload["operator_summary_path"] == "/tmp/db/pkg/OPERATOR_REVIEW.md"
    assert payload["package_index_path"] == "/tmp/db/pkg/package_index.json"



def test_main_report_publish_script_blocks_pytest_flow_on_canonical_live_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_artifacts_root = Path(__file__).resolve().parents[2] / "artifacts" / "pytest-should-block"
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp")
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            output_dir=str(live_artifacts_root),
            report_run_id=None,
            generated_at=None,
            include_empty=False,
            output_profile="internal",
            package_only=False,
        ),
    )

    with pytest.raises(module.TestLiveIsolationError, match="canonical/live DB"):
        module.main()
