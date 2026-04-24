import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


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
