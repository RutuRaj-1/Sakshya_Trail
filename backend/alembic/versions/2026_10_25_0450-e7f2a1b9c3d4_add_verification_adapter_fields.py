"""add verification adapter fields to requests and responses

Revision ID: e7f2a1b9c3d4
Revises: c5e8f1a3d9b4
Create Date: 2026-10-25 04:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f2a1b9c3d4'
down_revision: Union[str, None] = 'c5e8f1a3d9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update verification_requests with attempt, retry, error, closure and requested_fields columns
    with op.batch_alter_table('verification_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('requested_fields_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('correlation_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('error_details', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('closed_reason', sa.String(length=255), nullable=True))
        batch_op.create_index('ix_vr_correlation_id', ['correlation_id'])

    # 2. Update verification_responses with request_code, source_classification, comparisons, raw_metadata
    with op.batch_alter_table('verification_responses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('request_code', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('source_classification', sa.String(length=50), nullable=False, server_default='SIMULATION'))
        batch_op.add_column(sa.Column('source_identifier', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('field_comparisons_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        batch_op.add_column(sa.Column('evidence_references_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('recorded_by_service', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('raw_metadata_json', sa.Text(), nullable=True))
        batch_op.create_index('ix_vresp_request_code', ['request_code'])
        batch_op.create_index('ix_vresp_source_class', ['source_classification'])


def downgrade() -> None:
    with op.batch_alter_table('verification_responses', schema=None) as batch_op:
        batch_op.drop_index('ix_vresp_source_class')
        batch_op.drop_index('ix_vresp_request_code')
        batch_op.drop_column('raw_metadata_json')
        batch_op.drop_column('recorded_by_service')
        batch_op.drop_column('evidence_references_json')
        batch_op.drop_column('received_at')
        batch_op.drop_column('field_comparisons_json')
        batch_op.drop_column('source_identifier')
        batch_op.drop_column('source_classification')
        batch_op.drop_column('request_code')

    with op.batch_alter_table('verification_requests', schema=None) as batch_op:
        batch_op.drop_index('ix_vr_correlation_id')
        batch_op.drop_column('closed_reason')
        batch_op.drop_column('closed_at')
        batch_op.drop_column('error_details')
        batch_op.drop_column('next_retry_at')
        batch_op.drop_column('last_attempt_at')
        batch_op.drop_column('attempt_count')
        batch_op.drop_column('correlation_id')
        batch_op.drop_column('requested_fields_json')
