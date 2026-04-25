import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field


class StippleParams(BaseModel):
    dot_size: Annotated[float, Field(ge=0.5, le=10.0)] = 2.0
    density: Annotated[float, Field(ge=0.1, le=1.0)] = 0.5
    black_point: Annotated[int, Field(ge=0, le=100)] = 10
    highlights: Annotated[float, Field(ge=0.0, le=1.0)] = 0.3
    shadow_depth: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5


class FileUploadResponse(BaseModel):
    id: uuid.UUID
    mime_type: str
    file_size_bytes: int
    width_px: int
    height_px: int
    megapixels: Decimal
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class FileMetadataResponse(BaseModel):
    id: uuid.UUID
    mime_type: str
    file_size_bytes: int
    width_px: int
    height_px: int
    megapixels: Decimal
    uploaded_at: datetime

    model_config = {"from_attributes": True}
