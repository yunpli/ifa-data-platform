from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


TEST_DB_URL = "postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp"


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "fsj_support_bundle_persist.py"
spec = importlib.util.spec_from_file_location("fsj_support_bundle_persist", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class _StubProducer:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload or {
            "bundle": {
                "bundle_id": "bundle-1",
                "status": "active",
                "section_key": "support_macro",
            },
            "objects": [{"fsj_kind": "fact"}, {"fsj_kind": "signal"}, {"fsj_kind": "judgment"}],
            "edges": [{}, {}],
            "evidence_links": [{}],
            "observed_records": [{}],
        }
        self.error = error

    def produce_and_persist(self, *, business_date: str) -> dict:
        assert business_date == "2026-04-23"
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch):
    registry = {
        ("early", "macro"): lambda: _StubProducer(),
        ("early", "commodities"): lambda: _StubProducer(
            {
                "bundle": {"bundle_id": "bundle-2", "status": "active", "section_key": "support_commodities"},
                "objects": [{}, {}, {}],
                "edges": [{}, {}, {}],
                "evidence_links": [{}, {}],
                "observed_records": [{}],
            }
        ),
        ("early", "ai_tech"): lambda: _StubProducer(
            {
                "bundle": {"bundle_id": "bundle-3", "status": "active", "section_key": "support_ai_tech"},
                "objects": [{}, {}, {}, {}],
                "edges": [{}, {}, {}],
                "evidence_links": [{}, {}],
                "observed_records": [{}, {}],
            }
        ),
    }
    monkeypatch.setattr(module, "PRODUCER_REGISTRY", registry)
    return registry


def test_main_persists_selected_domains_and_writes_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], registry) -> None:
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            slot="early",
            agent_domains=["macro", "ai_tech"],
            output_root=str(tmp_path),
        ),
    )

    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["persisted_count"] == 2
    assert payload["blocked_count"] == 0
    assert [item["agent_domain"] for item in payload["results"]] == ["macro", "ai_tech"]
    assert json.loads((tmp_path / "persist_summary.json").read_text(encoding="utf-8"))["persisted_count"] == 2
    assert "FSJ support bundle persist｜2026-04-23｜early" in (tmp_path / "operator_summary.txt").read_text(encoding="utf-8")


def test_main_exits_nonzero_when_any_domain_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    monkeypatch.setattr(
        module,
        "PRODUCER_REGISTRY",
        {
            ("early", "macro"): lambda: _StubProducer(error=RuntimeError("db unavailable")),
        },
    )
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            slot="early",
            agent_domains=["macro"],
            output_root=str(tmp_path),
        ),
    )

    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["persisted_count"] == 0
    assert payload["blocked_count"] == 1
    assert payload["results"][0]["reason"] == "RuntimeError: db unavailable"


def test_main_blocks_pytest_flow_on_canonical_live_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_artifacts_root = Path(__file__).resolve().parents[2] / "artifacts" / "pytest-should-block"
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp")
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        "parse_args",
        lambda self: module.argparse.Namespace(
            business_date="2026-04-23",
            slot="early",
            agent_domains=["macro"],
            output_root=str(live_artifacts_root),
        ),
    )

    with pytest.raises(module.TestLiveIsolationError, match="canonical/live DB"):
        module.main()
