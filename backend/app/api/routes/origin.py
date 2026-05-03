"""
VERITAS INFRA™ — ORIGIN™ API Router
"""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Professional
from app.models.origin import OriginMaterialBatch, OriginSupplier, OriginTestRecord
from app.services.origin import (
    OriginBatchService, OriginSealGateService, OriginSupplierService,
)

router = APIRouter(prefix="/origin", tags=["ORIGIN™ — Material Provenance"])


class SupplierCreate(BaseModel):
    name: str = Field(min_length=2)
    country: str
    material_types: list[str]
    city: Optional[str] = None
    registration_number: Optional[str] = None


class SupplierTierUpgrade(BaseModel):
    new_tier: str
    audit_report_url: Optional[str] = None


class BatchRegister(BaseModel):
    batch_uid: str
    material_type: str
    supplier_id: Optional[int] = None
    specified_grade: Optional[str] = None
    specified_strength_mpa: Optional[float] = None
    design_standard: Optional[str] = None
    project_uid: Optional[str] = None
    mill_cert_url: Optional[str] = None
    mill_cert_sha256: Optional[str] = None
    delivery_note_number: Optional[str] = None


class TestRecordAdd(BaseModel):
    batch_uid: str
    test_standard: str
    laboratory_name: str
    actual_value: float
    specified_value: float
    test_type: str
    test_date: Optional[datetime] = None
    certificate_url: Optional[str] = None
    certificate_sha256: Optional[str] = None


class BatchVerify(BaseModel):
    notes: Optional[str] = None


class BatchReject(BaseModel):
    rejection_reason: str = Field(min_length=10)


# ── Suppliers ─────────────────────────────────────────────────────────────────

@router.post("/suppliers", status_code=201,
             summary="Register a material supplier")
def register_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:write")),
):
    supplier = OriginSupplierService.register_supplier(
        db, payload.name, payload.country, payload.material_types,
        payload.city, payload.registration_number, current_user,
    )
    return {"supplier_id": supplier.id, "uid": supplier.uid,
            "tier": supplier.tier}


@router.post("/suppliers/{supplier_id}/upgrade-tier",
             summary="Upgrade supplier tier after audit")
def upgrade_supplier_tier(
    supplier_id: int,
    payload: SupplierTierUpgrade,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:approve")),
):
    try:
        s = OriginSupplierService.upgrade_tier(
            db, supplier_id, payload.new_tier,
            payload.audit_report_url, current_user,
        )
        return {"supplier_id": s.id, "uid": s.uid, "tier": s.tier}
    except (ValueError, PermissionError) as e:
        raise HTTPException(422, str(e))


@router.get("/suppliers",
            summary="List registered suppliers")
def list_suppliers(
    tier: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:read")),
):
    q = db.query(OriginSupplier)
    if tier:
        q = q.filter(OriginSupplier.tier == tier)
    if country:
        q = q.filter(OriginSupplier.country == country)
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return {"total": total, "items": [
        {"id": s.id, "uid": s.uid, "name": s.name, "country": s.country,
         "tier": s.tier, "material_types": s.material_types}
        for s in items
    ]}


# ── Batches ───────────────────────────────────────────────────────────────────

@router.post("/batches", status_code=201,
             summary="Register a material batch")
def register_batch(
    payload: BatchRegister,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:write")),
):
    try:
        batch = OriginBatchService.register_batch(
            db, payload.batch_uid, payload.material_type,
            payload.supplier_id, payload.specified_grade,
            payload.specified_strength_mpa, payload.design_standard,
            payload.project_uid, current_user,
            mill_cert_url=payload.mill_cert_url,
            mill_cert_sha256=payload.mill_cert_sha256,
            delivery_note_number=payload.delivery_note_number,
        )
        return {"batch_id": batch.id, "batch_uid": batch.batch_uid,
                "provenance_status": batch.provenance_status}
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("/batches/test-record", status_code=201,
             summary="Add laboratory test result to a batch")
def add_test_record(
    payload: TestRecordAdd,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:write")),
):
    try:
        test, batch = OriginBatchService.add_test_record(
            db,
            batch_uid=payload.batch_uid,
            test_standard=payload.test_standard,
            laboratory_name=payload.laboratory_name,
            actual_value=payload.actual_value,
            specified_value=payload.specified_value,
            test_type=payload.test_type,
            test_date=payload.test_date,
            certificate_url=payload.certificate_url,
            certificate_sha256=payload.certificate_sha256,
            actor=current_user,
        )
        return {
            "test_id": test.id,
            "batch_uid": payload.batch_uid,
            "passed": test.passed,
            "strength_ratio": test.strength_ratio,
            "anomaly_flag": test.anomaly_flag,
            "ethics_flag_triggered": batch.ethics_flag_triggered,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/batches/{batch_uid}/verify",
             summary="Verify a material batch provenance")
def verify_batch(
    batch_uid: str,
    payload: BatchVerify,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:approve")),
):
    try:
        batch = OriginBatchService.verify_batch(
            db, batch_uid, current_user, payload.notes
        )
        return {"batch_uid": batch.batch_uid,
                "provenance_status": batch.provenance_status}
    except (ValueError, PermissionError) as e:
        raise HTTPException(422, str(e))


@router.post("/batches/{batch_uid}/reject",
             summary="Reject a material batch")
def reject_batch(
    batch_uid: str,
    payload: BatchReject,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:approve")),
):
    try:
        batch = OriginBatchService.reject_batch(
            db, batch_uid, payload.rejection_reason, current_user
        )
        return {"batch_uid": batch.batch_uid,
                "provenance_status": batch.provenance_status}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/batches/{batch_uid}",
            summary="Get batch provenance record")
def get_batch(
    batch_uid: str,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:read")),
):
    batch = db.query(OriginMaterialBatch).filter(
        OriginMaterialBatch.batch_uid == batch_uid
    ).first()
    if not batch:
        raise HTTPException(404, f"Batch {batch_uid} not found")
    tests = db.query(OriginTestRecord).filter(
        OriginTestRecord.batch_uid == batch_uid
    ).all()
    return {
        "batch_uid": batch.batch_uid,
        "material_type": batch.material_type,
        "provenance_status": batch.provenance_status,
        "specified_grade": batch.specified_grade,
        "strength_ratio": batch.strength_ratio,
        "anomaly_flags": batch.anomaly_flags,
        "ethics_flag_triggered": batch.ethics_flag_triggered,
        "test_records": [
            {"id": t.id, "test_type": t.test_type, "passed": t.passed,
             "strength_ratio": t.strength_ratio, "laboratory_name": t.laboratory_name}
            for t in tests
        ],
    }


# ── SEAL Gate 3 ───────────────────────────────────────────────────────────────

@router.get("/seal-gate/{project_uid}",
            summary="Check ORIGIN™ readiness for SEAL™ (Gate 3)")
def check_seal_gate(
    project_uid: str,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("origin:read")),
):
    return OriginSealGateService.check_seal_gate(db, project_uid)
