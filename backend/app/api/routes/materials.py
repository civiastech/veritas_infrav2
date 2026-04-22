from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_action
from app.models.entities import Material, Professional
from app.schemas.api import MaterialOut, MaterialCreate, MaterialUpdate, ApiList, MutationResult
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/materials', tags=['materials'])

@router.get('', response_model=ApiList)
def list_items(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('materials:read'))):
    q = db.query(Material).filter(Material.is_deleted.is_(False))
    total = q.count()
    items = q.order_by(Material.id.desc()).offset(skip).limit(min(limit, 200)).all()
    return {'items': [MaterialOut.model_validate(x).model_dump() for x in items], 'total': total}

@router.post('', response_model=MaterialOut)
def create_item(payload: MaterialCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    if db.query(Material).filter(Material.batch_uid == payload.batch_uid, Material.is_deleted.is_(False)).first():
        raise HTTPException(409, 'Material batch UID already exists')
    item = Material(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'MATERIAL_CREATED', {'batch_uid': item.batch_uid})
    record_audit(db, current_user.email, 'MATERIAL_CREATE', f'Created material {item.batch_uid}')
    return item

@router.put('/{material_id}', response_model=MaterialOut)
def update_item(material_id: int, payload: MaterialUpdate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    item = db.query(Material).filter(Material.id == material_id, Material.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Material not found')
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit(); db.refresh(item)
    publish_event(db, 'MATERIAL_UPDATED', {'batch_uid': item.batch_uid})
    record_audit(db, current_user.email, 'MATERIAL_UPDATE', f'Updated material {item.batch_uid}')
    return item

@router.delete('/{material_id}', response_model=MutationResult)
def delete_item(material_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    item = db.query(Material).filter(Material.id == material_id, Material.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Material not found')
    item.is_deleted = True
    item.deleted_at = datetime.now(timezone.utc)
    db.commit()
    publish_event(db, 'MATERIAL_SOFT_DELETED', {'batch_uid': item.batch_uid})
    record_audit(db, current_user.email, 'MATERIAL_DELETE', f'Deleted material {item.batch_uid}')
    return {'message': f'Material {item.batch_uid} deleted'}
