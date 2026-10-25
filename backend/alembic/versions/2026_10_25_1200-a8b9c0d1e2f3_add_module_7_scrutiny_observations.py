"""add module 7 scrutiny observations model

Revision ID: a8b9c0d1e2f3
Revises: f6a7b8c9d0e1
Create Date: 2026-10-25 12:00:00.000000

Creates:
- scrutiny_observations: Append-only scrutiny observations, deficiency instructions,
  and non-destructive supersession chains for instruments and release cases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scrutiny_observations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('instrument_id', sa.String(36), sa.ForeignKey('instruments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('release_request_id', sa.String(36), sa.ForeignKey('release_requests.id', ondelete='CASCADE'), nullable=True),
        sa.Column('finding_id', sa.String(36), sa.ForeignKey('validation_findings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('supporting_document_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('supporting_version_number', sa.Integer(), nullable=True),
        sa.Column('observation_category', sa.String(50), nullable=False, server_default='GENERAL'),
        sa.Column('observation_text', sa.Text(), nullable=False),
        sa.Column('author_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('author_role', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='RECORDED'),
        sa.Column('resolution_reason', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('supersedes_id', sa.String(36), sa.ForeignKey('scrutiny_observations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('superseded_by_id', sa.String(36), sa.ForeignKey('scrutiny_observations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_internal_only', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index('ix_scrutiny_obs_instrument', 'scrutiny_observations', ['instrument_id'])
    op.create_index('ix_scrutiny_obs_release', 'scrutiny_observations', ['release_request_id'])
    op.create_index('ix_scrutiny_obs_finding', 'scrutiny_observations', ['finding_id'])
    op.create_index('ix_scrutiny_obs_author', 'scrutiny_observations', ['author_user_id'])
    op.create_index('ix_scrutiny_obs_supersedes', 'scrutiny_observations', ['supersedes_id'])
    op.create_index('ix_scrutiny_obs_superseded_by', 'scrutiny_observations', ['superseded_by_id'])
    op.create_index('ix_obs_inst_created', 'scrutiny_observations', ['instrument_id', 'created_at'])
    op.create_index('ix_obs_rel_created', 'scrutiny_observations', ['release_request_id', 'created_at'])
    op.create_index('ix_obs_status', 'scrutiny_observations', ['status'])


def downgrade() -> None:
    op.drop_table('scrutiny_observations')
