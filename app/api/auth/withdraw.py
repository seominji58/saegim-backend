"""
회원 탈퇴 API
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import update, delete
from datetime import datetime, timedelta
from typing import Dict

from app.core.deps import get_session, get_current_user_id
from pydantic import BaseModel
from app.models.user import User
from app.models.diary import DiaryEntry
from app.models.fcm import FCMToken, NotificationSettings, NotificationHistory
from app.models.emotion_stats import EmotionStats
from app.models.ai_usage_log import AIUsageLog
from app.models.notification import Notification
from app.models.oauth_token import OAuthToken
from app.models.password_reset_token import PasswordResetToken
from app.models.email_verification import EmailVerification
from app.models.image import Image
from app.core.security import password_hasher
from app.schemas.base import BaseResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class WithdrawRequest(BaseModel):
    """탈퇴 요청 스키마"""
    password: str  # 이메일 계정의 경우 비밀번호 확인, 소셜 계정은 빈 문자열


class WithdrawResponse(BaseModel):
    """탈퇴 응답 스키마"""
    message: str
    withdrawal_date: datetime
    restore_until: datetime


@router.post("/withdraw", response_model=BaseResponse[WithdrawResponse])
async def withdraw_account(
    request: WithdrawRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_session),
) -> BaseResponse[WithdrawResponse]:
    """
    회원 탈퇴 API
    
    Args:
        request: 탈퇴 요청 데이터 (비밀번호 확인)
        current_user_id: 현재 로그인한 사용자 ID
        db: 데이터베이스 세션
        
    Returns:
        탈퇴 성공 응답
    """
    try:
        logger.info(f"탈퇴 요청 시작: {current_user_id}")
        
        # 1. 사용자 정보 조회
        user = db.query(User).filter(
            User.id == current_user_id,
            User.deleted_at == None
        ).first()
        
        if not user:
            logger.error(f"사용자를 찾을 수 없음: {current_user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        
        logger.info(f"사용자 조회 성공: {user.email}, 계정 타입: {user.account_type}")
        
        # 2. 계정 타입별 비밀번호 확인
        if user.account_type == "email":
            logger.info("이메일 계정 비밀번호 확인 중")
            # 이메일 계정은 비밀번호 필수
            if not request.password:
                logger.warning("이메일 계정에서 비밀번호가 제공되지 않음")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이메일 계정은 비밀번호 확인이 필요합니다."
                )
            if not password_hasher.verify_password(request.password, user.password_hash):
                logger.warning("이메일 계정 비밀번호 확인 실패")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="비밀번호가 올바르지 않습니다."
                )
            logger.info("이메일 계정 비밀번호 확인 성공")
        elif user.account_type == "social":
            logger.info("소셜 계정 탈퇴 - 비밀번호 확인 불필요")
            # 소셜 계정은 비밀번호 확인 불필요
            pass
        else:
            logger.error(f"알 수 없는 계정 타입: {user.account_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지원하지 않는 계정 타입입니다."
            )
        
        # 3. 탈퇴 처리 시작
        withdrawal_date = datetime.now()
        restore_until = withdrawal_date + timedelta(days=30)  # 30일 후
        
        logger.info("탈퇴 처리 시작")
        
        # 4. User 테이블 Soft Delete
        logger.info("User 테이블 Soft Delete 시작")
        db.execute(
            update(User)
            .where(User.id == current_user_id)
            .values(
                deleted_at=withdrawal_date
            )
        )
        logger.info("User 테이블 Soft Delete 완료")
        
        # 5. Diary 테이블 Soft Delete
        logger.info("Diary 테이블 Soft Delete 시작")
        db.execute(
            update(DiaryEntry)
            .where(DiaryEntry.user_id == current_user_id)
            .values(
                deleted_at=withdrawal_date
            )
        )
        logger.info("Diary 테이블 Soft Delete 완료")
        
        # 6. 관련 데이터 Hard Delete (즉시 삭제)
        logger.info("관련 데이터 Hard Delete 시작")
        
        # FCM 토큰 삭제
        db.execute(
            delete(FCMToken)
            .where(FCMToken.user_id == current_user_id)
        )
        
        # 알림 설정 삭제
        db.execute(
            delete(NotificationSettings)
            .where(NotificationSettings.user_id == current_user_id)
        )
        
        # 알림 히스토리 삭제
        db.execute(
            delete(NotificationHistory)
            .where(NotificationHistory.user_id == current_user_id)
        )
        
        # 감정 통계 삭제
        db.execute(
            delete(EmotionStats)
            .where(EmotionStats.user_id == current_user_id)
        )
        
        # AI 사용 로그 삭제
        db.execute(
            delete(AIUsageLog)
            .where(AIUsageLog.user_id == current_user_id)
        )
        
        # 알림 삭제
        db.execute(
            delete(Notification)
            .where(Notification.user_id == current_user_id)
        )
        
        # OAuth 토큰 삭제
        db.execute(
            delete(OAuthToken)
            .where(OAuthToken.user_id == current_user_id)
        )
        
        # 비밀번호 재설정 토큰 삭제
        db.execute(
            delete(PasswordResetToken)
            .where(PasswordResetToken.user_id == current_user_id)
        )
        
        # 이메일 인증 삭제
        db.execute(
            delete(EmailVerification)
            .where(EmailVerification.email == user.email)
        )
        
        # 이미지 삭제 (다이어리 관련)
        db.execute(
            delete(Image)
            .where(Image.diary_id.in_(
                db.query(DiaryEntry.id)
                .filter(DiaryEntry.user_id == current_user_id)
            ))
        )
        
        logger.info("관련 데이터 Hard Delete 완료")
        
        # 7. 변경사항 커밋
        logger.info("데이터베이스 커밋 시작")
        db.commit()
        logger.info("데이터베이스 커밋 완료")
        
        # 8. 응답 생성
        account_type_message = "이메일 계정" if user.account_type == "email" else "소셜 계정"
        response_data = WithdrawResponse(
            message=f"{account_type_message} 탈퇴가 완료되었습니다. 30일 이내에 계정을 복구할 수 있습니다.",
            withdrawal_date=withdrawal_date,
            restore_until=restore_until
        )
        
        logger.info(f"탈퇴 성공: {current_user_id} ({user.account_type})")
        
        return BaseResponse(
            success=True,
            data=response_data,
            message=f"{account_type_message} 탈퇴가 성공적으로 처리되었습니다."
        )
        
    except HTTPException:
        logger.error("HTTPException 발생, 롤백")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"탈퇴 처리 중 예외 발생: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="탈퇴 처리 중 오류가 발생했습니다."
        )
