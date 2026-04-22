
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import MonitorAlert, Professional, Sensor
from app.schemas.api import ApiList, MonitorAlertOut, SensorOut, SensorReadingIn
from app.services.audit import record_audit
from app.services.monitoring import ingest_sensor_reading

router = APIRouter(prefix="/monitor", tags=["monitor"])

@router.get("/sensors", response_model=ApiList)
def list_sensors(db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:read"))):
    items = db.query(Sensor).filter(Sensor.is_deleted.is_(False)).order_by(Sensor.id.asc()).all()
    return {"items": [SensorOut.model_validate(i).model_dump() for i in items], "total": len(items)}

@router.post("/readings")
def post_reading(payload: SensorReadingIn, db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:write"))):
    sensor = db.query(Sensor).filter(Sensor.id == payload.sensor_id, Sensor.is_deleted.is_(False)).first()
    if not sensor:
        raise HTTPException(404, "Sensor not found")
    sensor, alert = ingest_sensor_reading(db, sensor, payload.reading, actor_email=current_user.email)
    record_audit(db, current_user.email, "MONITOR_READING_CAPTURED", f"Sensor {sensor.id} updated to {payload.reading}")
    return {"sensor": SensorOut.model_validate(sensor).model_dump(), "alert": MonitorAlertOut.model_validate(alert).model_dump() if alert else None}

@router.get("/alerts", response_model=ApiList)
def list_alerts(db: Session = Depends(get_db), current_user: Professional = Depends(require_action("projects:read"))):
    items = db.query(MonitorAlert).order_by(MonitorAlert.id.desc()).all()
    return {"items": [MonitorAlertOut.model_validate(i).model_dump() for i in items], "total": len(items)}
