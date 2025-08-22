"""
감정 통계 모델
"""

from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

if TYPE_CHECKING:
    from app.models.user import User

from app.models.base import Base


class EmotionStats(Base):
    """감정 통계 테이블 모델"""

    __tablename__ = "emotion_stats"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "year", "month", "emotion", name="unique_user_period_emotion"
        ),
        Index("idx_emotion_stats_user_period", "user_id", "year", "month"),
        Index("idx_emotion_stats_emotion", "emotion"),
        CheckConstraint(
            "emotion IN ('happy', 'sad', 'angry', 'peaceful', 'unrest')",
            name="ck_emotion_stats_emotion",
        ),
        CheckConstraint("year >= 2020 AND year <= 2100", name="ck_emotion_stats_year"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_emotion_stats_month"),
        CheckConstraint("count >= 0", name="ck_emotion_stats_count"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    emotion: Mapped[str] = mapped_column(String(20), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 관계 설정
    user: Mapped["User"] = relationship("User", back_populates="emotion_stats")

    def __repr__(self) -> str:
        return f"<EmotionStats(user_id={self.user_id}, {self.year}-{self.month:02d}, {self.emotion}={self.count})>"
