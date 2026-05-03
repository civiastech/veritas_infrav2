"""
VERITAS INFRA™ — ETHICS™ Service
Complete violation management: creation, consequence application,
auto-trigger from other modules, panel review, and appeal.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import Milestone, Professional
from app.models.ethics import (
    EthicsProbationRecord, EthicsViolation, EthicsWhistleblowerReport,
    ViolationCategory, ViolationStatus, ViolationTier,
)
from app.services.audit import record_audit
from app.services.twin import append_twin_event


# ── Consequence Tables ────────────────────────────────────────────────────────

TIER_CONSEQUENCES: dict[str, dict] = {
    ViolationTier.TIER_1: {
        "pri_deduction": -100.0,
        "platform_action": "banned",
        "criminal_referral": True,
        "public_record": True,
        "lex_escalation": True,
        "consequences": [
            "band_revocation",
            "platform_ban",
            "criminal_referral",
            "public_record",
            "lex_escalation",
        ],
    },
    ViolationTier.TIER_2: {
        "pri_deduction": -25.0,
        "platform_action": "suspended",
        "probation_months": 12,
        "consequences": [
            "pri_deduction",
            "band_downgrade",
            "pay_hold",
            "platform_suspension",
            "probation",
            "mandatory_recertify",
            "lex_escalation",
        ],
    },
    ViolationTier.TIER_3: {
        "pri_deduction": -5.0,
        "platform_action": "none",
        "consequences": [
            "pri_deduction",
            "remediation_plan",
        ],
    },
}


def _generate_violation_uid() -> str:
    year = datetime.now().year
    token = secrets.token_hex(3).upper()
    return f"ETH-{year}-{token}"


def _get_band(score: float) -> str:
    if score >= 85:
        return "HONOR"
    elif score >= 70:
        return "TRUSTED"
    elif score >= 50:
        return "STABLE"
    return "PROVISIONAL"


# ── Core Violation Service ────────────────────────────────────────────────────

class EthicsService:

    @staticmethod
    def create_violation(
        db: Session,
        tier: str,
        category: str,
        description: str,
        *,
        against_professional_id: int | None = None,
        against_firm: str | None = None,
        reported_by_id: int | None = None,
        auto_trigger_source: str | None = None,
        project_uid: str | None = None,
        component_uid: str | None = None,
        reference_record_type: str | None = None,
        reference_record_id: int | None = None,
        supporting_evidence: dict | None = None,
        twin_event_hash: str | None = None,
        actor_email: str = "system",
    ) -> EthicsViolation:
        tier_conf = TIER_CONSEQUENCES.get(tier, {})

        violation = EthicsViolation(
            uid=_generate_violation_uid(),
            tier=tier,
            category=category,
            description=description,
            against_professional_id=against_professional_id,
            against_firm=against_firm,
            reported_by_id=reported_by_id,
            reported_by_system=auto_trigger_source is not None,
            auto_trigger_source=auto_trigger_source,
            project_uid=project_uid,
            component_uid=component_uid,
            reference_record_type=reference_record_type,
            reference_record_id=reference_record_id,
            supporting_evidence=supporting_evidence,
            twin_event_hash=twin_event_hash,
            status=ViolationStatus.REPORTED,
            consequences_applied=[],
            is_public_record=tier == ViolationTier.TIER_1,
        )
        db.add(violation)
        db.flush()

        if tier in (ViolationTier.TIER_1, ViolationTier.TIER_2):
            EthicsService._apply_consequences(
                db, violation, against_professional_id, tier_conf
            )

        db.commit()

        if project_uid:
            append_twin_event(
                db,
                project_uid=project_uid,
                component_uid=component_uid,
                event_type=f"ETHICS.VIOLATION_{tier}_CREATED",
                aggregate_type="ethics_violation",
                aggregate_uid=str(violation.id),
                actor_email=actor_email,
                payload={
                    "uid": violation.uid,
                    "tier": tier,
                    "category": category,
                    "against_professional_id": against_professional_id,
                    "consequences": tier_conf.get("consequences", []),
                },
            )

        record_audit(
            db, actor_email,
            f"ETHICS_VIOLATION_CREATED_{tier}",
            f"Ethics violation {violation.uid} — {category}"
        )
        return violation

    @staticmethod
    def _apply_consequences(
        db: Session,
        violation: EthicsViolation,
        professional_id: int | None,
        tier_conf: dict,
    ) -> None:
        if not professional_id:
            return

        professional = db.query(Professional).filter(
            Professional.id == professional_id
        ).first()
        if not professional:
            return

        consequences_applied = []
        band_before = _get_band(professional.pri_score or 0)

        deduction = tier_conf.get("pri_deduction", 0.0)
        if deduction != 0:
            new_score = max(0.0, (professional.pri_score or 0) + deduction)
            violation.pri_deduction_applied = deduction
            violation.band_before = band_before
            professional.pri_score = new_score
            violation.band_after = _get_band(new_score)
            consequences_applied.append("pri_deduction")

        if "pay_hold" in tier_conf.get("consequences", []):
            milestones = db.query(Milestone).filter(
                Milestone.project_uid == violation.project_uid,
                Milestone.status == "pending",
                Milestone.is_deleted.is_(False),
            ).all() if violation.project_uid else []
            for m in milestones:
                m.status = "hold_ethics"
            if milestones:
                violation.pay_hold_triggered = True
            consequences_applied.append("pay_hold")

        platform_action = tier_conf.get("platform_action", "none")
        violation.platform_action = platform_action
        if platform_action == "banned":
            professional.active = False
            consequences_applied.append("platform_ban")
        elif platform_action == "suspended":
            consequences_applied.append("platform_suspension")

        if tier_conf.get("criminal_referral"):
            violation.criminal_referral_issued = True
            consequences_applied.append("criminal_referral")

        if "probation" in tier_conf.get("consequences", []):
            months = tier_conf.get("probation_months", 12)
            now = datetime.now(timezone.utc)
            probation = EthicsProbationRecord(
                professional_id=professional_id,
                violation_id=violation.id,
                starts_at=now,
                ends_at=now + timedelta(days=30 * months),
                active=True,
                blocked_from_critical_approval=True,
                band_advancement_blocked=True,
                mandatory_recertification_by=now + timedelta(days=90),
            )
            db.add(probation)
            consequences_applied.append("probation")

        violation.consequences_applied = consequences_applied
        db.flush()

    @staticmethod
    def record_panel_decision(
        db: Session,
        violation_id: int,
        decision: str,
        notes: str,
        panel_member: Professional,
    ) -> EthicsViolation:
        violation = db.query(EthicsViolation).filter(
            EthicsViolation.id == violation_id
        ).first()
        if not violation:
            raise ValueError("Violation not found")
        if violation.panel_decision is not None:
            raise ValueError("Panel decision already recorded")

        band = _get_band(panel_member.pri_score or 0)
        if violation.tier == ViolationTier.TIER_1 and band != "HONOR":
            raise PermissionError(
                "Tier 1 violations require HONOR band panel member"
            )
        elif violation.tier == ViolationTier.TIER_2 and band not in ("TRUSTED", "HONOR"):
            raise PermissionError(
                "Tier 2 violations require TRUSTED or HONOR band panel member"
            )

        violation.panel_decision = decision
        violation.panel_notes = notes
        violation.panel_decision_by_id = panel_member.id
        violation.panel_decision_at = datetime.now(timezone.utc)
        violation.status = (
            ViolationStatus.UPHELD if decision == "upheld"
            else ViolationStatus.DISMISSED
        )

        if (decision == "upheld"
                and violation.tier == ViolationTier.TIER_3
                and not violation.consequences_applied):
            tier_conf = TIER_CONSEQUENCES[ViolationTier.TIER_3]
            EthicsService._apply_consequences(
                db, violation, violation.against_professional_id, tier_conf
            )

        db.commit()
        record_audit(
            db, panel_member.email,
            "ETHICS_PANEL_DECISION",
            f"Panel decision '{decision}' on {violation.uid}"
        )
        return violation

    @staticmethod
    def check_professional_violations(
        db: Session,
        professional_id: int,
    ) -> dict:
        tier1_open = db.query(EthicsViolation).filter(
            EthicsViolation.against_professional_id == professional_id,
            EthicsViolation.tier == ViolationTier.TIER_1,
            EthicsViolation.status.in_([
                ViolationStatus.REPORTED,
                ViolationStatus.UNDER_REVIEW,
                ViolationStatus.UPHELD,
            ]),
        ).count()

        tier2_open = db.query(EthicsViolation).filter(
            EthicsViolation.against_professional_id == professional_id,
            EthicsViolation.tier == ViolationTier.TIER_2,
            EthicsViolation.status.in_([
                ViolationStatus.REPORTED,
                ViolationStatus.UNDER_REVIEW,
                ViolationStatus.UPHELD,
            ]),
        ).count()

        on_probation = db.query(EthicsProbationRecord).filter(
            EthicsProbationRecord.professional_id == professional_id,
            EthicsProbationRecord.active.is_(True),
        ).count()

        return {
            "professional_id": professional_id,
            "tier1_open": tier1_open,
            "tier2_open": tier2_open,
            "on_probation": on_probation > 0,
            "blocks_critical_approval": tier1_open > 0 or tier2_open > 0 or on_probation > 0,
            "blocks_seal_gate_4": tier1_open > 0 or tier2_open > 0,
        }

    @staticmethod
    def check_project_violations(
        db: Session,
        project_uid: str,
    ) -> dict:
        tier1 = db.query(EthicsViolation).filter(
            EthicsViolation.project_uid == project_uid,
            EthicsViolation.tier == ViolationTier.TIER_1,
            EthicsViolation.status.notin_([
                ViolationStatus.DISMISSED, ViolationStatus.CLOSED
            ]),
        ).count()

        tier2 = db.query(EthicsViolation).filter(
            EthicsViolation.project_uid == project_uid,
            EthicsViolation.tier == ViolationTier.TIER_2,
            EthicsViolation.status.notin_([
                ViolationStatus.DISMISSED, ViolationStatus.CLOSED
            ]),
        ).count()

        return {
            "project_uid": project_uid,
            "tier1_violations": tier1,
            "tier2_violations": tier2,
            "gate_4_passed": tier1 == 0 and tier2 == 0,
            "failure_reason": (
                None if (tier1 == 0 and tier2 == 0)
                else f"{tier1} Tier-1 and {tier2} Tier-2 open ethics violations "
                     "must be resolved before SEAL™ can be issued."
            ),
        }

    @staticmethod
    def auto_trigger_concealed_deviation(
        db: Session,
        deviation_id: int,
        component_uid: str,
        project_uid: str,
        against_professional_id: int,
        twin_event_hash: str | None = None,
    ) -> EthicsViolation:
        return EthicsService.create_violation(
            db,
            tier=ViolationTier.TIER_2,
            category=ViolationCategory.CONCEALED_DEVIATION,
            description=(
                f"CAPTURE-LARGE Element 4 violation: MAJOR or CRITICAL structural "
                f"deviation on component {component_uid} was submitted without the "
                "mandatory Before/After Correction Photo Pair. This constitutes "
                "concealment of a structural correction under VISC Protocol 4.2."
            ),
            against_professional_id=against_professional_id,
            auto_trigger_source="DEVIATION_SERVICE",
            project_uid=project_uid,
            component_uid=component_uid,
            reference_record_type="deviation_record",
            reference_record_id=deviation_id,
            twin_event_hash=twin_event_hash,
            actor_email="system:deviation_service",
        )

    @staticmethod
    def auto_trigger_material_fraud(
        db: Session,
        batch_uid: str,
        project_uid: str | None,
        against_professional_id: int,
        strength_ratio: float,
        description: str,
    ) -> EthicsViolation:
        tier = (
            ViolationTier.TIER_1 if strength_ratio < 0.60
            else ViolationTier.TIER_2
        )
        return EthicsService.create_violation(
            db,
            tier=tier,
            category=ViolationCategory.MATERIAL_FRAUD,
            description=description,
            against_professional_id=against_professional_id,
            auto_trigger_source="ORIGIN_SERVICE",
            project_uid=project_uid,
            reference_record_type="origin_material_batch",
            supporting_evidence={
                "batch_uid": batch_uid,
                "strength_ratio": strength_ratio,
            },
            actor_email="system:origin_service",
        )


# ── Whistleblower Service ─────────────────────────────────────────────────────

class WhistleblowerService:

    @staticmethod
    def submit_report(
        db: Session,
        reporter_id: int | None,
        anonymous: bool,
        tier_suspected: str,
        category_suspected: str,
        description: str,
        against_professional_id: int | None = None,
        project_uid: str | None = None,
        evidence_urls: list | None = None,
    ) -> EthicsWhistleblowerReport:
        report = EthicsWhistleblowerReport(
            reporter_id=None if anonymous else reporter_id,
            anonymous=anonymous,
            violation_tier_suspected=tier_suspected,
            category_suspected=category_suspected,
            against_professional_id=against_professional_id,
            project_uid=project_uid,
            description=description,
            evidence_urls=evidence_urls,
            status="received",
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def convert_to_violation(
        db: Session,
        report_id: int,
        reviewer: Professional,
    ) -> tuple[EthicsWhistleblowerReport, EthicsViolation]:
        report = db.query(EthicsWhistleblowerReport).filter(
            EthicsWhistleblowerReport.id == report_id
        ).first()
        if not report:
            raise ValueError("Report not found")

        violation = EthicsService.create_violation(
            db,
            tier=report.violation_tier_suspected,
            category=report.category_suspected,
            description=report.description,
            against_professional_id=report.against_professional_id,
            reported_by_id=report.reporter_id,
            project_uid=report.project_uid,
            actor_email=reviewer.email,
        )

        report.converted_to_violation_id = violation.id
        report.status = "converted"
        db.commit()
        return report, violation
