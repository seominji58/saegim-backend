"""
데이터 정리 서비스 (영구 삭제 스케줄러)
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ai_usage_log import AIUsageLog
from app.models.diary import DiaryEntry
from app.models.email_verification import EmailVerification
from app.models.emotion_stats import EmotionStats
from app.models.image import Image
from app.models.oauth_token import OAuthToken
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User

logger = logging.getLogger(__name__)


class CleanupService:
    """데이터 정리 서비스"""

    def __init__(self, session: Session):
        self.session = session

    def cleanup_expired_soft_deleted_data(self) -> dict:
        """
        30일 경과된 Soft Delete 데이터 영구 삭제

        Returns:
            삭제된 데이터 통계
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=30)

            # 영구 삭제 대상 사용자 서브쿼리 (30일 경과 Soft Delete)
            users_to_delete_subq = select(User.id).where(
                User.deleted_at.is_not(None), User.deleted_at < cutoff_date
            )

            # 삭제 전 통계
            self.session.query(User).filter(
                User.deleted_at.is_not(None), User.deleted_at < cutoff_date
            ).count()

            self.session.query(DiaryEntry).filter(
                DiaryEntry.deleted_at.is_not(None), DiaryEntry.deleted_at < cutoff_date
            ).count()

            # 영구 삭제 실행 (FK 순서 준수: 가장 하위 → 상위)
            # 1) 이미지 삭제 (다이어리 기준)
            deleted_images = self.session.execute(
                delete(Image).where(
                    Image.diary_id.in_(
                        select(DiaryEntry.id).where(
                            (
                                DiaryEntry.deleted_at.is_not(None)
                                & (DiaryEntry.deleted_at < cutoff_date)
                            )
                            | (DiaryEntry.user_id.in_(users_to_delete_subq))
                        )
                    )
                )
            ).rowcount

            # 2) 다이어리 삭제 (사용자 기준 포함)
            deleted_diaries = self.session.execute(
                delete(DiaryEntry).where(
                    (
                        DiaryEntry.deleted_at.is_not(None)
                        & (DiaryEntry.deleted_at < cutoff_date)
                    )
                    | (DiaryEntry.user_id.in_(users_to_delete_subq))
                )
            ).rowcount

            # 3) 사용자 종속 테이블 삭제 (CASCADE 미설정 테이블)
            deleted_ai_logs = self.session.execute(
                delete(AIUsageLog).where(AIUsageLog.user_id.in_(users_to_delete_subq))
            ).rowcount
            deleted_oauth = self.session.execute(
                delete(OAuthToken).where(OAuthToken.user_id.in_(users_to_delete_subq))
            ).rowcount
            deleted_reset_tokens = self.session.execute(
                delete(PasswordResetToken).where(
                    PasswordResetToken.user_id.in_(users_to_delete_subq)
                )
            ).rowcount
            deleted_emotion_stats = self.session.execute(
                delete(EmotionStats).where(
                    EmotionStats.user_id.in_(users_to_delete_subq)
                )
            ).rowcount
            deleted_email_verifications = self.session.execute(
                delete(EmailVerification).where(
                    EmailVerification.user_id.in_(users_to_delete_subq)
                )
            ).rowcount

            # 4) 사용자 삭제 (최상위)
            deleted_users = self.session.execute(
                delete(User).where(User.id.in_(users_to_delete_subq))
            ).rowcount

            # 변경사항 커밋
            self.session.commit()

            # 로그 기록
            logger.info(
                "영구 삭제 완료: 사용자 %s, 다이어리 %s, 이미지 %s, oauth %s, reset_tokens %s, ai_logs %s, emotion_stats %s, email_verifications %s",
                deleted_users,
                deleted_diaries,
                deleted_images,
                deleted_oauth,
                deleted_reset_tokens,
                deleted_ai_logs,
                deleted_emotion_stats,
                deleted_email_verifications,
            )

            return {
                "deleted_users": deleted_users,
                "deleted_diaries": deleted_diaries,
                "deleted_images": deleted_images,
                "deleted_oauth_tokens": deleted_oauth,
                "deleted_password_reset_tokens": deleted_reset_tokens,
                "deleted_ai_usage_logs": deleted_ai_logs,
                "deleted_emotion_stats": deleted_emotion_stats,
                "deleted_email_verifications": deleted_email_verifications,
                "cutoff_date": cutoff_date.isoformat(),
                "message": (
                    "30일 경과 데이터 영구 삭제 완료: "
                    f"사용자 {deleted_users}개, 다이어리 {deleted_diaries}개, 이미지 {deleted_images}개"
                ),
            }

        except Exception as e:
            self.session.rollback()
            logger.error(f"영구 삭제 중 오류 발생: {e}")
            raise

    def get_soft_deleted_statistics(self) -> dict:
        """
        Soft Delete된 데이터 통계 조회

        Returns:
            Soft Delete 데이터 통계
        """
        try:
            current_time = datetime.now()
            thirty_days_ago = current_time - timedelta(days=30)

            # 30일 이내 Soft Delete된 데이터
            recent_users = (
                self.session.query(User)
                .filter(
                    User.deleted_at.is_not(None), User.deleted_at >= thirty_days_ago
                )
                .count()
            )

            recent_diaries = (
                self.session.query(DiaryEntry)
                .filter(
                    DiaryEntry.deleted_at.is_not(None),
                    DiaryEntry.deleted_at >= thirty_days_ago,
                )
                .count()
            )

            # 30일 경과된 데이터
            expired_users = (
                self.session.query(User)
                .filter(User.deleted_at.is_not(None), User.deleted_at < thirty_days_ago)
                .count()
            )

            expired_diaries = (
                self.session.query(DiaryEntry)
                .filter(
                    DiaryEntry.deleted_at.is_not(None),
                    DiaryEntry.deleted_at < thirty_days_ago,
                )
                .count()
            )

            return {
                "recent_users": recent_users,
                "recent_diaries": recent_diaries,
                "expired_users": expired_users,
                "expired_diaries": expired_diaries,
                "total_soft_deleted_users": recent_users + expired_users,
                "total_soft_deleted_diaries": recent_diaries + expired_diaries,
            }

        except Exception as e:
            logger.error(f"통계 조회 중 오류 발생: {e}")
            raise
