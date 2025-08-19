from __future__ import annotations
from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Index, Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        UniqueConstraint("token", name="uq_password_reset_token"),
        Index("idx_user_reset", "user_id", "is_used", "expires_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True
    )

    token: str = Field(nullable=False, index=True, max_length=255)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    is_used: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    user: "User" = Relationship(back_populates="reset_tokens")
