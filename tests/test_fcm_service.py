"""
FCM 서비스 레이어 테스트
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.notification_service import NotificationService
from app.models.fcm import FCMToken, NotificationSettings, NotificationHistory
from app.schemas.notification import (
    FCMTokenRegisterRequest,
    NotificationSettingsUpdate,
    NotificationSendRequest,
)


class TestNotificationService:
    """Notification 서비스 테스트 클래스"""

    @pytest.fixture
    def notification_service(self):
        """NotificationService 인스턴스"""
        return NotificationService()

    @pytest.fixture
    def mock_session(self):
        """Mock 데이터베이스 세션"""
        return Mock(spec=Session)

    @pytest.fixture
    def sample_user_id(self):
        """테스트용 사용자 ID"""
        return "test-user-123"

    @pytest.fixture
    def sample_token_request(self):
        """테스트용 토큰 등록 요청"""
        return FCMTokenRegisterRequest(
            token="test-fcm-token-12345",
            device_type="web",
            device_info={"user_agent": "test-browser", "platform": "web"},
        )

    @pytest.fixture
    def sample_fcm_token(self, sample_user_id):
        """테스트용 FCM 토큰 모델"""
        return FCMToken(
            id="token-id-123",
            user_id=sample_user_id,
            token="test-fcm-token-12345",
            device_type="web",
            device_info={"user_agent": "test-browser", "platform": "web"},
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_notification_settings(self, sample_user_id):
        """테스트용 알림 설정"""
        return NotificationSettings(
            id="settings-id-123",
            user_id=sample_user_id,
            push_enabled=True,
            diary_reminder_enabled=True,
            diary_reminder_time="21:00",
            diary_reminder_days=[],
            report_notification_enabled=True,
            ai_processing_enabled=True,
            browser_push_enabled=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_register_token_new_token(
        self, notification_service, mock_session, sample_user_id, sample_token_request
    ):
        """새로운 토큰 등록 테스트"""
        # Mock: PostgreSQL UPSERT 성공 케이스
        mock_result = Mock()
        mock_result.id = "token-id-123"
        mock_result.user_id = sample_user_id
        mock_result.token = sample_token_request.token
        mock_result.device_type = sample_token_request.device_type
        mock_result.device_info = sample_token_request.device_info
        mock_result.is_active = True
        mock_result.created_at = datetime.now(timezone.utc)
        mock_result.updated_at = datetime.now(timezone.utc)

        # Mock session.execute().scalar_one() 체인
        mock_execute_result = Mock()
        mock_execute_result.scalar_one.return_value = mock_result
        mock_session.execute.return_value = mock_execute_result
        mock_session.commit = Mock()

        # Mock FCMTokenResponse.model_validate
        with patch(
            "app.services.notification_service.FCMTokenResponse"
        ) as mock_response_class:
            mock_response = Mock()
            mock_response.token = sample_token_request.token
            mock_response.device_type = sample_token_request.device_type
            mock_response.device_info = sample_token_request.device_info
            mock_response.is_active = True
            mock_response_class.model_validate.return_value = mock_response

            result = notification_service.register_token(
                sample_user_id, sample_token_request, mock_session
            )

            # 검증
            assert result.token == sample_token_request.token
            assert result.device_type == sample_token_request.device_type
            assert result.device_info == sample_token_request.device_info
            assert result.is_active is True

            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_response_class.model_validate.assert_called_once_with(mock_result)

    def test_register_token_update_existing(
        self,
        notification_service,
        mock_session,
        sample_user_id,
        sample_token_request,
        sample_fcm_token,
    ):
        """기존 토큰 업데이트 테스트 - UPSERT 실패 시 fallback 로직"""
        # Mock: UPSERT 실패하여 UniqueViolation 발생

        # UniqueViolation을 상속하는 실제 예외 클래스 생성
        class MockUniqueViolation(Exception):
            pass

        upsert_exception = Exception("UPSERT failed")
        upsert_exception.__cause__ = MockUniqueViolation("duplicate key")

        mock_session.rollback = Mock()

        # Mock: fallback 로직에서 기존 토큰 조회 성공
        mock_execute_result_2 = Mock()
        mock_execute_result_2.scalar_one_or_none.return_value = sample_fcm_token

        # execute가 두 번 호출됨: 첫 번째는 UPSERT(실패), 두 번째는 조회(성공)
        mock_session.execute.side_effect = [
            upsert_exception,  # 첫 번째 UPSERT 실패
            mock_execute_result_2,  # 두 번째 조회 성공
        ]

        # psycopg2.errors.UniqueViolation 패치
        with patch("psycopg2.errors.UniqueViolation", MockUniqueViolation):
            mock_session.add = Mock()
            mock_session.commit = Mock()
            mock_session.refresh = Mock()

            # Mock FCMTokenResponse.model_validate
            with patch(
                "app.services.notification_service.FCMTokenResponse"
            ) as mock_response_class:
                mock_response = Mock()
                mock_response.token = sample_token_request.token
                mock_response.device_type = sample_token_request.device_type
                mock_response.device_info = sample_token_request.device_info
                mock_response.is_active = True
                mock_response_class.model_validate.return_value = mock_response

                result = notification_service.register_token(
                    sample_user_id, sample_token_request, mock_session
                )

                # 검증
                assert result.token == sample_token_request.token
                assert result.device_type == sample_token_request.device_type
                assert result.device_info == sample_token_request.device_info
                assert result.is_active is True

                # UPSERT 실패 후 rollback과 재시도 로직 검증
                mock_session.rollback.assert_called_once()
                mock_session.add.assert_called_once_with(sample_fcm_token)
                mock_session.commit.assert_called_once()
                mock_session.refresh.assert_called_once_with(sample_fcm_token)
                mock_response_class.model_validate.assert_called_once_with(
                    sample_fcm_token
                )

    def test_get_user_tokens(
        self, notification_service, mock_session, sample_user_id, sample_fcm_token
    ):
        """사용자 토큰 목록 조회 테스트"""
        # Mock: session.execute().scalars().all() 체인
        mock_scalars = Mock()
        mock_scalars.all.return_value = [sample_fcm_token]
        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_execute_result

        # Mock FCMTokenResponse.model_validate - 리스트 컴프리헨션을 위해 개별적으로 모킹
        with patch(
            "app.services.notification_service.FCMTokenResponse"
        ) as mock_response_class:
            mock_response = Mock()
            mock_response.token = sample_fcm_token.token
            mock_response.user_id = sample_user_id
            mock_response.device_type = sample_fcm_token.device_type
            mock_response.device_info = sample_fcm_token.device_info
            mock_response.is_active = sample_fcm_token.is_active
            mock_response_class.model_validate.return_value = mock_response

            result = notification_service.get_user_tokens(sample_user_id, mock_session)

            # 검증
            assert len(result) == 1
            assert result[0].token == sample_fcm_token.token
            assert result[0].user_id == sample_user_id
            assert result[0].device_type == sample_fcm_token.device_type
            assert result[0].is_active == sample_fcm_token.is_active

            mock_session.execute.assert_called_once()
            mock_response_class.model_validate.assert_called_once_with(sample_fcm_token)

    def test_delete_token_success(
        self, notification_service, mock_session, sample_user_id, sample_fcm_token
    ):
        """토큰 삭제 성공 테스트"""
        # Mock: 토큰 찾기 성공
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = sample_fcm_token
        mock_session.execute.return_value = mock_execute_result
        mock_session.add = Mock()
        mock_session.commit = Mock()

        result = notification_service.delete_token(
            sample_user_id, "token-id-123", mock_session
        )

        # 검증
        assert result is True
        assert sample_fcm_token.is_active is False
        mock_session.execute.assert_called_once()
        mock_session.add.assert_called_once_with(sample_fcm_token)
        mock_session.commit.assert_called_once()

    def test_delete_token_not_found(
        self, notification_service, mock_session, sample_user_id
    ):
        """토큰 삭제 실패 - 토큰 없음"""
        # Mock: 토큰을 찾을 수 없는 경우
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute_result

        with pytest.raises(HTTPException) as exc_info:
            notification_service.delete_token(
                sample_user_id, "non-existent-token", mock_session
            )

        # 검증
        assert exc_info.value.status_code == 404
        assert "FCM 토큰을 찾을 수 없습니다" in exc_info.value.detail

    def test_get_notification_settings_existing(
        self,
        notification_service,
        mock_session,
        sample_user_id,
        sample_notification_settings,
    ):
        """기존 알림 설정 조회 테스트"""
        # Mock: 기존 설정 반환
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = (
            sample_notification_settings
        )
        mock_session.execute.return_value = mock_execute_result

        result = notification_service.get_notification_settings(
            sample_user_id, mock_session
        )

        # 검증 - NotificationSettingsResponse 필드와 매칭
        assert result.diary_reminder is True
        assert result.ai_content_ready is True
        assert result.weekly_report is True
        mock_session.execute.assert_called_once()

    def test_get_notification_settings_create_default(
        self, notification_service, mock_session, sample_user_id
    ):
        """기본 알림 설정 생성 테스트"""
        # Mock: 기존 설정이 없는 경우
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute_result
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        result = notification_service.get_notification_settings(
            sample_user_id, mock_session
        )

        # 검증: 기본값이 설정되어야 함
        assert result.diary_reminder is True
        assert result.ai_content_ready is True
        assert result.weekly_report is True
        mock_session.execute.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_update_notification_settings(
        self,
        notification_service,
        mock_session,
        sample_user_id,
        sample_notification_settings,
    ):
        """알림 설정 업데이트 테스트"""
        # Mock: 기존 설정 반환
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = (
            sample_notification_settings
        )
        mock_session.execute.return_value = mock_execute_result
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        settings_update = NotificationSettingsUpdate(
            diary_reminder=False, ai_content_ready=True, emotion_trend=False
        )

        result = notification_service.update_notification_settings(
            sample_user_id, settings_update, mock_session
        )

        # 검증: 서비스가 모델 속성을 올바르게 업데이트했는지 확인
        # emotion_trend=False가 report_notification_enabled=False로 설정되어야 함
        assert sample_notification_settings.diary_reminder_enabled is False
        assert sample_notification_settings.ai_processing_enabled is True
        assert sample_notification_settings.report_notification_enabled is False

        # 응답 검증: 모델 필드가 응답 필드로 올바르게 매핑되는지 확인
        assert result.diary_reminder is False
        assert result.ai_content_ready is True
        assert (
            result.weekly_report is False
        )  # report_notification_enabled -> weekly_report

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_fcm_service")
    async def test_send_notification_success(
        self, mock_get_fcm_service, notification_service, mock_session, sample_fcm_token
    ):
        """알림 전송 성공 테스트"""
        # Mock FCM 서비스
        mock_fcm = AsyncMock()
        mock_fcm.send_notification.return_value = {
            "success": True,
            "message_id": "test-message-123",
        }
        mock_get_fcm_service.return_value = mock_fcm

        # Mock 토큰 조회 - SQLAlchemy 2.0 패턴
        mock_execute_result = Mock()
        mock_execute_result.all.return_value = [sample_fcm_token]
        mock_session.execute.return_value = mock_execute_result
        mock_session.add = Mock()
        mock_session.commit = Mock()

        notification_request = NotificationSendRequest(
            user_ids=["test-user-123"],
            title="테스트 알림",
            body="테스트 메시지",
            notification_type="general",
            data={"type": "test"},
        )

        result = await notification_service.send_notification(
            notification_request, mock_session
        )

        # 검증
        assert result.success_count == 1
        assert result.failure_count == 0
        assert len(result.successful_tokens) == 1
        mock_fcm.send_notification.assert_called_once()
        mock_session.add.assert_called_once()  # 히스토리 저장 확인

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_fcm_service")
    async def test_send_notification_failure(
        self, mock_get_fcm_service, notification_service, mock_session, sample_fcm_token
    ):
        """알림 전송 실패 테스트"""
        # Mock FCM 서비스 - 실패 케이스
        mock_fcm = AsyncMock()
        mock_fcm.send_notification.side_effect = Exception("FCM 전송 실패")
        mock_get_fcm_service.return_value = mock_fcm

        # Mock 토큰 조회 - SQLAlchemy 2.0 패턴
        mock_execute_result = Mock()
        mock_execute_result.all.return_value = [sample_fcm_token]
        mock_session.execute.return_value = mock_execute_result
        mock_session.add = Mock()
        mock_session.commit = Mock()

        notification_request = NotificationSendRequest(
            user_ids=["test-user-123"],
            title="테스트 알림",
            body="테스트 메시지",
            notification_type="general",
        )

        result = await notification_service.send_notification(
            notification_request, mock_session
        )

        # 검증
        assert result.success_count == 0
        assert result.failure_count == 1
        assert len(result.failed_tokens) == 1

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_fcm_service")
    async def test_send_diary_reminder(
        self,
        mock_get_fcm_service,
        notification_service,
        mock_session,
        sample_fcm_token,
        sample_notification_settings,
    ):
        """다이어리 리마인더 전송 테스트"""
        # Mock FCM 서비스
        mock_fcm = AsyncMock()
        mock_fcm.send_notification.return_value = {"success": True}
        mock_get_fcm_service.return_value = mock_fcm

        # Mock 조회 - SQLAlchemy 2.0 패턴
        mock_execute_results = [
            Mock(
                scalar_one_or_none=Mock(return_value=sample_notification_settings)
            ),  # 설정 조회
            Mock(all=Mock(return_value=[sample_fcm_token])),  # 토큰 조회
        ]
        mock_session.execute.side_effect = mock_execute_results
        mock_session.add = Mock()
        mock_session.commit = Mock()

        result = await notification_service.send_diary_reminder(
            "test-user-123", mock_session
        )

        # 검증
        assert result.success_count == 1
        assert (
            "오늘의 감정을 새김에 기록해보세요"
            in mock_fcm.send_notification.call_args[1]["body"]
        )

    @pytest.mark.asyncio
    async def test_send_diary_reminder_disabled(
        self, notification_service, mock_session, sample_notification_settings
    ):
        """다이어리 리마인더 비활성화 테스트"""
        # Mock: 다이어리 리마인더 비활성화
        sample_notification_settings.diary_reminder_enabled = False
        mock_execute_result = Mock()
        mock_execute_result.scalar_one_or_none.return_value = (
            sample_notification_settings
        )
        mock_session.execute.return_value = mock_execute_result

        result = await notification_service.send_diary_reminder(
            "test-user-123", mock_session
        )

        # 검증: 알림이 전송되지 않아야 함
        assert result.success_count == 0
        assert result.failure_count == 0

    def test_get_notification_history(
        self, notification_service, mock_session, sample_user_id
    ):
        """알림 기록 조회 테스트"""
        # Mock 알림 기록
        mock_history = [
            NotificationHistory(
                id="history-1",
                user_id=sample_user_id,
                notification_type="diary_reminder",
                status="sent",
                sent_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            ),
            NotificationHistory(
                id="history-2",
                user_id=sample_user_id,
                notification_type="ai_content_ready",
                status="failed",
                error_message="전송 실패",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # Mock SQLAlchemy 2.0 패턴: 체이닝된 호출 구조
        mock_offset_result = Mock()
        mock_offset_result.limit.return_value.all.return_value = mock_history

        mock_scalars_result = Mock()
        mock_scalars_result.offset.return_value = mock_offset_result

        mock_execute_result = Mock()
        mock_execute_result.scalars.return_value = mock_scalars_result
        mock_session.execute.return_value = mock_execute_result

        result = notification_service.get_notification_history(
            sample_user_id, 10, 0, mock_session
        )

        # 검증
        assert len(result) == 2
        assert result[0].notification_type == "diary_reminder"
        assert result[1].status == "failed"


@pytest.mark.integration
class TestFCMServiceIntegration:
    """FCM 서비스 통합 테스트"""

    def test_token_lifecycle(self, notification_service, test_session, sample_user_id):
        """토큰 생명주기 통합 테스트"""
        # 실제 데이터베이스를 사용한 통합 테스트
        # 이 테스트는 실제 DB 설정이 필요합니다.
        pass
