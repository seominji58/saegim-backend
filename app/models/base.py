"""
기본 데이터베이스 모델
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 기본 모델 클래스"""
    pass


class BaseModel(Base):
    """기본 모델 클래스 (abstract)"""
    __abstract__ = True  # 실제 테이블로 생성되지 않음

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.now(), onupdate=func.now(), nullable=True
    )
