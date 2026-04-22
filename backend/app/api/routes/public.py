
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import Certification
from app.schemas.api import PublicCertificateOut

router = APIRouter(prefix="/public", tags=["public"])

@router.get("/seal/{project_uid}", response_model=PublicCertificateOut)
def verify_seal(project_uid: str, db: Session = Depends(get_db)):
    cert = db.query(Certification).filter(
        Certification.project_uid == project_uid,
        Certification.status.in_(["issued", "pending_ceremony"]),
        Certification.is_deleted.is_(False),
    ).order_by(Certification.id.desc()).first()
    if not cert:
        raise HTTPException(404, "Certificate not found")
    return {
        "project_uid": cert.project_uid,
        "certificate_type": cert.type,
        "status": cert.status,
        "issued_date": cert.issued_date,
        "physical_plate": cert.physical_plate,
        "qr_code": cert.qr_code,
        "shi_composite": cert.shi_composite,
    }
