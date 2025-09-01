"""
다이어리 모델
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from app.models.base import Base

if TYPE_CHECKING:
    from .image import Image
    from .user import User


class DiaryEntry(Base):
    """다이어리 테이블 모델"""

    __tablename__ = "diaries"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str | None] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column()
    user_emotion: Mapped[str | None] = mapped_column(String(20), index=True)
    ai_emotion: Mapped[str | None] = mapped_column(String(20))
    ai_emotion_confidence: Mapped[float | None] = mapped_column(Float)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    ai_generated_text: Mapped[str | None] = mapped_column()
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    keywords: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True
    )  # JSONB 타입으로 변경

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 관계 설정
    user: Mapped[User] = relationship("User", back_populates="diaries")
    images: Mapped[list[Image]] = relationship(
        "Image", back_populates="diary", cascade="all, delete-orphan"
    )

    # 감정 값 제약 조건 추가
    __table_args__ = (
        CheckConstraint(
            "user_emotion IN ('happy', 'sad', 'angry', 'peaceful', 'unrest')",
            name="diaries_user_emotion_check",
        ),
        CheckConstraint(
            "ai_emotion IN ('happy', 'sad', 'angry', 'peaceful', 'unrest')",
            name="diaries_ai_emotion_check",
        ),
    )
