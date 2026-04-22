"""fix audit_logs id identity

Revision ID: 20260420_0005
Revises: 20260420_0004
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa

revision = "20260420_0005"
down_revision = "20260420_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE relname = 'audit_logs_id_seq'
        ) THEN
            CREATE SEQUENCE audit_logs_id_seq;
        END IF;
    END$$;
    """)

    op.execute("""
    SELECT setval(
        'audit_logs_id_seq',
        COALESCE((SELECT MAX(id) FROM audit_logs), 0) + 1,
        false
    );
    """)

    op.execute("""
    ALTER TABLE audit_logs
    ALTER COLUMN id SET DEFAULT nextval('audit_logs_id_seq');
    """)

    op.execute("""
    ALTER SEQUENCE audit_logs_id_seq OWNED BY audit_logs.id;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE audit_logs
    ALTER COLUMN id DROP DEFAULT;
    """)

    op.execute("""
    DROP SEQUENCE IF EXISTS audit_logs_id_seq;
    """)