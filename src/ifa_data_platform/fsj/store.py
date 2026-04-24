from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import text
from sqlalchemy.engine import Engine

from ifa_data_platform.db.engine import make_engine, make_engine_for_url
from ifa_data_platform.fsj.test_live_isolation import require_explicit_non_live_database_url

VALID_BUNDLE_STATUS = {"active", "superseded", "withdrawn"}
VALID_REPORT_ARTIFACT_STATUS = {"active", "superseded", "withdrawn"}
VALID_FSJ_KINDS = {"fact", "signal", "judgment"}
VALID_EDGE_TYPES = {"fact_to_signal", "signal_to_judgment", "judgment_to_judgment"}
CANONICAL_REPORT_LIFECYCLE_STATES = {
    "planned",
    "collecting",
    "producing",
    "qa_pending",
    "review_ready",
    "send_ready",
    "sent",
    "held",
    "failed",
    "superseded",
}
BUSINESS_REPO_MODELS_CONFIG = Path("/Users/neoclaw/repos/ifa-business-layer/config/llm/models.yaml")

@lru_cache(maxsize=1)
def _load_llm_model_pricing() -> dict[str, dict[str, Any]]:
    if not BUSINESS_REPO_MODELS_CONFIG.exists():
        return {}
    payload = yaml.safe_load(BUSINESS_REPO_MODELS_CONFIG.read_text(encoding="utf-8")) or {}
    models = dict(payload.get("models") or {})
    pricing: dict[str, dict[str, Any]] = {}
    for alias, cfg in models.items():
        if not isinstance(cfg, dict):
            continue
        pricing_cfg = dict(cfg.get("pricing") or {})
        if pricing_cfg:
            pricing[str(alias)] = pricing_cfg
    return pricing


def _usage_int(usage: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = usage.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _estimate_usage_cost_usd(*, model_alias: str | None, usage: dict[str, Any] | None) -> float | None:
    if not model_alias or not isinstance(usage, dict):
        return None
    pricing = _load_llm_model_pricing().get(str(model_alias)) or {}
    if not pricing:
        return None

    total_tokens = _usage_int(usage, "total_tokens", "totalTokens")
    input_tokens = _usage_int(usage, "input_tokens", "prompt_tokens", "inputTokens", "promptTokens")
    output_tokens = _usage_int(usage, "output_tokens", "completion_tokens", "outputTokens", "completionTokens")
    reasoning_tokens = _usage_int(usage, "reasoning_tokens", "reasoningTokens")

    total_rate = pricing.get("usd_per_1m_total_tokens")
    if total_rate is not None and total_tokens > 0:
        return round((float(total_rate) * total_tokens) / 1_000_000.0, 6)

    input_rate = pricing.get("usd_per_1m_input_tokens")
    output_rate = pricing.get("usd_per_1m_output_tokens")
    reasoning_rate = pricing.get("usd_per_1m_reasoning_tokens")
    if input_rate is None and output_rate is None and reasoning_rate is None:
        return None

    estimated = 0.0
    if input_rate is not None and input_tokens > 0:
        estimated += (float(input_rate) * input_tokens) / 1_000_000.0
    if output_rate is not None and output_tokens > 0:
        estimated += (float(output_rate) * output_tokens) / 1_000_000.0
    if reasoning_rate is not None and reasoning_tokens > 0:
        estimated += (float(reasoning_rate) * reasoning_tokens) / 1_000_000.0
    return round(estimated, 6)


def _llm_budget_posture(*, usage_bundle_count: int, costed_bundle_count: int, uncosted_bundle_count: int) -> dict[str, Any]:
    usage_bundle_count = max(int(usage_bundle_count or 0), 0)
    costed_bundle_count = max(int(costed_bundle_count or 0), 0)
    uncosted_bundle_count = max(int(uncosted_bundle_count or 0), 0)
    priced_bundle_count = min(costed_bundle_count, usage_bundle_count)

    if usage_bundle_count <= 0:
        posture = "no_usage"
        attention = False
        summary_line = "no_usage"
    elif uncosted_bundle_count <= 0 and priced_bundle_count >= usage_bundle_count:
        posture = "fully_priced"
        attention = False
        summary_line = f"fully_priced [{priced_bundle_count}/{usage_bundle_count}]"
    elif priced_bundle_count <= 0:
        posture = "unpriced"
        attention = True
        summary_line = f"unpriced [0/{usage_bundle_count} priced | unpriced={uncosted_bundle_count}]"
    else:
        posture = "mixed"
        attention = True
        summary_line = f"mixed [{priced_bundle_count}/{usage_bundle_count} priced | unpriced={uncosted_bundle_count}]"

    return {
        "posture": posture,
        "priced_bundle_count": priced_bundle_count,
        "costed_bundle_count": priced_bundle_count,
        "uncosted_bundle_count": uncosted_bundle_count,
        "attention": attention,
        "summary_line": summary_line,
    }


SCHEMA_DDL = [
    "CREATE SCHEMA IF NOT EXISTS ifa2",
    """
    CREATE TABLE IF NOT EXISTS ifa2.ifa_fsj_bundles (
        id uuid PRIMARY KEY,
        bundle_id text NOT NULL UNIQUE,
        market text NOT NULL,
        business_date date NOT NULL,
        slot text NOT NULL,
        agent_domain text NOT NULL,
        section_key text NOT NULL,
        section_type text NOT NULL,
        bundle_topic_key text NULL,
        producer text NOT NULL,
        producer_version text NOT NULL,
        assembly_mode text NOT NULL,
        status text NOT NULL,
        supersedes_bundle_id text NULL,
        slot_run_id text NULL,
        replay_id text NULL,
        report_run_id text NULL,
        summary text NOT NULL,
        payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_ifa_fsj_bundles_status CHECK (status IN ('active', 'superseded', 'withdrawn')),
        CONSTRAINT fk_ifa_fsj_bundles_supersedes FOREIGN KEY (supersedes_bundle_id) REFERENCES ifa2.ifa_fsj_bundles(bundle_id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ifa2.ifa_fsj_objects (
        id uuid PRIMARY KEY,
        bundle_id text NOT NULL REFERENCES ifa2.ifa_fsj_bundles(bundle_id) ON DELETE CASCADE,
        object_id text NOT NULL,
        fsj_kind text NOT NULL,
        object_key text NOT NULL,
        statement text NOT NULL,
        object_type text NULL,
        judgment_action text NULL,
        direction text NULL,
        priority text NULL,
        signal_strength text NULL,
        horizon text NULL,
        evidence_level text NULL,
        confidence text NULL,
        entity_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
        metric_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
        invalidators jsonb NOT NULL DEFAULT '[]'::jsonb,
        attributes_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_ifa_fsj_objects_kind CHECK (fsj_kind IN ('fact', 'signal', 'judgment')),
        CONSTRAINT uq_ifa_fsj_objects_bundle_kind_key UNIQUE (bundle_id, fsj_kind, object_key),
        CONSTRAINT uq_ifa_fsj_objects_bundle_object_id UNIQUE (bundle_id, object_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ifa2.ifa_fsj_edges (
        id uuid PRIMARY KEY,
        bundle_id text NOT NULL REFERENCES ifa2.ifa_fsj_bundles(bundle_id) ON DELETE CASCADE,
        edge_type text NOT NULL,
        from_fsj_kind text NOT NULL,
        from_object_key text NOT NULL,
        to_fsj_kind text NOT NULL,
        to_object_key text NOT NULL,
        role text NULL,
        attributes_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_ifa_fsj_edges_type CHECK (edge_type IN ('fact_to_signal', 'signal_to_judgment', 'judgment_to_judgment')),
        CONSTRAINT ck_ifa_fsj_edges_from_kind CHECK (from_fsj_kind IN ('fact', 'signal', 'judgment')),
        CONSTRAINT ck_ifa_fsj_edges_to_kind CHECK (to_fsj_kind IN ('fact', 'signal', 'judgment')),
        CONSTRAINT uq_ifa_fsj_edges_bundle_path UNIQUE (bundle_id, edge_type, from_object_key, to_object_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ifa2.ifa_fsj_evidence_links (
        id uuid PRIMARY KEY,
        bundle_id text NOT NULL REFERENCES ifa2.ifa_fsj_bundles(bundle_id) ON DELETE CASCADE,
        object_key text NULL,
        fsj_kind text NULL,
        evidence_role text NOT NULL,
        ref_system text NOT NULL,
        ref_family text NULL,
        ref_table text NULL,
        ref_key text NULL,
        ref_locator_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        observed_at timestamptz NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_ifa_fsj_evidence_links_kind CHECK (fsj_kind IS NULL OR fsj_kind IN ('fact', 'signal', 'judgment'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ifa2.ifa_fsj_observed_records (
        id uuid PRIMARY KEY,
        bundle_id text NOT NULL REFERENCES ifa2.ifa_fsj_bundles(bundle_id) ON DELETE CASCADE,
        object_key text NOT NULL,
        fsj_kind text NOT NULL,
        source_layer text NOT NULL,
        source_family text NULL,
        source_table text NULL,
        source_record_key text NULL,
        observed_label text NULL,
        observed_payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_ifa_fsj_observed_records_kind CHECK (fsj_kind IN ('fact', 'signal', 'judgment'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ifa2.ifa_fsj_report_links (
        id uuid PRIMARY KEY,
        bundle_id text NOT NULL REFERENCES ifa2.ifa_fsj_bundles(bundle_id) ON DELETE CASCADE,
        report_run_id text NULL,
        artifact_type text NOT NULL,
        artifact_uri text NULL,
        artifact_locator_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        section_render_key text NULL,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ifa2.ifa_fsj_report_artifacts (
        id uuid PRIMARY KEY,
        artifact_id text NOT NULL UNIQUE,
        artifact_family text NOT NULL,
        market text NOT NULL,
        business_date date NOT NULL,
        agent_domain text NOT NULL,
        render_format text NOT NULL,
        artifact_type text NOT NULL,
        content_type text NOT NULL,
        title text NOT NULL,
        report_run_id text NULL,
        artifact_uri text NULL,
        status text NOT NULL,
        supersedes_artifact_id text NULL,
        metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_ifa_fsj_report_artifacts_status CHECK (status IN ('active', 'superseded', 'withdrawn')),
        CONSTRAINT fk_ifa_fsj_report_artifacts_supersedes FOREIGN KEY (supersedes_artifact_id) REFERENCES ifa2.ifa_fsj_report_artifacts(artifact_id) ON DELETE SET NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_bundles_lookup ON ifa2.ifa_fsj_bundles (business_date, slot, agent_domain, section_key, status, bundle_topic_key)",
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_bundles_supersedes ON ifa2.ifa_fsj_bundles (supersedes_bundle_id)",
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_objects_kind_type ON ifa2.ifa_fsj_objects (fsj_kind, object_type)",
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_objects_bundle ON ifa2.ifa_fsj_objects (bundle_id, fsj_kind, object_key)",
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_edges_bundle ON ifa2.ifa_fsj_edges (bundle_id, edge_type)",
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_evidence_links_bundle ON ifa2.ifa_fsj_evidence_links (bundle_id, evidence_role, fsj_kind)",
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_observed_records_bundle ON ifa2.ifa_fsj_observed_records (bundle_id, fsj_kind, object_key)",
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_report_links_bundle ON ifa2.ifa_fsj_report_links (bundle_id, artifact_type)",
    "CREATE INDEX IF NOT EXISTS ix_ifa_fsj_report_artifacts_lookup ON ifa2.ifa_fsj_report_artifacts (business_date, agent_domain, artifact_family, status, created_at DESC)",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_ifa_fsj_evidence_links_natural
      ON ifa2.ifa_fsj_evidence_links (
        bundle_id,
        COALESCE(object_key, ''),
        COALESCE(fsj_kind, ''),
        evidence_role,
        ref_system,
        COALESCE(ref_family, ''),
        COALESCE(ref_table, ''),
        COALESCE(ref_key, '')
      )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_ifa_fsj_observed_records_natural
      ON ifa2.ifa_fsj_observed_records (
        bundle_id, object_key, fsj_kind, source_layer,
        COALESCE(source_family, ''), COALESCE(source_table, ''), COALESCE(source_record_key, '')
      )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_ifa_fsj_report_links_natural
      ON ifa2.ifa_fsj_report_links (
        bundle_id, artifact_type, COALESCE(report_run_id, ''), COALESCE(artifact_uri, ''), COALESCE(section_render_key, '')
      )
    """,
]


class FSJStore:
    def __init__(self, *, database_url: str | None = None, engine: Engine | None = None) -> None:
        if engine is not None:
            self.engine = engine
            return

        resolved_database_url = require_explicit_non_live_database_url(
            flow_name=self.__class__.__name__,
            database_url=database_url,
        )
        self.engine = make_engine() if database_url is None else make_engine_for_url(resolved_database_url)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, Decimal):
            return int(value) if value == value.to_integral_value() else float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        return str(value)

    def _json_dumps(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=self._json_default)

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            for ddl in SCHEMA_DDL:
                conn.execute(text(ddl))

    def upsert_bundle_graph(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema()
        bundle = dict(payload.get("bundle") or {})
        self._validate_bundle(bundle)
        objects = list(payload.get("objects") or [])
        edges = list(payload.get("edges") or [])
        evidence_links = list(payload.get("evidence_links") or [])
        observed_records = list(payload.get("observed_records") or [])
        report_links = list(payload.get("report_links") or [])

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.ifa_fsj_bundles (
                        id, bundle_id, market, business_date, slot, agent_domain,
                        section_key, section_type, bundle_topic_key, producer,
                        producer_version, assembly_mode, status, supersedes_bundle_id,
                        slot_run_id, replay_id, report_run_id, summary, payload_json
                    ) VALUES (
                        CAST(:id AS uuid), :bundle_id, :market, :business_date, :slot, :agent_domain,
                        :section_key, :section_type, :bundle_topic_key, :producer,
                        :producer_version, :assembly_mode, :status, :supersedes_bundle_id,
                        :slot_run_id, :replay_id, :report_run_id, :summary, CAST(:payload_json AS jsonb)
                    )
                    ON CONFLICT (bundle_id) DO UPDATE SET
                        market=EXCLUDED.market,
                        business_date=EXCLUDED.business_date,
                        slot=EXCLUDED.slot,
                        agent_domain=EXCLUDED.agent_domain,
                        section_key=EXCLUDED.section_key,
                        section_type=EXCLUDED.section_type,
                        bundle_topic_key=EXCLUDED.bundle_topic_key,
                        producer=EXCLUDED.producer,
                        producer_version=EXCLUDED.producer_version,
                        assembly_mode=EXCLUDED.assembly_mode,
                        status=EXCLUDED.status,
                        supersedes_bundle_id=EXCLUDED.supersedes_bundle_id,
                        slot_run_id=EXCLUDED.slot_run_id,
                        replay_id=EXCLUDED.replay_id,
                        report_run_id=EXCLUDED.report_run_id,
                        summary=EXCLUDED.summary,
                        payload_json=EXCLUDED.payload_json,
                        updated_at=now()
                    """
                ),
                {
                    "id": bundle.get("id") or str(uuid.uuid4()),
                    "bundle_id": bundle["bundle_id"],
                    "market": bundle["market"],
                    "business_date": bundle["business_date"],
                    "slot": bundle["slot"],
                    "agent_domain": bundle["agent_domain"],
                    "section_key": bundle["section_key"],
                    "section_type": bundle["section_type"],
                    "bundle_topic_key": bundle.get("bundle_topic_key"),
                    "producer": bundle["producer"],
                    "producer_version": bundle["producer_version"],
                    "assembly_mode": bundle["assembly_mode"],
                    "status": bundle["status"],
                    "supersedes_bundle_id": bundle.get("supersedes_bundle_id"),
                    "slot_run_id": bundle.get("slot_run_id"),
                    "replay_id": bundle.get("replay_id"),
                    "report_run_id": bundle.get("report_run_id"),
                    "summary": bundle["summary"],
                    "payload_json": self._json_dumps(bundle.get("payload_json") or {}),
                },
            )

            for obj in objects:
                self._validate_object(obj)
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.ifa_fsj_objects (
                            id, bundle_id, object_id, fsj_kind, object_key, statement, object_type,
                            judgment_action, direction, priority, signal_strength, horizon,
                            evidence_level, confidence, entity_refs, metric_refs, invalidators,
                            attributes_json
                        ) VALUES (
                            CAST(:id AS uuid), :bundle_id, :object_id, :fsj_kind, :object_key, :statement, :object_type,
                            :judgment_action, :direction, :priority, :signal_strength, :horizon,
                            :evidence_level, :confidence, CAST(:entity_refs AS jsonb), CAST(:metric_refs AS jsonb), CAST(:invalidators AS jsonb),
                            CAST(:attributes_json AS jsonb)
                        )
                        ON CONFLICT (bundle_id, fsj_kind, object_key) DO UPDATE SET
                            object_id=EXCLUDED.object_id,
                            statement=EXCLUDED.statement,
                            object_type=EXCLUDED.object_type,
                            judgment_action=EXCLUDED.judgment_action,
                            direction=EXCLUDED.direction,
                            priority=EXCLUDED.priority,
                            signal_strength=EXCLUDED.signal_strength,
                            horizon=EXCLUDED.horizon,
                            evidence_level=EXCLUDED.evidence_level,
                            confidence=EXCLUDED.confidence,
                            entity_refs=EXCLUDED.entity_refs,
                            metric_refs=EXCLUDED.metric_refs,
                            invalidators=EXCLUDED.invalidators,
                            attributes_json=EXCLUDED.attributes_json,
                            updated_at=now()
                        """
                    ),
                    {
                        "id": obj.get("id") or str(uuid.uuid4()),
                        "bundle_id": bundle["bundle_id"],
                        "object_id": obj.get("object_id") or obj["object_key"],
                        "fsj_kind": obj["fsj_kind"],
                        "object_key": obj["object_key"],
                        "statement": obj["statement"],
                        "object_type": obj.get("object_type"),
                        "judgment_action": obj.get("judgment_action"),
                        "direction": obj.get("direction"),
                        "priority": obj.get("priority"),
                        "signal_strength": obj.get("signal_strength"),
                        "horizon": obj.get("horizon"),
                        "evidence_level": obj.get("evidence_level"),
                        "confidence": obj.get("confidence"),
                        "entity_refs": self._json_dumps(obj.get("entity_refs") or []),
                        "metric_refs": self._json_dumps(obj.get("metric_refs") or []),
                        "invalidators": self._json_dumps(obj.get("invalidators") or []),
                        "attributes_json": self._json_dumps(obj.get("attributes_json") or {}),
                    },
                )

            for edge in edges:
                self._validate_edge(edge)
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.ifa_fsj_edges (
                            id, bundle_id, edge_type, from_fsj_kind, from_object_key,
                            to_fsj_kind, to_object_key, role, attributes_json
                        ) VALUES (
                            CAST(:id AS uuid), :bundle_id, :edge_type, :from_fsj_kind, :from_object_key,
                            :to_fsj_kind, :to_object_key, :role, CAST(:attributes_json AS jsonb)
                        )
                        ON CONFLICT (bundle_id, edge_type, from_object_key, to_object_key) DO UPDATE SET
                            from_fsj_kind=EXCLUDED.from_fsj_kind,
                            to_fsj_kind=EXCLUDED.to_fsj_kind,
                            role=EXCLUDED.role,
                            attributes_json=EXCLUDED.attributes_json
                        """
                    ),
                    {
                        "id": edge.get("id") or str(uuid.uuid4()),
                        "bundle_id": bundle["bundle_id"],
                        "edge_type": edge["edge_type"],
                        "from_fsj_kind": edge["from_fsj_kind"],
                        "from_object_key": edge["from_object_key"],
                        "to_fsj_kind": edge["to_fsj_kind"],
                        "to_object_key": edge["to_object_key"],
                        "role": edge.get("role"),
                        "attributes_json": self._json_dumps(edge.get("attributes_json") or {}),
                    },
                )

            for link in evidence_links:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.ifa_fsj_evidence_links (
                            id, bundle_id, object_key, fsj_kind, evidence_role, ref_system,
                            ref_family, ref_table, ref_key, ref_locator_json, observed_at
                        ) VALUES (
                            CAST(:id AS uuid), :bundle_id, :object_key, :fsj_kind, :evidence_role, :ref_system,
                            :ref_family, :ref_table, :ref_key, CAST(:ref_locator_json AS jsonb), :observed_at
                        )
                        ON CONFLICT ((bundle_id), (COALESCE(object_key, '')), (COALESCE(fsj_kind, '')), evidence_role, ref_system, (COALESCE(ref_family, '')), (COALESCE(ref_table, '')), (COALESCE(ref_key, ''))) DO UPDATE SET
                            ref_locator_json=EXCLUDED.ref_locator_json,
                            observed_at=EXCLUDED.observed_at
                        """
                    ),
                    {
                        "id": link.get("id") or str(uuid.uuid4()),
                        "bundle_id": bundle["bundle_id"],
                        "object_key": link.get("object_key"),
                        "fsj_kind": link.get("fsj_kind"),
                        "evidence_role": link["evidence_role"],
                        "ref_system": link["ref_system"],
                        "ref_family": link.get("ref_family"),
                        "ref_table": link.get("ref_table"),
                        "ref_key": link.get("ref_key"),
                        "ref_locator_json": self._json_dumps(link.get("ref_locator_json") or {}),
                        "observed_at": link.get("observed_at"),
                    },
                )

            for record in observed_records:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.ifa_fsj_observed_records (
                            id, bundle_id, object_key, fsj_kind, source_layer, source_family,
                            source_table, source_record_key, observed_label, observed_payload_json
                        ) VALUES (
                            CAST(:id AS uuid), :bundle_id, :object_key, :fsj_kind, :source_layer, :source_family,
                            :source_table, :source_record_key, :observed_label, CAST(:observed_payload_json AS jsonb)
                        )
                        ON CONFLICT ((bundle_id), object_key, fsj_kind, source_layer, (COALESCE(source_family, '')), (COALESCE(source_table, '')), (COALESCE(source_record_key, ''))) DO UPDATE SET
                            observed_label=EXCLUDED.observed_label,
                            observed_payload_json=EXCLUDED.observed_payload_json
                        """
                    ),
                    {
                        "id": record.get("id") or str(uuid.uuid4()),
                        "bundle_id": bundle["bundle_id"],
                        "object_key": record["object_key"],
                        "fsj_kind": record["fsj_kind"],
                        "source_layer": record["source_layer"],
                        "source_family": record.get("source_family"),
                        "source_table": record.get("source_table"),
                        "source_record_key": record.get("source_record_key"),
                        "observed_label": record.get("observed_label"),
                        "observed_payload_json": self._json_dumps(record.get("observed_payload_json") or {}),
                    },
                )

            for report in report_links:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.ifa_fsj_report_links (
                            id, bundle_id, report_run_id, artifact_type, artifact_uri,
                            artifact_locator_json, section_render_key
                        ) VALUES (
                            CAST(:id AS uuid), :bundle_id, :report_run_id, :artifact_type, :artifact_uri,
                            CAST(:artifact_locator_json AS jsonb), :section_render_key
                        )
                        ON CONFLICT ((bundle_id), artifact_type, (COALESCE(report_run_id, '')), (COALESCE(artifact_uri, '')), (COALESCE(section_render_key, ''))) DO UPDATE SET
                            artifact_locator_json=EXCLUDED.artifact_locator_json
                        """
                    ),
                    {
                        "id": report.get("id") or str(uuid.uuid4()),
                        "bundle_id": bundle["bundle_id"],
                        "report_run_id": report.get("report_run_id"),
                        "artifact_type": report["artifact_type"],
                        "artifact_uri": report.get("artifact_uri"),
                        "artifact_locator_json": self._json_dumps(report.get("artifact_locator_json") or {}),
                        "section_render_key": report.get("section_render_key"),
                    },
                )

        return self.get_bundle_graph(bundle["bundle_id"]) or {"bundle": bundle}

    def attach_report_links(self, bundle_id: str, report_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self.engine.begin() as conn:
            for report in report_links:
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.ifa_fsj_report_links (
                            id, bundle_id, report_run_id, artifact_type, artifact_uri,
                            artifact_locator_json, section_render_key
                        ) VALUES (
                            CAST(:id AS uuid), :bundle_id, :report_run_id, :artifact_type, :artifact_uri,
                            CAST(:artifact_locator_json AS jsonb), :section_render_key
                        )
                        ON CONFLICT ((bundle_id), artifact_type, (COALESCE(report_run_id, '')), (COALESCE(artifact_uri, '')), (COALESCE(section_render_key, ''))) DO UPDATE SET
                            artifact_locator_json=EXCLUDED.artifact_locator_json
                        """
                    ),
                    {
                        "id": report.get("id") or str(uuid.uuid4()),
                        "bundle_id": bundle_id,
                        "report_run_id": report.get("report_run_id"),
                        "artifact_type": report["artifact_type"],
                        "artifact_uri": report.get("artifact_uri"),
                        "artifact_locator_json": self._json_dumps(report.get("artifact_locator_json") or {}),
                        "section_render_key": report.get("section_render_key"),
                    },
                )
        graph = self.get_bundle_graph(bundle_id) or {}
        return list(graph.get("report_links") or [])

    def register_report_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_schema()
        required = [
            "artifact_id", "artifact_family", "market", "business_date", "agent_domain",
            "render_format", "artifact_type", "content_type", "title", "status",
        ]
        for key in required:
            if not payload.get(key):
                raise ValueError(f"report artifact missing required field: {key}")
        if payload["status"] not in VALID_REPORT_ARTIFACT_STATUS:
            raise ValueError(f"invalid report artifact status: {payload['status']}")

        with self.engine.begin() as conn:
            if payload["status"] == "active":
                active = conn.execute(
                    text(
                        """
                        SELECT artifact_id
                          FROM ifa2.ifa_fsj_report_artifacts
                         WHERE business_date=:business_date
                           AND agent_domain=:agent_domain
                           AND artifact_family=:artifact_family
                           AND status='active'
                           AND artifact_id <> :artifact_id
                         ORDER BY updated_at DESC, artifact_id DESC
                         LIMIT 1
                        """
                    ),
                    {
                        "business_date": payload["business_date"],
                        "agent_domain": payload["agent_domain"],
                        "artifact_family": payload["artifact_family"],
                        "artifact_id": payload["artifact_id"],
                    },
                ).mappings().first()
                supersedes_artifact_id = payload.get("supersedes_artifact_id") or (active["artifact_id"] if active else None)
                if supersedes_artifact_id:
                    conn.execute(
                        text(
                            """
                            UPDATE ifa2.ifa_fsj_report_artifacts
                               SET status='superseded', updated_at=now()
                             WHERE business_date=:business_date
                               AND agent_domain=:agent_domain
                               AND artifact_family=:artifact_family
                               AND status='active'
                               AND artifact_id <> :artifact_id
                            """
                        ),
                        {
                            "business_date": payload["business_date"],
                            "agent_domain": payload["agent_domain"],
                            "artifact_family": payload["artifact_family"],
                            "artifact_id": payload["artifact_id"],
                        },
                    )
                payload = {**payload, "supersedes_artifact_id": supersedes_artifact_id}

            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.ifa_fsj_report_artifacts (
                        id, artifact_id, artifact_family, market, business_date, agent_domain,
                        render_format, artifact_type, content_type, title, report_run_id,
                        artifact_uri, status, supersedes_artifact_id, metadata_json
                    ) VALUES (
                        CAST(:id AS uuid), :artifact_id, :artifact_family, :market, :business_date, :agent_domain,
                        :render_format, :artifact_type, :content_type, :title, :report_run_id,
                        :artifact_uri, :status, :supersedes_artifact_id, CAST(:metadata_json AS jsonb)
                    )
                    ON CONFLICT (artifact_id) DO UPDATE SET
                        artifact_family=EXCLUDED.artifact_family,
                        market=EXCLUDED.market,
                        business_date=EXCLUDED.business_date,
                        agent_domain=EXCLUDED.agent_domain,
                        render_format=EXCLUDED.render_format,
                        artifact_type=EXCLUDED.artifact_type,
                        content_type=EXCLUDED.content_type,
                        title=EXCLUDED.title,
                        report_run_id=EXCLUDED.report_run_id,
                        artifact_uri=EXCLUDED.artifact_uri,
                        status=EXCLUDED.status,
                        supersedes_artifact_id=EXCLUDED.supersedes_artifact_id,
                        metadata_json=EXCLUDED.metadata_json,
                        updated_at=now()
                    """
                ),
                {
                    "id": payload.get("id") or str(uuid.uuid4()),
                    "artifact_id": payload["artifact_id"],
                    "artifact_family": payload["artifact_family"],
                    "market": payload["market"],
                    "business_date": payload["business_date"],
                    "agent_domain": payload["agent_domain"],
                    "render_format": payload["render_format"],
                    "artifact_type": payload["artifact_type"],
                    "content_type": payload["content_type"],
                    "title": payload["title"],
                    "report_run_id": payload.get("report_run_id"),
                    "artifact_uri": payload.get("artifact_uri"),
                    "status": payload["status"],
                    "supersedes_artifact_id": payload.get("supersedes_artifact_id"),
                    "metadata_json": self._json_dumps(payload.get("metadata_json") or {}),
                },
            )
        return self.get_report_artifact(payload["artifact_id"]) or payload

    def get_report_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        self.ensure_schema()
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT * FROM ifa2.ifa_fsj_report_artifacts WHERE artifact_id=:artifact_id"), {"artifact_id": artifact_id}).mappings().first()
        return self._mapping_to_dict(row) if row else None

    def get_active_report_artifact(self, *, business_date: str, agent_domain: str, artifact_family: str) -> dict[str, Any] | None:
        self.ensure_schema()
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT *
                      FROM ifa2.ifa_fsj_report_artifacts
                     WHERE business_date=:business_date
                       AND agent_domain=:agent_domain
                       AND artifact_family=:artifact_family
                       AND status='active'
                     ORDER BY updated_at DESC, artifact_id DESC
                     LIMIT 1
                    """
                ),
                {
                    "business_date": business_date,
                    "agent_domain": agent_domain,
                    "artifact_family": artifact_family,
                },
            ).mappings().first()
        return self._mapping_to_dict(row) if row else None

    def get_latest_active_report_artifact(
        self,
        *,
        agent_domain: str,
        artifact_family: str,
        strongest_slot: str | None = None,
        max_business_date: str | date | None = None,
    ) -> dict[str, Any] | None:
        self.ensure_schema()
        slot_sql = ""
        params: dict[str, Any] = {
            "agent_domain": agent_domain,
            "artifact_family": artifact_family,
        }
        if strongest_slot is not None:
            slot_sql = """
               AND coalesce(
                     metadata_json->'delivery_package'->'slot_evaluation'->>'strongest_slot',
                     metadata_json->'report_evaluation'->'summary'->>'strongest_slot'
                   ) = :strongest_slot
            """
            params["strongest_slot"] = strongest_slot
        max_business_date_sql = ""
        if max_business_date is not None:
            params["max_business_date"] = max_business_date.isoformat() if isinstance(max_business_date, date) else str(max_business_date)
            max_business_date_sql = "AND business_date <= :max_business_date"

        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    f"""
                    SELECT *
                      FROM ifa2.ifa_fsj_report_artifacts
                     WHERE agent_domain=:agent_domain
                       AND artifact_family=:artifact_family
                       AND status='active'
                       {max_business_date_sql}
                       {slot_sql}
                     ORDER BY business_date DESC, updated_at DESC, artifact_id DESC
                     LIMIT 1
                    """
                ),
                params,
            ).mappings().first()
        return self._mapping_to_dict(row) if row else None

    def get_active_report_delivery_surface(
        self,
        *,
        business_date: str,
        agent_domain: str,
        artifact_family: str,
    ) -> dict[str, Any] | None:
        surfaces = self.list_report_delivery_surfaces(
            business_date=business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
            statuses=["active"],
            limit=1,
        )
        return surfaces[0] if surfaces else None

    def get_latest_active_report_delivery_surface(
        self,
        *,
        agent_domain: str,
        artifact_family: str,
        strongest_slot: str | None = None,
        max_business_date: str | date | None = None,
    ) -> dict[str, Any] | None:
        artifact = self.get_latest_active_report_artifact(
            agent_domain=agent_domain,
            artifact_family=artifact_family,
            strongest_slot=strongest_slot,
            max_business_date=max_business_date,
        )
        if not artifact:
            return None
        return self._report_delivery_surface_from_artifact(artifact)

    def list_report_delivery_surfaces(
        self,
        *,
        business_date: str,
        agent_domain: str,
        artifact_family: str,
        statuses: list[str] | tuple[str, ...] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        normalized_statuses = [str(status) for status in (statuses or ["active", "superseded"])]
        valid_statuses = [status for status in normalized_statuses if status in VALID_REPORT_ARTIFACT_STATUS]
        if not valid_statuses or limit <= 0:
            return []

        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT *
                      FROM ifa2.ifa_fsj_report_artifacts
                     WHERE business_date=:business_date
                       AND agent_domain=:agent_domain
                       AND artifact_family=:artifact_family
                       AND status = ANY(CAST(:statuses AS text[]))
                     ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'superseded' THEN 1 ELSE 2 END,
                              updated_at DESC,
                              artifact_id DESC
                     LIMIT :limit
                    """
                ),
                {
                    "business_date": business_date,
                    "agent_domain": agent_domain,
                    "artifact_family": artifact_family,
                    "statuses": valid_statuses,
                    "limit": int(limit),
                },
            ).mappings().all()
        return [self._report_delivery_surface_from_artifact(self._mapping_to_dict(row)) for row in rows]

    def list_report_business_dates(
        self,
        *,
        agent_domain: str,
        artifact_family: str,
        statuses: list[str] | tuple[str, ...] | None = None,
        limit: int = 10,
        max_business_date: str | date | None = None,
    ) -> list[str]:
        self.ensure_schema()
        normalized_statuses = [str(status) for status in (statuses or ["active"])]
        valid_statuses = [status for status in normalized_statuses if status in VALID_REPORT_ARTIFACT_STATUS]
        if not valid_statuses or limit <= 0:
            return []

        params: dict[str, Any] = {
            "agent_domain": agent_domain,
            "artifact_family": artifact_family,
            "statuses": valid_statuses,
            "limit": int(limit),
        }
        max_business_date_sql = ""
        if max_business_date is not None:
            params["max_business_date"] = max_business_date.isoformat() if isinstance(max_business_date, date) else str(max_business_date)
            max_business_date_sql = "AND business_date <= :max_business_date"

        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    f"""
                    SELECT business_date
                      FROM ifa2.ifa_fsj_report_artifacts
                     WHERE agent_domain=:agent_domain
                       AND artifact_family=:artifact_family
                       AND status = ANY(CAST(:statuses AS text[]))
                       {max_business_date_sql}
                     GROUP BY business_date
                     ORDER BY business_date DESC
                     LIMIT :limit
                    """
                ),
                params,
            ).scalars().all()
        return [str(value) for value in rows if value is not None]

    def get_active_report_operator_review_surface(
        self,
        *,
        business_date: str,
        agent_domain: str,
        artifact_family: str,
    ) -> dict[str, Any] | None:
        surface = self.get_active_report_delivery_surface(
            business_date=business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
        )
        if not surface:
            return None
        return self.report_operator_review_surface_from_surface(surface)

    def get_latest_active_report_operator_review_surface(
        self,
        *,
        agent_domain: str,
        artifact_family: str,
        strongest_slot: str | None = None,
        max_business_date: str | date | None = None,
    ) -> dict[str, Any] | None:
        surface = self.get_latest_active_report_delivery_surface(
            agent_domain=agent_domain,
            artifact_family=artifact_family,
            strongest_slot=strongest_slot,
            max_business_date=max_business_date,
        )
        if not surface:
            return None
        return self.report_operator_review_surface_from_surface(surface)

    def list_report_operator_review_surfaces(
        self,
        *,
        business_date: str,
        agent_domain: str,
        artifact_family: str,
        statuses: list[str] | tuple[str, ...] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        surfaces = self.list_report_delivery_surfaces(
            business_date=business_date,
            agent_domain=agent_domain,
            artifact_family=artifact_family,
            statuses=statuses,
            limit=limit,
        )
        return [self.report_operator_review_surface_from_surface(surface) for surface in surfaces]

    def _report_delivery_surface_from_artifact(self, artifact: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(artifact.get("metadata_json") or {})
        delivery_package = dict(metadata.get("delivery_package") or {})
        workflow_linkage = dict(metadata.get("workflow_linkage") or {})
        llm_lineage = self.report_llm_lineage_from_artifact(artifact)
        if not delivery_package:
            return {
                "artifact": artifact,
                "delivery_package": None,
                "workflow_linkage": workflow_linkage,
                "workflow_handoff": self._report_workflow_handoff_from_artifact(
                    artifact,
                    delivery_package=None,
                    workflow_linkage=workflow_linkage,
                ),
                "llm_lineage": llm_lineage,
                "send_ready": False,
                "review_required": False,
            }

        quality_gate = dict(delivery_package.get("quality_gate") or metadata.get("quality_gate") or {})
        workflow = {
            **dict(delivery_package.get("workflow") or {}),
            **workflow_linkage,
        }
        recommended_action = str(workflow.get("recommended_action") or "hold")
        normalized_delivery_package = {
            **delivery_package,
            "quality_gate": quality_gate,
            "workflow": workflow,
        }
        return {
            "artifact": artifact,
            "delivery_package": normalized_delivery_package,
            "workflow_linkage": workflow_linkage,
            "workflow_handoff": self._report_workflow_handoff_from_artifact(
                artifact,
                delivery_package=normalized_delivery_package,
                workflow_linkage=workflow_linkage,
            ),
            "llm_lineage": llm_lineage,
            "send_ready": bool(delivery_package.get("ready_for_delivery")) and recommended_action == "send",
            "review_required": recommended_action == "send_review",
        }

    def report_workflow_handoff_from_surface(self, surface: dict[str, Any] | None) -> dict[str, Any]:
        normalized_surface = dict(surface or {})
        handoff = dict(normalized_surface.get("workflow_handoff") or {})
        if handoff:
            return handoff
        artifact = dict(normalized_surface.get("artifact") or {})
        delivery_package = normalized_surface.get("delivery_package")
        workflow_linkage = normalized_surface.get("workflow_linkage")
        return self._report_workflow_handoff_from_artifact(
            artifact,
            delivery_package=dict(delivery_package or {}) or None,
            workflow_linkage=dict(workflow_linkage or {}) or None,
        )

    def report_package_surface_from_surface(self, surface: dict[str, Any] | None) -> dict[str, Any]:
        normalized_surface = dict(surface or {})
        artifact = dict(normalized_surface.get("artifact") or {})
        delivery_package = dict(normalized_surface.get("delivery_package") or {})
        workflow_handoff = self.report_workflow_handoff_from_surface(normalized_surface)
        manifest_pointers = dict(workflow_handoff.get("manifest_pointers") or {})
        selected_handoff = dict(workflow_handoff.get("selected_handoff") or {})
        state = dict(workflow_handoff.get("state") or {})
        version_pointers = dict(workflow_handoff.get("version_pointers") or {})
        artifacts = dict(delivery_package.get("artifacts") or {})

        package_paths = {
            "delivery_package_dir": selected_handoff.get("selected_delivery_package_dir") or selected_handoff.get("delivery_package_dir") or delivery_package.get("delivery_package_dir"),
            "delivery_manifest_path": manifest_pointers.get("delivery_manifest_path") or selected_handoff.get("selected_delivery_manifest_path") or selected_handoff.get("delivery_manifest_path"),
            "delivery_zip_path": manifest_pointers.get("delivery_zip_path") or selected_handoff.get("selected_delivery_zip_path") or selected_handoff.get("delivery_zip_path"),
            "telegram_caption_path": manifest_pointers.get("telegram_caption_path") or selected_handoff.get("selected_telegram_caption_path") or selected_handoff.get("telegram_caption_path"),
            "package_index_path": manifest_pointers.get("package_index_path"),
            "package_browse_readme_path": manifest_pointers.get("package_browse_readme_path"),
            "send_manifest_path": manifest_pointers.get("send_manifest_path"),
            "review_manifest_path": manifest_pointers.get("review_manifest_path"),
            "workflow_manifest_path": manifest_pointers.get("workflow_manifest_path"),
            "operator_review_bundle_path": manifest_pointers.get("operator_review_bundle_path"),
            "operator_review_readme_path": manifest_pointers.get("operator_review_readme_path"),
        }
        package_versions = {
            "artifact_version": version_pointers.get("artifact_version") or artifact.get("artifact_version"),
            "delivery_manifest_version": version_pointers.get("delivery_manifest_version") or artifacts.get("delivery_manifest"),
            "send_manifest_version": version_pointers.get("send_manifest_version") or artifacts.get("send_manifest"),
            "review_manifest_version": version_pointers.get("review_manifest_version") or artifacts.get("review_manifest"),
            "workflow_manifest_version": version_pointers.get("workflow_manifest_version") or artifacts.get("workflow_manifest"),
            "package_index_version": version_pointers.get("package_index_version") or artifacts.get("package_index"),
        }
        delivery_lineage = dict(delivery_package.get("lineage") or {})
        return {
            "artifact": dict(workflow_handoff.get("artifact") or {}),
            "selected_handoff": selected_handoff,
            "state": state,
            "package_paths": package_paths,
            "package_versions": package_versions,
            "package_state": {
                "package_state": delivery_package.get("package_state"),
                "ready_for_delivery": delivery_package.get("ready_for_delivery"),
                "quality_gate": dict(delivery_package.get("quality_gate") or {}),
                "slot_evaluation": dict(delivery_package.get("slot_evaluation") or {}),
                "dispatch_advice": dict(delivery_package.get("dispatch_advice") or {}),
                "support_summary_aggregate": dict(delivery_package.get("support_summary_aggregate") or {}),
                "lineage": delivery_lineage,
            },
            "package_artifacts": artifacts,
            "workflow_handoff": workflow_handoff,
        }

    def report_operator_review_surface_from_surface(self, surface: dict[str, Any] | None) -> dict[str, Any]:
        normalized_surface = dict(surface or {})
        artifact = dict(normalized_surface.get("artifact") or {})
        workflow_handoff = self.report_workflow_handoff_from_surface(normalized_surface)
        package_surface = self.report_package_surface_from_surface(normalized_surface)
        package_state = dict(package_surface.get("package_state") or {})
        quality_gate = dict(package_state.get("quality_gate") or {})
        state = dict(workflow_handoff.get("state") or {})
        workflow_linkage = dict(normalized_surface.get("workflow_linkage") or {})
        llm_lineage = dict(
            normalized_surface.get("llm_lineage")
            or workflow_linkage.get("llm_lineage")
            or self.report_llm_lineage_from_artifact(artifact)
        )
        llm_lineage_summary = self.report_llm_lineage_summary(llm_lineage)
        llm_role_policy = dict(llm_lineage.get("role_policy") or {})
        llm_role_policy_by_slot = {
            str(item.get("slot")): str(item.get("role_policy_boundary_mode"))
            for item in (llm_lineage.get("bundles") or [])
            if str(item.get("slot") or "").strip() and str(item.get("role_policy_boundary_mode") or "").strip()
        }

        review_payload = dict(
            dict(normalized_surface.get("review_surface") or {})
            or dict(workflow_linkage.get("review_surface") or {})
        )
        candidate_comparison = dict(review_payload.get("candidate_comparison") or {})
        operator_go_no_go = dict(review_payload.get("operator_go_no_go") or {})
        review_manifest = dict(review_payload.get("review_manifest") or {})
        send_manifest = dict(review_payload.get("send_manifest") or {})
        dispatch_receipt = self._report_dispatch_receipt_from_surface(normalized_surface)

        selected = dict(candidate_comparison.get("selected") or {})
        current_vs_selected = dict(candidate_comparison.get("current_vs_selected") or {})
        selected_artifact_id = (
            candidate_comparison.get("selected_artifact_id")
            or current_vs_selected.get("selected_artifact_id")
            or (workflow_handoff.get("selected_handoff") or {}).get("selected_artifact_id")
        )
        current_artifact_id = (
            candidate_comparison.get("current_artifact_id")
            or current_vs_selected.get("current_artifact_id")
            or artifact.get("artifact_id")
        )
        candidate_count = candidate_comparison.get("candidate_count")
        ready_candidate_count = candidate_comparison.get("ready_candidate_count")
        ranked_candidates = list(candidate_comparison.get("ranked_candidates") or [])
        if candidate_count is None:
            candidate_count = len(ranked_candidates)
        if ready_candidate_count is None:
            ready_candidate_count = len([item for item in ranked_candidates if item.get("ready_for_delivery")])

        computed_decision = operator_go_no_go.get("decision") or (
            "GO" if state.get("send_ready") else ("REVIEW" if state.get("review_required") else "NO_GO")
        )
        dispatch_state = self._report_dispatch_state(
            state=state,
            dispatch_receipt=dispatch_receipt,
        )
        canonical_lifecycle = self.project_report_lifecycle_state(
            artifact=artifact,
            workflow_state=state.get("workflow_state"),
            package_state=state.get("package_state"),
            recommended_action=state.get("recommended_action"),
            ready_for_delivery=state.get("ready_for_delivery"),
            review_required=state.get("review_required"),
            dispatch_state=dispatch_state,
            selected_is_current=(workflow_handoff.get("selected_handoff") or {}).get("selected_is_current"),
        )

        return {
            "artifact": dict(workflow_handoff.get("artifact") or artifact),
            "selected_handoff": dict(workflow_handoff.get("selected_handoff") or {}),
            "state": state,
            "package_paths": dict(package_surface.get("package_paths") or {}),
            "package_versions": dict(package_surface.get("package_versions") or {}),
            "package_state": package_state,
            "workflow_handoff": workflow_handoff,
            "llm_lineage": llm_lineage,
            "llm_lineage_summary": llm_lineage_summary,
            "llm_role_policy": {
                **llm_role_policy,
                "slot_boundary_modes": llm_role_policy_by_slot,
            },
            "candidate_comparison": {
                **candidate_comparison,
                "selected": selected,
                "selected_artifact_id": selected_artifact_id,
                "current_artifact_id": current_artifact_id,
                "candidate_count": candidate_count,
                "ready_candidate_count": ready_candidate_count,
            },
            "operator_go_no_go": {
                **operator_go_no_go,
                "decision": computed_decision,
                "artifact_integrity_ok": operator_go_no_go.get("artifact_integrity_ok"),
                "missing_artifacts": list(operator_go_no_go.get("missing_artifacts") or []),
            },
            "review_manifest": review_manifest,
            "send_manifest": send_manifest,
            "dispatch_receipt": dispatch_receipt,
            "dispatch_state": dispatch_state,
            "canonical_lifecycle": canonical_lifecycle,
            "review_summary": {
                "recommended_action": state.get("recommended_action"),
                "workflow_state": state.get("workflow_state"),
                "dispatch_state": dispatch_state,
                "canonical_lifecycle_state": canonical_lifecycle.get("state"),
                "canonical_lifecycle_reason": canonical_lifecycle.get("reason"),
                "dispatch_attempted": dispatch_state == "dispatch_attempted",
                "dispatch_succeeded": dispatch_state == "dispatch_succeeded",
                "dispatch_failed": dispatch_state == "dispatch_failed",
                "dispatch_receipt": dispatch_receipt,
                "selected_artifact_id": selected_artifact_id,
                "current_artifact_id": current_artifact_id,
                "selected_is_current": (workflow_handoff.get("selected_handoff") or {}).get("selected_is_current"),
                "candidate_count": candidate_count,
                "ready_candidate_count": ready_candidate_count,
                "qa_score": quality_gate.get("score"),
                "blocker_count": quality_gate.get("blocker_count"),
                "warning_count": quality_gate.get("warning_count"),
                "go_no_go_decision": computed_decision,
                "llm_bundle_count": llm_lineage.get("summary", {}).get("bundle_count"),
                "llm_applied_count": llm_lineage.get("summary", {}).get("applied_count"),
                "llm_degraded_count": llm_lineage.get("summary", {}).get("degraded_count"),
                "llm_primary_count": llm_lineage.get("summary", {}).get("primary_applied_count"),
                "llm_fallback_count": llm_lineage.get("summary", {}).get("fallback_applied_count"),
                "llm_models": list(llm_lineage_summary.get("models") or []),
                "llm_usage_bundle_count": llm_lineage_summary.get("usage_bundle_count"),
                "llm_total_tokens": _usage_int(dict(llm_lineage_summary.get("token_totals") or {}), "total_tokens", "totalTokens"),
                "llm_estimated_cost_usd": llm_lineage_summary.get("estimated_cost_usd"),
                "llm_uncosted_bundle_count": llm_lineage_summary.get("uncosted_bundle_count"),
                "llm_lineage_summary": llm_lineage_summary.get("summary_line"),
                "llm_lineage_status": llm_lineage_summary.get("status"),
                "llm_boundary_modes": list(llm_role_policy.get("boundary_modes") or []),
                "llm_policy_versions": list(llm_role_policy.get("policy_versions") or []),
                "llm_forbidden_decision_count": len(llm_role_policy.get("forbidden_decisions") or []),
                "llm_deterministic_owner_fields": list(llm_role_policy.get("deterministic_owner_fields") or []),
                "llm_override_precedence": list(llm_role_policy.get("override_precedence") or []),
                "llm_slot_boundary_modes": llm_role_policy_by_slot,
            },
        }

    def _report_dispatch_receipt_from_surface(self, surface: dict[str, Any] | None) -> dict[str, Any]:
        normalized_surface = dict(surface or {})
        workflow_linkage = dict(normalized_surface.get("workflow_linkage") or {})
        review_surface = dict(normalized_surface.get("review_surface") or workflow_linkage.get("review_surface") or {})
        return dict(
            review_surface.get("dispatch_receipt")
            or workflow_linkage.get("dispatch_receipt")
            or {}
        )

    def _report_dispatch_state(self, *, state: dict[str, Any] | None, dispatch_receipt: dict[str, Any] | None) -> str | None:
        normalized_state = dict(state or {})
        receipt = dict(dispatch_receipt or {})
        receipt_state = str(receipt.get("dispatch_state") or receipt.get("status") or "").strip()
        if receipt_state in {"dispatch_attempted", "dispatch_succeeded", "dispatch_failed"}:
            return receipt_state
        if bool(normalized_state.get("send_ready")):
            return "ready_to_dispatch"
        return None

    def project_report_lifecycle_state(
        self,
        *,
        artifact: dict[str, Any] | None,
        workflow_state: str | None,
        package_state: str | None,
        recommended_action: str | None,
        ready_for_delivery: bool | None,
        review_required: bool | None,
        dispatch_state: str | None,
        selected_is_current: bool | None,
    ) -> dict[str, Any]:
        normalized_artifact = dict(artifact or {})
        normalized_workflow_state = str(workflow_state or "").strip()
        normalized_package_state = str(package_state or "").strip()
        normalized_recommended_action = str(recommended_action or "").strip()
        normalized_dispatch_state = str(dispatch_state or "").strip()
        normalized_status = str(normalized_artifact.get("status") or "").strip()

        reasons: list[str] = []
        if normalized_status == "superseded":
            reasons.append("artifact_status_superseded")
            return {
                "state": "superseded",
                "reason": reasons[0],
                "reason_chain": reasons,
                "workflow_state": normalized_workflow_state or None,
                "dispatch_state": normalized_dispatch_state or None,
            }

        if normalized_dispatch_state == "dispatch_succeeded":
            reasons.append("dispatch_receipt_succeeded")
            state = "sent"
        elif normalized_dispatch_state == "dispatch_failed":
            reasons.append("dispatch_receipt_failed")
            state = "failed"
        elif normalized_recommended_action == "send" and bool(ready_for_delivery):
            reasons.append("ready_for_delivery_send")
            state = "send_ready"
        elif bool(review_required) or normalized_recommended_action == "send_review":
            reasons.append("manual_review_required")
            state = "review_ready"
        elif normalized_status == "withdrawn":
            reasons.append("artifact_status_withdrawn")
            state = "held"
        elif normalized_recommended_action == "hold":
            reasons.append("recommended_action_hold")
            state = "held"
        elif normalized_dispatch_state == "dispatch_attempted":
            reasons.append("dispatch_attempted_pending_receipt")
            state = "send_ready"
        elif normalized_package_state == "ready":
            reasons.append("package_ready_pending_workflow")
            state = "qa_pending"
        elif normalized_package_state == "blocked":
            reasons.append("package_blocked")
            state = "held"
        elif normalized_workflow_state in {"assembling", "rendering", "producing", "publishing"}:
            reasons.append(f"workflow_state_{normalized_workflow_state}")
            state = "producing"
        elif normalized_workflow_state in {"collecting", "scheduled", "planned"}:
            reasons.append(f"workflow_state_{normalized_workflow_state}")
            state = "collecting" if normalized_workflow_state == "collecting" else "planned"
        else:
            reasons.append("insufficient_runtime_progress_defaults_to_planned")
            state = "planned"

        if not bool(selected_is_current) and state not in {"sent", "superseded"}:
            reasons.append("selected_candidate_differs_from_current")
            if state == "send_ready":
                state = "review_ready"

        if state not in CANONICAL_REPORT_LIFECYCLE_STATES:
            raise ValueError(f"invalid projected canonical lifecycle state: {state}")
        return {
            "state": state,
            "reason": reasons[0],
            "reason_chain": reasons,
            "workflow_state": normalized_workflow_state or None,
            "dispatch_state": normalized_dispatch_state or None,
        }

    def report_llm_lineage_summary(self, llm_lineage: dict[str, Any] | None) -> dict[str, Any]:
        normalized_lineage = dict(llm_lineage or {})
        summary = dict(normalized_lineage.get("summary") or {})
        bundle_count = int(summary.get("bundle_count") or 0)
        applied_count = int(summary.get("applied_count") or 0)
        degraded_count = int(summary.get("degraded_count") or 0)
        missing_bundle_count = int(summary.get("missing_bundle_count") or 0)
        primary_count = int(summary.get("primary_applied_count") or 0)
        fallback_count = int(summary.get("fallback_applied_count") or 0)
        deterministic_degrade_count = int(summary.get("deterministic_degrade_count") or 0)
        operator_tags = sorted({str(item) for item in (summary.get("operator_tags") or []) if str(item).strip()})
        slots = [str(item) for item in (summary.get("slots") or []) if str(item).strip()]
        models = [str(item) for item in (summary.get("models") or []) if str(item).strip()]
        token_totals = dict(summary.get("token_totals") or {})
        total_tokens = _usage_int(token_totals, "total_tokens", "totalTokens")
        usage_bundle_count = int(summary.get("usage_bundle_count") or 0)
        costed_bundle_count = int(summary.get("costed_bundle_count") or 0)
        uncosted_bundle_count = int(summary.get("uncosted_bundle_count") or 0)
        estimated_cost_usd = summary.get("estimated_cost_usd")
        model_usage_breakdown = {
            str(model): dict(payload)
            for model, payload in dict(summary.get("model_usage_breakdown") or {}).items()
            if str(model).strip() and isinstance(payload, dict)
        }
        slot_usage_breakdown = {
            str(slot): dict(payload)
            for slot, payload in dict(summary.get("slot_usage_breakdown") or {}).items()
            if str(slot).strip() and isinstance(payload, dict)
        }

        if missing_bundle_count > 0:
            status = "incomplete"
        elif degraded_count > 0:
            status = "degraded"
        elif applied_count > 0:
            status = "applied"
        else:
            status = "not_applied"

        detail_parts = [f"applied={applied_count}/{bundle_count}"]
        if primary_count:
            detail_parts.append(f"primary={primary_count}")
        if fallback_count:
            detail_parts.append(f"fallback={fallback_count}")
        if degraded_count:
            detail_parts.append(f"degraded={degraded_count}")
        if deterministic_degrade_count:
            detail_parts.append(f"deterministic={deterministic_degrade_count}")
        if missing_bundle_count:
            detail_parts.append(f"missing={missing_bundle_count}")
        if operator_tags:
            detail_parts.append(f"tags={','.join(operator_tags)}")
        if slots:
            detail_parts.append(f"slots={','.join(slots)}")
        if models:
            detail_parts.append(f"models={','.join(models)}")
        if total_tokens:
            detail_parts.append(f"tokens={total_tokens}")
        if usage_bundle_count:
            detail_parts.append(f"usage={usage_bundle_count}")
        if estimated_cost_usd is not None:
            detail_parts.append(f"cost_usd={estimated_cost_usd:.6f}")
        elif uncosted_bundle_count:
            detail_parts.append(f"unpriced={uncosted_bundle_count}")
        budget_posture = _llm_budget_posture(
            usage_bundle_count=usage_bundle_count,
            costed_bundle_count=costed_bundle_count,
            uncosted_bundle_count=uncosted_bundle_count,
        )

        return {
            "status": status,
            "bundle_count": bundle_count,
            "applied_count": applied_count,
            "primary_applied_count": primary_count,
            "fallback_applied_count": fallback_count,
            "degraded_count": degraded_count,
            "deterministic_degrade_count": deterministic_degrade_count,
            "missing_bundle_count": missing_bundle_count,
            "operator_tags": operator_tags,
            "slots": slots,
            "models": models,
            "usage_bundle_count": usage_bundle_count,
            "costed_bundle_count": costed_bundle_count,
            "priced_bundle_count": budget_posture.get("priced_bundle_count"),
            "uncosted_bundle_count": uncosted_bundle_count,
            "budget_posture": budget_posture.get("posture"),
            "budget_attention": budget_posture.get("attention"),
            "budget_summary_line": budget_posture.get("summary_line"),
            "token_totals": token_totals,
            "estimated_cost_usd": estimated_cost_usd,
            "model_usage_breakdown": model_usage_breakdown,
            "slot_usage_breakdown": slot_usage_breakdown,
            "summary_line": f"{status} [{' | '.join(detail_parts)}]",
        }

    def report_llm_lineage_from_artifact(self, artifact: dict[str, Any] | None) -> dict[str, Any]:
        normalized_artifact = dict(artifact or {})
        metadata = dict(normalized_artifact.get("metadata_json") or {})
        bundle_ids = [str(item) for item in (metadata.get("bundle_ids") or []) if str(item).strip()]
        bundle_entries: list[dict[str, Any]] = []
        for bundle_id in bundle_ids:
            graph = self.get_bundle_graph(bundle_id)
            bundle = dict((graph or {}).get("bundle") or {})
            payload = dict(bundle.get("payload_json") or {})
            llm_assist = dict(payload.get("llm_assist") or {})
            if not bundle:
                bundle_entries.append({"bundle_id": bundle_id, "missing": True})
                continue
            policy = dict(llm_assist.get("policy") or {})
            role_policy = dict(payload.get("llm_role_policy") or {})
            attempt_failures = list(llm_assist.get("attempt_failures") or policy.get("prior_failures") or [])
            bundle_entries.append(
                {
                    "bundle_id": bundle_id,
                    "slot": bundle.get("slot"),
                    "section_key": bundle.get("section_key"),
                    "summary": bundle.get("summary"),
                    "applied": bool(llm_assist.get("applied")),
                    "model_alias": llm_assist.get("model_alias"),
                    "prompt_version": llm_assist.get("prompt_version"),
                    "input_digest": llm_assist.get("input_digest"),
                    "failure_classification": llm_assist.get("failure_classification"),
                    "operator_tag": policy.get("operator_tag"),
                    "outcome": policy.get("outcome") or ("applied" if llm_assist.get("applied") else "not_applied"),
                    "attempted_model_chain": list(policy.get("attempted_model_chain") or []),
                    "primary_model_alias": policy.get("primary_model_alias"),
                    "fallback_model_aliases": list(policy.get("fallback_model_aliases") or []),
                    "attempt_failure_count": len(attempt_failures),
                    "attempt_failures": attempt_failures,
                    "usage": dict(llm_assist.get("usage") or {}) if isinstance(llm_assist.get("usage"), dict) else None,
                    "role_policy": role_policy,
                    "role_policy_boundary_mode": role_policy.get("boundary_mode"),
                    "role_policy_version": role_policy.get("policy_version"),
                }
            )

        role_policy_versions = sorted({str(item.get("role_policy_version")) for item in bundle_entries if item.get("role_policy_version")})
        boundary_modes = sorted({str(item.get("role_policy_boundary_mode")) for item in bundle_entries if item.get("role_policy_boundary_mode")})
        models = sorted({str(item.get("model_alias")) for item in bundle_entries if item.get("model_alias")})
        slots = [str(item.get("slot")) for item in bundle_entries if item.get("slot")]
        token_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }
        usage_bundle_count = 0
        costed_bundle_count = 0
        estimated_cost_usd_total = 0.0
        model_usage_breakdown: dict[str, dict[str, Any]] = {}
        slot_usage_breakdown: dict[str, dict[str, Any]] = {}
        for item in bundle_entries:
            usage = dict(item.get("usage") or {})
            if not usage:
                continue
            usage_bundle_count += 1
            input_tokens = _usage_int(usage, "input_tokens", "prompt_tokens", "inputTokens", "promptTokens")
            output_tokens = _usage_int(usage, "output_tokens", "completion_tokens", "outputTokens", "completionTokens")
            reasoning_tokens = _usage_int(usage, "reasoning_tokens", "reasoningTokens")
            total_tokens = _usage_int(usage, "total_tokens", "totalTokens")
            if total_tokens <= 0:
                total_tokens = input_tokens + output_tokens + reasoning_tokens
            token_totals["input_tokens"] += input_tokens
            token_totals["output_tokens"] += output_tokens
            token_totals["reasoning_tokens"] += reasoning_tokens
            token_totals["total_tokens"] += total_tokens

            model_alias = str(item.get("model_alias") or "unknown")
            model_bucket = model_usage_breakdown.setdefault(
                model_alias,
                {"bundle_count": 0, "applied_count": 0, "fallback_applied_count": 0, "total_tokens": 0, "estimated_cost_usd": None},
            )
            model_bucket["bundle_count"] += 1
            model_bucket["applied_count"] += int(bool(item.get("applied")))
            model_bucket["fallback_applied_count"] += int(item.get("outcome") == "fallback_applied")
            model_bucket["total_tokens"] += total_tokens

            slot_key = str(item.get("slot") or "unknown")
            slot_bucket = slot_usage_breakdown.setdefault(
                slot_key,
                {"bundle_count": 0, "applied_count": 0, "fallback_applied_count": 0, "total_tokens": 0},
            )
            slot_bucket["bundle_count"] += 1
            slot_bucket["applied_count"] += int(bool(item.get("applied")))
            slot_bucket["fallback_applied_count"] += int(item.get("outcome") == "fallback_applied")
            slot_bucket["total_tokens"] += total_tokens

            estimated_cost_usd = _estimate_usage_cost_usd(model_alias=item.get("model_alias"), usage=usage)
            if estimated_cost_usd is not None:
                costed_bundle_count += 1
                estimated_cost_usd_total += estimated_cost_usd
                current_model_cost = model_bucket.get("estimated_cost_usd")
                model_bucket["estimated_cost_usd"] = round((float(current_model_cost or 0.0) + estimated_cost_usd), 6)

        deterministic_owner_fields = sorted(
            {
                str(field)
                for item in bundle_entries
                for field in (dict(item.get("role_policy") or {}).get("deterministic_owner_fields") or [])
                if str(field).strip()
            }
        )
        forbidden_decisions = sorted(
            {
                str(field)
                for item in bundle_entries
                for field in (dict(item.get("role_policy") or {}).get("forbidden_decisions") or [])
                if str(field).strip()
            }
        )
        override_precedence = next(
            (
                list(dict(item.get("role_policy") or {}).get("override_precedence") or [])
                for item in bundle_entries
                if (dict(item.get("role_policy") or {}).get("override_precedence") or [])
            ),
            [],
        )

        summary = {
            "bundle_count": len(bundle_entries),
            "applied_count": len([item for item in bundle_entries if item.get("applied") is True]),
            "degraded_count": len([item for item in bundle_entries if item.get("applied") is False and not item.get("missing")]),
            "missing_bundle_count": len([item for item in bundle_entries if item.get("missing")]),
            "fallback_applied_count": len([item for item in bundle_entries if item.get("outcome") == "fallback_applied"]),
            "primary_applied_count": len([item for item in bundle_entries if item.get("outcome") == "primary_applied"]),
            "deterministic_degrade_count": len([item for item in bundle_entries if item.get("outcome") == "deterministic_degrade"]),
            "operator_tags": sorted({str(item.get("operator_tag")) for item in bundle_entries if item.get("operator_tag")}),
            "slots": slots,
            "models": models,
            "role_policy_versions": role_policy_versions,
            "boundary_modes": boundary_modes,
            "deterministic_owner_fields": deterministic_owner_fields,
            "forbidden_decisions": forbidden_decisions,
            "override_precedence": override_precedence,
            "usage_bundle_count": usage_bundle_count,
            "uncosted_bundle_count": max(usage_bundle_count - costed_bundle_count, 0),
            "costed_bundle_count": costed_bundle_count,
            "token_totals": token_totals,
            "model_usage_breakdown": model_usage_breakdown,
            "slot_usage_breakdown": slot_usage_breakdown,
            "estimated_cost_usd": round(estimated_cost_usd_total, 6) if costed_bundle_count else None,
        }
        summary.update(
            _llm_budget_posture(
                usage_bundle_count=summary["usage_bundle_count"],
                costed_bundle_count=summary["costed_bundle_count"],
                uncosted_bundle_count=summary["uncosted_bundle_count"],
            )
        )
        return {
            "artifact_id": normalized_artifact.get("artifact_id"),
            "bundle_ids": bundle_ids,
            "summary": summary,
            "bundles": bundle_entries,
            "role_policy": {
                "policy_versions": role_policy_versions,
                "boundary_modes": boundary_modes,
                "deterministic_owner_fields": deterministic_owner_fields,
                "forbidden_decisions": forbidden_decisions,
                "override_precedence": override_precedence,
            },
        }

    def build_operator_board_surface(
        self,
        *,
        business_date: str | None = None,
        history_limit: int = 5,
    ) -> dict[str, Any]:
        from datetime import datetime, timedelta, timezone

        from ifa_data_platform.fsj.report_dispatch import MainReportDeliveryDispatchHelper

        def _lineage_summary(review_surface: dict[str, Any] | None) -> dict[str, Any] | None:
            if not review_surface:
                return None
            return dict(review_surface.get("llm_lineage_summary") or {}) or None

        def _lineage_subject(summary: dict[str, Any] | None, *, subject: str) -> dict[str, Any] | None:
            if not summary:
                return None
            return {
                "subject": subject,
                **summary,
            }

        def _aggregate_lineage_status(subjects: list[dict[str, Any]]) -> dict[str, Any]:
            status_order = {"incomplete": 0, "degraded": 1, "not_applied": 2, "applied": 3}
            status_counts = {
                status: len([item for item in subjects if item.get("status") == status])
                for status in ("incomplete", "degraded", "not_applied", "applied")
            }
            present_subjects = [item for item in subjects if item.get("status")]
            overall_status = "not_available"
            if present_subjects:
                overall_status = min(
                    (str(item.get("status") or "not_applied") for item in present_subjects),
                    key=lambda item: status_order.get(item, 99),
                )
            attention_subjects = [item["subject"] for item in present_subjects if item.get("status") in {"incomplete", "degraded", "not_applied"}]
            fleet_models = sorted({model for item in present_subjects for model in (item.get("models") or []) if str(model).strip()})
            fleet_total_tokens = sum(_usage_int(dict(item.get("token_totals") or {}), "total_tokens", "totalTokens") for item in present_subjects)
            fleet_usage_bundle_count = sum(int(item.get("usage_bundle_count") or 0) for item in present_subjects)
            fleet_costed_bundle_count = sum(int(item.get("costed_bundle_count") or item.get("priced_bundle_count") or 0) for item in present_subjects)
            fleet_uncosted_bundle_count = sum(int(item.get("uncosted_bundle_count") or 0) for item in present_subjects)
            fleet_cost_values = [float(item.get("estimated_cost_usd")) for item in present_subjects if item.get("estimated_cost_usd") is not None]
            fleet_model_usage_breakdown: dict[str, dict[str, Any]] = {}
            fleet_slot_usage_breakdown: dict[str, dict[str, Any]] = {}
            for item in present_subjects:
                for model, payload in dict(item.get("model_usage_breakdown") or {}).items():
                    if not str(model).strip() or not isinstance(payload, dict):
                        continue
                    bucket = fleet_model_usage_breakdown.setdefault(
                        str(model),
                        {"bundle_count": 0, "applied_count": 0, "fallback_applied_count": 0, "total_tokens": 0, "estimated_cost_usd": None},
                    )
                    bucket["bundle_count"] += int(payload.get("bundle_count") or 0)
                    bucket["applied_count"] += int(payload.get("applied_count") or 0)
                    bucket["fallback_applied_count"] += int(payload.get("fallback_applied_count") or 0)
                    bucket["total_tokens"] += _usage_int(dict(payload), "total_tokens", "totalTokens")
                    if payload.get("estimated_cost_usd") is not None:
                        bucket["estimated_cost_usd"] = round(float(bucket.get("estimated_cost_usd") or 0.0) + float(payload.get("estimated_cost_usd")), 6)
                for slot_name, payload in dict(item.get("slot_usage_breakdown") or {}).items():
                    if not str(slot_name).strip() or not isinstance(payload, dict):
                        continue
                    bucket = fleet_slot_usage_breakdown.setdefault(
                        str(slot_name),
                        {"bundle_count": 0, "applied_count": 0, "fallback_applied_count": 0, "total_tokens": 0},
                    )
                    bucket["bundle_count"] += int(payload.get("bundle_count") or 0)
                    bucket["applied_count"] += int(payload.get("applied_count") or 0)
                    bucket["fallback_applied_count"] += int(payload.get("fallback_applied_count") or 0)
                    bucket["total_tokens"] += _usage_int(dict(payload), "total_tokens", "totalTokens")
            budget_posture = _llm_budget_posture(
                usage_bundle_count=fleet_usage_bundle_count,
                costed_bundle_count=fleet_costed_bundle_count,
                uncosted_bundle_count=fleet_uncosted_bundle_count,
            )
            return {
                "overall_status": overall_status,
                "subject_count": len(subjects),
                "reported_subject_count": len(present_subjects),
                "status_counts": status_counts,
                "attention_subjects": attention_subjects,
                "models": fleet_models,
                "total_tokens": fleet_total_tokens,
                "usage_bundle_count": fleet_usage_bundle_count,
                "priced_bundle_count": budget_posture.get("priced_bundle_count"),
                "costed_bundle_count": budget_posture.get("costed_bundle_count"),
                "uncosted_bundle_count": fleet_uncosted_bundle_count,
                "budget_posture": budget_posture.get("posture"),
                "budget_attention": budget_posture.get("attention"),
                "budget_summary_line": budget_posture.get("summary_line"),
                "estimated_cost_usd": round(sum(fleet_cost_values), 6) if fleet_cost_values else None,
                "model_usage_breakdown": fleet_model_usage_breakdown,
                "slot_usage_breakdown": fleet_slot_usage_breakdown,
            }

        def _role_policy_subject(review_surface: dict[str, Any] | None, *, subject: str) -> dict[str, Any] | None:
            if not review_surface:
                return None
            llm_role_policy = dict(review_surface.get("llm_role_policy") or {})
            review_summary = dict(review_surface.get("review_summary") or {})
            slot_boundary_modes = {
                str(slot): str(mode)
                for slot, mode in dict(llm_role_policy.get("slot_boundary_modes") or {}).items()
                if str(slot).strip() and str(mode).strip()
            }
            policy_versions = [str(item) for item in (llm_role_policy.get("policy_versions") or []) if str(item).strip()]
            override_precedence = [str(item) for item in (llm_role_policy.get("override_precedence") or []) if str(item).strip()]
            deterministic_owner_fields = [
                str(item) for item in (llm_role_policy.get("deterministic_owner_fields") or []) if str(item).strip()
            ]
            forbidden_decisions = [str(item) for item in (llm_role_policy.get("forbidden_decisions") or []) if str(item).strip()]
            return {
                "subject": subject,
                "policy_versions": policy_versions,
                "boundary_modes": [str(item) for item in (llm_role_policy.get("boundary_modes") or []) if str(item).strip()],
                "slot_boundary_modes": slot_boundary_modes,
                "override_precedence": override_precedence,
                "deterministic_owner_fields": deterministic_owner_fields,
                "forbidden_decisions": forbidden_decisions,
                "forbidden_decision_count": len(forbidden_decisions),
                "llm_lineage_status": review_summary.get("llm_lineage_status"),
                "llm_lineage_summary": review_summary.get("llm_lineage_summary"),
            }

        def _aggregate_role_policy_review(subjects: list[dict[str, Any]]) -> dict[str, Any]:
            present_subjects = [item for item in subjects if item]
            policy_versions = sorted(
                {
                    version
                    for item in present_subjects
                    for version in (item.get("policy_versions") or [])
                    if str(version).strip()
                }
            )
            boundary_modes = sorted(
                {
                    mode
                    for item in present_subjects
                    for mode in (item.get("boundary_modes") or [])
                    if str(mode).strip()
                }
            )
            deterministic_owner_fields = sorted(
                {
                    field
                    for item in present_subjects
                    for field in (item.get("deterministic_owner_fields") or [])
                    if str(field).strip()
                }
            )
            forbidden_decisions = sorted(
                {
                    field
                    for item in present_subjects
                    for field in (item.get("forbidden_decisions") or [])
                    if str(field).strip()
                }
            )
            override_precedence = next(
                (
                    list(item.get("override_precedence") or [])
                    for item in present_subjects
                    if list(item.get("override_precedence") or [])
                ),
                [],
            )
            slot_boundary_modes_by_subject = {
                str(item.get("subject")): dict(item.get("slot_boundary_modes") or {})
                for item in present_subjects
                if dict(item.get("slot_boundary_modes") or {})
            }
            attention_subjects = [
                str(item.get("subject"))
                for item in present_subjects
                if dict(item.get("slot_boundary_modes") or {}) or list(item.get("override_precedence") or [])
            ]
            return {
                "subject_count": len(subjects),
                "reported_subject_count": len(present_subjects),
                "policy_versions": policy_versions,
                "boundary_modes": boundary_modes,
                "deterministic_owner_fields": deterministic_owner_fields,
                "forbidden_decisions": forbidden_decisions,
                "forbidden_decision_count": len(forbidden_decisions),
                "override_precedence": override_precedence,
                "slot_boundary_modes_by_subject": slot_boundary_modes_by_subject,
                "attention_subjects": attention_subjects,
            }

        def _readiness_subject(review_surface: dict[str, Any] | None, *, subject: str) -> dict[str, Any] | None:
            if not review_surface:
                return None
            artifact = dict(review_surface.get("artifact") or {})
            state = dict(review_surface.get("state") or {})
            review_summary = dict(review_surface.get("review_summary") or {})
            llm_lineage_summary = dict(review_surface.get("llm_lineage_summary") or {})
            canonical_lifecycle = dict(review_surface.get("canonical_lifecycle") or {})
            recommended_action = str(state.get("recommended_action") or review_summary.get("recommended_action") or "hold")
            send_ready = bool(state.get("send_ready"))
            review_required = bool(state.get("review_required")) or recommended_action == "send_review"
            blocked = not send_ready and not review_required
            posture = "blocked"
            if send_ready:
                posture = "ready_to_send"
            elif review_required:
                posture = "review_required"
            llm_status = llm_lineage_summary.get("status")
            lineage_attention = llm_status in {"incomplete", "degraded", "not_applied"}
            needs_attention = blocked or review_required or lineage_attention
            return {
                "subject": subject,
                "artifact_id": artifact.get("artifact_id"),
                "recommended_action": recommended_action,
                "workflow_state": state.get("workflow_state"),
                "package_state": state.get("package_state"),
                "canonical_lifecycle_state": canonical_lifecycle.get("state"),
                "canonical_lifecycle_reason": canonical_lifecycle.get("reason"),
                "go_no_go_decision": review_summary.get("go_no_go_decision"),
                "qa_score": review_summary.get("qa_score"),
                "blocker_count": review_summary.get("blocker_count"),
                "warning_count": review_summary.get("warning_count"),
                "llm_lineage_status": llm_status,
                "llm_lineage_summary": llm_lineage_summary.get("summary_line"),
                "send_ready": send_ready,
                "review_required": review_required,
                "blocked": blocked,
                "lineage_attention": lineage_attention,
                "needs_attention": needs_attention,
                "posture": posture,
            }

        def _qa_axis_subject(review_surface: dict[str, Any] | None, *, subject: str) -> dict[str, Any] | None:
            if not review_surface:
                return None
            state = dict(review_surface.get("state") or {})
            qa_axes = {
                str(axis): dict(payload or {})
                for axis, payload in dict(state.get("qa_axes") or {}).items()
                if str(axis).strip()
            }
            axes_with_attention = sorted(
                axis
                for axis, payload in qa_axes.items()
                if (payload.get("blocker_count") or 0) > 0 or (payload.get("warning_count") or 0) > 0
            )
            not_ready_axes = sorted(axis for axis, payload in qa_axes.items() if payload.get("ready") is False)
            return {
                "subject": subject,
                "qa_axes": qa_axes,
                "axes_with_attention": axes_with_attention,
                "not_ready_axes": not_ready_axes,
                "qa_axis_count": len(qa_axes),
                "qa_axis_ready_count": len([axis for axis, payload in qa_axes.items() if payload.get("ready") is True]),
                "qa_axis_attention_count": len(axes_with_attention),
            }

        def _aggregate_qa_axes(subjects: list[dict[str, Any]]) -> dict[str, Any]:
            present_subjects = [item for item in subjects if item]
            axis_totals: dict[str, dict[str, Any]] = {}
            subjects_with_attention: list[str] = []
            subject_axes_with_attention: dict[str, list[str]] = {}
            not_ready_subjects: list[str] = []
            subject_not_ready_axes: dict[str, list[str]] = {}
            for item in present_subjects:
                subject = str(item.get("subject") or "")
                qa_axes = {
                    str(axis): dict(payload or {})
                    for axis, payload in dict(item.get("qa_axes") or {}).items()
                    if str(axis).strip()
                }
                axes_with_attention = [str(axis) for axis in (item.get("axes_with_attention") or []) if str(axis).strip()]
                not_ready_axes = [str(axis) for axis in (item.get("not_ready_axes") or []) if str(axis).strip()]
                if axes_with_attention:
                    subjects_with_attention.append(subject)
                    subject_axes_with_attention[subject] = axes_with_attention
                if not_ready_axes:
                    not_ready_subjects.append(subject)
                    subject_not_ready_axes[subject] = not_ready_axes
                for axis, payload in qa_axes.items():
                    total = axis_totals.setdefault(
                        axis,
                        {
                            "subject_count": 0,
                            "ready_subject_count": 0,
                            "attention_subject_count": 0,
                            "blocker_count": 0,
                            "warning_count": 0,
                            "issue_codes": set(),
                        },
                    )
                    total["subject_count"] += 1
                    if payload.get("ready") is True:
                        total["ready_subject_count"] += 1
                    if (payload.get("blocker_count") or 0) > 0 or (payload.get("warning_count") or 0) > 0:
                        total["attention_subject_count"] += 1
                    total["blocker_count"] += int(payload.get("blocker_count") or 0)
                    total["warning_count"] += int(payload.get("warning_count") or 0)
                    total["issue_codes"].update(
                        str(code) for code in (payload.get("issue_codes") or []) if str(code).strip()
                    )

            normalized_axis_totals = {
                axis: {
                    "subject_count": payload["subject_count"],
                    "ready_subject_count": payload["ready_subject_count"],
                    "attention_subject_count": payload["attention_subject_count"],
                    "blocker_count": payload["blocker_count"],
                    "warning_count": payload["warning_count"],
                    "ready": payload["attention_subject_count"] == 0 and payload["subject_count"] > 0,
                    "issue_codes": sorted(payload["issue_codes"]),
                }
                for axis, payload in axis_totals.items()
            }
            overall_posture = "not_available"
            if present_subjects:
                if not_ready_subjects:
                    overall_posture = "blocked"
                elif subjects_with_attention:
                    overall_posture = "attention"
                else:
                    overall_posture = "ready"
            return {
                "overall_posture": overall_posture,
                "subject_count": len(subjects),
                "reported_subject_count": len(present_subjects),
                "qa_axis_subject_count": len([item for item in present_subjects if dict(item.get("qa_axes") or {})]),
                "subjects_with_attention": subjects_with_attention,
                "subject_axes_with_attention": subject_axes_with_attention,
                "not_ready_subjects": not_ready_subjects,
                "subject_not_ready_axes": subject_not_ready_axes,
                "axes": normalized_axis_totals,
            }

        def _aggregate_readiness(subjects: list[dict[str, Any]]) -> dict[str, Any]:
            present_subjects = [item for item in subjects if item]
            ready_subjects = [item["subject"] for item in present_subjects if item.get("send_ready")]
            review_subjects = [item["subject"] for item in present_subjects if item.get("review_required")]
            blocked_subjects = [item["subject"] for item in present_subjects if item.get("blocked")]
            lineage_attention_subjects = [item["subject"] for item in present_subjects if item.get("lineage_attention")]
            attention_subjects = [item["subject"] for item in present_subjects if item.get("needs_attention")]
            lifecycle_state_counts: dict[str, int] = {}
            lifecycle_subjects: dict[str, list[str]] = {}
            for item in present_subjects:
                lifecycle_state = str(item.get("canonical_lifecycle_state") or "").strip()
                if not lifecycle_state:
                    continue
                lifecycle_state_counts[lifecycle_state] = lifecycle_state_counts.get(lifecycle_state, 0) + 1
                lifecycle_subjects.setdefault(lifecycle_state, []).append(str(item.get("subject") or ""))
            overall_posture = "not_available"
            if present_subjects:
                if blocked_subjects:
                    overall_posture = "blocked"
                elif review_subjects:
                    overall_posture = "review_required"
                elif len(ready_subjects) == len(present_subjects):
                    overall_posture = "ready_to_send"
                else:
                    overall_posture = "mixed"
            return {
                "overall_posture": overall_posture,
                "subject_count": len(subjects),
                "reported_subject_count": len(present_subjects),
                "ready_subject_count": len(ready_subjects),
                "review_required_count": len(review_subjects),
                "blocked_subject_count": len(blocked_subjects),
                "attention_subject_count": len(attention_subjects),
                "lineage_attention_subject_count": len(lineage_attention_subjects),
                "ready_subjects": ready_subjects,
                "review_required_subjects": review_subjects,
                "blocked_subjects": blocked_subjects,
                "attention_subjects": attention_subjects,
                "lineage_attention_subjects": lineage_attention_subjects,
                "canonical_lifecycle_state_counts": lifecycle_state_counts,
                "canonical_lifecycle_subjects": lifecycle_subjects,
            }

        def _summarize_db_candidate_alignment(
            review_surface: dict[str, Any] | None,
            db_candidate_rows: list[dict[str, Any]],
            *,
            subject: str,
        ) -> dict[str, Any]:
            artifact = dict((review_surface or {}).get("artifact") or {})
            candidate_comparison = dict((review_surface or {}).get("candidate_comparison") or {})
            workflow_handoff = dict((review_surface or {}).get("workflow_handoff") or {})
            state = dict((review_surface or {}).get("state") or {})
            selected_handoff = dict(workflow_handoff.get("selected_handoff") or {})
            ranked_candidates = [dict(item) for item in (candidate_comparison.get("ranked_candidates") or []) if isinstance(item, dict)]
            canonical_db_candidates = [dict(item) for item in (db_candidate_rows or []) if isinstance(item, dict)]
            best_candidate = dict(canonical_db_candidates[0]) if canonical_db_candidates else (dict(ranked_candidates[0]) if ranked_candidates else {})
            current_vs_selected = dict(candidate_comparison.get("current_vs_selected") or {})

            current_artifact_id = (
                candidate_comparison.get("current_artifact_id")
                or current_vs_selected.get("current_artifact_id")
                or artifact.get("artifact_id")
            )
            selected_artifact_id = (
                candidate_comparison.get("selected_artifact_id")
                or current_vs_selected.get("selected_artifact_id")
                or selected_handoff.get("selected_artifact_id")
                or current_artifact_id
            )
            best_artifact_id = best_candidate.get("artifact_id")
            candidate_count = candidate_comparison.get("candidate_count")
            if candidate_count is None:
                candidate_count = len(ranked_candidates) or len(db_candidate_rows)
            ready_candidate_count = candidate_comparison.get("ready_candidate_count")
            if ready_candidate_count is None:
                ready_candidate_count = len([item for item in ranked_candidates or db_candidate_rows if item.get("ready_for_delivery")])

            current_rank = current_vs_selected.get("current_rank") or next(
                (item.get("rank") for item in ranked_candidates if item.get("artifact_id") == current_artifact_id),
                None,
            )
            selected_rank = current_vs_selected.get("selected_rank") or next(
                (item.get("rank") for item in ranked_candidates if item.get("artifact_id") == selected_artifact_id),
                None,
            )
            best_rank = best_candidate.get("rank") or (1 if best_artifact_id else None)

            current_matches_selected = bool(current_artifact_id and selected_artifact_id and current_artifact_id == selected_artifact_id)
            selected_matches_best = bool(selected_artifact_id and best_artifact_id and selected_artifact_id == best_artifact_id)
            current_matches_best = bool(current_artifact_id and best_artifact_id and current_artifact_id == best_artifact_id)

            if not current_artifact_id and not best_artifact_id:
                verdict = "not_available"
                reason_code = "no_main_or_candidate"
                summary_line = "No MAIN artifact or DB candidate is available on the operator board."
            elif not best_artifact_id:
                verdict = "current_only"
                reason_code = "no_db_candidates"
                summary_line = f"Current MAIN artifact {current_artifact_id or '-'} has no DB candidate set to compare against."
            elif current_matches_best and selected_matches_best:
                verdict = "aligned"
                reason_code = "current_selected_match_best_candidate"
                summary_line = f"Current MAIN artifact {current_artifact_id or '-'} matches the best DB candidate."
            elif selected_matches_best and not current_matches_selected:
                if best_candidate.get("ready_for_delivery"):
                    verdict = "mismatch"
                    reason_code = "better_ready_candidate_selected_current_outdated"
                    summary_line = (
                        f"Current MAIN artifact {current_artifact_id or '-'} is not the best DB candidate; "
                        f"selected artifact {selected_artifact_id or '-'} supersedes it as the best ready candidate."
                    )
                elif best_candidate.get("recommended_action") == "send_review":
                    verdict = "review_held"
                    reason_code = "review_held_selected_candidate_differs_from_current"
                    summary_line = (
                        f"Current MAIN artifact {current_artifact_id or '-'} is not the selected DB candidate; "
                        f"operator selection is held on {selected_artifact_id or '-'} for review."
                    )
                else:
                    verdict = "hold"
                    reason_code = "hold_selected_candidate_differs_from_current"
                    summary_line = (
                        f"Current MAIN artifact {current_artifact_id or '-'} differs from selected candidate {selected_artifact_id or '-'}; "
                        "board remains on hold pending the selected package."
                    )
            elif current_matches_selected and not current_matches_best:
                if best_candidate.get("ready_for_delivery"):
                    verdict = "mismatch"
                    reason_code = "selected_current_misses_better_ready_candidate"
                    summary_line = (
                        f"Current selected MAIN artifact {current_artifact_id or '-'} does not match best DB candidate {best_artifact_id or '-'}; "
                        "a better ready candidate exists in DB."
                    )
                elif best_candidate.get("recommended_action") == "send_review":
                    verdict = "review_held"
                    reason_code = "selected_current_held_below_review_candidate"
                    summary_line = (
                        f"Current selected MAIN artifact {current_artifact_id or '-'} trails best DB candidate {best_artifact_id or '-'}; "
                        "the better candidate is review-held rather than send-ready."
                    )
                else:
                    verdict = "hold"
                    reason_code = "selected_current_held_below_blocked_candidate"
                    summary_line = (
                        f"Current selected MAIN artifact {current_artifact_id or '-'} does not match best DB candidate {best_artifact_id or '-'}; "
                        "the board is holding rather than promoting the blocked candidate."
                    )
            else:
                verdict = "mismatch"
                if best_candidate.get("ready_for_delivery"):
                    reason_code = "selection_state_diverged_from_best_ready_candidate"
                    summary_line = (
                        f"Current MAIN artifact {current_artifact_id or '-'} and selected artifact {selected_artifact_id or '-'} "
                        f"both trail better ready DB candidate {best_artifact_id or '-'}."
                    )
                else:
                    reason_code = "selection_state_diverged_from_best_candidate"
                    summary_line = (
                        f"Current MAIN artifact {current_artifact_id or '-'}, selected artifact {selected_artifact_id or '-'}, "
                        f"and best DB candidate {best_artifact_id or '-'} are not aligned."
                    )

            return {
                "subject": subject,
                "verdict": verdict,
                "reason_code": reason_code,
                "summary_line": summary_line,
                "current_artifact_id": current_artifact_id,
                "selected_artifact_id": selected_artifact_id,
                "best_candidate_artifact_id": best_artifact_id,
                "current_matches_selected": current_matches_selected,
                "selected_matches_best": selected_matches_best,
                "current_matches_best": current_matches_best,
                "current_rank": current_rank,
                "selected_rank": selected_rank,
                "best_rank": best_rank,
                "candidate_count": candidate_count,
                "ready_candidate_count": ready_candidate_count,
                "best_candidate_recommended_action": best_candidate.get("recommended_action"),
                "best_candidate_selection_reason": best_candidate.get("selection_reason"),
                "workflow_state": state.get("workflow_state"),
                "recommended_action": state.get("recommended_action"),
                "selected_is_current": selected_handoff.get("selected_is_current"),
            }

        def _summarize_db_candidate_history(
            history_review_surfaces: list[dict[str, Any]],
            db_candidate_rows: list[dict[str, Any]],
        ) -> list[dict[str, Any]]:
            history_summaries: list[dict[str, Any]] = []
            for index, review_surface in enumerate(history_review_surfaces, start=1):
                artifact = dict((review_surface or {}).get("artifact") or {})
                history_summaries.append(
                    {
                        **_summarize_db_candidate_alignment(
                            review_surface,
                            db_candidate_rows,
                            subject=f"history:{index}",
                        ),
                        "history_index": index,
                        "artifact_status": artifact.get("status"),
                    }
                )
            return history_summaries

        beijing = timezone(timedelta(hours=8))
        helper = MainReportDeliveryDispatchHelper()
        resolved_business_date = business_date
        if resolved_business_date is None:
            latest_main = self.get_latest_active_report_delivery_surface(
                agent_domain="main",
                artifact_family="main_final_report",
                max_business_date=datetime.now(beijing).date(),
            )
            latest_artifact = dict((latest_main or {}).get("artifact") or {})
            resolved_business_date = str(latest_artifact.get("business_date") or "") or None
            resolution = {"mode": "latest_active_lookup", "business_date": resolved_business_date, "status": "resolved" if resolved_business_date else "not_found"}
        else:
            resolution = {"mode": "explicit_business_date", "business_date": resolved_business_date}
        empty_domains = {d: None for d in ("ai_tech", "commodities", "macro")}
        empty_lineage = {
            "main": None,
            "support": dict(empty_domains),
            "history": [],
            "aggregate": {
                "overall_status": "not_available",
                "subject_count": 0,
                "reported_subject_count": 0,
                "status_counts": {"incomplete": 0, "degraded": 0, "not_applied": 0, "applied": 0},
                "attention_subjects": [],
            },
        }
        if not resolved_business_date:
            return {
                "business_date": None,
                "resolution": resolution,
                "main": None,
                "main_package": None,
                "main_review": None,
                "main_workflow": None,
                "support": empty_domains,
                "support_packages": dict(empty_domains),
                "support_workflow": dict(empty_domains),
                "history": [],
                "history_packages": [],
                "history_reviews": [],
                "history_workflow": [],
                "db_candidates": [],
                "db_candidate_fleet_summary": {
                    "subject": "main",
                    "verdict": "not_available",
                    "reason_code": "no_business_date",
                    "summary_line": "No business date could be resolved for the operator board.",
                    "current_artifact_id": None,
                    "selected_artifact_id": None,
                    "best_candidate_artifact_id": None,
                    "current_matches_selected": False,
                    "selected_matches_best": False,
                    "current_matches_best": False,
                    "current_rank": None,
                    "selected_rank": None,
                    "best_rank": None,
                    "candidate_count": 0,
                    "ready_candidate_count": 0,
                    "best_candidate_recommended_action": None,
                    "best_candidate_selection_reason": None,
                    "workflow_state": None,
                    "recommended_action": None,
                    "selected_is_current": None,
                },
                "db_candidate_history_summary": [],
                "llm_lineage_summary": empty_lineage,
                "board_readiness_summary": {
                    "main": None,
                    "support": dict(empty_domains),
                    "aggregate": {
                        "overall_posture": "not_available",
                        "subject_count": 0,
                        "reported_subject_count": 0,
                        "ready_subject_count": 0,
                        "review_required_count": 0,
                        "blocked_subject_count": 0,
                        "attention_subject_count": 0,
                        "lineage_attention_subject_count": 0,
                        "ready_subjects": [],
                        "review_required_subjects": [],
                        "blocked_subjects": [],
                        "attention_subjects": [],
                        "lineage_attention_subjects": [],
                    },
                },
            }
        main_active = self.get_active_report_delivery_surface(business_date=resolved_business_date, agent_domain="main", artifact_family="main_final_report")
        main_review = self.get_active_report_operator_review_surface(business_date=resolved_business_date, agent_domain="main", artifact_family="main_final_report")
        support_active = {d: self.get_active_report_delivery_surface(business_date=resolved_business_date, agent_domain=d, artifact_family="support_domain_report") for d in ("ai_tech", "commodities", "macro")}
        support_reviews = {
            d: self.get_active_report_operator_review_surface(
                business_date=resolved_business_date,
                agent_domain=d,
                artifact_family="support_domain_report",
            )
            for d in ("ai_tech", "commodities", "macro")
        }
        history = self.list_report_delivery_surfaces(business_date=resolved_business_date, agent_domain="main", artifact_family="main_final_report", statuses=["active", "superseded"], limit=history_limit)
        history_reviews = self.list_report_operator_review_surfaces(business_date=resolved_business_date, agent_domain="main", artifact_family="main_final_report", statuses=["active", "superseded"], limit=history_limit)
        db_candidate_rows = helper.list_db_delivery_candidates(business_date=resolved_business_date, store=self, limit=history_limit)

        main_lineage = _lineage_summary(main_review)
        support_lineage = {domain: _lineage_summary(review) for domain, review in support_reviews.items()}
        history_lineage = [_lineage_summary(review) for review in history_reviews]
        main_role_policy = _role_policy_subject(main_review, subject="main")
        support_role_policy = {
            domain: _role_policy_subject(review, subject=f"support:{domain}")
            for domain, review in support_reviews.items()
        }
        history_role_policy = [
            _role_policy_subject(review, subject=f"history:{index}")
            for index, review in enumerate(history_reviews, start=1)
        ]
        lineage_subjects = [
            item
            for item in [
                _lineage_subject(main_lineage, subject="main"),
                *[_lineage_subject(summary, subject=f"support:{domain}") for domain, summary in support_lineage.items()],
                *[_lineage_subject(summary, subject=f"history:{index}") for index, summary in enumerate(history_lineage, start=1)],
            ]
            if item
        ]
        readiness_main = _readiness_subject(main_review, subject="main")
        readiness_support = {
            domain: _readiness_subject(review, subject=f"support:{domain}")
            for domain, review in support_reviews.items()
        }
        qa_axes_main = _qa_axis_subject(main_review, subject="main")
        qa_axes_support = {
            domain: _qa_axis_subject(review, subject=f"support:{domain}")
            for domain, review in support_reviews.items()
        }
        readiness_subjects = [item for item in [readiness_main, *readiness_support.values()] if item]
        qa_axis_subjects = [item for item in [qa_axes_main, *qa_axes_support.values()] if item]
        return {
            "business_date": resolved_business_date,
            "resolution": resolution,
            "main": main_review,
            "main_package": self.report_package_surface_from_surface(main_active) if main_active else None,
            "main_review": main_review,
            "main_workflow": self.report_workflow_handoff_from_surface(main_active) if main_active else None,
            "support": support_reviews,
            "support_packages": {d: self.report_package_surface_from_surface(s) if s else None for d, s in support_active.items()},
            "support_workflow": {d: self.report_workflow_handoff_from_surface(s) if s else None for d, s in support_active.items()},
            "history": history_reviews,
            "history_packages": [self.report_package_surface_from_surface(s) for s in history],
            "history_reviews": history_reviews,
            "history_workflow": [self.report_workflow_handoff_from_surface(s) for s in history],
            "db_candidates": [helper.summarize_candidate(c) for c in db_candidate_rows],
            "db_candidate_fleet_summary": _summarize_db_candidate_alignment(
                main_review,
                [helper.summarize_candidate(candidate) for candidate in db_candidate_rows],
                subject="main",
            ),
            "db_candidate_history_summary": _summarize_db_candidate_history(
                history_reviews,
                [helper.summarize_candidate(candidate) for candidate in db_candidate_rows],
            ),
            "llm_lineage_summary": {
                "main": main_lineage,
                "support": support_lineage,
                "history": history_lineage,
                "aggregate": _aggregate_lineage_status(lineage_subjects),
            },
            "llm_role_policy_review": {
                "main": main_role_policy,
                "support": support_role_policy,
                "history": history_role_policy,
                "aggregate": _aggregate_role_policy_review(
                    [
                        item
                        for item in [
                            main_role_policy,
                            *support_role_policy.values(),
                            *history_role_policy,
                        ]
                        if item
                    ]
                ),
            },
            "board_readiness_summary": {
                "main": readiness_main,
                "support": readiness_support,
                "aggregate": _aggregate_readiness(readiness_subjects),
            },
            "qa_axes_summary": {
                "main": qa_axes_main,
                "support": qa_axes_support,
                "aggregate": _aggregate_qa_axes(qa_axis_subjects),
            },
        }

    def _report_workflow_handoff_from_artifact(
        self,
        artifact: dict[str, Any],
        *,
        delivery_package: dict[str, Any] | None,
        workflow_linkage: dict[str, Any] | None,
    ) -> dict[str, Any]:
        normalized_artifact = dict(artifact or {})
        normalized_delivery_package = dict(delivery_package or {})
        normalized_workflow_linkage = dict(workflow_linkage or {})
        workflow = dict(normalized_delivery_package.get("workflow") or {})
        quality_gate = dict(normalized_delivery_package.get("quality_gate") or {})
        selected_handoff = dict(normalized_workflow_linkage.get("selected_handoff") or {})
        artifacts = dict(normalized_delivery_package.get("artifacts") or {})
        dispatch_advice = dict(normalized_delivery_package.get("dispatch_advice") or {})
        recommended_action = workflow.get("recommended_action") or dispatch_advice.get("recommended_action") or "hold"
        resolved_selected_handoff = {
            "selected_artifact_id": selected_handoff.get("selected_artifact_id") or normalized_artifact.get("artifact_id"),
            "selected_report_run_id": selected_handoff.get("selected_report_run_id") or normalized_artifact.get("report_run_id"),
            "selected_business_date": selected_handoff.get("selected_business_date") or normalized_artifact.get("business_date"),
            "selected_is_current": selected_handoff.get("selected_is_current") if "selected_is_current" in selected_handoff else True,
            "selected_delivery_package_dir": selected_handoff.get("delivery_package_dir") or normalized_delivery_package.get("delivery_package_dir"),
            "selected_delivery_manifest_path": selected_handoff.get("delivery_manifest_path") or normalized_delivery_package.get("delivery_manifest_path"),
            "selected_delivery_zip_path": selected_handoff.get("delivery_zip_path") or normalized_delivery_package.get("delivery_zip_path"),
            "selected_telegram_caption_path": selected_handoff.get("telegram_caption_path") or normalized_delivery_package.get("telegram_caption_path"),
        }
        return {
            "artifact": {
                "artifact_id": normalized_artifact.get("artifact_id"),
                "report_run_id": normalized_artifact.get("report_run_id"),
                "business_date": normalized_artifact.get("business_date"),
                "status": normalized_artifact.get("status"),
                "supersedes_artifact_id": normalized_artifact.get("supersedes_artifact_id"),
                "created_at": normalized_artifact.get("created_at"),
                "updated_at": normalized_artifact.get("updated_at"),
            },
            "selected_handoff": resolved_selected_handoff,
            "state": {
                "package_state": normalized_delivery_package.get("package_state"),
                "ready_for_delivery": normalized_delivery_package.get("ready_for_delivery"),
                "recommended_action": recommended_action,
                "dispatch_recommended_action": workflow.get("dispatch_recommended_action"),
                "workflow_state": workflow.get("workflow_state"),
                "ready_for_delivery": normalized_delivery_package.get("ready_for_delivery"),
                "send_ready": bool(normalized_delivery_package.get("ready_for_delivery")) and recommended_action == "send",
                "review_required": recommended_action == "send_review",
                "next_step": workflow.get("next_step"),
                "selection_reason": workflow.get("selection_reason"),
                "dispatch_selected_artifact_id": workflow.get("dispatch_selected_artifact_id"),
                "send_blockers": list(workflow.get("send_blockers") or []),
                "qa_score": quality_gate.get("score"),
                "blocker_count": quality_gate.get("blocker_count"),
                "warning_count": quality_gate.get("warning_count"),
                "qa_axes": dict(quality_gate.get("qa_axes") or {}),
                "late_contract_mode": quality_gate.get("late_contract_mode"),
            },
            "manifest_pointers": {
                "delivery_manifest_path": normalized_delivery_package.get("delivery_manifest_path"),
                "send_manifest_path": normalized_workflow_linkage.get("send_manifest_path"),
                "review_manifest_path": normalized_workflow_linkage.get("review_manifest_path"),
                "workflow_manifest_path": normalized_workflow_linkage.get("workflow_manifest_path"),
                "operator_review_bundle_path": normalized_workflow_linkage.get("operator_review_bundle_path"),
                "operator_review_readme_path": normalized_workflow_linkage.get("operator_review_readme_path"),
                "package_index_path": normalized_delivery_package.get("package_index_path"),
                "package_browse_readme_path": normalized_delivery_package.get("package_browse_readme_path"),
                "telegram_caption_path": normalized_delivery_package.get("telegram_caption_path"),
                "delivery_zip_path": normalized_delivery_package.get("delivery_zip_path"),
            },
            "version_pointers": {
                "artifact_version": normalized_artifact.get("artifact_version"),
                "delivery_manifest_version": artifacts.get("delivery_manifest"),
                "send_manifest_version": artifacts.get("send_manifest"),
                "review_manifest_version": artifacts.get("review_manifest"),
                "workflow_manifest_version": artifacts.get("workflow_manifest"),
                "package_index_version": artifacts.get("package_index"),
            },
        }

    def persist_report_workflow_linkage(self, artifact_id: str, workflow_linkage: dict[str, Any]) -> dict[str, Any] | None:
        self.ensure_schema()
        normalized_linkage = dict(workflow_linkage or {})
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT metadata_json FROM ifa2.ifa_fsj_report_artifacts WHERE artifact_id=:artifact_id"),
                {"artifact_id": artifact_id},
            ).mappings().first()
            if not row:
                return None
            metadata = dict(row.get("metadata_json") or {})
            delivery_package = dict(metadata.get("delivery_package") or {})
            delivery_workflow = {
                **dict(delivery_package.get("workflow") or {}),
                **normalized_linkage,
            }
            if delivery_package:
                delivery_package["workflow"] = delivery_workflow
            metadata["workflow_linkage"] = normalized_linkage
            review_surface = dict(metadata.get("review_surface") or {})
            incoming_review_surface = dict(normalized_linkage.get("review_surface") or {})
            if incoming_review_surface:
                review_surface = {
                    **review_surface,
                    **incoming_review_surface,
                }
                metadata["review_surface"] = review_surface
            if delivery_package:
                metadata["delivery_package"] = delivery_package
            conn.execute(
                text(
                    """
                    UPDATE ifa2.ifa_fsj_report_artifacts
                       SET metadata_json=CAST(:metadata_json AS jsonb),
                           updated_at=now()
                     WHERE artifact_id=:artifact_id
                    """
                ),
                {
                    "artifact_id": artifact_id,
                    "metadata_json": self._json_dumps(metadata),
                },
            )
        return self.get_report_artifact(artifact_id)

    def persist_report_dispatch_receipt(self, artifact_id: str, dispatch_receipt: dict[str, Any]) -> dict[str, Any] | None:
        self.ensure_schema()
        normalized_receipt = dict(dispatch_receipt or {})
        persisted_state = str(normalized_receipt.get("dispatch_state") or normalized_receipt.get("status") or "").strip()
        if persisted_state not in {"dispatch_attempted", "dispatch_succeeded", "dispatch_failed"}:
            raise ValueError("dispatch receipt must persist one of: dispatch_attempted|dispatch_succeeded|dispatch_failed")
        normalized_receipt["dispatch_state"] = persisted_state

        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT metadata_json FROM ifa2.ifa_fsj_report_artifacts WHERE artifact_id=:artifact_id"),
                {"artifact_id": artifact_id},
            ).mappings().first()
            if not row:
                return None

            metadata = dict(row.get("metadata_json") or {})
            workflow_linkage = dict(metadata.get("workflow_linkage") or {})
            workflow_linkage["dispatch_receipt"] = normalized_receipt
            metadata["workflow_linkage"] = workflow_linkage

            review_surface = dict(metadata.get("review_surface") or {})
            review_surface["dispatch_receipt"] = normalized_receipt
            metadata["review_surface"] = review_surface

            delivery_package = dict(metadata.get("delivery_package") or {})
            if delivery_package:
                workflow = dict(delivery_package.get("workflow") or {})
                workflow["dispatch_state"] = persisted_state
                delivery_package["workflow"] = workflow
                metadata["delivery_package"] = delivery_package

            conn.execute(
                text(
                    """
                    UPDATE ifa2.ifa_fsj_report_artifacts
                       SET metadata_json=CAST(:metadata_json AS jsonb),
                           updated_at=now()
                     WHERE artifact_id=:artifact_id
                    """
                ),
                {
                    "artifact_id": artifact_id,
                    "metadata_json": self._json_dumps(metadata),
                },
            )
        return self.get_report_artifact(artifact_id)

    def get_active_bundle(self, *, business_date: str, slot: str, agent_domain: str, section_key: str, bundle_topic_key: str | None = None) -> dict[str, Any] | None:
        self.ensure_schema()
        sql = """
        SELECT bundle_id
          FROM ifa2.ifa_fsj_bundles
         WHERE business_date=:business_date
           AND slot=:slot
           AND agent_domain=:agent_domain
           AND section_key=:section_key
           AND status='active'
        """
        params: dict[str, Any] = {
            "business_date": business_date,
            "slot": slot,
            "agent_domain": agent_domain,
            "section_key": section_key,
        }
        if bundle_topic_key is None:
            sql += " AND bundle_topic_key IS NULL"
        else:
            sql += " AND bundle_topic_key=:bundle_topic_key"
            params["bundle_topic_key"] = bundle_topic_key
        sql += " ORDER BY updated_at DESC LIMIT 1"
        with self.engine.begin() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if not row:
            return None
        return self.get_bundle_graph(row["bundle_id"])

    def get_bundle_graph(self, bundle_id: str) -> dict[str, Any] | None:
        self.ensure_schema()
        with self.engine.begin() as conn:
            bundle = conn.execute(text("SELECT * FROM ifa2.ifa_fsj_bundles WHERE bundle_id=:bundle_id"), {"bundle_id": bundle_id}).mappings().first()
            if not bundle:
                return None
            objects = conn.execute(text("SELECT * FROM ifa2.ifa_fsj_objects WHERE bundle_id=:bundle_id ORDER BY fsj_kind, object_key"), {"bundle_id": bundle_id}).mappings().all()
            edges = conn.execute(text("SELECT * FROM ifa2.ifa_fsj_edges WHERE bundle_id=:bundle_id ORDER BY edge_type, from_object_key, to_object_key"), {"bundle_id": bundle_id}).mappings().all()
            evidence_links = conn.execute(text("SELECT * FROM ifa2.ifa_fsj_evidence_links WHERE bundle_id=:bundle_id ORDER BY evidence_role, object_key NULLS FIRST"), {"bundle_id": bundle_id}).mappings().all()
            observed_records = conn.execute(text("SELECT * FROM ifa2.ifa_fsj_observed_records WHERE bundle_id=:bundle_id ORDER BY fsj_kind, object_key"), {"bundle_id": bundle_id}).mappings().all()
            report_links = conn.execute(text("SELECT * FROM ifa2.ifa_fsj_report_links WHERE bundle_id=:bundle_id ORDER BY artifact_type"), {"bundle_id": bundle_id}).mappings().all()
        return {
            "bundle": self._mapping_to_dict(bundle),
            "objects": [self._mapping_to_dict(x) for x in objects],
            "edges": [self._mapping_to_dict(x) for x in edges],
            "evidence_links": [self._mapping_to_dict(x) for x in evidence_links],
            "observed_records": [self._mapping_to_dict(x) for x in observed_records],
            "report_links": [self._mapping_to_dict(x) for x in report_links],
        }

    def _validate_bundle(self, bundle: dict[str, Any]) -> None:
        required = [
            "bundle_id", "market", "business_date", "slot", "agent_domain", "section_key",
            "section_type", "producer", "producer_version", "assembly_mode", "status", "summary",
        ]
        for key in required:
            if not bundle.get(key):
                raise ValueError(f"bundle missing required field: {key}")
        if bundle["status"] not in VALID_BUNDLE_STATUS:
            raise ValueError(f"invalid bundle status: {bundle['status']}")

    def _validate_object(self, obj: dict[str, Any]) -> None:
        for key in ["fsj_kind", "object_key", "statement"]:
            if not obj.get(key):
                raise ValueError(f"object missing required field: {key}")
        if obj["fsj_kind"] not in VALID_FSJ_KINDS:
            raise ValueError(f"invalid fsj_kind: {obj['fsj_kind']}")

    def _validate_edge(self, edge: dict[str, Any]) -> None:
        for key in ["edge_type", "from_fsj_kind", "from_object_key", "to_fsj_kind", "to_object_key"]:
            if not edge.get(key):
                raise ValueError(f"edge missing required field: {key}")
        if edge["edge_type"] not in VALID_EDGE_TYPES:
            raise ValueError(f"invalid edge_type: {edge['edge_type']}")
        if edge["from_fsj_kind"] not in VALID_FSJ_KINDS or edge["to_fsj_kind"] not in VALID_FSJ_KINDS:
            raise ValueError("edge fsj_kind must be one of fact|signal|judgment")

    def _mapping_to_dict(self, row: Any) -> dict[str, Any]:
        out: dict[str, Any] = dict(row)
        for key, value in list(out.items()):
            if isinstance(value, uuid.UUID):
                out[key] = str(value)
        return out
