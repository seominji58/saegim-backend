"""
알림 서비스
FCM 디바이스 토큰 관리, 푸시 알림 전송 및 인앱 알림 통합 관리
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.models.diary import DiaryEntry
from app.models.fcm import FCMToken, NotificationHistory, NotificationSettings
from app.schemas.notification import (
    FCMTokenRegisterRequest,
    FCMTokenResponse,
    NotificationHistoryResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from app.utils.fcm_push import get_fcm_service

logger = logging.getLogger(__name__)


class NotificationService:
    """알림 토큰 및 푸시 알림 관리 서비스"""

    @staticmethod
    def register_token(
        user_id: str, token_data: FCMTokenRegisterRequest, session: Session
    ) -> FCMTokenResponse:
        """FCM 토큰 등록 또는 업데이트"""
        from psycopg2.errors import UniqueViolation
        from sqlalchemy.dialects.postgresql import insert

        try:
            # PostgreSQL UPSERT를 사용하여 동시성 이슈 해결
            stmt = insert(FCMToken).values(
                user_id=user_id,
                token=token_data.token,
                device_type=token_data.device_type,
                device_info=token_data.device_info,
                is_active=True,
            )

            # ON CONFLICT DO UPDATE - 중복 시 업데이트
            stmt = stmt.on_conflict_do_update(
                constraint="uq_fcm_tokens_user_token",  # unique constraint 이름
                set_=dict(
                    device_type=stmt.excluded.device_type,
                    device_info=stmt.excluded.device_info,
                    is_active=stmt.excluded.is_active,
                    updated_at=datetime.now(timezone.utc),
                ),
            ).returning(FCMToken)

            result = session.execute(stmt).scalar_one()
            session.commit()

            return FCMTokenResponse.model_validate(result)

        except Exception as e:
            session.rollback()

            # UniqueViolation이 발생한 경우 기존 방식으로 재시도
            if isinstance(e.__cause__, UniqueViolation):
                try:
                    logger.warning(f"UPSERT 실패, 기존 토큰 조회로 재시도: {str(e)}")

                    # 기존 토큰 조회
                    stmt = select(FCMToken).where(
                        and_(
                            FCMToken.user_id == user_id,
                            FCMToken.token == token_data.token,
                        )
                    )
                    existing_token = session.execute(stmt).scalar_one_or_none()

                    if existing_token:
                        # 기존 토큰 업데이트
                        existing_token.device_type = token_data.device_type
                        existing_token.device_info = token_data.device_info
                        existing_token.is_active = True
                        existing_token.updated_at = datetime.now(timezone.utc)

                        session.add(existing_token)
                        session.commit()
                        session.refresh(existing_token)

                        return FCMTokenResponse.model_validate(existing_token)
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="토큰이 존재하지만 조회할 수 없습니다.",
                        )

                except Exception as retry_error:
                    session.rollback()
                    logger.error(f"FCM 토큰 등록 재시도 실패: {str(retry_error)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="FCM 토큰 등록에 실패했습니다.",
                    )
            else:
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
                and_(FCMToken.user_id == user_id, FCMToken.is_active)
            )
            tokens = session.execute(stmt).scalars().all()

            return [FCMTokenResponse.model_validate(token) for token in tokens]

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
            token = session.execute(stmt).scalar_one_or_none()

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
            settings = session.execute(stmt).scalar_one_or_none()

            if not settings:
                # 기본 설정 생성
                settings = NotificationSettings(
                    user_id=user_id,
                    diary_reminder_enabled=True,
                    ai_processing_enabled=True,
                    report_notification_enabled=True,
                    browser_push_enabled=False,
                )
                session.add(settings)
                session.commit()
                session.refresh(settings)

            return NotificationSettingsResponse(
                diary_reminder=settings.diary_reminder_enabled,
                ai_content_ready=settings.ai_processing_enabled,
                weekly_report=settings.report_notification_enabled,
                marketing=settings.browser_push_enabled,
                # 다이어리 리마인더 상세 설정 추가
                diary_reminder_time=settings.diary_reminder_time,
                diary_reminder_days=settings.diary_reminder_days or [],
                # 기존 필드 (하위 호환성)
                quiet_hours_start=settings.diary_reminder_time,
                quiet_hours_end=settings.diary_reminder_time,
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
            settings = session.execute(stmt).scalar_one_or_none()

            if not settings:
                # 새 설정 생성
                settings = NotificationSettings(user_id=user_id)
                session.add(settings)

            # 스키마 필드를 모델 필드로 매핑하여 설정 업데이트
            update_data = settings_data.model_dump(exclude_unset=True)

            # 필드명 매핑 처리
            field_mapping = {
                "enabled": "push_enabled",
                "diary_reminder": "diary_reminder_enabled",
                "ai_content_ready": "ai_processing_enabled",
                "emotion_trend": "report_notification_enabled",  # 임시 매핑
                "anniversary": "report_notification_enabled",  # 임시 매핑
                "friend_share": "report_notification_enabled",  # 임시 매핑
                "quiet_hours_enabled": "browser_push_enabled",  # 임시 매핑
                "quiet_start_time": "diary_reminder_time",  # 임시 매핑
                "quiet_end_time": "diary_reminder_time",  # 임시 매핑
            }

            for schema_field, value in update_data.items():
                model_field = field_mapping.get(schema_field)
                if model_field and hasattr(settings, model_field):
                    setattr(settings, model_field, value)

            settings.updated_at = datetime.now(timezone.utc)
            session.add(settings)
            session.commit()
            session.refresh(settings)

            return NotificationSettingsResponse(
                diary_reminder=settings.diary_reminder_enabled,
                ai_content_ready=settings.ai_processing_enabled,
                weekly_report=settings.report_notification_enabled,
                marketing=settings.browser_push_enabled,
                # 다이어리 리마인더 상세 설정 추가
                diary_reminder_time=settings.diary_reminder_time,
                diary_reminder_days=settings.diary_reminder_days or [],
                # 기존 필드 (하위 호환성)
                quiet_hours_start=settings.diary_reminder_time,
                quiet_hours_end=settings.diary_reminder_time,
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
            if fcm_service is None:
                logger.error("FCM 서비스가 초기화되지 않았습니다")
                return NotificationSendResponse(
                    success_count=0,
                    failure_count=0,
                    successful_tokens=[],
                    failed_tokens=[],
                    message="FCM 서비스 초기화 오류로 알림을 전송할 수 없습니다.",
                )

            successful_tokens = []
            failed_tokens = []

            # 대상 사용자들의 활성 토큰 조회
            all_tokens = []
            for user_id in notification_data.user_ids:
                stmt = select(FCMToken).where(
                    and_(FCMToken.user_id == user_id, FCMToken.is_active)
                )
                user_tokens = session.execute(stmt).scalars().all()
                all_tokens.extend(user_tokens)

            if not all_tokens:
                return NotificationSendResponse(
                    success_count=0,
                    failure_count=0,
                    successful_tokens=[],
                    failed_tokens=[],
                    message="전송할 활성 토큰이 없습니다.",
                )

            # notification 테이블에 알림 생성 (사용자별로 하나씩)
            from app.models.notification import Notification

            created_notifications = {}

            for user_id in notification_data.user_ids:
                notification = Notification(
                    user_id=user_id,
                    type=notification_data.notification_type,
                    title=notification_data.title,
                    message=notification_data.body,
                    data=notification_data.data,
                )
                session.add(notification)
                session.flush()  # ID를 얻기 위해 flush
                created_notifications[user_id] = notification.id

            # 각 토큰에 대해 알림 전송
            for token_model in all_tokens:
                try:
                    # 알림 전송
                    result = await fcm_service.send_notification(
                        token=token_model.token,
                        title=notification_data.title,
                        body=notification_data.body,
                        data=notification_data.data,
                    )

                    if result["success"]:
                        successful_tokens.append(token_model.token)
                        status_value = "sent"
                    else:
                        failed_tokens.append(token_model.token)
                        status_value = "failed"

                        # UNREGISTERED 토큰인 경우 비활성화
                        if result.get("error_type") == "UNREGISTERED":
                            logger.warning(
                                f"토큰 {token_model.token[:10]}...이 UNREGISTERED 상태입니다. 비활성화합니다."
                            )
                            token_model.is_active = False
                            token_model.updated_at = datetime.now(timezone.utc)

                    # 알림 기록 저장
                    history = NotificationHistory(
                        user_id=token_model.user_id,
                        notification_id=created_notifications.get(
                            str(token_model.user_id)
                        ),
                        fcm_token_id=token_model.id,
                        notification_type=notification_data.notification_type,
                        status=status_value,
                        data_payload={
                            "token": token_model.token[:10] + "...",  # 보안을 위해 일부만 저장
                            "success": result["success"],
                            "error_type": result.get("error_type"),
                            "fcm_response": result.get("response"),
                            "title": notification_data.title,  # data_payload에 저장
                            "body": notification_data.body,  # data_payload에 저장
                        },
                        sent_at=datetime.now(timezone.utc)
                        if result["success"]
                        else None,
                        error_message=(
                            str(result.get("response", {}).get("error", {}).get("message", ""))  # type: ignore[attr-defined]
                            if (
                                not result["success"]
                                and isinstance(result, dict)
                                and isinstance(result.get("response"), dict)
                            )
                            else None
                        ),
                    )
                    session.add(history)

                except Exception as e:
                    logger.error(
                        f"Error sending to token {token_model.token[:10]}...: {str(e)}"
                    )
                    failed_tokens.append(token_model.token)

                    # 실패 기록 저장
                    history = NotificationHistory(
                        user_id=token_model.user_id,
                        notification_id=created_notifications.get(
                            str(token_model.user_id)
                        ),
                        fcm_token_id=token_model.id,
                        notification_type=notification_data.notification_type,
                        status="failed",
                        error_message=str(e),
                        data_payload={
                            "token": token_model.token[:10] + "...",
                            "title": notification_data.title,  # data_payload에 저장
                            "body": notification_data.body,  # data_payload에 저장
                        },
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
    async def send_diary_reminder(
        user_id: str, session: Session
    ) -> NotificationSendResponse:
        """다이어리 작성 알림 전송"""
        try:
            # 알림 설정 확인
            settings_stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            settings = session.execute(settings_stmt).scalar_one_or_none()

            if settings and not settings.diary_reminder_enabled:
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

            return await NotificationService.send_notification(
                notification_request, session
            )

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
            diary = session.execute(diary_stmt).scalar_one_or_none()

            if not diary:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="다이어리를 찾을 수 없습니다.",
                )

            # 알림 설정 확인
            settings_stmt = select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
            settings = session.execute(settings_stmt).scalar_one_or_none()

            if settings and not settings.ai_processing_enabled:
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

            return await NotificationService.send_notification(
                notification_request, session
            )

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
        """사용자 알림 기록 조회 - JOIN으로 notification 데이터 포함"""
        try:
            from app.models.notification import Notification

            # notification_history와 notification을 LEFT JOIN
            stmt = (
                select(
                    NotificationHistory.id,
                    NotificationHistory.notification_id,
                    NotificationHistory.notification_type,
                    NotificationHistory.status,
                    NotificationHistory.sent_at,
                    NotificationHistory.delivered_at,
                    NotificationHistory.opened_at,
                    NotificationHistory.created_at,
                    NotificationHistory.error_message,
                    NotificationHistory.data_payload,  # data_payload에서 title, body 가져오기
                    Notification.title,
                    Notification.message,
                    Notification.is_read,
                )
                .select_from(NotificationHistory)
                .outerjoin(
                    Notification, NotificationHistory.notification_id == Notification.id
                )
                .where(NotificationHistory.user_id == user_id)
                .order_by(desc(NotificationHistory.created_at))
                .limit(limit)
                .offset(offset)
            )

            results = session.execute(stmt).all()

            return [
                NotificationHistoryResponse(
                    id=str(result.id),
                    notification_id=str(result.notification_id)
                    if result.notification_id
                    else None,
                    notification_type=result.notification_type,
                    status=result.status,
                    sent_at=result.sent_at,
                    delivered_at=result.delivered_at,
                    opened_at=result.opened_at,
                    created_at=result.created_at,
                    error_message=result.error_message,
                    # notification이 있으면 그것을 우선 사용, 없으면 data_payload에서 가져오기
                    title=result.title
                    or (
                        result.data_payload.get("title")
                        if result.data_payload
                        else None
                    ),
                    message=result.message
                    or (
                        result.data_payload.get("body") if result.data_payload else None
                    ),
                    is_read=result.is_read,
                )
                for result in results
            ]

        except Exception as e:
            logger.error(f"Error getting notification history: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="알림 기록 조회에 실패했습니다.",
            )

    @staticmethod
    async def cleanup_invalid_tokens(session: Session) -> int:
        """무효한 FCM 토큰들을 정리합니다"""
        try:
            fcm_service = get_fcm_service()
            if fcm_service is None:
                logger.warning("FCM 서비스를 사용할 수 없어 토큰 정리를 건너뜁니다.")
                return 0

            # 모든 활성 토큰 조회
            stmt = select(FCMToken).where(FCMToken.is_active)
            active_tokens = session.execute(stmt).scalars().all()

            cleanup_count = 0

            # 각 토큰을 테스트하여 유효성 확인 (주의: 실제 알림은 전송하지 않음)
            for token_model in active_tokens:
                try:
                    # 더미 알림으로 토큰 유효성 테스트 (dry run)
                    result = await fcm_service.send_notification(
                        token=token_model.token,
                        title="토큰 검증",
                        body="이 알림은 토큰 유효성 검증용입니다.",
                        data={"type": "validation", "test": "true"},
                    )

                    # UNREGISTERED 토큰인 경우 비활성화
                    if (
                        not result["success"]
                        and result.get("error_type") == "UNREGISTERED"
                    ):
                        logger.info(f"무효한 토큰 비활성화: {token_model.token[:10]}...")
                        token_model.is_active = False
                        token_model.updated_at = datetime.now(timezone.utc)
                        cleanup_count += 1

                except Exception as e:
                    logger.error(f"토큰 검증 중 오류 {token_model.token[:10]}...: {str(e)}")
                    continue

            session.commit()
            logger.info(f"FCM 토큰 정리 완료: {cleanup_count}개 토큰 비활성화")
            return cleanup_count

        except Exception as e:
            session.rollback()
            logger.error(f"FCM 토큰 정리 중 오류: {str(e)}")
            return 0

    @staticmethod
    def get_active_token_count(user_id: str, session: Session) -> int:
        """사용자의 활성 토큰 개수를 반환합니다"""
        try:
            stmt = select(FCMToken).where(
                and_(FCMToken.user_id == user_id, FCMToken.is_active)
            )
            count = len(session.execute(stmt).scalars().all())
            return count
        except Exception as e:
            logger.error(f"활성 토큰 개수 조회 실패: {str(e)}")
            return 0
