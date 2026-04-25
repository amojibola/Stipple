import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.images import StippleParams


class JobCreateRequest(BaseModel):
    source_file_id: uuid.UUID
    parameters: StippleParams


class JobCreateResponse(BaseModel):
    job_id: uuid.UUID


class JobStatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    queued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}
