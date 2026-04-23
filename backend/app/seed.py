import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.entities import (
    AtlasReport,
    AtlasSubscription,
    AuditLog,
    AuthorityDelegation,
    Bid,
    CSTMember,
    Certification,
    ComplianceMapping,
    Component,
    Consultation,
    Country,
    CountryTenant,
    Course,
    Dispute,
    Enrollment,
    Evidence,
    ExecutionHold,
    FinancialProduct,
    GovernanceCommittee,
    GovernanceResolution,
    GovernanceVote,
    Inspection,
    LaunchProgram,
    LearningPath,
    Material,
    Milestone,
    Notification,
    Payment,
    Professional,
    Project,
    ProjectAssignment,
    Regulation,
    RevenueShareRule,
    SHIMethod,
    Sensor,
    Tender,
    UnderwritingApplication,
)
from app.services.twin import append_twin_event, ensure_stream

SEED_FILE = Path(__file__).resolve().parent / "static" / "seed_data.json"

DEFAULT_ADMIN_EMAIL = os.getenv("FIRST_SUPERUSER_EMAIL", "admin@visc.org").strip().lower()
DEFAULT_ADMIN_PASSWORD = os.getenv("FIRST_SUPERUSER_PASSWORD", "AdminPass123!")

MODEL_MAP: dict[str, type] = {
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


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def table_exists(db: Session, table_name: str) -> bool:
    inspector = inspect(db.bind)
    return table_name in inspector.get_table_names()


def load_seed_data() -> dict[str, Any]:
    if not SEED_FILE.exists():
        print(f"Seed file not found: {SEED_FILE}")
        return {}
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


def run_seed_block(db: Session, name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        db.commit()
        print(f"{name}: ok")
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"{name}: skipped due to database error -> {exc}")
    except Exception as exc:
        db.rollback()
        print(f"{name}: skipped due to error -> {exc}")


def users_map(db: Session) -> dict[str, Professional]:
    if not table_exists(db, "professionals"):
        return {}
    return {normalize_email(u.email): u for u in db.query(Professional).all()}


def ensure_admin_user(db: Session) -> None:
    if not table_exists(db, "professionals"):
        print("admin bootstrap: professionals table missing")
        return

    admin = (
        db.query(Professional)
        .filter(Professional.email == DEFAULT_ADMIN_EMAIL)
        .first()
    )

    if admin:
        changed = False

        if not admin.name:
            admin.name = "Admin User"
            changed = True

        # CRITICAL: do not overwrite password on reseed if it already exists
        if not admin.hashed_password:
            admin.hashed_password = get_password_hash(DEFAULT_ADMIN_PASSWORD)
            changed = True

        if admin.role != "admin":
            admin.role = "admin"
            changed = True

        if not admin.band:
            admin.band = "HONOR"
            changed = True

        if not admin.discipline:
            admin.discipline = "Platform Administration"
            changed = True

        if not admin.country:
            admin.country = "International"
            changed = True

        if hasattr(admin, "projects") and admin.projects is None:
            admin.projects = 0
            changed = True

        if hasattr(admin, "shi_avg") and admin.shi_avg is None:
            admin.shi_avg = 0
            changed = True

        if hasattr(admin, "pri_score") and admin.pri_score is None:
            admin.pri_score = 0
            changed = True

        if hasattr(admin, "active") and admin.active is None:
            admin.active = True
            changed = True

        if hasattr(admin, "failed_login_attempts") and admin.failed_login_attempts is None:
            admin.failed_login_attempts = 0
            changed = True

        if hasattr(admin, "mfa_enabled") and admin.mfa_enabled is None:
            admin.mfa_enabled = False
            changed = True

        if changed and hasattr(admin, "updated_at"):
            admin.updated_at = utcnow()

        db.flush()
        return

    admin = Professional(
        name="Admin User",
        email=DEFAULT_ADMIN_EMAIL,
        hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
        role="admin",
        band="HONOR",
        discipline="Platform Administration",
        country="International",
        projects=0,
        shi_avg=0,
        pri_score=0,
        active=True,
        mfa_enabled=False,
        failed_login_attempts=0,
        created_at=utcnow(),
        updated_at=utcnow(),
        is_deleted=False,
        deleted_at=None,
    )
    db.add(admin)
    db.flush()


def seed_professionals(db: Session, data: dict[str, Any]) -> None:
    if not table_exists(db, "professionals"):
        return

    for item in data.get("professionals", []):
        payload = dict(item)
        email = normalize_email(payload.get("email"))
        if not email:
            continue

        plain = payload.pop("password", None)
        payload["email"] = email

        payload.setdefault("band", "TRUSTED")
        payload.setdefault("discipline", "General Engineering")
        payload.setdefault("country", "International")
        payload.setdefault("projects", 0)
        payload.setdefault("shi_avg", 0)
        payload.setdefault("pri_score", 0)
        payload.setdefault("active", True)
        payload.setdefault("mfa_enabled", False)
        payload.setdefault("failed_login_attempts", 0)

        existing = db.query(Professional).filter(Professional.email == email).first()

        if existing:
            changed = False

            # update only missing / safe fields
            for key, value in payload.items():
                current = getattr(existing, key, None)

                if key in {"role"} and email == DEFAULT_ADMIN_EMAIL:
                    if current != "admin":
                        setattr(existing, key, "admin")
                        changed = True
                    continue

                if current is None or current == "":
                    setattr(existing, key, value)
                    changed = True

            # CRITICAL: do not overwrite existing password hash on reseed
            if not getattr(existing, "hashed_password", None) and plain:
                existing.hashed_password = get_password_hash(plain)
                changed = True

            if changed and hasattr(existing, "updated_at"):
                existing.updated_at = utcnow()

            continue

        if plain:
            payload["hashed_password"] = get_password_hash(plain)
        else:
            payload["hashed_password"] = get_password_hash("ChangeMe123!")

        payload.setdefault("created_at", utcnow())
        payload.setdefault("updated_at", utcnow())
        payload.setdefault("is_deleted", False)
        payload.setdefault("deleted_at", None)

        db.add(Professional(**payload))

    ensure_admin_user(db)


def seed_projects(db: Session, data: dict[str, Any]) -> None:
    if not table_exists(db, "projects"):
        return

    for item in data.get("projects", []):
        uid = item.get("uid")
        if not uid:
            continue

        existing = db.query(Project).filter(Project.uid == uid).first()
        if existing:
            for key, value in item.items():
                setattr(existing, key, value)
        else:
            db.add(Project(**item))


def seed_components(db: Session, data: dict[str, Any]) -> None:
    if not table_exists(db, "components"):
        return

    for item in data.get("components", []):
        payload = dict(item)
        uid = payload.get("uid")
        if not uid:
            continue

        payload.setdefault("evidence_required", True)
        payload.setdefault("blocked_for_execution", payload.get("status") != "verified")

        existing = db.query(Component).filter(Component.uid == uid).first()
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(Component(**payload))


def seed_core_model_map_tables(db: Session, data: dict[str, Any]) -> None:
    natural_keys = {
        "milestones": "name",
        "payments": "payment_ref",
        "tenders": "tender_no",
        "bids": "bid_no",
        "disputes": "dispute_ref",
        "materials": "batch_no",
        "certifications": "certificate_no",
        "audit_logs": None,
        "notifications": None,
    }

    for key, model in MODEL_MAP.items():
        if key in {"projects", "components"}:
            continue

        table_name = getattr(model, "__tablename__", None)
        if not table_name or not table_exists(db, table_name):
            continue

        natural_key = natural_keys.get(key)
        for item in data.get(key, []):
            existing = None
            if natural_key and item.get(natural_key) is not None:
                existing = (
                    db.query(model)
                    .filter(getattr(model, natural_key) == item[natural_key])
                    .first()
                )

            if existing:
                for field, value in item.items():
                    setattr(existing, field, value)
            else:
                db.add(model(**item))


def seed_shi_method(db: Session) -> None:
    if not table_exists(db, "shi_methods"):
        print("shi_methods table missing; skipping SHI bootstrap")
        return

    existing = db.query(SHIMethod).filter(SHIMethod.version_code == "SHI-2-v1").first()
    if existing:
        existing.material_weight = 0.3
        existing.assembly_weight = 0.4
        existing.environment_weight = 0.1
        existing.supervision_weight = 0.2
        existing.active = True
        return

    db.add(
        SHIMethod(
            version_code="SHI-2-v1",
            material_weight=0.3,
            assembly_weight=0.4,
            environment_weight=0.1,
            supervision_weight=0.2,
            active=True,
        )
    )


def get_active_shi_method(db: Session) -> SHIMethod | None:
    if not table_exists(db, "shi_methods"):
        return None
    return db.query(SHIMethod).filter(SHIMethod.active.is_(True)).first()


def component_lookup(db: Session) -> dict[str, Component]:
    if not table_exists(db, "components"):
        return {}
    return {c.uid: c for c in db.query(Component).all()}


def seed_evidence(db: Session, data: dict[str, Any]) -> None:
    if not table_exists(db, "evidence"):
        return

    components = component_lookup(db)

    for item in data.get("evidence", []):
        component_uid = item.get("component_uid")
        comp = components.get(component_uid)
        if not comp:
            continue

        existing = None
        hash_value = item.get("hash")
        if hash_value and hasattr(Evidence, "hash"):
            existing = db.query(Evidence).filter(Evidence.hash == hash_value).first()

        if existing:
            payload = dict(item)
            payload["project_uid"] = comp.project_uid
            for key, value in payload.items():
                setattr(existing, key, value)
            if hasattr(existing, "manifest_hash") and getattr(existing, "manifest_hash", None) != hash_value:
                existing.manifest_hash = hash_value
            continue

        payload = dict(item)
        payload["project_uid"] = comp.project_uid
        evidence = Evidence(**payload)
        if hasattr(evidence, "manifest_hash") and hasattr(evidence, "hash"):
            evidence.manifest_hash = evidence.hash
        db.add(evidence)


def seed_inspections(db: Session, data: dict[str, Any]) -> None:
    if not table_exists(db, "inspections"):
        return

    components = component_lookup(db)
    shi_method = get_active_shi_method(db)

    for item in data.get("inspections", []):
        component_uid = item.get("component_uid")
        comp = components.get(component_uid)
        if not comp:
            continue

        existing = None
        if item.get("uid") and hasattr(Inspection, "uid"):
            existing = db.query(Inspection).filter(Inspection.uid == item["uid"]).first()

        payload = dict(item)
        payload["project_uid"] = comp.project_uid
        if shi_method and table_exists(db, "shi_methods"):
            payload["method_id"] = shi_method.id

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(Inspection(**payload))


def seed_sensors(db: Session, data: dict[str, Any]) -> None:
    if not table_exists(db, "sensors"):
        return

    components = component_lookup(db)

    for item in data.get("sensors", []):
        component_uid = item.get("component_uid")
        comp = components.get(component_uid)
        if not comp:
            continue

        existing = None
        if item.get("uid") and hasattr(Sensor, "uid"):
            existing = db.query(Sensor).filter(Sensor.uid == item["uid"]).first()

        payload = dict(item)
        payload["project_uid"] = comp.project_uid

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(Sensor(**payload))


def seed_project_assignments(db: Session) -> None:
    if not table_exists(db, "project_assignments") or not table_exists(db, "professionals"):
        return

    users = users_map(db)
    assignments = [
        ("BLD-NGR-LH1-2026", "a.okonkwo@visc.org", "lead_engineer", True),
        ("BLD-NGR-LH1-2026", "m.rodrigues@visc.org", "inspector", True),
        ("BLD-NGR-LH1-2026", "k.mensah@visc.org", "supervisor", False),
        ("BLD-GHA-001-2026", "a.okonkwo@visc.org", "lead_engineer", True),
        ("BLD-NGR-LH1-2026", DEFAULT_ADMIN_EMAIL, "admin", True),
    ]

    for project_uid, email, role_on_project, can_approve in assignments:
        user = users.get(normalize_email(email))
        if not user:
            continue

        existing = (
            db.query(ProjectAssignment)
            .filter(
                ProjectAssignment.project_uid == project_uid,
                ProjectAssignment.professional_id == user.id,
            )
            .first()
        )
        if existing:
            existing.role_on_project = role_on_project
            existing.can_approve = can_approve
        else:
            db.add(
                ProjectAssignment(
                    project_uid=project_uid,
                    professional_id=user.id,
                    role_on_project=role_on_project,
                    can_approve=can_approve,
                )
            )


def seed_holds_and_twin(db: Session) -> None:
    if not table_exists(db, "components"):
        return

    has_execution_holds = table_exists(db, "execution_holds")
    has_twin_streams = table_exists(db, "twin_streams")

    for comp in db.query(Component).all():
        if has_twin_streams:
            ensure_stream(db, comp.project_uid, comp.uid)

        if has_execution_holds and comp.blocked_for_execution:
            existing = (
                db.query(ExecutionHold)
                .filter(
                    ExecutionHold.component_uid == comp.uid,
                    ExecutionHold.reason_code == "EVIDENCE_REQUIRED",
                    ExecutionHold.status == "active",
                )
                .first()
            )
            if not existing:
                db.add(
                    ExecutionHold(
                        component_uid=comp.uid,
                        project_uid=comp.project_uid,
                        reason_code="EVIDENCE_REQUIRED",
                        status="active",
                        detail="Seeded hold until evidence approved",
                    )
                )

    if not table_exists(db, "projects"):
        return

    for proj in db.query(Project).all():
        if has_twin_streams:
            ensure_stream(db, proj.uid, None)
            append_twin_event(
                db,
                project_uid=proj.uid,
                event_type="PROJECT_CREATED",
                aggregate_type="project",
                aggregate_uid=proj.uid,
                payload={"project_uid": proj.uid},
                actor_email="system@veritas.local",
            )


def seed_atlas_and_finance(db: Session, users: dict[str, Professional]) -> None:
    admin = users.get(DEFAULT_ADMIN_EMAIL)

    if table_exists(db, "atlas_subscriptions"):
        atlas_rows = [
            {
                "subscriber_name": "Lagos State Infrastructure Agency",
                "subscriber_type": "government",
                "country_scope": "Nigeria",
                "access_tier": "institutional",
                "status": "active",
            },
            {
                "subscriber_name": "Continental Re",
                "subscriber_type": "insurer",
                "country_scope": "Multi-country",
                "access_tier": "enterprise",
                "status": "active",
            },
        ]
        for row in atlas_rows:
            existing = (
                db.query(AtlasSubscription)
                .filter(AtlasSubscription.subscriber_name == row["subscriber_name"])
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(AtlasSubscription(**row))

    if table_exists(db, "financial_products"):
        product_rows = [
            {
                "code": "VF-GUARANTEE-STD",
                "name": "Structural Integrity Guarantee",
                "category": "guarantee",
                "description": "Guarantee instrument priced from TWIN/SHI indicators.",
                "base_rate_bps": 125,
                "min_shi": 82,
                "active": True,
            },
            {
                "code": "VF-INSURE-PREM",
                "name": "Certified Asset Premium Cover",
                "category": "insurance",
                "description": "Enhanced insurance cover for SEAL-ready projects.",
                "base_rate_bps": 95,
                "min_shi": 85,
                "active": True,
            },
        ]
        for row in product_rows:
            existing = db.query(FinancialProduct).filter(FinancialProduct.code == row["code"]).first()
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(FinancialProduct(**row))

    if table_exists(db, "atlas_reports"):
        existing = (
            db.query(AtlasReport)
            .filter(AtlasReport.title == "Q1 Structural Integrity Portfolio")
            .first()
        )
        payload = {
            "title": "Q1 Structural Integrity Portfolio",
            "country_scope": "Multi-country",
            "report_type": "portfolio",
            "period_label": "Q1-2026",
            "generated_by": admin.id if admin else None,
            "payload": {"seeded": True},
            "status": "published",
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(AtlasReport(**payload))

    if table_exists(db, "underwriting_applications"):
        existing = (
            db.query(UnderwritingApplication)
            .filter(UnderwritingApplication.application_uid == "UW-2026-001")
            .first()
        )
        payload = {
            "application_uid": "UW-2026-001",
            "project_uid": "BLD-GHA-001-2026",
            "product_code": "VF-INSURE-PREM",
            "applicant_name": "Goldcoast Properties Ltd",
            "requested_amount": 12000000,
            "currency": "USD",
            "status": "submitted",
            "submitted_by": admin.id if admin else None,
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(UnderwritingApplication(**payload))


def seed_learning(db: Session, users: dict[str, Professional]) -> None:
    if table_exists(db, "learning_paths"):
        path_rows = [
            {
                "code": "ACA-TRUSTED-STRUCT",
                "title": "Trusted Structural Integrity Pathway",
                "target_band": "TRUSTED",
                "discipline_scope": "Structural Engineering",
                "description": "Band-advancement pathway for structural professionals.",
            },
            {
                "code": "ACA-HONOR-INSPECT",
                "title": "Honor Inspector Pathway",
                "target_band": "HONOR",
                "discipline_scope": "Inspection",
                "description": "Advanced pathway for senior inspectors.",
            },
        ]
        for row in path_rows:
            existing = db.query(LearningPath).filter(LearningPath.code == row["code"]).first()
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(LearningPath(**row))

    if table_exists(db, "courses"):
        course_rows = [
            {
                "path_code": "ACA-TRUSTED-STRUCT",
                "code": "COURSE-CAPTURE-LARGE",
                "title": "CAPTURE-LARGE Evidence Mastery",
                "delivery_mode": "async",
                "hours": 6,
            },
            {
                "path_code": "ACA-TRUSTED-STRUCT",
                "code": "COURSE-SHI-FOUND",
                "title": "SHI-2 Scoring Foundations",
                "delivery_mode": "cohort",
                "hours": 8,
            },
            {
                "path_code": "ACA-HONOR-INSPECT",
                "code": "COURSE-ARB-C",
                "title": "ARB-C Evidence Arbitration",
                "delivery_mode": "async",
                "hours": 5,
            },
        ]
        for row in course_rows:
            existing = db.query(Course).filter(Course.code == row["code"]).first()
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(Course(**row))

    if table_exists(db, "enrollments"):
        ada = users.get("a.okonkwo@visc.org")
        if ada:
            existing = (
                db.query(Enrollment)
                .filter(
                    Enrollment.professional_id == ada.id,
                    Enrollment.course_code == "COURSE-CAPTURE-LARGE",
                )
                .first()
            )
            payload = {
                "professional_id": ada.id,
                "course_code": "COURSE-CAPTURE-LARGE",
                "path_code": "ACA-TRUSTED-STRUCT",
                "status": "completed",
                "score": 96,
            }
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
            else:
                db.add(Enrollment(**payload))


def seed_country_and_governance(db: Session, users: dict[str, Professional]) -> None:
    admin = users.get(DEFAULT_ADMIN_EMAIL)
    engineer = users.get("a.okonkwo@visc.org")
    inspector_user = users.get("m.rodrigues@visc.org")

    if table_exists(db, "countries"):
        country_rows = [
            {
                "code": "NG",
                "name": "Nigeria",
                "region": "West Africa",
                "launch_stage": "lighthouse",
                "readiness_score": 86,
                "regulator_appetite": "high",
                "status": "active",
            },
            {
                "code": "GH",
                "name": "Ghana",
                "region": "West Africa",
                "launch_stage": "pilot",
                "readiness_score": 79,
                "regulator_appetite": "high",
                "status": "active",
            },
            {
                "code": "AE",
                "name": "United Arab Emirates",
                "region": "Gulf",
                "launch_stage": "strategic",
                "readiness_score": 82,
                "regulator_appetite": "medium",
                "status": "active",
            },
        ]
        for row in country_rows:
            existing = db.query(Country).filter(Country.code == row["code"]).first()
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(Country(**row))

    if table_exists(db, "country_tenants"):
        tenant_rows = [
            {
                "country_code": "NG",
                "operator_name": "Veritas Infra Nigeria Ltd",
                "license_type": "country_franchise",
                "revenue_share_pct": 35,
                "launch_status": "pilot",
                "start_date": date(2026, 4, 1),
            },
            {
                "country_code": "GH",
                "operator_name": "Veritas Infra Ghana Ltd",
                "license_type": "country_franchise",
                "revenue_share_pct": 32,
                "launch_status": "active",
                "start_date": date(2026, 6, 1),
            },
        ]
        for row in tenant_rows:
            existing = (
                db.query(CountryTenant)
                .filter(
                    CountryTenant.country_code == row["country_code"],
                    CountryTenant.operator_name == row["operator_name"],
                )
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(CountryTenant(**row))

    if table_exists(db, "launch_programs"):
        launch_rows = [
            {
                "country_code": "NG",
                "title": "Nigeria National Integrity Standard Launch",
                "phase": "regulatory_alignment",
                "progress": 62,
                "owner_professional_id": admin.id if admin else None,
                "status": "active",
                "notes": "Focused on lighthouse projects and ministry engagement.",
            },
            {
                "country_code": "GH",
                "title": "Ghana Evidence-First Procurement Rollout",
                "phase": "market_activation",
                "progress": 48,
                "owner_professional_id": admin.id if admin else None,
                "status": "active",
                "notes": "Public-private pilot under procurement reform framing.",
            },
        ]
        for row in launch_rows:
            existing = (
                db.query(LaunchProgram)
                .filter(
                    LaunchProgram.country_code == row["country_code"],
                    LaunchProgram.title == row["title"],
                )
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(LaunchProgram(**row))

    if table_exists(db, "revenue_share_rules"):
        rules = [
            {
                "country_code": "NG",
                "module_code": "PAY",
                "local_operator_pct": 35,
                "central_platform_pct": 55,
                "government_program_pct": 10,
                "status": "active",
            },
            {
                "country_code": "GH",
                "module_code": "SEAL",
                "local_operator_pct": 30,
                "central_platform_pct": 60,
                "government_program_pct": 10,
                "status": "active",
            },
        ]
        for row in rules:
            existing = (
                db.query(RevenueShareRule)
                .filter(
                    RevenueShareRule.country_code == row["country_code"],
                    RevenueShareRule.module_code == row["module_code"],
                )
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(RevenueShareRule(**row))

    if table_exists(db, "cst_members"):
        members = [
            {
                "professional_id": admin.id if admin else 1,
                "appointment_title": "Founding Council Chair",
                "voting_rights": True,
                "term_start": date(2026, 1, 1),
                "status": "active",
            },
            {
                "professional_id": engineer.id if engineer else 1,
                "appointment_title": "Standards Council Member",
                "voting_rights": True,
                "term_start": date(2026, 1, 1),
                "status": "active",
            },
            {
                "professional_id": inspector_user.id if inspector_user else 2,
                "appointment_title": "Evidence & Certification Council Member",
                "voting_rights": True,
                "term_start": date(2026, 1, 1),
                "status": "active",
            },
        ]
        for row in members:
            existing = (
                db.query(CSTMember)
                .filter(
                    CSTMember.professional_id == row["professional_id"],
                    CSTMember.appointment_title == row["appointment_title"],
                )
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(CSTMember(**row))

    if table_exists(db, "governance_committees"):
        committees = [
            {
                "code": "CST-STD",
                "name": "Standards & Protocol Committee",
                "scope": "Approves evidence, SHI, certification and protocol updates.",
                "status": "active",
            },
            {
                "code": "CST-REG",
                "name": "Regulatory & Country Expansion Committee",
                "scope": "Oversees launch readiness, consultations and country rollout.",
                "status": "active",
            },
        ]
        for row in committees:
            existing = db.query(GovernanceCommittee).filter(GovernanceCommittee.code == row["code"]).first()
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(GovernanceCommittee(**row))

    if table_exists(db, "governance_resolutions"):
        resolutions = [
            {
                "resolution_uid": "RES-2026-001",
                "committee_code": "CST-STD",
                "title": "Adopt SHI-2 as binding field scoring method",
                "resolution_type": "standard",
                "body_text": "SHI-2 becomes the mandatory field methodology for active Lighthouse programmes.",
                "status": "passed",
                "effective_date": date(2026, 5, 1),
                "issued_by": admin.id if admin else None,
            },
            {
                "resolution_uid": "RES-2026-002",
                "committee_code": "CST-REG",
                "title": "Approve Nigeria launch programme phase gate",
                "resolution_type": "country_launch",
                "body_text": "Nigeria advances from lighthouse stage to structured pilot subject to readiness controls.",
                "status": "review",
                "effective_date": date(2026, 6, 1),
                "issued_by": admin.id if admin else None,
            },
        ]
        for row in resolutions:
            existing = (
                db.query(GovernanceResolution)
                .filter(GovernanceResolution.resolution_uid == row["resolution_uid"])
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(GovernanceResolution(**row))

    if table_exists(db, "governance_votes"):
        votes = [
            {
                "resolution_uid": "RES-2026-001",
                "member_professional_id": admin.id if admin else 1,
                "vote": "yes",
                "rationale": "Required for standardization.",
            },
            {
                "resolution_uid": "RES-2026-001",
                "member_professional_id": engineer.id if engineer else 1,
                "vote": "yes",
                "rationale": "Method matches field execution realities.",
            },
            {
                "resolution_uid": "RES-2026-002",
                "member_professional_id": inspector_user.id if inspector_user else 2,
                "vote": "yes",
                "rationale": "Pilot controls are sufficient.",
            },
        ]
        for row in votes:
            existing = (
                db.query(GovernanceVote)
                .filter(
                    GovernanceVote.resolution_uid == row["resolution_uid"],
                    GovernanceVote.member_professional_id == row["member_professional_id"],
                )
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(GovernanceVote(**row))

    if table_exists(db, "authority_delegations"):
        payload = {
            "authority_code": "SEAL_CO_SIGN",
            "delegate_professional_id": engineer.id if engineer else 1,
            "scope": "May co-sign project SEAL decisions in West Africa under active protocols.",
            "status": "active",
            "valid_until": date(2027, 12, 31),
        }
        existing = (
            db.query(AuthorityDelegation)
            .filter(
                AuthorityDelegation.authority_code == payload["authority_code"],
                AuthorityDelegation.delegate_professional_id == payload["delegate_professional_id"],
            )
            .first()
        )
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            db.add(AuthorityDelegation(**payload))

    if table_exists(db, "regulations"):
        rows = [
            {
                "country_code": "NG",
                "regulation_code": "NG-CI-2026-DRAFT",
                "title": "Construction Integrity Evidence Standard Draft",
                "category": "construction_integrity",
                "status": "draft",
                "summary": "Draft evidence-first protocol for irreversible structural actions.",
            },
            {
                "country_code": "GH",
                "regulation_code": "GH-PROC-2026-DRAFT",
                "title": "Evidence-Based Procurement Scoring Draft",
                "category": "procurement",
                "status": "draft",
                "summary": "Draft MATRIX-C procurement framework for structural works.",
            },
        ]
        for row in rows:
            existing = db.query(Regulation).filter(Regulation.regulation_code == row["regulation_code"]).first()
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(Regulation(**row))

    if table_exists(db, "consultations"):
        rows = [
            {
                "consultation_uid": "CONS-NG-2026-001",
                "country_code": "NG",
                "title": "Nigeria Ministry Consultation on Structural Verification",
                "consultation_type": "regulatory",
                "status": "open",
                "opened_at_label": "2026-04-10",
            },
            {
                "consultation_uid": "CONS-GH-2026-001",
                "country_code": "GH",
                "title": "Ghana Procurement Reform Consultation",
                "consultation_type": "procurement",
                "status": "open",
                "opened_at_label": "2026-04-15",
            },
        ]
        for row in rows:
            existing = (
                db.query(Consultation)
                .filter(Consultation.consultation_uid == row["consultation_uid"])
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(Consultation(**row))

    if table_exists(db, "compliance_mappings"):
        rows = [
            {
                "country_code": "NG",
                "standard_code": "NG-CI-2026-DRAFT",
                "module_code": "BUILD",
                "requirement_summary": "Mandatory CAPTURE-LARGE submission before irreversible structural work.",
                "status": "mapped",
            },
            {
                "country_code": "NG",
                "standard_code": "NG-CI-2026-DRAFT",
                "module_code": "PAY",
                "requirement_summary": "Milestone releases blocked when SHI threshold is unmet.",
                "status": "mapped",
            },
            {
                "country_code": "GH",
                "standard_code": "GH-PROC-2026-DRAFT",
                "module_code": "MARKET",
                "requirement_summary": "Tender evaluation to include integrity and capacity scoring.",
                "status": "mapped",
            },
        ]
        for row in rows:
            existing = (
                db.query(ComplianceMapping)
                .filter(
                    ComplianceMapping.country_code == row["country_code"],
                    ComplianceMapping.standard_code == row["standard_code"],
                    ComplianceMapping.module_code == row["module_code"],
                )
                .first()
            )
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(ComplianceMapping(**row))


def seed_db(db: Session, mode: str = "all") -> None:
    data = load_seed_data()

    run_seed_block(db, "admin bootstrap", lambda: ensure_admin_user(db))

    if mode in {"all", "core"}:
        run_seed_block(db, "professionals", lambda: seed_professionals(db, data))
        run_seed_block(db, "projects", lambda: seed_projects(db, data))
        run_seed_block(db, "components", lambda: seed_components(db, data))
        run_seed_block(db, "core model map", lambda: seed_core_model_map_tables(db, data))
        run_seed_block(db, "shi method", lambda: seed_shi_method(db))
        run_seed_block(db, "evidence", lambda: seed_evidence(db, data))
        run_seed_block(db, "inspections", lambda: seed_inspections(db, data))
        run_seed_block(db, "sensors", lambda: seed_sensors(db, data))
        run_seed_block(db, "project assignments", lambda: seed_project_assignments(db))
        run_seed_block(db, "holds and twin", lambda: seed_holds_and_twin(db))

    if mode in {"all", "advanced"}:
        run_seed_block(db, "atlas and finance", lambda: seed_atlas_and_finance(db, users_map(db)))
        run_seed_block(db, "learning", lambda: seed_learning(db, users_map(db)))
        run_seed_block(db, "country and governance", lambda: seed_country_and_governance(db, users_map(db)))


def main() -> None:
    mode = os.getenv("SEED_MODE", "all").strip().lower()
    db = SessionLocal()
    try:
        seed_db(db, mode=mode)
        print("Seed complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()