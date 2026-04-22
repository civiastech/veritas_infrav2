
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Project, TwinEvent, TwinStream, Professional
from app.schemas.api import ApiList, TwinEventOut

router = APIRouter(prefix="/twin", tags=["twin"])

@router.get("/projects/{project_uid}/events", response_model=ApiList)
def list_project_events(project_uid: str, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:read"))):
    stream_ids = [s.id for s in db.query(TwinStream).filter(TwinStream.project_uid == project_uid).all()]
    items = []
    if stream_ids:
        items = db.query(TwinEvent).filter(TwinEvent.stream_id.in_(stream_ids)).order_by(TwinEvent.id.asc()).all()
    return {"items": [TwinEventOut.model_validate(i).model_dump() for i in items], "total": len(items)}
