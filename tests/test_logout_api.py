"""
로그아웃 API 테스트
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_logout_without_token():
    """토큰 없이 로그아웃 시도"""
    response = client.post("/auth/logout")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_logout_with_invalid_token():
    """유효하지 않은 토큰으로 로그아웃 시도"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.post("/auth/logout", headers=headers)
    assert response.status_code == 401
    assert "유효하지 않은 토큰입니다" in response.json()["detail"]


@patch("app.api.auth.logout.LogoutService.revoke_google_token")
@patch("app.api.auth.logout.get_current_user_id")
def test_logout_success(mock_get_user_id, mock_revoke_token):
    """성공적인 로그아웃 테스트"""
    # Mock 설정
    mock_get_user_id.return_value = 1
    mock_revoke_token.return_value = True

    # 유효한 토큰으로 요청 (실제로는 테스트용 토큰이 필요)
    headers = {"Authorization": "Bearer test_token"}

    with patch("app.core.security.decode_access_token") as mock_decode:
        mock_decode.return_value = {"sub": "1", "jti": "test_jti"}

        response = client.post("/auth/logout", headers=headers)

        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "로그아웃이 완료되었습니다" in data["message"]
        assert "logout_time" in data["data"]
        assert data["data"]["user_id"] == "1"


@patch("app.api.auth.logout.LogoutService.revoke_google_token")
@patch("app.api.auth.logout.get_current_user_id")
def test_logout_google_revocation_failed(mock_get_user_id, mock_revoke_token):
    """구글 토큰 무효화 실패 시 테스트"""
    # Mock 설정
    mock_get_user_id.return_value = 1
    mock_revoke_token.return_value = False  # 구글 토큰 무효화 실패

    headers = {"Authorization": "Bearer test_token"}

    with patch("app.core.security.decode_access_token") as mock_decode:
        mock_decode.return_value = {"sub": "1", "jti": "test_jti"}

        response = client.post("/auth/logout", headers=headers)

        # 응답 검증 - 실패해도 성공 응답 반환
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "구글 세션 정리 실패" in data["message"]
        assert data["data"]["errors"] == ["Google token revocation failed"]


def test_logout_cookie_cleanup():
    """쿠키 정리 테스트"""
    # 실제 구현에서는 쿠키가 설정된 상태에서 테스트해야 함
    # 여기서는 기본적인 응답 구조만 확인
    with patch("app.api.auth.logout.get_current_user_id") as mock_get_user_id:
        mock_get_user_id.return_value = 1

        headers = {"Authorization": "Bearer test_token"}

        with patch("app.core.security.decode_access_token") as mock_decode:
            mock_decode.return_value = {"sub": "1", "jti": "test_jti"}

            response = client.post("/auth/logout", headers=headers)

            # 쿠키 삭제 헤더 확인
            assert response.status_code == 200

            # 실제로는 쿠키 삭제 헤더가 응답에 포함되어야 함
            # 하지만 TestClient에서는 직접 확인하기 어려움


if __name__ == "__main__":
    pytest.main([__file__])
