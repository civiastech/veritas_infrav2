from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import AuditLog


def record_audit(db: Session, actor: str, action: str, detail: str, ip_address: str | None = None, route: str | None = None) -> None:
    db.add(AuditLog(action=action, actor=actor, detail=detail, timestamp=datetime.now(timezone.utc).isoformat(), ip_address=ip_address, route=route))
    db.commit()
