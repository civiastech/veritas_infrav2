from sqlalchemy import cast, func, or_, String, text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import (
    Certification,
    Material,
    MonitorAlert,
    Notification,
    Professional,
    Project,
    Tender,
    TwinEvent,
)


def _safe_scalar(query, db: Session, default=0):
    try:
        value = query.scalar()
        return value if value is not None else default
    except (ProgrammingError, SQLAlchemyError):
        db.rollback()
        return default


def _table_exists(db: Session, table_name: str) -> bool:
    try:
        result = db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = :table_name
                )
                """
            ),
            {"table_name": table_name},
        )
        return bool(result.scalar())
    except Exception:
        db.rollback()
        return False


def get_dashboard_summary(db: Session, current_role: str) -> dict:
    total_projects = _safe_scalar(
        db.query(func.count(Project.id)).filter(Project.is_deleted.is_(False)),
        db,
        0,
    )

    active_projects = _safe_scalar(
        db.query(func.count(Project.id)).filter(
            Project.is_deleted.is_(False),
            Project.status == "active",
        ),
        db,
        0,
    )

    total_professionals = _safe_scalar(
        db.query(func.count(Professional.id)).filter(Professional.is_deleted.is_(False)),
        db,
        0,
    )

    avg_shi = _safe_scalar(
        db.query(func.avg(Project.shi)).filter(Project.is_deleted.is_(False)),
        db,
        0,
    )

    total_materials = _safe_scalar(
        db.query(func.count(Material.id)).filter(Material.is_deleted.is_(False)),
        db,
        0,
    )

    open_tenders = _safe_scalar(
        db.query(func.count(Tender.id)).filter(
            Tender.is_deleted.is_(False),
            Tender.status == "open",
        ),
        db,
        0,
    )

    nq = db.query(func.count(Notification.id)).filter(
        Notification.is_deleted.is_(False),
        Notification.read.is_(False),
    )

    if current_role != "admin":
        nq = nq.filter(
            or_(
                Notification.for_role.is_(None),
                cast(Notification.for_role, String).like(f'%"{current_role}"%'),
            )
        )

    unread_notifications = _safe_scalar(nq, db, 0)

    total_project_value_usd = _safe_scalar(
        db.query(func.sum(Project.value)).filter(Project.is_deleted.is_(False)),
        db,
        0,
    )

    total_open_alerts = 0
    if _table_exists(db, "monitor_alerts"):
        total_open_alerts = _safe_scalar(
            db.query(func.count(MonitorAlert.id)).filter(MonitorAlert.status == "open"),
            db,
            0,
        )

    total_certifications = _safe_scalar(
        db.query(func.count(Certification.id)).filter(Certification.is_deleted.is_(False)),
        db,
        0,
    )

    total_twin_events = 0
    if _table_exists(db, "twin_events"):
        total_twin_events = _safe_scalar(
            db.query(func.count(TwinEvent.id)),
            db,
            0,
        )

    return {
        "total_projects": int(total_projects),
        "active_projects": int(active_projects),
        "total_professionals": int(total_professionals),
        "avg_shi": round(float(avg_shi or 0), 2),
        "total_materials": int(total_materials),
        "open_tenders": int(open_tenders),
        "unread_notifications": int(unread_notifications),
        "total_project_value_usd": float(total_project_value_usd or 0),
        "total_open_alerts": int(total_open_alerts),
        "total_certifications": int(total_certifications),
        "total_twin_events": int(total_twin_events),
    }