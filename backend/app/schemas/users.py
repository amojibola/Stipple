import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Optional[EmailStr] = None


class QuotaResponse(BaseModel):
    renders_today: int
    renders_this_month: int
    daily_limit: int
    monthly_limit: int
    day_reset_at: date
    month_reset_at: date
    updated_at: datetime

    model_config = {"from_attributes": True}
