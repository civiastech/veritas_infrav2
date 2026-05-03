"""
VERITAS INFRA™ — PREFAB™ Module Models
Component UID System, Structural Specification Spine, Deviation Log.

Every structural element in a registered project must have a ComponentSpec
before execution begins. The UID is the primary key for all BUILD™, VISION™,
PAY™, and TWIN™ records for that element. No spec = no pour = no payment.

Integration: append `from app.models.prefab import *` to entities.py imports.
New tables: component_specs, deviation_records, prefab_library_entries.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# ── Enumerations ──────────────────────────────────────────────────────────────

class ExecutionSensitivity(str, PyEnum):
    LOW      = "LOW"       # Standard precautions
    MEDIUM   = "MEDIUM"    # Enhanced supervision required
    HIGH     = "HIGH"      # TRUSTED+ sign-off mandatory; pour hold auto-set
    CRITICAL = "CRITICAL"  # HONOR sign-off mandatory; CST notification on deviation


class ComponentTypeCode(str, PyEnum):
    COL   = "COL"    # Column
    BEAM  = "BEAM"   # Beam
    SLAB  = "SLAB"   # Slab
    WALL  = "WALL"   # Structural wall
    FOUND = "FOUND"  # Foundation
    PILE  = "PILE"   # Pile
    PCAP  = "PCAP"   # Pile cap
    SWALL = "SWALL"  # Shear wall
    CWALL = "CWALL"  # Core wall
    TBEAM = "TBEAM"  # Transfer beam
    RWALL = "RWALL"  # Retaining wall
    STAIR = "STAIR"  # Staircase
    FSLAB = "FSLAB"  # Flat slab
    RBEAM = "RBEAM"  # Roof beam
    PAD   = "PAD"    # Pad foundation
    STRIP = "STRIP"  # Strip foundation
    RAFT  = "RAFT"   # Raft foundation
    OTHER = "OTHER"  # Other structural element


class DeviationType(str, PyEnum):
    MATERIAL      = "MATERIAL"       # Wrong material or grade
    DIMENSION     = "DIMENSION"      # Section size incorrect
    COVER         = "COVER"          # Inadequate concrete cover
    REBAR_SIZE    = "REBAR_SIZE"     # Wrong bar diameter
    REBAR_SPACING = "REBAR_SPACING"  # Incorrect bar spacing
    LAP_LENGTH    = "LAP_LENGTH"     # Insufficient lap length
    OMISSION      = "OMISSION"       # Element missing from spec
    ADDITION      = "ADDITION"       # Unauthorised addition
    SUBSTITUTION  = "SUBSTITUTION"   # Spec material replaced without approval
    ALIGNMENT     = "ALIGNMENT"      # Positional error
    OTHER         = "OTHER"


class DeviationSeverity(str, PyEnum):
    MINOR    = "MINOR"    # Self-correctable; Tier-3 Ethics; logged only
    MAJOR    = "MAJOR"    # Requires TRUSTED+ review; Tier-2 Ethics risk
    CRITICAL = "CRITICAL" # PAY hold triggered; LEX notified; Tier-1 Ethics risk


class ReviewDecision(str, PyEnum):
    ACCEPTED             = "accepted"
    REJECTED             = "rejected"
    REQUIRES_REMEDIATION = "requires_remediation"


# ── UID Validator ─────────────────────────────────────────────────────────────

UID_PATTERN = re.compile(
    r"^[A-Z0-9\-]+/[A-Z0-9]+/[A-Z0-9]+/[A-Z]+/\d{3,5}$"
)
# Format: PROJECT_CODE/LEVEL/GRID/TYPE/SEQUENCE
# Example: BLD-IKEJA/L3/C4/COL/019
# Example: BLD-NGR-LH1/L3/S1/SLAB/004


def validate_uid_format(uid: str) -> bool:
    """Return True if UID matches PREFAB™ canonical format."""
    return bool(UID_PATTERN.match(uid))


def parse_uid(uid: str) -> dict:
    """Parse a canonical UID into its structural components."""
    parts = uid.split("/")
    if len(parts) != 5:
        return {}
    return {
        "project_code": parts[0],
        "level": parts[1],
        "grid": parts[2],
        "type": parts[3],
        "sequence": parts[4],
    }


def generate_uid(project_code: str, level: str, grid: str,
                 component_type: str, sequence: int) -> str:
    """Generate a canonical PREFAB™ Component UID."""
    return f"{project_code.upper()}/{level.upper()}/{grid.upper()}/{component_type.upper()}/{sequence:03d}"


# ── ComponentSpec — The Specification Spine ───────────────────────────────────

class ComponentSpec(Base):
    """
    The structural specification for a single component instance.
    Created by a TRUSTED+ engineer before any construction activity begins.
    This record is the source of truth for BUILD™, VISION™, and TWIN™.

    Doctrine: Clarity removes uncertainty. Uncertainty enables failure.
    """
    __tablename__ = "component_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Identity ─────────────────────────────────────────────────────────────
    component_uid: Mapped[str] = mapped_column(
        String(180), unique=True, index=True, nullable=False
    )
    project_uid: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    # Parsed UID parts (stored for fast filtering)
    level_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    grid_reference: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    component_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sequence_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # ── Structural Specification ──────────────────────────────────────────────
    # Full canonical encoding, e.g.: C-305x305-4T20+R8@150
    specification_code: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Concrete
    concrete_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # e.g. C30/37
    concrete_fck_mpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    water_cement_ratio_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Cover
    cover_nominal_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cover_minimum_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exposure_class: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # XC1, XS2 etc.

    # Design
    design_standard: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # EC2, BS8110
    design_life_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Rebar specification stored as JSON
    # {
    #   "main_bars": "4T20",
    #   "secondary_bars": "2T16",
    #   "links": "R8",
    #   "link_spacing_mm": 150,
    #   "lap_length_mm": 720,
    #   "anchorage_length_mm": 600,
    #   "bar_grade": "B500B"
    # }
    rebar_spec: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Section dimensions
    section_width_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_depth_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    element_length_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Load Path ─────────────────────────────────────────────────────────────
    # Human-readable: "Gravity → Beam B2 → Foundation Pad F-11"
    load_path_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # UIDs of components this element directly supports or connects to
    connects_to_uids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # UID of the component directly below (foundation/column below this beam)
    supported_by_uid: Mapped[Optional[str]] = mapped_column(String(180), nullable=True)

    # ── Execution Sensitivity ─────────────────────────────────────────────────
    execution_sensitivity: Mapped[str] = mapped_column(
        String(20), default=ExecutionSensitivity.MEDIUM, nullable=False
    )
    sensitivity_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Substitution policy
    substitute_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    # Minimum PRI band required to approve a substitution
    substitute_requires_band: Mapped[str] = mapped_column(String(20), default="TRUSTED")

    # ── Approval ─────────────────────────────────────────────────────────────
    # The engineer who approved this spec — must be TRUSTED or HONOR
    approved_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Deviation Log Closure — SEAL™ Gate 9 ─────────────────────────────────
    # ALL deviations on this component must be closed before SEAL™ can be issued.
    deviation_log_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    deviation_log_closed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    deviation_log_closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deviation_log_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Convenience flag: no deviations exist (or all are MINOR self-corrected)
    has_open_deviations: Mapped[bool] = mapped_column(Boolean, default=False)
    deviation_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Library Reference ─────────────────────────────────────────────────────
    # Optional: created from a library template
    library_entry_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prefab_library_entries.id"), nullable=True
    )

    __table_args__ = (
        Index("ix_component_specs_project_type", "project_uid", "component_type"),
        Index("ix_component_specs_sensitivity", "execution_sensitivity"),
        Index("ix_component_specs_deviation_open", "has_open_deviations"),
    )

    def get_minimum_approver_band(self) -> str:
        """Return the minimum PRI band required to approve this spec."""
        if self.execution_sensitivity in (
            ExecutionSensitivity.HIGH, ExecutionSensitivity.CRITICAL
        ):
            return "TRUSTED"
        return "STABLE"

    def get_minimum_inspector_band(self) -> str:
        """Return the minimum PRI band required to inspect this component."""
        if self.execution_sensitivity == ExecutionSensitivity.CRITICAL:
            return "HONOR"
        elif self.execution_sensitivity == ExecutionSensitivity.HIGH:
            return "TRUSTED"
        return "STABLE"


# ── DeviationRecord — The Correction Pair Log ─────────────────────────────────

class DeviationRecord(Base):
    """
    Any deviation from the ComponentSpec specification.

    Doctrine: Concealed corrections without evidence pair trigger
    Tier-2 Ethics violation automatically.

    Both before_photo_url and after_photo_url are mandatory for all
    MAJOR and CRITICAL deviations. MINOR deviations may self-close
    but still require the after-photo confirming correction.

    This record feeds SEAL™ Gate 9 (deviation log closure).
    CRITICAL deviations trigger PAY™ hold and LEX™ notification.
    """
    __tablename__ = "deviation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Identification ────────────────────────────────────────────────────────
    component_uid: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    project_uid: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    component_spec_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("component_specs.id"), nullable=True, index=True
    )

    # ── Deviation Details ─────────────────────────────────────────────────────
    deviation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Specific measurement data where applicable
    # {"specified": "30mm", "actual": "22mm", "shortfall_mm": 8}
    measurement_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Discovered by
    discovered_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    discovered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Before/After Photo Pair — CAPTURE-LARGE Element 4 ────────────────────
    # MANDATORY for MAJOR and CRITICAL. Required for all deviations.
    before_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    before_photo_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    after_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    after_photo_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    photos_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Correction Status ─────────────────────────────────────────────────────
    corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    correction_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Engineering Review ─────────────────────────────────────────────────────
    # Required for MAJOR (TRUSTED+) and CRITICAL (HONOR)
    engineer_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_decision: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Closure ───────────────────────────────────────────────────────────────
    closed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Ethics Violation Auto-trigger ─────────────────────────────────────────
    ethics_violation_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    ethics_violation_tier: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ethics_violation_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── PAY Hold trigger ──────────────────────────────────────────────────────
    pay_hold_triggered: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── TWIN record ───────────────────────────────────────────────────────────
    twin_event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_deviation_records_closed", "closed"),
        Index("ix_deviation_records_severity", "severity"),
        Index("ix_deviation_records_project", "project_uid", "closed"),
    )

    @property
    def requires_before_after_photos(self) -> bool:
        return self.severity in (
            DeviationSeverity.MAJOR, DeviationSeverity.CRITICAL
        )

    @property
    def minimum_reviewer_band(self) -> str:
        if self.severity == DeviationSeverity.CRITICAL:
            return "HONOR"
        elif self.severity == DeviationSeverity.MAJOR:
            return "TRUSTED"
        return "STABLE"


# ── PrefabLibraryEntry — Reusable Specification Templates ────────────────────

class PrefabLibraryEntry(Base):
    """
    Reusable specification templates. A TRUSTED+ engineer creates these once
    and project specs reference them. Ensures consistency across projects
    and makes specification creation faster for repeat element types.
    """
    __tablename__ = "prefab_library_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_type: Mapped[str] = mapped_column(String(20), nullable=False)
    specification_code: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    concrete_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cover_nominal_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    design_standard: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rebar_spec: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    execution_sensitivity: Mapped[str] = mapped_column(
        String(20), default=ExecutionSensitivity.MEDIUM
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    # How many times this template has been used
    usage_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_library_entries_type", "component_type", "active"),
    )
