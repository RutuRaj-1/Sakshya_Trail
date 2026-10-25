"""add Module 5 lifecycle policies, renewal lineage, and lifecycle evaluations

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-25 07:00:00.000000

Adds:
- lifecycle_policies: Versioned configuration for reminder intervals, lead times, and tolerances.
- instrument_lineages: Predecessor-to-successor graph edges with anti-self-reference and institution safety.
- lifecycle_evaluations: Audit-safe time-sensitive evaluations, days-to-maturity, and due conditions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. lifecycle_policies table
    op.create_table(
        'lifecycle_policies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('policy_code', sa.String(length=50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('label', sa.String(length=255), nullable=False, server_default='DEMO POLICY — NOT OFFICIAL AICTE POLICY'),
        sa.Column('scope_instrument_type', sa.String(length=50), nullable=True),
        sa.Column('scope_institution_type', sa.String(length=100), nullable=True),
        sa.Column('scope_assigned_office', sa.String(length=100), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Asia/Kolkata'),
        sa.Column('reminder_intervals_days_json', sa.Text(), nullable=False, server_default='[90, 60, 30, 15, 7]'),
        sa.Column('recipient_roles_by_interval_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('institution_action_lead_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('officer_action_lead_days', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('escalation_interval_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('escalation_target_role', sa.String(length=50), nullable=False, server_default='BRANCH_HEAD'),
        sa.Column('maturity_critical_lead_days', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('renewal_comparison_method', sa.String(length=50), nullable=False, server_default='ISSUE_DATE_TO_MATURITY_DATE'),
        sa.Column('max_allowed_gap_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_allowed_overlap_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('approved_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_code', 'version', name='uq_policy_code_version')
    )
    with op.batch_alter_table('lifecycle_policies', schema=None) as batch_op:
        batch_op.create_index('ix_lifecycle_policies_policy_code', ['policy_code'], unique=False)
        batch_op.create_index('ix_lifecycle_policies_status', ['status'], unique=False)
        batch_op.create_index('ix_policy_code_status', ['policy_code', 'status'], unique=False)

    # 2. instrument_lineages table
    op.create_table(
        'instrument_lineages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('predecessor_instrument_id', sa.String(length=36), nullable=False),
        sa.Column('successor_instrument_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False, server_default='RENEWAL'),
        sa.Column('relationship_status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('reason_or_reference', sa.String(length=500), nullable=True),
        sa.Column('policy_id', sa.String(length=36), nullable=True),
        sa.Column('policy_version', sa.Integer(), nullable=True),
        sa.Column('validity_gap_days', sa.Integer(), nullable=True),
        sa.Column('validity_overlap_days', sa.Integer(), nullable=True),
        sa.Column('continuity_indicator', sa.String(length=50), nullable=False, server_default='CONTINUOUS'),
        sa.Column('concurrency_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['policy_id'], ['lifecycle_policies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['predecessor_instrument_id'], ['instruments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['successor_instrument_id'], ['instruments.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('predecessor_instrument_id != successor_instrument_id', name='ck_lineage_no_self_reference')
    )
    with op.batch_alter_table('instrument_lineages', schema=None) as batch_op:
        batch_op.create_index('ix_instrument_lineages_predecessor_instrument_id', ['predecessor_instrument_id'], unique=False)
        batch_op.create_index('ix_instrument_lineages_successor_instrument_id', ['successor_instrument_id'], unique=False)
        batch_op.create_index('ix_instrument_lineages_institution_id', ['institution_id'], unique=False)
        batch_op.create_index('ix_lineage_predecessor_status', ['predecessor_instrument_id', 'relationship_status'], unique=False)
        batch_op.create_index('ix_lineage_successor_status', ['successor_instrument_id', 'relationship_status'], unique=False)

    # 3. lifecycle_evaluations table
    op.create_table(
        'lifecycle_evaluations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('policy_id', sa.String(length=36), nullable=True),
        sa.Column('policy_version', sa.Integer(), nullable=True),
        sa.Column('evaluation_date', sa.Date(), nullable=False),
        sa.Column('evaluation_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluation_timezone', sa.String(length=50), nullable=False, server_default='Asia/Kolkata'),
        sa.Column('days_to_maturity', sa.Integer(), nullable=True),
        sa.Column('maturity_stage', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('institution_action_due_date', sa.Date(), nullable=True),
        sa.Column('officer_action_due_date', sa.Date(), nullable=True),
        sa.Column('is_overdue', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_escalated', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('escalation_role', sa.String(length=50), nullable=True),
        sa.Column('due_condition', sa.String(length=50), nullable=False, server_default='NORMAL'),
        sa.Column('matched_reminder_interval_days', sa.Integer(), nullable=True),
        sa.Column('lineage_relationship_id', sa.String(length=36), nullable=True),
        sa.Column('is_material_transition', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('prior_evaluation_id', sa.String(length=36), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lineage_relationship_id'], ['instrument_lineages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['policy_id'], ['lifecycle_policies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['prior_evaluation_id'], ['lifecycle_evaluations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('lifecycle_evaluations', schema=None) as batch_op:
        batch_op.create_index('ix_lifecycle_evaluations_instrument_id', ['instrument_id'], unique=False)
        batch_op.create_index('ix_lifecycle_evaluations_evaluation_date', ['evaluation_date'], unique=False)
        batch_op.create_index('ix_eval_instrument_date', ['instrument_id', 'evaluation_date'], unique=False)
        batch_op.create_index('ix_eval_maturity_stage', ['maturity_stage'], unique=False)
        batch_op.create_index('ix_eval_due_condition', ['due_condition'], unique=False)
        batch_op.create_index('ix_lifecycle_evaluations_is_overdue', ['is_overdue'], unique=False)
        batch_op.create_index('ix_lifecycle_evaluations_is_escalated', ['is_escalated'], unique=False)


def downgrade() -> None:
    op.drop_table('lifecycle_evaluations')
    op.drop_table('instrument_lineages')
    op.drop_table('lifecycle_policies')
