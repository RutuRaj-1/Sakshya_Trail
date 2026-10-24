"""add_module_3_validation_engine

Revision ID: b3c5d7e9f1a2
Revises: a7b2c4d9e8f5
Create Date: 2026-10-25 01:00:00.000000

Module 3: Validation, Discrepancy & Explainable Intelligence
Creates three additive tables:
  - validation_policy_configs: Versioned, authorized policy configuration values
  - validation_runs:           Lightweight sweep execution log
  - validation_findings:       Persisted discrepancy / finding records (never deleted)

Design notes
------------
* All tables are additive; no existing Module 1/2 tables are modified.
* Foreign keys: institution → instruments → documents → document_versions (via SET NULL on delete)
* The finding fingerprint index is intentionally NOT unique globally (see model docstring).
* No unique constraint prevents legitimate repeated findings across rule versions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c5d7e9f1a2'
down_revision: Union[str, None] = 'a7b2c4d9e8f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. validation_policy_configs
    # -------------------------------------------------------------------------
    op.create_table(
        'validation_policy_configs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=True),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(length=20), nullable=False, server_default='string'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('policy_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('authorized_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('effective_from', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['institution_id'], ['institutions.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_vpc_institution_id', 'validation_policy_configs', ['institution_id'])
    op.create_index('ix_vpc_config_key', 'validation_policy_configs', ['config_key'])
    op.create_index('ix_vpc_is_active', 'validation_policy_configs', ['is_active'])
    op.create_index('ix_vpc_key_institution', 'validation_policy_configs', ['config_key', 'institution_id'])
    op.create_index('ix_vpc_active_key', 'validation_policy_configs', ['is_active', 'config_key'])

    # -------------------------------------------------------------------------
    # 2. validation_runs (must be before validation_findings for FK)
    # -------------------------------------------------------------------------
    op.create_table(
        'validation_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('triggered_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rules_evaluated_csv', sa.Text(), nullable=True),
        sa.Column('outcome_summary_json', sa.Text(), nullable=True),
        sa.Column('policy_version_ref', sa.String(length=100), nullable=True),
        sa.Column('new_findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('resolved_findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('run_status', sa.String(length=20), nullable=False, server_default='COMPLETED'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_vr_instrument_id', 'validation_runs', ['instrument_id'])
    op.create_index('ix_vr_run_at', 'validation_runs', ['run_at'])

    # -------------------------------------------------------------------------
    # 3. validation_findings
    # -------------------------------------------------------------------------
    op.create_table(
        'validation_findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('finding_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=True),
        sa.Column('document_version_id', sa.String(length=36), nullable=True),
        sa.Column('rule_id', sa.String(length=50), nullable=False),
        sa.Column('rule_version', sa.String(length=20), nullable=False),
        sa.Column('rule_type', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=60), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='OPEN'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('observed_value', sa.String(length=500), nullable=True),
        sa.Column('expected_value', sa.String(length=500), nullable=True),
        sa.Column('evidence_refs_json', sa.Text(), nullable=True),
        sa.Column('suggested_action', sa.String(length=500), nullable=True),
        sa.Column('policy_version_ref', sa.String(length=100), nullable=True),
        sa.Column('first_detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('superseded_by_finding_id', sa.String(length=36), nullable=True),
        sa.Column('validation_run_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(
            ['superseded_by_finding_id'], ['validation_findings.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['validation_run_id'], ['validation_runs.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    # Core lookup indexes
    op.create_index('ix_vf_finding_fingerprint', 'validation_findings', ['finding_fingerprint'])
    op.create_index('ix_vf_instrument_id', 'validation_findings', ['instrument_id'])
    op.create_index('ix_vf_institution_id', 'validation_findings', ['institution_id'])
    op.create_index('ix_vf_document_id', 'validation_findings', ['document_id'])
    op.create_index('ix_vf_document_version_id', 'validation_findings', ['document_version_id'])
    op.create_index('ix_vf_rule_id', 'validation_findings', ['rule_id'])
    op.create_index('ix_vf_rule_version', 'validation_findings', ['rule_version'])
    op.create_index('ix_vf_status', 'validation_findings', ['status'])
    op.create_index('ix_vf_severity', 'validation_findings', ['severity'])
    op.create_index('ix_vf_category', 'validation_findings', ['category'])
    op.create_index('ix_vf_validation_run_id', 'validation_findings', ['validation_run_id'])
    # Composite indexes for common query patterns
    op.create_index('ix_vf_instrument_status', 'validation_findings', ['instrument_id', 'status'])
    op.create_index('ix_vf_instrument_rule', 'validation_findings', ['instrument_id', 'rule_id'])
    op.create_index('ix_vf_severity_status', 'validation_findings', ['severity', 'status'])
    op.create_index('ix_vf_category_status', 'validation_findings', ['category', 'status'])
    op.create_index('ix_vf_first_detected', 'validation_findings', ['first_detected_at'])
    op.create_index('ix_vf_last_evaluated', 'validation_findings', ['last_evaluated_at'])


def downgrade() -> None:
    # Drop validation_findings first (has FK to validation_runs)
    op.drop_index('ix_vf_last_evaluated', table_name='validation_findings')
    op.drop_index('ix_vf_first_detected', table_name='validation_findings')
    op.drop_index('ix_vf_category_status', table_name='validation_findings')
    op.drop_index('ix_vf_severity_status', table_name='validation_findings')
    op.drop_index('ix_vf_instrument_rule', table_name='validation_findings')
    op.drop_index('ix_vf_instrument_status', table_name='validation_findings')
    op.drop_index('ix_vf_validation_run_id', table_name='validation_findings')
    op.drop_index('ix_vf_category', table_name='validation_findings')
    op.drop_index('ix_vf_severity', table_name='validation_findings')
    op.drop_index('ix_vf_status', table_name='validation_findings')
    op.drop_index('ix_vf_rule_version', table_name='validation_findings')
    op.drop_index('ix_vf_rule_id', table_name='validation_findings')
    op.drop_index('ix_vf_document_version_id', table_name='validation_findings')
    op.drop_index('ix_vf_document_id', table_name='validation_findings')
    op.drop_index('ix_vf_institution_id', table_name='validation_findings')
    op.drop_index('ix_vf_instrument_id', table_name='validation_findings')
    op.drop_index('ix_vf_finding_fingerprint', table_name='validation_findings')
    op.drop_table('validation_findings')

    op.drop_index('ix_vr_run_at', table_name='validation_runs')
    op.drop_index('ix_vr_instrument_id', table_name='validation_runs')
    op.drop_table('validation_runs')

    op.drop_index('ix_vpc_active_key', table_name='validation_policy_configs')
    op.drop_index('ix_vpc_key_institution', table_name='validation_policy_configs')
    op.drop_index('ix_vpc_is_active', table_name='validation_policy_configs')
    op.drop_index('ix_vpc_config_key', table_name='validation_policy_configs')
    op.drop_index('ix_vpc_institution_id', table_name='validation_policy_configs')
    op.drop_table('validation_policy_configs')
