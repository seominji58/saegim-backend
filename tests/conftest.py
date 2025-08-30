"""
테스트용 공통 설정 및 픽스처
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.fcm import FCMToken, NotificationHistory, NotificationSettings
from app.models.user import User


@pytest.fixture
def test_engine():
    """테스트용 인메모리 데이터베이스 엔진"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


@pytest.fixture
def test_session(test_engine):
    """테스트용 데이터베이스 세션"""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def sample_user():
    """테스트용 사용자"""
    return User(
        id="test-user-123",
        email="test@example.com",
        name="테스트 사용자",
        provider="google",
        provider_id="google-123",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_fcm_token(sample_user):
    """테스트용 FCM 토큰"""
    return FCMToken(
        id="token-id-123",
        user_id=sample_user.id,
        token="test-fcm-token-12345",
        device_type="web",
        device_id="test-device-456",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_notification_settings(sample_user):
    """테스트용 알림 설정"""
    return NotificationSettings(
        id="settings-id-123",
        user_id=sample_user.id,
        diary_reminder=True,
        ai_content_ready=True,
        weekly_summary=False,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_notification_history(sample_user):
    """테스트용 알림 기록"""
    return NotificationHistory(
        id="history-id-123",
        user_id=sample_user.id,
        title="테스트 알림",
        body="테스트 메시지",
        notification_type="diary_reminder",
        status="sent",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_fcm_service():
    """Mock FCM 서비스"""
    mock = Mock()
    mock.send_notification.return_value = {
        "success": True,
        "message_id": "test-message-123",
    }
    return mock


# 환경변수 모킹을 위한 픽스처
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """테스트용 환경변수 설정"""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", "/test/path/credentials.json")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "test-access-key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "test-secret-key")


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI 서비스"""
    mock = Mock()
    mock.chat.completions.create.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content='{"emotion": "기쁨", "confidence": 0.85, "keywords": ["행복", "즐거움"], "text": "테스트 AI 생성 텍스트"}'
                )
            )
        ],
        usage=Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150),
    )
    return mock


@pytest.fixture
def mock_minio_client():
    """Mock MinIO 클라이언트"""
    mock = Mock()
    mock.bucket_exists.return_value = True
    mock.put_object.return_value = Mock(etag="test-etag")
    mock.remove_object.return_value = None
    mock.presigned_get_object.return_value = "http://test-minio/test-image.jpg"
    return mock


# 마커 설정
pytest_plugins: list[str] = []
