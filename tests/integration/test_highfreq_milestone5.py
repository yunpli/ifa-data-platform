from __future__ import annotations

from sqlalchemy import create_engine, text

from ifa_data_platform.highfreq.scope_manager import ScopeManager

ENGINE = create_engine("postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp", future=True)


def test_highfreq_scope_manager_builds_active_and_dynamic_scope() -> None:
    result = ScopeManager().rebuild()
    assert result.active_count > 0
    assert result.dynamic_count > 0
    assert result.active_scope_status == 'active_scope_landed'
    assert result.dynamic_scope_status == 'dynamic_upgrade_landed'


def test_highfreq_scope_tables_populated() -> None:
    with ENGINE.connect() as conn:
        active_count = conn.execute(text("select count(*) from ifa2.highfreq_active_scope")).scalar_one()
        dynamic_count = conn.execute(text("select count(*) from ifa2.highfreq_dynamic_candidate")).scalar_one()
    assert active_count > 0
    assert dynamic_count > 0
