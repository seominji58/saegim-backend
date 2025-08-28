"""
레거시 리다이렉트 API 라우터
기존 경로에서 새로운 경로로의 리다이렉트 처리
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["legacy"])


@router.get("/google/login")
async def redirect_google_login():
    """기존 구글 로그인 경로 → 새 경로 리다이렉트"""
    return RedirectResponse(url="/api/auth/google/login", status_code=307)


@router.get("/google/callback")
async def redirect_google_callback():
    """기존 구글 콜백 경로 → 새 경로 리다이렉트"""
    return RedirectResponse(url="/api/auth/google/callback", status_code=307)


@router.get("/google/token/{token_id}")
async def redirect_google_token(token_id: str):
    """기존 구글 토큰 경로 → 새 경로 리다이렉트"""
    return RedirectResponse(url=f"/api/auth/google/token/{token_id}", status_code=307)


@router.post("/logout")
async def redirect_logout():
    """기존 로그아웃 경로 → 새 경로 리다이렉트"""
    return RedirectResponse(url="/api/auth/logout", status_code=307)
