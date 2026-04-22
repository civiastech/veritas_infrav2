
import hashlib
import json
from sqlalchemy.orm import Session
from app.models.entities import TwinEvent, TwinStream

def ensure_stream(db: Session, project_uid: str, component_uid: str | None = None) -> TwinStream:
    stream_key = f"{project_uid}:{component_uid}" if component_uid else project_uid
    stream = db.query(TwinStream).filter(TwinStream.stream_key == stream_key).first()
    if not stream:
        stream = TwinStream(
            stream_key=stream_key,
            project_uid=project_uid,
            component_uid=component_uid,
            stream_type="component" if component_uid else "project",
        )
        db.add(stream)
        db.commit()
        db.refresh(stream)
    return stream

def append_twin_event(
    db: Session,
    *,
    project_uid: str,
    event_type: str,
    aggregate_type: str,
    aggregate_uid: str,
    payload: dict,
    actor_email: str | None = None,
    component_uid: str | None = None,
) -> TwinEvent:
    stream = ensure_stream(db, project_uid, component_uid)
    last = db.query(TwinEvent).filter(TwinEvent.stream_id == stream.id).order_by(TwinEvent.event_index.desc()).first()
    previous_hash = last.current_hash if last else None
    event_index = (last.event_index + 1) if last else 1
    encoded = json.dumps(
        {
            "stream_id": stream.id,
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_uid": aggregate_uid,
            "actor_email": actor_email,
            "payload": payload,
            "event_index": event_index,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    current_hash = hashlib.sha256(encoded).hexdigest()
    event = TwinEvent(
        stream_id=stream.id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_uid=aggregate_uid,
        actor_email=actor_email,
        payload=payload,
        event_index=event_index,
        previous_hash=previous_hash,
        current_hash=current_hash,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
