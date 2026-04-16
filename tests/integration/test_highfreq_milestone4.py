from __future__ import annotations

from sqlalchemy import create_engine, text

from ifa_data_platform.highfreq.derived_signals import DerivedSignalBuilder

ENGINE = create_engine("postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp", future=True)


def test_highfreq_derived_builder_lands_real_outputs() -> None:
    result = DerivedSignalBuilder().build()
    assert result['leader_candidate_count'] > 0
    assert 'emotion_stage' in result
    assert 'validation_state' in result
    assert 'risk_opportunity_state' in result


def test_highfreq_derived_tables_populated() -> None:
    with ENGINE.connect() as conn:
        counts = {
            'breadth': conn.execute(text("select count(*) from ifa2.highfreq_sector_breadth_working")).scalar_one(),
            'heat': conn.execute(text("select count(*) from ifa2.highfreq_sector_heat_working")).scalar_one(),
            'leader': conn.execute(text("select count(*) from ifa2.highfreq_leader_candidate_working")).scalar_one(),
            'limit_event': conn.execute(text("select count(*) from ifa2.highfreq_limit_event_stream_working")).scalar_one(),
            'signal_state': conn.execute(text("select count(*) from ifa2.highfreq_intraday_signal_state_working")).scalar_one(),
        }
    assert counts['breadth'] > 0
    assert counts['heat'] > 0
    assert counts['leader'] > 0
    assert counts['limit_event'] > 0
    assert counts['signal_state'] > 0
