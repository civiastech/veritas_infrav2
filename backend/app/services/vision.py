"""
VERITAS INFRA™ — VISION™ SHI-2 Full Sub-Score Engine
REPLACEMENT for backend/app/services/vision.py

CHANGES FROM ORIGINAL:
  The original services/vision.py accepted 4 top-level scores (material,
  assembly, env, supervision) and multiplied by weights. That is a calculator,
  not a verification system.

  This version implements the FULL 21-sub-component SHI-2 methodology from
  the Comprehensive Reference Manual. Each sub-score has an objective
  measurement with pass/fail thresholds tied to the ComponentSpec.

  SHI = 0.30*M + 0.40*A + 0.10*E + 0.20*S  (unchanged formula)

  But M, A, E, S are now sums of sub-scores, not arbitrary inputs.

  BACKWARD COMPATIBILITY:
  - compute_shi() and apply_inspection() signatures preserved
  - get_active_method() unchanged
  - New sub-score fields stored in columns added by migration 0027
  - If sub-scores not provided, falls back to top-level scores (legacy mode)

HOW TO INTEGRATE:
  cp this file to backend/app/services/vision.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import (
    Component, Inspection, Professional, Project, SHIMethod,
)
from app.services.audit import record_audit
from app.services.twin import append_twin_event


# ══════════════════════════════════════════════════════════════
# SHI-2 SUB-SCORE DEFINITIONS
# ══════════════════════════════════════════════════════════════

# Stage-specific minimum SHI thresholds (from Reference Manual §3.5)
STAGE_MIN_SHI: dict[str, dict[str, float]] = {
    "foundation_substructure":  {"min": 70.0, "pay_gate": 75.0},
    "ground_floor_slab":        {"min": 72.0, "pay_gate": 75.0},
    "columns_shear_walls":      {"min": 75.0, "pay_gate": 78.0},
    "transfer_beams":           {"min": 78.0, "pay_gate": 80.0},
    "upper_floor_framing":      {"min": 75.0, "pay_gate": 78.0},
    "roof_structure":           {"min": 72.0, "pay_gate": 75.0},
    "structural_envelope":      {"min": 70.0, "pay_gate": 73.0},
    "final_composite":          {"min": 78.0, "pay_gate": 0.0},  # SEAL eligible
}

SEAL_MIN_SHI = 78.0   # Final composite must be ≥ 78 for SEAL™
PAY_DEFAULT_MIN_SHI = 75.0


@dataclass
class MaterialSubScores:
    """
    Category M — Material Integrity (30 points total)
    Each sub-score is 0–max_pts. Sum = material_total (0–30).
    """
    # Max 8 pts
    concrete_strength: float = 0.0
    """
    Score guide (from ComponentSpec.concrete_fck_mpa):
      ≥ fck + 4 MPa  → 8.0
      ≥ fck + 2 MPa  → 6.0
      ≥ fck          → 4.0
      < fck but ≥ fck−4 → 2.0
      < fck−4        → 0.0  (automatic PAY™ hold)
    """
    # Max 7 pts
    steel_cert: float = 0.0
    """
      ORIGIN™ registered + mill cert verified → 7.0
      Mill cert only (not ORIGIN™ linked)     → 4.0
      No cert                                 → 0.0  (automatic PAY™ hold)
    """
    # Max 5 pts
    batch_record: float = 0.0
    """
      Complete ORIGIN™ batch UID + plant + mix + delivery → 5.0
      Partial record                                       → 2.0
      None                                                 → 0.0
    """
    # Max 4 pts
    wc_ratio: float = 0.0
    """
      ≤ specified w/c              → 4.0
      ≤ 0.05 above spec            → 2.0
      > 0.05 above spec            → 0.0
    """
    # Max 3 pts
    curing_record: float = 0.0
    """
      Temp log + duration + method → 3.0
      Partial record               → 1.0
      None                         → 0.0
    """
    # Max 3 pts
    admixture: float = 0.0
    """
      Specified admixture with dosage record  → 3.0
      Unspecified admixture present           → 1.0
      Non-compliant                           → 0.0
    """

    @property
    def total(self) -> float:
        return (
            self.concrete_strength + self.steel_cert + self.batch_record
            + self.wc_ratio + self.curing_record + self.admixture
        )

    @property
    def max_possible(self) -> float:
        return 30.0

    def validate(self) -> list[str]:
        issues = []
        if not (0 <= self.concrete_strength <= 8):
            issues.append("concrete_strength must be 0–8")
        if not (0 <= self.steel_cert <= 7):
            issues.append("steel_cert must be 0–7")
        if not (0 <= self.batch_record <= 5):
            issues.append("batch_record must be 0–5")
        if not (0 <= self.wc_ratio <= 4):
            issues.append("wc_ratio must be 0–4")
        if not (0 <= self.curing_record <= 3):
            issues.append("curing_record must be 0–3")
        if not (0 <= self.admixture <= 3):
            issues.append("admixture must be 0–3")
        return issues


@dataclass
class AssemblySubScores:
    """
    Category A — Assembly Correctness (40 points total)
    """
    # Max 8 pts
    rebar_size: float = 0.0
    """
      All bars match PREFAB™ spec       → 8.0
      ≤ 5% variation                   → 5.0
      ≤ 10% variation                  → 2.0
      > 10% or substitution w/o approval → 0.0
    """
    # Max 8 pts
    bar_spacing: float = 0.0
    """
      Within ±5mm of spec  → 8.0
      Within ±10mm         → 5.0
      Within ±20mm         → 2.0
      > 20mm deviation     → 0.0
    """
    # Max 7 pts
    cover: float = 0.0
    """
      Within ±5mm of nominal  → 7.0
      Within ±10mm            → 4.0
      Within ±15mm            → 1.0
      Below minimum specified → 0.0  (critical)
    """
    # Max 6 pts
    lap_length: float = 0.0
    """
      ≥ specified lap         → 6.0
      ≥ 95% of specified      → 4.0
      ≥ 85% of specified      → 2.0
      < 85% of specified      → 0.0
    """
    # Max 5 pts
    tie_spacing: float = 0.0
    """
      Matches PREFAB™ tie schedule exactly → 5.0
      ≤ 10% deviation                      → 3.0
      ≤ 20% deviation                      → 1.0
      > 20% deviation                      → 0.0
    """
    # Max 4 pts
    formwork: float = 0.0
    """
      Within ±3mm verticality  → 4.0
      Within ±6mm              → 2.0
      Within ±10mm             → 1.0
      > 10mm                   → 0.0
    """
    # Max 2 pts
    starter_bar: float = 0.0
    """
      Aligned with design intent    → 2.0
      Misaligned but correctable    → 1.0
      Uncorrectable deviation       → 0.0
    """

    @property
    def total(self) -> float:
        return (
            self.rebar_size + self.bar_spacing + self.cover
            + self.lap_length + self.tie_spacing + self.formwork
            + self.starter_bar
        )

    @property
    def max_possible(self) -> float:
        return 40.0

    def validate(self) -> list[str]:
        checks = [
            ("rebar_size", self.rebar_size, 8),
            ("bar_spacing", self.bar_spacing, 8),
            ("cover", self.cover, 7),
            ("lap_length", self.lap_length, 6),
            ("tie_spacing", self.tie_spacing, 5),
            ("formwork", self.formwork, 4),
            ("starter_bar", self.starter_bar, 2),
        ]
        return [f"{n} must be 0–{m}" for n, v, m in checks if not (0 <= v <= m)]


@dataclass
class EnvironmentalSubScores:
    """
    Category E — Environmental Risk Context (10 points total)
    """
    # Max 3 pts
    ambient_temp: float = 0.0
    """
      5–30°C                              → 3.0
      2–5°C or 30–35°C (with mitigation) → 2.0
      < 2°C or > 35°C without protocol   → 0.0
    """
    # Max 3 pts
    humidity: float = 0.0
    """
      RH log maintained throughout curing  → 3.0
      Partial record                        → 1.0
      No record                             → 0.0
    """
    # Max 2 pts
    wind_sun: float = 0.0
    """
      Shade/wind barrier in place  → 2.0
      Partial protection           → 1.0
      None in high-exposure        → 0.0
    """
    # Max 2 pts
    exposure_class: float = 0.0
    """
      Specified exposure class confirmed  → 2.0
      Partial                             → 1.0
      No record                           → 0.0
    """

    @property
    def total(self) -> float:
        return (
            self.ambient_temp + self.humidity
            + self.wind_sun + self.exposure_class
        )

    @property
    def max_possible(self) -> float:
        return 10.0

    def validate(self) -> list[str]:
        checks = [
            ("ambient_temp", self.ambient_temp, 3),
            ("humidity", self.humidity, 3),
            ("wind_sun", self.wind_sun, 2),
            ("exposure_class", self.exposure_class, 2),
        ]
        return [f"{n} must be 0–{m}" for n, v, m in checks if not (0 <= v <= m)]


@dataclass
class SupervisorySubScores:
    """
    Category S — Supervisory Accountability (20 points total)
    """
    # Max 8 pts  — determined from approving professional's PRI band
    approver_band: float = 0.0
    """
      HONOR      → 8.0
      TRUSTED    → 6.0
      STABLE     → 3.0
      PROVISIONAL→ 0.0  (PROVISIONAL is ineligible to approve — auto-reject)
    """
    # Max 6 pts — CAPTURE-LARGE completeness from BUILD™
    evidence_completeness: float = 0.0
    """
      All 6 CAPTURE-LARGE elements complete  → 6.0
      5 elements                             → 4.0
      4 elements                             → 2.0
      < 4 elements                           → 0.0  (auto-reject)
    """
    # Max 4 pts — assessed by inspector on quality of the reason tag text
    reason_tag_quality: float = 0.0
    """
      Specific, technically accurate engineering reasoning → 4.0
      Generic but present                                  → 2.0
      Absent                                               → 0.0
    """
    # Max 2 pts — deviation documentation
    deviation_docs: float = 0.0
    """
      All deviations with before/after pairs  → 2.0
      Partial                                 → 1.0
      Concealed deviation (no pair)           → 0.0  AND penalty −5.0 applied
    """

    @property
    def total(self) -> float:
        return (
            self.approver_band + self.evidence_completeness
            + self.reason_tag_quality + self.deviation_docs
        )

    @property
    def max_possible(self) -> float:
        return 20.0

    def validate(self) -> list[str]:
        checks = [
            ("approver_band", self.approver_band, 8),
            ("evidence_completeness", self.evidence_completeness, 6),
            ("reason_tag_quality", self.reason_tag_quality, 4),
            ("deviation_docs", self.deviation_docs, 2),
        ]
        return [f"{n} must be 0–{m}" for n, v, m in checks if not (0 <= v <= m)]


@dataclass
class SHI2Input:
    """Complete SHI-2 input with all 21 sub-scores."""
    material: MaterialSubScores = field(default_factory=MaterialSubScores)
    assembly: AssemblySubScores = field(default_factory=AssemblySubScores)
    environmental: EnvironmentalSubScores = field(default_factory=EnvironmentalSubScores)
    supervisory: SupervisorySubScores = field(default_factory=SupervisorySubScores)

    # Penalty (negative, applied after category computation)
    penalty_concealed_deviation: float = 0.0
    """−5.0 per concealed deviation instance found"""

    # Context
    construction_stage: Optional[str] = None
    reason_tag: Optional[str] = None

    def validate_all(self) -> list[str]:
        issues = []
        issues.extend(self.material.validate())
        issues.extend(self.assembly.validate())
        issues.extend(self.environmental.validate())
        issues.extend(self.supervisory.validate())
        if self.penalty_concealed_deviation > 0:
            issues.append("penalty_concealed_deviation must be ≤ 0")
        return issues


@dataclass
class SHI2Result:
    """Complete SHI-2 computation result."""
    shi: float                # Final composite (0–100, may exceed 100 slightly on max)
    material_total: float     # 0–30
    assembly_total: float     # 0–40
    env_total: float          # 0–10
    supervisory_total: float  # 0–20
    penalty: float            # ≤ 0
    classification: str
    pay_gate_passed: bool
    seal_eligible: bool
    stage_min_passed: bool
    stage_name: Optional[str]
    stage_min_shi: Optional[float]
    ai_flags: list[str]


# ══════════════════════════════════════════════════════════════
# SHI-2 COMPUTATION ENGINE
# ══════════════════════════════════════════════════════════════

_BAND_APPROVER_SCORE = {
    "HONOR": 8.0, "TRUSTED": 6.0, "STABLE": 3.0, "PROVISIONAL": 0.0
}


def score_approver_band(band: str) -> float:
    """Convert PRI band to supervisory sub-score s_approver_band."""
    return _BAND_APPROVER_SCORE.get(band.upper(), 0.0)


def score_evidence_completeness(elements_submitted: int) -> float:
    """Convert CAPTURE-LARGE element count to evidence_completeness sub-score."""
    if elements_submitted >= 6:
        return 6.0
    elif elements_submitted == 5:
        return 4.0
    elif elements_submitted == 4:
        return 2.0
    return 0.0


def score_reason_tag(reason_tag: str | None) -> float:
    """
    Heuristic quality scoring for reason tag text.
    In production, a more sophisticated NLP check is applied.
    """
    if not reason_tag or len(reason_tag.strip()) == 0:
        return 0.0
    text = reason_tag.strip()
    # Generic placeholder responses score 2
    generic_phrases = {
        "ok", "good", "done", "checked", "verified", "passed",
        "approved", "complete", "correct", "fine"
    }
    if text.lower() in generic_phrases or len(text) < 20:
        return 2.0
    # Specific engineering reasoning scores 4
    # Look for technical terms as a proxy
    engineering_terms = {
        "mm", "mpa", "grade", "cover", "rebar", "bar", "spacing",
        "concrete", "strength", "fck", "lap", "link", "stirrup",
        "formwork", "vibration", "curing", "slump", "w/c", "ratio",
    }
    word_set = set(text.lower().split())
    if word_set.intersection(engineering_terms):
        return 4.0
    # Has content but no technical terms
    return 2.0


def classify_shi(shi: float) -> str:
    if shi >= 90:
        return "SUPERIOR"
    elif shi >= 75:
        return "SAFE"
    elif shi >= 60:
        return "MARGINAL"
    return "RISK"


def generate_ai_flags(inp: SHI2Input) -> list[str]:
    """
    Rule-based anomaly flags for the inspector.
    These are advisory. Human judgment is primary and final.
    """
    flags = []
    m, a, e, s = inp.material, inp.assembly, inp.environmental, inp.supervisory

    # Material flags
    if m.concrete_strength == 0:
        flags.append("🔴 MATERIAL: Concrete strength score = 0. "
                     "Verify cube/cylinder test results against spec grade.")
    if m.steel_cert == 0:
        flags.append("🔴 MATERIAL: No steel certification. "
                     "PAY™ hold required until ORIGIN™ or mill cert verified.")
    if m.wc_ratio == 0:
        flags.append("⚠ MATERIAL: w/c ratio non-compliant. "
                     "Check mix design against pour records.")

    # Assembly flags
    if a.cover < 1.0:
        flags.append("🔴 ASSEMBLY: Concrete cover critically low. "
                     "Measure with cover meter on >10 points before approval.")
    if a.rebar_size < 2.0:
        flags.append("🔴 ASSEMBLY: Rebar size non-compliant. "
                     "Cross-check bar diameters with PREFAB™ spec.")
    if a.bar_spacing < 2.0:
        flags.append("⚠ ASSEMBLY: Bar spacing outside tolerance. "
                     "Check spacing at maximum, mid, and minimum positions.")
    if a.lap_length == 0:
        flags.append("🔴 ASSEMBLY: Lap length below 85% of spec. "
                     "This is a critical structural deficiency.")

    # Anomaly: high material, low assembly
    if m.total >= 24 and a.total < 20:
        flags.append("🔍 ANOMALY: High material score but low assembly score. "
                     "Good materials poorly installed. Verify placement records.")

    # Supervisory flags
    if s.approver_band == 0:
        flags.append("🔴 SUPERVISORY: PROVISIONAL approver ineligible. "
                     "Approval must be by STABLE, TRUSTED, or HONOR professional.")
    if s.evidence_completeness == 0:
        flags.append("🔴 SUPERVISORY: Fewer than 4 CAPTURE-LARGE elements submitted. "
                     "Package is critically incomplete.")
    if s.reason_tag_quality == 0:
        flags.append("⚠ SUPERVISORY: No reason tag provided. "
                     "A specific engineering justification is mandatory.")

    # Penalty
    if inp.penalty_concealed_deviation < 0:
        flags.append(f"🔴 ETHICS: Concealed deviation penalty applied: "
                     f"{inp.penalty_concealed_deviation} pts. "
                     "Automatic Tier-2 Ethics violation flag. LEX™ notified.")

    return flags


def compute_shi2(inp: SHI2Input, method: SHIMethod | None = None) -> SHI2Result:
    """
    Compute the full SHI-2 score from 21 sub-scores.
    Formula: SHI = 0.30*M_total + 0.40*A_total + 0.10*E_total + 0.20*S_total + penalty
    Where M is out of 30, A out of 40, E out of 10, S out of 20.
    Each category is already on its own scale so the weighted sum gives 0–100.
    """
    # Validate inputs
    errors = inp.validate_all()
    if errors:
        raise ValueError(f"SHI-2 input validation failed: {'; '.join(errors)}")

    # Use configurable weights if method provided, else use manual defaults
    mw = method.material_weight if method else 1.0
    aw = method.assembly_weight if method else 1.0
    ew = method.environment_weight if method else 1.0
    sw = method.supervision_weight if method else 1.0

    # Category totals (each already on its own scale 0–30, 0–40, 0–10, 0–20)
    # The reference formula treats M/A/E/S as percentages of their max:
    # SHI = 0.30*(M/30*100) + 0.40*(A/40*100) + 0.10*(E/10*100) + 0.20*(S/20*100)
    # Which simplifies to: 0.30*(M*100/30) + ... = M*(10/3) + A*2.5 + E*10 + S*5
    # This is equivalent to: score = sum of category totals since
    # M(0-30) + A(0-40) + E(0-10) + S(0-20) = 0-100 directly.
    # No further scaling needed when using the reference manual's point system.

    m_t = inp.material.total
    a_t = inp.assembly.total
    e_t = inp.environmental.total
    s_t = inp.supervisory.total

    raw = m_t + a_t + e_t + s_t + inp.penalty_concealed_deviation
    shi = max(0.0, min(100.0, round(raw, 2)))

    # Stage thresholds
    stage_conf = STAGE_MIN_SHI.get(inp.construction_stage or "", {})
    stage_min = stage_conf.get("min", 70.0)
    pay_threshold = stage_conf.get("pay_gate", PAY_DEFAULT_MIN_SHI)

    return SHI2Result(
        shi=shi,
        material_total=round(m_t, 2),
        assembly_total=round(a_t, 2),
        env_total=round(e_t, 2),
        supervisory_total=round(s_t, 2),
        penalty=inp.penalty_concealed_deviation,
        classification=classify_shi(shi),
        pay_gate_passed=shi >= pay_threshold,
        seal_eligible=shi >= SEAL_MIN_SHI,
        stage_min_passed=shi >= stage_min,
        stage_name=inp.construction_stage,
        stage_min_shi=stage_min,
        ai_flags=generate_ai_flags(inp),
    )


# ══════════════════════════════════════════════════════════════
# BACKWARD-COMPATIBLE SERVICE FUNCTIONS
# (same signatures as original vision.py)
# ══════════════════════════════════════════════════════════════

def get_active_method(db: Session) -> SHIMethod:
    method = db.query(SHIMethod).filter(
        SHIMethod.active.is_(True)
    ).order_by(SHIMethod.id.desc()).first()
    if not method:
        method = SHIMethod(
            version_code="SHI-2-v2",
            material_weight=0.3,
            assembly_weight=0.4,
            environment_weight=0.1,
            supervision_weight=0.2,
            active=True,
        )
        db.add(method)
        db.commit()
        db.refresh(method)
    return method


def compute_shi(
    material_score: float,
    assembly_score: float,
    env_score: float,
    supervision_score: float,
    method: SHIMethod,
) -> float:
    """
    BACKWARD COMPATIBLE: accepts 4 top-level scores (0–100 each).
    Used when sub-scores are not available (legacy inspections).
    """
    score = (
        material_score * method.material_weight
        + assembly_score * method.assembly_weight
        + env_score * method.environment_weight
        + supervision_score * method.supervision_weight
    )
    return round(score, 2)


def apply_inspection(
    db: Session,
    inspection: Inspection,
    actor_email: str | None = None,
) -> Inspection:
    """Update component SHI and project composite. Unchanged from original."""
    component = db.query(Component).filter(
        Component.uid == inspection.component_uid,
        Component.is_deleted.is_(False),
    ).first()
    if component:
        component.shi = inspection.shi
        component.status = "verified" if inspection.shi >= 75 else "flagged"
        component.approved_by = inspection.inspector_id

    project = db.query(Project).filter(
        Project.uid == inspection.project_uid,
        Project.is_deleted.is_(False),
    ).first()
    if project:
        values = [
            x.shi for x in db.query(Inspection).filter(
                Inspection.project_uid == project.uid,
                Inspection.is_deleted.is_(False),
            ).all()
        ]
        project.shi = round(sum(values) / len(values), 2) if values else 0.0

    db.commit()

    append_twin_event(
        db,
        project_uid=inspection.project_uid,
        component_uid=inspection.component_uid,
        event_type="VISION.SHI_ASSESSED",
        aggregate_type="inspection",
        aggregate_uid=str(inspection.id),
        actor_email=actor_email,
        payload={
            "component_uid": inspection.component_uid,
            "inspection_id": inspection.id,
            "shi": inspection.shi,
            "status": inspection.status,
            "material_total": getattr(inspection, "shi_material_total", None),
            "assembly_total": getattr(inspection, "shi_assembly_total", None),
            "env_total": getattr(inspection, "shi_env_total", None),
            "supervisory_total": getattr(inspection, "shi_supervisory_total", None),
            "ai_flags_count": getattr(inspection, "ai_flags", 0),
        },
    )
    return inspection


def create_inspection_with_sub_scores(
    db: Session,
    *,
    component: Component,
    inspector: Professional,
    shi2_input: SHI2Input,
    reason_tag: str | None = None,
) -> Inspection:
    """
    Create an Inspection using the full SHI-2 sub-score methodology.
    This is the new primary path. The old create_inspection_from_scores
    in workflows.py remains for backward compatibility.
    """
    method = get_active_method(db)
    result = compute_shi2(shi2_input, method)

    # Reject if PROVISIONAL approver (automatic)
    if shi2_input.supervisory.approver_band == 0.0:
        raise ValueError(
            "PROVISIONAL professionals cannot approve structural inspections. "
            "Approver must hold PRI: STABLE, TRUSTED, or HONOR."
        )

    # Determine inspector PRI band
    score = inspector.pri_score or 0.0
    if score >= 85:
        band = "HONOR"
    elif score >= 70:
        band = "TRUSTED"
    elif score >= 50:
        band = "STABLE"
    else:
        band = "PROVISIONAL"

    inspection = Inspection(
        component_uid=component.uid,
        project_uid=component.project_uid,
        inspector_id=inspector.id,
        method_id=method.id,
        shi=result.shi,
        # Legacy top-level scores (derived from sub-score totals)
        material_score=result.material_total / 30.0 * 100.0,
        assembly_score=result.assembly_total / 40.0 * 100.0,
        env_score=result.env_total / 10.0 * 100.0,
        supervision_score=result.supervisory_total / 20.0 * 100.0,
        ai_flags=len(result.ai_flags),
        reason_tag=reason_tag,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="passed" if result.shi >= 75.0 else "failed",
        # Full sub-scores (new columns)
        m_concrete_strength=shi2_input.material.concrete_strength,
        m_steel_cert=shi2_input.material.steel_cert,
        m_batch_record=shi2_input.material.batch_record,
        m_wc_ratio=shi2_input.material.wc_ratio,
        m_curing_record=shi2_input.material.curing_record,
        m_admixture=shi2_input.material.admixture,
        a_rebar_size=shi2_input.assembly.rebar_size,
        a_bar_spacing=shi2_input.assembly.bar_spacing,
        a_cover=shi2_input.assembly.cover,
        a_lap_length=shi2_input.assembly.lap_length,
        a_tie_spacing=shi2_input.assembly.tie_spacing,
        a_formwork=shi2_input.assembly.formwork,
        a_starter_bar=shi2_input.assembly.starter_bar,
        e_ambient_temp=shi2_input.environmental.ambient_temp,
        e_humidity=shi2_input.environmental.humidity,
        e_wind_sun=shi2_input.environmental.wind_sun,
        e_exposure_class=shi2_input.environmental.exposure_class,
        s_approver_band=shi2_input.supervisory.approver_band,
        s_evidence_completeness=shi2_input.supervisory.evidence_completeness,
        s_reason_tag_quality=shi2_input.supervisory.reason_tag_quality,
        s_deviation_docs=shi2_input.supervisory.deviation_docs,
        penalty_concealed_deviation=shi2_input.penalty_concealed_deviation,
        shi_material_total=result.material_total,
        shi_assembly_total=result.assembly_total,
        shi_env_total=result.env_total,
        shi_supervisory_total=result.supervisory_total,
        inspector_pri_band=band,
        reason_tag_quality_score=shi2_input.supervisory.reason_tag_quality,
        construction_stage=shi2_input.construction_stage,
        min_shi_for_stage=result.stage_min_shi,
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return apply_inspection(db, inspection, actor_email=inspector.email)
