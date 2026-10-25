"""add module 6 release and refund foundation models

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-25 11:00:00.000000

Creates:
- release_checklist_profiles: Versioned criteria profiles for release/discharge/refund.
- release_checklist_items: Discrete requirements with mandatory blocker flags.
- release_requests: Core administrative workflow cases.
- readiness_assessments: Historically reproducible assessment snapshots.
- readiness_check_results: Per-item evaluation outcomes and evidence references.
- release_review_observations: Scrutiny notes and deficiency instructions.
- release_decisions: Authorized maker-checker decisions and approval records.
- release_order_records: Administrative release letter tracking and bank action states.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. release_checklist_profiles
    op.create_table(
        'release_checklist_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('profile_code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('request_type', sa.String(30), nullable=False),
        sa.Column('case_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT'),
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('demo_disclaimer', sa.String(255), nullable=False, server_default='DEMO RELEASE POLICY — NOT OFFICIAL AICTE POLICY'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_by_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_by_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('audit_reference', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('profile_code', 'version', name='uq_release_profile_code_version'),
    )
    op.create_index('ix_release_checklist_profiles_profile_code', 'release_checklist_profiles', ['profile_code'])
    op.create_index('ix_release_profile_lookup', 'release_checklist_profiles', ['request_type', 'case_type', 'status'])

    # 2. release_checklist_items
    op.create_table(
        'release_checklist_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('profile_id', sa.String(36), sa.ForeignKey('release_checklist_profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_code', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('requirement_type', sa.String(50), nullable=False),
        sa.Column('is_mandatory_blocker', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('evaluation_type', sa.String(30), nullable=False, server_default='AUTOMATED'),
        sa.Column('expected_evidence_source', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('profile_id', 'item_code', name='uq_release_profile_item_code'),
    )
    op.create_index('ix_release_checklist_items_profile_id', 'release_checklist_items', ['profile_id'])
    op.create_index('ix_release_checklist_items_item_code', 'release_checklist_items', ['item_code'])

    # 3. release_requests
    op.create_table(
        'release_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_number', sa.String(50), nullable=False, unique=True),
        sa.Column('instrument_id', sa.String(36), sa.ForeignKey('instruments.id'), nullable=False),
        sa.Column('institution_id', sa.String(36), sa.ForeignKey('institutions.id'), nullable=False),
        sa.Column('request_type', sa.String(30), nullable=False),
        sa.Column('case_type', sa.String(50), nullable=False),
        sa.Column('policy_profile_id', sa.String(36), sa.ForeignKey('release_checklist_profiles.id'), nullable=True),
        sa.Column('policy_version', sa.Integer(), nullable=True),
        sa.Column('requester_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('request_reason', sa.Text(), nullable=False),
        sa.Column('workflow_status', sa.String(30), nullable=False, server_default='DRAFT'),
        sa.Column('assigned_reviewer_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('assigned_office', sa.String(100), nullable=True),
        sa.Column('latest_assessment_id', sa.String(36), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closure_notes', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_release_requests_case_number', 'release_requests', ['case_number'])
    op.create_index('ix_release_requests_instrument_id', 'release_requests', ['instrument_id'])
    op.create_index('ix_release_requests_institution_id', 'release_requests', ['institution_id'])
    op.create_index('ix_release_requests_workflow_status', 'release_requests', ['workflow_status'])
    op.create_index('ix_release_req_inst_status', 'release_requests', ['institution_id', 'workflow_status'])
    op.create_index('ix_release_req_instrument', 'release_requests', ['instrument_id', 'workflow_status'])

    # 4. readiness_assessments
    op.create_table(
        'readiness_assessments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('release_request_id', sa.String(36), sa.ForeignKey('release_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('profile_id', sa.String(36), sa.ForeignKey('release_checklist_profiles.id'), nullable=False),
        sa.Column('profile_version', sa.Integer(), nullable=False),
        sa.Column('assessment_outcome', sa.String(30), nullable=False, server_default='INCOMPLETE'),
        sa.Column('total_items_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('satisfied_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('blockers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pending_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('advisory_flags_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('summary_notes', sa.Text(), nullable=True),
        sa.Column('evaluated_by_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_readiness_assessments_release_request_id', 'readiness_assessments', ['release_request_id'])

    # 5. readiness_check_results
    op.create_table(
        'readiness_check_results',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('assessment_id', sa.String(36), sa.ForeignKey('readiness_assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('checklist_item_id', sa.String(36), sa.ForeignKey('release_checklist_items.id'), nullable=True),
        sa.Column('item_code', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('is_mandatory_blocker', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('evidence_references_json', sa.Text(), nullable=True),
        sa.Column('source_module', sa.String(50), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_readiness_check_results_assessment_id', 'readiness_check_results', ['assessment_id'])

    # 6. release_review_observations
    op.create_table(
        'release_review_observations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('release_request_id', sa.String(36), sa.ForeignKey('release_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('officer_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('observation_type', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('is_blocking', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_release_review_observations_release_request_id', 'release_review_observations', ['release_request_id'])

    # 7. release_decisions
    op.create_table(
        'release_decisions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('release_request_id', sa.String(36), sa.ForeignKey('release_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('actor_role', sa.String(50), nullable=False),
        sa.Column('decision_type', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('policy_version', sa.Integer(), nullable=True),
        sa.Column('readiness_assessment_id', sa.String(36), sa.ForeignKey('readiness_assessments.id'), nullable=True),
        sa.Column('evidence_references_json', sa.Text(), nullable=True),
        sa.Column('previous_status', sa.String(30), nullable=False),
        sa.Column('new_status', sa.String(30), nullable=False),
        sa.Column('audit_event_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_release_decisions_release_request_id', 'release_decisions', ['release_request_id'])

    # 8. release_order_records
    op.create_table(
        'release_order_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('release_request_id', sa.String(36), sa.ForeignKey('release_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_reference_number', sa.String(100), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('responsible_officer_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('supporting_document_id', sa.String(36), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='DRAFT_RECORDED'),
        sa.Column('bank_action_status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('bank_action_notes', sa.Text(), nullable=True),
        sa.Column('bank_action_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_synthetic_demo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_release_order_records_release_request_id', 'release_order_records', ['release_request_id'])
    op.create_index('ix_release_order_records_order_ref', 'release_order_records', ['order_reference_number'])


def downgrade() -> None:
    op.drop_table('release_order_records')
    op.drop_table('release_decisions')
    op.drop_table('release_review_observations')
    op.drop_table('readiness_check_results')
    op.drop_table('readiness_assessments')
    op.drop_table('release_requests')
    op.drop_table('release_checklist_items')
    op.drop_table('release_checklist_profiles')
