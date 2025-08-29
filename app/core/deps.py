"""
의존성 주입 (Dependency Injection)
"""

import logging
from typing import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token, get_current_user_id_from_cookie
from app.constants import AuthConstants, ResponseMessages
from app.db.database import get_session
from app.models.user import User

logger = logging.getLogger(__name__)

settings = get_settings()
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


async def get_current_user_id(request: Request) -> str:
    """
    쿠키 또는 Bearer 토큰을 통해 현재 로그인한 사용자 ID 조회
    (소셜 로그인: 쿠키, 이메일 로그인: Bearer 토큰)

    Args:
        request: FastAPI Request 객체

    Returns:
        현재 로그인한 사용자 ID

    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """

    try:
        # 디버깅: 쿠키 확인
        cookies = request.cookies
        logger.info(f"쿠키 확인: {list(cookies.keys())}")

        user_id = await _extract_user_id(request)

        if user_id is None:
            logger.error("인증 토큰을 찾을 수 없음")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ResponseMessages.TOKEN_REQUIRED,
            )

        return user_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"인증 중 예외 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ResponseMessages.AUTH_FAILED
        )


async def _extract_user_id(request: Request) -> str | None:
    """쿠키 또는 Bearer 토큰에서 사용자 ID 추출"""
    logger.info("사용자 ID 추출 시작")

    try:
        # 1. 쿠키에서 토큰 확인 (소셜 로그인)
        logger.info("쿠키에서 토큰 추출 시도")
        user_id = get_current_user_id_from_cookie(request)
        logger.info(f"쿠키에서 user_id 추출: {user_id}")
        return str(user_id)
    except HTTPException as e:
        logger.info(f"쿠키 인증 실패: {e.detail}")
    except Exception as e:
        logger.error(f"쿠키 인증 중 예상치 못한 오류: {e}")
        pass

    # 2. Authorization 헤더에서 토큰 확인 (이메일 로그인)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith(AuthConstants.BEARER_PREFIX):
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        logger.info(f"Bearer 토큰에서 user_id 추출: {user_id}")
        return user_id

    return None


async def _validate_user(user_id: str, db: Session) -> User:
    """사용자 존재 여부 및 활성 상태 확인"""
    logger.info(f"사용자 검증 시작: {user_id}")

    try:
        user_uuid = UUID(user_id)
        logger.info(f"UUID 변환 성공: {user_uuid}")
    except ValueError as e:
        logger.error(f"UUID 변환 실패: {user_id}, 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ResponseMessages.INVALID_USER_ID_FORMAT,
        )

    stmt = select(User).where(User.id == user_uuid, User.deleted_at.is_(None))
    result = db.execute(stmt)
    user = result.scalar_one_or_none()

    logger.info(f"데이터베이스 조회 결과: {'사용자 존재' if user else '사용자 없음'}")

    if user is None:
        logger.error(f"사용자를 찾을 수 없음: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ResponseMessages.USER_NOT_FOUND,
        )

    if not user.is_active:
        logger.error(f"비활성화된 계정: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ResponseMessages.ACCOUNT_INACTIVE
        )

    return user


async def get_current_user(
    request: Request, db: Session = Depends(get_session)
) -> User:
    """
    쿠키 또는 Bearer 토큰을 통해 현재 로그인한 사용자 조회
    (소셜 로그인: 쿠키, 이메일 로그인: Bearer 토큰)

    Args:
        request: FastAPI Request 객체
        db: 데이터베이스 세션

    Returns:
        현재 로그인한 사용자

    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    try:
        user_id = await _extract_user_id(request)

        if user_id is None:
            logger.error("인증 토큰을 찾을 수 없음")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ResponseMessages.TOKEN_REQUIRED,
            )

        user = await _validate_user(user_id, db)
        logger.info(f"인증 성공: {user_id}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"인증 중 예외 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ResponseMessages.AUTH_FAILED
        )
