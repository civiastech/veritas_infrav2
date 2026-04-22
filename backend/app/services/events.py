
from sqlalchemy.orm import Session
from app.models.entities import EventLog

def publish_event(db: Session, event_type: str, payload: dict) -> EventLog:
    event = EventLog(event_type=event_type, payload=payload)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
