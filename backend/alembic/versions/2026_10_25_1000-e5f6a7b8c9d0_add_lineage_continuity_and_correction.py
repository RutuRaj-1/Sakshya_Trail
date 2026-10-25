"""add lineage continuity details, correction history, and instrument effective_date

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-25 10:00:00.000000

Adds:
- instrument_lineages.continuity_details_json: Full audit trail of gap/overlap comparison, date fields, policy semantics, and findings.
- instrument_lineages.correction_history_json: Authorized link correction audit log.
- instruments.effective_date: Optional explicit statutory validity start date.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update instrument_lineages with continuity details and correction log
    with op.batch_alter_table('instrument_lineages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('continuity_details_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('correction_history_json', sa.Text(), nullable=True))

    # 2. Update instruments with optional effective_date
    with op.batch_alter_table('instruments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('effective_date', sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('instruments', schema=None) as batch_op:
        batch_op.drop_column('effective_date')

    with op.batch_alter_table('instrument_lineages', schema=None) as batch_op:
        batch_op.drop_column('correction_history_json')
        batch_op.drop_column('continuity_details_json')
