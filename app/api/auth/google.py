"""
구글 OAuth 라우트
"""
from typing import Dict
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.core.config import get_settings
from app.db.database import get_session
from app.services.oauth import GoogleOAuthService
from app.core.security import create_access_token, create_refresh_token

router = APIRouter(prefix="/auth/google", tags=["auth"])
settings = get_settings()


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
) -> Dict[str, str]:
    """구글 OAuth 콜백 처리

    Args:
        code: 인증 코드
        db: 데이터베이스 세션

    Returns:
        Dict[str, str]: JWT 토큰
    """
    oauth_service = GoogleOAuthService()
    user, _ = await oauth_service.process_oauth_callback(code, db)

    # JWT 토큰 생성
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
