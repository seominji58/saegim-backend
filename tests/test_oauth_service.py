"""
OAuth 서비스 단위 테스트
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constants import AccountType, OAuthProvider
from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.schemas.oauth import GoogleOAuthResponse, OAuthUserInfo
from app.services.oauth import GoogleOAuthService


class TestGoogleOAuthService:
    """GoogleOAuthService 단위 테스트"""

    @pytest.fixture
    def mock_settings(self):
        """Mock 설정"""
        with patch("app.services.oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = "test_client_secret"
            mock_settings.google_redirect_uri = (
                "http://localhost:8000/auth/google/callback"
            )
            mock_settings.google_token_uri = "https://oauth2.googleapis.com/token"
            yield mock_settings

    @pytest.fixture
    def oauth_service(self, mock_settings):
        """GoogleOAuthService 인스턴스"""
        return GoogleOAuthService()

    @pytest.fixture
    def mock_db(self):
        """Mock 데이터베이스 세션"""
        return Mock(spec=Session)

    @pytest.fixture
    def sample_token_response(self):
        """테스트용 토큰 응답"""
        return GoogleOAuthResponse(
            access_token="test_access_token",
            token_type="Bearer",
            refresh_token="test_refresh_token",
            expires_in=3600,
        )

    @pytest.fixture
    def sample_user_info(self):
        """테스트용 사용자 정보"""
        return OAuthUserInfo(
            id="google_user_123",
            email="test@example.com",
            name="테스트 사용자",
            picture="https://example.com/profile.jpg",
        )

    @pytest.fixture
    def sample_user(self, sample_user_info):
        """테스트용 사용자"""
        return User(
            id=uuid.uuid4(),
            email=sample_user_info.email,
            nickname=sample_user_info.name,
            profile_image_url=sample_user_info.picture,
            account_type=AccountType.SOCIAL.value,
            provider=OAuthProvider.GOOGLE.value,
            provider_id=sample_user_info.id,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_oauth_token(self, sample_user, sample_token_response):
        """테스트용 OAuth 토큰"""
        return OAuthToken(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            provider=OAuthProvider.GOOGLE.value,
            access_token=sample_token_response.access_token,
            refresh_token=sample_token_response.refresh_token,
            expires_at=datetime.now(UTC)
            + timedelta(seconds=sample_token_response.expires_in),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, oauth_service, sample_token_response):
        """액세스 토큰 요청 성공 테스트"""
        # http_client.post_json Mock 설정
        with patch("app.services.oauth.http_client") as mock_http_client:
            mock_http_client.post_json = AsyncMock(
                return_value={
                    "access_token": sample_token_response.access_token,
                    "token_type": sample_token_response.token_type,
                    "refresh_token": sample_token_response.refresh_token,
                    "expires_in": sample_token_response.expires_in,
                }
            )

            # 테스트 실행
            result = await oauth_service.get_access_token("test_auth_code")

            # 검증
            assert isinstance(result, GoogleOAuthResponse)
            assert result.access_token == sample_token_response.access_token
            assert result.refresh_token == sample_token_response.refresh_token
            assert result.expires_in == sample_token_response.expires_in

            # HTTP 클라이언트 호출 검증
            mock_http_client.post_json.assert_called_once()
            call_args = mock_http_client.post_json.call_args
            assert call_args[0][0] == "https://oauth2.googleapis.com/token"
            assert call_args[0][1]["code"] == "test_auth_code"
            assert call_args[0][1]["grant_type"] == "authorization_code"

    @pytest.mark.asyncio
    async def test_get_access_token_http_error(self, oauth_service):
        """액세스 토큰 요청 HTTP 오류 테스트"""
        # http_client.post_json Mock 설정 (예외 발생)
        with patch("app.services.oauth.http_client") as mock_http_client:
            mock_http_client.post_json = AsyncMock(
                side_effect=HTTPException(status_code=400, detail="Invalid code")
            )

            # 테스트 실행 및 예외 검증
            with pytest.raises(HTTPException) as exc_info:
                await oauth_service.get_access_token("invalid_code")

            # OAuthErrors.token_request_failed 예외 검증
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, oauth_service, sample_user_info):
        """사용자 정보 요청 성공 테스트"""
        # http_client.get_json Mock 설정
        with patch("app.services.oauth.http_client") as mock_http_client:
            mock_http_client.get_json = AsyncMock(
                return_value={
                    "sub": sample_user_info.id,
                    "email": sample_user_info.email,
                    "name": sample_user_info.name,
                    "picture": sample_user_info.picture,
                }
            )

            # 테스트 실행
            result = await oauth_service.get_user_info("test_access_token")

            # 검증
            assert isinstance(result, OAuthUserInfo)
            assert result.id == sample_user_info.id
            assert result.email == sample_user_info.email
            assert result.name == sample_user_info.name
            assert result.picture == sample_user_info.picture

            # HTTP 클라이언트 호출 검증
            mock_http_client.get_json.assert_called_once_with(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": "Bearer test_access_token"},
            )

    @pytest.mark.asyncio
    async def test_get_user_info_http_error(self, oauth_service):
        """사용자 정보 요청 HTTP 오류 테스트"""
        # http_client.get_json Mock 설정 (예외 발생)
        with patch("app.services.oauth.http_client") as mock_http_client:
            mock_http_client.get_json = AsyncMock(
                side_effect=HTTPException(status_code=401, detail="Invalid token")
            )

            # 테스트 실행 및 예외 검증
            with pytest.raises(HTTPException) as exc_info:
                await oauth_service.get_user_info("invalid_token")

            # OAuthErrors.userinfo_request_failed 예외 검증
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_user_info_id_fallback(self, oauth_service):
        """사용자 정보 ID 폴백 로직 테스트"""
        # http_client.get_json Mock 설정 (sub 없이 id만 있는 경우)
        with patch("app.services.oauth.http_client") as mock_http_client:
            mock_http_client.get_json = AsyncMock(
                return_value={
                    "id": "fallback_user_123",  # sub 대신 id 사용
                    "email": "fallback@example.com",
                    "name": "폴백 사용자",
                }
            )

            # 테스트 실행
            result = await oauth_service.get_user_info("test_access_token")

            # 검증 - id 필드가 사용되었는지 확인
            assert result.id == "fallback_user_123"
            assert result.email == "fallback@example.com"

    @pytest.mark.asyncio
    async def test_process_oauth_callback_new_user(
        self, oauth_service, mock_db, sample_token_response, sample_user_info
    ):
        """새로운 사용자 OAuth 콜백 처리 테스트"""
        # get_access_token Mock 설정
        with patch.object(
            oauth_service, "get_access_token", return_value=sample_token_response
        ):
            # get_user_info Mock 설정
            with patch.object(
                oauth_service, "get_user_info", return_value=sample_user_info
            ):
                # 기존 사용자 없음 Mock 설정
                mock_user_result = Mock()
                mock_user_result.scalar_one_or_none.return_value = None

                # OAuth 토큰 없음 Mock 설정
                mock_token_result = Mock()
                mock_token_result.scalar_one_or_none.return_value = None

                mock_db.execute.side_effect = [mock_user_result, mock_token_result]
                mock_db.add = Mock()
                mock_db.commit = Mock()
                mock_db.refresh = Mock()

                # 테스트 실행
                user, oauth_token = await oauth_service.process_oauth_callback(
                    "test_code", mock_db
                )

                # 검증 - 새 사용자와 토큰이 생성되었는지 확인
                assert mock_db.add.call_count == 2  # user + oauth_token
                assert mock_db.commit.call_count == 2  # user + oauth_token 커밋
                assert mock_db.refresh.call_count == 2  # user + oauth_token 새로고침

                # 생성된 사용자 검증
                user_call_args = mock_db.add.call_args_list[0][0][0]
                assert isinstance(user_call_args, User)
                assert user_call_args.email == sample_user_info.email
                assert user_call_args.nickname == sample_user_info.name
                assert user_call_args.provider == OAuthProvider.GOOGLE.value
                assert user_call_args.provider_id == sample_user_info.id

    @pytest.mark.asyncio
    async def test_process_oauth_callback_existing_user(
        self,
        oauth_service,
        mock_db,
        sample_token_response,
        sample_user_info,
        sample_user,
    ):
        """기존 사용자 OAuth 콜백 처리 테스트"""
        # get_access_token Mock 설정
        with patch.object(
            oauth_service, "get_access_token", return_value=sample_token_response
        ):
            # get_user_info Mock 설정
            with patch.object(
                oauth_service, "get_user_info", return_value=sample_user_info
            ):
                # 기존 사용자 있음 Mock 설정
                mock_user_result = Mock()
                mock_user_result.scalar_one_or_none.return_value = sample_user

                # 기존 OAuth 토큰 없음 Mock 설정
                mock_token_result = Mock()
                mock_token_result.scalar_one_or_none.return_value = None

                mock_db.execute.side_effect = [mock_user_result, mock_token_result]
                mock_db.add = Mock()
                mock_db.commit = Mock()
                mock_db.refresh = Mock()

                # 테스트 실행
                user, oauth_token = await oauth_service.process_oauth_callback(
                    "test_code", mock_db
                )

                # 검증 - 새 토큰만 생성되고 사용자는 기존 것 사용
                assert mock_db.add.call_count == 1  # oauth_token만
                assert mock_db.commit.call_count == 1  # oauth_token만
                assert mock_db.refresh.call_count == 1  # oauth_token만

    @pytest.mark.asyncio
    async def test_process_oauth_callback_update_existing_token(
        self,
        oauth_service,
        mock_db,
        sample_token_response,
        sample_user_info,
        sample_user,
        sample_oauth_token,
    ):
        """기존 토큰 업데이트 OAuth 콜백 처리 테스트"""
        # 새로운 토큰 응답 생성 (다른 값으로)
        new_token_response = GoogleOAuthResponse(
            access_token="new_test_access_token",
            token_type="Bearer",
            refresh_token="new_test_refresh_token",
            expires_in=3600,
        )

        # get_access_token Mock 설정
        with patch.object(
            oauth_service, "get_access_token", return_value=new_token_response
        ):
            # get_user_info Mock 설정
            with patch.object(
                oauth_service, "get_user_info", return_value=sample_user_info
            ):
                # 기존 사용자 있음 Mock 설정
                mock_user_result = Mock()
                mock_user_result.scalar_one_or_none.return_value = sample_user

                # 기존 OAuth 토큰 있음 Mock 설정
                mock_token_result = Mock()
                mock_token_result.scalar_one_or_none.return_value = sample_oauth_token

                mock_db.execute.side_effect = [mock_user_result, mock_token_result]
                mock_db.add = Mock()
                mock_db.commit = Mock()
                mock_db.refresh = Mock()

                # 원본 토큰 값 저장
                original_access_token = sample_oauth_token.access_token

                # 테스트 실행
                user, oauth_token = await oauth_service.process_oauth_callback(
                    "test_code", mock_db
                )

                # 검증 - 기존 토큰이 업데이트되고 새로 추가하지 않음
                assert mock_db.add.call_count == 0  # 새로 추가하지 않음
                assert mock_db.commit.call_count == 1
                assert mock_db.refresh.call_count == 1

                # 토큰 업데이트 검증
                assert (
                    sample_oauth_token.access_token == new_token_response.access_token
                )
                assert (
                    sample_oauth_token.refresh_token == new_token_response.refresh_token
                )
                assert sample_oauth_token.access_token != original_access_token

    @pytest.mark.asyncio
    async def test_process_oauth_callback_deleted_user_within_30_days(
        self,
        oauth_service,
        mock_db,
        sample_token_response,
        sample_user_info,
        sample_user,
    ):
        """30일 이내 삭제된 사용자 복구 불가 테스트"""
        # 사용자를 15일 전에 삭제된 상태로 설정
        sample_user.deleted_at = datetime.now(UTC) - timedelta(days=15)

        # get_access_token Mock 설정
        with patch.object(
            oauth_service, "get_access_token", return_value=sample_token_response
        ):
            # get_user_info Mock 설정
            with patch.object(
                oauth_service, "get_user_info", return_value=sample_user_info
            ):
                # 삭제된 사용자 반환 Mock 설정
                mock_user_result = Mock()
                mock_user_result.scalar_one_or_none.return_value = sample_user
                mock_db.execute.return_value = mock_user_result

                # 테스트 실행 및 예외 검증
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_service.process_oauth_callback("test_code", mock_db)

                # 예외 내용 검증
                assert exc_info.value.status_code == 403
                error_detail = exc_info.value.detail
                assert error_detail["error"] == "ACCOUNT_DELETED"
                assert error_detail["restore_available"] is True
                assert error_detail["days_remaining"] == 15

    @pytest.mark.asyncio
    async def test_process_oauth_callback_deleted_user_over_30_days(
        self,
        oauth_service,
        mock_db,
        sample_token_response,
        sample_user_info,
        sample_user,
    ):
        """30일 초과 삭제된 사용자 영구 삭제 테스트"""
        # 사용자를 35일 전에 삭제된 상태로 설정
        sample_user.deleted_at = datetime.now(UTC) - timedelta(days=35)

        # get_access_token Mock 설정
        with patch.object(
            oauth_service, "get_access_token", return_value=sample_token_response
        ):
            # get_user_info Mock 설정
            with patch.object(
                oauth_service, "get_user_info", return_value=sample_user_info
            ):
                # 삭제된 사용자 반환 Mock 설정
                mock_user_result = Mock()
                mock_user_result.scalar_one_or_none.return_value = sample_user
                mock_db.execute.return_value = mock_user_result

                # 테스트 실행 및 예외 검증
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_service.process_oauth_callback("test_code", mock_db)

                # 예외 내용 검증
                assert exc_info.value.status_code == 403
                error_detail = exc_info.value.detail
                assert error_detail["error"] == "ACCOUNT_PERMANENTLY_DELETED"
                assert error_detail["restore_available"] is False

    def test_oauth_service_initialization(self, oauth_service, mock_settings):
        """OAuth 서비스 초기화 테스트"""
        # 설정 값들이 올바르게 설정되었는지 확인
        assert oauth_service.client_id == "test_client_id"
        assert oauth_service.client_secret == "test_client_secret"
        assert (
            oauth_service.redirect_uri == "http://localhost:8000/auth/google/callback"
        )
        assert oauth_service.token_url == "https://oauth2.googleapis.com/token"
        assert (
            oauth_service.userinfo_url
            == "https://www.googleapis.com/oauth2/v2/userinfo"
        )

    @pytest.mark.asyncio
    async def test_get_user_info_email_fallback(self, oauth_service):
        """사용자 정보 이메일 폴백 로직 테스트"""
        # http_client.get_json Mock 설정 (sub와 id 없이 email만 있는 경우)
        with patch("app.services.oauth.http_client") as mock_http_client:
            mock_http_client.get_json = AsyncMock(
                return_value={
                    "email": "email_fallback@example.com",
                    "name": "이메일 폴백 사용자",
                }
            )

            # 테스트 실행
            result = await oauth_service.get_user_info("test_access_token")

            # 검증 - 이메일이 ID로 사용되었는지 확인
            assert result.id == "email_fallback@example.com"
            assert result.email == "email_fallback@example.com"


class TestGoogleOAuthServiceEdgeCases:
    """GoogleOAuthService 엣지 케이스 테스트"""

    @pytest.fixture
    def oauth_service(self):
        """GoogleOAuthService 인스턴스 (설정 없이)"""
        with patch("app.services.oauth.settings") as mock_settings:
            mock_settings.google_client_id = ""
            mock_settings.google_client_secret = ""
            mock_settings.google_redirect_uri = ""
            mock_settings.google_token_uri = ""
            return GoogleOAuthService()

    @pytest.fixture
    def mock_db(self):
        """Mock 데이터베이스 세션"""
        return Mock(spec=Session)

    @pytest.fixture
    def sample_token_response(self):
        """테스트용 토큰 응답"""
        return GoogleOAuthResponse(
            access_token="test_access_token",
            token_type="Bearer",
            refresh_token="test_refresh_token",
            expires_in=3600,
        )

    @pytest.fixture
    def sample_user_info(self):
        """테스트용 사용자 정보"""
        return OAuthUserInfo(
            id="google_user_123",
            email="test@example.com",
            name="테스트 사용자",
            picture="https://example.com/profile.jpg",
        )

    @pytest.mark.asyncio
    async def test_get_user_info_missing_required_fields(self, oauth_service):
        """사용자 정보 필수 필드 누락 테스트"""
        # http_client.get_json Mock 설정 (필수 필드 누락)
        with patch("app.services.oauth.http_client") as mock_http_client:
            mock_http_client.get_json = AsyncMock(
                return_value={
                    "name": "이름만 있는 사용자",
                    # email, sub, id 모두 없음
                }
            )

            # 테스트 실행 - 이메일이 없으면 KeyError 발생해야 함
            with pytest.raises(KeyError):
                await oauth_service.get_user_info("test_access_token")

    @pytest.mark.asyncio
    async def test_oauth_service_empty_configuration(self, oauth_service):
        """빈 설정으로 초기화 테스트"""
        # 빈 설정 값들 확인
        assert oauth_service.client_id == ""
        assert oauth_service.client_secret == ""
        assert oauth_service.redirect_uri == ""
        assert oauth_service.token_url == ""

    @pytest.mark.asyncio
    async def test_process_oauth_callback_timezone_handling(
        self, mock_db, sample_token_response, sample_user_info
    ):
        """타임존 처리 테스트"""
        # 설정 Mock
        with patch("app.services.oauth.settings") as mock_settings:
            mock_settings.google_client_id = "test"
            mock_settings.google_client_secret = "test"
            mock_settings.google_redirect_uri = "test"
            mock_settings.google_token_uri = "test"

            oauth_service = GoogleOAuthService()

            # 타임존이 있는 deleted_at을 가진 사용자
            deleted_user = User(
                id=uuid.uuid4(),
                email=sample_user_info.email,
                nickname=sample_user_info.name,
                deleted_at=datetime.now(UTC) - timedelta(days=10),  # UTC 타임존
            )

            # get_access_token Mock 설정
            with patch.object(
                oauth_service, "get_access_token", return_value=sample_token_response
            ):
                # get_user_info Mock 설정
                with patch.object(
                    oauth_service, "get_user_info", return_value=sample_user_info
                ):
                    # 삭제된 사용자 반환 Mock 설정
                    mock_user_result = Mock()
                    mock_user_result.scalar_one_or_none.return_value = deleted_user
                    mock_db.execute.return_value = mock_user_result

                    # 테스트 실행 및 예외 검증
                    with pytest.raises(HTTPException) as exc_info:
                        await oauth_service.process_oauth_callback("test_code", mock_db)

                    # 타임존 처리가 올바르게 되었는지 확인
                    assert exc_info.value.status_code == 403
                    assert "ACCOUNT_DELETED" in str(exc_info.value.detail)
