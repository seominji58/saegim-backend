"""
사용자 프로필 API 라우터
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr, validator
import re
import logging

from app.core.config import get_settings
from app.db.database import get_session
from app.models.user import User
from app.schemas.base import BaseResponse
from app.core.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])
settings = get_settings()
logger = logging.getLogger(__name__)


class ProfileResponse(BaseModel):
    user_id: str
    email: str
    nickname: str
    account_type: str
    is_active: bool


class ProfileUpdateRequest(BaseModel):
    nickname: str
    
    @validator('nickname')
    def validate_nickname(cls, v):
        if len(v) < 2 or len(v) > 10:
            raise ValueError('닉네임은 2-10자 사이여야 합니다')
        
        # 한글과 영문만 허용
        if not re.match(r'^[가-힣a-zA-Z]+$', v):
            raise ValueError('닉네임은 한글과 영문만 사용 가능합니다')
        
        return v


@router.get("", response_model=BaseResponse[ProfileResponse])
async def get_profile(
    current_user: User = Depends(get_current_user),
) -> BaseResponse[ProfileResponse]:
    """
    현재 로그인한 사용자의 프로필 정보 조회
    
    Args:
        current_user: 현재 로그인한 사용자
        
    Returns:
        사용자 프로필 정보 (이메일 마스킹 처리)
    """
    try:
        # 이메일 마스킹 처리
        email = current_user.email
        if '@' in email:
            username, domain = email.split('@')
            if len(username) > 2:
                masked_username = username[:2] + '*' * (len(username) - 2)
            else:
                masked_username = username[0] + '*'
            masked_email = f"{masked_username}@{domain}"
        else:
            masked_email = email
        
        profile_data = ProfileResponse(
            user_id=str(current_user.id),
            email=masked_email,
            nickname=current_user.nickname,
            account_type=current_user.account_type,
            is_active=current_user.is_active
        )
        
        return BaseResponse(
            data=profile_data,
            message="프로필 정보 조회 성공"
        )
        
    except Exception as e:
        logger.error(f"프로필 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 조회 중 오류가 발생했습니다."
        )


@router.put("", response_model=BaseResponse[ProfileResponse])
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> BaseResponse[ProfileResponse]:
    """
    사용자 프로필 정보 업데이트 (닉네임만)
    
    Args:
        request: 업데이트할 프로필 정보
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
        
    Returns:
        업데이트된 프로필 정보
    """
    try:
        # 닉네임 중복 확인
        if request.nickname != current_user.nickname:
            stmt = select(User).where(User.nickname == request.nickname)
            result = db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 사용 중인 닉네임입니다."
                )
        
        # 프로필 업데이트
        current_user.nickname = request.nickname
        db.commit()
        db.refresh(current_user)
        
        # 이메일 마스킹 처리
        email = current_user.email
        if '@' in email:
            username, domain = email.split('@')
            if len(username) > 2:
                masked_username = username[:2] + '*' * (len(username) - 2)
            else:
                masked_username = username[0] + '*'
            masked_email = f"{masked_username}@{domain}"
        else:
            masked_email = email
        
        profile_data = ProfileResponse(
            user_id=str(current_user.id),
            email=masked_email,
            nickname=current_user.nickname,
            account_type=current_user.account_type,
            is_active=current_user.is_active
        )
        
        logger.info(f"프로필 업데이트 성공: {current_user.email}")
        
        return BaseResponse(
            data=profile_data,
            message="프로필 업데이트 성공"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프로필 업데이트 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 업데이트 중 오류가 발생했습니다."
        )


@router.get("/check-nickname/{nickname}")
async def check_nickname_availability(
    nickname: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """
    닉네임 중복 확인 API
    
    Args:
        nickname: 확인할 닉네임
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션
        
    Returns:
        닉네임 사용 가능 여부
    """
    try:
        # 자신의 현재 닉네임과 같으면 사용 가능
        if nickname == current_user.nickname:
            data = {
                "available": True,
                "message": "현재 사용 중인 닉네임입니다."
            }
        else:
            stmt = select(User).where(User.nickname == nickname)
            result = db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            data = {
                "available": existing_user is None,
                "message": "사용 가능한 닉네임입니다." if existing_user is None else "이미 사용 중인 닉네임입니다."
            }
        
        return BaseResponse(
            data=data,
            message="닉네임 중복 확인이 완료되었습니다."
        )
    except Exception as e:
        logger.error(f"닉네임 확인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="닉네임 확인 중 오류가 발생했습니다."
        )
