from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_action
from app.models.entities import Component, Professional
from app.schemas.api import ComponentOut, ComponentCreate, ComponentUpdate, ApiList, MutationResult
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/components', tags=['components'])

@router.get('', response_model=ApiList)
def list_items(project_uid: str | None = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('components:read'))):
    q = db.query(Component).filter(Component.is_deleted.is_(False))
    if project_uid:
        q = q.filter(Component.project_uid == project_uid)
    total = q.count()
    items = q.order_by(Component.id.desc()).offset(skip).limit(min(limit, 200)).all()
    return {'items': [ComponentOut.model_validate(x).model_dump() for x in items], 'total': total}

@router.post('', response_model=ComponentOut)
def create_item(payload: ComponentCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('components:write'))):
    if db.query(Component).filter(Component.uid == payload.uid, Component.is_deleted.is_(False)).first():
        raise HTTPException(409, 'Component UID already exists')
    item = Component(**payload.model_dump())
    db.add(item)
    db.commit(); db.refresh(item)
    publish_event(db, 'COMPONENT_CREATED', {'component_uid': item.uid, 'project_uid': item.project_uid})
    record_audit(db, current_user.email, 'COMPONENT_CREATE', f'Created component {item.uid}')
    return item

@router.put('/{component_id}', response_model=ComponentOut)
def update_item(component_id: int, payload: ComponentUpdate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('components:write'))):
    item = db.query(Component).filter(Component.id == component_id, Component.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Component not found')
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit(); db.refresh(item)
    publish_event(db, 'COMPONENT_UPDATED', {'component_uid': item.uid})
    record_audit(db, current_user.email, 'COMPONENT_UPDATE', f'Updated component {item.uid}')
    return item

@router.delete('/{component_id}', response_model=MutationResult)
def delete_item(component_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('components:write'))):
    item = db.query(Component).filter(Component.id == component_id, Component.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Component not found')
    item.is_deleted = True
    item.deleted_at = datetime.now(timezone.utc)
    db.commit()
    publish_event(db, 'COMPONENT_SOFT_DELETED', {'component_uid': item.uid})
    record_audit(db, current_user.email, 'COMPONENT_DELETE', f'Deleted component {item.uid}')
    return {'message': f'Component {item.uid} deleted'}
