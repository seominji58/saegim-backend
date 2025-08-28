"""
이미지 모델
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from app.models.base import Base

if TYPE_CHECKING:
    from .diary import DiaryEntry


class Image(Base):
    """이미지 테이블 모델"""

    __tablename__ = "images"
    __table_args__ = (Index("idx_diary_images", "diary_id"),)

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    diary_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("diaries.id"), nullable=True, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exif_removed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 관계 설정
    diary: Mapped[DiaryEntry | None] = relationship(
        "DiaryEntry", back_populates="images"
    )

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, diary_id={self.diary_id}, file_path={self.file_path})>"
