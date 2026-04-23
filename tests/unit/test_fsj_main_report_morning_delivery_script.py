from __future__ import annotations

import importlib.util
from pathlib import Path


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
    pass


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
