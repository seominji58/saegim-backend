"""
계정 복구 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import update, select
from datetime import datetime, timedelta
from typing import Dict
from pydantic import BaseModel

from app.models.user import User
from app.models.diary import DiaryEntry
from app.models.email_verification import EmailVerification

from app.schemas.base import BaseResponse
from app.utils.email_service import EmailService
from app.core.deps import get_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class RestoreRequest(BaseModel):
    """복구 요청 스키마"""
    email: str
    verification_code: str


class RestoreResponse(BaseModel):
    """복구 응답 스키마"""
    message: str
    restored_at: datetime
    user_id: str
    email: str
    nickname: str


class SendRestoreEmailRequest(BaseModel):
    """복구 이메일 발송 요청 스키마"""
    email: str


@router.post("/restore", response_model=BaseResponse[RestoreResponse])
async def restore_account(
    request: RestoreRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[RestoreResponse]:
    """
    계정 복구 API
    
    Args:
        request: 복구 요청 데이터 (이메일, 인증코드)
        db: 데이터베이스 세션
        
    Returns:
        복구 성공 응답
    """
    try:
        # 1. 탈퇴된 사용자 조회
        user = db.query(User).filter(
            User.email == request.email,
            User.deleted_at.is_not(None)
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="탈퇴된 계정을 찾을 수 없습니다."
            )
        
        # 2. 30일 이내인지 확인
        # timezone을 일치시켜서 비교
        current_time = datetime.now(user.deleted_at.tzinfo) if user.deleted_at.tzinfo else datetime.now()
        deleted_time = user.deleted_at.replace(tzinfo=None) if user.deleted_at.tzinfo else user.deleted_at
        current_time_naive = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
        
        if deleted_time < current_time_naive - timedelta(days=30):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="탈퇴 후 30일이 경과되어 복구할 수 없습니다."
            )
        
        # 3. 이메일 인증 코드 확인
        stmt = select(EmailVerification).where(
            EmailVerification.email == request.email,
            EmailVerification.verification_code == request.verification_code,
            EmailVerification.verification_type == "restore",  # 복구용만
            EmailVerification.expires_at > datetime.now(),
            EmailVerification.is_used == False
        )
        result = db.execute(stmt)
        verification = result.scalar_one_or_none()
        
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 인증 코드입니다."
            )
        
        # 4. 인증 코드 사용 처리
        verification.is_used = True
        db.commit()
        
        # 5. 계정 복구 처리
        restored_at = datetime.now()
        
        # User 테이블 복구
        db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                deleted_at=None
            )
        )
        
        # Diary 테이블 복구
        db.execute(
            update(DiaryEntry)
            .where(DiaryEntry.user_id == user.id)
            .values(
                deleted_at=None
            )
        )
        
        # 6. 사용된 인증 코드 삭제
        db.delete(verification)
        
        # 7. 변경사항 커밋
        db.commit()
        
        # 8. 응답 생성
        account_type_message = "이메일 계정" if user.account_type == "email" else "소셜 계정"
        response_data = RestoreResponse(
            message=f"{account_type_message}이 성공적으로 복구되었습니다.",
            restored_at=restored_at,
            user_id=str(user.id),
            email=user.email,
            nickname=user.nickname
        )
        
        logger.info(f"계정 복구 성공: {user.email}")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message=f"{account_type_message} 복구가 완료되었습니다."
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"계정 복구 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="계정 복구 중 오류가 발생했습니다."
        )


@router.post("/restore/send-restore-email", response_model=BaseResponse[Dict[str, str]])
async def send_restore_email(
    request: SendRestoreEmailRequest,
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, str]]:
    """
    복구 이메일 발송 API
    
    Args:
        request: 복구 이메일 발송 요청 데이터
        db: 데이터베이스 세션
        
    Returns:
        이메일 발송 성공 응답
    """
    try:
        # 1. 탈퇴된 사용자 확인
        user = db.query(User).filter(
            User.email == request.email,
            User.deleted_at.is_not(None)
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="탈퇴된 계정을 찾을 수 없습니다."
            )
        
        # 2. 30일 이내인지 확인
        # timezone을 일치시켜서 비교
        current_time = datetime.now(user.deleted_at.tzinfo) if user.deleted_at.tzinfo else datetime.now()
        deleted_time = user.deleted_at.replace(tzinfo=None) if user.deleted_at.tzinfo else user.deleted_at
        current_time_naive = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
        
        if deleted_time < current_time_naive - timedelta(days=30):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="탈퇴 후 30일이 경과되어 복구할 수 없습니다."
            )
        
        # 3. 인증 코드 생성 (6자리 숫자)
        import random
        verification_code = str(random.randint(100000, 999999))
        
        # 4. 기존 인증 코드가 있다면 만료 처리 (삭제하지 않고 만료만 표시)
        stmt = select(EmailVerification).where(
            EmailVerification.email == request.email,
            EmailVerification.verification_type == "restore",
            EmailVerification.expires_at > datetime.now()  # 아직 유효한 코드만
        )
        result = db.execute(stmt)
        existing_verification = result.scalar_one_or_none()
        
        if existing_verification:
            # 기존 코드를 만료 처리 (삭제하지 않음)
            existing_verification.expires_at = datetime.now() - timedelta(seconds=1)
            existing_verification.is_used = True
            db.commit()
        
        # 5. 새로운 인증 코드 저장
        new_verification = EmailVerification(
            email=request.email,
            verification_code=verification_code,
            verification_type="restore",  # 복구용
            expires_at=datetime.now() + timedelta(minutes=10)  # 10분 유효
        )
        
        db.add(new_verification)
        db.commit()
        
        # 6. 실제 이메일 발송
        email_service = EmailService()
        email_sent = await email_service.send_verification_email(request.email, verification_code, "restore")
        
        if not email_sent:
            # 이메일 발송 실패 시 인증 코드 삭제
            db.delete(new_verification)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="복구 이메일 발송에 실패했습니다. 잠시 후 다시 시도해주세요."
            )
        
        logger.info(f"복구 이메일 발송 성공: {request.email} (인증코드: {verification_code})")
        
        return BaseResponse(
            success=True,
            data={"message": "복구 이메일이 발송되었습니다."},
            message="복구 이메일이 성공적으로 발송되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"복구 이메일 발송 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 발송 중 오류가 발생했습니다."
        )
