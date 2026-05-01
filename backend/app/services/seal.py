import base64
import io
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import Certification, Dispute, Material, Project
from app.services.twin import append_twin_event


def _generate_qr_code_b64(data: str) -> str:
    try:
        import qrcode
        from qrcode.image.pure import PyPNGImage
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8, border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(image_factory=PyPNGImage)
        buffer = io.BytesIO()
        img.save(buffer)
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{b64}'
    except Exception:
        return f'VERIFY:{data}'


def _build_verification_url(project_uid: str) -> str:
    try:
        from app.core.config import settings
        base = getattr(settings, 'seal_registry_url', None)
    except Exception:
        base = None
    return f"{base or 'https://verify.veritasinfra.com/seal'}/{project_uid}"


def certification_eligibility(db: Session, project_uid: str):
    project = db.query(Project).filter(
        Project.uid == project_uid, Project.is_deleted.is_(False)
    ).first()
    if not project:
        return False, 0.0, 'Project not found'
    unresolved = db.query(Dispute).filter(
        Dispute.project_uid == project_uid,
        Dispute.status.in_(['open', 'under_review']),
        Dispute.is_deleted.is_(False),
    ).count()
    if unresolved:
        return False, project.shi, f'Unresolved disputes: {unresolved}'
    related = db.query(Material).filter(
        Material.projects_used.is_not(None),
        Material.is_deleted.is_(False),
    ).all()
    unverified = [m.batch_uid for m in related
                  if project_uid in (m.projects_used or []) and not m.verified]
    if unverified:
        return False, project.shi, f'Unverified materials: {unverified}'
    try:
        from app.core.config import settings
        threshold = getattr(settings, 'seal_shi_threshold', 85.0)
    except Exception:
        threshold = 85.0
    if project.shi < threshold:
        return False, project.shi, f'SHI {project.shi:.2f} below {threshold:.2f}'
    return True, project.shi, 'Eligible'


def issue_certificate(db, project_uid, certificate_type,
                      issued_by, co_signed_by, notes, actor_email):
    eligible, shi, reason = certification_eligibility(db, project_uid)
    if not eligible:
        raise ValueError(reason)
    url = _build_verification_url(project_uid)
    qr = _generate_qr_code_b64(url)
    cert = Certification(
        project_uid=project_uid, type=certificate_type,
        shi_composite=shi, issued_by=issued_by,
        co_signed_by=co_signed_by,
        issued_date=datetime.now(timezone.utc).isoformat(),
        physical_plate=f'{certificate_type}-{project_uid}',
        status='issued', qr_code=qr, notes=notes,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    append_twin_event(
        db, project_uid=project_uid,
        event_type='SEAL.CERTIFICATE_ISSUED',
        aggregate_type='certificate',
        aggregate_uid=str(cert.id),
        actor_email=actor_email,
        payload={'project_uid': project_uid, 'type': certificate_type,
                 'shi': shi, 'verification_url': url},
    )
    return cert
