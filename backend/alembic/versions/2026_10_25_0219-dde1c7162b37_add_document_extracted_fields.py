"""add_document_extracted_fields

Revision ID: dde1c7162b37
Revises: b3c5d7e9f1a2
Create Date: 2026-10-25 02:19:40.579385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dde1c7162b37'
down_revision: Union[str, None] = 'b3c5d7e9f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_extracted_fields',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_version_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('extraction_status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('confidence_overall', sa.Float(), nullable=True),
        sa.Column('extracted_by', sa.String(length=100), nullable=True),
        sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('doc_bank_name', sa.String(length=200), nullable=True),
        sa.Column('doc_bank_name_confidence', sa.Float(), nullable=True),
        sa.Column('doc_reference_number', sa.String(length=100), nullable=True),
        sa.Column('doc_reference_number_confidence', sa.Float(), nullable=True),
        sa.Column('doc_amount_str', sa.String(length=30), nullable=True),
        sa.Column('doc_amount_confidence', sa.Float(), nullable=True),
        sa.Column('doc_issue_date_str', sa.String(length=20), nullable=True),
        sa.Column('doc_issue_date_confidence', sa.Float(), nullable=True),
        sa.Column('doc_maturity_date_str', sa.String(length=20), nullable=True),
        sa.Column('doc_maturity_date_confidence', sa.Float(), nullable=True),
        sa.Column('doc_account_holder', sa.String(length=255), nullable=True),
        sa.Column('doc_account_holder_confidence', sa.Float(), nullable=True),
        sa.Column('doc_lien_holder', sa.String(length=255), nullable=True),
        sa.Column('doc_lien_holder_confidence', sa.Float(), nullable=True),
        sa.Column('extra_fields_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_version_id'),
    )
    op.create_index('ix_def_instrument_id', 'document_extracted_fields', ['instrument_id'])
    op.create_index('ix_def_institution_id', 'document_extracted_fields', ['institution_id'])
    op.create_index('ix_def_extraction_status', 'document_extracted_fields', ['extraction_status'])


def downgrade() -> None:
    op.drop_index('ix_def_extraction_status', table_name='document_extracted_fields')
    op.drop_index('ix_def_institution_id', table_name='document_extracted_fields')
    op.drop_index('ix_def_instrument_id', table_name='document_extracted_fields')
    op.drop_table('document_extracted_fields')

