
from datetime import datetime, timezone
from hashlib import sha256
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Dispute, Professional
from app.schemas.api import ApiList, DisputeCreate, DisputeOut, DisputeResolve
from app.services.audit import record_audit
from app.services.twin import append_twin_event

router = APIRouter(prefix="/lex", tags=["lex"])

@router.get("/disputes", response_model=ApiList)
def list_disputes(db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:read"))):
    items = db.query(Dispute).filter(Dispute.is_deleted.is_(False)).order_by(Dispute.id.desc()).all()
    return {"items": [DisputeOut.model_validate(i).model_dump() for i in items], "total": len(items)}

@router.post("/disputes", response_model=DisputeOut)
def create_dispute(payload: DisputeCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:write"))):
    if db.query(Dispute).filter(Dispute.uid == payload.uid, Dispute.is_deleted.is_(False)).first():
        raise HTTPException(409, "Dispute UID already exists")
    item = Dispute(
        uid=payload.uid,
        project_uid=payload.project_uid,
        component_uid=payload.component_uid,
        type=payload.type,
        raised_by=current_user.id,
        against_party=payload.against_party,
        description=payload.description,
        status="open",
        raised_date=datetime.now(timezone.utc).isoformat(),
    )
    db.add(item)
    db.commit(); db.refresh(item)
    append_twin_event(db, project_uid=item.project_uid, component_uid=item.component_uid, event_type="LEX.DISPUTE_OPENED", aggregate_type="dispute", aggregate_uid=item.uid, actor_email=current_user.email, payload={"dispute_id": item.id, "uid": item.uid})
    record_audit(db, current_user.email, "LEX_DISPUTE_CREATE", f"Opened dispute {item.uid}")
    return item

@router.post("/disputes/{dispute_id}/resolve", response_model=DisputeOut)
def resolve_dispute(dispute_id: int, payload: DisputeResolve, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("inspections:approve"))):
    item = db.query(Dispute).filter(Dispute.id == dispute_id, Dispute.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, "Dispute not found")
    item.status = "resolved"
    item.resolution = payload.resolution
    item.resolved_date = datetime.now(timezone.utc).isoformat()
    item.arbitrator_id = current_user.id
    item.determination_hash = sha256(payload.resolution.encode()).hexdigest()
    db.commit(); db.refresh(item)
    append_twin_event(db, project_uid=item.project_uid or "UNKNOWN", component_uid=item.component_uid, event_type="LEX.DETERMINATION_ISSUED", aggregate_type="dispute", aggregate_uid=item.uid, actor_email=current_user.email, payload={"dispute_id": item.id, "determination_hash": item.determination_hash})
    record_audit(db, current_user.email, "LEX_DISPUTE_RESOLVE", f"Resolved dispute {item.uid}")
    return item
