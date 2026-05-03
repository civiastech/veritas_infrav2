"""
Alembic Migration — PREFAB™ Module
Creates: component_specs, deviation_records, prefab_library_entries

Revision: 0026_prefab_module
Down: drops the three tables cleanly.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0026_prefab_module"
down_revision = "20260421_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── prefab_library_entries ────────────────────────────────────────────────
    op.create_table(
        "prefab_library_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("component_type", sa.String(20), nullable=False),
        sa.Column("specification_code", sa.String(500), nullable=True),
        sa.Column("concrete_grade", sa.String(50), nullable=True),
        sa.Column("cover_nominal_mm", sa.Integer, nullable=True),
        sa.Column("design_standard", sa.String(50), nullable=True),
        sa.Column("rebar_spec", postgresql.JSON, nullable=True),
        sa.Column("execution_sensitivity", sa.String(20),
                  server_default="MEDIUM", nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("usage_count", sa.Integer,
                  server_default="0", nullable=False),
    )
    op.create_index(
        "ix_library_entries_type",
        "prefab_library_entries",
        ["component_type", "active"],
    )

    # ── component_specs ───────────────────────────────────────────────────────
    op.create_table(
        "component_specs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # Identity
        sa.Column("component_uid", sa.String(180),
                  unique=True, index=True, nullable=False),
        sa.Column("project_uid", sa.String(100), index=True, nullable=False),
        sa.Column("level_code", sa.String(20), nullable=True),
        sa.Column("grid_reference", sa.String(20), nullable=True),
        sa.Column("component_type", sa.String(20), nullable=True),
        sa.Column("sequence_number", sa.String(10), nullable=True),

        # Structural specification
        sa.Column("specification_code", sa.String(500), nullable=True),
        sa.Column("concrete_grade", sa.String(50), nullable=True),
        sa.Column("concrete_fck_mpa", sa.Float, nullable=True),
        sa.Column("water_cement_ratio_max", sa.Float, nullable=True),
        sa.Column("cover_nominal_mm", sa.Integer, nullable=True),
        sa.Column("cover_minimum_mm", sa.Integer, nullable=True),
        sa.Column("exposure_class", sa.String(50), nullable=True),
        sa.Column("design_standard", sa.String(50), nullable=True),
        sa.Column("design_life_years", sa.Integer, nullable=True),
        sa.Column("rebar_spec", postgresql.JSON, nullable=True),
        sa.Column("section_width_mm", sa.Integer, nullable=True),
        sa.Column("section_depth_mm", sa.Integer, nullable=True),
        sa.Column("element_length_mm", sa.Integer, nullable=True),

        # Load path
        sa.Column("load_path_description", sa.Text, nullable=True),
        sa.Column("connects_to_uids", postgresql.JSON, nullable=True),
        sa.Column("supported_by_uid", sa.String(180), nullable=True),

        # Execution
        sa.Column("execution_sensitivity", sa.String(20),
                  server_default="MEDIUM", nullable=False),
        sa.Column("sensitivity_reason", sa.Text, nullable=True),
        sa.Column("substitute_allowed", sa.Boolean,
                  server_default="false", nullable=False),
        sa.Column("substitute_requires_band", sa.String(20),
                  server_default="TRUSTED", nullable=False),

        # Approval
        sa.Column("approved_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_notes", sa.Text, nullable=True),
        sa.Column("is_approved", sa.Boolean,
                  server_default="false", nullable=False),

        # Deviation log closure (SEAL Gate 9)
        sa.Column("deviation_log_closed", sa.Boolean,
                  server_default="false", nullable=False),
        sa.Column("deviation_log_closed_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("deviation_log_closed_at",
                  sa.DateTime(timezone=True), nullable=True),
        sa.Column("deviation_log_notes", sa.Text, nullable=True),
        sa.Column("has_open_deviations", sa.Boolean,
                  server_default="false", nullable=False),
        sa.Column("deviation_count", sa.Integer,
                  server_default="0", nullable=False),

        # Library reference
        sa.Column("library_entry_id", sa.Integer,
                  sa.ForeignKey("prefab_library_entries.id"), nullable=True),
    )
    op.create_index(
        "ix_component_specs_project_type",
        "component_specs", ["project_uid", "component_type"],
    )
    op.create_index(
        "ix_component_specs_sensitivity",
        "component_specs", ["execution_sensitivity"],
    )
    op.create_index(
        "ix_component_specs_deviation_open",
        "component_specs", ["has_open_deviations"],
    )

    # ── deviation_records ─────────────────────────────────────────────────────
    op.create_table(
        "deviation_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        # Identification
        sa.Column("component_uid", sa.String(180), index=True, nullable=False),
        sa.Column("project_uid", sa.String(100), index=True, nullable=False),
        sa.Column("component_spec_id", sa.Integer,
                  sa.ForeignKey("component_specs.id"), nullable=True),

        # Deviation details
        sa.Column("deviation_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("measurement_data", postgresql.JSON, nullable=True),

        # Discovery
        sa.Column("discovered_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),

        # Before/After photos (CAPTURE-LARGE Element 4)
        sa.Column("before_photo_url", sa.String(500), nullable=True),
        sa.Column("before_photo_sha256", sa.String(64), nullable=True),
        sa.Column("after_photo_url", sa.String(500), nullable=True),
        sa.Column("after_photo_sha256", sa.String(64), nullable=True),
        sa.Column("photos_verified", sa.Boolean,
                  server_default="false", nullable=False),

        # Correction
        sa.Column("corrected", sa.Boolean,
                  server_default="false", nullable=False),
        sa.Column("correction_description", sa.Text, nullable=True),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),

        # Engineer review
        sa.Column("engineer_review_required", sa.Boolean,
                  server_default="false", nullable=False),
        sa.Column("reviewed_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_decision", sa.String(30), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),

        # Closure
        sa.Column("closed", sa.Boolean,
                  server_default="false", nullable=False),
        sa.Column("closed_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),

        # Auto-triggers
        sa.Column("ethics_violation_triggered", sa.Boolean,
                  server_default="false", nullable=False),
        sa.Column("ethics_violation_tier", sa.Integer, nullable=True),
        sa.Column("ethics_violation_id", sa.Integer, nullable=True),
        sa.Column("pay_hold_triggered", sa.Boolean,
                  server_default="false", nullable=False),
        sa.Column("twin_event_id", sa.Integer, nullable=True),
    )
    op.create_index(
        "ix_deviation_records_closed",
        "deviation_records", ["closed"],
    )
    op.create_index(
        "ix_deviation_records_severity",
        "deviation_records", ["severity"],
    )
    op.create_index(
        "ix_deviation_records_project",
        "deviation_records", ["project_uid", "closed"],
    )


def downgrade() -> None:
    op.drop_table("deviation_records")
    op.drop_table("component_specs")
    op.drop_table("prefab_library_entries")
