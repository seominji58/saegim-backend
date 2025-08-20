"""
다이어리 모델
"""

from typing import Optional, List
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship
from .base import BaseModel


class DiaryEntry(BaseModel, table=True):
    """다이어리 테이블 모델"""

    __tablename__ = "diaries"

    title: str = Field(max_length=255, index=True)
    content: str = Field()
    user_emotion: Optional[str] = Field(max_length=20, index=True)
    ai_emotion: Optional[str] = Field(max_length=20)
    ai_emotion_confidence: Optional[float] = Field(ge=0.0, le=1.0)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    ai_generated_text: Optional[str] = Field()
    is_public: bool = Field(default=False)
    keywords: Optional[str] = Field()  # JSON 저장

    # 관계 설정 - 일시적으로 제거 (OAuth 인증 문제 해결 후 복원 예정)
    # user: "User" = Relationship(back_populates="diaries")
