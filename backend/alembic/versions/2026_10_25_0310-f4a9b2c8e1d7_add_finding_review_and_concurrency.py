"""add finding review and concurrency

Revision ID: f4a9b2c8e1d7
Revises: dde1c7162b37
Create Date: 2026-10-25 03:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a9b2c8e1d7'
down_revision: Union[str, None] = 'dde1c7162b37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add review assignment, observation notes, and concurrency version columns
    with op.batch_alter_table('validation_findings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assigned_to_user_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('review_notes_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('concurrency_version', sa.Integer(), nullable=False, server_default='1'))
        batch_op.create_index('ix_vf_assigned_user', ['assigned_to_user_id'])
        batch_op.create_foreign_key(
            'fk_vf_assigned_user',
            'users',
            ['assigned_to_user_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('validation_findings', schema=None) as batch_op:
        batch_op.drop_constraint('fk_vf_assigned_user', type_='foreignkey')
        batch_op.drop_index('ix_vf_assigned_user')
        batch_op.drop_column('concurrency_version')
        batch_op.drop_column('review_notes_json')
        batch_op.drop_column('assigned_at')
        batch_op.drop_column('assigned_to_user_id')
