from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.fsj import FSJStore
from ifa_data_platform.fsj.report_rendering import MainReportArtifactPublishingService, MainReportRenderingService

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'


def engine():
    return sa.create_engine(DB_URL, future=True)


def _sample_payload(bundle_id: str, *, status: str = 'active', supersedes_bundle_id: str | None = None) -> dict:
    return {
        'bundle': {
            'bundle_id': bundle_id,
            'market': 'a_share',
            'business_date': '2099-04-18',
            'slot': 'mid',
            'agent_domain': 'main',
            'section_key': 'main_thesis',
            'section_type': 'thesis',
            'bundle_topic_key': 'theme:robotics',
            'producer': 'business-layer',
            'producer_version': 'phase1',
            'assembly_mode': 'hybrid',
            'status': status,
            'supersedes_bundle_id': supersedes_bundle_id,
            'slot_run_id': 'run-mid-2099-04-18',
            'replay_id': 'replay-mid-2099-04-18',
            'report_run_id': 'report-mid-2099-04-18',
            'summary': '机器人主线延续，但一致性开始分化',
            'payload_json': {'schema_version': 'phase1', 'notes': ['pytest']},
        },
        'objects': [
            {
                'object_id': 'fact-robotics-breadth',
                'fsj_kind': 'fact',
                'object_key': 'fact:theme:robotics:breadth_up',
                'statement': '机器人板块盘中涨停家数继续扩张',
                'object_type': 'theme',
                'evidence_level': 'E2',
                'confidence': 'high',
                'entity_refs': ['theme:robotics'],
                'metric_refs': ['limit_up_count'],
                'attributes_json': {'freshness_label': 'same_slot'},
            },
            {
                'object_id': 'signal-robotics-strengthening',
                'fsj_kind': 'signal',
                'object_key': 'signal:thesis:robotics:strengthening',
                'statement': '机器人主线强度继续增强',
                'object_type': 'strengthening',
                'signal_strength': 'high',
                'horizon': 'same_day',
                'confidence': 'medium',
                'attributes_json': {'based_on_fact_keys': ['fact:theme:robotics:breadth_up']},
            },
            {
                'object_id': 'judgment-robotics-keep',
                'fsj_kind': 'judgment',
                'object_key': 'judgment:thesis:robotics:keep_mainline',
                'statement': '机器人仍维持主线地位，但只应聚焦最强分支',
                'object_type': 'thesis',
                'judgment_action': 'hold',
                'direction': 'bullish',
                'priority': 'p0',
                'confidence': 'medium',
                'invalidators': ['高位一致性快速塌陷'],
            },
        ],
        'edges': [
            {
                'edge_type': 'fact_to_signal',
                'from_fsj_kind': 'fact',
                'from_object_key': 'fact:theme:robotics:breadth_up',
                'to_fsj_kind': 'signal',
                'to_object_key': 'signal:thesis:robotics:strengthening',
                'role': 'support',
            },
            {
                'edge_type': 'signal_to_judgment',
                'from_fsj_kind': 'signal',
                'from_object_key': 'signal:thesis:robotics:strengthening',
                'to_fsj_kind': 'judgment',
                'to_object_key': 'judgment:thesis:robotics:keep_mainline',
                'role': 'support',
            },
        ],
        'evidence_links': [
            {
                'evidence_role': 'slot_replay',
                'ref_system': 'runtime',
                'ref_family': 'slot_replay',
                'ref_table': 'slot_replay_evidence',
                'ref_key': 'slot-replay-id',
                'ref_locator_json': {'replay_id': 'replay-mid-2099-04-18'},
            },
            {
                'object_key': 'fact:theme:robotics:breadth_up',
                'fsj_kind': 'fact',
                'evidence_role': 'source_observed',
                'ref_system': 'midfreq',
                'ref_family': 'limit_up_detail',
                'ref_table': 'ifa2.limit_up_detail_history',
                'ref_key': '2099-04-18:robotics',
                'ref_locator_json': {'trade_date': '2099-04-18', 'tag': 'robotics'},
                'observed_at': '2099-04-18T05:05:00+00:00',
            },
        ],
        'observed_records': [
            {
                'object_key': 'fact:theme:robotics:breadth_up',
                'fsj_kind': 'fact',
                'source_layer': 'midfreq',
                'source_family': 'limit_up_detail',
                'source_table': 'ifa2.limit_up_detail_history',
                'source_record_key': '2099-04-18:robotics',
                'observed_label': '机器人涨停扩散',
                'observed_payload_json': {'count': 17, 'leader': '300024.SZ'},
            }
        ],
        'report_links': [
            {
                'report_run_id': 'report-mid-2099-04-18',
                'artifact_type': 'markdown',
                'artifact_uri': 'file:///tmp/report-mid-2099-04-18.md',
                'artifact_locator_json': {'path': '/tmp/report-mid-2099-04-18.md'},
                'section_render_key': 'main_thesis.robotics',
            }
        ],
    }


def _cleanup(bundle_ids: list[str]) -> None:
    with engine().begin() as conn:
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_report_links WHERE bundle_id = ANY(CAST(:bundle_ids AS text[]))'), {'bundle_ids': bundle_ids})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_observed_records WHERE bundle_id = ANY(CAST(:bundle_ids AS text[]))'), {'bundle_ids': bundle_ids})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_evidence_links WHERE bundle_id = ANY(CAST(:bundle_ids AS text[]))'), {'bundle_ids': bundle_ids})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_edges WHERE bundle_id = ANY(CAST(:bundle_ids AS text[]))'), {'bundle_ids': bundle_ids})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_objects WHERE bundle_id = ANY(CAST(:bundle_ids AS text[]))'), {'bundle_ids': bundle_ids})
        conn.execute(text('DELETE FROM ifa2.ifa_fsj_bundles WHERE bundle_id = ANY(CAST(:bundle_ids AS text[]))'), {'bundle_ids': bundle_ids})


def test_fsj_phase1_schema_round_trip_and_active_lookup() -> None:
    store = FSJStore()
    store.ensure_schema()
    bundle_id = f'fsj:test:{uuid.uuid4()}'
    try:
        payload = _sample_payload(bundle_id)
        store.upsert_bundle_graph(payload)

        graph = store.get_bundle_graph(bundle_id)
        assert graph is not None
        assert graph['bundle']['bundle_id'] == bundle_id
        assert graph['bundle']['bundle_topic_key'] == 'theme:robotics'
        assert len(graph['objects']) == 3
        assert len(graph['edges']) == 2
        assert len(graph['evidence_links']) == 2
        assert len(graph['observed_records']) == 1
        assert len(graph['report_links']) == 1

        active = store.get_active_bundle(
            business_date='2099-04-18',
            slot='mid',
            agent_domain='main',
            section_key='main_thesis',
            bundle_topic_key='theme:robotics',
        )
        assert active is not None
        assert active['bundle']['bundle_id'] == bundle_id
        judgments = [obj for obj in active['objects'] if obj['fsj_kind'] == 'judgment']
        assert len(judgments) == 1
        assert judgments[0]['judgment_action'] == 'hold'
    finally:
        _cleanup([bundle_id])


def test_fsj_phase1_upsert_is_idempotent_and_preserves_natural_keys() -> None:
    store = FSJStore()
    store.ensure_schema()
    bundle_id = f'fsj:test:{uuid.uuid4()}'
    try:
        payload = _sample_payload(bundle_id)
        store.upsert_bundle_graph(payload)
        payload['bundle']['summary'] = '机器人主线仍强，但高位分歧扩大'
        payload['objects'][2]['statement'] = '机器人仍维持主线，但只做最强核心'
        store.upsert_bundle_graph(payload)

        with engine().begin() as conn:
            counts = conn.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM ifa2.ifa_fsj_bundles WHERE bundle_id=:bundle_id) AS bundle_cnt,
                      (SELECT count(*) FROM ifa2.ifa_fsj_objects WHERE bundle_id=:bundle_id) AS object_cnt,
                      (SELECT count(*) FROM ifa2.ifa_fsj_edges WHERE bundle_id=:bundle_id) AS edge_cnt,
                      (SELECT count(*) FROM ifa2.ifa_fsj_evidence_links WHERE bundle_id=:bundle_id) AS evidence_cnt,
                      (SELECT count(*) FROM ifa2.ifa_fsj_observed_records WHERE bundle_id=:bundle_id) AS observed_cnt,
                      (SELECT count(*) FROM ifa2.ifa_fsj_report_links WHERE bundle_id=:bundle_id) AS report_cnt
                    """
                ),
                {'bundle_id': bundle_id},
            ).mappings().one()
        assert counts['bundle_cnt'] == 1
        assert counts['object_cnt'] == 3
        assert counts['edge_cnt'] == 2
        assert counts['evidence_cnt'] == 2
        assert counts['observed_cnt'] == 1
        assert counts['report_cnt'] == 1

        graph = store.get_bundle_graph(bundle_id)
        assert graph is not None
        assert graph['bundle']['summary'] == '机器人主线仍强，但高位分歧扩大'
        judgment = next(obj for obj in graph['objects'] if obj['fsj_kind'] == 'judgment')
        assert judgment['statement'] == '机器人仍维持主线，但只做最强核心'
    finally:
        _cleanup([bundle_id])


def test_fsj_phase1_status_chain_supports_superseded_and_active_versions() -> None:
    store = FSJStore()
    store.ensure_schema()
    old_bundle_id = f'fsj:test:{uuid.uuid4()}:old'
    new_bundle_id = f'fsj:test:{uuid.uuid4()}:new'
    try:
        old_payload = _sample_payload(old_bundle_id, status='superseded')
        new_payload = _sample_payload(new_bundle_id, status='active', supersedes_bundle_id=old_bundle_id)
        store.upsert_bundle_graph(old_payload)
        store.upsert_bundle_graph(new_payload)

        active = store.get_active_bundle(
            business_date='2099-04-18',
            slot='mid',
            agent_domain='main',
            section_key='main_thesis',
            bundle_topic_key='theme:robotics',
        )
        assert active is not None
        assert active['bundle']['bundle_id'] == new_bundle_id
        assert active['bundle']['supersedes_bundle_id'] == old_bundle_id

        with engine().begin() as conn:
            rows = conn.execute(
                text('SELECT bundle_id, status, supersedes_bundle_id FROM ifa2.ifa_fsj_bundles WHERE bundle_id IN (:a, :b) ORDER BY bundle_id'),
                {'a': old_bundle_id, 'b': new_bundle_id},
            ).mappings().all()
        by_id = {row['bundle_id']: row for row in rows}
        assert by_id[old_bundle_id]['status'] == 'superseded'
        assert by_id[new_bundle_id]['status'] == 'active'
        assert by_id[new_bundle_id]['supersedes_bundle_id'] == old_bundle_id
    finally:
        _cleanup([old_bundle_id, new_bundle_id])


class _StubAssemblyService:
    def __init__(self, bundle_id: str, *, summary: str):
        self.bundle_id = bundle_id
        self.summary = summary

    def assemble_main_sections(self, *, business_date: str, include_empty: bool = False) -> dict:
        return {
            'artifact_type': 'fsj_main_report_sections',
            'artifact_version': 'v1',
            'market': 'a_share',
            'business_date': business_date,
            'agent_domain': 'main',
            'section_count': 1,
            'sections': [
                {
                    'slot': 'mid',
                    'section_key': 'main_thesis',
                    'section_render_key': 'main.midday',
                    'title': '盘中主结论',
                    'order_index': 20,
                    'status': 'ready',
                    'bundle': {
                        'bundle_id': self.bundle_id,
                        'status': 'active',
                        'supersedes_bundle_id': None,
                        'bundle_topic_key': 'theme:robotics',
                        'producer': 'business-layer',
                        'producer_version': 'phase1',
                        'section_type': 'thesis',
                        'slot_run_id': 'slot-run-mid',
                        'replay_id': 'replay-mid',
                        'report_run_id': None,
                        'updated_at': '2099-04-18T12:00:00+00:00',
                    },
                    'summary': self.summary,
                    'judgments': [],
                    'signals': [],
                    'facts': [],
                    'lineage': {'bundle': {'bundle_id': self.bundle_id}, 'objects': [], 'edges': [], 'evidence_links': [], 'observed_records': [], 'report_links': []},
                }
            ],
        }


def test_main_report_artifact_publish_persists_links_and_supersedes_prior_active(tmp_path) -> None:
    store = FSJStore()
    store.ensure_schema()
    bundle_id = f'fsj:test:{uuid.uuid4()}:bundle'
    first: dict | None = None
    second: dict | None = None
    try:
        store.upsert_bundle_graph(_sample_payload(bundle_id))
        publisher_v1 = MainReportArtifactPublishingService(
            rendering_service=MainReportRenderingService(_StubAssemblyService(bundle_id, summary='v1 summary')),
            store=store,
        )
        first = publisher_v1.publish_main_report_html(
            business_date='2099-04-18',
            output_dir=tmp_path,
            report_run_id='report-run-v1',
            generated_at=datetime(2099, 4, 18, 12, 0, tzinfo=timezone.utc),
        )

        publisher_v2 = MainReportArtifactPublishingService(
            rendering_service=MainReportRenderingService(_StubAssemblyService(bundle_id, summary='v2 summary')),
            store=store,
        )
        second = publisher_v2.publish_main_report_html(
            business_date='2099-04-18',
            output_dir=tmp_path,
            report_run_id='report-run-v2',
            generated_at=datetime(2099, 4, 18, 12, 5, tzinfo=timezone.utc),
        )

        active_artifact = store.get_active_report_artifact(
            business_date='2099-04-18',
            agent_domain='main',
            artifact_family='main_final_report',
        )
        assert active_artifact is not None
        assert active_artifact['artifact_id'] == second['artifact']['artifact_id']
        assert active_artifact['supersedes_artifact_id'] == first['artifact']['artifact_id']

        with engine().begin() as conn:
            artifact_rows = conn.execute(
                text("SELECT artifact_id, status, supersedes_artifact_id FROM ifa2.ifa_fsj_report_artifacts WHERE artifact_id IN (:a, :b) ORDER BY artifact_id"),
                {'a': first['artifact']['artifact_id'], 'b': second['artifact']['artifact_id']},
            ).mappings().all()
            report_links = conn.execute(
                text("SELECT report_run_id, artifact_uri FROM ifa2.ifa_fsj_report_links WHERE bundle_id=:bundle_id AND artifact_type='html' ORDER BY report_run_id"),
                {'bundle_id': bundle_id},
            ).mappings().all()
        by_id = {row['artifact_id']: row for row in artifact_rows}
        assert by_id[first['artifact']['artifact_id']]['status'] == 'superseded'
        assert by_id[second['artifact']['artifact_id']]['status'] == 'active'
        assert by_id[second['artifact']['artifact_id']]['supersedes_artifact_id'] == first['artifact']['artifact_id']
        assert [row['report_run_id'] for row in report_links] == ['report-run-v1', 'report-run-v2']
        assert report_links[-1]['artifact_uri'] == Path(second['html_path']).as_uri()
    finally:
        _cleanup([bundle_id])
        if first and second:
            with engine().begin() as conn:
                conn.execute(text('DELETE FROM ifa2.ifa_fsj_report_artifacts WHERE artifact_id IN (:a, :b)'), {'a': first['artifact']['artifact_id'], 'b': second['artifact']['artifact_id']})
