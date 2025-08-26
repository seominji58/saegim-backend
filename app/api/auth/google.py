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
from app.core.security import create_access_token, create_refresh_token, get_current_user_id_from_cookie
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
    return RedirectResponse(
        f"{settings.google_auth_uri}?{query_string}"
    )


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
        response = RedirectResponse(url=f"{settings.frontend_callback_url}?success=true")
        
        # 쿠키에 토큰 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # 개발환경에서는 False
            samesite="lax",
            max_age=3600,  # 1시간
            path="/",  # 모든 경로에서 접근 가능
            domain="localhost"
        )
        
        response.set_cookie(
            key="refresh_token", 
            value=refresh_token,
            httponly=True,
            secure=False,  # 개발환경에서는 False
            samesite="lax",
            max_age=604800,  # 7일
            path="/",  # 모든 경로에서 접근 가능
            domain="localhost"
        )
        
        print(f"User logged in: {user.email}")
        print(f"Redirecting to: {settings.frontend_callback_url}?success=true")
        
        return response
        
    except HTTPException as http_ex:
        # HTTPException 처리 (탈퇴된 계정 등)
        error_detail = http_ex.detail
        if isinstance(error_detail, dict):
            # 탈퇴된 계정 에러 처리
            if error_detail.get("error") == "ACCOUNT_DELETED":
                error_url = f"{settings.frontend_callback_url}?error=account_deleted&message={error_detail.get('message', '탈퇴된 계정입니다.')}&restore_available=true&days_remaining={error_detail.get('days_remaining', 0)}"
            elif error_detail.get("error") == "ACCOUNT_PERMANENTLY_DELETED":
                error_url = f"{settings.frontend_callback_url}?error=account_permanently_deleted&message={error_detail.get('message', '탈퇴 후 30일이 경과되어 복구할 수 없습니다.')}&restore_available=false"
            else:
                error_url = f"{settings.frontend_callback_url}?error=login_failed&message={error_detail.get('message', str(http_ex))}"
        else:
            error_url = f"{settings.frontend_callback_url}?error=login_failed&message={str(error_detail)}"
        
        print(f"HTTPException - Error URL: {error_url}")
        print(f"HTTPException - Detail: {error_detail}")
        return RedirectResponse(url=error_url)
        
    except Exception as e:
        # 기타 에러 발생 시 프론트엔드 콜백 페이지로 리다이렉트 (에러 파라미터 포함)
        error_url = f"{settings.frontend_callback_url}?error=login_failed&message={str(e)}"
        print(f"Frontend callback URL (error): {settings.frontend_callback_url}")
        print(f"Error URL: {error_url}")
        print(f"OAuth Error: {e}")
        return RedirectResponse(url=error_url)
