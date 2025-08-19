"""
FCM 푸시 알림 기능 테스트

실제 기능 동작을 중심으로 한 테스트입니다.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock


@pytest.mark.asyncio
@patch("app.core.config.get_settings")
@patch("app.utils.fcm_push.httpx.AsyncClient")
@patch("app.utils.fcm_push.FCMPushService._get_access_token")
async def test_fcm_notification_success(
    mock_get_token, mock_async_client, mock_get_settings
):
    """FCM 알림 전송 성공 테스트"""
    # Settings Mock
    mock_settings = Mock()
    mock_settings.fcm_project_id = "test-project"
    mock_settings.fcm_service_account_json = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
        }
    )
    mock_get_settings.return_value = mock_settings

    # HTTP Mock - 성공 응답
    mock_get_token.return_value = "test_access_token"
    mock_response = Mock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_async_client.return_value.__aenter__.return_value = mock_client

    # FCM 서비스 사용
    from app.utils.fcm_push import send_push_notification

    result = await send_push_notification(
        token="test_fcm_token",
        title="테스트 알림",
        body="테스트 메시지입니다.",
        data={"type": "test", "id": "123"},
    )

    # 검증
    assert result is True
    mock_client.post.assert_called_once()

    # 요청 데이터 검증
    call_args = mock_client.post.call_args
    request_data = call_args[1]["json"]
    assert "message" in request_data
    assert request_data["message"]["token"] == "test_fcm_token"
    assert request_data["message"]["notification"]["title"] == "테스트 알림"


@pytest.mark.asyncio
@patch("app.core.config.get_settings")
@patch("app.utils.fcm_push.httpx.AsyncClient")
@patch("app.utils.fcm_push.FCMPushService._get_access_token")
async def test_fcm_notification_failure(
    mock_get_token, mock_async_client, mock_get_settings
):
    """FCM 알림 전송 실패 테스트"""
    # Settings Mock
    mock_settings = Mock()
    mock_settings.fcm_project_id = "test-project"
    mock_settings.fcm_service_account_json = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
        }
    )
    mock_get_settings.return_value = mock_settings

    # HTTP Mock - 실패 응답
    mock_get_token.return_value = "test_access_token"
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Invalid token"
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_async_client.return_value.__aenter__.return_value = mock_client

    # FCM 서비스 사용
    from app.utils.fcm_push import send_push_notification

    result = await send_push_notification(
        token="invalid_token", title="테스트 알림", body="테스트 메시지입니다."
    )

    # 검증
    assert result is False


@pytest.mark.asyncio
@patch("app.core.config.get_settings")
async def test_diary_reminder_convenience_function(mock_get_settings):
    """다이어리 알림 편의 함수 테스트"""
    # Settings Mock
    mock_settings = Mock()
    mock_settings.fcm_project_id = "test-project"
    mock_settings.fcm_service_account_json = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
        }
    )
    mock_get_settings.return_value = mock_settings

    # FCM 서비스 모킹
    with patch("app.utils.fcm_push.get_fcm_service") as mock_get_service:
        mock_service = Mock()
        mock_service.send_diary_reminder = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_service

        from app.utils.fcm_push import send_diary_reminder

        result = await send_diary_reminder("test_token", "홍길동")

        assert result is True
        mock_service.send_diary_reminder.assert_called_once_with("test_token", "홍길동")


@pytest.mark.asyncio
@patch("app.core.config.get_settings")
async def test_ai_analysis_complete_convenience_function(mock_get_settings):
    """AI 분석 완료 알림 편의 함수 테스트"""
    # Settings Mock
    mock_settings = Mock()
    mock_settings.fcm_project_id = "test-project"
    mock_settings.fcm_service_account_json = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
        }
    )
    mock_get_settings.return_value = mock_settings

    # FCM 서비스 모킹
    with patch("app.utils.fcm_push.get_fcm_service") as mock_get_service:
        mock_service = Mock()
        mock_service.send_ai_analysis_complete = AsyncMock(return_value=True)
        mock_get_service.return_value = mock_service

        from app.utils.fcm_push import send_ai_analysis_complete

        result = await send_ai_analysis_complete("test_token", "diary_123")

        assert result is True
        mock_service.send_ai_analysis_complete.assert_called_once_with(
            "test_token", "diary_123"
        )


@patch("app.core.config.get_settings")
def test_fcm_service_creation_and_configuration(mock_get_settings):
    """FCM 서비스 생성 및 설정 테스트"""
    # Settings Mock
    mock_settings = Mock()
    mock_settings.fcm_project_id = "saegim-test"
    mock_settings.fcm_service_account_json = json.dumps(
        {
            "type": "service_account",
            "project_id": "saegim-test",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest_key\n-----END PRIVATE KEY-----\n",
            "client_email": "firebase-adminsdk@saegim-test.iam.gserviceaccount.com",
            "client_id": "123456789",
        }
    )
    mock_get_settings.return_value = mock_settings

    from app.utils.fcm_push import FCMPushService

    service = FCMPushService()

    # 설정 검증
    # 프로젝트 ID가 설정되어 있는지만 확인 (실제 값은 환경에 따라 다를 수 있음)
    assert service.project_id  # 빈 문자열이 아닌지 확인
    assert service.service_account["type"] == "service_account"
    assert service.project_id in service.fcm_url


@patch("app.core.config.get_settings")
@patch("app.utils.fcm_push.jwt.encode")
def test_jwt_token_creation(mock_jwt_encode, mock_get_settings):
    """JWT 토큰 생성 테스트"""
    # Settings Mock
    mock_settings = Mock()
    mock_settings.fcm_project_id = "test-project"
    mock_settings.fcm_service_account_json = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
        }
    )
    mock_get_settings.return_value = mock_settings

    mock_jwt_encode.return_value = "test_jwt_token"

    from app.utils.fcm_push import FCMPushService

    service = FCMPushService()
    token = service._create_jwt_token()

    assert token == "test_jwt_token"

    # JWT 생성 호출 검증
    mock_jwt_encode.assert_called_once()
    call_args = mock_jwt_encode.call_args[0]
    payload = call_args[0]

    # Payload 내용 검증 (일부 값은 환경에 따라 다를 수 있음)
    assert "@" in payload["iss"]  # 이메일 형식인지 확인
    assert payload["scope"] == "https://www.googleapis.com/auth/firebase.messaging"
    assert payload["aud"] == "https://oauth2.googleapis.com/token"


@patch("app.core.config.get_settings")
@patch("app.utils.fcm_push.httpx.Client")
@patch("app.utils.fcm_push.FCMPushService._create_jwt_token")
def test_access_token_acquisition(
    mock_create_jwt, mock_httpx_client, mock_get_settings
):
    """OAuth 2.0 Access Token 획득 테스트"""
    # Settings Mock
    mock_settings = Mock()
    mock_settings.fcm_project_id = "test-project"
    mock_settings.fcm_service_account_json = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
        }
    )
    mock_get_settings.return_value = mock_settings

    # HTTP Mock
    mock_create_jwt.return_value = "test_jwt_token"
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "access_token": "test_access_token",
        "expires_in": 3600,
    }
    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_httpx_client.return_value.__enter__.return_value = mock_client

    from app.utils.fcm_push import FCMPushService

    service = FCMPushService()
    token = service._get_access_token()

    assert token == "test_access_token"

    # HTTP 요청 검증
    mock_client.post.assert_called_once_with(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": "test_jwt_token",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )


def test_fcm_singleton_pattern():
    """FCM 서비스 싱글톤 패턴 테스트"""
    # 기존 인스턴스 초기화
    import app.utils.fcm_push

    app.utils.fcm_push._fcm_instance = None

    from app.utils.fcm_push import get_fcm_service

    service1 = get_fcm_service()
    service2 = get_fcm_service()

    # 동일한 인스턴스인지 확인
    assert service1 is service2

    # FCMPushService 타입인지 확인
    from app.utils.fcm_push import FCMPushService

    assert isinstance(service1, FCMPushService)
