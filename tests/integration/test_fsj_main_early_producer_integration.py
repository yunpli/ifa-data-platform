from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.fsj import FSJStore
from ifa_data_platform.fsj.early_main_producer import EarlyMainFSJProducer, EarlyMainProducerInput

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'


class FakeEarlyMainInputReader:
    def __init__(self, payload: EarlyMainProducerInput) -> None:
        self.payload = payload

    def read(self, *, business_date: str, slot: str = 'early', section_key: str = 'pre_open_main') -> EarlyMainProducerInput:
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


def test_early_main_producer_persists_first_slice_bundle_graph() -> None:
    sample = EarlyMainProducerInput(
        business_date='2099-04-22',
        slot='early',
        section_key='pre_open_main',
        section_type='thesis',
        bundle_topic_key=f'mainline_candidate:{uuid.uuid4()}',
        summary_topic='A股盘前主线预案',
        trading_day_open=True,
        trading_day_label='open',
        focus_symbols=['300024.SZ', '002031.SZ', '601127.SH'],
        focus_list_types=['focus', 'key_focus'],
        auction_count=12,
        auction_snapshot_time='2099-04-22T09:27:00+08:00',
        event_count=5,
        event_latest_time='2099-04-22T09:24:00+08:00',
        event_titles=['机器人链条隔夜催化', 'AI 应用催化'],
        leader_count=3,
        leader_symbols=['300024.SZ', '002031.SZ'],
        signal_scope_count=1,
        latest_signal_state='candidate_confirming',
        text_catalyst_count=2,
        text_catalyst_titles=['机器人政策催化', 'AI 应用发布'],
        previous_archive_summary='昨日机器人主线维持高位扩散',
        replay_id=f'replay:{uuid.uuid4()}',
        slot_run_id=f'slot-run:{uuid.uuid4()}',
        report_run_id=None,
    )
    producer = EarlyMainFSJProducer(reader=FakeEarlyMainInputReader(sample), store=FSJStore())
    payload = producer.produce(business_date='2099-04-22')
    bundle_id = payload['bundle']['bundle_id']
    try:
        persisted = producer.produce_and_persist(business_date='2099-04-22')
        assert persisted['bundle']['bundle_id'] == bundle_id
        assert persisted['bundle']['slot'] == 'early'
        assert persisted['bundle']['section_key'] == 'pre_open_main'

        judgments = [obj for obj in persisted['objects'] if obj['fsj_kind'] == 'judgment']
        assert len(judgments) == 1
        assert judgments[0]['judgment_action'] == 'validate'

        evidence_roles = {(row['evidence_role'], row['ref_system']) for row in persisted['evidence_links']}
        assert ('slot_replay', 'runtime') in evidence_roles
        assert ('source_observed', 'highfreq') in evidence_roles
        assert ('source_observed', 'business_seed') in evidence_roles

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
        assert counts['object_cnt'] >= 4
        assert counts['edge_cnt'] >= 2
        assert counts['evidence_cnt'] >= 4
        assert counts['observed_cnt'] >= 3
    finally:
        _cleanup(bundle_id)
