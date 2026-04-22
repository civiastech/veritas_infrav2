
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.entities import (
    AuditLog, Bid, Certification, Component, Dispute, Evidence, ExecutionHold, Inspection, Material,
    Milestone, Notification, Payment, Professional, Project, ProjectAssignment, Sensor, Tender,
    SHIMethod, TwinStream, AtlasSubscription, AtlasReport, FinancialProduct, UnderwritingApplication, LearningPath, Course, Enrollment,
    Country, CountryTenant, LaunchProgram, RevenueShareRule, CSTMember, GovernanceCommittee, GovernanceResolution, GovernanceVote, AuthorityDelegation, Regulation, Consultation, ComplianceMapping
)
from app.core.security import get_password_hash
from app.services.twin import ensure_stream, append_twin_event

SEED_FILE = Path(__file__).resolve().parent / "static" / "seed_data.json"

MODEL_MAP = {
    "projects": Project,
    "components": Component,
    "milestones": Milestone,
    "payments": Payment,
    "tenders": Tender,
    "bids": Bid,
    "disputes": Dispute,
    "materials": Material,
    "certifications": Certification,
    "audit_logs": AuditLog,
    "notifications": Notification,
}

def seed_db(db: Session):
    if db.query(Professional).first():
        return
    data = json.loads(SEED_FILE.read_text())

    for item in data["professionals"]:
        item = dict(item)
        plain = item.pop("password")
        item["hashed_password"] = get_password_hash(plain)
        db.add(Professional(**item))
    db.commit()

    for item in data.get("projects", []):
        db.add(Project(**item))
    db.commit()

    for item in data.get("components", []):
        item = dict(item)
        item.setdefault("evidence_required", True)
        item.setdefault("blocked_for_execution", item.get("status") != "verified")
        db.add(Component(**item))
    db.commit()

    for key, model in MODEL_MAP.items():
        if key == "projects" or key == "components":
            continue
        for item in data.get(key, []):
            db.add(model(**item))
    db.commit()

    # active SHI method
    db.add(SHIMethod(version_code="SHI-2-v1", material_weight=0.3, assembly_weight=0.4, environment_weight=0.1, supervision_weight=0.2, active=True))
    db.commit()

    component_map = {c.uid: c for c in db.query(Component).all()}

    for item in data.get("evidence", []):
        comp = component_map[item["component_uid"]]
        payload = dict(item)
        payload["project_uid"] = comp.project_uid
        evidence = Evidence(**payload)
        evidence.manifest_hash = evidence.hash
        db.add(evidence)
    db.commit()

    for item in data.get("inspections", []):
        comp = component_map[item["component_uid"]]
        payload = dict(item)
        payload["project_uid"] = comp.project_uid
        payload["method_id"] = db.query(SHIMethod).first().id
        db.add(Inspection(**payload))
    db.commit()

    for item in data.get("sensors", []):
        comp = component_map[item["component_uid"]]
        payload = dict(item)
        payload["project_uid"] = comp.project_uid
        db.add(Sensor(**payload))
    db.commit()

    # project assignments for ABAC demonstration
    users = {u.email: u for u in db.query(Professional).all()}
    assignments = [
        ("BLD-NGR-LH1-2026", "a.okonkwo@visc.org", "lead_engineer", True),
        ("BLD-NGR-LH1-2026", "m.rodrigues@visc.org", "inspector", True),
        ("BLD-NGR-LH1-2026", "k.mensah@visc.org", "supervisor", False),
        ("BLD-GHA-001-2026", "a.okonkwo@visc.org", "lead_engineer", True),
        ("BLD-NGR-LH1-2026", "admin@visc.org", "admin", True),
    ]
    for project_uid, email, role_on_project, can_approve in assignments:
        if email in users:
            db.add(ProjectAssignment(project_uid=project_uid, professional_id=users[email].id, role_on_project=role_on_project, can_approve=can_approve))
    db.commit()

    # holds and twin streams/events
    for comp in db.query(Component).all():
        ensure_stream(db, comp.project_uid, comp.uid)
        if comp.blocked_for_execution:
            db.add(ExecutionHold(component_uid=comp.uid, project_uid=comp.project_uid, reason_code="EVIDENCE_REQUIRED", status="active", detail="Seeded hold until evidence approved"))
    db.commit()

    for proj in db.query(Project).all():
        ensure_stream(db, proj.uid, None)
        append_twin_event(db, project_uid=proj.uid, event_type="PROJECT_CREATED", aggregate_type="project", aggregate_uid=proj.uid, payload={"project_uid": proj.uid}, actor_email="system@veritas.local")

    # institutional intelligence seed
    admin = users.get('admin@visc.org')
    db.add_all([
        AtlasSubscription(subscriber_name='Lagos State Infrastructure Agency', subscriber_type='government', country_scope='Nigeria', access_tier='institutional', status='active'),
        AtlasSubscription(subscriber_name='Continental Re', subscriber_type='insurer', country_scope='Multi-country', access_tier='enterprise', status='active'),
    ])
    db.add_all([
        FinancialProduct(code='VF-GUARANTEE-STD', name='Structural Integrity Guarantee', category='guarantee', description='Guarantee instrument priced from TWIN/SHI indicators.', base_rate_bps=125, min_shi=82, active=True),
        FinancialProduct(code='VF-INSURE-PREM', name='Certified Asset Premium Cover', category='insurance', description='Enhanced insurance cover for SEAL-ready projects.', base_rate_bps=95, min_shi=85, active=True),
    ])
    db.add_all([
        LearningPath(code='ACA-TRUSTED-STRUCT', title='Trusted Structural Integrity Pathway', target_band='TRUSTED', discipline_scope='Structural Engineering', description='Band-advancement pathway for structural professionals.'),
        LearningPath(code='ACA-HONOR-INSPECT', title='Honor Inspector Pathway', target_band='HONOR', discipline_scope='Inspection', description='Advanced pathway for senior inspectors.'),
    ])
    db.commit()
    db.add_all([
        Course(path_code='ACA-TRUSTED-STRUCT', code='COURSE-CAPTURE-LARGE', title='CAPTURE-LARGE Evidence Mastery', delivery_mode='async', hours=6),
        Course(path_code='ACA-TRUSTED-STRUCT', code='COURSE-SHI-FOUND', title='SHI-2 Scoring Foundations', delivery_mode='cohort', hours=8),
        Course(path_code='ACA-HONOR-INSPECT', code='COURSE-ARB-C', title='ARB-C Evidence Arbitration', delivery_mode='async', hours=5),
    ])
    db.commit()
    ada = users.get('a.okonkwo@visc.org')
    if ada:
        db.add(Enrollment(professional_id=ada.id, course_code='COURSE-CAPTURE-LARGE', path_code='ACA-TRUSTED-STRUCT', status='completed', score=96))
    db.add(AtlasReport(title='Q1 Structural Integrity Portfolio', country_scope='Multi-country', report_type='portfolio', period_label='Q1-2026', generated_by=admin.id if admin else None, payload={'seeded': True}, status='published'))
    db.add(UnderwritingApplication(application_uid='UW-2026-001', project_uid='BLD-GHA-001-2026', product_code='VF-INSURE-PREM', applicant_name='Goldcoast Properties Ltd', requested_amount=12000000, currency='USD', status='submitted', submitted_by=admin.id if admin else None))
    db.commit()
    # governance, country rollout, and regulatory seed
    db.add_all([
        Country(code='NG', name='Nigeria', region='West Africa', launch_stage='lighthouse', readiness_score=86, regulator_appetite='high', status='active'),
        Country(code='GH', name='Ghana', region='West Africa', launch_stage='pilot', readiness_score=79, regulator_appetite='high', status='active'),
        Country(code='AE', name='United Arab Emirates', region='Gulf', launch_stage='strategic', readiness_score=82, regulator_appetite='medium', status='active'),
    ])
    db.commit()

    db.add_all([
        CountryTenant(country_code='NG', operator_name='Veritas Infra Nigeria Ltd', license_type='country_franchise', revenue_share_pct=35, launch_status='pilot', start_date='2026-04-01'),
        CountryTenant(country_code='GH', operator_name='Veritas Infra Ghana Ltd', license_type='country_franchise', revenue_share_pct=32, launch_status='active', start_date='2026-06-01'),
    ])
    db.add_all([
        LaunchProgram(country_code='NG', title='Nigeria National Integrity Standard Launch', phase='regulatory_alignment', progress=62, owner_professional_id=admin.id if admin else None, status='active', notes='Focused on lighthouse projects and ministry engagement.'),
        LaunchProgram(country_code='GH', title='Ghana Evidence-First Procurement Rollout', phase='market_activation', progress=48, owner_professional_id=admin.id if admin else None, status='active', notes='Public-private pilot under procurement reform framing.'),
    ])
    db.add_all([
        RevenueShareRule(country_code='NG', module_code='PAY', local_operator_pct=35, central_platform_pct=55, government_program_pct=10, status='active'),
        RevenueShareRule(country_code='GH', module_code='SEAL', local_operator_pct=30, central_platform_pct=60, government_program_pct=10, status='active'),
    ])
    db.commit()

    engineer = users.get('a.okonkwo@visc.org')
    inspector = users.get('m.rodrigues@visc.org')
    db.add_all([
        CSTMember(professional_id=admin.id if admin else 1, appointment_title='Founding Council Chair', voting_rights=True, term_start='2026-01-01', status='active'),
        CSTMember(professional_id=engineer.id if engineer else 1, appointment_title='Standards Council Member', voting_rights=True, term_start='2026-01-01', status='active'),
        CSTMember(professional_id=inspector.id if inspector else 2, appointment_title='Evidence & Certification Council Member', voting_rights=True, term_start='2026-01-01', status='active'),
    ])
    db.add_all([
        GovernanceCommittee(code='CST-STD', name='Standards & Protocol Committee', scope='Approves evidence, SHI, certification and protocol updates.', status='active'),
        GovernanceCommittee(code='CST-REG', name='Regulatory & Country Expansion Committee', scope='Oversees launch readiness, consultations and country rollout.', status='active'),
    ])
    db.commit()

    db.add_all([
        GovernanceResolution(resolution_uid='RES-2026-001', committee_code='CST-STD', title='Adopt SHI-2 as binding field scoring method', resolution_type='standard', body_text='SHI-2 becomes the mandatory field methodology for active Lighthouse programmes.', status='passed', effective_date='2026-05-01', issued_by=admin.id if admin else None),
        GovernanceResolution(resolution_uid='RES-2026-002', committee_code='CST-REG', title='Approve Nigeria launch programme phase gate', resolution_type='country_launch', body_text='Nigeria advances from lighthouse stage to structured pilot subject to readiness controls.', status='review', effective_date='2026-06-01', issued_by=admin.id if admin else None),
    ])
    db.commit()

    db.add_all([
        GovernanceVote(resolution_uid='RES-2026-001', member_professional_id=admin.id if admin else 1, vote='yes', rationale='Required for standardization.'),
        GovernanceVote(resolution_uid='RES-2026-001', member_professional_id=engineer.id if engineer else 1, vote='yes', rationale='Method matches field execution realities.'),
        GovernanceVote(resolution_uid='RES-2026-002', member_professional_id=inspector.id if inspector else 2, vote='yes', rationale='Pilot controls are sufficient.'),
    ])
    db.add(AuthorityDelegation(authority_code='SEAL_CO_SIGN', delegate_professional_id=engineer.id if engineer else 1, scope='May co-sign project SEAL decisions in West Africa under active protocols.', status='active', valid_until='2027-12-31'))
    db.commit()

    db.add_all([
        Regulation(country_code='NG', regulation_code='NG-CI-2026-DRAFT', title='Construction Integrity Evidence Standard Draft', category='construction_integrity', status='draft', summary='Draft evidence-first protocol for irreversible structural actions.'),
        Regulation(country_code='GH', regulation_code='GH-PROC-2026-DRAFT', title='Evidence-Based Procurement Scoring Draft', category='procurement', status='draft', summary='Draft MATRIX-C procurement framework for structural works.'),
    ])
    db.add_all([
        Consultation(consultation_uid='CONS-NG-2026-001', country_code='NG', title='Nigeria Ministry Consultation on Structural Verification', consultation_type='regulatory', status='open', opened_at_label='2026-04-10'),
        Consultation(consultation_uid='CONS-GH-2026-001', country_code='GH', title='Ghana Procurement Reform Consultation', consultation_type='procurement', status='open', opened_at_label='2026-04-15'),
    ])
    db.add_all([
        ComplianceMapping(country_code='NG', standard_code='NG-CI-2026-DRAFT', module_code='BUILD', requirement_summary='Mandatory CAPTURE-LARGE submission before irreversible structural work.', status='mapped'),
        ComplianceMapping(country_code='NG', standard_code='NG-CI-2026-DRAFT', module_code='PAY', requirement_summary='Milestone releases blocked when SHI threshold is unmet.', status='mapped'),
        ComplianceMapping(country_code='GH', standard_code='GH-PROC-2026-DRAFT', module_code='MARKET', requirement_summary='Tender evaluation to include integrity and capacity scoring.', status='mapped'),
    ])
    db.commit()

def main():
    db = SessionLocal()
    try:
        seed_db(db)
        print("Seed complete")
    finally:
        db.close()

if __name__ == "__main__":
    main()
