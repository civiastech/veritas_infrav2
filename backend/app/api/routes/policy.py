
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.api import PolicyRuleIn, PolicyEvalIn
from app.services.domainx.services import PolicyService

router = APIRouter(prefix="/policy", tags=["policy"])

@router.post("/rules")
def add_rule(payload: PolicyRuleIn, db: Session = Depends(get_db)):
    return PolicyService(db).add_rule(**payload.model_dump())

@router.post("/evaluate")
def evaluate(payload: PolicyEvalIn, db: Session = Depends(get_db)):
    return PolicyService(db).evaluate(**payload.model_dump())
