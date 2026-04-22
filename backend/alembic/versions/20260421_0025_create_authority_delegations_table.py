"""create authority delegations table

Revision ID: 20260421_0025
Revises: 20260421_0024
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0025"
down_revision = "20260421_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authority_delegations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("authority_code", sa.String(length=100), nullable=True),
        sa.Column("delegate_professional_id", sa.Integer(), nullable=True),
        sa.Column("scope", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("valid_until", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("authority_delegations")