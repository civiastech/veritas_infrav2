"""
VERITAS INFRA™ — ETHICS™ Module Models
The immune system of the platform. Violation records, tier classification,
auto-trigger conditions, whistleblower protection, and PRI consequences.

Three tiers:
  Tier 1 — CATASTROPHIC: collapse, falsification, criminal fraud.
            Consequences: HONOR automatic revocation, criminal referral,
            permanent platform ban, LEX™ escalation, public record.

  Tier 2 — SERIOUS: concealed deviations, false declarations,
            ghost supervision, procurement fraud.
            Consequences: TRUSTED downgrade, PAY™ hold, 12-month probation,
            mandatory re-certification, LEX™ referral.

  Tier 3 — MINOR: incomplete records, procedural failures,
            inadequate supervision logs.
            Consequences: PRI −5, remediation plan required,
            30-day compliance review.

New tables: ethics_violations, ethics_whistleblower_reports,
            ethics_probation_records, ethics_panel_decisions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# ── Enumerations ──────────────────────────────────────────────────────────────

class ViolationTier(str, PyEnum):
    TIER_1 = "TIER_1"   # Catastrophic — criminal referral threshold
    TIER_2 = "TIER_2"   # Serious — probation threshold
    TIER_3 = "TIER_3"   # Minor — remediation threshold


class ViolationCategory(str, PyEnum):
    # Tier 1 categories
    STRUCTURAL_COLLAPSE_CAUSE     = "structural_collapse_cause"
    EVIDENCE_FALSIFICATION        = "evidence_falsification"
    MATERIAL_FRAUD                = "material_fraud"
    CRIMINAL_PROCUREMENT_FRAUD    = "criminal_procurement_fraud"
    PROFESSIONAL_IMPERSONATION    = "professional_impersonation"
    # Tier 2 categories
    CONCEALED_DEVIATION           = "concealed_deviation"
    FALSE_DECLARATION             = "false_declaration"
    GHOST_SUPERVISION             = "ghost_supervision"
    UNAUTHORISED_SUBSTITUTION     = "unauthorised_substitution"
    PROCUREMENT_COLLUSION         = "procurement_collusion"
    BRIBERY_ATTEMPT               = "bribery_attempt"
    INSPECTION_AVOIDANCE          = "inspection_avoidance"
    # Tier 3 categories
    INCOMPLETE_EVIDENCE           = "incomplete_evidence"
    INADEQUATE_SUPERVISION_LOG    = "inadequate_supervision_log"
    LATE_EVIDENCE_SUBMISSION      = "late_evidence_submission"
    PROCEDURAL_NON_COMPLIANCE     = "procedural_non_compliance"
    MINOR_RECORD_FALSIFICATION    = "minor_record_falsification"


class ViolationStatus(str, PyEnum):
    REPORTED     = "reported"
    UNDER_REVIEW = "under_review"
    UPHELD       = "upheld"
    DISMISSED    = "dismissed"
    APPEALED     = "appealed"
    CLOSED       = "closed"


class ConsequenceType(str, PyEnum):
    PRI_DEDUCTION           = "pri_deduction"
    BAND_DOWNGRADE          = "band_downgrade"
    BAND_REVOCATION         = "band_revocation"
    PAY_HOLD                = "pay_hold"
    PLATFORM_SUSPENSION     = "platform_suspension"
    PLATFORM_BAN            = "platform_ban"
    PROBATION               = "probation"
    MANDATORY_RECERTIFY     = "mandatory_recertify"
    CRIMINAL_REFERRAL       = "criminal_referral"
    PUBLIC_RECORD           = "public_record"
    LEX_ESCALATION          = "lex_escalation"
    REMEDIATION_PLAN        = "remediation_plan"


# ── Ethics Violation ──────────────────────────────────────────────────────────

class EthicsViolation(Base):
    """
    An ethics violation record. Once created, this record is permanent.
    Only the status and panel decision fields may be updated.
    The core violation facts are immutable — they cannot be erased.
    """
    __tablename__ = "ethics_violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    uid: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    tier: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False)

    # ── Parties ────────────────────────────────────────────────────────────────
    against_professional_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True, index=True
    )
    against_firm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reported_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    reported_by_system: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_trigger_source: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True
    )

    # ── Context ────────────────────────────────────────────────────────────────
    project_uid: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    component_uid: Mapped[Optional[str]] = mapped_column(
        String(180), nullable=True
    )
    reference_record_type: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True
    )
    reference_record_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # ── Evidence ───────────────────────────────────────────────────────────────
    description: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    evidence_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    twin_event_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )

    # ── Status & Decision ──────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(30), default=ViolationStatus.REPORTED, index=True
    )
    panel_decision: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    panel_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    panel_decision_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    panel_decision_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Consequences Applied ───────────────────────────────────────────────────
    consequences_applied: Mapped[list] = mapped_column(JSON, default=list)
    pri_deduction_applied: Mapped[float] = mapped_column(Float, default=0.0)
    band_before: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    band_after: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pay_hold_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    platform_action: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    criminal_referral_issued: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Appeal ────────────────────────────────────────────────────────────────
    appealed: Mapped[bool] = mapped_column(Boolean, default=False)
    appeal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    appeal_outcome: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )

    # ── Public Record (Tier 1 only) ───────────────────────────────────────────
    is_public_record: Mapped[bool] = mapped_column(Boolean, default=False)
    public_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_ethics_against_professional", "against_professional_id", "tier"),
        Index("ix_ethics_status_tier", "status", "tier"),
        Index("ix_ethics_project", "project_uid"),
    )


# ── Whistleblower Report ──────────────────────────────────────────────────────

class EthicsWhistleblowerReport(Base):
    """
    Confidential report submitted by a professional about another.
    Reporter identity is never disclosed to the accused party.
    """
    __tablename__ = "ethics_whistleblower_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    reporter_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    violation_tier_suspected: Mapped[str] = mapped_column(String(10), nullable=False)
    category_suspected: Mapped[str] = mapped_column(String(80), nullable=False)
    against_professional_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("professionals.id"), nullable=True
    )
    project_uid: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    converted_to_violation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ethics_violations.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="received"
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    protection_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    protection_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ── Probation Record ──────────────────────────────────────────────────────────

class EthicsProbationRecord(Base):
    """
    Tier 2 violations result in a 12-month probation period.
    During probation, the professional may not approve CRITICAL components
    and cannot advance PRI band.
    """
    __tablename__ = "ethics_probation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id"), nullable=False, index=True
    )
    violation_id: Mapped[int] = mapped_column(
        ForeignKey("ethics_violations.id"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    blocked_from_critical_approval: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    band_advancement_blocked: Mapped[bool] = mapped_column(Boolean, default=True)
    mandatory_recertification_by: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recertification_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    terminated_early: Mapped[bool] = mapped_column(Boolean, default=False)
    termination_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_probation_professional_active",
              "professional_id", "active"),
    )
