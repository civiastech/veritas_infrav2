
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Course, CredentialAward, Enrollment, LearningPath, Professional
from app.schemas.api import ApiList, BandAdvancementSummary, CompleteEnrollmentRequest, CourseCreate, CourseOut, CredentialAwardOut, EnrollmentCreate, EnrollmentOut, LearningPathCreate, LearningPathOut
from app.services.academy import band_advancement_summary, complete_enrollment, maybe_award_path
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/academy', tags=['academy'])

@router.get('/paths', response_model=ApiList)
def list_paths(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:read'))):
    items = db.query(LearningPath).filter(LearningPath.is_deleted.is_(False)).order_by(LearningPath.id.desc()).all()
    return {'items': [LearningPathOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/paths', response_model=LearningPathOut)
def create_path(payload: LearningPathCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:write'))):
    item = LearningPath(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'ACADEMY.PATH_CREATED', {'path_code': item.code})
    record_audit(db, current_user.email, 'ACADEMY_PATH_CREATE', f'Created path {item.code}')
    return item

@router.get('/courses', response_model=ApiList)
def list_courses(path_code: str | None = None, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:read'))):
    q = db.query(Course).filter(Course.is_deleted.is_(False))
    if path_code:
        q = q.filter(Course.path_code == path_code)
    items = q.order_by(Course.id.desc()).all()
    return {'items': [CourseOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/courses', response_model=CourseOut)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:write'))):
    item = Course(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'ACADEMY.COURSE_CREATED', {'course_code': item.code})
    record_audit(db, current_user.email, 'ACADEMY_COURSE_CREATE', f'Created course {item.code}')
    return item

@router.get('/enrollments', response_model=ApiList)
def list_enrollments(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:read'))):
    q = db.query(Enrollment).filter(Enrollment.is_deleted.is_(False))
    if current_user.role != 'admin':
        q = q.filter(Enrollment.professional_id == current_user.id)
    items = q.order_by(Enrollment.id.desc()).all()
    return {'items': [EnrollmentOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/enrollments', response_model=EnrollmentOut)
def enroll(payload: EnrollmentCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:read'))):
    course = db.query(Course).filter(Course.code == payload.course_code, Course.is_deleted.is_(False)).first()
    if not course:
        raise HTTPException(404, 'Course not found')
    existing = db.query(Enrollment).filter(Enrollment.professional_id == current_user.id, Enrollment.course_code == payload.course_code, Enrollment.is_deleted.is_(False)).first()
    if existing:
        return existing
    item = Enrollment(professional_id=current_user.id, course_code=course.code, path_code=course.path_code, status='enrolled')
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'ACADEMY.ENROLLMENT_CREATED', {'professional_id': current_user.id, 'course_code': item.course_code})
    record_audit(db, current_user.email, 'ACADEMY_ENROLL', f'Enrolled in {item.course_code}')
    return item

@router.post('/enrollments/{enrollment_id}/complete', response_model=EnrollmentOut)
def complete(enrollment_id: int, payload: CompleteEnrollmentRequest, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:read'))):
    item = db.query(Enrollment).filter(Enrollment.id == enrollment_id, Enrollment.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Enrollment not found')
    if current_user.role != 'admin' and item.professional_id != current_user.id:
        raise HTTPException(403, 'Cannot complete another professional enrollment')
    item = complete_enrollment(db, item, payload.score)
    professional = db.query(Professional).filter(Professional.id == item.professional_id).first()
    maybe_award_path(db, professional, item.path_code, current_user.id)
    publish_event(db, 'ACADEMY.ENROLLMENT_COMPLETED', {'professional_id': item.professional_id, 'course_code': item.course_code, 'score': item.score})
    record_audit(db, current_user.email, 'ACADEMY_COMPLETE', f'Completed {item.course_code}')
    return item

@router.get('/credentials', response_model=ApiList)
def list_credentials(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:read'))):
    q = db.query(CredentialAward).filter(CredentialAward.is_deleted.is_(False))
    if current_user.role != 'admin':
        q = q.filter(CredentialAward.professional_id == current_user.id)
    items = q.order_by(CredentialAward.id.desc()).all()
    return {'items': [CredentialAwardOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.get('/advancement/me', response_model=BandAdvancementSummary)
def my_advancement(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('academy:read'))):
    return band_advancement_summary(db, current_user)
