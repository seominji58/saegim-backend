"""
구글 OAuth 라우트
"""

from typing import Dict, Any
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session
import uuid
import time
from uuid import UUID

from app.core.config import get_settings
from app.db.database import get_session
from app.services.oauth import GoogleOAuthService
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user_id_from_cookie,
)
from app.models.user import User
from sqlmodel import select
import logging
from fastapi import status

# 로거 설정

router = APIRouter(prefix="/google", tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("/login")
async def google_login() -> RedirectResponse:
    """구글 로그인 페이지로 리다이렉트"""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
    }

    # URL 파라미터 생성 (URL 인코딩 적용)
    query_string = urlencode(params)

    # 구글 인증 페이지로 리다이렉트
    return RedirectResponse(f"{settings.google_auth_uri}?{query_string}")


@router.get("/callback")
async def google_callback(
    code: str,
    db: Session = Depends(get_session),
) -> RedirectResponse:
    # 디버깅: 설정값 확인
    print(f"Debug - Frontend callback URL: {settings.frontend_callback_url}")
    print(f"Debug - Frontend URL: {settings.frontend_url}")
    print(f"Debug - Google client ID: {settings.google_client_id[:8]}...")
    """구글 OAuth 콜백 처리

    Args:
        code: 인증 코드
        db: 데이터베이스 세션

    Returns:
        RedirectResponse: 프론트엔드 콜백 페이지로 리다이렉트
    """
    try:
        oauth_service = GoogleOAuthService()
        user, _ = await oauth_service.process_oauth_callback(code, db)

        # JWT 토큰 생성
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        # 프론트엔드로 리다이렉트 (쿠키에 토큰 설정)
        response = RedirectResponse(
            url=f"{settings.frontend_callback_url}?success=true"
        )

        # 쿠키에 토큰 설정 (환경별 동적 설정)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.jwt_access_token_expire_minutes * 60,  # 분을 초로 변환
            path="/",
            domain=settings.cookie_domain,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.jwt_refresh_token_expire_days
            * 24
            * 60
            * 60,  # 일을 초로 변환
            path="/",
            domain=settings.cookie_domain,
        )

        print(f"User logged in: {user.email}")
        print(f"Redirecting to: {settings.frontend_callback_url}?success=true")

        return response

    except Exception as e:
        # 에러 발생 시 프론트엔드 콜백 페이지로 리다이렉트 (에러 파라미터 포함)
        error_url = (
            f"{settings.frontend_callback_url}?error=login_failed&message={str(e)}"
        )
        print(f"Frontend callback URL (error): {settings.frontend_callback_url}")
        print(f"Error URL: {error_url}")
        print(f"OAuth Error: {e}")
        return RedirectResponse(url=error_url)
