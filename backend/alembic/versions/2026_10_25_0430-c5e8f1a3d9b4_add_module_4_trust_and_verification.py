"""add module 4 trust and verification tables

Revision ID: c5e8f1a3d9b4
Revises: f4a9b2c8e1d7
Create Date: 2026-10-25 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e8f1a3d9b4'
down_revision: Union[str, None] = 'f4a9b2c8e1d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. field_provenances
    op.create_table(
        'field_provenances',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('recorded_value', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_actor_id', sa.String(length=36), nullable=True),
        sa.Column('source_service_id', sa.String(length=100), nullable=True),
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_reference', sa.String(length=255), nullable=True),
        sa.Column('related_document_id', sa.String(length=36), nullable=True),
        sa.Column('related_document_version_id', sa.String(length=36), nullable=True),
        sa.Column('related_validation_run_id', sa.String(length=36), nullable=True),
        sa.Column('prior_provenance_id', sa.String(length=36), nullable=True),
        sa.Column('superseded_by_id', sa.String(length=36), nullable=True),
        sa.Column('provenance_schema_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_validation_run_id'], ['validation_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['prior_provenance_id'], ['field_provenances.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['superseded_by_id'], ['field_provenances.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fp_instrument', 'field_provenances', ['instrument_id'])
    op.create_index('ix_fp_field_name', 'field_provenances', ['field_name'])
    op.create_index('ix_fp_source_type', 'field_provenances', ['source_type'])
    op.create_index('ix_fp_source_actor', 'field_provenances', ['source_actor_id'])
    op.create_index('ix_fp_is_active', 'field_provenances', ['is_active'])

    # 2. verification_requests
    op.create_table(
        'verification_requests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('reference_code', sa.String(length=100), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('snapshot_data_json', sa.Text(), nullable=False),
        sa.Column('requested_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference_code')
    )
    op.create_index('ix_vr_instrument', 'verification_requests', ['instrument_id'])
    op.create_index('ix_vr_status', 'verification_requests', ['status'])

    # 3. verification_responses
    op.create_table(
        'verification_responses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('result', sa.String(length=50), nullable=False),
        sa.Column('bank_reference_number', sa.String(length=100), nullable=True),
        sa.Column('bank_values_json', sa.Text(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_document_id', sa.String(length=36), nullable=True),
        sa.Column('evidence_document_version_id', sa.String(length=36), nullable=True),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('recorded_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['verification_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['evidence_document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recorded_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('ix_vresp_request', 'verification_responses', ['request_id'])
    op.create_index('ix_vresp_instrument', 'verification_responses', ['instrument_id'])
    op.create_index('ix_vresp_result', 'verification_responses', ['result'])
    op.create_index('ix_vresp_simulated', 'verification_responses', ['is_simulated'])

    # 4. trust_assessments
    op.create_table(
        'trust_assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('trust_level', sa.String(length=50), nullable=False),
        sa.Column('supporting_evidence_references_json', sa.Text(), nullable=True),
        sa.Column('supporting_document_version_id', sa.String(length=36), nullable=True),
        sa.Column('related_validation_run_id', sa.String(length=36), nullable=True),
        sa.Column('related_verification_response_id', sa.String(length=36), nullable=True),
        sa.Column('assessing_user_id', sa.String(length=36), nullable=True),
        sa.Column('assessing_service', sa.String(length=100), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('assessment_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trust_rule_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('is_downgrade', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('superseded_by_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supporting_document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_validation_run_id'], ['validation_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_verification_response_id'], ['verification_responses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assessing_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['superseded_by_id'], ['trust_assessments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ta_instrument', 'trust_assessments', ['instrument_id'])
    op.create_index('ix_ta_field_name', 'trust_assessments', ['field_name'])
    op.create_index('ix_ta_trust_level', 'trust_assessments', ['trust_level'])
    op.create_index('ix_ta_status', 'trust_assessments', ['status'])

    # 5. trust_transition_history
    op.create_table(
        'trust_transition_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('prior_trust_level', sa.String(length=50), nullable=False),
        sa.Column('new_trust_level', sa.String(length=50), nullable=False),
        sa.Column('actor_user_id', sa.String(length=36), nullable=True),
        sa.Column('actor_service', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evidence_references_json', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(length=50), nullable=False),
        sa.Column('related_verification_response_id', sa.String(length=36), nullable=True),
        sa.Column('rule_policy_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('outcome', sa.String(length=20), nullable=False, server_default='APPLIED'),
        sa.Column('is_downgrade', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_verification_response_id'], ['verification_responses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tth_instrument', 'trust_transition_history', ['instrument_id'])


def downgrade() -> None:
    op.drop_table('trust_transition_history')
    op.drop_table('trust_assessments')
    op.drop_table('verification_responses')
    op.drop_table('verification_requests')
    op.drop_table('field_provenances')
