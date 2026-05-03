
from datetime import datetime, timezone
from hashlib import sha256
import json
from sqlalchemy.orm import Session
from app.models.entities import Component, Evidence, EvidenceAsset, ExecutionHold, Inspection, Professional
from app.services.storage import store_object
from app.services.twin import append_twin_event
from app.services.vision import apply_inspection, compute_shi, get_active_method

def build_evidence_manifest(evidence: Evidence, assets: list[EvidenceAsset]) -> str:
    payload = {
        "evidence_id": evidence.id,
        "component_uid": evidence.component_uid,
        "project_uid": evidence.project_uid,
        "submitted_by": evidence.submitted_by,
        "timestamp": evidence.timestamp,
        "assets": [{"sha256": a.sha256, "name": a.original_name, "size_bytes": a.size_bytes} for a in assets],
    }
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def create_or_get_hold(db: Session, component: Component) -> ExecutionHold:
    hold = db.query(ExecutionHold).filter(
        ExecutionHold.component_uid == component.uid,
        ExecutionHold.status == "active"
    ).order_by(ExecutionHold.id.desc()).first()
    if hold:
        return hold
    hold = ExecutionHold(component_uid=component.uid, project_uid=component.project_uid, reason_code="EVIDENCE_REQUIRED", status="active", detail="Component blocked until approved evidence exists")
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return hold

def upload_evidence_payload(
    db: Session,
    *,
    component: Component,
    current_user: Professional,
    filename: str,
    payload: bytes,
    content_type: str,
    description: str | None = None,
    type_name: str = "CAPTURE-LARGE",
):
    digest = sha256(payload).hexdigest()
    object_name = f"evidence/{component.project_uid}/{component.uid}/{digest[:12]}_{filename}"
    backend_name, storage_path = store_object(object_name, payload, content_type=content_type)
    evidence = Evidence(
        component_uid=component.uid,
        project_uid=component.project_uid,
        type=type_name,
        images=1,
        submitted_by=current_user.id,
        description=description,
        timestamp=datetime.now(timezone.utc).isoformat(),
        hash=digest,
        status="submitted",
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    asset = EvidenceAsset(
        evidence_id=evidence.id,
        original_name=filename,
        storage_path=storage_path,
        storage_backend=backend_name,
        content_type=content_type,
        sha256=digest,
        size_bytes=len(payload),
        immutable=True,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    evidence.manifest_hash = build_evidence_manifest(evidence, [asset])
    db.commit()
    append_twin_event(
        db,
        project_uid=component.project_uid,
        component_uid=component.uid,
        event_type="BUILD.EVIDENCE_SUBMITTED",
        aggregate_type="evidence",
        aggregate_uid=str(evidence.id),
        actor_email=current_user.email,
        payload={"evidence_id": evidence.id, "sha256": digest, "manifest_hash": evidence.manifest_hash},
    )
    return evidence, asset

def approve_evidence(db: Session, evidence: Evidence, approver: Professional) -> Evidence:
    evidence.status = "approved"
    evidence.approved_by = approver.id
    component = db.query(Component).filter(Component.uid == evidence.component_uid, Component.is_deleted.is_(False)).first()
    if component:
        component.blocked_for_execution = False
        component.status = "evidence-approved"
        active_hold = db.query(ExecutionHold).filter(ExecutionHold.component_uid == component.uid, ExecutionHold.status == "active").first()
        if active_hold:
            active_hold.status = "cleared"
            active_hold.cleared_by = approver.id
    db.commit()
    append_twin_event(
        db,
        project_uid=evidence.project_uid,
        component_uid=evidence.component_uid,
        event_type="BUILD.EVIDENCE_APPROVED",
        aggregate_type="evidence",
        aggregate_uid=str(evidence.id),
        actor_email=approver.email,
        payload={"evidence_id": evidence.id, "status": evidence.status},
    )
    return evidence

def create_inspection_from_scores(
    db: Session,
    *,
    component: Component,
    inspector: Professional,
    material_score: float,
    assembly_score: float,
    env_score: float,
    supervision_score: float,
    ai_flags: int,
    reason_tag: str | None,
) -> Inspection:
    method = get_active_method(db)
    shi = compute_shi(material_score, assembly_score, env_score, supervision_score, method)
    inspection = Inspection(
        component_uid=component.uid,
        project_uid=component.project_uid,
        inspector_id=inspector.id,
        method_id=method.id,
        shi=shi,
        material_score=material_score,
        assembly_score=assembly_score,
        env_score=env_score,
        supervision_score=supervision_score,
        ai_flags=ai_flags,
        reason_tag=reason_tag,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="passed" if shi >= 75 else "failed",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    result = apply_inspection(db, inspection, actor_email=inspector.email)
    try:
        from app.services.pri_engine import recompute_pri
        recompute_pri(db, inspector.id)
    except Exception:
        pass
    return result
