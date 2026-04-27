from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID

from app.db import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type = Column(String(50), nullable=False)
    ip_address = Column(INET, nullable=True)
    # "metadata" conflicts with SQLAlchemy's DeclarativeBase.metadata class attr.
    # Column name stays "metadata" in the DB; Python attribute is log_metadata.
    log_metadata = Column(
        "metadata",
        JSONB(astext_type=String()),
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_event_type", "event_type"),
    )
