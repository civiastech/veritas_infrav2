
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Milestone, Payment, Professional
from app.schemas.api import ApiList, GateDecisionOut, PaymentOut
from app.services.audit import record_audit
from app.services.payments import evaluate_milestone_gate, release_payment

router = APIRouter(prefix="/pay", tags=["pay"])

@router.get("/milestones", response_model=ApiList)
def list_milestones(db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:read"))):
    items = db.query(Milestone).filter(Milestone.is_deleted.is_(False)).order_by(Milestone.project_uid.asc(), Milestone.phase.asc()).all()
    return {"items": items, "total": len(items)}

@router.post("/milestones/{milestone_id}/evaluate", response_model=GateDecisionOut)
def evaluate_gate(milestone_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:write"))):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id, Milestone.is_deleted.is_(False)).first()
    if not milestone:
        raise HTTPException(404, "Milestone not found")
    eligible, project_shi, reason = evaluate_milestone_gate(db, milestone)
    return {
        "project_uid": milestone.project_uid,
        "milestone_id": milestone.id,
        "project_shi": project_shi,
        "required_shi": milestone.required_shi,
        "eligible": eligible,
        "reason": reason,
    }

@router.post("/milestones/{milestone_id}/release", response_model=PaymentOut)
def release_gate(milestone_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:write"))):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id, Milestone.is_deleted.is_(False)).first()
    if not milestone:
        raise HTTPException(404, "Milestone not found")
    payment = release_payment(db, milestone, current_user.email)
    record_audit(db, current_user.email, "PAY_RELEASE_ATTEMPT", f"Milestone {milestone.id} resulted in {payment.status}")
    return payment

@router.get("/payments", response_model=ApiList)
def list_payments(db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:read"))):
    items = db.query(Payment).filter(Payment.is_deleted.is_(False)).order_by(Payment.id.desc()).all()
    return {"items": [PaymentOut.model_validate(i).model_dump() for i in items], "total": len(items)}
