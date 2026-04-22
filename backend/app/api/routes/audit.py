from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.entities import AuditLog, Professional
from app.schemas.api import ApiList, AuditLogOut

router = APIRouter(prefix='/audit', tags=['audit'])

@router.get('', response_model=ApiList)
def list_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: Professional = Depends(require_roles('admin'))):
    q = db.query(AuditLog)
    total = q.count()
    items = q.order_by(AuditLog.id.desc()).offset(skip).limit(min(limit, 200)).all()
    return {'items': [AuditLogOut.model_validate(x).model_dump() for x in items], 'total': total}
