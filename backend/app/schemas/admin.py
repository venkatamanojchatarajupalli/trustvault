
from typing import Literal

from pydantic import BaseModel


class RoleUpdateRequest(BaseModel):
    role: Literal["viewer", "editor", "admin"]


class AccountStatusUpdateRequest(BaseModel):
    is_active: bool
