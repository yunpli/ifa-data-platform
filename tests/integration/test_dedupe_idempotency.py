from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import create_engine, text

from ifa_data_platform.highfreq.derived_signals import DerivedSignalBuilder
from ifa_data_platform.lowfreq.version_persistence import NewsHistory
from ifa_data_platform.midfreq.runner import MidfreqRunner


ENGINE = create_engine("postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp", future=True)


def test_midfreq_history_rerun_does_not_grow_when_payload_unchanged() -> None:
    runner = MidfreqRunner(source_name="dummy")
    version_1 = str(uuid.uuid4())
    version_2 = str(uuid.uuid4())

    with ENGINE.begin() as conn:
        conn.execute(text("delete from ifa2.equity_daily_bar_current where ts_code in ('000001.SZ','000002.SZ') and trade_date = date '2025-04-10'"))
        conn.execute(text("delete from ifa2.equity_daily_bar_history where ts_code in ('000001.SZ','000002.SZ') and trade_date = date '2025-04-10'"))
        conn.execute(text("""
            insert into ifa2.equity_daily_bar_current
            (id, ts_code, trade_date, open, high, low, close, vol, amount, pre_close, change, pct_chg, version_id)
            values
            (gen_random_uuid(), '000001.SZ', date '2025-04-10', 10.5, 11.2, 10.3, 11.0, 1000000, 11000000, 10.5, 0.5, 4.76, :version_id),
            (gen_random_uuid(), '000002.SZ', date '2025-04-10', 20.0, 20.5, 19.8, 20.2, 500000, 10100000, 20.0, 0.2, 1.0, :version_id)
        """), {"version_id": version_1})

    inserted_first = runner._persist_current_to_history("equity_daily_bar", version_1)

    with ENGINE.begin() as conn:
        conn.execute(text("update ifa2.equity_daily_bar_current set version_id = :version_id where ts_code in ('000001.SZ','000002.SZ') and trade_date = date '2025-04-10'"), {"version_id": version_2})

    inserted_second = runner._persist_current_to_history("equity_daily_bar", version_2)

    with ENGINE.begin() as conn:
        after = conn.execute(
            text("select count(*) from ifa2.equity_daily_bar_history where ts_code in ('000001.SZ','000002.SZ') and trade_date = date '2025-04-10'")
        ).scalar_one()

    assert inserted_first == 2
    assert inserted_second == 0
    assert after == 2


def test_highfreq_derived_rerun_replaces_snapshot_instead_of_appending() -> None:
    builder = DerivedSignalBuilder()
    first = builder.build()
    second = builder.build()

    with ENGINE.begin() as conn:
        after = {
            "breadth": conn.execute(text("select count(*) from ifa2.highfreq_sector_breadth_working")).scalar_one(),
            "heat": conn.execute(text("select count(*) from ifa2.highfreq_sector_heat_working")).scalar_one(),
            "leader": conn.execute(text("select count(*) from ifa2.highfreq_leader_candidate_working")).scalar_one(),
            "limit_event": conn.execute(text("select count(*) from ifa2.highfreq_limit_event_stream_working")).scalar_one(),
            "signal_state": conn.execute(text("select count(*) from ifa2.highfreq_intraday_signal_state_working")).scalar_one(),
        }

    assert first["leader_candidate_count"] == second["leader_candidate_count"]
    assert first["limit_event_count"] == second["limit_event_count"]
    assert after == {
        "breadth": 1,
        "heat": 1,
        "leader": second["leader_candidate_count"],
        "limit_event": second["limit_event_count"],
        "signal_state": 1,
    }


def test_lowfreq_news_history_rerun_does_not_append_exact_duplicates() -> None:
    history = NewsHistory()
    record = {
        "datetime": datetime(2026, 4, 21, 8, 30, 0),
        "classify": "财经",
        "title": "dedupe-test-news-history",
        "source": "pytest",
        "url": f"https://example.com/{uuid.uuid4()}",
        "content": "same payload",
    }

    with ENGINE.begin() as conn:
        before = conn.execute(
            text("select count(*) from ifa2.news_history where title = 'dedupe-test-news-history' and source = 'pytest'")
        ).scalar_one()

    inserted_first = history.store_version(str(uuid.uuid4()), [record])
    inserted_second = history.store_version(str(uuid.uuid4()), [record])

    with ENGINE.begin() as conn:
        after = conn.execute(
            text("select count(*) from ifa2.news_history where title = 'dedupe-test-news-history' and source = 'pytest'")
        ).scalar_one()

    assert inserted_first == 1
    assert inserted_second == 0
    assert after - before == 1
