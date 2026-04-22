from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Regulation, Consultation, ComplianceMapping, Professional
from app.schemas.api import ApiList, RegulationCreate, RegulationOut, ConsultationCreate, ConsultationOut, ComplianceMappingCreate, ComplianceMappingOut, RegulatoryReadinessSummary
from app.services.regulatory import build_regulatory_readiness
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/regulatory', tags=['regulatory'])

@router.get('/readiness', response_model=RegulatoryReadinessSummary)
def readiness(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('regulatory:read'))):
    return build_regulatory_readiness(db)

@router.get('/regulations', response_model=ApiList)
def list_regulations(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('regulatory:read'))):
    items = db.query(Regulation).filter(Regulation.is_deleted.is_(False)).order_by(Regulation.id.desc()).all()
    return {'items': [RegulationOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/regulations', response_model=RegulationOut)
def create_regulation(payload: RegulationCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('regulatory:write'))):
    item = Regulation(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'REGULATORY.REGULATION_CREATED', {'regulation_code': item.regulation_code, 'country_code': item.country_code})
    record_audit(db, current_user.email, 'REGULATION_CREATE', f'Created regulation {item.regulation_code}')
    return item

@router.get('/consultations', response_model=ApiList)
def list_consultations(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('regulatory:read'))):
    items = db.query(Consultation).filter(Consultation.is_deleted.is_(False)).order_by(Consultation.id.desc()).all()
    return {'items': [ConsultationOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/consultations', response_model=ConsultationOut)
def create_consultation(payload: ConsultationCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('regulatory:write'))):
    item = Consultation(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'REGULATORY.CONSULTATION_OPENED', {'consultation_uid': item.consultation_uid, 'country_code': item.country_code})
    record_audit(db, current_user.email, 'CONSULTATION_CREATE', f'Opened consultation {item.consultation_uid}')
    return item

@router.get('/compliance-mappings', response_model=ApiList)
def list_mappings(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('regulatory:read'))):
    items = db.query(ComplianceMapping).filter(ComplianceMapping.is_deleted.is_(False)).order_by(ComplianceMapping.id.desc()).all()
    return {'items': [ComplianceMappingOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/compliance-mappings', response_model=ComplianceMappingOut)
def create_mapping(payload: ComplianceMappingCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('regulatory:write'))):
    item = ComplianceMapping(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'REGULATORY.COMPLIANCE_MAPPED', {'country_code': item.country_code, 'module_code': item.module_code})
    record_audit(db, current_user.email, 'COMPLIANCE_MAPPING_CREATE', f'Mapped {item.module_code} for {item.country_code}')
    return item
