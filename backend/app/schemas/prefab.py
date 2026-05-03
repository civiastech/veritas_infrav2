"""
VERITAS INFRA™ — PREFAB™ Schemas
All Pydantic request/response models for the PREFAB™ module.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Library Entry Schemas ─────────────────────────────────────────────────────

class LibraryEntryCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    component_type: str
    specification_code: Optional[str] = None
    concrete_grade: Optional[str] = None
    cover_nominal_mm: Optional[int] = Field(default=None, ge=10, le=150)
    design_standard: Optional[str] = None
    rebar_spec: Optional[dict] = None
    execution_sensitivity: str = "MEDIUM"
    description: Optional[str] = None

    @field_validator("execution_sensitivity")
    @classmethod
    def validate_sensitivity(cls, v: str) -> str:
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if v not in allowed:
            raise ValueError(f"Must be one of {allowed}")
        return v


class LibraryEntryOut(BaseModel):
    id: int
    name: str
    component_type: str
    specification_code: Optional[str]
    concrete_grade: Optional[str]
    cover_nominal_mm: Optional[int]
    execution_sensitivity: str
    description: Optional[str]
    active: bool
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Component Spec Schemas ────────────────────────────────────────────────────

class RebarSpec(BaseModel):
    """Structured rebar specification."""
    main_bars: Optional[str] = None           # e.g. "4T20"
    secondary_bars: Optional[str] = None      # e.g. "2T16"
    links: Optional[str] = None               # e.g. "R8"
    link_spacing_mm: Optional[int] = None     # e.g. 150
    lap_length_mm: Optional[int] = None       # e.g. 720
    anchorage_length_mm: Optional[int] = None # e.g. 600
    bar_grade: Optional[str] = None           # e.g. "B500B"


class ComponentSpecCreate(BaseModel):
    """
    Create a ComponentSpec for a registered component UID.
    Requires TRUSTED or HONOR PRI band for HIGH/CRITICAL sensitivity.
    """
    component_uid: str = Field(
        min_length=5,
        description="Canonical UID: PROJECT_CODE/LEVEL/GRID/TYPE/SEQ — e.g. BLD-IKEJA/L3/C4/COL/019"
    )
    project_uid: str

    # Optional: create from library template
    library_entry_id: Optional[int] = None

    # Structural specification
    specification_code: Optional[str] = None
    concrete_grade: Optional[str] = None
    concrete_fck_mpa: Optional[float] = Field(default=None, ge=16.0, le=100.0)
    water_cement_ratio_max: Optional[float] = Field(default=None, ge=0.3, le=0.7)
    cover_nominal_mm: Optional[int] = Field(default=None, ge=10, le=150)
    cover_minimum_mm: Optional[int] = Field(default=None, ge=10, le=150)
    exposure_class: Optional[str] = None
    design_standard: Optional[str] = None
    design_life_years: Optional[int] = Field(default=None, ge=5, le=200)

    rebar_spec: Optional[RebarSpec] = None

    section_width_mm: Optional[int] = Field(default=None, ge=100, le=5000)
    section_depth_mm: Optional[int] = Field(default=None, ge=100, le=5000)
    element_length_mm: Optional[int] = Field(default=None, ge=100, le=50000)

    # Load path
    load_path_description: Optional[str] = None
    connects_to_uids: Optional[list[str]] = None
    supported_by_uid: Optional[str] = None

    # Execution
    execution_sensitivity: str = "MEDIUM"
    sensitivity_reason: Optional[str] = None
    substitute_allowed: bool = False
    substitute_requires_band: str = "TRUSTED"

    @field_validator("execution_sensitivity")
    @classmethod
    def validate_sensitivity(cls, v: str) -> str:
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if v not in allowed:
            raise ValueError(f"execution_sensitivity must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_cover_logic(self) -> "ComponentSpecCreate":
        if self.cover_nominal_mm and self.cover_minimum_mm:
            if self.cover_minimum_mm >= self.cover_nominal_mm:
                raise ValueError(
                    "cover_minimum_mm must be less than cover_nominal_mm. "
                    "Typically: nominal = minimum + 10mm allowance"
                )
        return self


class ComponentSpecApprove(BaseModel):
    approval_notes: Optional[str] = None


class ComponentSpecOut(BaseModel):
    id: int
    component_uid: str
    project_uid: str
    level_code: Optional[str]
    grid_reference: Optional[str]
    component_type: Optional[str]
    sequence_number: Optional[str]

    specification_code: Optional[str]
    concrete_grade: Optional[str]
    concrete_fck_mpa: Optional[float]
    cover_nominal_mm: Optional[int]
    cover_minimum_mm: Optional[int]
    exposure_class: Optional[str]
    design_standard: Optional[str]
    rebar_spec: Optional[dict]

    load_path_description: Optional[str]
    connects_to_uids: Optional[list]
    supported_by_uid: Optional[str]

    execution_sensitivity: str
    sensitivity_reason: Optional[str]
    substitute_allowed: bool

    is_approved: bool
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]

    deviation_log_closed: bool
    has_open_deviations: bool
    deviation_count: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComponentSpecSummary(BaseModel):
    """Compact view for lists."""
    id: int
    component_uid: str
    project_uid: str
    component_type: Optional[str]
    execution_sensitivity: str
    is_approved: bool
    deviation_log_closed: bool
    has_open_deviations: bool
    deviation_count: int

    class Config:
        from_attributes = True


# ── Deviation Record Schemas ──────────────────────────────────────────────────

class DeviationCreate(BaseModel):
    """
    Report a deviation from the ComponentSpec.
    MAJOR and CRITICAL deviations require before/after photo URLs.
    """
    component_uid: str
    project_uid: str
    deviation_type: str
    severity: str
    description: str = Field(min_length=10)
    measurement_data: Optional[dict] = None

    # Photos — MANDATORY for MAJOR and CRITICAL
    before_photo_url: Optional[str] = None
    before_photo_sha256: Optional[str] = None
    after_photo_url: Optional[str] = None
    after_photo_sha256: Optional[str] = None

    @field_validator("deviation_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {
            "MATERIAL", "DIMENSION", "COVER", "REBAR_SIZE",
            "REBAR_SPACING", "LAP_LENGTH", "OMISSION",
            "ADDITION", "SUBSTITUTION", "ALIGNMENT", "OTHER"
        }
        if v not in allowed:
            raise ValueError(f"deviation_type must be one of {allowed}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in {"MINOR", "MAJOR", "CRITICAL"}:
            raise ValueError("severity must be MINOR, MAJOR, or CRITICAL")
        return v

    @model_validator(mode="after")
    def validate_photos_for_major_critical(self) -> "DeviationCreate":
        if self.severity in ("MAJOR", "CRITICAL"):
            if not self.before_photo_url:
                raise ValueError(
                    f"{self.severity} deviations require before_photo_url. "
                    "CAPTURE-LARGE Element 4: Before/After pair is mandatory."
                )
            if not self.after_photo_url:
                raise ValueError(
                    f"{self.severity} deviations require after_photo_url. "
                    "CAPTURE-LARGE Element 4: Before/After pair is mandatory."
                )
        return self


class DeviationCorrect(BaseModel):
    correction_description: str = Field(min_length=10)
    after_photo_url: str
    after_photo_sha256: str


class DeviationReview(BaseModel):
    review_decision: str  # "accepted" | "rejected" | "requires_remediation"
    review_notes: str = Field(min_length=10)

    @field_validator("review_decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        allowed = {"accepted", "rejected", "requires_remediation"}
        if v not in allowed:
            raise ValueError(f"review_decision must be one of {allowed}")
        return v


class DeviationOut(BaseModel):
    id: int
    component_uid: str
    project_uid: str
    deviation_type: str
    severity: str
    description: str
    measurement_data: Optional[dict]

    before_photo_url: Optional[str]
    after_photo_url: Optional[str]
    photos_verified: bool

    corrected: bool
    correction_description: Optional[str]

    engineer_review_required: bool
    reviewed_by_id: Optional[int]
    review_decision: Optional[str]
    review_notes: Optional[str]

    closed: bool
    closed_at: Optional[datetime]

    ethics_violation_triggered: bool
    ethics_violation_tier: Optional[int]
    pay_hold_triggered: bool

    created_at: datetime

    class Config:
        from_attributes = True


class DeviationLogCloseRequest(BaseModel):
    notes: Optional[str] = None


# ── SEAL Gate Check ───────────────────────────────────────────────────────────

class PrefabSealCheck(BaseModel):
    project_uid: str
    total_components: int
    specs_created: int
    specs_approved: int
    deviation_logs_closed: int
    open_deviations: int
    gate_passed: bool
    failure_reasons: list[str]
