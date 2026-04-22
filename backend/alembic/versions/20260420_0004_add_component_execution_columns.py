"""add missing component execution columns

Revision ID: 20260420_0004
Revises: 20260417_0003
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa

revision = "20260420_0004"
down_revision = "20260417_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "components",
        sa.Column(
            "evidence_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "components",
        sa.Column(
            "blocked_for_execution",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("components", "blocked_for_execution")
    op.drop_column("components", "evidence_required")