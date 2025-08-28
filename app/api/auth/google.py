"""
구글 OAuth 라우트
"""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token
from app.db.database import get_session
from app.services.oauth import GoogleOAuthService

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
    # 디버깅: 설정값 확인 (운영 환경에서는 로깅으로 대체)
    if settings.is_development:
        print(f"Debug - Frontend callback URL: {settings.frontend_callback_url}")
        print(f"Debug - Frontend URL: {settings.frontend_url}")
        print(f"Debug - Google client ID: {settings.google_client_id[:8]}...")
    else:
        logger.info("Google OAuth callback initiated")
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

        # 쿠키에 토큰 설정 (환경별 보안 강화)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=settings.cookie_httponly,
            secure=settings.is_production,  # 운영 환경에서는 강제 HTTPS
            samesite="strict"
            if settings.is_production
            else settings.cookie_samesite,  # 운영 환경에서는 strict
            max_age=settings.jwt_access_token_expire_minutes * 60,  # 분을 초로 변환
            path="/",
            domain=settings.cookie_domain,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=settings.cookie_httponly,
            secure=settings.is_production,  # 운영 환경에서는 강제 HTTPS
            samesite="strict"
            if settings.is_production
            else settings.cookie_samesite,  # 운영 환경에서는 strict
            max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,  # 일을 초로 변환
            path="/",
            domain=settings.cookie_domain,
        )

        # 로그인 성공 로깅 (개인정보 보호)
        if settings.is_development:
            print(f"User logged in: {user.email}")
            print(f"Redirecting to: {settings.frontend_callback_url}?success=true")
        else:
            logger.info(f"User authentication successful: user_id={user.id}")
            logger.info("Redirecting to frontend callback")

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

        # 에러 로깅 (운영 환경에서는 상세 정보 숨김)
        if settings.is_development:
            print(f"HTTPException - Error URL: {error_url}")
            print(f"HTTPException - Detail: {error_detail}")
        else:
            logger.warning(
                f"Authentication error occurred: status={http_ex.status_code}"
            )
            logger.debug(f"Error detail: {error_detail}")
        return RedirectResponse(url=error_url)

    except Exception as e:
        # 기타 에러 발생 시 프론트엔드 콜백 페이지로 리다이렉트 (에러 파라미터 포함)
        error_url = (
            f"{settings.frontend_callback_url}?error=login_failed&message={str(e)}"
        )
        # 일반 에러 로깅 (운영 환경에서는 민감 정보 제외)
        if settings.is_development:
            print(f"Frontend callback URL (error): {settings.frontend_callback_url}")
            print(f"Error URL: {error_url}")
            print(f"OAuth Error: {e}")
        else:
            logger.error(f"OAuth authentication failed: {type(e).__name__}")
            logger.debug(f"OAuth error detail: {str(e)}")
        return RedirectResponse(url=error_url)
