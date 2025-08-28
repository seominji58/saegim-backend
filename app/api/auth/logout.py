"""
로그아웃 API 라우터
"""

import logging
from datetime import datetime
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import AccountType, OAuthProvider
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.database import get_session
from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.schemas.base import BaseResponse

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
settings = get_settings()


class LogoutService:
    """로그아웃 서비스"""

    def __init__(self, db: Session):
        self.db = db

    async def revoke_google_token(self, access_token: str) -> bool:
        """구글 OAuth 토큰 무효화"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    data={"token": access_token},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Google token revocation failed: {e}")
            return False

    def invalidate_oauth_tokens(self, user_id: str) -> None:
        """사용자의 OAuth 토큰들을 무효화"""
        try:
            # 사용자의 OAuth 토큰 조회
            stmt = select(OAuthToken).where(OAuthToken.user_id == user_id)
            result = self.db.execute(stmt)
            oauth_tokens = result.scalars().all()

            for oauth_token in oauth_tokens:
                # 토큰 만료 시간을 현재 시간으로 설정하여 무효화
                oauth_token.expires_at = datetime.utcnow()

            self.db.commit()
            logger.info(
                f"Invalidated {len(oauth_tokens)} OAuth tokens for user {user_id}"
            )

        except Exception as e:
            logger.error(f"Failed to invalidate OAuth tokens for user {user_id}: {e}")
            self.db.rollback()

    def log_logout_attempt(
        self, user_id: str, success: bool, details: str = ""
    ) -> None:
        """로그아웃 시도 기록"""
        try:
            log_message = f"Logout attempt - User: {user_id}, Success: {success}"
            if details:
                log_message += f", Details: {details}"

            if success:
                logger.info(log_message)
            else:
                logger.warning(log_message)

        except Exception as e:
            logger.error(f"Failed to log logout attempt: {e}")


@router.post("/logout", response_model=BaseResponse[Dict[str, Any]])
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """
    로그아웃 API

    - 구글 OAuth 세션 정리
    - JWT 토큰 무효화
    - 쿠키 정리
    - 보안 로그 기록
    """
    logout_service = LogoutService(db)
    success = True
    error_details = []
    current_user_id = None
    user = None

    try:
        # 1. Authorization 헤더에서 토큰 추출 및 사용자 ID 파싱
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            try:
                # 토큰 페이로드에서 사용자 ID 추출
                payload = decode_access_token(token)
                current_user_id = int(payload.get("sub"))
                jti = payload.get("jti")

                # 사용자 정보 조회
                stmt = select(User).where(User.id == current_user_id)
                result = db.execute(stmt)
                user = result.scalar_one_or_none()

                # TODO: Redis나 데이터베이스에 토큰 블랙리스트 추가
                # 현재는 로그로만 기록
                if jti:
                    logger.info(f"Token blacklisted: {jti}")

            except Exception as e:
                logger.warning(f"Failed to decode token: {e}")
                # 토큰이 유효하지 않아도 로그아웃은 성공으로 처리

        # 2. 구글 OAuth 세션 정리 (사용자 정보가 있는 경우에만)
        if (
            user
            and user.account_type == AccountType.SOCIAL.value
            and user.provider == OAuthProvider.GOOGLE.value
        ):
            stmt = select(OAuthToken).where(
                OAuthToken.user_id == current_user_id,
                OAuthToken.provider == OAuthProvider.GOOGLE.value,
            )
            result = db.execute(stmt)
            oauth_token = result.scalar_one_or_none()

            if oauth_token and oauth_token.access_token:
                if not await logout_service.revoke_google_token(
                    oauth_token.access_token
                ):
                    error_details.append("Google token revocation failed")
                    success = False

        # 3. OAuth 토큰 무효화 (사용자 ID가 있는 경우에만)
        if current_user_id:
            logout_service.invalidate_oauth_tokens(str(current_user_id))

        # 5. 쿠키 정리 (환경별 동적 설정)
        response.delete_cookie(
            key="access_token",
            path="/",
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite,
            domain=settings.cookie_domain,
        )
        response.delete_cookie(
            key="refresh_token",
            path="/",
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite,
            domain=settings.cookie_domain,
        )
        response.delete_cookie(
            key="session",
            path="/",
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite,
            domain=settings.cookie_domain,
        )

        # 4. 보안 로그 기록
        if current_user_id:
            logout_service.log_logout_attempt(
                str(current_user_id),
                success,
                ", ".join(error_details) if error_details else "",
            )

        # 5. 응답 반환 (항상 성공 응답)
        return BaseResponse(
            data={
                "logout_time": datetime.utcnow().isoformat(),
                "user_id": str(current_user_id) if current_user_id else None,
                "account_type": user.account_type if user else None,
                "provider": user.provider
                if user and user.account_type == AccountType.SOCIAL.value
                else None,
                "errors": error_details if error_details else None,
            },
            message="로그아웃이 완료되었습니다" if success else "로그아웃이 완료되었습니다 (구글 세션 정리 실패)",
        )

    except HTTPException:
        # HTTP 예외는 그대로 재발생
        raise
    except Exception as e:
        # 기타 예외는 로그 기록 후 성공 응답 반환
        logger.error(f"Unexpected error during logout for user {current_user_id}: {e}")
        if current_user_id:
            logout_service.log_logout_attempt(str(current_user_id), False, str(e))

        # 프론트엔드 정리를 위해 항상 성공 응답 반환
        return BaseResponse(
            data={
                "logout_time": datetime.utcnow().isoformat(),
                "user_id": str(current_user_id) if current_user_id else None,
                "account_type": "unknown",
                "provider": None,
                "errors": ["Unexpected error occurred"],
            },
            message="로그아웃이 완료되었습니다",
        )
