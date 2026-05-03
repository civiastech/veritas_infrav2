"""
Alembic Migration 0027 — CAPTURE-LARGE + SHI-2 Sub-Scores + PRI Components

Adds to 'evidence' table:
  - photo_type           VARCHAR(30)   — wide_context|detail_closeup|measurement_reference|
                                         before_correction|after_correction|geo_tag|supplemental
  - geo_lat              FLOAT         — GPS latitude from EXIF/client
  - geo_lon              FLOAT         — GPS longitude from EXIF/client
  - geo_accuracy_m       FLOAT         — GPS accuracy in metres (must be ≤15m)
  - geo_verified         BOOLEAN       — True if accuracy ≤ 15m
  - capture_ts           TIMESTAMPTZ   — device capture timestamp
  - server_ts            TIMESTAMPTZ   — server receipt timestamp
  - timestamp_drift_s    INTEGER       — abs(server_ts - capture_ts) seconds
  - element_index        INTEGER       — which of 6 CAPTURE-LARGE elements this is (1–6)

Adds to 'inspections' table (SHI-2 full sub-scores, 21 fields):
  Material (30 pts):
    m_concrete_strength, m_steel_cert, m_batch_record,
    m_wc_ratio, m_curing_record, m_admixture
  Assembly (40 pts):
    a_rebar_size, a_bar_spacing, a_cover,
    a_lap_length, a_tie_spacing, a_formwork, a_starter_bar
  Environmental (10 pts):
    e_ambient_temp, e_humidity, e_wind_sun, e_exposure_class
  Supervisory (20 pts):
    s_approver_pri_band, s_evidence_completeness,
    s_reason_tag_quality, s_deviation_documentation
  Penalties:
    penalty_concealed_deviation  FLOAT  (negative, applied to SHI)
  Computed:
    shi_material_total, shi_assembly_total,
    shi_env_total, shi_supervisory_total
  Meta:
    inspector_pri_band, reason_tag_quality_assessed

Adds to 'professionals' table (PRI 5-component formula):
  pri_eqh           FLOAT   — Execution Quality History (35%)
  pri_esi           FLOAT   — Evidence Submission Integrity (25%)
  pri_ar            FLOAT   — Accountability Record (20%)
  pri_sis           FLOAT   — Supervisory Influence Score (12%)
  pri_pd            FLOAT   — Professional Development (8%)
  pri_score_computed FLOAT  — Computed PRI (0-100)
  pri_last_full_compute TIMESTAMPTZ

Adds to 'evidence' table (CAPTURE-LARGE package tracking):
  capture_large_package_id  INTEGER  — groups 6 elements into one submission
  is_capture_large_complete BOOLEAN  — True when all 6 elements submitted

New table: capture_large_packages
  Tracks grouped 6-element CAPTURE-LARGE submissions per component action.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0027_capture_large_shi2_pri"
down_revision = "0026_prefab_module"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── capture_large_packages ────────────────────────────────────────────────
    op.create_table(
        "capture_large_packages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("component_uid", sa.String(180), index=True, nullable=False),
        sa.Column("project_uid", sa.String(100), index=True, nullable=False),
        sa.Column("action_type", sa.String(80), nullable=False),
        sa.Column("submitted_by_id", sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),

        # Element completion flags
        sa.Column("has_wide_context",      sa.Boolean, server_default="false"),
        sa.Column("has_detail_closeup",    sa.Boolean, server_default="false"),
        sa.Column("has_measurement_ref",   sa.Boolean, server_default="false"),
        sa.Column("has_before_correction", sa.Boolean, server_default="false"),
        sa.Column("has_after_correction",  sa.Boolean, server_default="false"),
        sa.Column("has_geo_tag",           sa.Boolean, server_default="false"),

        # Aggregate GPS (from geo_tag element)
        sa.Column("geo_lat",        sa.Float, nullable=True),
        sa.Column("geo_lon",        sa.Float, nullable=True),
        sa.Column("geo_accuracy_m", sa.Float, nullable=True),
        sa.Column("geo_verified",   sa.Boolean, server_default="false"),

        # Completion
        sa.Column("is_complete",         sa.Boolean, server_default="false"),
        sa.Column("completed_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_score",    sa.Float, nullable=True),
        sa.Column("package_hash",        sa.String(64), nullable=True),

        # Review
        sa.Column("status",           sa.String(30), server_default="pending"),
        sa.Column("reviewed_by_id",   sa.Integer,
                  sa.ForeignKey("professionals.id"), nullable=True),
        sa.Column("reviewed_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_clp_component_status",
        "capture_large_packages", ["component_uid", "status"],
    )

    # ── evidence: CAPTURE-LARGE enforcement fields ────────────────────────────
    with op.batch_alter_table("evidence") as batch_op:
        batch_op.add_column(sa.Column(
            "photo_type", sa.String(30), nullable=True,
            comment="wide_context|detail_closeup|measurement_reference|"
                    "before_correction|after_correction|geo_tag|supplemental"
        ))
        batch_op.add_column(sa.Column("geo_lat",         sa.Float, nullable=True))
        batch_op.add_column(sa.Column("geo_lon",         sa.Float, nullable=True))
        batch_op.add_column(sa.Column("geo_accuracy_m",  sa.Float, nullable=True))
        batch_op.add_column(sa.Column(
            "geo_verified", sa.Boolean, server_default="false", nullable=False
        ))
        batch_op.add_column(sa.Column(
            "capture_ts", sa.DateTime(timezone=True), nullable=True
        ))
        batch_op.add_column(sa.Column(
            "server_ts", sa.DateTime(timezone=True), nullable=True
        ))
        batch_op.add_column(sa.Column(
            "timestamp_drift_s", sa.Integer, nullable=True
        ))
        batch_op.add_column(sa.Column(
            "element_index", sa.Integer, nullable=True,
            comment="Which of the 6 CAPTURE-LARGE elements: 1=wide_context "
                    "2=detail_closeup 3=measurement_ref 4=before/after "
                    "5=geo_tag 6=supplemental"
        ))
        batch_op.add_column(sa.Column(
            "capture_large_package_id", sa.Integer,
            sa.ForeignKey("capture_large_packages.id"), nullable=True
        ))

    # ── inspections: SHI-2 full sub-scores ───────────────────────────────────
    with op.batch_alter_table("inspections") as batch_op:

        # Material sub-scores (30 pts)
        batch_op.add_column(sa.Column("m_concrete_strength", sa.Float, nullable=True))
        batch_op.add_column(sa.Column("m_steel_cert",        sa.Float, nullable=True))
        batch_op.add_column(sa.Column("m_batch_record",      sa.Float, nullable=True))
        batch_op.add_column(sa.Column("m_wc_ratio",          sa.Float, nullable=True))
        batch_op.add_column(sa.Column("m_curing_record",     sa.Float, nullable=True))
        batch_op.add_column(sa.Column("m_admixture",         sa.Float, nullable=True))

        # Assembly sub-scores (40 pts)
        batch_op.add_column(sa.Column("a_rebar_size",    sa.Float, nullable=True))
        batch_op.add_column(sa.Column("a_bar_spacing",   sa.Float, nullable=True))
        batch_op.add_column(sa.Column("a_cover",         sa.Float, nullable=True))
        batch_op.add_column(sa.Column("a_lap_length",    sa.Float, nullable=True))
        batch_op.add_column(sa.Column("a_tie_spacing",   sa.Float, nullable=True))
        batch_op.add_column(sa.Column("a_formwork",      sa.Float, nullable=True))
        batch_op.add_column(sa.Column("a_starter_bar",   sa.Float, nullable=True))

        # Environmental sub-scores (10 pts)
        batch_op.add_column(sa.Column("e_ambient_temp",   sa.Float, nullable=True))
        batch_op.add_column(sa.Column("e_humidity",       sa.Float, nullable=True))
        batch_op.add_column(sa.Column("e_wind_sun",       sa.Float, nullable=True))
        batch_op.add_column(sa.Column("e_exposure_class", sa.Float, nullable=True))

        # Supervisory sub-scores (20 pts)
        batch_op.add_column(sa.Column("s_approver_band",        sa.Float, nullable=True))
        batch_op.add_column(sa.Column("s_evidence_completeness",sa.Float, nullable=True))
        batch_op.add_column(sa.Column("s_reason_tag_quality",   sa.Float, nullable=True))
        batch_op.add_column(sa.Column("s_deviation_docs",       sa.Float, nullable=True))

        # Penalty
        batch_op.add_column(sa.Column(
            "penalty_concealed_deviation", sa.Float,
            server_default="0.0", nullable=False
        ))

        # Category totals (stored for fast reporting)
        batch_op.add_column(sa.Column("shi_material_total",    sa.Float, nullable=True))
        batch_op.add_column(sa.Column("shi_assembly_total",    sa.Float, nullable=True))
        batch_op.add_column(sa.Column("shi_env_total",         sa.Float, nullable=True))
        batch_op.add_column(sa.Column("shi_supervisory_total", sa.Float, nullable=True))

        # Meta
        batch_op.add_column(sa.Column(
            "inspector_pri_band", sa.String(20), nullable=True
        ))
        batch_op.add_column(sa.Column(
            "reason_tag_quality_score", sa.Float, nullable=True
        ))
        batch_op.add_column(sa.Column(
            "construction_stage", sa.String(50), nullable=True
        ))
        batch_op.add_column(sa.Column(
            "min_shi_for_stage", sa.Float, nullable=True
        ))

    # ── professionals: PRI 5-component fields ────────────────────────────────
    with op.batch_alter_table("professionals") as batch_op:
        batch_op.add_column(sa.Column(
            "pri_eqh", sa.Float, server_default="0.0", nullable=False,
            comment="Execution Quality History 35%"
        ))
        batch_op.add_column(sa.Column(
            "pri_esi", sa.Float, server_default="1.0", nullable=False,
            comment="Evidence Submission Integrity 25%"
        ))
        batch_op.add_column(sa.Column(
            "pri_ar", sa.Float, server_default="1.0", nullable=False,
            comment="Accountability Record 20% (1.0=clean)"
        ))
        batch_op.add_column(sa.Column(
            "pri_sis", sa.Float, server_default="0.0", nullable=False,
            comment="Supervisory Influence Score 12%"
        ))
        batch_op.add_column(sa.Column(
            "pri_pd", sa.Float, server_default="0.0", nullable=False,
            comment="Professional Development 8%"
        ))
        batch_op.add_column(sa.Column(
            "pri_score_computed", sa.Float, server_default="35.0", nullable=False,
            comment="Computed PRI from 5-component formula"
        ))
        batch_op.add_column(sa.Column(
            "pri_last_full_compute", sa.DateTime(timezone=True), nullable=True
        ))
        # Counts used in formula computation
        batch_op.add_column(sa.Column(
            "total_inspections_approved", sa.Integer,
            server_default="0", nullable=False
        ))
        batch_op.add_column(sa.Column(
            "total_evidence_required", sa.Integer,
            server_default="0", nullable=False
        ))
        batch_op.add_column(sa.Column(
            "total_evidence_complete", sa.Integer,
            server_default="0", nullable=False
        ))
        batch_op.add_column(sa.Column(
            "total_disputes_caused", sa.Integer,
            server_default="0", nullable=False
        ))
        batch_op.add_column(sa.Column(
            "total_disputes_unresolved", sa.Integer,
            server_default="0", nullable=False
        ))
        batch_op.add_column(sa.Column(
            "total_supervised_count", sa.Integer,
            server_default="0", nullable=False
        ))
        batch_op.add_column(sa.Column(
            "supervised_avg_shi", sa.Float,
            server_default="0.0", nullable=False
        ))
        batch_op.add_column(sa.Column(
            "total_academy_completions", sa.Integer,
            server_default="0", nullable=False
        ))


def downgrade() -> None:
    # professionals
    for col in [
        "pri_eqh","pri_esi","pri_ar","pri_sis","pri_pd",
        "pri_score_computed","pri_last_full_compute",
        "total_inspections_approved","total_evidence_required",
        "total_evidence_complete","total_disputes_caused",
        "total_disputes_unresolved","total_supervised_count",
        "supervised_avg_shi","total_academy_completions",
    ]:
        with op.batch_alter_table("professionals") as b:
            b.drop_column(col)

    # inspections
    for col in [
        "m_concrete_strength","m_steel_cert","m_batch_record",
        "m_wc_ratio","m_curing_record","m_admixture",
        "a_rebar_size","a_bar_spacing","a_cover","a_lap_length",
        "a_tie_spacing","a_formwork","a_starter_bar",
        "e_ambient_temp","e_humidity","e_wind_sun","e_exposure_class",
        "s_approver_band","s_evidence_completeness",
        "s_reason_tag_quality","s_deviation_docs",
        "penalty_concealed_deviation",
        "shi_material_total","shi_assembly_total",
        "shi_env_total","shi_supervisory_total",
        "inspector_pri_band","reason_tag_quality_score",
        "construction_stage","min_shi_for_stage",
    ]:
        with op.batch_alter_table("inspections") as b:
            b.drop_column(col)

    # evidence
    for col in [
        "photo_type","geo_lat","geo_lon","geo_accuracy_m",
        "geo_verified","capture_ts","server_ts","timestamp_drift_s",
        "element_index","capture_large_package_id",
    ]:
        with op.batch_alter_table("evidence") as b:
            b.drop_column(col)

    op.drop_index("ix_clp_component_status", "capture_large_packages")
    op.drop_table("capture_large_packages")
