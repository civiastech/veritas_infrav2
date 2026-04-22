
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import FinancialProduct, Professional, UnderwritingApplication
from app.schemas.api import ApiList, FinancialProductCreate, FinancialProductOut, RiskDecisionOut, UnderwritingApplicationCreate, UnderwritingApplicationOut, UnderwritingEvaluationOut
from app.services.audit import record_audit
from app.services.events import publish_event
from app.services.verifund import evaluate_application

router = APIRouter(prefix='/verifund', tags=['verifund'])

@router.get('/products', response_model=ApiList)
def list_products(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('verifund:read'))):
    items = db.query(FinancialProduct).filter(FinancialProduct.is_deleted.is_(False)).order_by(FinancialProduct.id.desc()).all()
    return {'items': [FinancialProductOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/products', response_model=FinancialProductOut)
def create_product(payload: FinancialProductCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('verifund:write'))):
    item = FinancialProduct(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'VERIFUND.PRODUCT_CREATED', {'product_code': item.code})
    record_audit(db, current_user.email, 'VERIFUND_PRODUCT_CREATE', f'Created product {item.code}')
    return item

@router.get('/applications', response_model=ApiList)
def list_applications(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('verifund:read'))):
    items = db.query(UnderwritingApplication).filter(UnderwritingApplication.is_deleted.is_(False)).order_by(UnderwritingApplication.id.desc()).all()
    return {'items': [UnderwritingApplicationOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/applications', response_model=UnderwritingApplicationOut)
def create_application(payload: UnderwritingApplicationCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('verifund:write'))):
    item = UnderwritingApplication(**payload.model_dump(), submitted_by=current_user.id)
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'VERIFUND.APPLICATION_SUBMITTED', {'application_uid': item.application_uid, 'project_uid': item.project_uid})
    record_audit(db, current_user.email, 'VERIFUND_APPLICATION_CREATE', f'Created application {item.application_uid}')
    return item

@router.post('/applications/{application_id}/evaluate', response_model=UnderwritingEvaluationOut)
def evaluate(application_id: int, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('verifund:write'))):
    item = db.query(UnderwritingApplication).filter(UnderwritingApplication.id == application_id, UnderwritingApplication.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(404, 'Application not found')
    decision = evaluate_application(db, item)
    publish_event(db, 'VERIFUND.RISK_DECISION_MADE', {'application_uid': item.application_uid, 'decision': decision.decision, 'risk_score': decision.risk_score})
    record_audit(db, current_user.email, 'VERIFUND_APPLICATION_EVALUATE', f'Evaluated application {item.application_uid}')
    return {'application': UnderwritingApplicationOut.model_validate(item), 'decision': RiskDecisionOut.model_validate(decision)}
