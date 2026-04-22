
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Component, Inspection, Professional
from app.schemas.api import ApiList, InspectionCreate, InspectionOut
from app.services.audit import record_audit
from app.services.workflows import create_inspection_from_scores

router = APIRouter(prefix="/vision", tags=["vision"])

@router.get("/inspections", response_model=ApiList)
def list_inspections(db: Session = Depends(get_db), current_user: Professional = Depends(require_action("inspections:read"))):
    items = db.query(Inspection).filter(Inspection.is_deleted.is_(False)).order_by(Inspection.id.desc()).all()
    return {"items": [InspectionOut.model_validate(i).model_dump() for i in items], "total": len(items)}

@router.post("/inspections", response_model=InspectionOut)
def create_inspection(payload: InspectionCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("inspections:approve"))):
    component = db.query(Component).filter(Component.uid == payload.component_uid, Component.is_deleted.is_(False)).first()
    if not component:
        raise HTTPException(404, "Component not found")
    if component.blocked_for_execution:
        raise HTTPException(409, "Component remains blocked for execution until approved evidence exists")
    inspection = create_inspection_from_scores(
        db,
        component=component,
        inspector=current_user,
        material_score=payload.material_score,
        assembly_score=payload.assembly_score,
        env_score=payload.env_score,
        supervision_score=payload.supervision_score,
        ai_flags=payload.ai_flags,
        reason_tag=payload.reason_tag,
    )
    record_audit(db, current_user.email, "VISION_INSPECTION_CREATE", f"Created SHI assessment for {component.uid}")
    return inspection
