"""
Alembic Migration 0029 — Missing Tables

Creates tables that exist in models but had no migration:
  - underwriting_applications
  - risk_decisions
  - country_tenants
  - launch_programs
  - revenue_share_rules
  - governance_votes
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0029_missing_tables"
down_revision = "0028_ethics_origin_matrix"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "underwriting_applications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_uid", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("project_uid", sa.String(100), index=True, nullable=False),
        sa.Column("product_code", sa.String(80), index=True, nullable=False),
        sa.Column("applicant_name", sa.String(255), nullable=False),
        sa.Column("requested_amount", sa.Float, server_default="0", nullable=False),
        sa.Column("currency", sa.String(10), server_default="USD", nullable=False),
        sa.Column("status", sa.String(50), server_default="submitted", nullable=False),
        sa.Column("submitted_by", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
    )

    op.create_table(
        "risk_decisions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("application_id", sa.Integer,
                  sa.ForeignKey("underwriting_applications.id"),
                  nullable=False, index=True),
        sa.Column("risk_score", sa.Float, server_default="0", nullable=False),
        sa.Column("decision", sa.String(50), server_default="review", nullable=False),
        sa.Column("premium_adjustment_bps", sa.Float, server_default="0", nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("feature_snapshot", postgresql.JSON, nullable=False),
    )

    op.create_table(
        "country_tenants",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("country_code", sa.String(8), nullable=False, index=True),
        sa.Column("operator_name", sa.String(255), nullable=False),
        sa.Column("license_type", sa.String(80), server_default="country_franchise",
                  nullable=False),
        sa.Column("revenue_share_pct", sa.Float, server_default="0", nullable=False),
        sa.Column("launch_status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("start_date", sa.String(30), nullable=True),
        sa.Column("end_date", sa.String(30), nullable=True),
    )

    op.create_table(
        "launch_programs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("country_code", sa.String(8), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("phase", sa.String(80), server_default="readiness", nullable=False),
        sa.Column("progress", sa.Float, server_default="0", nullable=False),
        sa.Column("owner_professional_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )

    op.create_table(
        "revenue_share_rules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("country_code", sa.String(8), nullable=False, index=True),
        sa.Column("module_code", sa.String(80), nullable=False),
        sa.Column("local_operator_pct", sa.Float, server_default="0", nullable=False),
        sa.Column("central_platform_pct", sa.Float, server_default="0", nullable=False),
        sa.Column("government_program_pct", sa.Float, server_default="0", nullable=False),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
    )

    op.create_table(
        "governance_votes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("resolution_uid", sa.String(100), nullable=False, index=True),
        sa.Column("member_professional_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=False, index=True),
        sa.Column("vote", sa.String(20), server_default="yes", nullable=False),
        sa.Column("rationale", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("governance_votes")
    op.drop_table("revenue_share_rules")
    op.drop_table("launch_programs")
    op.drop_table("country_tenants")
    op.drop_table("risk_decisions")
    op.drop_table("underwriting_applications")
