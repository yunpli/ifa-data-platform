from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Protocol, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.fsj.llm_assist import (
    FSJEarlyLLMAssistant,
    FSJEarlyLLMRequest,
    build_fsj_early_evidence_packet,
    build_fsj_role_policy,
)
from ifa_data_platform.fsj.store import FSJStore

BJ_TZ = ZoneInfo("Asia/Shanghai")
EARLY_MAIN_PRODUCER = "ifa_data_platform.fsj.early_main_producer"
EARLY_MAIN_PRODUCER_VERSION = "phase1-main-early-v1"


@dataclass(frozen=True)
class EarlyEvidenceRecord:
    source_layer: str
    source_family: str
    source_table: str
    source_record_key: str
    observed_label: str
    observed_payload: dict[str, Any]
    observed_at: str | None = None


@dataclass(frozen=True)
class EarlyMainProducerInput:
    business_date: str
    slot: str
    section_key: str
    section_type: str
    bundle_topic_key: str
    summary_topic: str
    trading_day_open: bool
    trading_day_label: str
    focus_symbols: list[str]
    focus_list_types: list[str]
    focus_items: list[dict[str, Any]]
    auction_count: int
    auction_snapshot_time: str | None
    event_count: int
    event_latest_time: str | None
    event_titles: list[str]
    leader_count: int
    leader_symbols: list[str]
    signal_scope_count: int
    latest_signal_state: str | None
    text_catalyst_count: int
    text_catalyst_titles: list[str]
    previous_archive_summary: str | None
    replay_id: str | None = None
    slot_run_id: str | None = None
    report_run_id: str | None = None

    @property
    def has_high_evidence(self) -> bool:
        return self.auction_count > 0 or self.event_count > 0 or self.leader_count > 0 or self.signal_scope_count > 0

    @property
    def has_low_evidence(self) -> bool:
        return self.text_catalyst_count > 0


class EarlyMainInputReader(Protocol):
    def read(
        self,
        *,
        business_date: str,
        slot: str = "early",
        section_key: str = "pre_open_main",
    ) -> EarlyMainProducerInput: ...


class SqlEarlyMainInputReader:
    def __init__(self) -> None:
        self.engine = make_engine()

    def read(
        self,
        *,
        business_date: str,
        slot: str = "early",
        section_key: str = "pre_open_main",
    ) -> EarlyMainProducerInput:
        with self.engine.begin() as conn:
            trading_day_row = conn.execute(
                text(
                    """
                    select cal_date, is_open, pretrade_date
                    from ifa2.trade_cal_history
                    where exchange='SSE' and cal_date <= cast(:business_date as date)
                    order by cal_date desc, version_id desc nulls last
                    limit 1
                    """
                ),
                {"business_date": business_date},
            ).mappings().first()

            focus_rows = conn.execute(
                text(
                    """
                    select fi.symbol as symbol,
                           coalesce(
                               nullif(trim(fi.name), ''),
                               stock_basic_current_name.name,
                               stock_basic_history_name.name,
                               symbol_universe_name.name,
                               fi.symbol
                           ) as name,
                           coalesce(stock_basic_current_name.industry, stock_basic_history_name.industry) as sector_or_theme,
                           fl.list_type,
                           fi.priority,
                           case when fl.list_type like '%key_focus' then true else false end as is_key_focus,
                           market_evidence.has_daily_bar,
                           market_evidence.latest_trade_date,
                           market_evidence.recent_return_pct,
                           market_evidence.latest_volume,
                           market_evidence.latest_amount,
                           text_evidence.announcement_count,
                           text_evidence.research_count,
                           text_evidence.investor_qa_count,
                           text_evidence.dragon_tiger_count,
                           text_evidence.limit_up_count,
                           event_evidence.event_count
                    from ifa2.focus_lists fl
                    join ifa2.focus_list_items fi on fi.list_id = fl.id
                    left join lateral (
                        select nullif(trim(sbc.name), '') as name,
                               nullif(trim(sbc.industry), '') as industry
                        from ifa2.stock_basic_current sbc
                        where sbc.ts_code = fi.symbol
                           or sbc.symbol = split_part(fi.symbol, '.', 1)
                        order by case when sbc.ts_code = fi.symbol then 0 else 1 end,
                                 sbc.ts_code,
                                 sbc.symbol
                        limit 1
                    ) stock_basic_current_name on true
                    left join lateral (
                        select nullif(trim(sbh.name), '') as name,
                               nullif(trim(sbh.industry), '') as industry
                        from ifa2.stock_basic_history sbh
                        where sbh.ts_code = fi.symbol
                           or sbh.symbol = split_part(fi.symbol, '.', 1)
                        order by case when sbh.ts_code = fi.symbol then 0 else 1 end,
                                 sbh.ts_code,
                                 sbh.symbol
                        limit 1
                    ) stock_basic_history_name on true
                    left join lateral (
                        select min(nullif(trim(su.name), '')) as name
                        from ifa2.symbol_universe su
                        where su.symbol = fi.symbol
                    ) symbol_universe_name on true
                    left join lateral (
                        select true as has_daily_bar,
                               latest.trade_date::text as latest_trade_date,
                               case
                                   when prev.close is not null and prev.close <> 0
                                   then round(((latest.close - prev.close) / prev.close) * 100.0, 2)
                                   else null
                               end as recent_return_pct,
                               latest.vol as latest_volume,
                               latest.amount as latest_amount
                        from lateral (
                            select edbh.trade_date, edbh.close, edbh.vol, edbh.amount
                            from ifa2.equity_daily_bar_history edbh
                            where edbh.ts_code = fi.symbol
                              and edbh.trade_date <= cast(:business_date as date)
                            order by edbh.trade_date desc
                            limit 1
                        ) latest
                        left join lateral (
                            select edbh.close
                            from ifa2.equity_daily_bar_history edbh
                            where edbh.ts_code = fi.symbol
                              and edbh.trade_date < latest.trade_date
                            order by edbh.trade_date desc
                            limit 1
                        ) prev on true
                    ) market_evidence on true
                    left join lateral (
                        select
                            count(*) filter (where src = 'announcement') as announcement_count,
                            count(*) filter (where src = 'research') as research_count,
                            count(*) filter (where src = 'investor_qa') as investor_qa_count,
                            count(*) filter (where src = 'dragon_tiger') as dragon_tiger_count,
                            count(*) filter (where src = 'limit_up') as limit_up_count
                        from (
                            select 'announcement' as src
                            from ifa2.announcements_history ah
                            where ah.ts_code = fi.symbol
                              and ah.ann_date in (cast(:business_date as date), cast(:business_date as date) - interval '1 day')
                            union all
                            select 'research' as src
                            from ifa2.research_reports_history rrh
                            where rrh.ts_code = fi.symbol
                              and rrh.trade_date in (cast(:business_date as date), cast(:business_date as date) - interval '1 day')
                            union all
                            select 'investor_qa' as src
                            from ifa2.investor_qa_history iqh
                            where iqh.ts_code = fi.symbol
                              and iqh.trade_date in (cast(:business_date as date), cast(:business_date as date) - interval '1 day')
                            union all
                            select 'dragon_tiger' as src
                            from ifa2.dragon_tiger_list_history dtlh
                            where dtlh.ts_code = fi.symbol
                              and dtlh.trade_date in (cast(:business_date as date), cast(:business_date as date) - interval '1 day')
                            union all
                            select 'limit_up' as src
                            from ifa2.limit_up_detail_history ludh
                            where ludh.ts_code = fi.symbol
                              and ludh.trade_date in (cast(:business_date as date), cast(:business_date as date) - interval '1 day')
                        ) text_union
                    ) text_evidence on true
                    left join lateral (
                        select count(*) as event_count
                        from ifa2.highfreq_event_stream_working hesw
                        where upper(hesw.symbol) = upper(fi.symbol)
                          and hesw.event_time::date = cast(:business_date as date)
                    ) event_evidence on true
                    where fl.owner_type='default' and fl.owner_id='default'
                      and fl.list_type in ('key_focus','focus','tech_key_focus','tech_focus')
                      and coalesce(fi.asset_category, 'stock') = 'stock'
                      and fi.is_active = true
                      and fi.symbol is not null
                    order by fi.symbol,
                             case when fl.list_type like '%key_focus' then 0 else 1 end,
                             fi.priority nulls last,
                             fl.list_type
                    """
                ),
                {"business_date": business_date}
            ).mappings().all()
            focus_symbols = sorted({row["symbol"] for row in focus_rows})
            focus_list_types = sorted({row["list_type"] for row in focus_rows})
            focus_item_map: dict[str, dict[str, Any]] = {}
            for row in focus_rows:
                symbol = str(row.get("symbol") or "").strip()
                if not symbol:
                    continue
                item = focus_item_map.setdefault(
                    symbol,
                    {
                        "symbol": symbol,
                        "name": str(row.get("name") or "").strip() or symbol,
                        "company_name": str(row.get("name") or "").strip() or symbol,
                        "list_types": [],
                        "list_type": str(row.get("list_type") or "").strip() or None,
                        "priority": row.get("priority"),
                        "key_focus": bool(row.get("is_key_focus")),
                        "sector_or_theme": str(row.get("sector_or_theme") or "").strip() or None,
                        "market_evidence": {
                            "has_daily_bar": bool(row.get("has_daily_bar")),
                            "latest_trade_date": str(row.get("latest_trade_date") or "").strip() or None,
                            "recent_return_pct": row.get("recent_return_pct"),
                            "latest_volume": row.get("latest_volume"),
                            "latest_amount": row.get("latest_amount"),
                        },
                        "text_event_evidence": {
                            "announcement_count": int(row.get("announcement_count") or 0),
                            "research_count": int(row.get("research_count") or 0),
                            "investor_qa_count": int(row.get("investor_qa_count") or 0),
                            "dragon_tiger_count": int(row.get("dragon_tiger_count") or 0),
                            "limit_up_count": int(row.get("limit_up_count") or 0),
                            "event_count": int(row.get("event_count") or 0),
                        },
                    },
                )
                list_type = str(row.get("list_type") or "").strip()
                if list_type and list_type not in item["list_types"]:
                    item["list_types"].append(list_type)
                if item.get("priority") is None and row.get("priority") is not None:
                    item["priority"] = row.get("priority")
                if item.get("list_type") is None and list_type:
                    item["list_type"] = list_type
                item["key_focus"] = bool(item.get("key_focus") or row.get("is_key_focus") or ("key_focus" in list_type))
                if not item.get("sector_or_theme") and row.get("sector_or_theme"):
                    item["sector_or_theme"] = str(row.get("sector_or_theme") or "").strip() or None
                market_evidence = dict(item.get("market_evidence") or {})
                if row.get("has_daily_bar"):
                    market_evidence["has_daily_bar"] = True
                if not market_evidence.get("latest_trade_date") and row.get("latest_trade_date"):
                    market_evidence["latest_trade_date"] = str(row.get("latest_trade_date") or "").strip() or None
                for field in ("recent_return_pct", "latest_volume", "latest_amount"):
                    if market_evidence.get(field) is None and row.get(field) is not None:
                        market_evidence[field] = row.get(field)
                item["market_evidence"] = market_evidence
                text_event_evidence = dict(item.get("text_event_evidence") or {})
                for field in ("announcement_count", "research_count", "investor_qa_count", "dragon_tiger_count", "limit_up_count", "event_count"):
                    text_event_evidence[field] = max(int(text_event_evidence.get(field) or 0), int(row.get(field) or 0))
                item["text_event_evidence"] = text_event_evidence
            focus_items = sorted(
                focus_item_map.values(),
                key=lambda item: (
                    0 if any("key_focus" in str(list_type) for list_type in (item.get("list_types") or [])) else 1,
                    item.get("priority") if item.get("priority") is not None else 999999,
                    str(item.get("symbol") or ""),
                ),
            )

            auction_row = conn.execute(
                text(
                    """
                    select count(*) as cnt, max(trade_date::text) as snapshot_time
                    from ifa2.highfreq_open_auction_working
                    where trade_date = cast(:business_date as date)
                    """
                ),
                {"business_date": business_date},
            ).mappings().one()

            event_rows = conn.execute(
                text(
                    """
                    select title, event_time
                    from ifa2.highfreq_event_stream_working
                    where event_time::date = cast(:business_date as date)
                    order by event_time desc
                    limit 8
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            leader_rows = conn.execute(
                text(
                    """
                    select symbol
                    from ifa2.highfreq_leader_candidate_working
                    where trade_time::date = cast(:business_date as date)
                    order by candidate_score desc, trade_time desc
                    limit 10
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            signal_rows = conn.execute(
                text(
                    """
                    select validation_state, trade_time
                    from ifa2.highfreq_intraday_signal_state_working
                    where trade_time::date = cast(:business_date as date)
                    order by trade_time desc
                    limit 2
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            text_rows = conn.execute(
                text(
                    """
                    with latest_text as (
                        select title, datetime as published_at from ifa2.news_history
                        where datetime::date in (cast(:business_date as date), (cast(:business_date as date) - interval '1 day'))
                        union all
                        select title, rec_time as published_at from ifa2.announcements_history
                        where ann_date in (cast(:business_date as date), (cast(:business_date as date) - interval '1 day'))
                        union all
                        select title, trade_date::timestamp as published_at from ifa2.research_reports_history
                        where trade_date in (cast(:business_date as date), (cast(:business_date as date) - interval '1 day'))
                        union all
                        select left(coalesce(q, 'investor_qa'), 80) as title, pub_time as published_at from ifa2.investor_qa_history
                        where trade_date in (cast(:business_date as date), (cast(:business_date as date) - interval '1 day'))
                    )
                    select title, published_at
                    from latest_text
                    order by published_at desc nulls last
                    limit 8
                    """
                ),
                {"business_date": business_date},
            ).mappings().all()

            archive_row = conn.execute(
                text(
                    """
                    select summary
                    from ifa2.ifa_fsj_bundles
                    where market='a_share'
                      and slot='late'
                      and agent_domain='main'
                      and section_key in ('post_close_main', 'main_thesis')
                      and status='active'
                      and business_date < cast(:business_date as date)
                    order by business_date desc, created_at desc
                    limit 1
                    """
                ),
                {"business_date": business_date},
            ).mappings().first()

        selected_focus_symbols = focus_symbols[:30]
        selected_focus_symbol_set = set(selected_focus_symbols)
        selected_focus_items = [item for item in focus_items if str(item.get("symbol") or "") in selected_focus_symbol_set]

        event_latest_time = event_rows[0]["event_time"].isoformat() if event_rows else None
        signal_latest_time = signal_rows[0]["trade_time"].isoformat() if signal_rows else None
        latest_signal_state = signal_rows[0]["validation_state"] if signal_rows else None
        return EarlyMainProducerInput(
            business_date=business_date,
            slot=slot,
            section_key=section_key,
            section_type="thesis",
            bundle_topic_key=f"mainline_candidate:{business_date}",
            summary_topic="A股盘前主线预案",
            trading_day_open=bool(trading_day_row["is_open"]) if trading_day_row is not None else False,
            trading_day_label=(
                ("open" if trading_day_row["is_open"] else "closed")
                if trading_day_row is not None and str(trading_day_row["cal_date"]) == business_date
                else "calendar_fallback"
            ),
            focus_symbols=selected_focus_symbols,
            focus_list_types=focus_list_types,
            focus_items=selected_focus_items,
            auction_count=int(auction_row["cnt"] or 0),
            auction_snapshot_time=auction_row["snapshot_time"],
            event_count=len(event_rows),
            event_latest_time=event_latest_time,
            event_titles=[row["title"] for row in event_rows if row.get("title")],
            leader_count=len(leader_rows),
            leader_symbols=[row["symbol"] for row in leader_rows if row.get("symbol")],
            signal_scope_count=len(signal_rows),
            latest_signal_state=latest_signal_state,
            text_catalyst_count=len(text_rows),
            text_catalyst_titles=[row["title"] for row in text_rows if row.get("title")],
            previous_archive_summary=archive_row["summary"] if archive_row else None,
            slot_run_id=None,
            replay_id=None,
            report_run_id=None,
        )


class EarlyMainFSJAssembler:
    def __init__(self, *, llm_assistant: FSJEarlyLLMAssistant | None = None) -> None:
        self.llm_assistant = llm_assistant or FSJEarlyLLMAssistant()

    def build_bundle_graph(self, data: EarlyMainProducerInput) -> dict[str, Any]:
        object_records: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        evidence_links: list[dict[str, Any]] = []
        observed_records: list[dict[str, Any]] = []

        bundle_id = self._bundle_id(data)
        completeness_label = self._completeness_label(data)
        degrade_reason = self._degrade_reason(data)
        contract_mode = self._contract_mode(data)
        llm_result = None
        llm_audit: dict[str, Any] = {"applied": False, "reason": "early_llm_assist_not_attempted"}
        if data.has_high_evidence or data.has_low_evidence:
            llm_result, llm_audit = self.llm_assistant.maybe_synthesize(
                FSJEarlyLLMRequest(
                    business_date=data.business_date,
                    section_key=data.section_key,
                    contract_mode=contract_mode,
                    completeness_label=completeness_label,
                    degrade_reason=degrade_reason,
                    evidence_packet=build_fsj_early_evidence_packet(
                        data,
                        contract_mode=contract_mode,
                        completeness_label=completeness_label,
                        degrade_reason=degrade_reason,
                    ),
                )
            )
        payload_meta = self._payload_meta(data, completeness_label, degrade_reason, contract_mode, llm_audit)

        fact_market = self._append_fact(
            object_records,
            data=data,
            object_key="fact:early:market_inputs",
            statement=self._market_fact_statement(data),
            object_type="market",
            confidence="medium" if data.has_high_evidence else "low",
            evidence_level="E2" if data.has_high_evidence else "E3",
            metric_refs=["auction_count", "event_count", "leader_count", "signal_scope_count"],
            attributes_json={
                "freshness_label": "fresh" if data.has_high_evidence else "stale-hard",
                "completeness_label": "partial" if data.has_high_evidence else "sparse",
                "is_finalized_equivalent": False,
                "degrade_reason": None if data.has_high_evidence else "missing_preopen_high_layer",
            },
        )
        observed_records.extend(
            self._build_observed_records(
                fact_market,
                [
                    EarlyEvidenceRecord(
                        source_layer="highfreq",
                        source_family="open_auction_snapshot",
                        source_table="ifa2.highfreq_open_auction_working",
                        source_record_key=f"{data.business_date}:auction",
                        observed_label="盘前竞价快照覆盖",
                        observed_payload={"auction_count": data.auction_count, "snapshot_time": data.auction_snapshot_time},
                        observed_at=data.auction_snapshot_time,
                    ),
                    EarlyEvidenceRecord(
                        source_layer="highfreq",
                        source_family="event_time_stream",
                        source_table="ifa2.highfreq_event_stream_working",
                        source_record_key=f"{data.business_date}:events",
                        observed_label="盘前事件流覆盖",
                        observed_payload={"event_count": data.event_count, "latest_time": data.event_latest_time, "titles": data.event_titles[:5]},
                        observed_at=data.event_latest_time,
                    ),
                    EarlyEvidenceRecord(
                        source_layer="highfreq",
                        source_family="leader_candidate",
                        source_table="ifa2.highfreq_leader_candidate_working",
                        source_record_key=f"{data.business_date}:leaders",
                        observed_label="盘前候选龙头覆盖",
                        observed_payload={"leader_count": data.leader_count, "symbols": data.leader_symbols[:5]},
                    ),
                    EarlyEvidenceRecord(
                        source_layer="highfreq",
                        source_family="intraday_signal_state",
                        source_table="ifa2.highfreq_intraday_signal_state_working",
                        source_record_key=f"{data.business_date}:signal_state",
                        observed_label="盘前信号状态覆盖",
                        observed_payload={"signal_scope_count": data.signal_scope_count, "latest_signal_state": data.latest_signal_state},
                        observed_at=data.event_latest_time or signal_latest_time(data),
                    ),
                ],
            )
        )
        evidence_links.extend(
            self._build_evidence_links(
                fact_market,
                [
                    ("source_observed", "highfreq", "open_auction_snapshot", "ifa2.highfreq_open_auction_working", f"{data.business_date}:auction", {"snapshot_time": data.auction_snapshot_time}),
                    ("source_observed", "highfreq", "event_time_stream", "ifa2.highfreq_event_stream_working", f"{data.business_date}:events", {"latest_time": data.event_latest_time}),
                ],
            )
        )

        fact_reference = self._append_fact(
            object_records,
            data=data,
            object_key="fact:early:reference_scope",
            statement=self._reference_fact_statement(data),
            object_type="reference",
            confidence="high" if data.focus_symbols else "low",
            evidence_level="E3",
            entity_refs=data.focus_symbols[:8],
            attributes_json={
                "freshness_label": "fresh-reference",
                "completeness_label": "complete" if data.focus_symbols else "missing",
                "is_finalized_equivalent": False,
                "source_list_types": data.focus_list_types,
            },
        )
        observed_records.extend(
            self._build_observed_records(
                fact_reference,
                [
                    EarlyEvidenceRecord(
                        source_layer="business_seed",
                        source_family="focus_lists",
                        source_table="ifa2.focus_lists+ifa2.focus_list_items",
                        source_record_key=f"default:{data.business_date}:focus_scope",
                        observed_label="当前业务 seed/focus 覆盖",
                        observed_payload={"focus_symbols": data.focus_symbols[:10], "focus_list_types": data.focus_list_types},
                    )
                ],
            )
        )
        evidence_links.extend(
            self._build_evidence_links(
                fact_reference,
                [
                    ("source_observed", "business_seed", "focus_lists", "ifa2.focus_lists", "default:focus_scope", {"list_types": data.focus_list_types}),
                ],
            )
        )

        extra_fact_keys: list[str] = [fact_market["object_key"], fact_reference["object_key"]]
        if data.has_low_evidence:
            fact_catalyst = self._append_fact(
                object_records,
                data=data,
                object_key="fact:early:text_catalysts",
                statement=self._text_fact_statement(data),
                object_type="news",
                confidence="medium",
                evidence_level="E2",
                attributes_json={
                    "freshness_label": "fresh-reference",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": False,
                },
            )
            extra_fact_keys.append(fact_catalyst["object_key"])
            observed_records.extend(
                self._build_observed_records(
                    fact_catalyst,
                    [
                        EarlyEvidenceRecord(
                            source_layer="lowfreq",
                            source_family="latest_text",
                            source_table="ifa2.news_history+ifa2.announcements_history+ifa2.research_reports_history+ifa2.investor_qa_history",
                            source_record_key=f"{data.business_date}:text_catalysts",
                            observed_label="隔夜/近期文本催化",
                            observed_payload={"titles": data.text_catalyst_titles[:6], "count": data.text_catalyst_count},
                        )
                    ],
                )
            )
            evidence_links.extend(
                self._build_evidence_links(
                    fact_catalyst,
                    [
                        ("source_observed", "lowfreq", "latest_text", "ifa2.news_history", f"{data.business_date}:text_catalysts", {"count": data.text_catalyst_count}),
                    ],
                )
            )

        if data.previous_archive_summary:
            fact_background = self._append_fact(
                object_records,
                data=data,
                object_key="fact:early:t_minus_1_background",
                statement=f"T-1 背景锚点：{data.previous_archive_summary}",
                object_type="background",
                confidence="medium",
                evidence_level="E1",
                attributes_json={
                    "freshness_label": "historical-reference",
                    "completeness_label": "partial",
                    "is_finalized_equivalent": True,
                },
            )
            extra_fact_keys.append(fact_background["object_key"])
            evidence_links.extend(
                self._build_evidence_links(
                    fact_background,
                    [
                        ("historical_reference", "archive_v2", "fsj_bundle", "ifa2.ifa_fsj_bundles", f"late:<{data.business_date}", {"summary": data.previous_archive_summary}),
                    ],
                )
            )

        signal_record = self._append_signal(
            object_records,
            data=data,
            object_key="signal:early:mainline_candidate_state",
            statement=llm_result.candidate_signal_statement if llm_result else self._signal_statement(data),
            signal_strength="medium" if data.has_high_evidence else "low",
            confidence="medium" if (data.has_high_evidence or data.has_low_evidence) else "low",
            attributes_json={
                "based_on_fact_keys": extra_fact_keys,
                "degrade_reason": degrade_reason,
                "llm_assist_applied": bool(llm_result),
                "llm_reasoning_trace": llm_result.reasoning_trace if llm_result else [],
            },
        )
        for fact_key in extra_fact_keys:
            edges.append(
                {
                    "edge_type": "fact_to_signal",
                    "from_fsj_kind": "fact",
                    "from_object_key": fact_key,
                    "to_fsj_kind": "signal",
                    "to_object_key": signal_record["object_key"],
                    "role": "support",
                }
            )

        judgment_record = self._append_judgment(
            object_records,
            data=data,
            object_key="judgment:early:mainline_plan",
            statement=llm_result.judgment_statement if llm_result else self._judgment_statement(data),
            object_type="thesis" if data.has_high_evidence else "watch_item",
            judgment_action="validate" if data.has_high_evidence else "watch",
            direction="conditional",
            priority="p0",
            confidence="medium" if data.has_high_evidence else "low",
            invalidators=llm_result.invalidators if llm_result else self._invalidators(data),
            attributes_json={
                "required_open_validation": True,
                "contract_mode": contract_mode,
                "deferred": [
                    "support-agent merge not yet implemented",
                    "section-level multi-judgment expansion deferred",
                    "no late/final evidence implied in early slot",
                ],
                "llm_assist_applied": bool(llm_result),
                "llm_reasoning_trace": llm_result.reasoning_trace if llm_result else [],
            },
        )
        edges.append(
            {
                "edge_type": "signal_to_judgment",
                "from_fsj_kind": "signal",
                "from_object_key": signal_record["object_key"],
                "to_fsj_kind": "judgment",
                "to_object_key": judgment_record["object_key"],
                "role": "support",
            }
        )

        replay_id = data.replay_id or self._default_runtime_id(data, kind="replay")
        slot_run_id = data.slot_run_id or self._default_runtime_id(data, kind="slot_run")

        if replay_id:
            evidence_links.append(
                {
                    "object_key": None,
                    "fsj_kind": None,
                    "evidence_role": "slot_replay",
                    "ref_system": "runtime",
                    "ref_family": "slot_replay",
                    "ref_table": "ifa2.slot_replay_evidence",
                    "ref_key": replay_id,
                    "ref_locator_json": {"replay_id": replay_id},
                }
            )

        bundle = {
            "bundle_id": bundle_id,
            "market": "a_share",
            "business_date": data.business_date,
            "slot": data.slot,
            "agent_domain": "main",
            "section_key": data.section_key,
            "section_type": data.section_type,
            "bundle_topic_key": data.bundle_topic_key,
            "producer": EARLY_MAIN_PRODUCER,
            "producer_version": EARLY_MAIN_PRODUCER_VERSION,
            "assembly_mode": "contract_driven_first_slice",
            "status": "active",
            "supersedes_bundle_id": None,
            "slot_run_id": slot_run_id,
            "replay_id": replay_id,
            "report_run_id": data.report_run_id,
            "summary": llm_result.summary if llm_result else self._bundle_summary(data),
            "payload_json": payload_meta,
        }
        return {
            "bundle": bundle,
            "objects": object_records,
            "edges": edges,
            "evidence_links": evidence_links,
            "observed_records": observed_records,
            "report_links": [],
        }

    def _append_fact(self, objects: list[dict[str, Any]], *, data: EarlyMainProducerInput, object_key: str, statement: str, object_type: str, confidence: str, evidence_level: str, entity_refs: Sequence[str] | None = None, metric_refs: Sequence[str] | None = None, attributes_json: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "object_id": object_key,
            "fsj_kind": "fact",
            "object_key": object_key,
            "statement": statement,
            "object_type": object_type,
            "confidence": confidence,
            "evidence_level": evidence_level,
            "entity_refs": list(entity_refs or []),
            "metric_refs": list(metric_refs or []),
            "attributes_json": attributes_json or {},
        }
        objects.append(record)
        return record

    def _append_signal(self, objects: list[dict[str, Any]], *, data: EarlyMainProducerInput, object_key: str, statement: str, signal_strength: str, confidence: str, attributes_json: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "object_id": object_key,
            "fsj_kind": "signal",
            "object_key": object_key,
            "statement": statement,
            "object_type": "confirmation" if data.has_high_evidence else "risk",
            "signal_strength": signal_strength,
            "horizon": "same_day",
            "confidence": confidence,
            "attributes_json": attributes_json or {},
        }
        objects.append(record)
        return record

    def _append_judgment(self, objects: list[dict[str, Any]], *, data: EarlyMainProducerInput, object_key: str, statement: str, object_type: str, judgment_action: str, direction: str, priority: str, confidence: str, invalidators: Sequence[str], attributes_json: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "object_id": object_key,
            "fsj_kind": "judgment",
            "object_key": object_key,
            "statement": statement,
            "object_type": object_type,
            "judgment_action": judgment_action,
            "direction": direction,
            "priority": priority,
            "confidence": confidence,
            "invalidators": list(invalidators),
            "attributes_json": attributes_json or {},
        }
        objects.append(record)
        return record

    def _build_observed_records(self, obj: dict[str, Any], evidence: Sequence[EarlyEvidenceRecord]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in evidence:
            records.append(
                {
                    "object_key": obj["object_key"],
                    "fsj_kind": obj["fsj_kind"],
                    "source_layer": item.source_layer,
                    "source_family": item.source_family,
                    "source_table": item.source_table,
                    "source_record_key": item.source_record_key,
                    "observed_label": item.observed_label,
                    "observed_payload_json": item.observed_payload,
                }
            )
        return records

    def _build_evidence_links(self, obj: dict[str, Any], refs: Sequence[tuple[str, str, str, str, str, dict[str, Any]]]) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []
        for evidence_role, ref_system, ref_family, ref_table, ref_key, ref_locator_json in refs:
            links.append(
                {
                    "object_key": obj["object_key"],
                    "fsj_kind": obj["fsj_kind"],
                    "evidence_role": evidence_role,
                    "ref_system": ref_system,
                    "ref_family": ref_family,
                    "ref_table": ref_table,
                    "ref_key": ref_key,
                    "ref_locator_json": ref_locator_json,
                }
            )
        return links

    def _bundle_id(self, data: EarlyMainProducerInput) -> str:
        seed = f"a_share|{data.business_date}|{data.slot}|main|{data.section_key}|{data.bundle_topic_key}|{EARLY_MAIN_PRODUCER_VERSION}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
        return f"fsj:a_share:{data.business_date}:{data.slot}:main:{data.section_key}:{digest}"

    def _default_runtime_id(self, data: EarlyMainProducerInput, *, kind: str) -> str:
        seed = f"a_share|{data.business_date}|{data.slot}|main|{data.section_key}|{data.bundle_topic_key}|{kind}|{EARLY_MAIN_PRODUCER_VERSION}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
        return f"fsj-runtime:{kind}:{data.business_date}:{data.slot}:{digest}"

    def _payload_meta(self, data: EarlyMainProducerInput, completeness_label: str, degrade_reason: str | None, contract_mode: str, llm_audit: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": EARLY_MAIN_PRODUCER_VERSION,
            "contract_source": "A_SHARE_EARLY_MID_LATE_DATA_CONSUMPTION_CONTRACT_V1",
            "focus_scope": {
                "focus_symbols": data.focus_symbols,
                "focus_symbol_count": len(data.focus_symbols),
                "focus_list_types": data.focus_list_types,
                "items": data.focus_items,
                "name_map": {item["symbol"]: item["name"] for item in data.focus_items if item.get("symbol") and item.get("name")},
                "source": "ifa2.focus_lists+ifa2.focus_list_items",
                "why_included": self._reference_fact_statement(data),
            },
            "implemented_scope": {
                "slot": "early",
                "agent_domain": "main",
                "section": data.section_key,
                "included_inputs": [
                    "trade_cal_history",
                    "focus_lists",
                    "highfreq_open_auction_working",
                    "highfreq_event_stream_working",
                    "highfreq_leader_candidate_working",
                    "highfreq_intraday_signal_state_working",
                    "recent lowfreq text catalysts",
                    "optional T-1 FSJ background",
                ],
                "deferred_inputs": [
                    "support-agent merge",
                    "chain mapping / sector-level explicit object graph",
                    "late/final evidence",
                    "report artifact linking",
                ],
            },
            "degrade": {
                "contract_mode": contract_mode,
                "completeness_label": completeness_label,
                "degrade_reason": degrade_reason,
                "has_high_evidence": data.has_high_evidence,
                "has_low_evidence": data.has_low_evidence,
                "candidate_only": contract_mode == "candidate_only",
            },
            "llm_assist": llm_audit,
            "llm_role_policy": build_fsj_role_policy(
                slot="early",
                contract_mode=contract_mode,
                completeness_label=completeness_label,
                degrade_reason=degrade_reason,
            ),
        }

    def _bundle_summary(self, data: EarlyMainProducerInput) -> str:
        if data.has_high_evidence:
            return f"{data.summary_topic}：已基于盘前 high+reference 形成待开盘验证的主线候选。"
        if data.has_low_evidence:
            return f"{data.summary_topic}：仅形成事件驱动候选，尚无足够盘前市场侧确认。"
        return f"{data.summary_topic}：仅保留观察清单，未形成可确认的盘前主线结论。"

    def _market_fact_statement(self, data: EarlyMainProducerInput) -> str:
        return (
            f"盘前市场侧输入覆盖：竞价样本 {data.auction_count} 条，事件流 {data.event_count} 条，"
            f"候选龙头 {data.leader_count} 个，信号状态 {data.signal_scope_count} 条。"
        )

    def _reference_fact_statement(self, data: EarlyMainProducerInput) -> str:
        return (
            f"当前业务观察池覆盖 {len(data.focus_symbols)} 个 A 股 focus/key-focus 对象，"
            f"可作为盘前主线验证与噪音过滤锚点。"
        )

    def _text_fact_statement(self, data: EarlyMainProducerInput) -> str:
        preview = "；".join(data.text_catalyst_titles[:3])
        return f"隔夜/近期文本催化共 {data.text_catalyst_count} 条，最新线索包括：{preview or '暂无标题样本'}。"

    def _signal_statement(self, data: EarlyMainProducerInput) -> str:
        if data.has_high_evidence:
            return "盘前 high layer 与 reference seed 已足以形成待开盘验证的主线候选，但仍不应视为已确认。"
        if data.has_low_evidence:
            return "当前仅看到文本/事件催化与 seed 锚点，主线仍停留在事件驱动候选阶段。"
        return "当前缺少可验证的盘前市场侧输入，只能保留观察对象与验证清单。"

    def _judgment_statement(self, data: EarlyMainProducerInput) -> str:
        if data.has_high_evidence:
            return "将当前候选主线作为开盘首要验证对象；若竞价强度和事件延续性无法继续兑现，则立即降回观察项。"
        if data.has_low_evidence:
            return "仅将隔夜催化对应方向列为观察候选，不输出‘今日主线已成立’式判断。"
        return "本时段只保留 focus 观察池和开盘验证计划，不形成正式 thesis judgment。"

    def _completeness_label(self, data: EarlyMainProducerInput) -> str:
        if data.has_high_evidence:
            return "complete"
        if data.has_low_evidence:
            return "partial"
        return "sparse"

    def _degrade_reason(self, data: EarlyMainProducerInput) -> str | None:
        if data.has_high_evidence:
            return None
        if data.has_low_evidence:
            return "missing_preopen_high_layer"
        return "observation_scope_only"

    def _contract_mode(self, data: EarlyMainProducerInput) -> str:
        if data.has_high_evidence:
            return "candidate_with_open_validation"
        if data.has_low_evidence:
            return "candidate_only"
        return "watchlist_only"

    def _invalidators(self, data: EarlyMainProducerInput) -> list[str]:
        invalidators = [
            "09:27/开盘前后高频覆盖未刷新或快速失真",
            "竞价与事件流未能在 focus 池中形成一致强化",
        ]
        if data.has_low_evidence:
            invalidators.append("文本催化无法获得盘前市场侧呼应")
        return invalidators


class EarlyMainFSJProducer:
    def __init__(
        self,
        *,
        reader: EarlyMainInputReader | None = None,
        assembler: EarlyMainFSJAssembler | None = None,
        store: FSJStore | None = None,
    ) -> None:
        self.reader = reader or SqlEarlyMainInputReader()
        self.assembler = assembler or EarlyMainFSJAssembler()
        self.store = store or FSJStore()

    def produce(
        self,
        *,
        business_date: str,
        slot: str = "early",
        section_key: str = "pre_open_main",
    ) -> dict[str, Any]:
        data = self.reader.read(business_date=business_date, slot=slot, section_key=section_key)
        return self.assembler.build_bundle_graph(data)

    def produce_and_persist(
        self,
        *,
        business_date: str,
        slot: str = "early",
        section_key: str = "pre_open_main",
    ) -> dict[str, Any]:
        payload = self.produce(business_date=business_date, slot=slot, section_key=section_key)
        self.store.upsert_bundle_graph(payload)
        bundle_id = payload["bundle"]["bundle_id"]
        graph = self.store.get_bundle_graph(bundle_id)
        if graph is None:
            raise RuntimeError(f"persisted FSJ bundle not found: {bundle_id}")
        return graph


def signal_latest_time(data: EarlyMainProducerInput) -> str | None:
    return data.event_latest_time
