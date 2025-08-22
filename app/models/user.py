from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List
from uuid import uuid4, UUID
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Index,
    UniqueConstraint,
    CheckConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

if TYPE_CHECKING:
    from app.models.oauth_token import OAuthToken
    from app.models.password_reset_token import PasswordResetToken
    from app.models.diary import DiaryEntry
    from app.models.fcm import FCMToken, NotificationSettings, NotificationHistory
    from app.models.emotion_stats import EmotionStats
    from app.models.ai_usage_log import AIUsageLog
    from app.models.notification import Notification

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("nickname", name="uq_users_nickname"),
        UniqueConstraint("provider", "provider_id", name="uq_users_provider_pid"),
        CheckConstraint(
            "account_type IN ('social','email')", name="ck_users_account_type"
        ),
        CheckConstraint(
            "(provider IS NULL OR provider IN ('google','kakao','naver'))",
            name="ck_users_provider",
        ),
        Index("idx_users_provider", "provider", "provider_id"),
        Index("idx_account_type", "account_type"),
        # partial index: WHERE deleted_at IS NULL
        Index(
            "idx_users_active",
            "is_active",
            "deleted_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    account_type: Mapped[str] = mapped_column(
        String(6), nullable=False, default="social"
    )
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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

    # 관계 정의 - SQLAlchemy 2.0 방식
    oauth_tokens: Mapped[List["OAuthToken"]] = relationship(
        back_populates="user", lazy="selectin"
    )
    reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        back_populates="user", lazy="selectin"
    )
    diaries: Mapped[List["DiaryEntry"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    # FCM 관련 관계
    fcm_tokens: Mapped[List["FCMToken"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    notification_settings: Mapped[Optional["NotificationSettings"]] = relationship(
        back_populates="user",
        lazy="selectin",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notification_history: Mapped[List["NotificationHistory"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    # 새로 추가된 관계들
    emotion_stats: Mapped[List["EmotionStats"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    ai_usage_logs: Mapped[List["AIUsageLog"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )
