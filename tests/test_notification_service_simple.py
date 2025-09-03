"""
알림 서비스 간단한 단위 테스트
"""

import uuid
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.schemas.notification import (
    FCMTokenRegisterRequest,
    NotificationSendRequest,
    NotificationSettingsUpdate,
)
from app.services.notification_service import NotificationService


class TestNotificationServiceSimple:
    """NotificationService 간단한 테스트"""

    def test_extract_error_message_with_error(self):
        """에러 메시지 추출 테스트 - 에러 있는 경우"""
        result = {"response": {"error": {"code": 400, "message": "Invalid token"}}}

        service = NotificationService()
        error_msg = service._extract_error_message(result)
        assert "Invalid token" in error_msg

    def test_extract_error_message_no_error(self):
        """에러 메시지 추출 테스트 - 에러 없는 경우"""
        result = {"response": {}}

        service = NotificationService()
        error_msg = service._extract_error_message(result)
        assert "알 수 없는 오류" in error_msg

    def test_extract_error_message_no_response(self):
        """에러 메시지 추출 테스트 - 응답 없는 경우"""
        result = {}

        service = NotificationService()
        error_msg = service._extract_error_message(result)
        assert "알 수 없는 오류" in error_msg

    def test_get_active_token_count(self):
        """활성 토큰 개수 조회 테스트"""
        # Mock 데이터베이스 세션
        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        # 테스트 실행
        user_id = uuid.uuid4()
        service = NotificationService(mock_session)
        count = service.get_active_token_count(user_id)

        # 검증
        assert count == 5
        mock_session.execute.assert_called_once()

    def test_get_user_tokens_empty(self):
        """사용자 토큰 조회 테스트 - 빈 결과"""
        # Mock 데이터베이스 세션
        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # 테스트 실행
        user_id = uuid.uuid4()
        service = NotificationService(mock_session)
        tokens = service.get_user_tokens(user_id)

        # 검증
        assert len(tokens) == 0
        mock_session.execute.assert_called_once()

    def test_delete_token_not_found(self):
        """토큰 삭제 테스트 - 토큰 없음"""
        # Mock 데이터베이스 세션
        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # 테스트 실행
        user_id = uuid.uuid4()
        service = NotificationService(mock_session)
        result = service.delete_token(user_id, "fake_token_id")

        # 검증
        assert result is False
        mock_session.execute.assert_called_once()

    def test_delete_token_success(self):
        """토큰 삭제 테스트 - 성공"""
        # Mock FCM 토큰
        mock_token = Mock()
        mock_token.id = uuid.uuid4()

        # Mock 데이터베이스 세션
        mock_session = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_session.execute.return_value = mock_result

        # 테스트 실행
        user_id = uuid.uuid4()
        service = NotificationService(mock_session)
        result = service.delete_token(user_id, str(mock_token.id))

        # 검증 - TransactionManager 사용으로 인해 직접적인 delete/commit 호출은 없음
        assert result is True
        mock_session.execute.assert_called()

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
    async def test_send_notification_empty_user_list(self):
        """빈 사용자 목록 알림 전송 테스트"""
        # 빈 사용자 목록 요청
        empty_request = NotificationSendRequest(
            user_ids=[],
            title="테스트 알림",
            body="내용",
            notification_type="diary_reminder",
        )

        # Mock 데이터베이스 세션
        mock_db = Mock(spec=Session)
        service = NotificationService(mock_db)

        # 테스트 실행
        result = await service.send_notification(empty_request)

        # 검증
        assert result.success_count == 0
        assert result.failure_count == 0
        assert len(result.successful_tokens) == 0
        assert len(result.failed_tokens) == 0

    def test_register_token_validation_error(self):
        """토큰 등록 유효성 검증 테스트"""
        # 유효하지 않은 device_type으로 요청 생성시 Pydantic 유효성 검사 오류 발생
        with pytest.raises(ValidationError):
            FCMTokenRegisterRequest(
                token="valid_token_string",
                device_type="invalid_device_type",  # 잘못된 디바이스 타입
                device_info={"platform": "Web"},
            )

    def test_notification_settings_update_validation(self):
        """알림 설정 업데이트 유효성 검증 테스트"""
        # 정상적인 업데이트 요청 생성 - 새로운 스키마 필드 사용
        update_request = NotificationSettingsUpdate(
            push_enabled=True,
            diary_reminder_enabled=False,
            diary_reminder_time="19:30",
            diary_reminder_days=["monday", "wednesday", "friday"],
            ai_processing_enabled=True,
            report_notification_enabled=True,
            browser_push_enabled=False,
        )

        # 검증
        assert update_request.push_enabled is True
        assert update_request.diary_reminder_enabled is False
        assert update_request.diary_reminder_time == "19:30"
        assert update_request.diary_reminder_days == ["monday", "wednesday", "friday"]
        assert update_request.ai_processing_enabled is True
        assert update_request.report_notification_enabled is True
        assert update_request.browser_push_enabled is False
