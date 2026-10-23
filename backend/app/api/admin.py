
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.models.audit_event import AuditEvent
from app.models.document import Document
from app.models.incident import Incident
from fastapi import Request
from app.schemas.admin import (
    RoleUpdateRequest,
    AccountStatusUpdateRequest,
)
from app.schemas.auth import UserResponse

class IncidentCreateRequest(BaseModel):
    document_id: int
    description: str = Field(min_length=5, max_length=5000)

router = APIRouter(
    prefix="/api/admin",
    tags=["Administrator"],
    dependencies=[Depends(require_admin)],
)


def ensure_another_active_admin(
    db: Session,
    target: User,
) -> None:
    if target.role != "admin" or not target.is_active:
        return

    active_admins = db.scalar(
        select(func.count(User.id)).where(
            User.role == "admin",
            User.is_active.is_(True),
        )
    ) or 0

    if active_admins <= 1:
        raise HTTPException(
            status_code=409,
            detail="Cannot remove the last active administrator",
        )
class IncidentCreateRequest(BaseModel):
    document_id: int
    description: str = Field(min_length=5, max_length=5000)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(User).order_by(User.id)
    ).all()

@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
)
def update_user_role(
    user_id: int,
    data: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=409,
            detail="You cannot change your own role",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if user.role == "admin" and data.role != "admin":
        ensure_another_active_admin(db, user)

    user.role = data.role
    db.commit()
    db.refresh(user)

    return user


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
)
def update_user_status(
    user_id: int,
    data: AccountStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=409,
            detail="You cannot change your own account status",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not data.is_active:
        ensure_another_active_admin(db, user)

    user.is_active = data.is_active
    db.commit()
    db.refresh(user)

    return user


@router.get("/audit/last-24-hours")
def get_audit_events_last_24_hours(
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.occurred_at >= cutoff)
        .order_by(AuditEvent.occurred_at.desc())
    ).all()

    return events

@router.post("/incidents", status_code=201)
def create_incident(
    data: IncidentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.get(Document, data.document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    incident = Incident(
        document_id=data.document_id,
        reported_by=current_user.id,
        description=data.description,
        status="open",
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


@router.get("/incidents")
def list_incidents(
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Incident)
        .order_by(Incident.detected_at.desc())
    ).all()
