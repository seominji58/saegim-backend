"""
이메일 변경 API 라우터
"""

import logging
import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.email_verification import EmailVerification
from app.models.user import User
from app.schemas.base import BaseResponse
from app.utils.email_service import EmailService

router = APIRouter(prefix="/change-email", tags=["change-email"])
settings = get_settings()
logger = logging.getLogger(__name__)


class EmailChangeRequest(BaseModel):
    new_email: EmailStr
    password: str  # 기존 이메일 인증을 위한 비밀번호


class EmailVerificationRequest(BaseModel):
    new_email: EmailStr


# 이 클래스는 더 이상 필요하지 않으므로 제거


@router.post("/send-verification", response_model=BaseResponse[Dict[str, str]])
async def send_email_change_verification(
    request: EmailVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, str]]:
    """
    이메일 변경을 위한 인증 URL 발송 API

    Args:
        request: 새로운 이메일 주소
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션

    Returns:
        인증 URL 발송 성공 응답
    """
    try:
        # 1. 새로운 이메일 중복 확인
        stmt = select(User).where(User.email == request.new_email)
        result = db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 이메일입니다.",
            )

        # 2. 기존 이메일과 같은지 확인
        if request.new_email == current_user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 사용 중인 이메일과 동일합니다.",
            )

        # 3. 인증 토큰 생성 (6자리 랜덤 코드)
        verification_token = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )

        # 4. 기존 인증 코드가 있다면 삭제
        stmt = select(EmailVerification).where(
            EmailVerification.email == request.new_email,
            EmailVerification.verification_type == "change",
        )
        result = db.execute(stmt)
        existing_verification = result.scalar_one_or_none()

        if existing_verification:
            db.delete(existing_verification)

        # 5. 새로운 인증 토큰 저장
        new_verification = EmailVerification(
            email=request.new_email,
            verification_code=verification_token,  # 토큰을 verification_code 필드에 저장
            verification_type="change",  # 이메일 변경용 (10자 이하로 수정)
            expires_at=datetime.now() + timedelta(minutes=30),  # 30분 유효
        )

        db.add(new_verification)
        db.commit()

        # 6. 인증 URL 생성 (토큰만 포함)
        verification_url = f"{settings.frontend_url}/profile?token={verification_token}&action=change-email"

        # 7. 실제 이메일 발송
        email_service = EmailService()
        await email_service.send_email_change_verification(
            to_email=request.new_email,
            verification_url=verification_url,
            current_email=current_user.email,
        )

        logger.info(f"이메일 변경 인증 URL 발송: {request.new_email}")

        return BaseResponse(
            data={
                "message": "인증 이메일이 발송되었습니다.",
                "email_sent": "true",
                "target_email": request.new_email,
                "current_email": current_user.email,
                "expires_in_minutes": "30",
                "instructions": "이메일을 확인하여 인증 링크를 클릭해주세요.",
            },
            message="이메일 변경 인증 이메일이 성공적으로 발송되었습니다.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이메일 변경 인증 URL 발송 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "인증 이메일 발송 중 오류가 발생했습니다.",
                "email_sent": "false",
                "error_type": "email_send_failed",
                "suggestion": "잠시 후 다시 시도해주세요.",
            },
        )


@router.get("/verify-token")
async def verify_email_change_token(
    token: str,
    email: str = None,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """
    이메일 변경 토큰 검증 API

    Args:
        token: 인증 토큰
        email: 새로운 이메일 주소
        db: 데이터베이스 세션

    Returns:
        토큰 검증 결과
    """
    try:
        # 1. 토큰 검증 (email 파라미터가 있으면 사용, 없으면 토큰만으로 검증)
        if email:
            stmt = select(EmailVerification).where(
                EmailVerification.email == email,
                EmailVerification.verification_code == token,
                EmailVerification.verification_type == "change",
                EmailVerification.expires_at > datetime.now(),
                EmailVerification.is_used is False,
            )
        else:
            stmt = select(EmailVerification).where(
                EmailVerification.verification_code == token,
                EmailVerification.verification_type == "change",
                EmailVerification.expires_at > datetime.now(),
                EmailVerification.is_used is False,
            )

        result = db.execute(stmt)
        verification = result.scalar_one_or_none()

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 인증 토큰입니다.",
            )

        return BaseResponse(
            data={
                "valid": "true",
                "email": verification.email,
                "message": "인증 토큰이 유효합니다.",
            },
            message="토큰 검증 성공",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"토큰 검증 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="토큰 검증 중 오류가 발생했습니다.",
        )


# 이 API는 더 이상 필요하지 않으므로 제거
# 이메일 변경은 verify-password API에서 한 번에 처리됨


class EmailChangeWithTokenRequest(BaseModel):
    new_email: EmailStr
    password: str  # 기존 이메일 인증을 위한 비밀번호
    token: str  # 이메일 인증 토큰


@router.post("/verify-password", response_model=BaseResponse[Dict[str, str]])
async def verify_password_and_change_email(
    request: EmailChangeWithTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, str]]:
    """
    토큰 검증 및 비밀번호 확인 후 이메일 변경 API (이메일 회원가입 사용자만)

    Args:
        request: 토큰, 비밀번호 확인 및 이메일 변경 요청
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션

    Returns:
        이메일 변경 성공 응답 (로그아웃 필요)
    """
    try:
        # 1. 이메일 회원가입 사용자인지 확인
        if current_user.account_type != "email":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="소셜 로그인 사용자는 비밀번호 확인이 필요하지 않습니다.",
            )

        # 2. 토큰 검증
        stmt = select(EmailVerification).where(
            EmailVerification.email == request.new_email,
            EmailVerification.verification_code == request.token,
            EmailVerification.verification_type == "change",
            EmailVerification.expires_at > datetime.now(),
            EmailVerification.is_used is False,
        )
        result = db.execute(stmt)
        verification = result.scalar_one_or_none()

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 인증 토큰입니다.",
            )

        # 3. 비밀번호 검증
        from app.utils.encryption import password_hasher

        if not password_hasher.verify_password(
            request.password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비밀번호가 올바르지 않습니다.",
            )

        # 4. 새로운 이메일 중복 확인
        stmt = select(User).where(User.email == request.new_email)
        result = db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 이메일입니다.",
            )

        # 5. 기존 이메일과 같은지 확인
        if request.new_email == current_user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 사용 중인 이메일과 동일합니다.",
            )

        # 6. 이메일 변경
        old_email = current_user.email
        current_user.email = request.new_email

        # 7. 토큰 사용 처리
        verification.is_used = True

        db.commit()
        db.refresh(current_user)
        db.refresh(current_user)

        logger.info(f"이메일 변경 성공: {old_email} → {request.new_email}")

        return BaseResponse(
            data={
                "message": "이메일이 성공적으로 변경되었습니다.",
                "email_changed": "true",
                "old_email": old_email,
                "new_email": request.new_email,
                "requires_logout": "true",
                "redirect_to": "/login",
            },
            message="이메일 변경이 완료되었습니다. 보안을 위해 다시 로그인해주세요.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이메일 변경 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 변경 중 오류가 발생했습니다.",
        )
