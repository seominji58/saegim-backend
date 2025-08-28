from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

if TYPE_CHECKING:
    pass

from app.models.base import Base


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    __table_args__ = (
        Index("idx_email_code", "email", "verification_code"),
        Index(
            "idx_expires", "expires_at", postgresql_where=text("expires_at IS NOT NULL")
        ),
        CheckConstraint("char_length(verification_code) = 6", name="ck_verif_code_len"),
        CheckConstraint(
            "verification_type IN ('signup','change','restore')",
            name="ck_verification_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    verification_code: Mapped[str] = mapped_column(String(6), nullable=False)
    verification_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="signup"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_used: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 관계 정의 - User와 연결 (선택적)
    # signup: user_id = NULL (회원가입 전)
    # change: user_id = 실제값 (이메일 변경 시)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
