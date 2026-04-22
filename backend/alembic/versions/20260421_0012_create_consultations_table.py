"""create consultations table

Revision ID: 20260421_0012
Revises: 20260421_0011
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0012"
down_revision = "20260421_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consultations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consultation_uid", sa.String(length=100), nullable=True),
        sa.Column("country_code", sa.String(length=20), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("consultation_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("opened_at_label", sa.String(length=100), nullable=True),
        sa.Column("closed_at_label", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("consultations")