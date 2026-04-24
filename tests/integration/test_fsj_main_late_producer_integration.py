from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine

from ifa_data_platform.fsj import FSJStore
from ifa_data_platform.fsj.late_main_producer import LateMainFSJProducer, LateMainProducerInput

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_test?host=/tmp'


@pytest.fixture(autouse=True)
def _explicit_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    make_engine.cache_clear()
    get_settings.cache_clear()


class FakeLateMainInputReader:
    def __init__(self, payload: LateMainProducerInput) -> None:
        self.payload = payload

    def read(self, *, business_date: str, slot: str = 'late', section_key: str = 'post_close_main') -> LateMainProducerInput:
        assert business_date == self.payload.business_date
        assert slot == self.payload.slot
        assert section_key == self.payload.section_key
        return self.payload


def engine():
    return sa.create_engine(DB_URL, future=True)


def _cleanup(bundle_id: str) -> None:
    with engine().begin() as conn:
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_report_links WHERE bundle_id = :bundle_id'), {'bundle_id': bundle_id})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_observed_records WHERE bundle_id = :bundle_id'), {'bundle_id': bundle_id})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_evidence_links WHERE bundle_id = :bundle_id'), {'bundle_id': bundle_id})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_edges WHERE bundle_id = :bundle_id'), {'bundle_id': bundle_id})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_objects WHERE bundle_id = :bundle_id'), {'bundle_id': bundle_id})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_bundles WHERE bundle_id = :bundle_id'), {'bundle_id': bundle_id})


def test_late_main_producer_persists_provisional_close_bundle_graph() -> None:
    sample = LateMainProducerInput(
        business_date='2099-04-22',
        slot='late',
        section_key='post_close_main',
        section_type='thesis',
        bundle_topic_key=f'mainline_close:{uuid.uuid4()}',
        summary_topic='A股收盘主线复盘',
        equity_daily_count=420,
        equity_daily_latest_trade_date='2099-04-22',
        equity_daily_sample_symbols=['300024.SZ', '002031.SZ', '601127.SH'],
        northbound_flow_count=0,
        northbound_latest_trade_date=None,
        northbound_net_amount=None,
        limit_up_detail_count=0,
        limit_up_detail_latest_trade_date=None,
        limit_up_detail_sample_symbols=[],
        limit_up_down_status_count=0,
        limit_up_down_latest_trade_date=None,
        limit_up_count=None,
        limit_down_count=None,
        dragon_tiger_count=0,
        dragon_tiger_latest_trade_date=None,
        dragon_tiger_sample_symbols=[],
        sector_performance_count=0,
        sector_performance_latest_trade_date=None,
        sector_performance_top_sector=None,
        sector_performance_top_pct_chg=None,
        latest_text_count=0,
        latest_text_titles=[],
        latest_text_source_times=[],
        intraday_event_count=4,
        intraday_event_latest_time='2099-04-22T14:55:00+08:00',
        intraday_event_titles=['机器人午后回流', 'AI 应用分支走强'],
        intraday_leader_count=3,
        intraday_leader_latest_time='2099-04-22T14:57:00+08:00',
        intraday_leader_symbols=['300024.SZ', '002031.SZ'],
        intraday_signal_scope_count=2,
        intraday_signal_latest_time='2099-04-22T14:58:00+08:00',
        intraday_validation_state='confirmed',
        previous_late_summary='T-1 晚报维持机器人主线高位扩散',
        same_day_mid_summary='盘中机器人链条继续扩散并保持 validation=confirmed',
        replay_id=f'replay:{uuid.uuid4()}',
        slot_run_id=f'slot-run:{uuid.uuid4()}',
        report_run_id=None,
    )
    producer = LateMainFSJProducer(reader=FakeLateMainInputReader(sample), store=FSJStore(database_url=DB_URL))
    payload = producer.produce(business_date='2099-04-22')
    bundle_id = payload['bundle']['bundle_id']
    try:
        persisted = producer.produce_and_persist(business_date='2099-04-22')
        assert persisted['bundle']['bundle_id'] == bundle_id
        assert persisted['bundle']['slot'] == 'late'
        assert persisted['bundle']['section_key'] == 'post_close_main'

        judgments = [obj for obj in persisted['objects'] if obj['fsj_kind'] == 'judgment']
        assert len(judgments) == 1
        assert judgments[0]['judgment_action'] == 'monitor'
        assert judgments[0]['object_type'] == 'watch_item'
        assert judgments[0]['attributes_json']['contract_mode'] == 'provisional_close_only'

        evidence_roles = {(row['evidence_role'], row['ref_system']) for row in persisted['evidence_links']}
        assert ('slot_replay', 'runtime') in evidence_roles
        assert ('source_observed', 'midfreq') in evidence_roles
        assert ('source_observed', 'highfreq') in evidence_roles
        assert ('prior_slot_reference', 'fsj') in evidence_roles
        assert ('historical_reference', 'archive_v2') in evidence_roles

        with engine().begin() as conn:
            counts = conn.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM ifa2.ifa_fsj_objects WHERE bundle_id=:bundle_id) AS object_cnt,
                      (SELECT count(*) FROM ifa2.ifa_fsj_edges WHERE bundle_id=:bundle_id) AS edge_cnt,
                      (SELECT count(*) FROM ifa2.ifa_fsj_evidence_links WHERE bundle_id=:bundle_id) AS evidence_cnt,
                      (SELECT count(*) FROM ifa2.ifa_fsj_observed_records WHERE bundle_id=:bundle_id) AS observed_cnt
                    """
                ),
                {'bundle_id': bundle_id},
            ).mappings().one()
        assert counts['object_cnt'] >= 5
        assert counts['edge_cnt'] >= 4
        assert counts['evidence_cnt'] >= 8
        assert counts['observed_cnt'] >= 4
    finally:
        _cleanup(bundle_id)
