"""
사용자 모델
"""

from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship
from .base import BaseModel


class User(BaseModel, table=True):
    """사용자 테이블 모델"""
    
    __tablename__ = "users"
    
    email: str = Field(unique=True, index=True, max_length=255)
    name: str = Field(max_length=100)
    provider: str = Field(max_length=20, default="local")  # local, google, kakao, naver
    profile_image_url: Optional[str] = Field(max_length=500)
    
    # 관계 설정
    diaries: List["DiaryEntry"] = Relationship(back_populates="user")
