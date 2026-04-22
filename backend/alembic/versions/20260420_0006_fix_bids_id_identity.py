"""fix bids id identity

Revision ID: 20260420_0006
Revises: 20260420_0005
Create Date: 2026-04-20
"""
from alembic import op

revision = "20260420_0006"
down_revision = "20260420_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE relname = 'bids_id_seq'
        ) THEN
            CREATE SEQUENCE bids_id_seq;
        END IF;
    END$$;
    """)

    op.execute("""
    SELECT setval(
        'bids_id_seq',
        COALESCE((SELECT MAX(id) FROM bids), 0) + 1,
        false
    );
    """)

    op.execute("""
    ALTER TABLE bids
    ALTER COLUMN id SET DEFAULT nextval('bids_id_seq');
    """)

    op.execute("""
    ALTER SEQUENCE bids_id_seq OWNED BY bids.id;
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE bids
    ALTER COLUMN id DROP DEFAULT;
    """)

    op.execute("""
    DROP SEQUENCE IF EXISTS bids_id_seq;
    """)