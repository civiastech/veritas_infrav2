"""add inspection method_id

Revision ID: 20260421_0009
Revises: 20260421_0008
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0009"
down_revision = "20260421_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inspections",
        sa.Column("method_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("inspections", "method_id")