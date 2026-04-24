import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserQuota(Base):
    __tablename__ = "user_quotas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    renders_today: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    renders_this_month: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    daily_limit: Mapped[int] = mapped_column(
        Integer, server_default=text("10"), nullable=False
    )
    monthly_limit: Mapped[int] = mapped_column(
        Integer, server_default=text("100"), nullable=False
    )
    day_reset_at: Mapped[date] = mapped_column(
        Date, server_default=text("CURRENT_DATE"), nullable=False
    )
    month_reset_at: Mapped[date] = mapped_column(
        Date,
        server_default=text("date_trunc('month', CURRENT_DATE)::date"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
