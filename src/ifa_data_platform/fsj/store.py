from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine

VALID_BUNDLE_STATUS = {"active", "superseded", "withdrawn"}
VALID_REPORT_ARTIFACT_STATUS = {"active", "superseded", "withdrawn"}
VALID_FSJ_KINDS = {"fact", "signal", "judgment"}
VALID_EDGE_TYPES = {"fact_to_signal", "signal_to_judgment", "judgment_to_judgment"}

SCHEMA_DDL = [
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
    def __init__(self) -> None:
        self.engine = make_engine()

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

    def _report_delivery_surface_from_artifact(self, artifact: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(artifact.get("metadata_json") or {})
        delivery_package = dict(metadata.get("delivery_package") or {})
        workflow_linkage = dict(metadata.get("workflow_linkage") or {})
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

        review_payload = dict(
            dict(normalized_surface.get("review_surface") or {})
            or dict((normalized_surface.get("workflow_linkage") or {}).get("review_surface") or {})
        )
        candidate_comparison = dict(review_payload.get("candidate_comparison") or {})
        operator_go_no_go = dict(review_payload.get("operator_go_no_go") or {})
        review_manifest = dict(review_payload.get("review_manifest") or {})
        send_manifest = dict(review_payload.get("send_manifest") or {})

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

        return {
            "artifact": dict(workflow_handoff.get("artifact") or artifact),
            "selected_handoff": dict(workflow_handoff.get("selected_handoff") or {}),
            "state": state,
            "package_paths": dict(package_surface.get("package_paths") or {}),
            "package_versions": dict(package_surface.get("package_versions") or {}),
            "package_state": package_state,
            "workflow_handoff": workflow_handoff,
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
            "review_summary": {
                "recommended_action": state.get("recommended_action"),
                "workflow_state": state.get("workflow_state"),
                "selected_artifact_id": selected_artifact_id,
                "current_artifact_id": current_artifact_id,
                "selected_is_current": (workflow_handoff.get("selected_handoff") or {}).get("selected_is_current"),
                "candidate_count": candidate_count,
                "ready_candidate_count": ready_candidate_count,
                "qa_score": quality_gate.get("score"),
                "blocker_count": quality_gate.get("blocker_count"),
                "warning_count": quality_gate.get("warning_count"),
                "go_no_go_decision": computed_decision,
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
        if not resolved_business_date:
            return {"business_date": None, "resolution": resolution, "main": None, "main_package": None, "support": {d: None for d in ("ai_tech", "commodities", "macro")}, "support_packages": {d: None for d in ("ai_tech", "commodities", "macro")}, "history": [], "history_packages": [], "db_candidates": []}
        main_active = self.get_active_report_delivery_surface(business_date=resolved_business_date, agent_domain="main", artifact_family="main_final_report")
        support = {d: self.get_active_report_delivery_surface(business_date=resolved_business_date, agent_domain=d, artifact_family="support_domain_report") for d in ("ai_tech", "commodities", "macro")}
        history = self.list_report_delivery_surfaces(business_date=resolved_business_date, agent_domain="main", artifact_family="main_final_report", statuses=["active", "superseded"], limit=history_limit)
        db_candidates = helper.list_db_delivery_candidates(business_date=resolved_business_date, store=self, limit=history_limit)
        return {
            "business_date": resolved_business_date,
            "resolution": resolution,
            "main": self.report_workflow_handoff_from_surface(main_active) if main_active else None,
            "main_package": self.report_package_surface_from_surface(main_active) if main_active else None,
            "support": {d: self.report_workflow_handoff_from_surface(s) if s else None for d, s in support.items()},
            "support_packages": {d: self.report_package_surface_from_surface(s) if s else None for d, s in support.items()},
            "history": [self.report_workflow_handoff_from_surface(s) for s in history],
            "history_packages": [self.report_package_surface_from_surface(s) for s in history],
            "db_candidates": [helper.summarize_candidate(c) for c in db_candidates],
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
                "send_ready": bool(normalized_delivery_package.get("ready_for_delivery")) and recommended_action == "send",
                "review_required": recommended_action == "send_review",
                "next_step": workflow.get("next_step"),
                "selection_reason": workflow.get("selection_reason"),
                "dispatch_selected_artifact_id": workflow.get("dispatch_selected_artifact_id"),
                "send_blockers": list(workflow.get("send_blockers") or []),
                "qa_score": quality_gate.get("score"),
                "blocker_count": quality_gate.get("blocker_count"),
                "warning_count": quality_gate.get("warning_count"),
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
