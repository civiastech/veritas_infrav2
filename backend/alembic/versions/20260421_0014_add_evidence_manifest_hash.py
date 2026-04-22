"""add evidence manifest_hash

Revision ID: 20260421_0014
Revises: 20260421_0013
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0014"
down_revision = "20260421_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column("manifest_hash", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence", "manifest_hash")