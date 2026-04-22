
from sqlalchemy.orm import Session
from app.models.entities import Project, Certification, Material, MonitorAlert, FinancialProduct, UnderwritingApplication, RiskDecision, Evidence, Inspection


def evaluate_application(db: Session, application: UnderwritingApplication) -> RiskDecision:
    project = db.query(Project).filter(Project.uid == application.project_uid, Project.is_deleted.is_(False)).first()
    product = db.query(FinancialProduct).filter(FinancialProduct.code == application.product_code, FinancialProduct.is_deleted.is_(False)).first()
    if not project or not product:
        raise ValueError('Project or product not found')
    alerts = db.query(MonitorAlert).filter(MonitorAlert.project_uid == application.project_uid, MonitorAlert.status == 'open').count()
    cert = db.query(Certification).filter(Certification.project_uid == application.project_uid, Certification.is_deleted.is_(False)).first()
    materials = [m for m in db.query(Material).filter(Material.is_deleted.is_(False)).all() if application.project_uid in (m.projects_used or [])]
    verified_materials = sum(1 for m in materials if m.verified)
    evidences = db.query(Evidence).filter(Evidence.project_uid == application.project_uid, Evidence.status == 'approved', Evidence.is_deleted.is_(False)).count()
    inspections = db.query(Inspection).filter(Inspection.project_uid == application.project_uid, Inspection.is_deleted.is_(False)).count()
    risk_score = 50.0
    risk_score -= min(project.shi or 0, 100) * 0.25
    risk_score += alerts * 8
    risk_score -= min(verified_materials * 2, 10)
    risk_score -= 8 if cert and cert.status in {'issued', 'pending_ceremony', 'issued_active'} else 0
    risk_score -= min(evidences, 10) * 0.8
    risk_score -= min(inspections, 10) * 0.6
    risk_score = max(1.0, min(99.0, round(risk_score, 2)))
    if (project.shi or 0) < product.min_shi:
        decision, premium, rationale = 'declined', product.base_rate_bps + 200, f'Project SHI {project.shi} is below minimum threshold {product.min_shi}.'
    elif risk_score <= 25:
        decision, premium, rationale = 'approved', max(product.base_rate_bps - 40, 0), 'Low risk profile based on SHI, certification status, evidence density, and low alert count.'
    elif risk_score <= 55:
        decision, premium, rationale = 'conditional', product.base_rate_bps + 35, 'Moderate risk profile; terms adjusted upward pending continued monitoring performance.'
    else:
        decision, premium, rationale = 'review', product.base_rate_bps + 90, 'Elevated risk profile due to alerts, insufficient verification depth, or weaker structural indicators.'
    feature_snapshot = {
        'project_shi': project.shi,
        'open_alerts': alerts,
        'has_certificate': bool(cert and cert.status in {'issued', 'pending_ceremony', 'issued_active'}),
        'verified_material_batches': verified_materials,
        'approved_evidence_count': evidences,
        'inspection_count': inspections,
    }
    existing = db.query(RiskDecision).filter(RiskDecision.application_id == application.id).first()
    if existing:
        existing.risk_score = risk_score
        existing.decision = decision
        existing.premium_adjustment_bps = premium
        existing.rationale = rationale
        existing.feature_snapshot = feature_snapshot
        result = existing
    else:
        result = RiskDecision(application_id=application.id, risk_score=risk_score, decision=decision, premium_adjustment_bps=premium, rationale=rationale, feature_snapshot=feature_snapshot)
        db.add(result)
    application.status = 'evaluated'
    db.commit(); db.refresh(result)
    return result
