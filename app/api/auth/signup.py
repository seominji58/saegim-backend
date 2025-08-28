"""
회원가입 API 라우터
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose.exceptions import JWTError
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import AccountType
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token
from app.db.database import get_session
from app.models.email_verification import EmailVerification
from app.models.user import User
from app.schemas.base import BaseResponse
from app.utils.email_service import EmailService
from app.utils.encryption import password_hasher

router = APIRouter(tags=["auth"])
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

        # 한글과 영문만 허용
        if not re.match(r"^[가-힣a-zA-Z]+$", v):
            raise ValueError("닉네임은 한글과 영문만 사용 가능합니다")

        return v


class SignupResponse(BaseModel):
    user_id: str
    email: str
    nickname: str
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
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
    """
    이메일 회원가입 API

    Args:
        request: 회원가입 요청 데이터
        db: 데이터베이스 세션

    Returns:
        회원가입 성공 응답
    """
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
            EmailVerification.verification_type == "signup",  # 회원가입용만
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
            account_type=AccountType.EMAIL.value,  # 이메일 회원가입
            provider=None,  # 소셜 로그인이 아님
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
    """
    이메일 중복 확인 API

    Args:
        email: 확인할 이메일
        db: 데이터베이스 세션

    Returns:
        이메일 사용 가능 여부
    """
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
    """
    닉네임 중복 확인 API

    Args:
        nickname: 확인할 닉네임
        db: 데이터베이스 세션

    Returns:
        닉네임 사용 가능 여부
    """
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


@router.post("/login", response_model=BaseResponse[LoginResponse])
async def login(
    request: LoginRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[LoginResponse]:
    """
    이메일 로그인 API

    Args:
        request: 로그인 요청 데이터
        db: 데이터베이스 세션

    Returns:
        로그인 성공 응답 (쿠키에 토큰 설정)
    """
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
            # timezone을 일치시켜서 비교
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
        from fastapi.responses import JSONResponse

        response = JSONResponse(
            content={
                "success": True,
                "message": "로그인이 성공적으로 완료되었습니다.",
                "data": response_data.dict(),
            }
        )

        # 쿠키에 토큰 설정 (환경별 동적 설정)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.jwt_access_token_expire_minutes * 60,  # 분을 초로 변환
            path="/",
            domain=settings.cookie_domain,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,  # 일을 초로 변환
            path="/",
            domain=settings.cookie_domain,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 중 오류가 발생했습니다.",
        )


@router.post("/send-verification-email", response_model=BaseResponse[Dict[str, str]])
async def send_verification_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, str]]:
    logger.info(f"인증 코드 발송 요청 시작: {request.email}")
    """
    이메일 인증 코드 발송 API

    Args:
        request: 이메일 주소
        db: 데이터베이스 세션

    Returns:
        인증 코드 발송 성공 응답
    """
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
        import random

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
            verification_type="signup",  # 회원가입용
            expires_at=datetime.now() + timedelta(minutes=10),  # 10분 유효
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
        logger.error(f"요청 데이터: {request}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인증 코드 발송 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/verify-email", response_model=BaseResponse[Dict[str, str]])
async def verify_email(
    request: EmailVerificationConfirmRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, str]]:
    """
    이메일 인증 코드 확인 API

    Args:
        request: 이메일과 인증 코드
        db: 데이터베이스 세션

    Returns:
        인증 성공 응답
    """
    try:
        # 1. 인증 코드 조회
        stmt = select(EmailVerification).where(
            EmailVerification.email == request.email,
            EmailVerification.verification_code == request.verification_code,
            EmailVerification.verification_type == "signup",  # 회원가입용만
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


@router.get("/me", response_model=BaseResponse[Dict[str, Any]])
async def get_current_user_info(
    request: Request,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, Any]]:
    """
    현재 로그인한 사용자 정보 조회 API (Bearer 토큰 또는 쿠키 기반)

    Args:
        request: FastAPI Request 객체
        db: 데이터베이스 세션

    Returns:
        사용자 정보
    """
    try:
        # 1. Authorization 헤더에서 Bearer 토큰 확인
        auth_header = request.headers.get("Authorization")
        current_user = None

        if auth_header and auth_header.startswith("Bearer "):
            # Bearer 토큰 방식
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

        # 3. 사용자를 찾을 수 없는 경우
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다."
            )

        # 4. 계정 활성화 상태 확인
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비활성화된 계정입니다.",
            )

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
