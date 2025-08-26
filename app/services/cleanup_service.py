"""
데이터 정리 서비스 (영구 삭제 스케줄러)
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import delete
from app.models.user import User
from app.models.diary import DiaryEntry
import logging

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
            
            # 삭제 전 통계
            expired_users_count = self.session.query(User).filter(
                User.deleted_at.is_not(None),
                User.deleted_at < cutoff_date
            ).count()
            
            expired_diaries_count = self.session.query(DiaryEntry).filter(
                DiaryEntry.deleted_at.is_not(None),
                DiaryEntry.deleted_at < cutoff_date
            ).count()
            
            # 영구 삭제 실행
            deleted_users = self.session.execute(
                delete(User).where(
                    User.deleted_at.is_not(None),
                    User.deleted_at < cutoff_date
                )
            ).rowcount
            
            deleted_diaries = self.session.execute(
                delete(DiaryEntry).where(
                    DiaryEntry.deleted_at.is_not(None),
                    DiaryEntry.deleted_at < cutoff_date
                )
            ).rowcount
            
            # 변경사항 커밋
            self.session.commit()
            
            # 로그 기록
            logger.info(
                f"영구 삭제 완료: 사용자 {deleted_users}개, 다이어리 {deleted_diaries}개 삭제됨"
            )
            
            return {
                "deleted_users": deleted_users,
                "deleted_diaries": deleted_diaries,
                "cutoff_date": cutoff_date.isoformat(),
                "message": f"30일 경과 데이터 영구 삭제 완료: 사용자 {deleted_users}개, 다이어리 {deleted_diaries}개"
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
            recent_users = self.session.query(User).filter(
                User.deleted_at.is_not(None),
                User.deleted_at >= thirty_days_ago
            ).count()
            
            recent_diaries = self.session.query(DiaryEntry).filter(
                DiaryEntry.deleted_at.is_not(None),
                DiaryEntry.deleted_at >= thirty_days_ago
            ).count()
            
            # 30일 경과된 데이터
            expired_users = self.session.query(User).filter(
                User.deleted_at.is_not(None),
                User.deleted_at < thirty_days_ago
            ).count()
            
            expired_diaries = self.session.query(DiaryEntry).filter(
                DiaryEntry.deleted_at.is_not(None),
                DiaryEntry.deleted_at < thirty_days_ago
            ).count()
            
            return {
                "recent_users": recent_users,
                "recent_diaries": recent_diaries,
                "expired_users": expired_users,
                "expired_diaries": expired_diaries,
                "total_soft_deleted_users": recent_users + expired_users,
                "total_soft_deleted_diaries": recent_diaries + expired_diaries
            }
            
        except Exception as e:
            logger.error(f"통계 조회 중 오류 발생: {e}")
            raise
