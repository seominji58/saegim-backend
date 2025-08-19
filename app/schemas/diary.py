"""
다이어리 API 스키마 (캘린더용)
"""

from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid


class DiaryResponse(BaseModel):
    """다이어리 응답 스키마"""
    id: str
    title: str
    content: str
    user_emotion: Optional[str] = None
    ai_emotion: Optional[str] = None
    ai_emotion_confidence: Optional[float] = None
    user_id: str
    ai_generated_text: Optional[str] = None
    is_public: bool
    keywords: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        """UUID를 문자열로 변환"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class DiaryListResponse(BaseModel):
    """다이어리 목록 응답 스키마 (캘린더용)"""
    id: str
    title: str
    user_emotion: Optional[str] = None
    ai_emotion: Optional[str] = None
    created_at: datetime
    is_public: bool

    @field_validator('id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        """UUID를 문자열로 변환"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
