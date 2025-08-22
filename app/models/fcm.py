"""
FCM (Firebase Cloud Messaging) 관련 모델
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any
from uuid import uuid4, UUID
from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Boolean,
    Index,
    UniqueConstraint,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey

if TYPE_CHECKING:
    from app.models.user import User

from app.models.base import Base


class FCMToken(Base):
    """FCM 토큰 모델 - 사용자별 FCM 디바이스 토큰 관리"""

    __tablename__ = "fcm_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "token", name="uq_fcm_tokens_user_token"),
        Index("idx_fcm_tokens_user_id", "user_id"),
        Index("idx_fcm_tokens_active", "is_active", "created_at"),
        Index("idx_fcm_tokens_device_type", "device_type"),
        CheckConstraint(
            "device_type IN ('web','android','ios')", name="ck_fcm_device_type"
        ),
    )

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Key to User
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # FCM Token
    token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Device Information
    device_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="web"
    )  # web, android, ios
    device_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # user_agent, platform 등

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="fcm_tokens")
    notification_history: Mapped[list["NotificationHistory"]] = relationship(
        "NotificationHistory", back_populates="fcm_token", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FCMToken(id={self.id}, user_id={self.user_id}, device_type={self.device_type})>"


class NotificationSettings(Base):
    """사용자별 알림 설정 모델"""

    __tablename__ = "notification_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_settings_user_id"),
        Index("idx_notification_settings_user_id", "user_id"),
    )

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Key to User
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # ERD 기준 알림 설정 필드
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    diary_reminder_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    diary_reminder_time: Mapped[Optional[str]] = mapped_column(
        String(5), nullable=True, default="21:00"
    )  # HH:MM 형식
    diary_reminder_days: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True, default=lambda: []
    )  # 리마인드 요일 배열 ['mon','tue',...]
    report_notification_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_processing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    browser_push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notification_settings")

    def __repr__(self) -> str:
        return f"<NotificationSettings(id={self.id}, user_id={self.user_id}, push_enabled={self.push_enabled})>"


class NotificationHistory(Base):
    """알림 전송 이력 모델"""

    __tablename__ = "notification_history"
    __table_args__ = (
        Index("idx_notification_history_user_id", "user_id"),
        Index("idx_notification_history_type", "notification_type"),
        Index("idx_notification_history_sent_at", "sent_at"),
        Index("idx_notification_history_status", "status"),
        CheckConstraint(
            "notification_type IN ('diary_reminder','ai_content_ready','emotion_trend','anniversary','friend_share','general')",
            name="ck_notification_type",
        ),
        CheckConstraint(
            "status IN ('sent','failed','pending','delivered','opened')",
            name="ck_notification_status",
        ),
    )

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Key to User
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # FCM Token used for sending (optional, token might be deleted)
    fcm_token_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("fcm_tokens.id", ondelete="SET NULL"), nullable=True
    )

    # Notification Content
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Additional Data
    data_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # FCM data payload

    # Status and Tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Timestamps
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notification_history")
    fcm_token: Mapped[Optional["FCMToken"]] = relationship(
        "FCMToken", back_populates="notification_history"
    )

    def __repr__(self) -> str:
        return f"<NotificationHistory(id={self.id}, user_id={self.user_id}, type={self.notification_type}, status={self.status})>"
