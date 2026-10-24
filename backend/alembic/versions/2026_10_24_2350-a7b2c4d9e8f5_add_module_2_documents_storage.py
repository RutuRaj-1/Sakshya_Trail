"""add_module_2_documents_storage

Revision ID: a7b2c4d9e8f5
Revises: 058efcf1e144
Create Date: 2026-10-24 23:50:00.000000

Module 2: Document Intake & Evidence Intelligence
- document_categories: Configurable document category catalog
- documents: Logical document entities
- document_versions: Immutable document version records with storage abstraction
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b2c4d9e8f5'
down_revision: Union[str, None] = '058efcf1e144'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_categories table
    op.create_table(
        'document_categories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_document_categories_code', 'document_categories', ['code'], unique=True)
    op.create_index('ix_document_categories_is_active', 'document_categories', ['is_active'])

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column('current_version_id', sa.String(length=36), nullable=True),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_reason', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_documents_institution_id', 'documents', ['institution_id'])
    op.create_index('ix_documents_instrument_id', 'documents', ['instrument_id'])
    op.create_index('ix_documents_category', 'documents', ['category'])
    op.create_index('ix_documents_status', 'documents', ['status'])

    # Create document_versions table
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('uploader_user_id', sa.String(length=36), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default="PENDING_SCAN"),
        sa.Column('scan_provider', sa.String(length=100), nullable=True),
        sa.Column('scan_result_json', sa.Text(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('parent_version_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'])
    op.create_index('ix_document_versions_storage_key', 'document_versions', ['storage_key'], unique=True)
    op.create_index('ix_document_versions_sha256_hash', 'document_versions', ['sha256_hash'])
    op.create_index('ix_document_versions_processing_status', 'document_versions', ['processing_status'])

    # Add foreign key for current_version_id in documents (after document_versions table exists)
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_documents_current_version_id',
            'document_versions',
            ['current_version_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    # Drop foreign key constraint for current_version_id
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_constraint('fk_documents_current_version_id', type_='foreignkey')

    # Drop indexes and tables
    op.drop_index('ix_document_versions_processing_status', table_name='document_versions')
    op.drop_index('ix_document_versions_sha256_hash', table_name='document_versions')
    op.drop_index('ix_document_versions_storage_key', table_name='document_versions')
    op.drop_index('ix_document_versions_document_id', table_name='document_versions')
    op.drop_table('document_versions')

    op.drop_index('ix_documents_status', table_name='documents')
    op.drop_index('ix_documents_category', table_name='documents')
    op.drop_index('ix_documents_instrument_id', table_name='documents')
    op.drop_index('ix_documents_institution_id', table_name='documents')
    op.drop_table('documents')

    op.drop_index('ix_document_categories_is_active', table_name='document_categories')
    op.drop_index('ix_document_categories_code', table_name='document_categories')
    op.drop_table('document_categories')
