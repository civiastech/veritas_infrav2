
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import Milestone, Payment, Project
from app.services.twin import append_twin_event

def evaluate_milestone_gate(db: Session, milestone: Milestone) -> tuple[bool, float, str]:
    project = db.query(Project).filter(Project.uid == milestone.project_uid, Project.is_deleted.is_(False)).first()
    project_shi = project.shi if project else 0
    eligible = project_shi >= milestone.required_shi
    reason = "SHI threshold met" if eligible else f"Project SHI {project_shi:.2f} below required {milestone.required_shi:.2f}"
    return eligible, project_shi, reason

def release_payment(db: Session, milestone: Milestone, actor_email: str) -> Payment:
    eligible, project_shi, reason = evaluate_milestone_gate(db, milestone)
    payment = db.query(Payment).filter(Payment.milestone_id == milestone.id, Payment.is_deleted.is_(False)).first()
    if not payment:
        payment = Payment(
            project_uid=milestone.project_uid,
            milestone_id=milestone.id,
            amount=milestone.amount,
            currency=milestone.currency,
            status="pending",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
    payment.gate_decision = "approved" if eligible else "blocked"
    payment.gate_reason = reason
    if eligible:
        payment.status = "completed"
        payment.released_by = actor_email
        payment.date = datetime.now(timezone.utc).isoformat()
        payment.tx_id = f"AUTO-{payment.id:06d}"
        milestone.status = "released"
        milestone.released_date = payment.date
    else:
        payment.status = "blocked"
    db.commit()
    append_twin_event(
        db,
        project_uid=milestone.project_uid,
        event_type="PAY.RELEASE_COMPLETED" if eligible else "PAY.RELEASE_BLOCKED",
        aggregate_type="milestone",
        aggregate_uid=str(milestone.id),
        actor_email=actor_email,
        payload={
            "milestone_id": milestone.id,
            "payment_id": payment.id,
            "eligible": eligible,
            "reason": reason,
            "project_shi": project_shi,
            "required_shi": milestone.required_shi,
        },
    )
    return payment
