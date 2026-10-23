
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShareRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    can_edit: bool = False


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    user_id: int
    can_read: bool
    can_edit: bool
    granted_by: int
    revoked_at: datetime | None
    created_at: datetime
