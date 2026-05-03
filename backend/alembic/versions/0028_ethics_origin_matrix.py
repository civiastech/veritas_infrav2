"""
Alembic Migration 0028 — ETHICS™ + ORIGIN™ Tables + MATRIX-C Bid Columns

Creates:
  - ethics_violations
  - ethics_whistleblower_reports
  - ethics_probation_records
  - origin_suppliers
  - origin_material_batches
  - origin_supply_chain_records
  - origin_test_records

Adds to 'bids' table:
  - matrix_c_score      FLOAT
  - pri_bid_ratio        FLOAT
  - price_flagged        BOOLEAN
  - price_flag_reason    TEXT
  - capacity_detail      JSON
  - integrity_detail     JSON
  - matrix_evaluated_at  TIMESTAMPTZ
  - matrix_evaluated_by  INTEGER → professionals.id
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0028_ethics_origin_matrix"
down_revision = "0027_capture_large_shi2_pri"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── ethics_violations ─────────────────────────────────────────────────────
    op.create_table(
        "ethics_violations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("uid", sa.String(80), unique=True, index=True, nullable=False),
        sa.Column("tier", sa.String(10), nullable=False, index=True),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("against_professional_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("against_firm", sa.String(255), nullable=True),
        sa.Column("reported_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("reported_by_system", sa.Boolean, server_default="false"),
        sa.Column("auto_trigger_source", sa.String(80), nullable=True),
        sa.Column("project_uid", sa.String(100), nullable=True, index=True),
        sa.Column("component_uid", sa.String(180), nullable=True),
        sa.Column("reference_record_type", sa.String(80), nullable=True),
        sa.Column("reference_record_id", sa.Integer, nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("supporting_evidence", postgresql.JSON, nullable=True),
        sa.Column("evidence_urls", postgresql.JSON, nullable=True),
        sa.Column("twin_event_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(30), server_default="reported", index=True),
        sa.Column("panel_decision", sa.String(30), nullable=True),
        sa.Column("panel_notes", sa.Text, nullable=True),
        sa.Column("panel_decision_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("panel_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consequences_applied", postgresql.JSON, server_default="[]"),
        sa.Column("pri_deduction_applied", sa.Float, server_default="0.0"),
        sa.Column("band_before", sa.String(20), nullable=True),
        sa.Column("band_after", sa.String(20), nullable=True),
        sa.Column("pay_hold_triggered", sa.Boolean, server_default="false"),
        sa.Column("platform_action", sa.String(30), nullable=True),
        sa.Column("criminal_referral_issued", sa.Boolean, server_default="false"),
        sa.Column("appealed", sa.Boolean, server_default="false"),
        sa.Column("appeal_notes", sa.Text, nullable=True),
        sa.Column("appeal_outcome", sa.String(30), nullable=True),
        sa.Column("is_public_record", sa.Boolean, server_default="false"),
        sa.Column("public_summary", sa.Text, nullable=True),
    )
    op.create_index("ix_ethics_against",
                    "ethics_violations",
                    ["against_professional_id", "tier"])
    op.create_index("ix_ethics_status_tier",
                    "ethics_violations", ["status", "tier"])

    # ── ethics_whistleblower_reports ──────────────────────────────────────────
    op.create_table(
        "ethics_whistleblower_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("reporter_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("anonymous", sa.Boolean, server_default="false"),
        sa.Column("violation_tier_suspected", sa.String(10), nullable=False),
        sa.Column("category_suspected", sa.String(80), nullable=False),
        sa.Column("against_professional_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("project_uid", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence_urls", postgresql.JSON, nullable=True),
        sa.Column("converted_to_violation_id", sa.Integer,
                  sa.ForeignKey("ethics_violations.id"), nullable=True),
        sa.Column("status", sa.String(30), server_default="received"),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column("protection_issued", sa.Boolean, server_default="false"),
        sa.Column("protection_expiry", sa.DateTime(timezone=True), nullable=True),
    )

    # ── ethics_probation_records ──────────────────────────────────────────────
    op.create_table(
        "ethics_probation_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("professional_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=False, index=True),
        sa.Column("violation_id", sa.Integer,
                  sa.ForeignKey("ethics_violations.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean, server_default="true"),
        sa.Column("blocked_from_critical_approval",
                  sa.Boolean, server_default="true"),
        sa.Column("band_advancement_blocked", sa.Boolean, server_default="true"),
        sa.Column("mandatory_recertification_by",
                  sa.DateTime(timezone=True), nullable=True),
        sa.Column("recertification_completed", sa.Boolean, server_default="false"),
        sa.Column("terminated_early", sa.Boolean, server_default="false"),
        sa.Column("termination_reason", sa.Text, nullable=True),
    )
    op.create_index("ix_probation_professional_active",
                    "ethics_probation_records",
                    ["professional_id", "active"])

    # ── origin_suppliers ──────────────────────────────────────────────────────
    op.create_table(
        "origin_suppliers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("uid", sa.String(80), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("registration_number", sa.String(120), nullable=True),
        sa.Column("material_types", postgresql.JSON, server_default="[]"),
        sa.Column("tier", sa.String(20), server_default="unverified"),
        sa.Column("tier_last_assessed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason", sa.Text, nullable=True),
        sa.Column("audit_report_url", sa.String(500), nullable=True),
        sa.Column("audit_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_batches_registered", sa.Integer, server_default="0"),
        sa.Column("batches_verified", sa.Integer, server_default="0"),
        sa.Column("batches_rejected", sa.Integer, server_default="0"),
        sa.Column("avg_strength_ratio", sa.Float, server_default="0.0"),
    )
    op.create_index("ix_origin_suppliers_tier", "origin_suppliers", ["tier"])

    # ── origin_material_batches ───────────────────────────────────────────────
    op.create_table(
        "origin_material_batches",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("batch_uid", sa.String(120), unique=True, index=True, nullable=False),
        sa.Column("material_type", sa.String(50), nullable=False),
        sa.Column("supplier_id", sa.Integer,
                  sa.ForeignKey("origin_suppliers.id"), nullable=True),
        sa.Column("supplier_uid", sa.String(80), nullable=True),
        sa.Column("production_plant", sa.String(255), nullable=True),
        sa.Column("production_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heat_number", sa.String(80), nullable=True),
        sa.Column("mix_design_ref", sa.String(80), nullable=True),
        sa.Column("specified_grade", sa.String(50), nullable=True),
        sa.Column("specified_strength_mpa", sa.Float, nullable=True),
        sa.Column("design_standard", sa.String(30), nullable=True),
        sa.Column("delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_note_number", sa.String(120), nullable=True),
        sa.Column("delivery_note_url", sa.String(500), nullable=True),
        sa.Column("quantity_delivered", sa.Float, nullable=True),
        sa.Column("quantity_unit", sa.String(20), nullable=True),
        sa.Column("projects_used", postgresql.JSON, nullable=True),
        sa.Column("components_used", postgresql.JSON, nullable=True),
        sa.Column("mill_cert_number", sa.String(120), nullable=True),
        sa.Column("mill_cert_url", sa.String(500), nullable=True),
        sa.Column("mill_cert_sha256", sa.String(64), nullable=True),
        sa.Column("provenance_status", sa.String(20),
                  server_default="incomplete", nullable=False, index=True),
        sa.Column("verified_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_notes", sa.Text, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("strength_ratio", sa.Float, nullable=True),
        sa.Column("anomaly_flags", postgresql.JSON, server_default="[]"),
        sa.Column("ethics_flag_triggered", sa.Boolean, server_default="false"),
    )
    op.create_index("ix_origin_batches_status",
                    "origin_material_batches", ["provenance_status"])

    # ── origin_supply_chain_records ───────────────────────────────────────────
    op.create_table(
        "origin_supply_chain_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("batch_uid", sa.String(120), nullable=False, index=True),
        sa.Column("batch_id", sa.Integer,
                  sa.ForeignKey("origin_material_batches.id"), nullable=True),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("from_party", sa.String(255), nullable=True),
        sa.Column("to_party", sa.String(255), nullable=True),
        sa.Column("from_location", sa.String(255), nullable=True),
        sa.Column("to_location", sa.String(255), nullable=True),
        sa.Column("from_geo", sa.String(60), nullable=True),
        sa.Column("to_geo", sa.String(60), nullable=True),
        sa.Column("transfer_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("quantity_unit", sa.String(20), nullable=True),
        sa.Column("document_ref", sa.String(120), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column("document_sha256", sa.String(64), nullable=True),
        sa.Column("recorded_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("verified", sa.Boolean, server_default="false"),
    )

    # ── origin_test_records ──────────────────────────────────────────��────────
    op.create_table(
        "origin_test_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("batch_uid", sa.String(120), nullable=False, index=True),
        sa.Column("batch_id", sa.Integer,
                  sa.ForeignKey("origin_material_batches.id"), nullable=True),
        sa.Column("test_standard", sa.String(30), nullable=False),
        sa.Column("laboratory_name", sa.String(255), nullable=False),
        sa.Column("laboratory_accreditation", sa.String(120), nullable=True),
        sa.Column("test_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sample_reference", sa.String(120), nullable=True),
        sa.Column("specified_value", sa.Float, nullable=True),
        sa.Column("actual_value", sa.Float, nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("test_type", sa.String(80), nullable=True),
        sa.Column("passed", sa.Boolean, server_default="false"),
        sa.Column("strength_ratio", sa.Float, nullable=True),
        sa.Column("certificate_number", sa.String(120), nullable=True),
        sa.Column("certificate_url", sa.String(500), nullable=True),
        sa.Column("certificate_sha256", sa.String(64), nullable=True),
        sa.Column("verified_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anomaly_flag", sa.Boolean, server_default="false"),
        sa.Column("anomaly_description", sa.Text, nullable=True),
    )

    # ── bids: MATRIX-C columns ────────────────────────────────────────────────
    with op.batch_alter_table("bids") as batch_op:
        batch_op.add_column(sa.Column(
            "matrix_c_score", sa.Float, nullable=True
        ))
        batch_op.add_column(sa.Column(
            "pri_bid_ratio", sa.Float, nullable=True
        ))
        batch_op.add_column(sa.Column(
            "price_flagged", sa.Boolean, server_default="false"
        ))
        batch_op.add_column(sa.Column(
            "price_flag_reason", sa.Text, nullable=True
        ))
        batch_op.add_column(sa.Column(
            "capacity_detail", postgresql.JSON, nullable=True
        ))
        batch_op.add_column(sa.Column(
            "integrity_detail", postgresql.JSON, nullable=True
        ))
        batch_op.add_column(sa.Column(
            "matrix_evaluated_at", sa.DateTime(timezone=True), nullable=True
        ))
        batch_op.add_column(sa.Column(
            "matrix_evaluated_by_id", sa.Integer,
            sa.ForeignKey("professionals.id"), nullable=True
        ))


def downgrade() -> None:
    for col in ["matrix_c_score", "pri_bid_ratio", "price_flagged",
                "price_flag_reason", "capacity_detail", "integrity_detail",
                "matrix_evaluated_at", "matrix_evaluated_by_id"]:
        with op.batch_alter_table("bids") as b:
            b.drop_column(col)

    op.drop_table("origin_test_records")
    op.drop_table("origin_supply_chain_records")
    op.drop_table("origin_material_batches")
    op.drop_table("origin_suppliers")
    op.drop_table("ethics_probation_records")
    op.drop_table("ethics_whistleblower_reports")
    op.drop_table("ethics_violations")
