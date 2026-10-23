
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentPermission(Base):
    __tablename__ = "document_permissions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    can_read: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    can_edit: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    granted_by: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
