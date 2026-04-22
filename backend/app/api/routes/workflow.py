
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.api import WorkflowDefinitionIn, WorkflowStateIn, WorkflowTransitionIn, WorkflowInstanceIn, WorkflowActionIn
from app.services.domainx.services import WorkflowService
from app.domainx.models import WorkflowHistory

router = APIRouter(prefix="/workflow", tags=["workflow"])

@router.post("/definitions")
def create_definition(payload: WorkflowDefinitionIn, db: Session = Depends(get_db)):
    return WorkflowService(db).create_definition(**payload.model_dump())

@router.post("/states")
def add_state(payload: WorkflowStateIn, db: Session = Depends(get_db)):
    return WorkflowService(db).add_state(**payload.model_dump())

@router.post("/transitions")
def add_transition(payload: WorkflowTransitionIn, db: Session = Depends(get_db)):
    return WorkflowService(db).add_transition(**payload.model_dump())

@router.post("/instances")
def start_instance(payload: WorkflowInstanceIn, db: Session = Depends(get_db)):
    return WorkflowService(db).start_instance(**payload.model_dump())

@router.post("/instances/{instance_id}/actions")
def apply_action(instance_id: int, payload: WorkflowActionIn, db: Session = Depends(get_db)):
    try:
        return WorkflowService(db).apply_transition(instance_id, **payload.model_dump())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/instances/{instance_id}/history")
def get_history(instance_id: int, db: Session = Depends(get_db)):
    return db.query(WorkflowHistory).filter(WorkflowHistory.instance_id == instance_id).all()
