"""
이미지 모델
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from app.models.base import Base


class Image(Base):
    """이미지 테이블 모델"""

    __tablename__ = "images"
    __table_args__ = (Index("idx_diary_images", "diary_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    diary_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("diaries.id"), nullable=True, index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exif_removed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 관계 설정
    diary: Mapped[Optional["DiaryEntry"]] = relationship(
        "DiaryEntry", back_populates="images"
    )

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, diary_id={self.diary_id}, file_path={self.file_path})>"
