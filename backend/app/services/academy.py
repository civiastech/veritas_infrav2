
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import Course, CredentialAward, Enrollment, LearningPath, Professional

BAND_ORDER = ['PROVISIONAL', 'STABLE', 'TRUSTED', 'HONOR']


def complete_enrollment(db: Session, enrollment: Enrollment, score: float) -> Enrollment:
    enrollment.status = 'completed'
    enrollment.score = score
    enrollment.completed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(enrollment)
    return enrollment


def maybe_award_path(db: Session, professional: Professional, path_code: str, awarded_by: int | None = None):
    courses = db.query(Course).filter(Course.path_code == path_code, Course.is_deleted.is_(False)).all()
    required = {c.code for c in courses}
    completed = {e.course_code for e in db.query(Enrollment).filter(Enrollment.professional_id == professional.id, Enrollment.path_code == path_code, Enrollment.status == 'completed', Enrollment.is_deleted.is_(False)).all()}
    if required and required.issubset(completed):
        existing = db.query(CredentialAward).filter(CredentialAward.professional_id == professional.id, CredentialAward.path_code == path_code, CredentialAward.is_deleted.is_(False)).first()
        if existing:
            return existing
        path = db.query(LearningPath).filter(LearningPath.code == path_code).first()
        rec = False
        if path and path.target_band in BAND_ORDER and professional.band in BAND_ORDER:
            rec = BAND_ORDER.index(path.target_band) > BAND_ORDER.index(professional.band)
        award = CredentialAward(professional_id=professional.id, path_code=path_code, credential_title=f'{path.title if path else path_code} Credential', awarded_by=awarded_by, status='awarded', advancement_recommended=rec)
        db.add(award); db.commit(); db.refresh(award)
        return award
    return None


def band_advancement_summary(db: Session, professional: Professional) -> dict:
    completed = db.query(Enrollment).filter(Enrollment.professional_id == professional.id, Enrollment.status == 'completed', Enrollment.is_deleted.is_(False)).all()
    awards = db.query(CredentialAward).filter(CredentialAward.professional_id == professional.id, CredentialAward.is_deleted.is_(False)).all()
    targets = []
    if awards:
        paths = {p.code: p for p in db.query(LearningPath).filter(LearningPath.code.in_([a.path_code for a in awards])).all()}
        targets = [paths[a.path_code].target_band for a in awards if a.advancement_recommended and a.path_code in paths and paths[a.path_code].target_band]
    recommended = max(targets, key=lambda b: BAND_ORDER.index(b)) if targets else None
    return {
        'professional_id': professional.id,
        'current_band': professional.band,
        'completed_courses': len(completed),
        'completed_paths': len(awards),
        'recommended_next_band': recommended,
        'recommendation_ready': recommended is not None,
    }
