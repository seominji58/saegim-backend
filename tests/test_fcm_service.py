"""
FCM 서비스 레이어 테스트
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from sqlmodel import Session
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
            enabled=True,
            diary_reminder=True,
            ai_content_ready=True,
            emotion_trend=True,
            anniversary=True,
            friend_share=False,
            quiet_hours_enabled=False,
            quiet_start_time="22:00",
            quiet_end_time="08:00",
            frequency="immediate",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_register_token_new_token(
        self, notification_service, mock_session, sample_user_id, sample_token_request
    ):
        """새로운 토큰 등록 테스트"""
        # Mock: 기존 토큰이 없는 경우
        mock_session.exec.return_value.first.return_value = None

        # Mock: 새 토큰 생성과 refresh 시 속성 설정
        mock_token = Mock()
        mock_token.id = "token-id-123"
        mock_token.token = sample_token_request.token
        mock_token.device_type = sample_token_request.device_type
        mock_token.device_info = sample_token_request.device_info
        mock_token.is_active = True
        mock_token.created_at = datetime.now(timezone.utc)
        mock_token.updated_at = datetime.now(timezone.utc)

        def mock_refresh(obj):
            # refresh 호출 시 객체에 속성 설정
            obj.id = mock_token.id
            obj.token = mock_token.token
            obj.created_at = mock_token.created_at
            obj.updated_at = mock_token.updated_at

        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock(side_effect=mock_refresh)

        result = notification_service.register_token(
            sample_user_id, sample_token_request, mock_session
        )

        # 검증
        assert result.token == sample_token_request.token
        assert result.device_type == sample_token_request.device_type
        assert result.device_info == sample_token_request.device_info
        assert result.is_active is True

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_register_token_update_existing(
        self, mock_session, sample_user_id, sample_token_request, sample_fcm_token
    ):
        """기존 토큰 업데이트 테스트"""
        # Mock: 기존 토큰이 있는 경우
        mock_session.exec.return_value.first.return_value = sample_fcm_token
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        result = notification_service.register_token(
            sample_user_id, sample_token_request, mock_session
        )

        # 검증
        assert result.token == sample_token_request.token
        assert result.is_active is True
        mock_session.commit.assert_called_once()

    def test_get_user_tokens(
        self, notification_service, mock_session, sample_user_id, sample_fcm_token
    ):
        """사용자 토큰 목록 조회 테스트"""
        # Mock: 토큰 목록 반환
        mock_session.exec.return_value.all.return_value = [sample_fcm_token]

        result = notification_service.get_user_tokens(sample_user_id, mock_session)

        # 검증
        assert len(result) == 1
        assert result[0].token == sample_fcm_token.token
        assert result[0].user_id == sample_user_id

    def test_delete_token_success(
        self, notification_service, mock_session, sample_user_id, sample_fcm_token
    ):
        """토큰 삭제 성공 테스트"""
        # Mock: 토큰 찾기 성공
        mock_session.exec.return_value.first.return_value = sample_fcm_token
        mock_session.commit = Mock()

        result = notification_service.delete_token(
            sample_user_id, "token-id-123", mock_session
        )

        # 검증
        assert result is True
        assert sample_fcm_token.is_active is False
        mock_session.commit.assert_called_once()

    def test_delete_token_not_found(
        self, notification_service, mock_session, sample_user_id
    ):
        """토큰 삭제 실패 - 토큰 없음"""
        # Mock: 토큰을 찾을 수 없는 경우
        mock_session.exec.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            notification_service.delete_token(
                sample_user_id, "nonexistent-token", mock_session
            )

        assert exc_info.value.status_code == 404

    def test_get_notification_settings_existing(
        self, mock_session, sample_user_id, sample_notification_settings
    ):
        """기존 알림 설정 조회 테스트"""
        # Mock: 기존 설정 반환
        mock_session.exec.return_value.first.return_value = sample_notification_settings

        result = notification_service.get_notification_settings(
            sample_user_id, mock_session
        )

        # 검증
        assert result.diary_reminder is True
        assert result.ai_content_ready is True
        assert result.emotion_trend is True

    def test_get_notification_settings_create_default(
        self, mock_session, sample_user_id
    ):
        """기본 알림 설정 생성 테스트"""
        # Mock: 기존 설정이 없는 경우
        mock_session.exec.return_value.first.return_value = None
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        result = notification_service.get_notification_settings(
            sample_user_id, mock_session
        )

        # 검증: 기본값이 설정되어야 함
        assert result.diary_reminder is True
        assert result.ai_content_ready is True
        assert result.emotion_trend is True
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_update_notification_settings(
        self, mock_session, sample_user_id, sample_notification_settings
    ):
        """알림 설정 업데이트 테스트"""
        # Mock: 기존 설정 반환
        mock_session.exec.return_value.first.return_value = sample_notification_settings
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        settings_update = NotificationSettingsUpdate(
            diary_reminder=False, ai_content_ready=True, emotion_trend=False
        )

        result = notification_service.update_notification_settings(
            sample_user_id, settings_update, mock_session
        )

        # 검증
        assert result.diary_reminder is False
        assert result.ai_content_ready is True
        assert result.emotion_trend is False
        mock_session.commit.assert_called_once()

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

        # Mock 토큰 조회
        mock_session.exec.return_value.all.return_value = [sample_fcm_token]
        mock_session.add = Mock()
        mock_session.commit = Mock()

        notification_request = NotificationSendRequest(
            user_ids=["test-user-123"],
            title="테스트 알림",
            body="테스트 메시지",
            data={"type": "test"},
        )

        result = await notification_service.send_notification(
            notification_request, mock_session
        )

        # 검증
        assert result.success_count == 1
        assert result.failure_count == 0
        assert len(result.results) == 1
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

        # Mock 토큰 조회
        mock_session.exec.return_value.all.return_value = [sample_fcm_token]
        mock_session.add = Mock()
        mock_session.commit = Mock()

        notification_request = NotificationSendRequest(
            user_ids=["test-user-123"], title="테스트 알림", body="테스트 메시지"
        )

        result = await notification_service.send_notification(
            notification_request, mock_session
        )

        # 검증
        assert result.success_count == 0
        assert result.failure_count == 1
        assert len(result.results) == 1
        assert "FCM 전송 실패" in result.results[0]["error"]

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

        # Mock 조회
        mock_session.exec.side_effect = [
            Mock(first=Mock(return_value=sample_notification_settings)),  # 설정 조회
            Mock(all=Mock(return_value=[sample_fcm_token])),  # 토큰 조회
        ]
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
        # 알림 설정 비활성화
        sample_notification_settings.diary_reminder = False
        mock_session.exec.return_value.first.return_value = sample_notification_settings

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
                title="테스트 알림 1",
                body="테스트 메시지 1",
                notification_type="diary_reminder",
                status="sent",
                created_at=datetime.now(timezone.utc),
            ),
            NotificationHistory(
                id="history-2",
                user_id=sample_user_id,
                title="테스트 알림 2",
                body="테스트 메시지 2",
                notification_type="ai_content_ready",
                status="failed",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        mock_session.exec.return_value.offset.return_value.limit.return_value.all.return_value = mock_history

        result = notification_service.get_notification_history(
            sample_user_id, 10, 0, mock_session
        )

        # 검증
        assert len(result) == 2
        assert result[0].title == "테스트 알림 1"
        assert result[1].status == "failed"


@pytest.mark.integration
class TestFCMServiceIntegration:
    """FCM 서비스 통합 테스트"""

    def test_token_lifecycle(self, notification_service, test_session, sample_user_id):
        """토큰 생명주기 통합 테스트"""
        # 실제 데이터베이스를 사용한 통합 테스트
        # 이 테스트는 실제 DB 설정이 필요합니다.
        pass
