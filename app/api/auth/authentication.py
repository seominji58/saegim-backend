"""
인증 관리 API 라우터
로그인, 로그아웃, 토큰 갱신, 사용자 정보 조회
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from jose.exceptions import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import AccountType, OAuthProvider
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.db.database import get_session
from app.models.oauth_token import OAuthToken
from app.models.user import User
from app.schemas.base import BaseResponse
from app.utils.encryption import password_hasher

# TODO: Implement standardized error handling
# from app.utils.error_handlers import StandardHTTPException, unauthorized_exception

router = APIRouter(tags=["authentication"])

# 인증이 필요한 라우터
authenticated_router = APIRouter(
    tags=["authentication"],
    dependencies=[Depends(get_current_user)],
)

settings = get_settings()
logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user_id: str
    email: str
    nickname: str
    message: str


@router.post("/login", response_model=BaseResponse[LoginResponse])
async def login(
    request: LoginRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[LoginResponse]:
    """이메일 로그인 API"""
    try:
        # 1. 사용자 조회 (Soft Delete 포함)
        stmt = select(User).where(User.email == request.email)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        # 2. Soft Delete된 계정인지 확인
        if user.deleted_at is not None:
            current_time = (
                datetime.now(user.deleted_at.tzinfo)
                if user.deleted_at.tzinfo
                else datetime.now()
            )
            deleted_time = (
                user.deleted_at.replace(tzinfo=None)
                if user.deleted_at.tzinfo
                else user.deleted_at
            )
            current_time_naive = (
                current_time.replace(tzinfo=None)
                if current_time.tzinfo
                else current_time
            )

            # 30일 이내인지 확인
            if deleted_time >= current_time_naive - timedelta(days=30):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "ACCOUNT_DELETED",
                        "message": "탈퇴된 계정입니다. 30일 이내에 복구할 수 있습니다.",
                        "deleted_at": user.deleted_at.isoformat(),
                        "restore_available": True,
                        "days_remaining": 30 - (current_time_naive - deleted_time).days,
                    },
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "ACCOUNT_PERMANENTLY_DELETED",
                        "message": "탈퇴 후 30일이 경과되어 복구할 수 없습니다.",
                        "deleted_at": user.deleted_at.isoformat(),
                        "restore_available": False,
                    },
                )

        # 3. 이메일 회원가입 사용자인지 확인
        if user.account_type != AccountType.EMAIL.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="소셜 로그인으로 가입된 계정입니다.",
            )

        # 4. 비밀번호 검증
        if not password_hasher.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        # 5. 계정 활성화 상태 확인
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다.",
            )

        # 6. JWT 토큰 생성
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        # 7. 응답 생성 (쿠키만 설정, 응답에는 토큰 제외)
        response_data = LoginResponse(
            user_id=str(user.id),
            email=user.email,
            nickname=user.nickname,
            message="로그인이 완료되었습니다.",
        )

        logger.info(f"사용자 로그인: {user.email}")

        # 쿠키 설정을 위한 응답 생성
        response = JSONResponse(
            content={
                "success": True,
                "message": "로그인이 성공적으로 완료되었습니다.",
                "data": response_data.dict(),
            }
        )

        # 쿠키에 토큰 설정 (환경별 동적 설정)
        _set_auth_cookies(response, access_token, refresh_token)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 중 오류가 발생했습니다.",
        )


class LogoutService:
    """로그아웃 서비스"""

    def __init__(self, db: Session):
        self.db = db

    async def revoke_google_token(self, access_token: str) -> bool:
        """구글 OAuth 토큰 무효화"""
        try:
            import httpx

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
                oauth_token.expires_at = datetime.now(timezone.utc)

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
    """로그아웃 API - 구글 OAuth 세션 정리, JWT 토큰 무효화, 쿠키 정리"""
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

                if jti:
                    logger.info(f"Token logout requested: {jti}")

            except Exception as e:
                logger.warning(f"Failed to decode token: {e}")

        # 2. 구글 OAuth 세션 정리
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

        # 3. OAuth 토큰 무효화
        if current_user_id:
            logout_service.invalidate_oauth_tokens(str(current_user_id))

        # 4. 쿠키 정리
        _clear_auth_cookies(response)

        # 5. 보안 로그 기록
        if current_user_id:
            logout_service.log_logout_attempt(
                str(current_user_id),
                success,
                ", ".join(error_details) if error_details else "",
            )

        return BaseResponse(
            data={
                "logout_time": datetime.now(timezone.utc).isoformat(),
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
        raise
    except Exception as e:
        logger.error(f"Unexpected error during logout: {e}")
        if current_user_id:
            logout_service.log_logout_attempt(str(current_user_id), False, str(e))

        return BaseResponse(
            data={
                "logout_time": datetime.now(timezone.utc).isoformat(),
                "user_id": str(current_user_id) if current_user_id else None,
                "account_type": "unknown",
                "provider": None,
                "errors": ["Unexpected error occurred"],
            },
            message="로그아웃이 완료되었습니다",
        )


@router.post("/refresh", response_model=BaseResponse[Dict[str, Any]])
async def refresh_token(
    request: Request,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """JWT 토큰 갱신 API - Refresh Token을 사용하여 새로운 Access Token 발급"""
    try:
        # 1. 쿠키에서 Refresh Token 추출
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token이 필요합니다.",
            )

        # 2. Refresh Token 검증
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = payload.get("sub")
            token_type = payload.get("type")

            if token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="유효하지 않은 토큰 타입입니다.",
                )

        except Exception as e:
            logger.warning(f"Refresh token 검증 실패: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 refresh token입니다.",
            )

        # 3. 사용자 정보 조회
        stmt = select(User).where(User.id == user_id)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다.",
            )

        # 4. 새로운 토큰 발급
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

        logger.info(f"토큰 갱신 성공: {user.email}")

        # 5. 쿠키에 새로운 토큰 설정
        response = JSONResponse(
            content={
                "success": True,
                "message": "토큰이 성공적으로 갱신되었습니다.",
                "data": {
                    "user_id": str(user.id),
                    "email": user.email,
                    "nickname": user.nickname,
                },
            }
        )

        _set_auth_cookies(response, access_token, new_refresh_token)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 갱신 중 오류 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 갱신 중 오류가 발생했습니다.",
        )


@authenticated_router.get("/me", response_model=BaseResponse[Dict[str, Any]])
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """현재 로그인한 사용자 정보 조회 API"""
    try:
        user_data = {
            "user_id": str(current_user.id),
            "email": current_user.email,
            "nickname": current_user.nickname,
            "account_type": current_user.account_type,
            "provider": current_user.provider,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat()
            if current_user.created_at
            else None,
        }

        return BaseResponse(data=user_data, message="현재 사용자 정보를 성공적으로 조회했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 정보 조회 중 오류가 발생했습니다.",
        )


# 헬퍼 함수들
async def _get_user_from_request(request: Request, db: Session) -> User | None:
    """요청에서 사용자 정보 추출 (Bearer token 또는 Cookie)"""
    current_user = None

    # 1. Authorization 헤더에서 Bearer 토큰 확인
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.jwt_algorithm]
            )
            user_id = payload.get("sub")
            if user_id:
                stmt = select(User).where(User.id == user_id)
                result = db.execute(stmt)
                current_user = result.scalar_one_or_none()
        except JWTError:
            pass

    # 2. Bearer 토큰이 없거나 유효하지 않으면 쿠키 확인
    if not current_user:
        access_token = request.cookies.get("access_token")
        if access_token:
            try:
                payload = jwt.decode(
                    access_token,
                    settings.secret_key,
                    algorithms=[settings.jwt_algorithm],
                )
                user_id = payload.get("sub")
                if user_id:
                    stmt = select(User).where(User.id == user_id)
                    result = db.execute(stmt)
                    current_user = result.scalar_one_or_none()
            except JWTError:
                pass

    return current_user


def _set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str):
    """인증 쿠키 설정"""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
        domain=settings.cookie_domain,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        path="/",
        domain=settings.cookie_domain,
    )


def _clear_auth_cookies(response: Response):
    """인증 쿠키 삭제"""
    for key in ["access_token", "refresh_token", "session"]:
        response.delete_cookie(
            key=key,
            path="/",
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite,
            domain=settings.cookie_domain,
        )
