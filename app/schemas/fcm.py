"""
FCM (Firebase Cloud Messaging) 관련 스키마
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class DeviceType(str, Enum):
    """디바이스 타입"""

    WEB = "web"
    ANDROID = "android"
    IOS = "ios"


class NotificationStatus(str, Enum):
    """알림 상태"""

    SENT = "sent"
    FAILED = "failed"
    PENDING = "pending"
    DELIVERED = "delivered"
    OPENED = "opened"


class NotificationType(str, Enum):
    """알림 타입"""

    DIARY_REMINDER = "diary_reminder"
    AI_CONTENT_READY = "ai_content_ready"
    EMOTION_TREND = "emotion_trend"
    ANNIVERSARY = "anniversary"
    FRIEND_SHARE = "friend_share"
    GENERAL = "general"


class NotificationFrequency(str, Enum):
    """알림 주기"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    NEVER = "never"


# Request Schemas
class FCMTokenCreate(BaseModel):
    """FCM 토큰 등록 요청"""

    model_config = ConfigDict(from_attributes=True)

    token: str = Field(..., description="FCM 토큰", max_length=255)
    device_type: DeviceType = Field(..., description="디바이스 타입")
    device_info: Optional[Dict[str, Any]] = Field(None, description="디바이스 정보")


class NotificationSettingsUpdate(BaseModel):
    """알림 설정 업데이트 요청"""

    model_config = ConfigDict(from_attributes=True)

    enabled: Optional[bool] = Field(None, description="알림 활성화")
    diary_reminder: Optional[bool] = Field(None, description="다이어리 리마인더")
    ai_content_ready: Optional[bool] = Field(None, description="AI 콘텐츠 준비 완료")
    emotion_trend: Optional[bool] = Field(None, description="감정 트렌드")
    anniversary: Optional[bool] = Field(None, description="기념일")
    friend_share: Optional[bool] = Field(None, description="친구 공유")
    quiet_hours_enabled: Optional[bool] = Field(None, description="조용 시간 활성화")
    quiet_start_time: Optional[str] = Field(
        None, description="조용 시간 시작", max_length=5
    )
    quiet_end_time: Optional[str] = Field(
        None, description="조용 시간 종료", max_length=5
    )
    frequency: Optional[NotificationFrequency] = Field(None, description="알림 주기")


class TestNotificationCreate(BaseModel):
    """테스트 알림 전송 요청"""

    model_config = ConfigDict(from_attributes=True)

    type: str = Field(default="test", description="알림 타입")
    title: str = Field(..., description="알림 제목", max_length=255)
    message: str = Field(..., description="알림 메시지", max_length=1000)
    data: Optional[Dict[str, Any]] = Field(None, description="추가 데이터")


class DiaryNotificationCreate(BaseModel):
    """다이어리 알림 전송 요청"""

    model_config = ConfigDict(from_attributes=True)

    type: NotificationType = Field(..., description="알림 타입")
    diary_id: Optional[UUID] = Field(None, description="다이어리 ID")
    title: str = Field(..., description="알림 제목", max_length=255)
    message: str = Field(..., description="알림 메시지", max_length=1000)
    data: Optional[Dict[str, Any]] = Field(None, description="추가 데이터")


# Response Schemas
class FCMTokenResponse(BaseModel):
    """FCM 토큰 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    token: str
    device_type: DeviceType
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime


class FCMTokenListResponse(BaseModel):
    """FCM 토큰 목록 응답"""

    model_config = ConfigDict(from_attributes=True)

    tokens: List[FCMTokenResponse]
    total: int


class NotificationSettingsResponse(BaseModel):
    """알림 설정 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    enabled: bool
    diary_reminder: bool
    ai_content_ready: bool
    emotion_trend: bool
    anniversary: bool
    friend_share: bool
    quiet_hours_enabled: bool
    quiet_start_time: Optional[str]
    quiet_end_time: Optional[str]
    frequency: NotificationFrequency
    created_at: datetime
    updated_at: datetime


class NotificationHistoryResponse(BaseModel):
    """알림 히스토리 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    notification_type: NotificationType
    title: str
    body: str
    status: NotificationStatus
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    created_at: datetime


class NotificationHistoryListResponse(BaseModel):
    """알림 히스토리 목록 응답"""

    model_config = ConfigDict(from_attributes=True)

    notifications: List[NotificationHistoryResponse]
    pagination: Dict[str, Any]


class NotificationSendResponse(BaseModel):
    """알림 전송 응답"""

    model_config = ConfigDict(from_attributes=True)

    notification_id: Optional[UUID] = None
    sent_count: int
    failed_count: int
    sent_tokens: Optional[List[str]] = None
