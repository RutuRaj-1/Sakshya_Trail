"""add lifecycle_notifications, delivery attempts, and policy channels

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-25 09:00:00.000000

Adds:
- lifecycle_notifications: Time-sensitive reminder, due-date, and escalation notification history.
- notification_delivery_attempts: Granular attempt log for channel delivery, retries, and failure diagnostics.
- lifecycle_policies updates: Permitted channels, retry limits, and template settings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update lifecycle_policies with notification channels and retry settings
    with op.batch_alter_table('lifecycle_policies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('permitted_channels_json', sa.Text(), nullable=False, server_default='["IN_APP", "EMAIL"]'))
        batch_op.add_column(sa.Column('max_retry_limit', sa.Integer(), nullable=False, server_default='3'))
        batch_op.add_column(sa.Column('retry_interval_minutes', sa.Integer(), nullable=False, server_default='60'))
        batch_op.add_column(sa.Column('template_id', sa.String(length=100), nullable=False, server_default='DEFAULT_REGULATORY_REMINDER'))
        batch_op.add_column(sa.Column('template_version', sa.Integer(), nullable=False, server_default='1'))

    # 2. Create lifecycle_notifications table
    op.create_table(
        'lifecycle_notifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('instrument_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('policy_id', sa.String(length=36), nullable=True),
        sa.Column('policy_version', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('reminder_milestone_days', sa.Integer(), nullable=True),
        sa.Column('trigger_date', sa.Date(), nullable=False),
        sa.Column('recipient_user_id', sa.String(length=36), nullable=True),
        sa.Column('recipient_role', sa.String(length=50), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=True),
        sa.Column('recipient_name', sa.String(length=255), nullable=True),
        sa.Column('channel', sa.String(length=50), nullable=False, server_default='IN_APP'),
        sa.Column('template_id', sa.String(length=100), nullable=False, server_default='DEFAULT_REGULATORY_REMINDER'),
        sa.Column('template_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('payload_metadata_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='CREATED'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('first_attempted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_attempted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('failure_category', sa.String(length=50), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('is_mock', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('mock_disclaimer', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['policy_id'], ['lifecycle_policies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_lifecycle_notification_idempotency')
    )
    with op.batch_alter_table('lifecycle_notifications', schema=None) as batch_op:
        batch_op.create_index('ix_notif_instrument', ['instrument_id'], unique=False)
        batch_op.create_index('ix_notif_institution', ['institution_id'], unique=False)
        batch_op.create_index('ix_notif_recipient_user', ['recipient_user_id'], unique=False)
        batch_op.create_index('ix_notif_status', ['status'], unique=False)
        batch_op.create_index('ix_notif_event_date', ['event_type', 'trigger_date'], unique=False)

    # 3. Create notification_delivery_attempts table
    op.create_table(
        'notification_delivery_attempts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('notification_id', sa.String(length=36), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('provider_response_code', sa.String(length=100), nullable=True),
        sa.Column('provider_reference_id', sa.String(length=255), nullable=True),
        sa.Column('error_category', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['notification_id'], ['lifecycle_notifications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notification_delivery_attempts', schema=None) as batch_op:
        batch_op.create_index('ix_attempt_notification', ['notification_id'], unique=False)
        batch_op.create_index('ix_attempt_status', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('notification_delivery_attempts')
    op.drop_table('lifecycle_notifications')
    with op.batch_alter_table('lifecycle_policies', schema=None) as batch_op:
        batch_op.drop_column('template_version')
        batch_op.drop_column('template_id')
        batch_op.drop_column('retry_interval_minutes')
        batch_op.drop_column('max_retry_limit')
        batch_op.drop_column('permitted_channels_json')
