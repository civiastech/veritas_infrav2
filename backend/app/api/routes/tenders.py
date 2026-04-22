from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_action
from app.models.entities import Tender, Professional
from app.schemas.api import TenderOut, TenderCreate, TenderUpdate, ApiList, MutationResult
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/tenders', tags=['tenders'])

@router.get('', response_model=ApiList)
def list_items(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('tenders:read'))):
    q = db.query(Tender).filter(Tender.is_deleted.is_(False))
    total = q.count()
    items = q.order_by(Tender.id.desc()).offset(skip).limit(min(limit, 200)).all()
    return {'items': [TenderOut.model_validate(x).model_dump() for x in items], 'total': total}

@router.post('', response_model=TenderOut)
def create_item(payload: TenderCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    if db.query(Tender).filter(Tender.uid == payload.uid, Tender.is_deleted.is_(False)).first():
        raise HTTPException(409, 'Tender UID already exists')
    item = Tender(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'TENDER_CREATED', {'tender_uid': item.uid})
    record_audit(db, current_user.email, 'TENDER_CREATE', f'Created tender {item.uid}')
    return item

@router.put('/{tender_id}', response_model=TenderOut)
def update_item(tender_id: int, payload: TenderUpdate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    item = db.query(Tender).filter(Tender.id == tender_id, Tender.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Tender not found')
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit(); db.refresh(item)
    publish_event(db, 'TENDER_UPDATED', {'tender_uid': item.uid})
    record_audit(db, current_user.email, 'TENDER_UPDATE', f'Updated tender {item.uid}')
    return item

@router.delete('/{tender_id}', response_model=MutationResult)
def delete_item(tender_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('projects:write'))):
    item = db.query(Tender).filter(Tender.id == tender_id, Tender.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Tender not found')
    item.is_deleted = True
    item.deleted_at = datetime.now(timezone.utc)
    db.commit()
    publish_event(db, 'TENDER_SOFT_DELETED', {'tender_uid': item.uid})
    record_audit(db, current_user.email, 'TENDER_DELETE', f'Deleted tender {item.uid}')
    return {'message': f'Tender {item.uid} deleted'}
