
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import AtlasReport, AtlasSubscription, Professional
from app.schemas.api import ApiList, AtlasPortfolioSummary, AtlasReportCreate, AtlasReportOut, AtlasSubscriptionCreate, AtlasSubscriptionOut
from app.services.atlas import build_portfolio_summary
from app.services.audit import record_audit
from app.services.events import publish_event

router = APIRouter(prefix='/atlas', tags=['atlas'])

@router.get('/portfolio/overview', response_model=AtlasPortfolioSummary)
def portfolio_overview(country: str | None = None, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('atlas:read'))):
    return build_portfolio_summary(db, country)

@router.get('/subscriptions', response_model=ApiList)
def list_subscriptions(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('atlas:read'))):
    items = db.query(AtlasSubscription).filter(AtlasSubscription.is_deleted.is_(False)).order_by(AtlasSubscription.id.desc()).all()
    return {'items': [AtlasSubscriptionOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/subscriptions', response_model=AtlasSubscriptionOut)
def create_subscription(payload: AtlasSubscriptionCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('atlas:write'))):
    item = AtlasSubscription(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'ATLAS.SUBSCRIPTION_CREATED', {'subscription_id': item.id, 'subscriber_name': item.subscriber_name})
    record_audit(db, current_user.email, 'ATLAS_SUBSCRIPTION_CREATE', f'Created ATLAS subscription {item.subscriber_name}')
    return item

@router.get('/reports', response_model=ApiList)
def list_reports(db: Session = Depends(get_db), current_user: Professional = Depends(require_action('atlas:read'))):
    items = db.query(AtlasReport).filter(AtlasReport.is_deleted.is_(False)).order_by(AtlasReport.id.desc()).all()
    return {'items': [AtlasReportOut.model_validate(x).model_dump() for x in items], 'total': len(items)}

@router.post('/reports', response_model=AtlasReportOut)
def generate_report(payload: AtlasReportCreate, db: Session = Depends(get_db), current_user: Professional = Depends(require_action('atlas:write'))):
    summary = build_portfolio_summary(db, payload.country_scope)
    item = AtlasReport(title=payload.title, country_scope=payload.country_scope, report_type=payload.report_type, period_label=payload.period_label, generated_by=current_user.id, payload=summary, status='published')
    db.add(item); db.commit(); db.refresh(item)
    publish_event(db, 'ATLAS.REPORT_PUBLISHED', {'report_id': item.id, 'title': item.title})
    record_audit(db, current_user.email, 'ATLAS_REPORT_CREATE', f'Generated report {item.title}')
    return item
