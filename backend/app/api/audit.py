
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.audit_event import AuditEvent

router = APIRouter(
    prefix="/api/audit",
    tags=["Audit"],
)


@router.get("/my-events")
def get_my_audit_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(AuditEvent)
        .filter(AuditEvent.actor_id == current_user.id)
        .order_by(AuditEvent.occurred_at.desc())
        .all()
    )
