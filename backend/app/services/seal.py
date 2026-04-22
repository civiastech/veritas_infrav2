
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import Certification, Dispute, Material, Project
from app.services.twin import append_twin_event

def certification_eligibility(db: Session, project_uid: str) -> tuple[bool, float, str]:
    project = db.query(Project).filter(Project.uid == project_uid, Project.is_deleted.is_(False)).first()
    if not project:
        return False, 0.0, "Project not found"
    unresolved = db.query(Dispute).filter(
        Dispute.project_uid == project_uid,
        Dispute.status.in_(["open", "under_review"]),
        Dispute.is_deleted.is_(False),
    ).count()
    if unresolved:
        return False, project.shi, "Unresolved disputes exist"
    related_materials = db.query(Material).filter(Material.projects_used.is_not(None), Material.is_deleted.is_(False)).all()
    unverified = [m.batch_uid for m in related_materials if project_uid in (m.projects_used or []) and not m.verified]
    if unverified:
        return False, project.shi, "Unverified material batches exist"
    if project.shi < 85:
        return False, project.shi, f"Project SHI {project.shi:.2f} below certification threshold 85.00"
    return True, project.shi, "Eligible"

def issue_certificate(db: Session, project_uid: str, certificate_type: str, issued_by: int, co_signed_by: int | None, notes: str | None, actor_email: str) -> Certification:
    eligible, shi, reason = certification_eligibility(db, project_uid)
    if not eligible:
        raise ValueError(reason)
    cert = Certification(
        project_uid=project_uid,
        type=certificate_type,
        shi_composite=shi,
        issued_by=issued_by,
        co_signed_by=co_signed_by,
        issued_date=datetime.now(timezone.utc).isoformat(),
        physical_plate=f"{certificate_type}-{project_uid}",
        status="issued",
        qr_code=f"VRF-{project_uid}",
        notes=notes,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    append_twin_event(
        db,
        project_uid=project_uid,
        event_type="SEAL.CERTIFICATE_ISSUED",
        aggregate_type="certificate",
        aggregate_uid=str(cert.id),
        actor_email=actor_email,
        payload={"project_uid": project_uid, "certificate_type": certificate_type, "shi": shi},
    )
    return cert
