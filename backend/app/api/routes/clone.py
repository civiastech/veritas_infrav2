from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Country, CountryTenant, LaunchProgram, RevenueShareRule, Professional
from app.schemas.api import ApiList, CloneRolloutSummary, CountryCreate, CountryOut, CountryTenantCreate, CountryTenantOut, LaunchProgramCreate, LaunchProgramOut, RevenueShareRuleCreate, RevenueShareRuleOut
from app.services.clone import build_rollout_summary
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/clone', tags=['clone'])

@router.get('/rollout/summary', response_model=CloneRolloutSummary)
def rollout_summary(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:read'))):
    return build_rollout_summary(db)

@router.get('/countries', response_model=ApiList)
def list_countries(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:read'))):
    items = db.query(Country).filter(Country.is_deleted.is_(False)).order_by(Country.readiness_score.desc()).all()
    return {'items': [CountryOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/countries', response_model=CountryOut)
def create_country(payload: CountryCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:write'))):
    item = Country(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'CLONE.COUNTRY_REGISTERED', {'country_code': item.code, 'name': item.name})
    record_audit(db, current_user.email, 'CLONE_COUNTRY_CREATE', f'Created country {item.code}')
    return item

@router.get('/tenants', response_model=ApiList)
def list_tenants(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:read'))):
    items = db.query(CountryTenant).filter(CountryTenant.is_deleted.is_(False)).order_by(CountryTenant.id.desc()).all()
    return {'items': [CountryTenantOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/tenants', response_model=CountryTenantOut)
def create_tenant(payload: CountryTenantCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:write'))):
    item = CountryTenant(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'CLONE.TENANT_CREATED', {'country_code': item.country_code, 'operator_name': item.operator_name})
    record_audit(db, current_user.email, 'CLONE_TENANT_CREATE', f'Created tenant {item.operator_name} for {item.country_code}')
    return item

@router.get('/launch-programs', response_model=ApiList)
def list_programs(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:read'))):
    items = db.query(LaunchProgram).filter(LaunchProgram.is_deleted.is_(False)).order_by(LaunchProgram.id.desc()).all()
    return {'items': [LaunchProgramOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/launch-programs', response_model=LaunchProgramOut)
def create_program(payload: LaunchProgramCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:write'))):
    item = LaunchProgram(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'CLONE.LAUNCH_PROGRAM_CREATED', {'country_code': item.country_code, 'title': item.title})
    record_audit(db, current_user.email, 'CLONE_LAUNCH_PROGRAM_CREATE', f'Created launch program {item.title}')
    return item

@router.get('/revenue-share-rules', response_model=ApiList)
def list_rules(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:read'))):
    items = db.query(RevenueShareRule).filter(RevenueShareRule.is_deleted.is_(False)).order_by(RevenueShareRule.id.desc()).all()
    return {'items': [RevenueShareRuleOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/revenue-share-rules', response_model=RevenueShareRuleOut)
def create_rule(payload: RevenueShareRuleCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('clone:write'))):
    item = RevenueShareRule(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'CLONE.REVENUE_RULE_CREATED', {'country_code': item.country_code, 'module_code': item.module_code})
    record_audit(db, current_user.email, 'CLONE_REVENUE_RULE_CREATE', f'Created revenue share rule {item.module_code}/{item.country_code}')
    return item
