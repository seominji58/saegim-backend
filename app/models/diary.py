"""
다이어리 모델
"""

from typing import Optional, List, Dict, Any
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy import (
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class DiaryEntry(Base):
    """다이어리 테이블 모델"""

    __tablename__ = "diaries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column()
    user_emotion: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    ai_emotion: Mapped[Optional[str]] = mapped_column(String(20))
    ai_emotion_confidence: Mapped[Optional[float]] = mapped_column(Float)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    ai_generated_text: Mapped[Optional[str]] = mapped_column()
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True
    )  # JSON 타입으로 변경

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 관계 설정
    user: Mapped["User"] = relationship("User", back_populates="diaries")
    images: Mapped[List["Image"]] = relationship(
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
