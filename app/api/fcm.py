"""
FCM (Firebase Cloud Messaging) API 라우터
푸시 알림 토큰 관리 및 알림 전송
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.core.auth import get_current_user
from app.models.user import User
from app.services.fcm_service import FCMService
from app.schemas.fcm import (
    FCMTokenRegisterRequest,
    FCMTokenResponse,
    NotificationSettingsUpdate,
    NotificationSettingsResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationHistoryResponse,
)
from app.schemas.base import BaseResponse

router = APIRouter(tags=["FCM"])


@router.post(
    "/register-token",
    response_model=BaseResponse[FCMTokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="FCM 토큰 등록",
    description="사용자 디바이스의 FCM 토큰을 등록하거나 업데이트합니다.",
)
async def register_fcm_token(
    token_data: FCMTokenRegisterRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """FCM 토큰 등록"""
    token_response = await FCMService.register_token(
        user_id=current_user.id, token_data=token_data, session=session
    )

    return BaseResponse(
        success=True,
        message="FCM 토큰이 성공적으로 등록되었습니다.",
        data=token_response,
    )


@router.get(
    "/tokens",
    response_model=BaseResponse[List[FCMTokenResponse]],
    summary="FCM 토큰 목록 조회",
    description="현재 사용자의 등록된 FCM 토큰 목록을 조회합니다.",
)
async def get_fcm_tokens(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """사용자 FCM 토큰 목록 조회"""
    tokens = await FCMService.get_user_tokens(user_id=current_user.id, session=session)

    return BaseResponse(
        success=True, message="FCM 토큰 목록을 성공적으로 조회했습니다.", data=tokens
    )


@router.delete(
    "/tokens/{token_id}",
    response_model=BaseResponse[bool],
    summary="FCM 토큰 삭제",
    description="특정 FCM 토큰을 삭제(비활성화)합니다.",
)
async def delete_fcm_token(
    token_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """FCM 토큰 삭제"""
    success = await FCMService.delete_token(
        user_id=current_user.id, token_id=str(token_id), session=session
    )

    return BaseResponse(
        success=True, message="FCM 토큰이 성공적으로 삭제되었습니다.", data=success
    )


@router.get(
    "/settings",
    response_model=BaseResponse[NotificationSettingsResponse],
    summary="알림 설정 조회",
    description="사용자의 알림 설정을 조회합니다.",
)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """알림 설정 조회"""
    settings = await FCMService.get_notification_settings(
        user_id=current_user.id, session=session
    )

    return BaseResponse(
        success=True, message="알림 설정을 성공적으로 조회했습니다.", data=settings
    )


@router.patch(
    "/settings",
    response_model=BaseResponse[NotificationSettingsResponse],
    summary="알림 설정 업데이트",
    description="사용자의 알림 설정을 업데이트합니다.",
)
async def update_notification_settings(
    settings_data: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """알림 설정 업데이트"""
    settings = await FCMService.update_notification_settings(
        user_id=current_user.id, settings_data=settings_data, session=session
    )

    return BaseResponse(
        success=True,
        message="알림 설정이 성공적으로 업데이트되었습니다.",
        data=settings,
    )


@router.post(
    "/send-notification",
    response_model=BaseResponse[NotificationSendResponse],
    summary="알림 전송",
    description="사용자 또는 특정 토큰에 푸시 알림을 전송합니다.",
)
async def send_notification(
    notification_data: NotificationSendRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),  # 관리자 권한 체크 가능
):
    """푸시 알림 전송"""
    result = await FCMService.send_notification(
        notification_data=notification_data, session=session
    )

    return BaseResponse(
        success=True, message="알림이 성공적으로 전송되었습니다.", data=result
    )


@router.post(
    "/test-notification",
    response_model=BaseResponse[NotificationSendResponse],
    summary="테스트 알림 전송",
    description="현재 사용자에게 테스트 알림을 전송합니다.",
)
async def send_test_notification(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """테스트 알림 전송"""
    notification_data = NotificationSendRequest(
        title="🔔 새김 테스트 알림",
        body="테스트 알림이 정상적으로 전송되었습니다!",
        notification_type="test",
        user_ids=[current_user.id],
        data={"test": "true"},
    )

    result = await FCMService.send_notification(
        notification_data=notification_data, session=session
    )

    return BaseResponse(
        success=True, message="테스트 알림이 성공적으로 전송되었습니다.", data=result
    )


@router.post(
    "/diary-notification/{diary_id}",
    response_model=BaseResponse[NotificationSendResponse],
    summary="다이어리 알림 전송",
    description="특정 다이어리에 대한 AI 콘텐츠 준비 알림을 전송합니다.",
)
async def send_diary_notification(
    diary_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """다이어리 AI 콘텐츠 알림 전송"""
    result = await FCMService.send_diary_notification(
        user_id=current_user.id, diary_id=str(diary_id), session=session
    )

    return BaseResponse(
        success=True, message="다이어리 알림이 성공적으로 전송되었습니다.", data=result
    )


@router.get(
    "/history",
    response_model=BaseResponse[List[NotificationHistoryResponse]],
    summary="알림 기록 조회",
    description="사용자의 알림 전송 기록을 조회합니다.",
)
async def get_notification_history(
    limit: int = Query(default=20, le=100, description="조회할 기록 수"),
    offset: int = Query(default=0, ge=0, description="건너뛸 기록 수"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """알림 기록 조회"""
    history = await FCMService.get_notification_history(
        user_id=current_user.id, limit=limit, offset=offset, session=session
    )

    return BaseResponse(
        success=True, message="알림 기록을 성공적으로 조회했습니다.", data=history
    )
