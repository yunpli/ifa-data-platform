from __future__ import annotations

from ifa_data_platform.fsj.support_common import coalesce_support_lineage_ids


def test_coalesce_support_lineage_ids_preserves_explicit_values() -> None:
    assert coalesce_support_lineage_ids(
        business_date="2026-04-23",
        slot="early",
        agent_domain="macro",
        slot_run_id="slot-run:1",
        replay_id="replay:1",
    ) == ("slot-run:1", "replay:1")


def test_coalesce_support_lineage_ids_generates_deterministic_fallbacks() -> None:
    assert coalesce_support_lineage_ids(
        business_date="2026-04-23",
        slot="early",
        agent_domain="ai_tech",
        slot_run_id=None,
        replay_id=None,
    ) == (
        "fsj-support-slot:2026-04-23:early:ai_tech",
        "fsj-support-replay:2026-04-23:early:ai_tech",
    )
