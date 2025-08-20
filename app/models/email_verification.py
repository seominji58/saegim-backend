from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from uuid import uuid4, UUID
from datetime import datetime

from sqlalchemy import Index, CheckConstraint, text, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from app.models.user import User

from app.models.base import Base

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    __table_args__ = (
        Index("idx_email_code", "email", "verification_code"),
        Index("idx_expires", "expires_at", postgresql_where=text("expires_at IS NOT NULL")),
        CheckConstraint("char_length(verification_code) = 6", name="ck_verif_code_len"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    verification_code: Mapped[str] = mapped_column(String(6), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 관계 정의 - User와 연결 (선택적)
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    user: Mapped[Optional["User"]] = relationship(back_populates="email_verifications")
