"""
회원가입 및 이메일 인증 API 라우터
이메일 회원가입, 이메일 인증, 중복 확인
"""

import logging
import random
import re
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import AccountType
from app.core.config import get_settings
from app.db.database import get_session
from app.models.email_verification import EmailVerification
from app.models.user import User
from app.schemas.base import BaseResponse
from app.utils.email_service import EmailService
from app.utils.encryption import password_hasher

router = APIRouter(tags=["registration"])
settings = get_settings()
logger = logging.getLogger(__name__)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 9:
            raise ValueError("비밀번호는 9자 이상이어야 합니다")

        # 영문, 숫자, 특수문자 포함 검사
        has_letter = bool(re.search(r"[a-zA-Z]", v))
        has_number = bool(re.search(r"\d", v))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?]', v))

        if not (has_letter and has_number and has_special):
            raise ValueError("비밀번호는 영문, 숫자, 특수문자를 모두 포함해야 합니다")

        return v

    @validator("nickname")
    def validate_nickname(cls, v):
        if len(v) < 2 or len(v) > 10:
            raise ValueError("닉네임은 2-10자 사이여야 합니다")

        if not re.match(r"^[가-힣a-zA-Z]+$", v):
            raise ValueError("닉네임은 한글과 영문만 사용 가능합니다")

        return v


class SignupResponse(BaseModel):
    user_id: str
    email: str
    nickname: str
    message: str


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirmRequest(BaseModel):
    email: EmailStr
    verification_code: str


@router.post("/signup", response_model=BaseResponse[SignupResponse])
async def signup(
    request: SignupRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[SignupResponse]:
    """이메일 회원가입 API"""
    try:
        # 1. 이메일 중복 확인
        stmt = select(User).where(User.email == request.email)
        result = db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 가입된 이메일입니다.",
            )

        # 2. 이메일 인증 확인
        stmt = select(EmailVerification).where(
            EmailVerification.email == request.email,
            EmailVerification.verification_type == "signup",
            EmailVerification.is_used is True,
        )
        result = db.execute(stmt)
        email_verification = result.scalar_one_or_none()

        if not email_verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 인증이 필요합니다.",
            )

        # 3. 닉네임 중복 확인
        stmt = select(User).where(User.nickname == request.nickname)
        result = db.execute(stmt)
        existing_nickname = result.scalar_one_or_none()

        if existing_nickname:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용 중인 닉네임입니다.",
            )

        # 4. 비밀번호 해싱
        hashed_password = password_hasher.hash_password(request.password)

        # 5. 사용자 생성
        new_user = User(
            email=request.email,
            password_hash=hashed_password,
            nickname=request.nickname,
            account_type=AccountType.EMAIL.value,
            provider=None,
            provider_id=None,
            is_active=True,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 6. 이메일 인증 기록 삭제 (회원가입 완료 후)
        db.delete(email_verification)
        db.commit()

        # 7. 환영 이메일 발송
        email_service = EmailService()
        await email_service.send_welcome_email(new_user.email, new_user.nickname)

        logger.info(f"새 사용자 가입: {new_user.email}")

        return BaseResponse(
            data=SignupResponse(
                user_id=str(new_user.id),
                email=new_user.email,
                nickname=new_user.nickname,
                message="회원가입이 완료되었습니다.",
            ),
            message="회원가입이 성공적으로 완료되었습니다.",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"회원가입 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다.",
        )


@router.get("/check-email/{email}")
async def check_email_availability(
    email: str,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """이메일 중복 확인 API"""
    try:
        stmt = select(User).where(User.email == email)
        result = db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        data = {
            "available": existing_user is None,
            "message": "사용 가능한 이메일입니다."
            if existing_user is None
            else "이미 사용 중인 이메일입니다.",
        }

        return BaseResponse(data=data, message="이메일 중복 확인이 완료되었습니다.")
    except Exception as e:
        logger.error(f"이메일 확인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 확인 중 오류가 발생했습니다.",
        )


@router.get("/check-nickname/{nickname}")
async def check_nickname_availability(
    nickname: str,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """닉네임 중복 확인 API"""
    try:
        stmt = select(User).where(User.nickname == nickname)
        result = db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        data = {
            "available": existing_user is None,
            "message": "사용 가능한 닉네임입니다."
            if existing_user is None
            else "이미 사용 중인 닉네임입니다.",
        }

        return BaseResponse(data=data, message="닉네임 중복 확인이 완료되었습니다.")
    except Exception as e:
        logger.error(f"닉네임 확인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="닉네임 확인 중 오류가 발생했습니다.",
        )


@router.post("/send-verification-email", response_model=BaseResponse[Dict[str, str]])
async def send_verification_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, str]]:
    """이메일 인증 코드 발송 API"""
    logger.info(f"인증 코드 발송 요청 시작: {request.email}")

    try:
        # 1. 이메일 중복 확인
        stmt = select(User).where(User.email == request.email)
        result = db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 가입된 이메일입니다.",
            )

        # 2. 인증 코드 생성 (6자리 숫자)
        verification_code = str(random.randint(100000, 999999))

        # 3. 기존 인증 코드가 있다면 삭제
        stmt = select(EmailVerification).where(EmailVerification.email == request.email)
        result = db.execute(stmt)
        existing_verification = result.scalar_one_or_none()

        if existing_verification:
            db.delete(existing_verification)

        # 4. 새로운 인증 코드 저장
        new_verification = EmailVerification(
            email=request.email,
            verification_code=verification_code,
            verification_type="signup",
            expires_at=datetime.now() + timedelta(minutes=10),
        )

        db.add(new_verification)
        db.commit()

        # 5. 실제 이메일 발송
        email_service = EmailService()
        email_sent = await email_service.send_verification_email(
            request.email, verification_code
        )

        if not email_sent:
            # 이메일 발송 실패 시 인증 코드 삭제
            db.delete(new_verification)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요.",
            )

        logger.info(f"인증 코드 발송: {request.email}")

        return BaseResponse(
            data={"message": "인증 코드가 발송되었습니다."},
            message="인증 코드가 이메일로 발송되었습니다.",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"인증 코드 발송 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인증 코드 발송 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/verify-email", response_model=BaseResponse[Dict[str, str]])
async def verify_email(
    request: EmailVerificationConfirmRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, str]]:
    """이메일 인증 코드 확인 API"""
    try:
        # 1. 인증 코드 조회
        stmt = select(EmailVerification).where(
            EmailVerification.email == request.email,
            EmailVerification.verification_code == request.verification_code,
            EmailVerification.verification_type == "signup",
            EmailVerification.expires_at > datetime.now(),
            EmailVerification.is_used is False,
        )
        result = db.execute(stmt)
        verification = result.scalar_one_or_none()

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 인증 코드입니다.",
            )

        # 2. 인증 완료 처리
        verification.is_used = True
        db.commit()

        logger.info(f"이메일 인증 완료: {request.email}")

        return BaseResponse(
            data={"message": "이메일 인증이 완료되었습니다."},
            message="이메일 인증이 성공적으로 완료되었습니다.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이메일 인증 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 인증 중 오류가 발생했습니다.",
        )
