
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Component, Evidence, EvidenceAsset, Professional
from app.schemas.api import ApiList, EvidenceAssetOut, MutationResult
from app.services.audit import record_audit
from app.services.workflows import approve_evidence, create_or_get_hold, upload_evidence_payload

router = APIRouter(prefix="/evidence", tags=["evidence"])

@router.get("", response_model=ApiList)
def list_evidence(db: Session = Depends(get_db), current_user: Professional = Depends(require_action("evidence:read"))):
    items = db.query(Evidence).filter(Evidence.is_deleted.is_(False)).order_by(Evidence.id.desc()).all()
    return {"items": items, "total": len(items)}

@router.post("/upload", response_model=EvidenceAssetOut)
def upload_evidence(
    component_uid: str = Form(...),
    description: str | None = Form(None),
    type: str = Form("CAPTURE-LARGE"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("evidence:write")),
):
    component = db.query(Component).filter(Component.uid == component_uid, Component.is_deleted.is_(False)).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    create_or_get_hold(db, component)
    payload = file.file.read()
    evidence, asset = upload_evidence_payload(
        db,
        component=component,
        current_user=current_user,
        filename=file.filename,
        payload=payload,
        content_type=file.content_type or "application/octet-stream",
        description=description,
        type_name=type,
    )
    record_audit(db, current_user.email, "BUILD_EVIDENCE_UPLOAD", f"Uploaded evidence {evidence.id} for {component_uid}")
    return asset

@router.get("/{evidence_id}/assets", response_model=ApiList)
def list_assets(evidence_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("evidence:read"))):
    items = db.query(EvidenceAsset).filter(EvidenceAsset.evidence_id == evidence_id).order_by(EvidenceAsset.id.asc()).all()
    return {"items": [EvidenceAssetOut.model_validate(x).model_dump() for x in items], "total": len(items)}

@router.patch("/{evidence_id}", response_model=MutationResult)
def approve_evidence_route(evidence_id: int, status_text: str = Form(...), db: Session = Depends(get_db), current_user: Professional = Depends(require_action("inspections:approve"))):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id, Evidence.is_deleted.is_(False)).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if status_text.lower() == "approved":
        approve_evidence(db, evidence, current_user)
    else:
        evidence.status = status_text
        evidence.approved_by = current_user.id
        db.commit()
    record_audit(db, current_user.email, "BUILD_EVIDENCE_STATUS", f"Set evidence {evidence.id} to {status_text}")
    return MutationResult(message="Evidence updated successfully")
