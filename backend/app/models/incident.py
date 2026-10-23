
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), index=True
    )
    reported_by: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30), default="open"
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
