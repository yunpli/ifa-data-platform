from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.fsj import FSJStore
from ifa_data_platform.fsj.ai_tech_support_producer import (
    AITechSupportProducerInput,
    EarlyAITechSupportProducer,
    LateAITechSupportProducer,
)
from ifa_data_platform.fsj.support_common import SupportSnapshot, SupportTextItem

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'


class FakeAITechSupportInputReader:
    def __init__(self, early_payload: AITechSupportProducerInput, late_payload: AITechSupportProducerInput) -> None:
        self.payloads = {"early": early_payload, "late": late_payload}

    def read(self, *, business_date: str, slot: str) -> AITechSupportProducerInput:
        payload = self.payloads[slot]
        assert payload.business_date == business_date
        assert payload.slot == slot
        return payload



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



def _sample_payload(slot: str) -> AITechSupportProducerInput:
    fresh = slot == "early"
    return AITechSupportProducerInput(
        business_date="2099-04-22",
        slot=slot,
        agent_domain="ai_tech",
        section_key="support_ai_tech",
        section_type="support",
        bundle_topic_key=f"ai_tech_{slot}_support:{uuid.uuid4()}",
        summary_topic="A股AI-tech support",
        tech_focus_count=18,
        tech_key_focus_count=6,
        tech_focus_symbols=["300308.SZ", "688981.SH", "002230.SZ"],
        ai_tech_sector_snapshots=[
            SupportSnapshot(
                object_key="ai_tech:人工智能",
                label="人工智能",
                source_layer="midfreq",
                source_family="sector_performance",
                source_table="ifa2.sector_performance_history",
                source_record_key=f"人工智能@{'2099-04-22' if fresh else '2099-04-21'}",
                freshness_label="fresh" if fresh else "t_minus_1",
                confidence="high",
                value_text="人工智能 当日涨跌幅 3.8%" if fresh else "人工智能 当日涨跌幅 1.2%",
                observed_at="2099-04-22" if fresh else "2099-04-21",
                attributes={"trade_date": "2099-04-22" if fresh else "2099-04-21", "pct_chg": 3.8 if fresh else 1.2},
            )
        ],
        latest_text_items=[
            SupportTextItem(title="算力订单再获验证", published_at="2099-04-22T07:10:00+08:00", source_table="news_history")
        ] if fresh else [],
        archive_sector_count=9,
        archive_sector_latest_business_date="2099-04-21",
        current_top_sector="人工智能",
        current_top_sector_pct_chg=3.8 if fresh else 1.2,
        prior_main_summary="主判断维持科技修复",
        previous_support_summary="前一日 AI-tech 仍为支线跟踪",
        replay_id=f"replay:{uuid.uuid4()}",
        slot_run_id=f"slot-run:{uuid.uuid4()}",
        report_run_id=None,
    )



def test_ai_tech_support_producers_persist_bundle_graphs() -> None:
    early_payload = _sample_payload("early")
    late_payload = _sample_payload("late")
    reader = FakeAITechSupportInputReader(early_payload, late_payload)

    early_producer = EarlyAITechSupportProducer(reader=reader, store=FSJStore())
    late_producer = LateAITechSupportProducer(reader=reader, store=FSJStore())

    early_graph = early_producer.produce(business_date="2099-04-22")
    late_graph = late_producer.produce(business_date="2099-04-22")

    early_bundle_id = early_graph["bundle"]["bundle_id"]
    late_bundle_id = late_graph["bundle"]["bundle_id"]

    try:
        persisted_early = early_producer.produce_and_persist(business_date="2099-04-22")
        persisted_late = late_producer.produce_and_persist(business_date="2099-04-22")

        assert persisted_early["bundle"]["slot"] == "early"
        assert persisted_late["bundle"]["slot"] == "late"
        assert persisted_early["bundle"]["section_key"] == "support_ai_tech"
        assert persisted_late["bundle"]["section_key"] == "support_ai_tech"

        early_judgment = next(obj for obj in persisted_early["objects"] if obj["fsj_kind"] == "judgment")
        late_judgment = next(obj for obj in persisted_late["objects"] if obj["fsj_kind"] == "judgment")
        assert early_judgment["judgment_action"] == "adjust"
        assert late_judgment["judgment_action"] in {"confirm", "prepare", "adjust"}

        with engine().begin() as conn:
            counts = conn.execute(
                text(
                    """
                    select bundle_id,
                           (select count(*) from ifa2.ifa_fsj_objects o where o.bundle_id = b.bundle_id) as object_cnt,
                           (select count(*) from ifa2.ifa_fsj_edges e where e.bundle_id = b.bundle_id) as edge_cnt,
                           (select count(*) from ifa2.ifa_fsj_evidence_links l where l.bundle_id = b.bundle_id) as evidence_cnt,
                           (select count(*) from ifa2.ifa_fsj_observed_records r where r.bundle_id = b.bundle_id) as observed_cnt
                    from ifa2.ifa_fsj_bundles b
                    where b.bundle_id in (:early_bundle_id, :late_bundle_id)
                    order by bundle_id
                    """
                ),
                {"early_bundle_id": early_bundle_id, "late_bundle_id": late_bundle_id},
            ).mappings().all()
        assert len(counts) == 2
        for row in counts:
            assert row["object_cnt"] >= 3
            assert row["edge_cnt"] >= 3
            assert row["evidence_cnt"] >= 2
            assert row["observed_cnt"] >= 1
    finally:
        _cleanup(early_bundle_id)
        _cleanup(late_bundle_id)
