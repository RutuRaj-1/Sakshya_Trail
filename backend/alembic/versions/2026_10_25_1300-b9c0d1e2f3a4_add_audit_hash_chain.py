"""add audit hash chain and append-only constraints

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-10-25 13:00:00.000000

Expands audit_events table with:
- sequence_number: Monotonic integer sequence counter for gap and reorder detection
- previous_hash: Cryptographic SHA-256 digest of preceding event (or GENESIS)
- current_hash: Cryptographic SHA-256 digest of canonicalized payload + previous_hash
- policy_version: Effective policy version at the time of action

Applies database-level triggers to enforce append-only immutability.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c0d1e2f3a4'
down_revision: Union[str, None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sequence_number', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('previous_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('current_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('policy_version', sa.String(length=50), nullable=True))
        batch_op.create_index(batch_op.f('ix_audit_events_sequence_number'), ['sequence_number'], unique=True)
        batch_op.create_index(batch_op.f('ix_audit_events_current_hash'), ['current_hash'], unique=False)

    # SQLite Trigger protection for append-only immutability
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == 'sqlite':
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(FAIL, 'Mutation of audit records is strictly prohibited: audit_events table is append-only');
            END;
        """)
        op.execute("""
            CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(FAIL, 'Deletion of audit records is strictly prohibited: audit_events table is append-only');
            END;
        """)
    elif dialect == 'postgresql':
        op.execute("""
            CREATE OR REPLACE FUNCTION prevent_audit_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'Mutation or deletion of audit records is strictly prohibited: audit_events table is append-only';
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_prevent_audit_update ON audit_events;
            CREATE TRIGGER trg_prevent_audit_update
            BEFORE UPDATE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();

            DROP TRIGGER IF EXISTS trg_prevent_audit_delete ON audit_events;
            CREATE TRIGGER trg_prevent_audit_delete
            BEFORE DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
        """)


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == 'sqlite':
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_update;")
        op.execute("DROP TRIGGER IF EXISTS prevent_audit_delete;")
    elif dialect == 'postgresql':
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_update ON audit_events;")
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_delete ON audit_events;")
        op.execute("DROP FUNCTION IF EXISTS prevent_audit_mutation();")

    with op.batch_alter_table('audit_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_events_current_hash'))
        batch_op.drop_index(batch_op.f('ix_audit_events_sequence_number'))
        batch_op.drop_column('policy_version')
        batch_op.drop_column('current_hash')
        batch_op.drop_column('previous_hash')
        batch_op.drop_column('sequence_number')
