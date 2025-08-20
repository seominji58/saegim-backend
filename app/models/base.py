"""
기본 데이터베이스 모델
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class BaseModel(SQLModel):
    """기본 모델 클래스"""

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})
