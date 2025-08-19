from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from app.models.oauth_token import OAuthToken
    from app.models.password_reset_token import PasswordResetToken
from uuid import uuid4, UUID
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Index, UniqueConstraint, CheckConstraint, text, Column, String, DateTime
)
from sqlalchemy.sql import func


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("provider", "provider_id", name="uq_users_provider_pid"),
        CheckConstraint("account_type IN ('social','email')", name="ck_users_account_type"),
        CheckConstraint("(provider IS NULL OR provider IN ('google','kakao','naver'))", name="ck_users_provider"),
        Index("idx_users_provider", "provider", "provider_id"),
        Index("idx_account_type", "account_type"),
        # partial index: WHERE deleted_at IS NULL
        Index("idx_users_active", "is_active", "deleted_at",
              postgresql_where=text("deleted_at IS NULL")),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(nullable=False, index=True, max_length=255)
    password_hash: Optional[str] = Field(default=None, nullable=True, max_length=255)
    account_type: str = Field(default="social", nullable=False, max_length=6)
    nickname: str = Field(nullable=False, max_length=50)
    provider: Optional[str] = Field(default=None, nullable=True, max_length=20)
    provider_id: Optional[str] = Field(default=None, nullable=True, max_length=255)
    profile_image_url: Optional[str] = Field(default=None, nullable=True, max_length=500)
    is_active: bool = Field(default=True, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )
    deleted_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # 관계 정의 - 일시적으로 제거 (문제 해결 후 복원 예정)
    # oauth_tokens: List["OAuthToken"] = Relationship(back_populates="user")
    # reset_tokens: List["PasswordResetToken"] = Relationship(back_populates="user")
