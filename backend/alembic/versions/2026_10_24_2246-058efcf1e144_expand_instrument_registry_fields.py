"""expand_instrument_registry_fields

Revision ID: 058efcf1e144
Revises: 1a1cd8595579
Create Date: 2026-10-24 22:46:12.550938

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '058efcf1e144'
down_revision: Union[str, None] = '1a1cd8595579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('instruments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('instrument_type', sa.String(length=50), nullable=False, server_default="FDR"))
        batch_op.add_column(sa.Column('lien_holder', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('lien_details', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('assigned_office', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('trust_level', sa.String(length=50), nullable=False, server_default="L0_DECLARED"))
        batch_op.add_column(sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column('created_by_user_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('updated_by_user_id', sa.String(length=36), nullable=True))
        batch_op.alter_column('amount',
               existing_type=sa.NUMERIC(precision=14, scale=2),
               type_=sa.Numeric(precision=18, scale=2),
               existing_nullable=False)
        batch_op.drop_index('ix_instruments_reference_number')
        batch_op.create_index('ix_instruments_reference_number', ['reference_number'], unique=False)
        batch_op.create_index('ix_instruments_trust_level', ['trust_level'], unique=False)
        batch_op.drop_column('verification_level')


def downgrade() -> None:
    with op.batch_alter_table('instruments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('verification_level', sa.VARCHAR(length=50), nullable=False, server_default="L1_DECLARED"))
        batch_op.drop_index('ix_instruments_trust_level')
        batch_op.drop_index('ix_instruments_reference_number')
        batch_op.create_index('ix_instruments_reference_number', ['reference_number'], unique=True)
        batch_op.alter_column('amount',
               existing_type=sa.Numeric(precision=18, scale=2),
               type_=sa.NUMERIC(precision=14, scale=2),
               existing_nullable=False)
        batch_op.drop_column('updated_by_user_id')
        batch_op.drop_column('created_by_user_id')
        batch_op.drop_column('is_synthetic')
        batch_op.drop_column('trust_level')
        batch_op.drop_column('assigned_office')
        batch_op.drop_column('lien_details')
        batch_op.drop_column('lien_holder')
        batch_op.drop_column('instrument_type')
