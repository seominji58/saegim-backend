"""
알림 서비스 간단한 단위 테스트
"""

import uuid
from unittest.mock import Mock

import pytest
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

        error_msg = NotificationService._extract_error_message(result)
        assert "Invalid token" in error_msg

    def test_extract_error_message_no_error(self):
        """에러 메시지 추출 테스트 - 에러 없는 경우"""
        result = {"response": {}}

        error_msg = NotificationService._extract_error_message(result)
        assert "알 수 없는 오류" in error_msg

    def test_extract_error_message_no_response(self):
        """에러 메시지 추출 테스트 - 응답 없는 경우"""
        result = {}

        error_msg = NotificationService._extract_error_message(result)
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
        count = NotificationService.get_active_token_count(user_id, mock_session)

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
        tokens = NotificationService.get_user_tokens(user_id, mock_session)

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
        result = NotificationService.delete_token(
            user_id, "fake_token_id", mock_session
        )

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
        result = NotificationService.delete_token(
            user_id, str(mock_token.id), mock_session
        )

        # 검증
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.delete.assert_called_once_with(mock_token)
        mock_session.commit.assert_called_once()

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
        result = await service.send_notification(empty_request, mock_db)

        # 검증
        assert "sent_notifications" in result
        assert len(result["sent_notifications"]) == 0

    def test_register_token_validation_error(self):
        """토큰 등록 유효성 검증 테스트"""
        # 빈 토큰으로 요청 생성시 Pydantic 유효성 검사 오류 발생
        with pytest.raises(Exception):
            FCMTokenRegisterRequest(
                token="",  # 빈 토큰
                device_type="web",
                device_info={"platform": "Web"},
            )

    def test_notification_settings_update_validation(self):
        """알림 설정 업데이트 유효성 검증 테스트"""
        # 정상적인 업데이트 요청 생성
        update_request = NotificationSettingsUpdate(
            enabled=True,
            diary_reminder=False,
            ai_content_ready=True,
        )

        # 검증
        assert update_request.enabled is True
        assert update_request.diary_reminder is False
        assert update_request.ai_content_ready is True
