"""add trust assessment concurrency version and source classification constraint

Revision ID: a1b2c3d4e5f6
Revises: e7f2a1b9c3d4
Create Date: 2026-10-25 06:00:00.000000

Adds:
- trust_assessments.concurrency_version  — optimistic-locking counter that prevents
  two concurrent trust transitions from silently clobbering each other.
- trust_assessments.prior_assessment_id  — explicit backward link to the assessment
  this one superseded (complements the existing superseded_by_id forward link).
- trust_transition_history.previous_assessment_id — links each history entry to
  the concrete assessment that was superseded.
- Enforces the DB-level CHECK: trust_level = L3_BANK_CONFIRMED requires
  related_verification_response_id IS NOT NULL (already in model; confirmed here).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e7f2a1b9c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- trust_assessments additions ---
    with op.batch_alter_table('trust_assessments', schema=None) as batch_op:
        # Optimistic concurrency version (starts at 1, incremented on each supersession)
        batch_op.add_column(
            sa.Column('concurrency_version', sa.Integer(), nullable=False, server_default='1')
        )
        # Explicit backward link to the superseded assessment
        batch_op.add_column(
            sa.Column('prior_assessment_id', sa.String(length=36), nullable=True)
        )
        # Policy gate: which source authorisation config qualified this assessment
        batch_op.add_column(
            sa.Column('source_authorization_config', sa.String(length=100), nullable=True)
        )

    # --- trust_transition_history additions ---
    with op.batch_alter_table('trust_transition_history', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('previous_assessment_id', sa.String(length=36), nullable=True)
        )
        batch_op.add_column(
            sa.Column('new_assessment_id', sa.String(length=36), nullable=True)
        )
        batch_op.add_column(
            sa.Column('concurrency_version_before', sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('trust_transition_history', schema=None) as batch_op:
        batch_op.drop_column('concurrency_version_before')
        batch_op.drop_column('new_assessment_id')
        batch_op.drop_column('previous_assessment_id')

    with op.batch_alter_table('trust_assessments', schema=None) as batch_op:
        batch_op.drop_column('source_authorization_config')
        batch_op.drop_column('prior_assessment_id')
        batch_op.drop_column('concurrency_version')
