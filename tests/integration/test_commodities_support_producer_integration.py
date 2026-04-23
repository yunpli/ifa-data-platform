from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import text

from ifa_data_platform.fsj import FSJStore
from ifa_data_platform.fsj.commodities_support_producer import (
    CommoditiesSupportProducerInput,
    EarlyCommoditiesSupportProducer,
    LateCommoditiesSupportProducer,
)
from ifa_data_platform.fsj.support_common import SupportSnapshot, SupportTextItem

DB_URL = 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'


class FakeCommoditiesSupportInputReader:
    def __init__(self, early_payload: CommoditiesSupportProducerInput, late_payload: CommoditiesSupportProducerInput) -> None:
        self.payloads = {"early": early_payload, "late": late_payload}

    def read(self, *, business_date: str, slot: str) -> CommoditiesSupportProducerInput:
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



def _sample_payload(slot: str) -> CommoditiesSupportProducerInput:
    fresh = slot == "early"
    return CommoditiesSupportProducerInput(
        business_date="2099-04-22",
        slot=slot,
        agent_domain="commodities",
        section_key="support_commodities",
        section_type="support",
        bundle_topic_key=f"commodities_{slot}_support:{uuid.uuid4()}",
        summary_topic="A股 commodities support",
        commodity_snapshots=[
            SupportSnapshot(
                object_key="commodity:precious_metal:AU9999.SGE",
                label="AU9999.SGE",
                source_layer="midfreq",
                source_family="precious_metal_15min_history",
                source_table="ifa2.precious_metal_15min_history",
                source_record_key=f"AU9999.SGE@{'2099-04-22T09:15:00' if fresh else '2099-04-21T14:45:00'}",
                freshness_label="fresh" if fresh else "t_minus_1",
                confidence="high",
                value_text="AU9999.SGE 最新价 582.6 vol=1200 oi=3100" if fresh else "AU9999.SGE 最新价 578.3 vol=980 oi=3005",
                observed_at="2099-04-22T09:15:00" if fresh else "2099-04-21T14:45:00",
                attributes={"trade_time": "2099-04-22T09:15:00" if fresh else "2099-04-21T14:45:00", "close": 582.6 if fresh else 578.3, "vol": 1200.0 if fresh else 980.0, "oi": 3100.0 if fresh else 3005.0, "family": "precious_metal"},
            )
        ],
        latest_text_items=[
            SupportTextItem(title="黄金夜盘走强带动资源链关注升温", published_at="2099-04-22T07:10:00+08:00", source_table="news_history")
        ] if fresh else [],
        futures_daily_count=5,
        futures_latest_trade_date="2099-04-21",
        intraday_snapshot_latest_time="2099-04-22T09:15:00" if fresh else None,
        prior_main_summary="主判断维持资源映射跟踪",
        previous_support_summary="前一期商品链以背景观察为主",
        replay_id=f"replay:{uuid.uuid4()}",
        slot_run_id=f"slot-run:{uuid.uuid4()}",
        report_run_id=None,
    )



def test_commodities_support_producers_persist_bundle_graphs() -> None:
    early_payload = _sample_payload("early")
    late_payload = _sample_payload("late")
    reader = FakeCommoditiesSupportInputReader(early_payload, late_payload)

    early_producer = EarlyCommoditiesSupportProducer(reader=reader, store=FSJStore())
    late_producer = LateCommoditiesSupportProducer(reader=reader, store=FSJStore())

    early_graph = early_producer.produce(business_date="2099-04-22")
    late_graph = late_producer.produce(business_date="2099-04-22")

    early_bundle_id = early_graph["bundle"]["bundle_id"]
    late_bundle_id = late_graph["bundle"]["bundle_id"]

    try:
        persisted_early = early_producer.produce_and_persist(business_date="2099-04-22")
        persisted_late = late_producer.produce_and_persist(business_date="2099-04-22")

        assert persisted_early["bundle"]["slot"] == "early"
        assert persisted_late["bundle"]["slot"] == "late"
        assert persisted_early["bundle"]["section_key"] == "support_commodities"
        assert persisted_late["bundle"]["section_key"] == "support_commodities"

        early_judgment = next(obj for obj in persisted_early["objects"] if obj["fsj_kind"] == "judgment")
        late_judgment = next(obj for obj in persisted_late["objects"] if obj["fsj_kind"] == "judgment")
        assert early_judgment["judgment_action"] == "adjust"
        assert late_judgment["judgment_action"] in {"confirm", "prepare"}

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
            assert row["evidence_cnt"] >= 1
            assert row["observed_cnt"] >= 1
    finally:
        _cleanup(early_bundle_id)
        _cleanup(late_bundle_id)
