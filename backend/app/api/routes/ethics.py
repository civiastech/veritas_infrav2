"""
VERITAS INFRA™ — ETHICS™ API Router
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Professional
from app.models.ethics import EthicsViolation, EthicsWhistleblowerReport
from app.services.ethics import EthicsService, WhistleblowerService

router = APIRouter(prefix="/ethics", tags=["ETHICS™ — Platform Integrity"])


class ViolationCreate(BaseModel):
    tier: str
    category: str
    description: str = Field(min_length=20)
    against_professional_id: Optional[int] = None
    against_firm: Optional[str] = None
    project_uid: Optional[str] = None
    component_uid: Optional[str] = None
    reference_record_type: Optional[str] = None
    reference_record_id: Optional[int] = None


class WhistleblowerReportCreate(BaseModel):
    anonymous: bool = False
    tier_suspected: str
    category_suspected: str
    description: str = Field(min_length=30)
    against_professional_id: Optional[int] = None
    project_uid: Optional[str] = None
    evidence_urls: Optional[list[str]] = None


class PanelDecision(BaseModel):
    decision: str  # "upheld" | "dismissed" | "partially_upheld"
    notes: str = Field(min_length=20)


@router.post("/violations", status_code=201,
             summary="Report an ethics violation")
def create_violation(
    payload: ViolationCreate,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("ethics:write")),
):
    try:
        v = EthicsService.create_violation(
            db,
            tier=payload.tier,
            category=payload.category,
            description=payload.description,
            against_professional_id=payload.against_professional_id,
            against_firm=payload.against_firm,
            reported_by_id=current_user.id,
            project_uid=payload.project_uid,
            component_uid=payload.component_uid,
            reference_record_type=payload.reference_record_type,
            reference_record_id=payload.reference_record_id,
            actor_email=current_user.email,
        )
        return {"violation_id": v.id, "uid": v.uid, "tier": v.tier,
                "consequences": v.consequences_applied}
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/violations/project/{project_uid}",
            summary="Check project ethics violations (SEAL Gate 4)")
def project_violations(
    project_uid: str,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("ethics:read")),
):
    return EthicsService.check_project_violations(db, project_uid)


@router.get("/violations/professional/{professional_id}",
            summary="Check professional ethics violations")
def professional_violations(
    professional_id: int,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("ethics:read")),
):
    return EthicsService.check_professional_violations(db, professional_id)


@router.post("/violations/{violation_id}/panel-decision",
             summary="Record panel decision on a violation")
def panel_decision(
    violation_id: int,
    payload: PanelDecision,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("ethics:panel")),
):
    try:
        v = EthicsService.record_panel_decision(
            db, violation_id, payload.decision, payload.notes, current_user
        )
        return {"violation_id": v.id, "status": v.status,
                "decision": v.panel_decision}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/violations",
            summary="List ethics violations")
def list_violations(
    tier: Optional[str] = Query(None),
    project_uid: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("ethics:read")),
):
    q = db.query(EthicsViolation)
    if tier:
        q = q.filter(EthicsViolation.tier == tier)
    if project_uid:
        q = q.filter(EthicsViolation.project_uid == project_uid)
    total = q.count()
    items = q.order_by(EthicsViolation.id.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [
        {"id": v.id, "uid": v.uid, "tier": v.tier, "category": v.category,
         "status": v.status, "against_professional_id": v.against_professional_id,
         "project_uid": v.project_uid, "created_at": str(v.created_at)}
        for v in items
    ]}


@router.post("/whistleblower", status_code=201,
             summary="Submit a confidential whistleblower report")
def submit_whistleblower(
    payload: WhistleblowerReportCreate,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("ethics:write")),
):
    report = WhistleblowerService.submit_report(
        db,
        reporter_id=current_user.id,
        anonymous=payload.anonymous,
        tier_suspected=payload.tier_suspected,
        category_suspected=payload.category_suspected,
        description=payload.description,
        against_professional_id=payload.against_professional_id,
        project_uid=payload.project_uid,
        evidence_urls=payload.evidence_urls,
    )
    return {
        "report_id": report.id,
        "status": report.status,
        "anonymous": report.anonymous,
        "message": "Report received. Your identity is protected." if report.anonymous
                   else "Report received and will be reviewed.",
    }
