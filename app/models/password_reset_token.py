from __future__ import annotations
from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime

from sqlalchemy import UniqueConstraint, Index, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        UniqueConstraint("token", name="uq_password_reset_token"),
        Index("idx_user_reset", "user_id", "is_used", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 관계 정의 - SQLAlchemy 2.0 방식
    user: Mapped["User"] = relationship(back_populates="reset_tokens")
