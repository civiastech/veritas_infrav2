"""
VERITAS INFRA™ — PREFAB™ Service Layer
All business logic for component specification, deviation management,
and SEAL™ Gate 9 verification.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import (
    Component, ExecutionHold, Milestone, Payment, Professional,
)
from app.models.prefab import (
    ComponentSpec, DeviationRecord, DeviationSeverity,
    ExecutionSensitivity, PrefabLibraryEntry, generate_uid, parse_uid,
    validate_uid_format,
)
from app.schemas.prefab import (
    ComponentSpecCreate, DeviationCreate, DeviationCorrect,
    DeviationLogCloseRequest, DeviationReview, PrefabSealCheck,
)
from app.services.audit import record_audit
from app.services.twin import append_twin_event


# ── PRI Band Helpers ──────────────────────────────────────────────────────────

BAND_RANK = {"PROVISIONAL": 0, "STABLE": 1, "TRUSTED": 2, "HONOR": 3}


def _band_meets(professional_band: str, required_band: str) -> bool:
    return BAND_RANK.get(professional_band, -1) >= BAND_RANK.get(required_band, 99)


def _get_band(professional: Professional) -> str:
    """Derive PRI band from current pri_score."""
    score = professional.pri_score or 0
    if score >= 85:
        return "HONOR"
    elif score >= 70:
        return "TRUSTED"
    elif score >= 50:
        return "STABLE"
    return "PROVISIONAL"


# ── Library Service ───────────────────────────────────────────────────────────

class PrefabLibraryService:

    @staticmethod
    def list_entries(
        db: Session,
        component_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PrefabLibraryEntry], int]:
        q = db.query(PrefabLibraryEntry).filter(PrefabLibraryEntry.active.is_(True))
        if component_type:
            q = q.filter(PrefabLibraryEntry.component_type == component_type)
        total = q.count()
        items = q.order_by(PrefabLibraryEntry.usage_count.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def create_entry(
        db: Session,
        data: dict,
        creator: Professional,
    ) -> PrefabLibraryEntry:
        entry = PrefabLibraryEntry(
            **data,
            created_by_id=creator.id,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        record_audit(db, creator.email, "PREFAB_LIBRARY_CREATE",
                     f"Created library entry: {entry.name}")
        return entry


# ── ComponentSpec Service ─────────────────────────────────────────────────────

class ComponentSpecService:

    @staticmethod
    def create_spec(
        db: Session,
        data: ComponentSpecCreate,
        creator: Professional,
    ) -> ComponentSpec:
        """
        Create a structural specification for a component UID.

        Rules:
        - UID must match canonical format
        - Component UID must exist in components table
        - No duplicate spec per UID
        - HIGH/CRITICAL specs require TRUSTED+ creator
        """
        # Validate UID format
        if not validate_uid_format(data.component_uid):
            raise ValueError(
                f"Invalid UID format: '{data.component_uid}'. "
                "Required format: PROJECT_CODE/LEVEL/GRID/TYPE/SEQUENCE "
                "(e.g. BLD-IKEJA/L3/C4/COL/019)"
            )

        # Component must exist
        component = db.query(Component).filter(
            Component.uid == data.component_uid,
            Component.is_deleted.is_(False),
        ).first()
        if not component:
            raise ValueError(
                f"Component UID '{data.component_uid}' not found. "
                "Register the component first, then create its specification."
            )

        # No duplicate spec
        existing = db.query(ComponentSpec).filter(
            ComponentSpec.component_uid == data.component_uid
        ).first()
        if existing:
            raise ValueError(
                f"A specification already exists for {data.component_uid}. "
                "Use update to modify an existing spec."
            )

        # HIGH/CRITICAL needs TRUSTED+
        creator_band = _get_band(creator)
        if data.execution_sensitivity in ("HIGH", "CRITICAL"):
            if not _band_meets(creator_band, "TRUSTED"):
                raise PermissionError(
                    f"Creating {data.execution_sensitivity} sensitivity specs "
                    f"requires PRI: TRUSTED or HONOR. Your band: {creator_band}."
                )

        # Parse UID
        parsed = parse_uid(data.component_uid)

        # Handle library template
        rebar_dict = None
        if data.rebar_spec:
            rebar_dict = data.rebar_spec.model_dump(exclude_none=True)

        library_entry_id = None
        if data.library_entry_id:
            lib = db.query(PrefabLibraryEntry).filter(
                PrefabLibraryEntry.id == data.library_entry_id,
                PrefabLibraryEntry.active.is_(True),
            ).first()
            if lib:
                library_entry_id = lib.id
                lib.usage_count += 1

        spec = ComponentSpec(
            component_uid=data.component_uid,
            project_uid=data.project_uid,
            level_code=parsed.get("level"),
            grid_reference=parsed.get("grid"),
            component_type=parsed.get("type"),
            sequence_number=parsed.get("sequence"),
            specification_code=data.specification_code,
            concrete_grade=data.concrete_grade,
            concrete_fck_mpa=data.concrete_fck_mpa,
            water_cement_ratio_max=data.water_cement_ratio_max,
            cover_nominal_mm=data.cover_nominal_mm,
            cover_minimum_mm=data.cover_minimum_mm,
            exposure_class=data.exposure_class,
            design_standard=data.design_standard,
            design_life_years=data.design_life_years,
            rebar_spec=rebar_dict,
            section_width_mm=data.section_width_mm,
            section_depth_mm=data.section_depth_mm,
            element_length_mm=data.element_length_mm,
            load_path_description=data.load_path_description,
            connects_to_uids=data.connects_to_uids,
            supported_by_uid=data.supported_by_uid,
            execution_sensitivity=data.execution_sensitivity,
            sensitivity_reason=data.sensitivity_reason,
            substitute_allowed=data.substitute_allowed,
            substitute_requires_band=data.substitute_requires_band,
            library_entry_id=library_entry_id,
            is_approved=False,
        )
        db.add(spec)
        db.commit()
        db.refresh(spec)

        # Write TWIN event
        append_twin_event(
            db,
            project_uid=data.project_uid,
            component_uid=data.component_uid,
            event_type="PREFAB.SPEC_CREATED",
            aggregate_type="component_spec",
            aggregate_uid=str(spec.id),
            actor_email=creator.email,
            payload={
                "component_uid": data.component_uid,
                "execution_sensitivity": data.execution_sensitivity,
                "specification_code": data.specification_code,
                "concrete_grade": data.concrete_grade,
            },
        )

        record_audit(
            db, creator.email, "PREFAB_SPEC_CREATE",
            f"Created spec for {data.component_uid} — sensitivity: {data.execution_sensitivity}"
        )
        return spec

    @staticmethod
    def approve_spec(
        db: Session,
        spec_id: int,
        approver: Professional,
        notes: str | None = None,
    ) -> ComponentSpec:
        """
        Approve a ComponentSpec. Approver must meet the minimum band
        for the spec's sensitivity level.
        """
        spec = db.query(ComponentSpec).filter(ComponentSpec.id == spec_id).first()
        if not spec:
            raise ValueError("ComponentSpec not found")
        if spec.is_approved:
            raise ValueError("Spec is already approved")

        approver_band = _get_band(approver)
        required_band = spec.get_minimum_approver_band()
        if not _band_meets(approver_band, required_band):
            raise PermissionError(
                f"Approving {spec.execution_sensitivity} specs requires "
                f"PRI: {required_band}. Approver band: {approver_band}."
            )

        spec.is_approved = True
        spec.approved_by_id = approver.id
        spec.approved_at = datetime.now(timezone.utc)
        spec.approval_notes = notes
        db.commit()

        append_twin_event(
            db,
            project_uid=spec.project_uid,
            component_uid=spec.component_uid,
            event_type="PREFAB.SPEC_APPROVED",
            aggregate_type="component_spec",
            aggregate_uid=str(spec.id),
            actor_email=approver.email,
            payload={
                "component_uid": spec.component_uid,
                "approver_band": approver_band,
                "notes": notes,
            },
        )

        record_audit(
            db, approver.email, "PREFAB_SPEC_APPROVE",
            f"Approved spec for {spec.component_uid}"
        )
        return spec

    @staticmethod
    def get_spec_by_uid(db: Session, component_uid: str) -> ComponentSpec | None:
        return db.query(ComponentSpec).filter(
            ComponentSpec.component_uid == component_uid
        ).first()

    @staticmethod
    def list_project_specs(
        db: Session,
        project_uid: str,
        sensitivity: str | None = None,
        approved_only: bool = False,
        has_open_deviations: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[ComponentSpec], int]:
        q = db.query(ComponentSpec).filter(ComponentSpec.project_uid == project_uid)
        if sensitivity:
            q = q.filter(ComponentSpec.execution_sensitivity == sensitivity)
        if approved_only:
            q = q.filter(ComponentSpec.is_approved.is_(True))
        if has_open_deviations is not None:
            q = q.filter(ComponentSpec.has_open_deviations.is_(has_open_deviations))
        total = q.count()
        items = q.order_by(ComponentSpec.component_uid).offset(skip).limit(limit).all()
        return items, total


# ── Deviation Service ─────────────────────────────────────────────────────────

class DeviationService:

    @staticmethod
    def report_deviation(
        db: Session,
        data: DeviationCreate,
        reporter: Professional,
    ) -> DeviationRecord:
        """
        Report a structural deviation.

        Auto-triggers:
        - PAY hold for CRITICAL deviations
        - TWIN event for all deviations
        - Ethics violation flag for concealed deviations (no before photo)
        """
        # Spec must exist
        spec = db.query(ComponentSpec).filter(
            ComponentSpec.component_uid == data.component_uid
        ).first()

        engineer_review_required = data.severity in (
            DeviationSeverity.MAJOR, DeviationSeverity.CRITICAL
        )

        record = DeviationRecord(
            component_uid=data.component_uid,
            project_uid=data.project_uid,
            component_spec_id=spec.id if spec else None,
            deviation_type=data.deviation_type,
            severity=data.severity,
            description=data.description,
            measurement_data=data.measurement_data,
            discovered_by_id=reporter.id,
            discovered_at=datetime.now(timezone.utc),
            before_photo_url=data.before_photo_url,
            before_photo_sha256=data.before_photo_sha256,
            after_photo_url=data.after_photo_url,
            after_photo_sha256=data.after_photo_sha256,
            photos_verified=bool(data.before_photo_url and data.after_photo_url),
            engineer_review_required=engineer_review_required,
        )
        db.add(record)
        db.flush()

        # ── CRITICAL: trigger PAY hold ────────────────────────────────────────
        if data.severity == DeviationSeverity.CRITICAL:
            record.pay_hold_triggered = True
            # Find and lock any pending milestones for this project
            milestones = db.query(Milestone).filter(
                Milestone.project_uid == data.project_uid,
                Milestone.status == "pending",
                Milestone.is_deleted.is_(False),
            ).all()
            for m in milestones:
                m.status = "hold_deviation"

        # ── MAJOR/CRITICAL without before photo = concealed deviation ─────────
        if data.severity in (DeviationSeverity.MAJOR, DeviationSeverity.CRITICAL):
            if not data.before_photo_url:
                from app.services.ethics import EthicsService
                EthicsService.auto_trigger_concealed_deviation(
                    db,
                    deviation_id=record.id,
                    component_uid=data.component_uid,
                    project_uid=data.project_uid,
                    against_professional_id=reporter.id,
                )
                record.ethics_violation_triggered = True
                record.ethics_violation_tier = 2

        # ── Update ComponentSpec deviation counts ─────────────────────────────
        if spec:
            spec.has_open_deviations = True
            spec.deviation_count += 1

        db.commit()

        # ── TWIN event ────────────────────────────────────────────────────────
        twin_event = append_twin_event(
            db,
            project_uid=data.project_uid,
            component_uid=data.component_uid,
            event_type=f"PREFAB.DEVIATION_{data.severity}",
            aggregate_type="deviation_record",
            aggregate_uid=str(record.id),
            actor_email=reporter.email,
            payload={
                "deviation_type": data.deviation_type,
                "severity": data.severity,
                "description": data.description,
                "engineer_review_required": engineer_review_required,
                "pay_hold_triggered": record.pay_hold_triggered,
                "photos_submitted": record.photos_verified,
            },
        )
        record.twin_event_id = twin_event.id
        db.commit()

        record_audit(
            db, reporter.email, "PREFAB_DEVIATION_REPORT",
            f"{data.severity} deviation on {data.component_uid}: {data.deviation_type}"
        )
        return record

    @staticmethod
    def mark_corrected(
        db: Session,
        deviation_id: int,
        data: DeviationCorrect,
        actor: Professional,
    ) -> DeviationRecord:
        record = db.query(DeviationRecord).filter(
            DeviationRecord.id == deviation_id
        ).first()
        if not record:
            raise ValueError("Deviation record not found")
        if record.closed:
            raise ValueError("Deviation is already closed")

        record.corrected = True
        record.correction_description = data.correction_description
        record.corrected_at = datetime.now(timezone.utc)
        record.after_photo_url = data.after_photo_url
        record.after_photo_sha256 = data.after_photo_sha256
        record.photos_verified = True

        # MINOR deviations auto-close on correction
        if record.severity == DeviationSeverity.MINOR:
            record.closed = True
            record.closed_by_id = actor.id
            record.closed_at = datetime.now(timezone.utc)
            DeviationService._refresh_spec_flags(db, record.component_uid)

        db.commit()

        append_twin_event(
            db,
            project_uid=record.project_uid,
            component_uid=record.component_uid,
            event_type="PREFAB.DEVIATION_CORRECTED",
            aggregate_type="deviation_record",
            aggregate_uid=str(record.id),
            actor_email=actor.email,
            payload={
                "severity": record.severity,
                "auto_closed": record.severity == DeviationSeverity.MINOR,
            },
        )
        record_audit(
            db, actor.email, "PREFAB_DEVIATION_CORRECTED",
            f"Correction recorded for deviation {deviation_id} on {record.component_uid}"
        )
        return record

    @staticmethod
    def review_deviation(
        db: Session,
        deviation_id: int,
        data: DeviationReview,
        reviewer: Professional,
    ) -> DeviationRecord:
        """
        Engineer reviews a MAJOR or CRITICAL deviation.
        Reviewer must meet the minimum band for the severity level.
        """
        record = db.query(DeviationRecord).filter(
            DeviationRecord.id == deviation_id
        ).first()
        if not record:
            raise ValueError("Deviation record not found")
        if not record.engineer_review_required:
            raise ValueError("This deviation does not require engineer review")
        if record.reviewed_by_id:
            raise ValueError("Deviation already reviewed")

        # Band check
        reviewer_band = _get_band(reviewer)
        required = record.minimum_reviewer_band
        if not _band_meets(reviewer_band, required):
            raise PermissionError(
                f"Reviewing {record.severity} deviations requires "
                f"PRI: {required}. Your band: {reviewer_band}."
            )

        record.reviewed_by_id = reviewer.id
        record.reviewed_at = datetime.now(timezone.utc)
        record.review_decision = data.review_decision
        record.review_notes = data.review_notes

        if data.review_decision == "accepted":
            record.closed = True
            record.closed_by_id = reviewer.id
            record.closed_at = datetime.now(timezone.utc)
            DeviationService._refresh_spec_flags(db, record.component_uid)

        db.commit()

        append_twin_event(
            db,
            project_uid=record.project_uid,
            component_uid=record.component_uid,
            event_type="PREFAB.DEVIATION_REVIEWED",
            aggregate_type="deviation_record",
            aggregate_uid=str(record.id),
            actor_email=reviewer.email,
            payload={
                "severity": record.severity,
                "decision": data.review_decision,
                "reviewer_band": reviewer_band,
            },
        )
        record_audit(
            db, reviewer.email, "PREFAB_DEVIATION_REVIEW",
            f"Reviewed deviation {deviation_id}: {data.review_decision}"
        )
        return record

    @staticmethod
    def close_deviation_log(
        db: Session,
        spec_id: int,
        data: DeviationLogCloseRequest,
        closer: Professional,
    ) -> ComponentSpec:
        """
        Close the deviation log for a component spec.
        This is SEAL™ Gate 9 — required before certification.
        All deviations must be individually closed first.
        """
        spec = db.query(ComponentSpec).filter(ComponentSpec.id == spec_id).first()
        if not spec:
            raise ValueError("ComponentSpec not found")
        if spec.deviation_log_closed:
            raise ValueError("Deviation log is already closed")

        # All deviations must be closed
        open_deviations = db.query(DeviationRecord).filter(
            DeviationRecord.component_uid == spec.component_uid,
            DeviationRecord.closed.is_(False),
        ).count()
        if open_deviations > 0:
            raise ValueError(
                f"Cannot close deviation log: {open_deviations} open "
                f"deviation(s) must be resolved first."
            )

        # Closer must be TRUSTED+ for HIGH/CRITICAL specs
        closer_band = _get_band(closer)
        if spec.execution_sensitivity in ("HIGH", "CRITICAL"):
            if not _band_meets(closer_band, "TRUSTED"):
                raise PermissionError(
                    "Closing deviation log on HIGH/CRITICAL components "
                    f"requires PRI: TRUSTED or HONOR. Your band: {closer_band}."
                )

        spec.deviation_log_closed = True
        spec.deviation_log_closed_by_id = closer.id
        spec.deviation_log_closed_at = datetime.now(timezone.utc)
        spec.deviation_log_notes = data.notes
        db.commit()

        append_twin_event(
            db,
            project_uid=spec.project_uid,
            component_uid=spec.component_uid,
            event_type="PREFAB.DEVIATION_LOG_CLOSED",
            aggregate_type="component_spec",
            aggregate_uid=str(spec.id),
            actor_email=closer.email,
            payload={"component_uid": spec.component_uid, "notes": data.notes},
        )
        record_audit(
            db, closer.email, "PREFAB_DEVIATION_LOG_CLOSE",
            f"Closed deviation log for {spec.component_uid}"
        )
        return spec

    @staticmethod
    def _refresh_spec_flags(db: Session, component_uid: str) -> None:
        """Recalculate has_open_deviations on the ComponentSpec."""
        spec = db.query(ComponentSpec).filter(
            ComponentSpec.component_uid == component_uid
        ).first()
        if not spec:
            return
        open_count = db.query(DeviationRecord).filter(
            DeviationRecord.component_uid == component_uid,
            DeviationRecord.closed.is_(False),
        ).count()
        spec.has_open_deviations = open_count > 0
        db.commit()


# ── SEAL Gate 9 Check ─────────────────────────────────────────────────────────

class PrefabSealGateService:

    @staticmethod
    def check_seal_gate(db: Session, project_uid: str) -> PrefabSealCheck:
        """
        SEAL™ Gate 9: PREFAB™ deviation log closed with engineer sign-off.

        Checks:
        1. All components have a ComponentSpec
        2. All ComponentSpecs are approved
        3. All deviation logs are closed (no open deviations)
        """
        failure_reasons = []

        # Count all project components
        total_components = db.query(Component).filter(
            Component.project_uid == project_uid,
            Component.is_deleted.is_(False),
        ).count()

        # Count specs
        specs_created = db.query(ComponentSpec).filter(
            ComponentSpec.project_uid == project_uid
        ).count()

        specs_approved = db.query(ComponentSpec).filter(
            ComponentSpec.project_uid == project_uid,
            ComponentSpec.is_approved.is_(True),
        ).count()

        deviation_logs_closed = db.query(ComponentSpec).filter(
            ComponentSpec.project_uid == project_uid,
            ComponentSpec.deviation_log_closed.is_(True),
        ).count()

        open_deviations = db.query(DeviationRecord).filter(
            DeviationRecord.project_uid == project_uid,
            DeviationRecord.closed.is_(False),
        ).count()

        # Evaluate gate
        if specs_created < total_components:
            missing = total_components - specs_created
            failure_reasons.append(
                f"PREFAB™ specifications missing for {missing} component(s). "
                "All components require a specification before SEAL™."
            )

        if specs_approved < specs_created:
            unapproved = specs_created - specs_approved
            failure_reasons.append(
                f"{unapproved} component specification(s) not yet approved by "
                "a TRUSTED+ engineer."
            )

        if open_deviations > 0:
            failure_reasons.append(
                f"{open_deviations} open deviation record(s) must be resolved "
                "and deviation logs closed before SEAL™ can be issued."
            )

        if deviation_logs_closed < specs_created and open_deviations == 0:
            not_closed = specs_created - deviation_logs_closed
            failure_reasons.append(
                f"{not_closed} component deviation log(s) not formally closed. "
                "Run close-deviation-log on all components even with zero deviations."
            )

        return PrefabSealCheck(
            project_uid=project_uid,
            total_components=total_components,
            specs_created=specs_created,
            specs_approved=specs_approved,
            deviation_logs_closed=deviation_logs_closed,
            open_deviations=open_deviations,
            gate_passed=len(failure_reasons) == 0,
            failure_reasons=failure_reasons,
        )
