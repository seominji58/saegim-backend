"""
사용자 알림 모델
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
    CheckConstraint,
    JSON,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey

if TYPE_CHECKING:
    from app.models.user import User

from app.models.base import Base


class Notification(Base):
    """사용자 알림 모델 - 인앱 알림 관리"""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_user_notifications", "user_id", "created_at"),
        Index("idx_notification_type", "type", "scheduled_at"),
        Index("idx_unread_notifications", "user_id", "is_read", "created_at",
              postgresql_where="is_read = false"),
        CheckConstraint(
            "type IN ('diary_reminder','report_ready','ai_complete')",
            name="ck_notification_type",
        ),
    )

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Key to User
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Notification Content
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Additional Data
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # 알림 관련 세부 데이터 (JSON)

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # 예약 전송 시간
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # 읽음 시간

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
    user: Mapped["User"] = relationship("User", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, is_read={self.is_read})>"