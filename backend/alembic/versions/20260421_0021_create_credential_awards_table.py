"""create credential awards table

Revision ID: 20260421_0021
Revises: 20260421_0020
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "20260421_0021"
down_revision = "20260421_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credential_awards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("professional_id", sa.Integer(), nullable=True),
        sa.Column("path_code", sa.String(length=100), nullable=True),
        sa.Column("credential_title", sa.String(length=255), nullable=True),
        sa.Column("awarded_by", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("advancement_recommended", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("credential_awards")