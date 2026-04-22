from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import cast, or_, String
from sqlalchemy.orm import Session

from app.api.deps import require_action
from app.db.session import get_db
from app.models.entities import Notification, Professional
from app.schemas.api import ApiList, MutationResult, NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=ApiList)
def list_notifications(
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("notifications:read")),
):
    q = db.query(Notification).filter(Notification.is_deleted.is_(False))

    if current_user.role != "admin":
        q = q.filter(
            or_(
                Notification.for_role.is_(None),
                cast(Notification.for_role, String).like(f'%"{current_user.role}"%'),
            )
        )

    items = q.order_by(Notification.id.desc()).all()
    return {
        "items": [NotificationOut.model_validate(i).model_dump() for i in items],
        "total": len(items),
    }


@router.post("/{notification_id}/read", response_model=MutationResult)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: Professional = Depends(require_action("notifications:read")),
):
    note = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.is_deleted.is_(False),
        )
        .first()
    )

    if not note:
        raise HTTPException(status_code=404, detail="Notification not found")

    note.read = True
    db.commit()
    return MutationResult(message="Notification marked as read")