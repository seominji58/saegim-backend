from __future__ import annotations
from uuid import uuid4, UUID
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import Index, CheckConstraint, text, Column, String, DateTime
from sqlalchemy.sql import func


class EmailVerification(SQLModel, table=True):
    __tablename__ = "email_verifications"
    __table_args__ = (
        Index("idx_email_code", "email", "verification_code"),
        Index("idx_expires", "expires_at", postgresql_where=text("expires_at IS NOT NULL")),
        CheckConstraint("char_length(verification_code) = 6", name="ck_verif_code_len"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(nullable=False, index=True, max_length=255)
    verification_code: str = Field(nullable=False, max_length=6)

    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    is_used: bool = Field(default=False, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
