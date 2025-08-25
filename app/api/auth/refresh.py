"""
JWT 토큰 갱신 API 라우터
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.security import decode_refresh_token, create_access_token, create_refresh_token
from app.db.database import get_session
from app.models.user import User
from app.schemas.base import BaseResponse

router = APIRouter(tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/refresh", response_model=BaseResponse[Dict[str, Any]])
async def refresh_token(
    request: Request,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """
    JWT 토큰 갱신 API
    
    - Refresh Token을 사용하여 새로운 Access Token 발급
    - Access Token이 만료되었을 때 자동으로 호출
    """
    try:
        # 1. 쿠키에서 Refresh Token 추출
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token이 필요합니다."
            )
        
        # 2. Refresh Token 검증
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = int(payload.get("sub"))
            token_type = payload.get("type")
            
            if token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="유효하지 않은 토큰 타입입니다."
                )
                
        except Exception as e:
            logger.warning(f"Refresh token 검증 실패: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 refresh token입니다."
            )
        
        # 3. 사용자 정보 조회
        stmt = select(User).where(User.id == user_id)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다."
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다."
            )
        
        # 4. 새로운 토큰 발급
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        logger.info(f"토큰 갱신 성공: {user.email}")
        
        # 5. 쿠키에 새로운 토큰 설정
        from fastapi.responses import JSONResponse
        response = JSONResponse(
            content={
                "success": True,
                "message": "토큰이 성공적으로 갱신되었습니다.",
                "data": {
                    "user_id": str(user.id),
                    "email": user.email,
                    "nickname": user.nickname
                }
            }
        )
        
        # 쿠키에 새로운 토큰 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # 개발환경에서는 False
            samesite="lax",
            max_age=3600,  # 1시간
            path="/",
            domain="localhost"
        )
        
        response.set_cookie(
            key="refresh_token", 
            value=new_refresh_token,
            httponly=True,
            secure=False,  # 개발환경에서는 False
            samesite="lax",
            max_age=604800,  # 7일
            path="/",
            domain="localhost"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 갱신 중 오류 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 갱신 중 오류가 발생했습니다."
        )
