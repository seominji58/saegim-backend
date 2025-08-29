"""
알림 시스템 관련 스키마
FCM (Firebase Cloud Messaging) 및 인앱 알림 통합 스키마
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.validators import convert_uuid_to_string


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
class FCMTokenRegisterRequest(BaseModel):
    """FCM 토큰 등록 요청"""

    model_config = ConfigDict(from_attributes=True)

    token: str = Field(..., description="FCM 토큰", max_length=255)
    device_type: DeviceType = Field(..., description="디바이스 타입")
    device_info: dict[str, Any] | None = Field(None, description="디바이스 정보")
    app_version: str | None = Field(None, description="앱 버전", max_length=50)


class FCMTokenCreate(BaseModel):
    """FCM 토큰 등록 요청"""

    model_config = ConfigDict(from_attributes=True)

    token: str = Field(..., description="FCM 토큰", max_length=255)
    device_type: DeviceType = Field(..., description="디바이스 타입")
    device_info: dict[str, Any] | None = Field(None, description="디바이스 정보")


class NotificationSendRequest(BaseModel):
    """알림 전송 요청"""

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., description="알림 제목", max_length=255)
    body: str = Field(..., description="알림 내용", max_length=1000)
    notification_type: str = Field(..., description="알림 타입")
    user_ids: list[str] = Field(..., description="대상 사용자 ID 목록")
    data: dict[str, Any] | None = Field(None, description="추가 데이터")


class NotificationSettingsUpdate(BaseModel):
    """알림 설정 업데이트 요청"""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool | None = Field(None, description="알림 활성화")
    diary_reminder: bool | None = Field(None, description="다이어리 리마인더")
    ai_content_ready: bool | None = Field(None, description="AI 콘텐츠 준비 완료")
    emotion_trend: bool | None = Field(None, description="감정 트렌드")
    anniversary: bool | None = Field(None, description="기념일")
    friend_share: bool | None = Field(None, description="친구 공유")
    quiet_hours_enabled: bool | None = Field(None, description="조용 시간 활성화")
    quiet_start_time: str | None = Field(
        None, description="조용 시간 시작", max_length=5
    )
    quiet_end_time: str | None = Field(None, description="조용 시간 종료", max_length=5)
    frequency: NotificationFrequency | None = Field(None, description="알림 주기")


class TestNotificationCreate(BaseModel):
    """테스트 알림 전송 요청"""

    model_config = ConfigDict(from_attributes=True)

    type: str = Field(default="test", description="알림 타입")
    title: str = Field(..., description="알림 제목", max_length=255)
    message: str = Field(..., description="알림 메시지", max_length=1000)
    data: dict[str, Any] | None = Field(None, description="추가 데이터")


class DiaryNotificationCreate(BaseModel):
    """다이어리 알림 전송 요청"""

    model_config = ConfigDict(from_attributes=True)

    type: NotificationType = Field(..., description="알림 타입")
    diary_id: UUID | None = Field(None, description="다이어리 ID")
    title: str = Field(..., description="알림 제목", max_length=255)
    message: str = Field(..., description="알림 메시지", max_length=1000)
    data: dict[str, Any] | None = Field(None, description="추가 데이터")


# Response Schemas
class FCMTokenResponse(BaseModel):
    """FCM 토큰 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    token: str
    device_type: DeviceType
    device_info: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None


class NotificationSettingsResponse(BaseModel):
    """알림 설정 응답"""

    model_config = ConfigDict(from_attributes=True)

    diary_reminder: bool
    ai_content_ready: bool
    weekly_report: bool
    marketing: bool

    # 다이어리 리마인더 상세 설정
    diary_reminder_time: str | None = Field(
        None, description="다이어리 리마인더 시간 (HH:MM)"
    )
    diary_reminder_days: list[str] | None = Field(
        None, description="다이어리 리마인더 요일 ['mon','tue',...]"
    )

    # 기존 필드 (하위 호환성)
    quiet_hours_start: str | None = Field(
        None, description="조용 시간 시작 (deprecated)"
    )
    quiet_hours_end: str | None = Field(None, description="조용 시간 종료 (deprecated)")


class NotificationSendResponse(BaseModel):
    """알림 전송 응답"""

    model_config = ConfigDict(from_attributes=True)

    success_count: int
    failure_count: int
    successful_tokens: list[str]
    failed_tokens: list[str]
    message: str


class NotificationHistoryResponse(BaseModel):
    """알림 기록 응답 - notification과 FK 관계를 통한 데이터 조회"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    notification_id: str | None = Field(None, description="연결된 알림 ID")
    notification_type: str
    status: str
    sent_at: datetime | None = Field(None, description="전송 시간")
    delivered_at: datetime | None = Field(None, description="전달 시간")
    opened_at: datetime | None = Field(None, description="열람 시간")
    created_at: datetime
    error_message: str | None = Field(None, description="에러 메시지")

    # notification 테이블에서 가져올 데이터
    title: str | None = Field(None, description="알림 제목 (from notification)")
    message: str | None = Field(None, description="알림 내용 (from notification)")
    is_read: bool | None = Field(None, description="읽음 상태 (from notification)")

    @field_validator("id", "notification_id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        """UUID를 문자열로 변환"""
        return convert_uuid_to_string(v)


class FCMTokenListResponse(BaseModel):
    """FCM 토큰 목록 응답"""

    model_config = ConfigDict(from_attributes=True)

    tokens: list[FCMTokenResponse]
    total: int
