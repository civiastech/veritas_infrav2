from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, require_action
from app.models.entities import Project, Professional
from app.schemas.api import ProjectOut, ProjectCreate, ProjectUpdate, ApiList, MutationResult
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/projects', tags=['projects'])

@router.get('', response_model=ApiList)
def list_items(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:read'))):
    q = db.query(Project).filter(Project.is_deleted.is_(False))
    total = q.count()
    items = q.order_by(Project.id.desc()).offset(skip).limit(min(limit, 200)).all()
    return {'items': [ProjectOut.model_validate(x).model_dump() for x in items], 'total': total}

@router.get('/{project_id}', response_model=ProjectOut)
def get_item(project_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:read'))):
    item = db.query(Project).filter(Project.id == project_id, Project.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Project not found')
    return item

@router.post('', response_model=ProjectOut)
def create_item(payload: ProjectCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    if db.query(Project).filter(Project.uid == payload.uid, Project.is_deleted.is_(False)).first():
        raise HTTPException(409, 'Project UID already exists')
    item = Project(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    publish_event(db, 'PROJECT_CREATED', {'project_uid': item.uid})
    record_audit(db, current_user.email, 'PROJECT_CREATE', f'Created project {item.uid}')
    return item

@router.put('/{project_id}', response_model=ProjectOut)
def update_item(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    item = db.query(Project).filter(Project.id == project_id, Project.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Project not found')
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit(); db.refresh(item)
    publish_event(db, 'PROJECT_UPDATED', {'project_uid': item.uid})
    record_audit(db, current_user.email, 'PROJECT_UPDATE', f'Updated project {item.uid}')
    return item

@router.delete('/{project_id}', response_model=MutationResult)
def delete_item(project_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    item = db.query(Project).filter(Project.id == project_id, Project.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Project not found')
    item.is_deleted = True
    item.deleted_at = datetime.now(timezone.utc)
    db.commit()
    publish_event(db, 'PROJECT_SOFT_DELETED', {'project_uid': item.uid})
    record_audit(db, current_user.email, 'PROJECT_DELETE', f'Soft deleted project {item.uid}')
    return {'message': f'Project {item.uid} deleted'}
