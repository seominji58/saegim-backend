"""
FCM 서비스
사용자 디바이스 토큰 관리 및 푸시 알림 전송
"""

from typing import List, Dict
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlmodel import Session, select, and_, desc
from app.utils.fcm_push import get_fcm_service
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
    def register_token(
        user_id: str, token_data: FCMTokenRegisterRequest, session: Session
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
            existing_token = session.exec(stmt).first()

            if existing_token:
                # 기존 토큰 업데이트
                existing_token.token = token_data.token
                existing_token.device_type = token_data.device_type
                existing_token.app_version = token_data.app_version
                existing_token.is_active = True
                existing_token.updated_at = datetime.now(timezone.utc)
                
                session.add(existing_token)
                session.commit()
                session.refresh(existing_token)
                
                return FCMTokenResponse(
                    id=existing_token.id,
                    device_id=existing_token.device_id,
                    device_type=existing_token.device_type,
                    app_version=existing_token.app_version,
                    is_active=existing_token.is_active,
                    created_at=existing_token.created_at,
                    updated_at=existing_token.updated_at,
                )
            else:
                # 새 토큰 생성
                new_token = FCMToken(
                    user_id=user_id,
                    token=token_data.token,
                    device_id=token_data.device_id,
                    device_type=token_data.device_type,
                    app_version=token_data.app_version,
                    is_active=True,
                )
                
                session.add(new_token)
                session.commit()
                session.refresh(new_token)
                
                return FCMTokenResponse(
                    id=new_token.id,
                    device_id=new_token.device_id,
                    device_type=new_token.device_type,
                    app_version=new_token.app_version,
                    is_active=new_token.is_active,
                    created_at=new_token.created_at,
                    updated_at=new_token.updated_at,
                )

        except Exception as e:
            session.rollback()
            logger.error(f"Error registering FCM token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FCM 토큰 등록에 실패했습니다.",
            )

    @staticmethod
    def get_user_tokens(user_id: str, session: Session) -> List[FCMTokenResponse]:
        """사용자의 활성 FCM 토큰 목록 조회"""
        try:
            stmt = select(FCMToken).where(
                and_(FCMToken.user_id == user_id, FCMToken.is_active == True)
            )
            tokens = session.exec(stmt).all()

            return [
                FCMTokenResponse(
                    id=token.id,
                    device_id=token.device_id,
                    device_type=token.device_type,
                    app_version=token.app_version,
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
                detail="FCM 토큰 목록 조회에 실패했습니다.",
            )

    @staticmethod
    def delete_token(user_id: str, token_id: str, session: Session) -> bool:
        """FCM 토큰 삭제 (비활성화)"""
        try:
            stmt = select(FCMToken).where(
                and_(FCMToken.id == token_id, FCMToken.user_id == user_id)
            )
            token = session.exec(stmt).first()

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="FCM 토큰을 찾을 수 없습니다.",
                )

            token.is_active = False
            token.updated_at = datetime.now(timezone.utc)
            
            session.add(token)
            session.commit()

            return True

        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting FCM token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FCM 토큰 삭제에 실패했습니다.",
            )

    @staticmethod
    def get_notification_settings(
        user_id: str, session: Session
    ) -> NotificationSettingsResponse:
        """사용자 알림 설정 조회"""
        try:
            stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            settings = session.exec(stmt).first()

            if not settings:
                # 기본 설정 생성
                settings = NotificationSettings(
                    user_id=user_id,
                    diary_reminder=True,
                    ai_content_ready=True,
                    weekly_report=True,
                    marketing=False,
                )
                session.add(settings)
                session.commit()
                session.refresh(settings)

            return NotificationSettingsResponse(
                diary_reminder=settings.diary_reminder,
                ai_content_ready=settings.ai_content_ready,
                weekly_report=settings.weekly_report,
                marketing=settings.marketing,
                quiet_hours_start=settings.quiet_hours_start,
                quiet_hours_end=settings.quiet_hours_end,
            )

        except Exception as e:
            logger.error(f"Error getting notification settings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 설정 조회에 실패했습니다.",
            )

    @staticmethod
    def update_notification_settings(
        user_id: str, settings_data: NotificationSettingsUpdate, session: Session
    ) -> NotificationSettingsResponse:
        """사용자 알림 설정 업데이트"""
        try:
            stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            settings = session.exec(stmt).first()

            if not settings:
                # 새 설정 생성
                settings = NotificationSettings(user_id=user_id)
                session.add(settings)

            # 설정 업데이트
            update_data = settings_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(settings, key, value)

            settings.updated_at = datetime.now(timezone.utc)
            session.add(settings)
            session.commit()
            session.refresh(settings)

            return NotificationSettingsResponse(
                diary_reminder=settings.diary_reminder,
                ai_content_ready=settings.ai_content_ready,
                weekly_report=settings.weekly_report,
                marketing=settings.marketing,
                quiet_hours_start=settings.quiet_hours_start,
                quiet_hours_end=settings.quiet_hours_end,
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating notification settings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 설정 업데이트에 실패했습니다.",
            )

    @staticmethod
    async def send_notification(
        notification_data: NotificationSendRequest, session: Session
    ) -> NotificationSendResponse:
        """푸시 알림 전송"""
        try:
            fcm_service = get_fcm_service()
            successful_tokens = []
            failed_tokens = []

            # 대상 사용자들의 활성 토큰 조회
            all_tokens = []
            for user_id in notification_data.user_ids:
                stmt = select(FCMToken).where(
                    and_(FCMToken.user_id == user_id, FCMToken.is_active == True)
                )
                user_tokens = session.exec(stmt).all()
                all_tokens.extend(user_tokens)

            if not all_tokens:
                return NotificationSendResponse(
                    success_count=0,
                    failure_count=0,
                    successful_tokens=[],
                    failed_tokens=[],
                    message="전송할 활성 토큰이 없습니다.",
                )

            # 각 토큰에 대해 알림 전송
            for token_model in all_tokens:
                try:
                    # 알림 전송
                    success = await fcm_service.send_notification(
                        token=token_model.token,
                        title=notification_data.title,
                        body=notification_data.body,
                        data=notification_data.data,
                    )

                    if success:
                        successful_tokens.append(token_model.token)
                        status_value = "sent"
                    else:
                        failed_tokens.append(token_model.token)
                        status_value = "failed"

                    # 알림 기록 저장
                    history = NotificationHistory(
                        user_id=token_model.user_id,
                        title=notification_data.title,
                        body=notification_data.body,
                        notification_type=notification_data.notification_type,
                        status=status_value,
                        fcm_response={
                            "token": token_model.token[:10] + "...",  # 보안을 위해 일부만 저장
                            "success": success,
                        },
                    )
                    session.add(history)

                except Exception as e:
                    logger.error(f"Error sending to token {token_model.token[:10]}...: {str(e)}")
                    failed_tokens.append(token_model.token)
                    
                    # 실패 기록 저장
                    history = NotificationHistory(
                        user_id=token_model.user_id,
                        title=notification_data.title,
                        body=notification_data.body,
                        notification_type=notification_data.notification_type,
                        status="failed",
                        fcm_response={"error": str(e)},
                    )
                    session.add(history)

            session.commit()

            return NotificationSendResponse(
                success_count=len(successful_tokens),
                failure_count=len(failed_tokens),
                successful_tokens=successful_tokens,
                failed_tokens=failed_tokens,
                message=f"알림 전송 완료: 성공 {len(successful_tokens)}개, 실패 {len(failed_tokens)}개",
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Error sending notification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 전송에 실패했습니다.",
            )

    @staticmethod
    async def send_diary_reminder(user_id: str, session: Session) -> NotificationSendResponse:
        """다이어리 작성 알림 전송"""
        try:
            # 알림 설정 확인
            settings_stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            settings = session.exec(settings_stmt).first()

            if settings and not settings.diary_reminder:
                return NotificationSendResponse(
                    success_count=0,
                    failure_count=0,
                    successful_tokens=[],
                    failed_tokens=[],
                    message="사용자가 다이어리 알림을 비활성화했습니다.",
                )

            # 알림 전송
            notification_request = NotificationSendRequest(
                title="📝 오늘의 감정을 기록해보세요",
                body="새김에서 오늘 하루를 돌아보며 마음을 정리해보세요.",
                notification_type="diary_reminder",
                user_ids=[user_id],
                data={"action": "write_diary"},
            )

            return await FCMService.send_notification(notification_request, session)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending diary reminder: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="다이어리 알림 전송에 실패했습니다.",
            )

    @staticmethod
    async def send_ai_content_ready(
        user_id: str, diary_id: str, session: Session
    ) -> NotificationSendResponse:
        """AI 콘텐츠 준비 완료 알림 전송"""
        try:
            # 다이어리 존재 확인
            diary_stmt = select(DiaryEntry).where(DiaryEntry.id == diary_id)
            diary = session.exec(diary_stmt).first()

            if not diary:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="다이어리를 찾을 수 없습니다.",
                )

            # 알림 설정 확인
            settings_stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            settings = session.exec(settings_stmt).first()

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
            logger.error(f"Error sending AI content notification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI 콘텐츠 알림 전송에 실패했습니다.",
            )

    @staticmethod
    def get_notification_history(
        user_id: str, limit: int, offset: int, session: Session
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

            histories = session.exec(stmt).all()

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
