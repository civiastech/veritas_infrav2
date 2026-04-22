"""create cst members table

Revision ID: 20260421_0022
Revises: 20260421_0021
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0022"
down_revision = "20260421_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cst_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("professional_id", sa.Integer(), nullable=True),
        sa.Column("appointment_title", sa.String(length=255), nullable=True),
        sa.Column("voting_rights", sa.Boolean(), nullable=True),
        sa.Column("term_start", sa.String(length=100), nullable=True),
        sa.Column("term_end", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("cst_members")