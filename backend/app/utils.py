from sqlalchemy.orm import Session
from app.models.entities import Professional, Project

def get_professional_id_by_email(db: Session, email: str) -> int:
    obj = db.query(Professional).filter(Professional.email == email).first()
    if not obj:
        raise ValueError(f"Professional not found for email={email}")
    return obj.id

def get_project_uid(db: Session, uid: str) -> str:
    obj = db.query(Project).filter(Project.uid == uid).first()
    if not obj:
        raise ValueError(f"Project not found for uid={uid}")
    return obj.uid