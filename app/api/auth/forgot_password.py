"""
비밀번호 재설정 관련 API
"""
import re
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_session
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.utils.email_service import EmailService

router = APIRouter()


class SendPasswordResetEmailRequest(BaseModel):
    email: EmailStr


class VerifyPasswordResetCodeRequest(BaseModel):
    email: EmailStr
    verification_code: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    verification_code: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 9:
            raise ValueError('비밀번호는 9자 이상이어야 합니다')
        
        # 영문, 숫자, 특수문자 포함 검증
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{9,}$', v):
            raise ValueError('비밀번호는 영문, 숫자, 특수문자를 포함해야 합니다')
        
        return v


@router.post("")
async def send_password_reset_email(
    request: SendPasswordResetEmailRequest,
    db: Session = Depends(get_session),
) -> dict:
    """
    비밀번호 재설정 이메일 발송
    
    Args:
        request: 이메일 주소
        db: 데이터베이스 세션
        
    Returns:
        발송 결과
    """
    try:
        # 사용자 조회
        stmt = select(User).where(User.email == request.email)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 이메일로 가입된 계정이 없습니다."
            )
        
        # 소셜 계정 사용자인 경우
        if user.account_type == "social":
            # 소셜 계정은 비밀번호 재설정 불가능 - 에러 페이지로 리다이렉트
            provider_name = user.provider or '소셜'
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"소셜 계정 사용자입니다. {provider_name} 계정으로 가입된 사용자입니다. 비밀번호 재설정은 해당 서비스에서 직접 진행해주세요."
            )
        
        # 이메일 계정 사용자인 경우
        else:
            # 기존 토큰이 있다면 만료 처리
            stmt = select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used == False
            )
            result = db.execute(stmt)
            existing_tokens = result.scalars().all()
            
            for token in existing_tokens:
                token.is_used = True
                token.used_at = datetime.utcnow()
            
            # 새로운 토큰 생성
            token_value = str(uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token_value,
                expires_at=expires_at,
                is_used=False
            )
            
            db.add(reset_token)
            db.commit()
            db.refresh(reset_token)
            
            # 비밀번호 재설정 이메일 발송
            email_service = EmailService()
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token_value}"
            
            email_sent = await email_service.send_password_reset_email(
                to_email=user.email,
                nickname=user.nickname,
                reset_url=reset_url
            )
            
            if not email_sent:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요."
                )
            
            return {
                "success": True,
                "message": "비밀번호 재설정 이메일을 발송했습니다.",
                "is_social_account": False
            }
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"비밀번호 재설정 이메일 발송 중 오류: {e}")
        
        # 소셜 계정 사용자인 경우 에러 페이지로 리다이렉트하도록 안내
        if user and user.account_type == "social":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{user.provider or '소셜'} 계정으로 가입된 사용자입니다. 비밀번호 재설정은 해당 서비스에서 직접 진행해주세요."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이메일 발송 중 오류가 발생했습니다."
            )


@router.post("/verify")
async def verify_password_reset_code(
    request: VerifyPasswordResetCodeRequest,
    db: Session = Depends(get_session),
) -> dict:
    """
    비밀번호 재설정 인증코드 확인
    
    Args:
        request: 이메일과 인증코드
        db: 데이터베이스 세션
        
    Returns:
        인증 결과
    """
    try:
        # 사용자 조회
        stmt = select(User).where(User.email == request.email)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 이메일로 가입된 계정이 없습니다."
            )
        
        # 소셜 계정 사용자인 경우
        if user.account_type == "social":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="소셜 계정 사용자는 비밀번호 재설정이 불가능합니다."
            )
        
        # 토큰 조회
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.token == request.verification_code,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        )
        result = db.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 인증코드입니다."
            )
        
        return {
            "success": True,
            "message": "인증코드가 확인되었습니다.",
            "verified": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증코드 확인 중 오류가 발생했습니다."
        )


@router.post("/reset")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_session),
) -> dict:
    """
    비밀번호 재설정
    
    Args:
        request: 이메일, 인증코드, 새 비밀번호
        db: 데이터베이스 세션
        
    Returns:
        재설정 결과
    """
    try:
        # 사용자 조회
        stmt = select(User).where(User.email == request.email)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 이메일로 가입된 계정이 없습니다."
            )
        
        # 소셜 계정 사용자인 경우
        if user.account_type == "social":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="소셜 계정 사용자는 비밀번호 재설정이 불가능합니다."
            )
        
        # 토큰 조회 및 검증
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.token == request.verification_code,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        )
        result = db.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 인증코드입니다."
            )
        
        # 비밀번호 해시화 및 업데이트
        from app.core.security import get_password_hash
        user.password_hash = get_password_hash(request.new_password)
        
        # 토큰 사용 처리
        token.is_used = True
        token.used_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": "비밀번호가 성공적으로 변경되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 재설정 중 오류가 발생했습니다."
        )
