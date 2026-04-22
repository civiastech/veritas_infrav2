
from sqlalchemy.orm import Session
from app.models.entities import SHIMethod, Inspection, Component, Project
from app.services.twin import append_twin_event

def get_active_method(db: Session) -> SHIMethod:
    method = db.query(SHIMethod).filter(SHIMethod.active.is_(True)).order_by(SHIMethod.id.desc()).first()
    if not method:
        method = SHIMethod(version_code="SHI-2-v1", material_weight=0.3, assembly_weight=0.4, environment_weight=0.1, supervision_weight=0.2, active=True)
        db.add(method)
        db.commit()
        db.refresh(method)
    return method

def compute_shi(material_score: float, assembly_score: float, env_score: float, supervision_score: float, method: SHIMethod) -> float:
    score = (
        material_score * method.material_weight
        + assembly_score * method.assembly_weight
        + env_score * method.environment_weight
        + supervision_score * method.supervision_weight
    )
    return round(score, 2)

def apply_inspection(db: Session, inspection: Inspection, actor_email: str | None = None) -> Inspection:
    component = db.query(Component).filter(Component.uid == inspection.component_uid, Component.is_deleted.is_(False)).first()
    if component:
        component.shi = inspection.shi
        component.status = "verified" if inspection.shi >= 75 else "flagged"
        component.approved_by = inspection.inspector_id
    project = db.query(Project).filter(Project.uid == inspection.project_uid, Project.is_deleted.is_(False)).first()
    if project:
        values = [x.shi for x in db.query(Inspection).filter(Inspection.project_uid == project.uid, Inspection.is_deleted.is_(False)).all()]
        project.shi = round(sum(values) / len(values), 2) if values else 0
    db.commit()
    append_twin_event(
        db,
        project_uid=inspection.project_uid,
        component_uid=inspection.component_uid,
        event_type="VISION.SHI_ASSESSED",
        aggregate_type="inspection",
        aggregate_uid=str(inspection.id),
        actor_email=actor_email,
        payload={
            "component_uid": inspection.component_uid,
            "inspection_id": inspection.id,
            "shi": inspection.shi,
            "status": inspection.status,
        },
    )
    return inspection
