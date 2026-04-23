from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Sequence

from sqlalchemy import text

from .store import FSJStore
from .support_common import SECTION_KEY_BY_DOMAIN, VALID_SUPPORT_AGENT_DOMAINS, ensure_support_contract

SLOT_ORDER: dict[str, int] = {"early": 10, "mid": 20, "late": 30}
STATUS_ORDER: dict[str, int] = {"active": 0, "superseded": 1, "withdrawn": 2}


@dataclass(frozen=True)
class MainReportSectionSpec:
    slot: str
    section_key: str
    section_render_key: str
    title: str
    order_index: int


DEFAULT_MAIN_REPORT_SECTION_SPECS: tuple[MainReportSectionSpec, ...] = (
    MainReportSectionSpec(
        slot="early",
        section_key="pre_open_main",
        section_render_key="main.pre_open",
        title="盘前主结论",
        order_index=10,
    ),
    MainReportSectionSpec(
        slot="mid",
        section_key="midday_main",
        section_render_key="main.midday",
        title="盘中主结论",
        order_index=20,
    ),
    MainReportSectionSpec(
        slot="late",
        section_key="post_close_main",
        section_render_key="main.post_close",
        title="收盘主结论",
        order_index=30,
    ),
)


class MainReportSectionAssembler:
    def __init__(self, specs: Sequence[MainReportSectionSpec] | None = None):
        self.specs = tuple(specs or DEFAULT_MAIN_REPORT_SECTION_SPECS)

    def build(
        self,
        bundle_graphs: Sequence[dict[str, Any]],
        *,
        business_date: str,
        market: str = "a_share",
        agent_domain: str = "main",
        include_empty: bool = False,
        support_bundle_graphs: Sequence[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        selected = self._select_effective_graphs(bundle_graphs)
        support_selected = self._select_support_graphs(support_bundle_graphs or [])
        sections: list[dict[str, Any]] = []
        for spec in self.specs:
            graph = selected.get((spec.slot, spec.section_key))
            support_summaries = support_selected.get(spec.slot, [])
            if graph is None and not include_empty and not support_summaries:
                continue
            sections.append(self._build_section(spec, graph, support_summaries=support_summaries))

        return {
            "artifact_type": "fsj_main_report_sections",
            "artifact_version": "v2",
            "market": market,
            "business_date": business_date,
            "agent_domain": agent_domain,
            "section_count": len(sections),
            "support_summary_domains": sorted({item["agent_domain"] for section in sections for item in (section.get("support_summaries") or [])}),
            "sections": sections,
        }

    def _select_effective_graphs(self, bundle_graphs: Sequence[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for graph in bundle_graphs:
            bundle = graph.get("bundle") or {}
            key = (str(bundle.get("slot") or ""), str(bundle.get("section_key") or ""))
            if not all(key):
                continue
            grouped.setdefault(key, []).append(graph)

        selected: dict[tuple[str, str], dict[str, Any]] = {}
        for key, graphs in grouped.items():
            selected[key] = sorted(graphs, key=self._bundle_rank)[0]
        return selected

    def _select_support_graphs(self, support_bundle_graphs: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for graph in support_bundle_graphs:
            bundle = graph.get("bundle") or {}
            slot = str(bundle.get("slot") or "")
            agent_domain = str(bundle.get("agent_domain") or "")
            section_key = str(bundle.get("section_key") or "")
            if agent_domain not in VALID_SUPPORT_AGENT_DOMAINS:
                continue
            if not slot or SECTION_KEY_BY_DOMAIN.get(agent_domain) != section_key:
                continue
            grouped.setdefault((slot, agent_domain), []).append(graph)

        selected_by_slot: dict[str, list[dict[str, Any]]] = {}
        for (slot, agent_domain), graphs in grouped.items():
            selected_by_slot.setdefault(slot, []).append(sorted(graphs, key=self._bundle_rank)[0])

        for slot, graphs in selected_by_slot.items():
            graphs.sort(key=lambda graph: str((graph.get("bundle") or {}).get("agent_domain") or ""))
        return selected_by_slot

    def _bundle_rank(self, graph: dict[str, Any]) -> tuple[int, int, str, str]:
        bundle = graph.get("bundle") or {}
        status = str(bundle.get("status") or "withdrawn")
        updated_at = self._sortable_ts(bundle.get("updated_at"))
        bundle_id = str(bundle.get("bundle_id") or "")
        supersedes = str(bundle.get("supersedes_bundle_id") or "")
        return (
            STATUS_ORDER.get(status, 99),
            -updated_at,
            "" if supersedes else "~",
            bundle_id,
        )

    def _build_section(self, spec: MainReportSectionSpec, graph: dict[str, Any] | None, *, support_summaries: Sequence[dict[str, Any]]) -> dict[str, Any]:
        if graph is None:
            return {
                "slot": spec.slot,
                "section_key": spec.section_key,
                "section_render_key": spec.section_render_key,
                "title": spec.title,
                "order_index": spec.order_index,
                "status": "missing",
                "bundle": None,
                "summary": None,
                "judgments": [],
                "signals": [],
                "facts": [],
                "support_summaries": [self._build_support_summary(graph) for graph in support_summaries],
                "lineage": None,
            }

        bundle = dict(graph.get("bundle") or {})
        objects = list(graph.get("objects") or [])
        return {
            "slot": spec.slot,
            "section_key": spec.section_key,
            "section_render_key": spec.section_render_key,
            "title": spec.title,
            "order_index": spec.order_index,
            "status": "ready",
            "bundle": {
                "bundle_id": bundle.get("bundle_id"),
                "status": bundle.get("status"),
                "supersedes_bundle_id": bundle.get("supersedes_bundle_id"),
                "bundle_topic_key": bundle.get("bundle_topic_key"),
                "producer": bundle.get("producer"),
                "producer_version": bundle.get("producer_version"),
                "section_type": bundle.get("section_type"),
                "slot_run_id": bundle.get("slot_run_id"),
                "replay_id": bundle.get("replay_id"),
                "report_run_id": bundle.get("report_run_id"),
                "updated_at": bundle.get("updated_at"),
            },
            "summary": bundle.get("summary"),
            "judgments": self._project_objects(objects, "judgment"),
            "signals": self._project_objects(objects, "signal"),
            "facts": self._project_objects(objects, "fact"),
            "support_summaries": [self._build_support_summary(support_graph) for support_graph in support_summaries],
            "lineage": {
                "bundle": bundle,
                "objects": sorted(objects, key=lambda row: (str(row.get("fsj_kind") or ""), str(row.get("object_key") or ""))),
                "edges": sorted(list(graph.get("edges") or []), key=lambda row: (str(row.get("edge_type") or ""), str(row.get("from_object_key") or ""), str(row.get("to_object_key") or ""))),
                "evidence_links": sorted(list(graph.get("evidence_links") or []), key=lambda row: (str(row.get("evidence_role") or ""), str(row.get("object_key") or ""), str(row.get("ref_system") or ""), str(row.get("ref_key") or ""))),
                "observed_records": sorted(list(graph.get("observed_records") or []), key=lambda row: (str(row.get("fsj_kind") or ""), str(row.get("object_key") or ""), str(row.get("source_layer") or ""), str(row.get("source_record_key") or ""))),
                "report_links": sorted(list(graph.get("report_links") or []), key=lambda row: (str(row.get("artifact_type") or ""), str(row.get("section_render_key") or ""), str(row.get("artifact_uri") or ""))),
                "support_bundle_ids": [item["bundle_id"] for item in [self._build_support_summary(support_graph) for support_graph in support_summaries]],
            },
        }

    def _build_support_summary(self, graph: dict[str, Any]) -> dict[str, Any]:
        bundle = dict(graph.get("bundle") or {})
        return {
            "bundle_id": bundle.get("bundle_id"),
            "slot": bundle.get("slot"),
            "agent_domain": bundle.get("agent_domain"),
            "section_key": bundle.get("section_key"),
            "bundle_topic_key": bundle.get("bundle_topic_key"),
            "status": bundle.get("status"),
            "summary": bundle.get("summary"),
            "producer": bundle.get("producer"),
            "producer_version": bundle.get("producer_version"),
            "slot_run_id": bundle.get("slot_run_id"),
            "replay_id": bundle.get("replay_id"),
            "report_run_id": bundle.get("report_run_id"),
            "updated_at": bundle.get("updated_at"),
            "lineage": {
                "report_links": sorted(list(graph.get("report_links") or []), key=lambda row: (str(row.get("artifact_type") or ""), str(row.get("section_render_key") or ""), str(row.get("artifact_uri") or ""))),
                "evidence_links": sorted(list(graph.get("evidence_links") or []), key=lambda row: (str(row.get("evidence_role") or ""), str(row.get("object_key") or ""), str(row.get("ref_system") or ""), str(row.get("ref_key") or ""))),
            },
        }

    def _project_objects(self, objects: Iterable[dict[str, Any]], fsj_kind: str) -> list[dict[str, Any]]:
        rows = [obj for obj in objects if obj.get("fsj_kind") == fsj_kind]
        rows.sort(key=lambda row: (str(row.get("object_key") or ""), str(row.get("statement") or "")))
        projected: list[dict[str, Any]] = []
        for row in rows:
            projected.append(
                {
                    "object_key": row.get("object_key"),
                    "statement": row.get("statement"),
                    "object_type": row.get("object_type"),
                    "signal_strength": row.get("signal_strength"),
                    "judgment_action": row.get("judgment_action"),
                    "confidence": row.get("confidence"),
                    "evidence_level": row.get("evidence_level"),
                    "priority": row.get("priority"),
                    "direction": row.get("direction"),
                    "horizon": row.get("horizon"),
                    "attributes_json": row.get("attributes_json"),
                    "invalidators": row.get("invalidators"),
                }
            )
        return projected

    def _sortable_ts(self, value: Any) -> int:
        if not value:
            return 0
        if isinstance(value, datetime):
            return int(value.timestamp())
        text_value = str(value)
        try:
            return int(datetime.fromisoformat(text_value.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return 0


SUPPORT_DOMAIN_TITLES: dict[str, str] = {
    "macro": "宏观 support",
    "commodities": "商品 support",
    "ai_tech": "AI / 科技 support",
}

SUPPORT_SLOT_TITLES: dict[str, str] = {
    "early": "盘前",
    "late": "收盘后",
}


class FSJReportAssemblyStore(FSJStore):
    def list_bundle_graphs(
        self,
        *,
        business_date: str,
        agent_domain: str,
        slots: Sequence[str] | None = None,
        section_keys: Sequence[str] | None = None,
        statuses: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        sql = """
        SELECT bundle_id
          FROM ifa2.ifa_fsj_bundles
         WHERE business_date=:business_date
           AND agent_domain=:agent_domain
        """
        params: dict[str, Any] = {
            "business_date": business_date,
            "agent_domain": agent_domain,
        }
        if slots:
            sql += " AND slot = ANY(CAST(:slots AS text[]))"
            params["slots"] = list(slots)
        if section_keys:
            sql += " AND section_key = ANY(CAST(:section_keys AS text[]))"
            params["section_keys"] = list(section_keys)
        if statuses:
            sql += " AND status = ANY(CAST(:statuses AS text[]))"
            params["statuses"] = list(statuses)
        sql += " ORDER BY business_date, slot, section_key, updated_at DESC, bundle_id"
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [self.get_bundle_graph(row["bundle_id"]) for row in rows if row.get("bundle_id")]


class MainReportAssemblyService:
    def __init__(
        self,
        store: FSJReportAssemblyStore,
        assembler: MainReportSectionAssembler | None = None,
    ):
        self.store = store
        self.assembler = assembler or MainReportSectionAssembler()

    def assemble_main_sections(self, *, business_date: str, include_empty: bool = False) -> dict[str, Any]:
        graphs = self.store.list_bundle_graphs(
            business_date=business_date,
            agent_domain="main",
            slots=[spec.slot for spec in self.assembler.specs],
            section_keys=[spec.section_key for spec in self.assembler.specs],
            statuses=["active", "superseded", "withdrawn"],
        )
        support_graphs: list[dict[str, Any]] = []
        support_slots = sorted({spec.slot for spec in self.assembler.specs if spec.slot in {"early", "late"}})
        for support_domain in sorted(VALID_SUPPORT_AGENT_DOMAINS):
            support_graphs.extend(
                self.store.list_bundle_graphs(
                    business_date=business_date,
                    agent_domain=support_domain,
                    slots=support_slots,
                    section_keys=[SECTION_KEY_BY_DOMAIN[support_domain]],
                    statuses=["active", "superseded", "withdrawn"],
                )
            )
        return self.assembler.build(
            graphs,
            business_date=business_date,
            market="a_share",
            agent_domain="main",
            include_empty=include_empty,
            support_bundle_graphs=support_graphs,
        )


class SupportReportAssemblyService:
    def __init__(self, store: FSJReportAssemblyStore) -> None:
        self.store = store
        self._main_assembler = MainReportSectionAssembler()

    def assemble_support_section(
        self,
        *,
        business_date: str,
        agent_domain: str,
        slot: str,
    ) -> dict[str, Any]:
        section_key = SECTION_KEY_BY_DOMAIN[agent_domain]
        ensure_support_contract(agent_domain=agent_domain, slot=slot, section_key=section_key)
        graphs = self.store.list_bundle_graphs(
            business_date=business_date,
            agent_domain=agent_domain,
            slots=[slot],
            section_keys=[section_key],
            statuses=["active", "superseded", "withdrawn"],
        )
        graph = self._main_assembler._select_effective_graphs(graphs).get((slot, section_key))
        section_render_key = f"support.{agent_domain}.{slot}"
        title = f"{SUPPORT_DOMAIN_TITLES.get(agent_domain, agent_domain)}｜{SUPPORT_SLOT_TITLES.get(slot, slot)}"

        if graph is None:
            return {
                "artifact_type": "fsj_support_report_section",
                "artifact_version": "v1",
                "market": "a_share",
                "business_date": business_date,
                "agent_domain": agent_domain,
                "slot": slot,
                "section_key": section_key,
                "section_render_key": section_render_key,
                "title": title,
                "status": "missing",
                "bundle": None,
                "summary": None,
                "judgments": [],
                "signals": [],
                "facts": [],
                "lineage": None,
            }

        bundle = dict(graph.get("bundle") or {})
        objects = list(graph.get("objects") or [])
        return {
            "artifact_type": "fsj_support_report_section",
            "artifact_version": "v1",
            "market": str(bundle.get("market") or "a_share"),
            "business_date": business_date,
            "agent_domain": agent_domain,
            "slot": slot,
            "section_key": section_key,
            "section_render_key": section_render_key,
            "title": title,
            "status": "ready",
            "bundle": {
                "bundle_id": bundle.get("bundle_id"),
                "status": bundle.get("status"),
                "supersedes_bundle_id": bundle.get("supersedes_bundle_id"),
                "bundle_topic_key": bundle.get("bundle_topic_key"),
                "producer": bundle.get("producer"),
                "producer_version": bundle.get("producer_version"),
                "section_type": bundle.get("section_type"),
                "slot_run_id": bundle.get("slot_run_id"),
                "replay_id": bundle.get("replay_id"),
                "report_run_id": bundle.get("report_run_id"),
                "updated_at": bundle.get("updated_at"),
            },
            "summary": bundle.get("summary"),
            "judgments": self._main_assembler._project_objects(objects, "judgment"),
            "signals": self._main_assembler._project_objects(objects, "signal"),
            "facts": self._main_assembler._project_objects(objects, "fact"),
            "lineage": {
                "bundle": bundle,
                "objects": sorted(objects, key=lambda row: (str(row.get("fsj_kind") or ""), str(row.get("object_key") or ""))),
                "edges": sorted(list(graph.get("edges") or []), key=lambda row: (str(row.get("edge_type") or ""), str(row.get("from_object_key") or ""), str(row.get("to_object_key") or ""))),
                "evidence_links": sorted(list(graph.get("evidence_links") or []), key=lambda row: (str(row.get("evidence_role") or ""), str(row.get("object_key") or ""), str(row.get("ref_system") or ""), str(row.get("ref_key") or ""))),
                "observed_records": sorted(list(graph.get("observed_records") or []), key=lambda row: (str(row.get("fsj_kind") or ""), str(row.get("object_key") or ""), str(row.get("source_layer") or ""), str(row.get("source_record_key") or ""))),
                "report_links": sorted(list(graph.get("report_links") or []), key=lambda row: (str(row.get("artifact_type") or ""), str(row.get("section_render_key") or ""), str(row.get("artifact_uri") or ""))),
            },
        }
