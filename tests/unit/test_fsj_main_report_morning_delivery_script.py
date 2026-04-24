from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_main_report_morning_delivery.py"
_spec = importlib.util.spec_from_file_location("fsj_main_report_morning_delivery_script", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)
_load_comparison_candidates = _module._load_comparison_candidates


class _FakeHelper:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def list_db_delivery_candidates(self, *, business_date: str, store, limit: int = 8) -> list[dict]:
        self.calls.append(("db-list", business_date, limit))
        return [
            {
                "artifact": {"artifact_id": "artifact-db", "business_date": business_date, "artifact_family": "main_final_report"},
                "delivery_manifest_path": "/tmp/db/delivery_manifest.json",
                "delivery_manifest": {"artifact_id": "artifact-db", "business_date": business_date},
                "source": "db_active_delivery_surface",
            },
            {
                "artifact": {"artifact_id": "artifact-db-history", "business_date": business_date, "artifact_family": "main_final_report"},
                "delivery_manifest_path": "/tmp/db-history/delivery_manifest.json",
                "delivery_manifest": {"artifact_id": "artifact-db-history", "business_date": business_date},
                "source": "db_delivery_history_surface",
            },
        ]

    def load_active_published_candidate(self, *, business_date: str, store) -> dict | None:
        self.calls.append(("db", business_date))
        return {
            "artifact": {"artifact_id": "artifact-db", "business_date": business_date, "artifact_family": "main_final_report"},
            "delivery_manifest_path": "/tmp/db/delivery_manifest.json",
            "delivery_manifest": {"artifact_id": "artifact-db", "business_date": business_date},
        }

    def discover_published_candidates(self, root: str, *, business_date: str | None = None, limit: int | None = None, store=None, prefer_db_active: bool = False) -> list[dict]:
        self.calls.append(("discover", root, prefer_db_active, store is not None))
        results = [
            {
                "artifact": {"artifact_id": "artifact-db-dupe", "business_date": business_date, "artifact_family": "main_final_report"},
                "delivery_manifest_path": "/tmp/db/delivery_manifest.json",
                "delivery_manifest": {"artifact_id": "artifact-db-dupe", "business_date": business_date},
            },
            {
                "artifact": {"artifact_id": "artifact-db-history-dupe", "business_date": business_date, "artifact_family": "main_final_report"},
                "delivery_manifest_path": "/tmp/db-history/delivery_manifest.json",
                "delivery_manifest": {"artifact_id": "artifact-db-history-dupe", "business_date": business_date},
            },
            {
                "artifact": {"artifact_id": "artifact-fs", "business_date": business_date, "artifact_family": "main_final_report"},
                "delivery_manifest_path": "/tmp/fs/delivery_manifest.json",
                "delivery_manifest": {"artifact_id": "artifact-fs", "business_date": business_date},
            },
        ]
        if prefer_db_active:
            results = [*self.list_db_delivery_candidates(business_date=business_date or "", store=store, limit=limit or 8), *results]
        return results

    def load_published_candidate(self, path: str) -> dict:
        self.calls.append(("load", path))
        return {
            "artifact": {"artifact_id": f"artifact:{path}", "business_date": "2099-04-22", "artifact_family": "main_final_report"},
            "delivery_manifest_path": f"{path}/delivery_manifest.json",
            "delivery_manifest": {"artifact_id": f"artifact:{path}", "business_date": "2099-04-22"},
        }


class _FakeStore:
    def get_active_report_operator_review_surface(self, **_: object):
        return None


class _DummyOrchestrator:
    def __init__(self, publisher, dispatch_helper) -> None:
        self.publisher = publisher
        self.dispatch_helper = dispatch_helper
        self.calls: list[dict] = []

    def run_workflow(self, **kwargs: object) -> dict:
        self.calls.append(dict(kwargs))
        output_dir = Path(str(kwargs["output_dir"]))
        return {
            "artifact": {"artifact_id": "artifact-main-workflow", "report_run_id": kwargs.get("report_run_id")},
            "delivery_manifest": {"artifact_id": "artifact-main-workflow", "business_date": kwargs["business_date"]},
            "dispatch_decision": {"recommended_action": "send", "selected": {"artifact_id": "artifact-main-workflow"}},
            "workflow_manifest": {"workflow_state": "ready_to_send"},
            "delivery_package_dir": str(output_dir / "pkg"),
            "delivery_manifest_path": str(output_dir / "pkg" / "delivery_manifest.json"),
            "send_manifest_path": str(output_dir / "pkg" / "send_manifest.json"),
            "review_manifest_path": str(output_dir / "pkg" / "review_manifest.json"),
            "operator_summary_path": str(output_dir / "pkg" / "operator_summary.txt"),
            "workflow_manifest_path": str(output_dir / "pkg" / "workflow_manifest.json"),
            "delivery_zip_path": str(output_dir / "pkg.zip"),
            "telegram_caption_path": str(output_dir / "pkg" / "telegram_caption.txt"),
            "selected_handoff": {"selected_artifact_id": "artifact-main-workflow", "selected_is_current": True},
        }


def test_load_comparison_candidates_prefers_db_active_surface_and_dedupes_filesystem_fallback() -> None:
    helper = _FakeHelper()

    candidates = _load_comparison_candidates(
        helper=helper,
        store=_FakeStore(),
        compare_under_output_dir="/tmp/out",
        comparison_package_dir=["/tmp/pkg-a"],
        comparison_manifest=["/tmp/manifest-b.json"],
        business_date="2099-04-22",
        compare_limit=8,
    )

    assert [item["artifact"]["artifact_id"] for item in candidates] == [
        "artifact-db",
        "artifact-db-history",
        "artifact-fs",
        "artifact:/tmp/pkg-a",
        "artifact:/tmp/manifest-b.json",
    ]
    assert helper.calls[0] == ("discover", "/tmp/out", True, True)
    assert helper.calls[1] == ("db-list", "2099-04-22", 8)



def test_main_report_morning_delivery_script_uses_canonical_main_delivery_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp")
    monkeypatch.setattr(
        _module.argparse.ArgumentParser,
        "parse_args",
        lambda self: _module.argparse.Namespace(
            business_date="2026-04-23",
            output_dir=str(tmp_path),
            report_run_id="fsj-main-morning:2026-04-23",
            generated_at="2026-04-23T11:50:24+00:00",
            include_empty=False,
            compare_under_output_dir=None,
            compare_limit=8,
            comparison_package_dir=[],
            comparison_manifest=[],
        ),
    )

    monkeypatch.setattr(_module, "FSJReportAssemblyStore", lambda: object())
    monkeypatch.setattr(_module, "MainReportAssemblyService", lambda store: {"assembly_store": store})
    monkeypatch.setattr(_module, "FSJStore", lambda: _FakeStore())

    dummy_orchestrator: _DummyOrchestrator | None = None
    captured_factory_kwargs: dict[str, object] = {}

    def _factory(**kwargs: object):
        captured_factory_kwargs.update(kwargs)
        return object()

    def _orchestrator_builder(*, publisher, dispatch_helper):
        nonlocal dummy_orchestrator
        dummy_orchestrator = _DummyOrchestrator(publisher=publisher, dispatch_helper=dispatch_helper)
        return dummy_orchestrator

    monkeypatch.setattr(_module, "build_main_report_delivery_publisher", _factory)
    monkeypatch.setattr(_module, "MainReportMorningDeliveryOrchestrator", _orchestrator_builder)

    _module.main()

    payload = json.loads(capsys.readouterr().out)
    assert captured_factory_kwargs["artifact_root"] == tmp_path
    assert captured_factory_kwargs["assembly_service"] == {"assembly_store": captured_factory_kwargs["assembly_service"]["assembly_store"]}
    assert dummy_orchestrator is not None
    assert dummy_orchestrator.calls[0]["business_date"] == "2026-04-23"
    assert dummy_orchestrator.calls[0]["comparison_candidates"] == []
    assert payload["artifact"]["artifact_id"] == "artifact-main-workflow"
    assert payload["workflow_manifest"]["workflow_state"] == "ready_to_send"
