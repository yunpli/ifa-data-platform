from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.fsj import FSJStore
from ifa_data_platform.fsj.mid_main_producer import MidMainFSJProducer, MidMainProducerInput

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'


class FakeMidMainInputReader:
    def __init__(self, payload: MidMainProducerInput) -> None:
        self.payload = payload

    def read(self, *, business_date: str, slot: str = 'mid', section_key: str = 'midday_main') -> MidMainProducerInput:
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


def test_mid_main_producer_persists_first_slice_bundle_graph() -> None:
    sample = MidMainProducerInput(
        business_date='2099-04-22',
        slot='mid',
        section_key='midday_main',
        section_type='thesis',
        bundle_topic_key=f'mainline_mid_update:{uuid.uuid4()}',
        summary_topic='A股盘中主线更新',
        stock_1m_count=128,
        stock_1m_latest_time='2099-04-22T11:18:00+08:00',
        breadth_count=24,
        breadth_latest_time='2099-04-22T11:16:00+08:00',
        breadth_sector_code='BK0421',
        breadth_spread_ratio=0.72,
        heat_count=20,
        heat_latest_time='2099-04-22T11:17:00+08:00',
        heat_sector_code='BK0421',
        heat_score=8.4,
        leader_count=5,
        leader_latest_time='2099-04-22T11:19:00+08:00',
        leader_symbols=['300024.SZ', '002031.SZ', '601127.SH'],
        leader_confirmation_states=['confirmed', 'candidate_confirming'],
        signal_scope_count=2,
        signal_latest_time='2099-04-22T11:20:00+08:00',
        latest_validation_state='confirmed',
        latest_emotion_stage='expanding',
        latest_risk_state='balanced',
        event_count=4,
        event_latest_time='2099-04-22T11:21:00+08:00',
        event_titles=['机器人链条盘中继续扩散', '算力方向再获催化'],
        latest_text_count=3,
        latest_text_titles=['机器人政策催化', 'AI 应用发布', '龙头预告更新'],
        early_plan_summary='盘前预案聚焦机器人链条强度延续',
        previous_late_summary='T-1 晚报维持机器人主线高位扩散',
        replay_id=f'replay:{uuid.uuid4()}',
        slot_run_id=f'slot-run:{uuid.uuid4()}',
        report_run_id=None,
    )
    producer = MidMainFSJProducer(reader=FakeMidMainInputReader(sample), store=FSJStore())
    payload = producer.produce(business_date='2099-04-22')
    bundle_id = payload['bundle']['bundle_id']
    try:
        persisted = producer.produce_and_persist(business_date='2099-04-22')
        assert persisted['bundle']['bundle_id'] == bundle_id
        assert persisted['bundle']['slot'] == 'mid'
        assert persisted['bundle']['section_key'] == 'midday_main'

        judgments = [obj for obj in persisted['objects'] if obj['fsj_kind'] == 'judgment']
        assert len(judgments) == 1
        assert judgments[0]['judgment_action'] == 'adjust'
        assert judgments[0]['object_type'] == 'thesis'

        evidence_roles = {(row['evidence_role'], row['ref_system']) for row in persisted['evidence_links']}
        assert ('slot_replay', 'runtime') in evidence_roles
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
        assert counts['object_cnt'] >= 6
        assert counts['edge_cnt'] >= 4
        assert counts['evidence_cnt'] >= 8
        assert counts['observed_cnt'] >= 6
    finally:
        _cleanup(bundle_id)
