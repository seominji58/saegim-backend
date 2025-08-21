"""
FCM 서비스
사용자 디바이스 토큰 관리 및 푸시 알림 전송
"""

from typing import List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from firebase_admin import messaging
import logging

from app.models.fcm import FCMToken, NotificationSettings, NotificationHistory
from app.models.diary import DiaryEntry
from app.schemas.fcm import (
    FCMTokenRegisterRequest,
    FCMTokenResponse,
    NotificationSettingsUpdate,
    NotificationSettingsResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationHistoryResponse,
)

logger = logging.getLogger(__name__)


class FCMService:
    """FCM 토큰 및 알림 관리 서비스"""

    @staticmethod
    async def register_token(
        user_id: str, token_data: FCMTokenRegisterRequest, session: AsyncSession
    ) -> FCMTokenResponse:
        """FCM 토큰 등록 또는 업데이트"""
        try:
            # 기존 토큰이 있는지 확인
            stmt = select(FCMToken).where(
                and_(
                    FCMToken.user_id == user_id,
                    FCMToken.device_id == token_data.device_id,
                )
            )
            result = await session.execute(stmt)
            existing_token = result.scalar_one_or_none()

            if existing_token:
                # 기존 토큰 업데이트
                existing_token.token = token_data.token
                existing_token.device_type = token_data.device_type
                existing_token.device_name = token_data.device_name
                existing_token.app_version = token_data.app_version
                existing_token.os_version = token_data.os_version
                existing_token.is_active = True
                existing_token.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(existing_token)
                fcm_token = existing_token
            else:
                # 새 토큰 생성
                fcm_token = FCMToken(
                    user_id=user_id,
                    token=token_data.token,
                    device_id=token_data.device_id,
                    device_type=token_data.device_type,
                    device_name=token_data.device_name,
                    app_version=token_data.app_version,
                    os_version=token_data.os_version,
                    is_active=True,
                )
                session.add(fcm_token)
                await session.commit()
                await session.refresh(fcm_token)

            logger.info(
                f"FCM token registered for user {user_id}, device {token_data.device_id}"
            )

            return FCMTokenResponse(
                id=fcm_token.id,
                device_id=fcm_token.device_id,
                device_type=fcm_token.device_type,
                device_name=fcm_token.device_name,
                is_active=fcm_token.is_active,
                created_at=fcm_token.created_at,
                updated_at=fcm_token.updated_at,
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Error registering FCM token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FCM 토큰 등록에 실패했습니다.",
            )

    @staticmethod
    async def get_user_tokens(
        user_id: str, session: AsyncSession
    ) -> List[FCMTokenResponse]:
        """사용자의 모든 FCM 토큰 조회"""
        try:
            stmt = (
                select(FCMToken)
                .where(and_(FCMToken.user_id == user_id, FCMToken.is_active))
                .order_by(desc(FCMToken.updated_at))
            )

            result = await session.execute(stmt)
            tokens = result.scalars().all()

            return [
                FCMTokenResponse(
                    id=token.id,
                    device_id=token.device_id,
                    device_type=token.device_type,
                    device_name=token.device_name,
                    is_active=token.is_active,
                    created_at=token.created_at,
                    updated_at=token.updated_at,
                )
                for token in tokens
            ]

        except Exception as e:
            logger.error(f"Error getting user tokens: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="토큰 조회에 실패했습니다.",
            )

    @staticmethod
    async def delete_token(user_id: str, token_id: str, session: AsyncSession) -> bool:
        """FCM 토큰 삭제 (비활성화)"""
        try:
            stmt = select(FCMToken).where(
                and_(FCMToken.id == token_id, FCMToken.user_id == user_id)
            )
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="토큰을 찾을 수 없습니다.",
                )

            token.is_active = False
            token.updated_at = datetime.now(timezone.utc)

            await session.commit()
            logger.info(f"FCM token {token_id} deactivated for user {user_id}")

            return True

        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting FCM token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="토큰 삭제에 실패했습니다.",
            )

    @staticmethod
    async def get_notification_settings(
        user_id: str, session: AsyncSession
    ) -> NotificationSettingsResponse:
        """사용자 알림 설정 조회"""
        try:
            stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            result = await session.execute(stmt)
            settings = result.scalar_one_or_none()

            if not settings:
                # 기본 설정 생성
                settings = NotificationSettings(
                    user_id=user_id,
                    diary_reminder=True,
                    ai_content_ready=True,
                    weekly_summary=True,
                    system_notifications=True,
                    quiet_hours_start="22:00",
                    quiet_hours_end="08:00",
                )
                session.add(settings)
                await session.commit()
                await session.refresh(settings)

            return NotificationSettingsResponse(
                diary_reminder=settings.diary_reminder,
                ai_content_ready=settings.ai_content_ready,
                weekly_summary=settings.weekly_summary,
                system_notifications=settings.system_notifications,
                quiet_hours_start=settings.quiet_hours_start,
                quiet_hours_end=settings.quiet_hours_end,
                updated_at=settings.updated_at,
            )

        except Exception as e:
            logger.error(f"Error getting notification settings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 설정 조회에 실패했습니다.",
            )

    @staticmethod
    async def update_notification_settings(
        user_id: str, settings_data: NotificationSettingsUpdate, session: AsyncSession
    ) -> NotificationSettingsResponse:
        """사용자 알림 설정 업데이트"""
        try:
            stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            result = await session.execute(stmt)
            settings = result.scalar_one_or_none()

            if not settings:
                settings = NotificationSettings(user_id=user_id)
                session.add(settings)

            # 업데이트할 필드만 설정
            update_data = settings_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(settings, field, value)

            settings.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(settings)

            logger.info(f"Notification settings updated for user {user_id}")

            return NotificationSettingsResponse(
                diary_reminder=settings.diary_reminder,
                ai_content_ready=settings.ai_content_ready,
                weekly_summary=settings.weekly_summary,
                system_notifications=settings.system_notifications,
                quiet_hours_start=settings.quiet_hours_start,
                quiet_hours_end=settings.quiet_hours_end,
                updated_at=settings.updated_at,
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating notification settings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 설정 업데이트에 실패했습니다.",
            )

    @staticmethod
    async def send_notification(
        notification_data: NotificationSendRequest, session: AsyncSession
    ) -> NotificationSendResponse:
        """푸시 알림 전송"""
        try:
            # 대상 토큰 조회
            if notification_data.user_ids:
                # 특정 사용자들에게 전송
                stmt = select(FCMToken).where(
                    and_(
                        FCMToken.user_id.in_(notification_data.user_ids),
                        FCMToken.is_active,
                    )
                )
            elif notification_data.tokens:
                # 특정 토큰들에게 전송
                stmt = select(FCMToken).where(
                    and_(
                        FCMToken.token.in_(notification_data.tokens), FCMToken.is_active
                    )
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user_ids 또는 tokens 중 하나는 필수입니다.",
                )

            result = await session.execute(stmt)
            tokens = result.scalars().all()

            if not tokens:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="전송할 토큰을 찾을 수 없습니다.",
                )

            # FCM 메시지 생성
            messages = []
            for token in tokens:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=notification_data.title,
                        body=notification_data.body,
                        image=notification_data.image_url,
                    ),
                    data=notification_data.data or {},
                    token=token.token,
                    android=messaging.AndroidConfig(
                        notification=messaging.AndroidNotification(
                            icon="ic_notification",
                            color="#7C9885",  # 새김 브랜드 컬러
                        )
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(badge=1, sound="default")
                        )
                    ),
                )
                messages.append(message)

            # FCM 전송
            response = messaging.send_all(messages)

            # 전송 결과 기록
            successful_tokens = []
            failed_tokens = []

            for i, result in enumerate(response.responses):
                token = tokens[i]

                if result.success:
                    successful_tokens.append(token.token)

                    # 성공 기록 저장
                    history = NotificationHistory(
                        user_id=token.user_id,
                        title=notification_data.title,
                        body=notification_data.body,
                        notification_type=notification_data.notification_type,
                        status="sent",
                        fcm_response={"message_id": result.message_id},
                    )
                    session.add(history)
                else:
                    failed_tokens.append(
                        {"token": token.token, "error": str(result.exception)}
                    )

                    # 실패 기록 저장
                    history = NotificationHistory(
                        user_id=token.user_id,
                        title=notification_data.title,
                        body=notification_data.body,
                        notification_type=notification_data.notification_type,
                        status="failed",
                        fcm_response={"error": str(result.exception)},
                    )
                    session.add(history)

                    # 토큰이 유효하지 않은 경우 비활성화
                    if "not-registered" in str(result.exception).lower():
                        token.is_active = False
                        token.updated_at = datetime.now(timezone.utc)

            await session.commit()

            logger.info(
                f"Notification sent: {len(successful_tokens)} success, {len(failed_tokens)} failed"
            )

            return NotificationSendResponse(
                success_count=len(successful_tokens),
                failure_count=len(failed_tokens),
                successful_tokens=successful_tokens,
                failed_tokens=failed_tokens,
            )

        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Error sending notification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 전송에 실패했습니다.",
            )

    @staticmethod
    async def send_diary_notification(
        user_id: str, diary_id: str, session: AsyncSession
    ) -> NotificationSendResponse:
        """다이어리 관련 알림 전송"""
        try:
            # 다이어리 정보 조회
            stmt = select(DiaryEntry).where(DiaryEntry.id == diary_id)
            result = await session.execute(stmt)
            diary = result.scalar_one_or_none()

            if not diary:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="다이어리를 찾을 수 없습니다.",
                )

            # 알림 설정 확인
            settings_stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            settings_result = await session.execute(settings_stmt)
            settings = settings_result.scalar_one_or_none()

            if settings and not settings.ai_content_ready:
                return NotificationSendResponse(
                    success_count=0,
                    failure_count=0,
                    successful_tokens=[],
                    failed_tokens=[],
                    message="사용자가 AI 콘텐츠 알림을 비활성화했습니다.",
                )

            # 알림 전송
            notification_request = NotificationSendRequest(
                title="✨ AI가 당신의 마음을 읽었어요",
                body=f"'{diary.title}' 일기에 특별한 글귀가 준비되었습니다.",
                notification_type="ai_content_ready",
                user_ids=[user_id],
                data={"diary_id": diary_id, "action": "view_ai_content"},
            )

            return await FCMService.send_notification(notification_request, session)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending diary notification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="다이어리 알림 전송에 실패했습니다.",
            )

    @staticmethod
    async def get_notification_history(
        user_id: str, limit: int, offset: int, session: AsyncSession
    ) -> List[NotificationHistoryResponse]:
        """사용자 알림 기록 조회"""
        try:
            stmt = (
                select(NotificationHistory)
                .where(NotificationHistory.user_id == user_id)
                .order_by(desc(NotificationHistory.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(stmt)
            histories = result.scalars().all()

            return [
                NotificationHistoryResponse(
                    id=history.id,
                    title=history.title,
                    body=history.body,
                    notification_type=history.notification_type,
                    status=history.status,
                    created_at=history.created_at,
                    fcm_response=history.fcm_response,
                )
                for history in histories
            ]

        except Exception as e:
            logger.error(f"Error getting notification history: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 기록 조회에 실패했습니다.",
            )
