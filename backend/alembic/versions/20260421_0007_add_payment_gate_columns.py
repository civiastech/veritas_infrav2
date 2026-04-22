"""add payment gate columns

Revision ID: 20260421_0007
Revises: 20260420_0006
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0007"
down_revision = "20260420_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("gate_decision", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("gate_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "gate_reason")
    op.drop_column("payments", "gate_decision")