"""create compliance_mappings table

Revision ID: 20260421_0015
Revises: 20260421_0014
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0015"
down_revision = "20260421_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("country_code", sa.String(length=20), nullable=True),
        sa.Column("standard_code", sa.String(length=100), nullable=True),
        sa.Column("module_code", sa.String(length=100), nullable=True),
        sa.Column("requirement_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("compliance_mappings")