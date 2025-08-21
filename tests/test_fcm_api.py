"""
FCM API 엔드포인트 테스트
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status
from datetime import datetime, timezone

from app.main import app
from app.core.security import get_current_user_id
from app.db.database import get_session
from app.services.fcm_service import FCMService
from app.schemas.fcm import (
    FCMTokenResponse,
    NotificationSettingsResponse,
    NotificationSendResponse,
    NotificationHistoryResponse,
)


class TestFCMAPI:
    """FCM API 테스트 클래스"""

    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        return TestClient(app)

    @pytest.fixture
    def mock_user_id(self):
        """테스트용 사용자 ID"""
        return "test-user-123"

    @pytest.fixture
    def mock_session(self):
        """Mock 데이터베이스 세션"""
        return Mock()

    @pytest.fixture(autouse=True)
    def setup_dependencies(self, mock_user_id, mock_session):
        """의존성 오버라이드 설정"""
        app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        app.dependency_overrides[get_session] = lambda: mock_session
        yield
        app.dependency_overrides.clear()

    def test_fcm_health_check(self, client):
        """FCM 헬스체크 테스트"""
        response = client.get("/api/fcm/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "FCM 서비스가 정상 작동 중입니다."
        assert data["data"] == "healthy"

    @patch.object(FCMService, 'register_token')
    def test_register_fcm_token_success(self, mock_register, client):
        """FCM 토큰 등록 성공 테스트"""
        # Mock 서비스 응답
        mock_response = FCMTokenResponse(
            id="token-id-123",
            user_id="test-user-123",
            token="test-fcm-token-12345",
            device_type="web",
            device_id="test-device-456",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_register.return_value = mock_response

        # 요청 데이터
        request_data = {
            "token": "test-fcm-token-12345",
            "device_type": "web",
            "device_id": "test-device-456"
        }

        response = client.post("/api/fcm/register-token", json=request_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "FCM 토큰이 성공적으로 등록되었습니다."
        assert data["data"]["token"] == "test-fcm-token-12345"
        mock_register.assert_called_once()

    @patch.object(FCMService, 'register_token')
    def test_register_fcm_token_validation_error(self, mock_register, client):
        """FCM 토큰 등록 유효성 검사 실패 테스트"""
        # 잘못된 요청 데이터 (토큰 누락)
        request_data = {
            "device_type": "web",
            "device_id": "test-device-456"
        }

        response = client.post("/api/fcm/register-token", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_register.assert_not_called()

    @patch.object(FCMService, 'get_user_tokens')
    def test_get_fcm_tokens(self, mock_get_tokens, client):
        """FCM 토큰 목록 조회 테스트"""
        # Mock 서비스 응답
        mock_tokens = [
            FCMTokenResponse(
                id="token-id-1",
                user_id="test-user-123",
                token="token-1",
                device_type="web",
                device_id="device-1",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            FCMTokenResponse(
                id="token-id-2",
                user_id="test-user-123",
                token="token-2",
                device_type="mobile",
                device_id="device-2",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]
        mock_get_tokens.return_value = mock_tokens

        response = client.get("/api/fcm/tokens")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["device_type"] == "web"
        assert data["data"][1]["device_type"] == "mobile"

    @patch.object(FCMService, 'delete_token')
    def test_delete_fcm_token_success(self, mock_delete, client):
        """FCM 토큰 삭제 성공 테스트"""
        mock_delete.return_value = True

        response = client.delete("/api/fcm/tokens/token-id-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"] is True
        mock_delete.assert_called_once_with("test-user-123", "token-id-123", mock_delete.call_args[0][2])

    @patch.object(FCMService, 'delete_token')
    def test_delete_fcm_token_not_found(self, mock_delete, client):
        """FCM 토큰 삭제 실패 - 토큰 없음 테스트"""
        from fastapi import HTTPException
        mock_delete.side_effect = HTTPException(status_code=404, detail="토큰을 찾을 수 없습니다.")

        response = client.delete("/api/fcm/tokens/nonexistent-token")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch.object(FCMService, 'get_notification_settings')
    def test_get_notification_settings(self, mock_get_settings, client):
        """알림 설정 조회 테스트"""
        mock_settings = NotificationSettingsResponse(
            id="settings-id-123",
            user_id="test-user-123",
            diary_reminder=True,
            ai_content_ready=True,
            weekly_summary=False,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_get_settings.return_value = mock_settings

        response = client.get("/api/fcm/settings")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["diary_reminder"] is True
        assert data["data"]["weekly_summary"] is False

    @patch.object(FCMService, 'update_notification_settings')
    def test_update_notification_settings(self, mock_update_settings, client):
        """알림 설정 업데이트 테스트"""
        mock_settings = NotificationSettingsResponse(
            id="settings-id-123",
            user_id="test-user-123",
            diary_reminder=False,
            ai_content_ready=True,
            weekly_summary=True,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        mock_update_settings.return_value = mock_settings

        request_data = {
            "diary_reminder": False,
            "ai_content_ready": True,
            "weekly_summary": True
        }

        response = client.put("/api/fcm/settings", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["diary_reminder"] is False
        assert data["data"]["weekly_summary"] is True

    @patch.object(FCMService, 'send_notification')
    @pytest.mark.asyncio
    async def test_send_push_notification_success(self, mock_send, client):
        """푸시 알림 전송 성공 테스트"""
        mock_response = NotificationSendResponse(
            success_count=2,
            failure_count=0,
            results=[
                {"user_id": "user-1", "status": "sent", "message_id": "msg-1"},
                {"user_id": "user-2", "status": "sent", "message_id": "msg-2"}
            ]
        )
        mock_send.return_value = mock_response

        request_data = {
            "user_ids": ["user-1", "user-2"],
            "title": "테스트 알림",
            "body": "테스트 메시지",
            "data": {"type": "test"}
        }

        response = client.post("/api/fcm/send-notification", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success_count"] == 2
        assert data["data"]["failure_count"] == 0

    @patch.object(FCMService, 'send_diary_reminder')
    @pytest.mark.asyncio
    async def test_send_diary_reminder_notification(self, mock_send_reminder, client):
        """다이어리 작성 알림 전송 테스트"""
        mock_response = NotificationSendResponse(
            success_count=1,
            failure_count=0,
            results=[{"user_id": "user-123", "status": "sent", "message_id": "msg-123"}]
        )
        mock_send_reminder.return_value = mock_response

        response = client.post("/api/fcm/send-diary-reminder/user-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success_count"] == 1

    @patch.object(FCMService, 'send_ai_content_ready')
    @pytest.mark.asyncio
    async def test_send_ai_content_ready_notification(self, mock_send_ai, client):
        """AI 콘텐츠 준비 완료 알림 전송 테스트"""
        mock_response = NotificationSendResponse(
            success_count=1,
            failure_count=0,
            results=[{"user_id": "user-123", "status": "sent", "message_id": "msg-456"}]
        )
        mock_send_ai.return_value = mock_response

        response = client.post("/api/fcm/send-ai-content-ready/user-123/diary-456")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success_count"] == 1

    @patch.object(FCMService, 'get_notification_history')
    def test_get_notification_history(self, mock_get_history, client):
        """알림 기록 조회 테스트"""
        mock_history = [
            NotificationHistoryResponse(
                id="history-1",
                user_id="test-user-123",
                title="다이어리 알림",
                body="오늘의 감정을 기록해보세요",
                notification_type="diary_reminder",
                status="sent",
                created_at=datetime.now(timezone.utc)
            ),
            NotificationHistoryResponse(
                id="history-2",
                user_id="test-user-123",
                title="AI 콘텐츠 준비",
                body="새로운 AI 콘텐츠가 준비되었습니다",
                notification_type="ai_content_ready",
                status="failed",
                error_message="토큰 만료",
                created_at=datetime.now(timezone.utc)
            )
        ]
        mock_get_history.return_value = mock_history

        response = client.get("/api/fcm/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["notification_type"] == "diary_reminder"
        assert data["data"][1]["status"] == "failed"

    def test_get_notification_history_with_pagination(self, client):
        """알림 기록 조회 페이지네이션 테스트"""
        response = client.get("/api/fcm/history?limit=5&offset=10")

        # 요청이 정상적으로 처리되는지만 확인 (실제 서비스는 Mock됨)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthorized_access(self, client):
        """인증되지 않은 접근 테스트"""
        # 의존성 오버라이드 제거
        app.dependency_overrides.clear()

        response = client.get("/api/fcm/tokens")
        
        # 인증 관련 에러가 발생해야 함 (실제 구현에 따라 상태 코드가 다를 수 있음)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.integration  
class TestFCMAPIIntegration:
    """FCM API 통합 테스트"""

    def test_full_fcm_workflow(self):
        """전체 FCM 워크플로우 통합 테스트"""
        # 실제 데이터베이스와 Firebase를 사용한 통합 테스트
        # 실제 환경 설정이 필요합니다.
        pass

    def test_fcm_api_with_real_database(self):
        """실제 데이터베이스를 사용한 FCM API 테스트"""
        # 실제 데이터베이스 연결이 필요한 테스트
        pass
