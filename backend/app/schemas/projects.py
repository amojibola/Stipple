import uuid
from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    source_file_id: Optional[uuid.UUID] = None
    parameters: Optional[dict] = None


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[Annotated[str, Field(min_length=1, max_length=255)]] = None
    parameters: Optional[dict] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_file_id: Optional[uuid.UUID]
    parameters: dict
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    limit: int
    pages: int
