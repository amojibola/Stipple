import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width_px: Mapped[int] = mapped_column(Integer, nullable=False)
    height_px: Mapped[int] = mapped_column(Integer, nullable=False)
    megapixels: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __table_args__ = (
        Index("ix_uploaded_files_user_id", "user_id"),
        Index("ix_uploaded_files_original_sha256", "original_sha256"),
        CheckConstraint("file_size_bytes >= 1", name="ck_uploaded_files_file_size_bytes_positive"),
        CheckConstraint("width_px >= 1", name="ck_uploaded_files_width_px_positive"),
        CheckConstraint("height_px >= 1", name="ck_uploaded_files_height_px_positive"),
        CheckConstraint("megapixels >= 0", name="ck_uploaded_files_megapixels_positive"),
    )
