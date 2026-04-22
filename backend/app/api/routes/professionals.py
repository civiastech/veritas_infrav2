from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.entities import Professional
from app.schemas.api import ApiList, ProfessionalOut

router = APIRouter(prefix='/professionals', tags=['professionals'])

@router.get('', response_model=ApiList)
def list_items(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: Professional = Depends(require_roles('admin', 'engineer', 'inspector'))):
    q = db.query(Professional).filter(Professional.is_deleted.is_(False))
    total = q.count()
    items = q.order_by(Professional.id.asc()).offset(skip).limit(min(limit, 200)).all()
    return {'items': [ProfessionalOut.model_validate(x).model_dump() for x in items], 'total': total}
