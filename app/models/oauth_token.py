from __future__ import annotations
from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Index, UniqueConstraint, CheckConstraint, text,
    Column, String, DateTime, Text, ForeignKey
)
from sqlalchemy.sql import func


class OAuthToken(SQLModel, table=True):
    __tablename__ = "oauth_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
        CheckConstraint("provider IN ('google','kakao','naver')", name="ck_oauth_provider"),
        Index("idx_oauth_expires", "expires_at", postgresql_where=text("expires_at IS NOT NULL")),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )

    provider: str = Field(nullable=False, index=True, max_length=20)

    # 토큰은 애플리케이션 레벨 암호화/보관 전제 (원문 저장 지양)
    access_token: str = Field(nullable=False)
    refresh_token: Optional[str] = Field(default=None, nullable=True)

    expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    user: "User" = Relationship(back_populates="oauth_tokens")
