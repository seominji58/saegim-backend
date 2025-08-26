"""
의존성 주입 (Dependency Injection)
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.db.database import get_session
from app.models.user import User
from app.core.config import get_settings

settings = get_settings()
security = HTTPBearer()

def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성"""
    return get_session()

async def get_current_user_id(
    request: Request,
    db: Session = Depends(get_session)
) -> str:
    """
    쿠키 또는 Bearer 토큰을 통해 현재 로그인한 사용자 ID 조회
    (소셜 로그인: 쿠키, 이메일 로그인: Bearer 토큰)

    Args:
        request: FastAPI Request 객체
        db: 데이터베이스 세션

    Returns:
        현재 로그인한 사용자 ID

    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from app.core.security import get_current_user_id_from_cookie, decode_access_token
    
    try:
        user_id = None
        
        # 디버깅: 쿠키 확인
        cookies = request.cookies
        logger.info(f"쿠키 확인: {list(cookies.keys())}")
        
        # 1. 먼저 쿠키에서 토큰 확인 (소셜 로그인)
        try:
            user_id = get_current_user_id_from_cookie(request)
            logger.info(f"쿠키에서 user_id 추출: {user_id}")
        except HTTPException as e:
            logger.warning(f"쿠키에서 user_id 추출 실패: {e.detail}")
            pass
        
        # 2. 쿠키에 토큰이 없으면 Authorization 헤더 확인 (이메일 로그인)
        if user_id is None:
            auth_header = request.headers.get("Authorization")
            logger.info(f"Authorization 헤더: {auth_header}")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_access_token(token)
                user_id = payload.get("sub")
                logger.info(f"Bearer 토큰에서 user_id 추출: {user_id}")
        
        # 3. 토큰이 없으면 인증 실패
        if user_id is None:
            logger.error("인증 토큰을 찾을 수 없음")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증 토큰이 필요합니다."
            )
        
        # 사용자 존재 여부 확인 (Soft Delete 제외)
        stmt = select(User).where(
            User.id == user_id,
            User.deleted_at == None
        )
        result = db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            logger.error(f"사용자를 찾을 수 없음: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다."
            )

        if not user.is_active:
            logger.error(f"비활성화된 계정: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다."
            )

        logger.info(f"인증 성공: {user_id}")
        return user_id
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"인증 중 예외 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다."
        )

async def get_current_user(
    request: Request,
    db: Session = Depends(get_session)
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
    from app.core.security import get_current_user_id_from_cookie, decode_access_token
    
    try:
        user_id = None
        
        # 1. 먼저 쿠키에서 토큰 확인 (소셜 로그인)
        try:
            user_id = get_current_user_id_from_cookie(request)
        except HTTPException:
            pass
        
        # 2. 쿠키에 토큰이 없으면 Authorization 헤더 확인 (이메일 로그인)
        if user_id is None:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_access_token(token)
                user_id = payload.get("sub")
        
        # 3. 토큰이 없으면 인증 실패
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증 토큰이 필요합니다."
            )
        
        # 사용자 조회 (Soft Delete 제외)
        stmt = select(User).where(
            User.id == user_id,
            User.deleted_at == None
        )
        result = db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다."
            )

        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다."
        )
