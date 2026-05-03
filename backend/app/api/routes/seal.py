
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_action
from app.db.session import get_db
from app.models.entities import Certification, Professional
from app.schemas.api import ApiList, CertificationIssueRequest, CertificationOut
from app.services.audit import record_audit
from app.services.seal import certification_eligibility, get_full_gate_status, issue_certificate

router = APIRouter(prefix="/seal", tags=["seal"])

@router.get("/certifications", response_model=ApiList)
def list_certifications(db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:read"))):
    items = db.query(Certification).filter(Certification.is_deleted.is_(False)).order_by(Certification.id.desc()).all()
    return {"items": [CertificationOut.model_validate(i).model_dump() for i in items], "total": len(items)}

@router.get("/projects/{project_uid}/eligibility")
def get_eligibility(
    project_uid: str,
    certifying_engineer_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("projects:read")),
):
    eligible, shi, reason, gates = certification_eligibility(
        db, project_uid, certifying_engineer_id
    )
    return {
        "project_uid": project_uid,
        "eligible": eligible,
        "shi": shi,
        "reason": reason,
        "gates_summary": {k: v.get("passed") for k, v in gates.items()},
    }

@router.get("/projects/{project_uid}/gate-status")
def get_gate_status(
    project_uid: str,
    certifying_engineer_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("projects:read")),
):
    """Full 10-gate SEAL™ diagnostic. Shows exactly what remains before certification."""
    return get_full_gate_status(db, project_uid, certifying_engineer_id)

@router.post("/issue", response_model=CertificationOut)
def issue(payload: CertificationIssueRequest, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:write"))):
    try:
        cert = issue_certificate(
            db,
            project_uid=payload.project_uid,
            certificate_type=payload.certificate_type,
            issued_by=current_user.id,
            co_signed_by=current_user.id,
            notes=payload.notes,
            actor_email=current_user.email,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    record_audit(db, current_user.email, "SEAL_ISSUED", f"Issued {payload.certificate_type} for {payload.project_uid}")
    return cert
