"""
구글 OAuth 라우트
"""
from typing import Dict
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session
import uuid
import time

from app.core.config import get_settings
from app.db.database import get_session
from app.services.oauth import GoogleOAuthService
from app.core.security import create_access_token, create_refresh_token

# 임시 토큰 저장소 (실제로는 Redis를 사용하는 것이 좋습니다)
temp_tokens = {}

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

        # 임시 토큰 ID 생성
        temp_token_id = str(uuid.uuid4())
        temp_tokens[temp_token_id] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "created_at": time.time()
        }

        # 프론트엔드 콜백 페이지로 리다이렉트 (토큰 ID 포함)
        frontend_callback_url = f"{settings.frontend_callback_url}?token_id={temp_token_id}"
        
        print(f"Frontend callback URL: {settings.frontend_callback_url}")
        print(f"Redirecting to: {frontend_callback_url}")
        print(f"User logged in: {user.email}")
        print(f"Token ID: {temp_token_id}")
        
        return RedirectResponse(url=frontend_callback_url)
        
    except Exception as e:
        # 에러 발생 시 프론트엔드 콜백 페이지로 리다이렉트 (에러 파라미터 포함)
        error_url = f"{settings.frontend_callback_url}?error=login_failed"
        print(f"Frontend callback URL (error): {settings.frontend_callback_url}")
        print(f"Error URL: {error_url}")
        print(f"OAuth Error: {e}")
        return RedirectResponse(url=error_url)


@router.get("/token/{token_id}")
async def get_token(token_id: str) -> Dict[str, str]:
    """임시 토큰 ID로 실제 토큰 반환"""
    if token_id in temp_tokens:
        token_data = temp_tokens.pop(token_id)  # 사용 후 삭제
        
        # 5분 이내에 생성된 토큰만 유효
        if time.time() - token_data["created_at"] < 300:
            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "token_type": "bearer",
            }
    
    raise HTTPException(status_code=400, detail="Invalid or expired token")
