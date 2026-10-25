"""add lifecycle_job_runs table and evaluation date uniqueness

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-25 08:00:00.000000

Adds:
- lifecycle_job_runs: Execution logs, summaries, and lease locks for scheduler and on-demand runs.
- uq_eval_instrument_date: Unique constraint on (instrument_id, evaluation_date) for idempotent evaluations.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. lifecycle_job_runs table
    op.create_table(
        'lifecycle_job_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_type', sa.String(length=50), nullable=False, server_default='DAILY_MATURITY_SCAN'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='RUNNING'),
        sa.Column('trigger_source', sa.String(length=50), nullable=False, server_default='SCHEDULED'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evaluation_date', sa.Date(), nullable=False),
        sa.Column('evaluation_timezone', sa.String(length=50), nullable=False, server_default='Asia/Kolkata'),
        sa.Column('total_eligible', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('evaluated_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('material_transitions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('approaching_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('matured_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overdue_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('worker_instance_id', sa.String(length=100), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_summary_json', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('lifecycle_job_runs', schema=None) as batch_op:
        batch_op.create_index('ix_lifecycle_job_runs_status', ['status'], unique=False)
        batch_op.create_index('ix_job_status_started', ['status', 'started_at'], unique=False)
        batch_op.create_index('ix_job_type_date', ['job_type', 'evaluation_date'], unique=False)

    # 2. Add unique constraint on lifecycle_evaluations (instrument_id, evaluation_date)
    with op.batch_alter_table('lifecycle_evaluations', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_eval_instrument_date', ['instrument_id', 'evaluation_date'])


def downgrade() -> None:
    with op.batch_alter_table('lifecycle_evaluations', schema=None) as batch_op:
        batch_op.drop_constraint('uq_eval_instrument_date', type_='unique')
    op.drop_table('lifecycle_job_runs')
