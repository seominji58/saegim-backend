"""
다이어리 API 스키마 (캘린더용)
"""

from typing import Optional, Union, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid
import json


class ImageResponse(BaseModel):
    """이미지 응답 스키마"""
    id: str
    file_path: str
    thumbnail_path: Optional[str] = None
    mime_type: Optional[str] = None

    @field_validator('id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        """UUID를 문자열로 변환"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


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
    keywords: Optional[List[str]] = None  # keywords를 리스트 타입으로 수정
    created_at: datetime
    updated_at: Optional[datetime] = None
    images: Optional[List[ImageResponse]] = None  # 이미지 정보 추가

    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        """UUID를 문자열로 변환"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    @field_validator('keywords', mode='before')
    @classmethod
    def parse_keywords(cls, v):
        """keywords를 JSON 문자열에서 리스트로 변환"""
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        return []

    class Config:
        from_attributes = True


class DiaryListResponse(BaseModel):
    """다이어리 목록 응답 스키마 (캘린더용)"""
    id: str
    title: str
    content: str  # 수정된 본문 내용을 표시하기 위해 content 필드 추가
    ai_generated_text: Optional[str] = None  # ai_generated_text 필드 추가
    user_emotion: Optional[str] = None
    ai_emotion: Optional[str] = None
    keywords: Optional[List[str]] = None  # keywords를 리스트 타입으로 수정
    created_at: datetime
    is_public: bool
    images: Optional[List[ImageResponse]] = None  # 이미지 정보 추가

    @field_validator('id', mode='before')
    @classmethod
    def validate_uuid(cls, v):
        """UUID를 문자열로 변환"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    @field_validator('keywords', mode='before')
    @classmethod
    def parse_keywords(cls, v):
        """keywords를 JSON 문자열에서 리스트로 변환"""
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        return []

    class Config:
        from_attributes = True


class DiaryCreateRequest(BaseModel):
    """다이어리 생성 요청 스키마"""
    title: str = Field(..., min_length=1, max_length=255, description="다이어리 제목")
    content: str = Field(..., min_length=1, description="다이어리 내용")
    user_emotion: Optional[str] = Field(None, description="사용자 감정")
    is_public: bool = Field(False, description="공개 여부")
    keywords: Optional[List[str]] = Field(None, description="키워드 목록")

    @field_validator('user_emotion')
    @classmethod
    def validate_emotion(cls, v):
        """감정 값 검증"""
        if v is not None:
            allowed_emotions = ['happy', 'sad', 'angry', 'peaceful', 'unrest']
            if v not in allowed_emotions:
                raise ValueError(f'감정은 {allowed_emotions} 중 하나여야 합니다')
        return v

    @field_validator('keywords', mode='before')
    @classmethod
    def parse_keywords(cls, v):
        """keywords를 JSON 문자열에서 리스트로 변환"""
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        return []

    class Config:
        from_attributes = True


class DiaryUpdateRequest(BaseModel):
    """다이어리 수정 요청 스키마"""
    title: Optional[str] = None
    content: Optional[str] = None
    user_emotion: Optional[str] = None
    is_public: Optional[bool] = None
    keywords: Optional[List[str]] = None

    @field_validator('keywords', mode='before')
    @classmethod
    def parse_keywords(cls, v):
        """keywords를 JSON 문자열에서 리스트로 변환"""
        if isinstance(v, str):
            try:
                return json.loads(v) if v else []
            except json.JSONDecodeError:
                return []
        elif isinstance(v, list):
            return v
        return []

    class Config:
        from_attributes = True
