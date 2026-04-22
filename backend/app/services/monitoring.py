
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import MonitorAlert, Notification, Sensor
from app.services.twin import append_twin_event

def ingest_sensor_reading(db: Session, sensor: Sensor, reading: float, actor_email: str | None = None) -> tuple[Sensor, MonitorAlert | None]:
    sensor.current_reading = reading
    sensor.last_update = datetime.now(timezone.utc).isoformat()
    alert = None
    if reading > sensor.threshold:
        sensor.status = "alert"
        severity = "critical" if reading >= sensor.threshold * 1.5 else "high"
        alert = MonitorAlert(
            sensor_id=sensor.id,
            project_uid=sensor.project_uid,
            component_uid=sensor.component_uid,
            reading=reading,
            threshold=sensor.threshold,
            severity=severity,
            status="open",
            message=f"{sensor.type} reading {reading} exceeded threshold {sensor.threshold}",
        )
        db.add(alert)
        db.flush()
        db.add(Notification(type="monitor_alert", message=alert.message, priority="high", read=False, for_role=["engineer", "inspector", "admin"]))
    else:
        sensor.status = "normal"
    db.commit()
    append_twin_event(
        db,
        project_uid=sensor.project_uid,
        component_uid=sensor.component_uid,
        event_type="MONITOR.ALERT_TRIGGERED" if alert else "MONITOR.READING_CAPTURED",
        aggregate_type="sensor",
        aggregate_uid=str(sensor.id),
        actor_email=actor_email,
        payload={"reading": reading, "threshold": sensor.threshold, "alert_id": alert.id if alert else None},
    )
    return sensor, alert
