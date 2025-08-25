"""
FCM (Firebase Cloud Messaging) API 라우터
푸시 알림 토큰 관리 및 알림 전송
"""

from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlmodel import Session

from app.db.database import get_session
from app.core.security import get_current_user_id_from_cookie
from app.services.fcm_service import FCMService
from app.schemas.base import BaseResponse
from app.schemas.fcm import (
    FCMTokenRegisterRequest,
    FCMTokenResponse,
    NotificationSettingsUpdate,
    NotificationSettingsResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationHistoryResponse,
)

router = APIRouter(tags=["FCM"])


@router.get(
    "/health",
    response_model=BaseResponse[str],
    summary="FCM 서비스 상태 확인",
    description="FCM 서비스가 정상 작동하는지 확인합니다.",
)
async def fcm_health_check():
    """FCM 서비스 상태 확인"""
    return BaseResponse(
        success=True, message="FCM 서비스가 정상 작동 중입니다.", data="healthy"
    )


@router.post(
    "/register-token",
    response_model=BaseResponse[FCMTokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="FCM 토큰 등록",
    description="새로운 FCM 토큰을 등록하거나 기존 토큰을 업데이트합니다.",
)
def register_fcm_token(
    token_data: FCMTokenRegisterRequest,
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """FCM 토큰 등록 또는 업데이트"""
    result = FCMService.register_token(current_user_id, token_data, session)
    return BaseResponse(
        success=True, message="FCM 토큰이 성공적으로 등록되었습니다.", data=result
    )


@router.get(
    "/tokens",
    response_model=BaseResponse[List[FCMTokenResponse]],
    summary="FCM 토큰 목록 조회",
    description="현재 사용자의 활성 FCM 토큰 목록을 조회합니다.",
)
def get_fcm_tokens(
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """사용자 FCM 토큰 목록 조회"""
    tokens = FCMService.get_user_tokens(current_user_id, session)
    return BaseResponse(
        success=True, message="FCM 토큰 목록을 성공적으로 조회했습니다.", data=tokens
    )


@router.delete(
    "/tokens/{token_id}",
    response_model=BaseResponse[bool],
    summary="FCM 토큰 삭제",
    description="지정된 FCM 토큰을 삭제(비활성화)합니다.",
)
def delete_fcm_token(
    token_id: str,
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """FCM 토큰 삭제"""
    result = FCMService.delete_token(current_user_id, token_id, session)
    return BaseResponse(
        success=True, message="FCM 토큰이 성공적으로 삭제되었습니다.", data=result
    )


@router.get(
    "/settings",
    response_model=BaseResponse[NotificationSettingsResponse],
    summary="알림 설정 조회",
    description="현재 사용자의 알림 설정을 조회합니다.",
)
def get_notification_settings(
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """알림 설정 조회"""
    settings = FCMService.get_notification_settings(current_user_id, session)
    return BaseResponse(
        success=True, message="알림 설정을 성공적으로 조회했습니다.", data=settings
    )


@router.put(
    "/settings",
    response_model=BaseResponse[NotificationSettingsResponse],
    summary="알림 설정 업데이트",
    description="사용자의 알림 설정을 업데이트합니다.",
)
def update_notification_settings(
    settings_data: NotificationSettingsUpdate,
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """알림 설정 업데이트"""
    result = FCMService.update_notification_settings(
        current_user_id, settings_data, session
    )
    return BaseResponse(
        success=True, message="알림 설정이 성공적으로 업데이트되었습니다.", data=result
    )


@router.post(
    "/send-notification",
    response_model=BaseResponse[NotificationSendResponse],
    summary="푸시 알림 전송",
    description="지정된 사용자들에게 푸시 알림을 전송합니다.",
)
async def send_push_notification(
    notification_data: NotificationSendRequest,
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """푸시 알림 전송"""
    result = await FCMService.send_notification(notification_data, session)
    return BaseResponse(
        success=True, message="알림이 성공적으로 전송되었습니다.", data=result
    )


@router.post(
    "/send-diary-reminder",
    response_model=BaseResponse[NotificationSendResponse],
    summary="다이어리 작성 알림 전송",
    description="현재 인증된 사용자에게 다이어리 작성 알림을 전송합니다.",
)
async def send_diary_reminder_notification(
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """다이어리 작성 알림 전송"""
    result = await FCMService.send_diary_reminder(str(current_user_id), session)
    return BaseResponse(
        success=True, message="다이어리 알림이 성공적으로 전송되었습니다.", data=result
    )


@router.post(
    "/send-ai-content-ready/{diary_id}",
    response_model=BaseResponse[NotificationSendResponse],
    summary="AI 콘텐츠 준비 완료 알림 전송",
    description="AI 콘텐츠가 준비되었을 때 현재 인증된 사용자에게 알림을 전송합니다.",
)
async def send_ai_content_ready_notification(
    diary_id: str,
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """AI 콘텐츠 준비 완료 알림 전송"""
    result = await FCMService.send_ai_content_ready(
        str(current_user_id), diary_id, session
    )
    return BaseResponse(
        success=True, message="AI 콘텐츠 알림이 성공적으로 전송되었습니다.", data=result
    )


@router.get(
    "/history",
    response_model=BaseResponse[List[NotificationHistoryResponse]],
    summary="알림 기록 조회",
    description="현재 사용자의 알림 전송 기록을 조회합니다.",
)
def get_notification_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """알림 기록 조회"""
    history = FCMService.get_notification_history(
        current_user_id, limit, offset, session
    )
    return BaseResponse(
        success=True, message="알림 기록을 성공적으로 조회했습니다.", data=history
    )


@router.post(
    "/cleanup-tokens",
    response_model=BaseResponse[dict],
    summary="무효한 토큰 정리",
    description="무효한 FCM 토큰들을 자동으로 감지하고 비활성화합니다.",
)
async def cleanup_invalid_tokens(
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """무효한 FCM 토큰 정리"""
    cleanup_count = await FCMService.cleanup_invalid_tokens(session)
    active_count = FCMService.get_active_token_count(current_user_id, session)
    
    return BaseResponse(
        success=True,
        message=f"무효한 토큰 정리가 완료되었습니다. {cleanup_count}개 토큰이 비활성화되었습니다.",
        data={
            "cleanup_count": cleanup_count,
            "active_token_count": active_count,
        }
    )


@router.get(
    "/token-status", 
    response_model=BaseResponse[dict],
    summary="토큰 상태 조회",
    description="현재 사용자의 FCM 토큰 상태를 조회합니다.",
)
def get_token_status(
    current_user_id: str = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """FCM 토큰 상태 조회"""
    active_count = FCMService.get_active_token_count(current_user_id, session)
    tokens = FCMService.get_user_tokens(current_user_id, session)
    
    return BaseResponse(
        success=True,
        message="FCM 토큰 상태를 성공적으로 조회했습니다.",
        data={
            "active_token_count": active_count,
            "total_token_count": len(tokens),
            "tokens": [
                {
                    "id": str(token.id),
                    "device_type": token.device_type,
                    "is_active": token.is_active,
                    "created_at": token.created_at.isoformat(),
                    "updated_at": token.updated_at.isoformat(),
                    "token_preview": token.token[:20] + "..." if token.token else None,
                }
                for token in tokens
            ],
        }
    )
