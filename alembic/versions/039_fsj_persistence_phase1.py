"""Add FSJ persistence phase1 core tables

Revision ID: 039_fsj_persistence_phase1
Revises: 038_slot_replay_evidence
Create Date: 2026-04-22 07:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '039_fsj_persistence_phase1'
down_revision = '038_slot_replay_evidence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ifa_fsj_bundles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('bundle_id', sa.Text(), nullable=False),
        sa.Column('market', sa.Text(), nullable=False),
        sa.Column('business_date', sa.Date(), nullable=False),
        sa.Column('slot', sa.Text(), nullable=False),
        sa.Column('agent_domain', sa.Text(), nullable=False),
        sa.Column('section_key', sa.Text(), nullable=False),
        sa.Column('section_type', sa.Text(), nullable=False),
        sa.Column('bundle_topic_key', sa.Text(), nullable=True),
        sa.Column('producer', sa.Text(), nullable=False),
        sa.Column('producer_version', sa.Text(), nullable=False),
        sa.Column('assembly_mode', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('supersedes_bundle_id', sa.Text(), nullable=True),
        sa.Column('slot_run_id', sa.Text(), nullable=True),
        sa.Column('replay_id', sa.Text(), nullable=True),
        sa.Column('report_run_id', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("status in ('active', 'superseded', 'withdrawn')", name='ck_ifa_fsj_bundles_status'),
        sa.ForeignKeyConstraint(['supersedes_bundle_id'], ['ifa2.ifa_fsj_bundles.bundle_id'], ondelete='SET NULL'),
        sa.UniqueConstraint('bundle_id', name='uq_ifa_fsj_bundles_bundle_id'),
        schema='ifa2',
    )
    op.create_index('ix_ifa_fsj_bundles_lookup', 'ifa_fsj_bundles', ['business_date', 'slot', 'agent_domain', 'section_key', 'status', 'bundle_topic_key'], unique=False, schema='ifa2')
    op.create_index('ix_ifa_fsj_bundles_supersedes', 'ifa_fsj_bundles', ['supersedes_bundle_id'], unique=False, schema='ifa2')

    op.create_table(
        'ifa_fsj_objects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('bundle_id', sa.Text(), nullable=False),
        sa.Column('object_id', sa.Text(), nullable=False),
        sa.Column('fsj_kind', sa.Text(), nullable=False),
        sa.Column('object_key', sa.Text(), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('object_type', sa.Text(), nullable=True),
        sa.Column('judgment_action', sa.Text(), nullable=True),
        sa.Column('direction', sa.Text(), nullable=True),
        sa.Column('priority', sa.Text(), nullable=True),
        sa.Column('signal_strength', sa.Text(), nullable=True),
        sa.Column('horizon', sa.Text(), nullable=True),
        sa.Column('evidence_level', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Text(), nullable=True),
        sa.Column('entity_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('metric_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('invalidators', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('attributes_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("fsj_kind in ('fact', 'signal', 'judgment')", name='ck_ifa_fsj_objects_kind'),
        sa.ForeignKeyConstraint(['bundle_id'], ['ifa2.ifa_fsj_bundles.bundle_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('bundle_id', 'fsj_kind', 'object_key', name='uq_ifa_fsj_objects_bundle_kind_key'),
        sa.UniqueConstraint('bundle_id', 'object_id', name='uq_ifa_fsj_objects_bundle_object_id'),
        schema='ifa2',
    )
    op.create_index('ix_ifa_fsj_objects_kind_type', 'ifa_fsj_objects', ['fsj_kind', 'object_type'], unique=False, schema='ifa2')
    op.create_index('ix_ifa_fsj_objects_bundle', 'ifa_fsj_objects', ['bundle_id', 'fsj_kind', 'object_key'], unique=False, schema='ifa2')

    op.create_table(
        'ifa_fsj_edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('bundle_id', sa.Text(), nullable=False),
        sa.Column('edge_type', sa.Text(), nullable=False),
        sa.Column('from_fsj_kind', sa.Text(), nullable=False),
        sa.Column('from_object_key', sa.Text(), nullable=False),
        sa.Column('to_fsj_kind', sa.Text(), nullable=False),
        sa.Column('to_object_key', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=True),
        sa.Column('attributes_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("edge_type in ('fact_to_signal', 'signal_to_judgment', 'judgment_to_judgment')", name='ck_ifa_fsj_edges_type'),
        sa.CheckConstraint("from_fsj_kind in ('fact', 'signal', 'judgment')", name='ck_ifa_fsj_edges_from_kind'),
        sa.CheckConstraint("to_fsj_kind in ('fact', 'signal', 'judgment')", name='ck_ifa_fsj_edges_to_kind'),
        sa.ForeignKeyConstraint(['bundle_id'], ['ifa2.ifa_fsj_bundles.bundle_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('bundle_id', 'edge_type', 'from_object_key', 'to_object_key', name='uq_ifa_fsj_edges_bundle_path'),
        schema='ifa2',
    )
    op.create_index('ix_ifa_fsj_edges_bundle', 'ifa_fsj_edges', ['bundle_id', 'edge_type'], unique=False, schema='ifa2')

    op.create_table(
        'ifa_fsj_evidence_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('bundle_id', sa.Text(), nullable=False),
        sa.Column('object_key', sa.Text(), nullable=True),
        sa.Column('fsj_kind', sa.Text(), nullable=True),
        sa.Column('evidence_role', sa.Text(), nullable=False),
        sa.Column('ref_system', sa.Text(), nullable=False),
        sa.Column('ref_family', sa.Text(), nullable=True),
        sa.Column('ref_table', sa.Text(), nullable=True),
        sa.Column('ref_key', sa.Text(), nullable=True),
        sa.Column('ref_locator_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("fsj_kind is null or fsj_kind in ('fact', 'signal', 'judgment')", name='ck_ifa_fsj_evidence_links_kind'),
        sa.ForeignKeyConstraint(['bundle_id'], ['ifa2.ifa_fsj_bundles.bundle_id'], ondelete='CASCADE'),
        schema='ifa2',
    )
    op.create_index('ix_ifa_fsj_evidence_links_bundle', 'ifa_fsj_evidence_links', ['bundle_id', 'evidence_role', 'fsj_kind'], unique=False, schema='ifa2')
    op.execute("""
    CREATE UNIQUE INDEX uq_ifa_fsj_evidence_links_natural
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
    """)

    op.create_table(
        'ifa_fsj_observed_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('bundle_id', sa.Text(), nullable=False),
        sa.Column('object_key', sa.Text(), nullable=False),
        sa.Column('fsj_kind', sa.Text(), nullable=False),
        sa.Column('source_layer', sa.Text(), nullable=False),
        sa.Column('source_family', sa.Text(), nullable=True),
        sa.Column('source_table', sa.Text(), nullable=True),
        sa.Column('source_record_key', sa.Text(), nullable=True),
        sa.Column('observed_label', sa.Text(), nullable=True),
        sa.Column('observed_payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("fsj_kind in ('fact', 'signal', 'judgment')", name='ck_ifa_fsj_observed_records_kind'),
        sa.ForeignKeyConstraint(['bundle_id'], ['ifa2.ifa_fsj_bundles.bundle_id'], ondelete='CASCADE'),
        schema='ifa2',
    )
    op.create_index('ix_ifa_fsj_observed_records_bundle', 'ifa_fsj_observed_records', ['bundle_id', 'fsj_kind', 'object_key'], unique=False, schema='ifa2')
    op.execute("""
    CREATE UNIQUE INDEX uq_ifa_fsj_observed_records_natural
      ON ifa2.ifa_fsj_observed_records (
        bundle_id, object_key, fsj_kind, source_layer,
        COALESCE(source_family, ''), COALESCE(source_table, ''), COALESCE(source_record_key, '')
      )
    """)

    op.create_table(
        'ifa_fsj_report_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('bundle_id', sa.Text(), nullable=False),
        sa.Column('report_run_id', sa.Text(), nullable=True),
        sa.Column('artifact_type', sa.Text(), nullable=False),
        sa.Column('artifact_uri', sa.Text(), nullable=True),
        sa.Column('artifact_locator_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('section_render_key', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bundle_id'], ['ifa2.ifa_fsj_bundles.bundle_id'], ondelete='CASCADE'),
        schema='ifa2',
    )
    op.create_index('ix_ifa_fsj_report_links_bundle', 'ifa_fsj_report_links', ['bundle_id', 'artifact_type'], unique=False, schema='ifa2')
    op.execute("""
    CREATE UNIQUE INDEX uq_ifa_fsj_report_links_natural
      ON ifa2.ifa_fsj_report_links (
        bundle_id, artifact_type, COALESCE(report_run_id, ''), COALESCE(artifact_uri, ''), COALESCE(section_render_key, '')
      )
    """)


def downgrade() -> None:
    op.drop_index('ix_ifa_fsj_report_links_bundle', table_name='ifa_fsj_report_links', schema='ifa2')
    op.execute('DROP INDEX IF EXISTS ifa2.uq_ifa_fsj_report_links_natural')
    op.drop_table('ifa_fsj_report_links', schema='ifa2')

    op.drop_index('ix_ifa_fsj_observed_records_bundle', table_name='ifa_fsj_observed_records', schema='ifa2')
    op.execute('DROP INDEX IF EXISTS ifa2.uq_ifa_fsj_observed_records_natural')
    op.drop_table('ifa_fsj_observed_records', schema='ifa2')

    op.drop_index('ix_ifa_fsj_evidence_links_bundle', table_name='ifa_fsj_evidence_links', schema='ifa2')
    op.execute('DROP INDEX IF EXISTS ifa2.uq_ifa_fsj_evidence_links_natural')
    op.drop_table('ifa_fsj_evidence_links', schema='ifa2')

    op.drop_index('ix_ifa_fsj_edges_bundle', table_name='ifa_fsj_edges', schema='ifa2')
    op.drop_table('ifa_fsj_edges', schema='ifa2')

    op.drop_index('ix_ifa_fsj_objects_bundle', table_name='ifa_fsj_objects', schema='ifa2')
    op.drop_index('ix_ifa_fsj_objects_kind_type', table_name='ifa_fsj_objects', schema='ifa2')
    op.drop_table('ifa_fsj_objects', schema='ifa2')

    op.drop_index('ix_ifa_fsj_bundles_supersedes', table_name='ifa_fsj_bundles', schema='ifa2')
    op.drop_index('ix_ifa_fsj_bundles_lookup', table_name='ifa_fsj_bundles', schema='ifa2')
    op.drop_table('ifa_fsj_bundles', schema='ifa2')
