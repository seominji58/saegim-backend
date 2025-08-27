"""
AI 사용 로그 모델
"""

from typing import TYPE_CHECKING, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
    desc,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from app.models.user import User

from app.models.base import Base


class AIUsageLog(Base):
    """AI 사용 로그 테이블 모델"""

    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index("idx_ai_usage_user_created", "user_id", desc("created_at")),
        Index("idx_ai_usage_session_regen", "session_id", "regeneration_count"),
        Index(
            "idx_ai_usage_user_sessions", "user_id", "session_id", desc("created_at")
        ),
        Index("idx_ai_usage_api_type", "api_type"),
        CheckConstraint(
            "api_type IN ('generate', 'keywords', 'emotion_analysis', 'integrated_analysis')",
            name="ck_ai_usage_api_type",
        ),
        CheckConstraint(
            "regeneration_count >= 1 AND regeneration_count <= 5",
            name="ck_ai_usage_regeneration_count",
        ),
        CheckConstraint("tokens_used >= 0", name="ck_ai_usage_tokens_positive"),
    )

    # 기본 필드
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    api_type: Mapped[str] = mapped_column(String(50), nullable=False)
    session_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    regeneration_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    response_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # 타임스탬프 필드
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 관계 설정
    user: Mapped["User"] = relationship("User", back_populates="ai_usage_logs")

    def __repr__(self) -> str:
        return f"<AIUsageLog(user_id={self.user_id}, api_type={self.api_type}, session_id={self.session_id}, regen={self.regeneration_count})>"
