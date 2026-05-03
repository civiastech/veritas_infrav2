"""
VERITAS INFRA™ — ORIGIN™ Service
Material provenance verification, supply chain management,
test record processing, and SEAL™ Gate 3 check.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import Material, Professional
from app.models.origin import (
    OriginMaterialBatch, OriginSupplier, OriginSupplyChainRecord,
    OriginTestRecord, ProvenanceStatus, SupplierTier,
)
from app.services.audit import record_audit
from app.services.twin import append_twin_event


# ── Thresholds ────────────────────────────────────────────────────────────────
STRENGTH_RATIO_FLAG     = 0.95
STRENGTH_RATIO_ETHICS   = 0.80
STRENGTH_RATIO_TIER1    = 0.60


# ── Supplier Service ──────────────────────────────────────────────────────────

class OriginSupplierService:

    @staticmethod
    def register_supplier(
        db: Session,
        name: str,
        country: str,
        material_types: list,
        city: str | None = None,
        registration_number: str | None = None,
        creator: Professional | None = None,
    ) -> OriginSupplier:
        year = datetime.now().year
        token = secrets.token_hex(3).upper()
        uid = f"SUP-{country[:3].upper()}-{year}-{token}"

        supplier = OriginSupplier(
            uid=uid,
            name=name,
            country=country,
            city=city,
            registration_number=registration_number,
            material_types=material_types,
            tier=SupplierTier.UNVERIFIED,
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

        if creator:
            record_audit(
                db, creator.email, "ORIGIN_SUPPLIER_REGISTERED",
                f"Supplier {supplier.uid} — {name}"
            )
        return supplier

    @staticmethod
    def upgrade_tier(
        db: Session,
        supplier_id: int,
        new_tier: str,
        audit_report_url: str | None,
        auditor: Professional,
    ) -> OriginSupplier:
        supplier = db.query(OriginSupplier).filter(
            OriginSupplier.id == supplier_id
        ).first()
        if not supplier:
            raise ValueError("Supplier not found")

        score = auditor.pri_score or 0
        if score < 70:
            raise PermissionError(
                "Supplier tier upgrade requires PRI: TRUSTED or HONOR"
            )

        supplier.tier = new_tier
        supplier.tier_last_assessed = datetime.now(timezone.utc)
        supplier.audit_report_url = audit_report_url
        db.commit()

        record_audit(
            db, auditor.email, "ORIGIN_SUPPLIER_TIER_UPGRADED",
            f"Supplier {supplier.uid} → {new_tier}"
        )
        return supplier


# ── Material Batch Service ────────────────────────────────────────────────────

class OriginBatchService:

    @staticmethod
    def register_batch(
        db: Session,
        batch_uid: str,
        material_type: str,
        supplier_id: int | None,
        specified_grade: str | None,
        specified_strength_mpa: float | None,
        design_standard: str | None,
        project_uid: str | None,
        actor: Professional,
        **kwargs,
    ) -> OriginMaterialBatch:
        existing = db.query(OriginMaterialBatch).filter(
            OriginMaterialBatch.batch_uid == batch_uid
        ).first()
        if existing:
            raise ValueError(
                f"Batch {batch_uid} already registered in ORIGIN™"
            )

        batch = OriginMaterialBatch(
            batch_uid=batch_uid,
            material_type=material_type,
            supplier_id=supplier_id,
            specified_grade=specified_grade,
            specified_strength_mpa=specified_strength_mpa,
            design_standard=design_standard,
            projects_used=[project_uid] if project_uid else [],
            provenance_status=ProvenanceStatus.INCOMPLETE,
            **{k: v for k, v in kwargs.items()
               if hasattr(OriginMaterialBatch, k)},
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        if project_uid:
            append_twin_event(
                db,
                project_uid=project_uid,
                event_type="ORIGIN.BATCH_REGISTERED",
                aggregate_type="origin_batch",
                aggregate_uid=str(batch.id),
                actor_email=actor.email,
                payload={
                    "batch_uid": batch_uid,
                    "material_type": material_type,
                    "specified_grade": specified_grade,
                },
            )

        record_audit(
            db, actor.email, "ORIGIN_BATCH_REGISTERED",
            f"Batch {batch_uid} registered — {material_type}"
        )
        return batch

    @staticmethod
    def add_test_record(
        db: Session,
        batch_uid: str,
        test_standard: str,
        laboratory_name: str,
        actual_value: float,
        specified_value: float,
        test_type: str,
        test_date: datetime | None,
        certificate_url: str | None,
        certificate_sha256: str | None,
        actor: Professional,
    ) -> tuple[OriginTestRecord, OriginMaterialBatch]:
        batch = db.query(OriginMaterialBatch).filter(
            OriginMaterialBatch.batch_uid == batch_uid
        ).first()
        if not batch:
            raise ValueError(f"Batch {batch_uid} not found in ORIGIN™")

        passed = actual_value >= (specified_value * STRENGTH_RATIO_FLAG)
        strength_ratio = actual_value / specified_value if specified_value else 0.0
        anomaly = strength_ratio < STRENGTH_RATIO_FLAG

        test = OriginTestRecord(
            batch_uid=batch_uid,
            batch_id=batch.id,
            test_standard=test_standard,
            laboratory_name=laboratory_name,
            specified_value=specified_value,
            actual_value=actual_value,
            test_type=test_type,
            test_date=test_date,
            certificate_url=certificate_url,
            certificate_sha256=certificate_sha256,
            passed=passed,
            strength_ratio=strength_ratio,
            anomaly_flag=anomaly,
            anomaly_description=(
                f"Strength ratio {strength_ratio:.3f} below "
                f"acceptable threshold {STRENGTH_RATIO_FLAG}"
                if anomaly else None
            ),
        )
        db.add(test)
        db.flush()

        batch.strength_ratio = strength_ratio

        if strength_ratio < STRENGTH_RATIO_FLAG:
            flags = batch.anomaly_flags or []
            flags.append({
                "test_id": test.id,
                "ratio": strength_ratio,
                "type": test_type,
                "date": test_date.isoformat() if test_date else None,
            })
            batch.anomaly_flags = flags

        if strength_ratio < STRENGTH_RATIO_ETHICS:
            batch.ethics_flag_triggered = True
            projects = batch.projects_used or []
            project_uid = projects[0] if projects else None

            from app.services.ethics import EthicsService
            EthicsService.auto_trigger_material_fraud(
                db,
                batch_uid=batch_uid,
                project_uid=project_uid,
                against_professional_id=actor.id,
                strength_ratio=strength_ratio,
                description=(
                    f"Material batch {batch_uid} ({batch.material_type}) "
                    f"tested at {actual_value:.1f} MPa against specified "
                    f"{specified_value:.1f} MPa — strength ratio "
                    f"{strength_ratio:.2f} ({strength_ratio*100:.0f}%). "
                    f"This represents a material fraud risk. "
                    f"Laboratory: {laboratory_name}, Standard: {test_standard}."
                ),
            )

        db.commit()
        record_audit(
            db, actor.email, "ORIGIN_TEST_RECORD_ADDED",
            f"Test added to batch {batch_uid}: ratio={strength_ratio:.3f}"
        )
        return test, batch

    @staticmethod
    def verify_batch(
        db: Session,
        batch_uid: str,
        verifier: Professional,
        notes: str | None = None,
    ) -> OriginMaterialBatch:
        score = verifier.pri_score or 0
        if score < 70:
            raise PermissionError(
                "ORIGIN™ batch verification requires PRI: TRUSTED or HONOR"
            )

        batch = db.query(OriginMaterialBatch).filter(
            OriginMaterialBatch.batch_uid == batch_uid
        ).first()
        if not batch:
            raise ValueError(f"Batch {batch_uid} not found")

        test_count = db.query(OriginTestRecord).filter(
            OriginTestRecord.batch_uid == batch_uid
        ).count()
        if test_count == 0:
            raise ValueError(
                f"Batch {batch_uid} has no test records. "
                "At least one laboratory test must be recorded before verification."
            )

        if batch.strength_ratio and batch.strength_ratio < STRENGTH_RATIO_ETHICS:
            raise ValueError(
                f"Batch {batch_uid} cannot be verified — strength ratio "
                f"{batch.strength_ratio:.2f} is critically below threshold. "
                "Batch must be rejected."
            )

        batch.provenance_status = ProvenanceStatus.VERIFIED
        batch.verified_by_id = verifier.id
        batch.verified_at = datetime.now(timezone.utc)
        batch.verification_notes = notes
        db.commit()

        material = db.query(Material).filter(
            Material.batch_uid == batch_uid
        ).first()
        if material:
            material.verified = True
            db.commit()

        record_audit(
            db, verifier.email, "ORIGIN_BATCH_VERIFIED",
            f"Verified batch {batch_uid}"
        )
        return batch

    @staticmethod
    def reject_batch(
        db: Session,
        batch_uid: str,
        rejection_reason: str,
        actor: Professional,
    ) -> OriginMaterialBatch:
        batch = db.query(OriginMaterialBatch).filter(
            OriginMaterialBatch.batch_uid == batch_uid
        ).first()
        if not batch:
            raise ValueError(f"Batch {batch_uid} not found")

        batch.provenance_status = ProvenanceStatus.REJECTED
        batch.rejection_reason = rejection_reason
        db.commit()

        material = db.query(Material).filter(
            Material.batch_uid == batch_uid
        ).first()
        if material:
            material.status = "rejected"
            material.suspension_reason = rejection_reason
            db.commit()

        record_audit(
            db, actor.email, "ORIGIN_BATCH_REJECTED",
            f"Rejected batch {batch_uid}: {rejection_reason}"
        )
        return batch


# ── SEAL™ Gate 3 Check ────────────────────────────────────────────────────────

class OriginSealGateService:

    @staticmethod
    def check_seal_gate(
        db: Session,
        project_uid: str,
    ) -> dict:
        failure_reasons = []

        all_batches = db.query(OriginMaterialBatch).filter(
            OriginMaterialBatch.projects_used.contains([project_uid])
        ).all()

        all_materials = db.query(Material).filter(
            Material.projects_used.contains([project_uid]),
            Material.is_deleted.is_(False),
        ).all()

        material_batch_uids = {b.batch_uid for b in all_batches}
        materials_without_origin = [
            m.batch_uid for m in all_materials
            if m.batch_uid not in material_batch_uids
        ]
        if materials_without_origin:
            failure_reasons.append(
                f"{len(materials_without_origin)} material batch(es) have no "
                f"ORIGIN™ provenance record: {', '.join(str(x) for x in materials_without_origin)}"
            )

        unverified = [
            b.batch_uid for b in all_batches
            if b.provenance_status != ProvenanceStatus.VERIFIED
        ]
        if unverified:
            failure_reasons.append(
                f"{len(unverified)} material batch(es) not yet verified: "
                f"{', '.join(unverified)}"
            )

        rejected = [
            b.batch_uid for b in all_batches
            if b.provenance_status == ProvenanceStatus.REJECTED
        ]
        if rejected:
            failure_reasons.append(
                f"{len(rejected)} rejected material batch(es) present: "
                f"{', '.join(rejected)}. Remove rejected materials from project."
            )

        ethics_flagged = [
            b.batch_uid for b in all_batches if b.ethics_flag_triggered
        ]
        if ethics_flagged:
            failure_reasons.append(
                f"Active ETHICS™ violation on material batch(es): "
                f"{', '.join(ethics_flagged)}. Resolve before certification."
            )

        return {
            "project_uid": project_uid,
            "total_material_batches": len(all_materials),
            "origin_registered": len(all_batches),
            "verified": sum(
                1 for b in all_batches
                if b.provenance_status == ProvenanceStatus.VERIFIED
            ),
            "unverified": len(unverified),
            "rejected": len(rejected),
            "ethics_flagged": len(ethics_flagged),
            "gate_passed": len(failure_reasons) == 0,
            "failure_reasons": failure_reasons,
        }
