"""
알림 서비스 단위 테스트
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.fcm import FCMToken, NotificationHistory, NotificationSettings
from app.schemas.notification import (
    FCMTokenRegisterRequest,
    FCMTokenResponse,
    NotificationSendRequest,
    NotificationSettingsUpdate,
)
from app.services.notification_service import NotificationService


class TestNotificationService:
    """NotificationService 단위 테스트"""

    @pytest.fixture
    def mock_db(self):
        """Mock 데이터베이스 세션"""
        return Mock(spec=Session)

    @pytest.fixture
    def notification_service(self, mock_db):
        """NotificationService 인스턴스"""
        return NotificationService(mock_db)

    @pytest.fixture
    def sample_user_id(self):
        """테스트용 사용자 ID"""
        return uuid.uuid4()

    @pytest.fixture
    def sample_fcm_token(self, sample_user_id):
        """테스트용 FCM 토큰"""
        return FCMToken(
            id=uuid.uuid4(),
            user_id=sample_user_id,
            token="test_fcm_token_12345",
            device_type="web",
            device_info={"platform": "Web", "version": "1.0"},
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_notification_settings(self, sample_user_id):
        """테스트용 알림 설정"""
        return NotificationSettings(
            id=uuid.uuid4(),
            user_id=sample_user_id,
            push_enabled=True,
            diary_reminder_enabled=True,
            diary_reminder_time="21:00",
            diary_reminder_days=[
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
            ],
            report_notification_enabled=True,
            ai_processing_enabled=True,
            browser_push_enabled=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_token_register_request(self):
        """테스트용 토큰 등록 요청"""
        return FCMTokenRegisterRequest(
            token="new_fcm_token_456",
            device_type="ios",
            device_info={"platform": "iOS", "version": "15.0"},
        )

    @pytest.fixture
    def sample_notification_request(self):
        """테스트용 알림 전송 요청"""
        return NotificationSendRequest(
            user_ids=[str(uuid.uuid4())],  # 문자열로 변환
            title="테스트 알림",
            body="테스트 메시지 내용",
            notification_type="diary_reminder",
        )

    def test_register_token_new_token(
        self,
        notification_service,
        mock_db,
        sample_user_id,
        sample_token_register_request,
    ):
        """새로운 토큰 등록 테스트"""
        # UPSERT 결과 Mock 설정 (새 토큰 생성)
        mock_token_result = Mock()
        mock_token_result.id = sample_user_id
        mock_token_result.token = sample_token_register_request.token
        mock_token_result.device_type = sample_token_register_request.device_type
        mock_token_result.device_info = sample_token_register_request.device_info
        mock_token_result.is_active = True
        mock_token_result.created_at = datetime.now(UTC)
        mock_token_result.updated_at = datetime.now(UTC)

        # execute 반환값 Mock 설정
        mock_result = Mock()
        mock_result.scalar_one.return_value = mock_token_result
        mock_db.execute.return_value = mock_result

        # DB Mock 설정
        mock_db.commit = Mock()

        # 테스트 실행
        result = notification_service.register_token(
            sample_user_id, sample_token_register_request, mock_db
        )

        # 검증
        mock_db.execute.assert_called()  # UPSERT 실행
        mock_db.commit.assert_called()
        assert isinstance(result, FCMTokenResponse)
        assert result.token == sample_token_register_request.token
        assert result.device_type == sample_token_register_request.device_type

    def test_register_token_update_existing(
        self, notification_service, mock_db, sample_user_id, sample_fcm_token
    ):
        """기존 토큰 업데이트 테스트"""
        # 업데이트 요청 (다른 토큰 값으로)
        update_request = FCMTokenRegisterRequest(
            token="updated_fcm_token_789",
            device_type="android",
            device_info=sample_fcm_token.device_info,  # 같은 디바이스 정보
        )

        # UPSERT 결과 Mock 설정 (업데이트된 토큰)
        mock_token_result = Mock()
        mock_token_result.id = sample_user_id
        mock_token_result.token = update_request.token
        mock_token_result.device_type = update_request.device_type
        mock_token_result.device_info = update_request.device_info
        mock_token_result.is_active = True
        mock_token_result.created_at = datetime.now(UTC)
        mock_token_result.updated_at = datetime.now(UTC)

        # execute 반환값 Mock 설정
        mock_result = Mock()
        mock_result.scalar_one.return_value = mock_token_result
        mock_db.execute.return_value = mock_result

        # DB Mock 설정
        mock_db.commit = Mock()

        # 테스트 실행
        result = notification_service.register_token(
            sample_user_id, update_request, mock_db
        )

        # 검증 - 업데이트된 토큰 반환
        mock_db.execute.assert_called()  # UPSERT 실행
        mock_db.commit.assert_called()
        assert isinstance(result, FCMTokenResponse)
        assert result.token == update_request.token
        assert result.device_type == update_request.device_type

    def test_get_user_tokens(
        self, notification_service, sample_user_id, sample_fcm_token
    ):
        """사용자 토큰 조회 테스트"""
        # Mock 데이터베이스 세션 생성
        mock_session = Mock(spec=Session)

        # 토큰 조회 Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_fcm_token]
        mock_session.execute.return_value = mock_result

        # 테스트 실행
        tokens = notification_service.get_user_tokens(sample_user_id, mock_session)

        # 검증
        assert len(tokens) == 1
        assert tokens[0].token == sample_fcm_token.token
        assert tokens[0].device_type == sample_fcm_token.device_type
        assert tokens[0].is_active == sample_fcm_token.is_active

    def test_delete_token_success(
        self, notification_service, sample_user_id, sample_fcm_token
    ):
        """토큰 삭제 성공 테스트"""
        # Mock 데이터베이스 세션 생성
        mock_session = Mock(spec=Session)

        # 기존 토큰 조회 Mock 설정
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_fcm_token
        mock_session.execute.return_value = mock_result

        # DB Mock 설정
        mock_session.add = Mock()
        mock_session.commit = Mock()

        # 테스트 실행
        result = notification_service.delete_token(
            sample_user_id, str(sample_fcm_token.id), mock_session
        )

        # 검증
        assert result is True
        assert sample_fcm_token.is_active is False  # 토큰이 비활성화되어야 함
        mock_session.add.assert_called_once_with(sample_fcm_token)
        mock_session.commit.assert_called_once()

    def test_delete_token_not_found(self, notification_service, sample_user_id):
        """토큰 삭제 실패 테스트 (토큰 없음)"""
        # Mock 데이터베이스 세션 생성
        mock_session = Mock(spec=Session)

        # 토큰 없음 Mock 설정
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # 테스트 실행
        result = notification_service.delete_token(
            sample_user_id, "nonexistent_token_id", mock_session
        )

        # 검증
        assert result is False
        # add와 commit이 호출되지 않았는지 확인
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_get_notification_settings_existing(
        self, notification_service, sample_user_id, sample_notification_settings
    ):
        """기존 알림 설정 조회 테스트"""
        # Mock 데이터베이스 세션 생성
        mock_session = Mock(spec=Session)

        # 기존 설정 조회 Mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_notification_settings
        mock_session.execute.return_value = mock_result

        # 테스트 실행
        settings = notification_service.get_notification_settings(
            sample_user_id, mock_session
        )

        # 검증 - 새로운 스키마 필드들 확인
        assert settings.push_enabled == sample_notification_settings.push_enabled
        assert (
            settings.diary_reminder_enabled
            == sample_notification_settings.diary_reminder_enabled
        )
        assert (
            settings.diary_reminder_time
            == sample_notification_settings.diary_reminder_time
        )
        assert (
            settings.diary_reminder_days
            == sample_notification_settings.diary_reminder_days
        )
        assert (
            settings.ai_processing_enabled
            == sample_notification_settings.ai_processing_enabled
        )
        assert (
            settings.report_notification_enabled
            == sample_notification_settings.report_notification_enabled
        )
        assert (
            settings.browser_push_enabled
            == sample_notification_settings.browser_push_enabled
        )

    def test_get_notification_settings_create_default(
        self, notification_service, sample_user_id
    ):
        """기본 알림 설정 생성 테스트"""
        import uuid
        from datetime import UTC, datetime

        # Mock 데이터베이스 세션 생성
        mock_session = Mock(spec=Session)

        # 기존 설정 없음 Mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # DB Mock 설정 - refresh 메서드가 데이터베이스 필드를 시뮬레이션하도록 설정
        mock_session.add = Mock()
        mock_session.commit = Mock()

        def mock_refresh(settings):
            """데이터베이스가 설정하는 필드들을 시뮬레이션"""
            settings.id = uuid.uuid4()
            settings.created_at = datetime.now(UTC)
            settings.updated_at = datetime.now(UTC)

        mock_session.refresh = Mock(side_effect=mock_refresh)

        # 테스트 실행
        settings = notification_service.get_notification_settings(
            sample_user_id, mock_session
        )

        # 검증 - 기본값으로 새 설정이 생성됨
        assert settings is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # 생성된 설정 검증
        added_settings = mock_session.add.call_args[0][0]
        assert isinstance(added_settings, NotificationSettings)
        assert added_settings.user_id == sample_user_id
        assert added_settings.diary_reminder_enabled is True  # 기본값
        assert added_settings.ai_processing_enabled is True  # 기본값
        assert added_settings.report_notification_enabled is True  # 기본값

        # 반환된 응답 객체 검증 (NotificationSettingsResponse)
        assert hasattr(settings, "user_id")
        assert hasattr(settings, "diary_reminder_enabled")
        assert hasattr(settings, "ai_processing_enabled")
        assert hasattr(settings, "report_notification_enabled")

    def test_update_notification_settings(
        self, notification_service, sample_user_id, sample_notification_settings
    ):
        """알림 설정 업데이트 테스트"""
        # Mock 데이터베이스 세션 생성
        mock_session = Mock(spec=Session)

        # 기존 설정 조회 Mock
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_notification_settings
        mock_session.execute.return_value = mock_result

        # DB Mock 설정
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        # 업데이트 요청 - 새로운 스키마 필드 사용
        update_request = NotificationSettingsUpdate(
            push_enabled=True,
            diary_reminder_enabled=False,
            diary_reminder_time="20:00",
            diary_reminder_days=["saturday", "sunday"],
            ai_processing_enabled=True,
            report_notification_enabled=False,
        )

        # 테스트 실행
        settings = notification_service.update_notification_settings(
            sample_user_id, update_request, mock_session
        )

        # 검증 - 설정이 업데이트됨  (실제 서비스 로직에 따라 설정됨)
        assert settings is not None
        mock_session.add.assert_called_once_with(sample_notification_settings)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(sample_notification_settings)

    @pytest.mark.asyncio
    async def test_send_notification_success(
        self, notification_service, mock_db, sample_notification_request
    ):
        """알림 전송 성공 테스트"""
        # FCM 토큰 조회 Mock 설정
        sample_token = FCMToken(
            id=uuid.uuid4(),
            user_id=sample_notification_request.user_ids[0],
            token="test_fcm_token",
            device_type="web",
            device_info={"platform": "Web", "version": "1.0"},
            is_active=True,
        )

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_token]
        mock_db.execute.return_value = mock_result

        # FCM 서비스 Mock 설정
        with patch("app.services.notification_service.get_fcm_service") as mock_get_fcm:
            mock_fcm_service = Mock()
            mock_fcm_service.send_notification = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": "test_message_123",
                    "response": {"name": "projects/test/messages/123"},
                }
            )
            mock_get_fcm.return_value = mock_fcm_service

            # DB Mock 설정
            mock_db.add = Mock()
            mock_db.commit = Mock()

            # 테스트 실행
            result = await notification_service.send_notification(
                sample_notification_request, mock_db
            )

            # 검증
            assert result.success_count == 1
            assert result.failure_count == 0
            assert len(result.successful_tokens) == 1
            assert result.successful_tokens[0] == "test_fcm_token"

            # FCM 서비스 호출 검증
            mock_fcm_service.send_notification.assert_called_once()

            # 알림 기록 저장 검증
            mock_db.add.assert_called_once()
            added_history = mock_db.add.call_args[0][0]
            assert isinstance(added_history, NotificationHistory)
            assert (
                added_history.data_payload["title"] == sample_notification_request.title
            )
            assert (
                added_history.data_payload["body"] == sample_notification_request.body
            )
            assert (
                added_history.notification_type
                == sample_notification_request.notification_type
            )

    @pytest.mark.asyncio
    async def test_send_notification_no_tokens(
        self, notification_service, mock_db, sample_notification_request
    ):
        """토큰 없는 사용자 알림 전송 테스트"""
        # 토큰 없음 Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 테스트 실행
        result = await notification_service.send_notification(
            sample_notification_request, mock_db
        )

        # 검증
        assert result.success_count == 0
        assert result.failure_count == 0
        assert len(result.successful_tokens) == 0
        assert len(result.failed_tokens) == 0
        assert "전송할 활성 토큰이 없습니다" in result.message

    @pytest.mark.asyncio
    async def test_send_notification_fcm_error(
        self, notification_service, mock_db, sample_notification_request
    ):
        """FCM 전송 오류 테스트"""
        # FCM 토큰 Mock 설정
        sample_token = FCMToken(
            id=uuid.uuid4(),
            user_id=sample_notification_request.user_ids[0],
            token="test_fcm_token",
            device_type="web",
            device_info={"platform": "Web", "version": "1.0"},
            is_active=True,
        )

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_token]
        mock_db.execute.return_value = mock_result

        # FCM 서비스 Mock 설정 (오류 발생)
        with patch("app.services.notification_service.get_fcm_service") as mock_get_fcm:
            mock_fcm_service = Mock()
            mock_fcm_service.send_notification = AsyncMock(
                side_effect=Exception("FCM Service Error")
            )
            mock_get_fcm.return_value = mock_fcm_service

            # DB Mock 설정
            mock_db.add = Mock()
            mock_db.commit = Mock()

            # 테스트 실행
            result = await notification_service.send_notification(
                sample_notification_request, mock_db
            )

            # 검증
            assert result.success_count == 0
            assert result.failure_count == 1
            assert len(result.failed_tokens) == 1
            assert result.failed_tokens[0] == "test_fcm_token"

    def test_get_active_token_count(self, notification_service, sample_user_id):
        """활성 토큰 개수 조회 테스트"""
        # Mock 데이터베이스 세션 생성
        mock_session = Mock(spec=Session)

        # 토큰 개수 Mock 설정
        mock_result = Mock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        # 테스트 실행
        count = notification_service.get_active_token_count(
            sample_user_id, mock_session
        )

        # 검증
        assert count == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_invalid_tokens(self, notification_service):
        """유효하지 않은 토큰 정리 테스트"""
        # Mock 데이터베이스 세션 생성
        mock_session = Mock(spec=Session)

        # 유효하지 않은 토큰들 Mock 설정
        invalid_tokens = [
            FCMToken(id=uuid.uuid4(), token="invalid_token_1", is_active=True),
            FCMToken(id=uuid.uuid4(), token="invalid_token_2", is_active=True),
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = invalid_tokens
        mock_session.execute.return_value = mock_result

        # FCM 서비스 Mock 설정
        with patch("app.services.notification_service.get_fcm_service") as mock_get_fcm:
            mock_fcm_service = Mock()
            # 첫 번째 토큰은 유효, 두 번째는 UNREGISTERED로 무효
            mock_fcm_service.send_notification = AsyncMock(
                side_effect=[
                    {"success": True, "message_id": "test_123"},  # 유효한 토큰
                    {"success": False, "error_type": "UNREGISTERED"},  # 무효한 토큰
                ]
            )
            mock_get_fcm.return_value = mock_fcm_service

            # DB Mock 설정
            mock_session.add = Mock()
            mock_session.commit = Mock()

            # 테스트 실행
            cleaned_count = await notification_service.cleanup_invalid_tokens(
                mock_session
            )

            # 검증 - 1개 토큰이 비활성화됨
            assert cleaned_count == 1

            # 두 번째 토큰이 비활성화되었는지 확인
            assert invalid_tokens[1].is_active is False
            assert invalid_tokens[0].is_active is True  # 첫 번째는 유지

    def test_extract_error_message(self):
        """에러 메시지 추출 테스트"""
        # 정상적인 응답 구조
        normal_result = {
            "response": {"error": {"code": 400, "message": "Invalid token"}}
        }

        service = NotificationService()
        error_msg = service._extract_error_message(normal_result)
        assert "Invalid token" in error_msg

        # 에러 구조가 없는 경우
        empty_result = {"response": {}}
        error_msg = service._extract_error_message(empty_result)
        assert "알 수 없는 오류" in error_msg

        # 응답이 없는 경우
        no_response = {}
        error_msg = service._extract_error_message(no_response)
        assert "알 수 없는 오류" in error_msg


class TestNotificationServiceEdgeCases:
    """NotificationService 엣지 케이스 테스트"""

    @pytest.fixture
    def mock_db(self):
        """Mock 데이터베이스 세션"""
        return Mock(spec=Session)

    @pytest.fixture
    def notification_service(self, mock_db):
        """NotificationService 인스턴스"""
        return NotificationService(mock_db)

    @pytest.fixture
    def sample_user_id(self):
        """테스트용 사용자 ID"""
        return uuid.uuid4()

    def test_register_token_validation(
        self, notification_service, mock_db, sample_user_id
    ):
        """토큰 등록 유효성 검증 테스트"""
        # 유효하지 않은 device_type으로 ValidationError 발생시킴
        with pytest.raises(ValidationError):  # Pydantic 유효성 검사 오류 발생
            FCMTokenRegisterRequest(
                token="valid_token_string",
                device_type="invalid_device_type",  # 잘못된 디바이스 타입
                device_info={"platform": "Web"},
            )

    def test_notification_service_initialization(self):
        """NotificationService 초기화 테스트"""
        # DB 없이 초기화
        service = NotificationService()
        assert service.db is None

        # DB와 함께 초기화
        mock_db = Mock(spec=Session)
        service_with_db = NotificationService(mock_db)
        assert service_with_db.db == mock_db

    @pytest.mark.asyncio
    async def test_send_notification_empty_user_list(
        self, notification_service, mock_db
    ):
        """빈 사용자 목록 알림 전송 테스트"""
        # 빈 사용자 목록 요청
        empty_request = NotificationSendRequest(
            user_ids=[],  # 빈 목록
            title="테스트 알림",
            body="내용",
            notification_type="diary_reminder",
        )

        # 테스트 실행
        result = await notification_service.send_notification(empty_request, mock_db)

        # 검증
        assert result.success_count == 0
        assert result.failure_count == 0
        assert len(result.successful_tokens) == 0
        assert len(result.failed_tokens) == 0
        assert "전송할 사용자가 없습니다" in result.message
