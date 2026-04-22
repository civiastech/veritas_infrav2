"""create atlas reports table

Revision ID: 20260421_0018
Revises: 20260421_0017
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0018"
down_revision = "20260421_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atlas_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("country_scope", sa.String(length=120), nullable=True),
        sa.Column("report_type", sa.String(length=120), nullable=True),
        sa.Column("period_label", sa.String(length=120), nullable=True),
        sa.Column("generated_by", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("atlas_reports")