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
        
        # 사용자 조회
        stmt = select(User).where(User.id == user_id)
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
