"""
알림 시스템 API 라우터
FCM 푸시 알림, 인앱 알림 관리 및 읽음 처리 통합 API
"""

from typing import List
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID

from app.db.database import get_session
from app.core.security import get_current_user_id_from_cookie
from app.services.notification_service import NotificationService
from app.schemas.base import BaseResponse
from app.schemas.notification import (
    FCMTokenRegisterRequest,
    FCMTokenResponse,
    NotificationSettingsUpdate,
    NotificationSettingsResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationHistoryResponse,
)
from app.models.notification import Notification
from app.models.fcm import NotificationHistory

router = APIRouter(tags=["Notifications"])


# ==================== FCM 토큰 관리 ====================


@router.get(
    "/health",
    response_model=BaseResponse[str],
    summary="알림 서비스 상태 확인",
    description="알림 서비스가 정상 작동하는지 확인합니다.",
)
async def notification_health_check():
    """알림 서비스 상태 확인"""
    return BaseResponse(
        success=True, message="알림 서비스가 정상 작동 중입니다.", data="healthy"
    )


@router.post(
    "/tokens",
    response_model=BaseResponse[FCMTokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="FCM 토큰 등록",
    description="새로운 FCM 토큰을 등록하거나 기존 토큰을 업데이트합니다.",
)
def register_fcm_token(
    token_data: FCMTokenRegisterRequest,
    current_user_id: UUID = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """FCM 토큰 등록"""
    token = NotificationService.register_token(
        str(current_user_id), token_data, session
    )
    return BaseResponse(
        success=True, message="FCM 토큰이 성공적으로 등록되었습니다.", data=token
    )


@router.get(
    "/tokens",
    response_model=BaseResponse[List[FCMTokenResponse]],
    summary="FCM 토큰 목록 조회",
    description="현재 사용자의 활성 FCM 토큰 목록을 조회합니다.",
)
def get_fcm_tokens(
    current_user_id: UUID = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """FCM 토큰 목록 조회"""
    tokens = NotificationService.get_user_tokens(str(current_user_id), session)
    return BaseResponse(
        success=True, message="FCM 토큰 목록을 성공적으로 조회했습니다.", data=tokens
    )


@router.delete(
    "/tokens/{token_id}",
    response_model=BaseResponse[str],
    summary="FCM 토큰 삭제",
    description="지정된 FCM 토큰을 삭제(비활성화)합니다.",
)
def delete_fcm_token(
    token_id: str,
    current_user_id: UUID = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """FCM 토큰 삭제"""
    success = NotificationService.delete_token(str(current_user_id), token_id, session)
    if success:
        return BaseResponse(
            success=True,
            message="FCM 토큰이 성공적으로 삭제되었습니다.",
            data="deleted",
        )


# ==================== 알림 설정 관리 ====================


@router.get(
    "/settings",
    response_model=BaseResponse[NotificationSettingsResponse],
    summary="알림 설정 조회",
    description="현재 사용자의 알림 설정을 조회합니다.",
)
def get_notification_settings(
    current_user_id: UUID = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """알림 설정 조회"""
    settings = NotificationService.get_notification_settings(
        str(current_user_id), session
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
def update_notification_settings(
    settings_data: NotificationSettingsUpdate,
    current_user_id: UUID = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """알림 설정 업데이트"""
    updated_settings = NotificationService.update_notification_settings(
        str(current_user_id), settings_data, session
    )
    return BaseResponse(
        success=True,
        message="알림 설정이 성공적으로 업데이트되었습니다.",
        data=updated_settings,
    )


# ==================== 알림 전송 ====================


@router.post(
    "/send",
    response_model=BaseResponse[NotificationSendResponse],
    summary="알림 전송",
    description="지정된 사용자들에게 푸시 알림을 전송합니다.",
)
async def send_notification(
    notification_data: NotificationSendRequest,
    session: Session = Depends(get_session),
):
    """알림 전송"""
    result = await NotificationService.send_notification(notification_data, session)
    return BaseResponse(
        success=True,
        message=f"알림 전송 완료 (성공: {result.success_count}, 실패: {result.failure_count})",
        data=result,
    )


@router.post(
    "/diary-reminder/{user_id}",
    response_model=BaseResponse[NotificationSendResponse],
    summary="다이어리 작성 알림 전송",
    description="특정 사용자에게 다이어리 작성 알림을 전송합니다.",
)
async def send_diary_reminder(
    user_id: str,
    session: Session = Depends(get_session),
):
    """다이어리 작성 알림 전송"""
    result = await NotificationService.send_diary_reminder(user_id, session)
    return BaseResponse(
        success=True, message="다이어리 작성 알림이 전송되었습니다.", data=result
    )


@router.post(
    "/ai-content-ready/{user_id}/{diary_id}",
    response_model=BaseResponse[NotificationSendResponse],
    summary="AI 콘텐츠 준비 완료 알림",
    description="AI 콘텐츠 생성 완료 알림을 전송합니다.",
)
async def send_ai_content_ready(
    user_id: str,
    diary_id: str,
    session: Session = Depends(get_session),
):
    """AI 콘텐츠 준비 완료 알림"""
    result = await NotificationService.send_ai_content_ready(user_id, diary_id, session)
    return BaseResponse(
        success=True, message="AI 콘텐츠 준비 완료 알림이 전송되었습니다.", data=result
    )


# ==================== 알림 이력 조회 ====================


@router.get(
    "/history",
    response_model=BaseResponse[List[NotificationHistoryResponse]],
    summary="알림 이력 조회",
    description="현재 사용자의 알림 전송 이력을 조회합니다.",
)
def get_notification_history(
    limit: int = Query(20, le=100, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    current_user_id: UUID = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """알림 이력 조회"""
    history = NotificationService.get_notification_history(
        str(current_user_id), limit, offset, session
    )
    return BaseResponse(
        success=True, message="알림 이력을 성공적으로 조회했습니다.", data=history
    )


# ==================== 알림 읽음 처리 ====================


@router.patch(
    "/{notification_id}/read",
    response_model=BaseResponse[dict],
    summary="알림 읽음 처리",
    description="알림을 읽음으로 표시하고 관련 히스토리도 동시에 업데이트합니다.",
)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """알림 읽음 처리 - 양쪽 테이블 동기화"""
    try:
        # 1. notification 테이블 업데이트
        notification_stmt = select(Notification).where(
            Notification.id == notification_id, Notification.user_id == current_user_id
        )
        notification = session.execute(notification_stmt).scalar_one_or_none()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다."
            )

        # notification 읽음 처리
        from datetime import datetime

        notification.is_read = True
        notification.read_at = datetime.utcnow()

        # 2. notification_history 테이블 업데이트
        history_stmt = select(NotificationHistory).where(
            NotificationHistory.notification_id == notification_id
        )
        histories = session.execute(history_stmt).scalars().all()

        # history 레코드들의 opened_at 업데이트
        for history in histories:
            if not history.opened_at:
                history.opened_at = datetime.utcnow()

        session.commit()

        return BaseResponse(
            success=True,
            message="알림이 읽음으로 처리되었습니다.",
            data={
                "notification_id": str(notification_id),
                "updated_histories": len(histories),
                "read_at": notification.read_at.isoformat(),
            },
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"알림 읽음 처리 중 오류가 발생했습니다: {str(e)}",
        )


@router.patch(
    "/read-all",
    response_model=BaseResponse[dict],
    summary="모든 알림 읽음 처리",
    description="사용자의 모든 읽지 않은 알림을 읽음으로 표시합니다.",
)
async def mark_all_notifications_as_read(
    current_user_id: UUID = Depends(get_current_user_id_from_cookie),
    session: Session = Depends(get_session),
):
    """모든 알림 읽음 처리"""
    try:
        from datetime import datetime

        now = datetime.utcnow()

        # 1. 모든 읽지 않은 notification 조회
        unread_notifications_stmt = select(Notification).where(
            Notification.user_id == current_user_id, not Notification.is_read
        )
        unread_notifications = (
            session.execute(unread_notifications_stmt).scalars().all()
        )

        if not unread_notifications:
            return BaseResponse(
                success=True,
                message="읽지 않은 알림이 없습니다.",
                data={"updated_count": 0},
            )

        # 2. notification 테이블 일괄 업데이트
        notification_ids = [notif.id for notif in unread_notifications]
        for notification in unread_notifications:
            notification.is_read = True
            notification.read_at = now

        # 3. 관련 notification_history 업데이트
        history_stmt = select(NotificationHistory).where(
            NotificationHistory.notification_id.in_(notification_ids)
        )
        histories = session.execute(history_stmt).scalars().all()

        for history in histories:
            if not history.opened_at:
                history.opened_at = now

        session.commit()

        return BaseResponse(
            success=True,
            message="모든 알림이 읽음으로 처리되었습니다.",
            data={
                "updated_notifications": len(unread_notifications),
                "updated_histories": len(histories),
                "read_at": now.isoformat(),
            },
        )

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"전체 알림 읽음 처리 중 오류가 발생했습니다: {str(e)}",
        )
