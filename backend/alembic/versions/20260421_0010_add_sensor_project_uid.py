"""add sensor project_uid

Revision ID: 20260421_0010
Revises: 20260421_0009
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0010"
down_revision = "20260421_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sensors",
        sa.Column("project_uid", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sensors", "project_uid")