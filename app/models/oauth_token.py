from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from uuid import uuid4, UUID
from datetime import datetime

from sqlalchemy import Index, UniqueConstraint, CheckConstraint, text, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401

from app.models.base import Base


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
        CheckConstraint("provider IN ('google','kakao','naver')", name="ck_oauth_provider"),
        Index("idx_oauth_expires", "expires_at", postgresql_where=text("expires_at IS NOT NULL")),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # 토큰은 애플리케이션 레벨 암호화/보관 전제 (원문 저장 지양)
    access_token: Mapped[str] = mapped_column(nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(nullable=True)

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 관계 정의 - SQLAlchemy 2.0 방식
    user: Mapped["User"] = relationship(back_populates="oauth_tokens")
