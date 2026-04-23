from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

VALID_SUPPORT_AGENT_DOMAINS = {"macro", "commodities", "ai_tech"}
VALID_SUPPORT_SLOTS = {"early", "late"}
VALID_SUPPORT_RELATIONS = {"support", "adjust", "counter"}

SECTION_KEY_BY_DOMAIN = {
    "macro": "support_macro",
    "commodities": "support_commodities",
    "ai_tech": "support_ai_tech",
}


@dataclass(frozen=True)
class SupportEvidenceRecord:
    source_layer: str
    source_family: str
    source_table: str
    source_record_key: str
    observed_label: str
    observed_payload: dict[str, Any]


@dataclass(frozen=True)
class SupportTextItem:
    title: str
    published_at: str | None = None
    source_table: str | None = None


@dataclass(frozen=True)
class SupportSnapshot:
    object_key: str
    label: str
    source_layer: str
    source_family: str
    source_table: str
    source_record_key: str
    freshness_label: str
    confidence: str
    value_text: str
    observed_at: str | None = None
    attributes: dict[str, Any] | None = None


@dataclass(frozen=True)
class SupportBundleBase:
    business_date: str
    slot: str
    agent_domain: str
    section_key: str
    section_type: str
    bundle_topic_key: str
    summary_topic: str
    replay_id: str | None = None
    slot_run_id: str | None = None
    report_run_id: str | None = None


@dataclass(frozen=True)
class SupportJudgmentPlan:
    primary_relation: str
    secondary_relations: list[str]
    judgment_type: str
    judgment_action: str
    direction: str
    priority: str
    signal_type: str
    signal_strength: str
    horizon: str
    confidence: str
    object_key: str
    signal_key: str
    summary: str
    signal_statement: str
    judgment_statement: str
    invalidators: list[str]
    degrade_reason: str | None = None



def ensure_support_contract(*, agent_domain: str, slot: str, section_key: str) -> None:
    if agent_domain not in VALID_SUPPORT_AGENT_DOMAINS:
        raise ValueError(f"invalid support agent_domain: {agent_domain}")
    if slot not in VALID_SUPPORT_SLOTS:
        raise ValueError(f"invalid support slot: {slot}")
    expected_section_key = SECTION_KEY_BY_DOMAIN[agent_domain]
    if section_key != expected_section_key:
        raise ValueError(
            f"invalid support section_key for {agent_domain}: {section_key} != {expected_section_key}"
        )



def object_id(prefix: str, *parts: str) -> str:
    return ":".join([prefix, *parts])



def make_fact_object(
    *,
    bundle_id: str,
    object_key: str,
    object_type: str,
    statement: str,
    confidence: str,
    entity_refs: Iterable[str] = (),
    metric_refs: Iterable[str] = (),
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "object_id": object_id("fact", *object_key.split(":")),
        "fsj_kind": "fact",
        "object_key": object_key,
        "statement": statement,
        "object_type": object_type,
        "confidence": confidence,
        "entity_refs": list(entity_refs),
        "metric_refs": list(metric_refs),
        "invalidators": [],
        "attributes_json": attributes or {},
    }



def make_signal_object(
    *,
    bundle_id: str,
    object_key: str,
    object_type: str,
    statement: str,
    signal_strength: str,
    horizon: str,
    confidence: str,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "object_id": object_id("signal", *object_key.split(":")),
        "fsj_kind": "signal",
        "object_key": object_key,
        "statement": statement,
        "object_type": object_type,
        "signal_strength": signal_strength,
        "horizon": horizon,
        "confidence": confidence,
        "entity_refs": [],
        "metric_refs": [],
        "invalidators": [],
        "attributes_json": attributes or {},
    }



def make_judgment_object(
    *,
    bundle_id: str,
    object_key: str,
    object_type: str,
    statement: str,
    judgment_action: str,
    direction: str,
    priority: str,
    confidence: str,
    invalidators: list[str],
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "object_id": object_id("judgment", *object_key.split(":")),
        "fsj_kind": "judgment",
        "object_key": object_key,
        "statement": statement,
        "object_type": object_type,
        "judgment_action": judgment_action,
        "direction": direction,
        "priority": priority,
        "confidence": confidence,
        "entity_refs": [],
        "metric_refs": [],
        "invalidators": invalidators,
        "attributes_json": attributes or {},
    }



def edge(bundle_id: str, edge_type: str, from_kind: str, from_key: str, to_kind: str, to_key: str, *, role: str | None = None, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "edge_type": edge_type,
        "from_fsj_kind": from_kind,
        "from_object_key": from_key,
        "to_fsj_kind": to_kind,
        "to_object_key": to_key,
        "role": role,
        "attributes_json": attributes or {},
    }



def support_relation_edge(bundle_id: str, from_key: str, to_key: str, *, relation: str, strength: str = "primary") -> dict[str, Any]:
    if relation not in VALID_SUPPORT_RELATIONS:
        raise ValueError(f"invalid support relation: {relation}")
    return edge(
        bundle_id,
        "judgment_to_judgment",
        "judgment",
        from_key,
        "judgment",
        to_key,
        role=relation,
        attributes={"relation_type": relation, "relation_strength": strength},
    )
