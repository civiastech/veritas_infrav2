from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.api import DashboardSummary
from app.services.dashboard import get_dashboard_summary
from app.models.entities import Professional

router = APIRouter(prefix='/dashboard', tags=['dashboard'])

@router.get('/summary', response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), current_user: Professional = Depends(get_current_user)):
    return get_dashboard_summary(db, current_user.role)
