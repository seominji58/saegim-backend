"""
통일된 서비스 기본 클래스
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BaseService:
    """모든 서비스의 기본 클래스"""

    def __init__(self, db: AsyncSession | Session | None = None):
        """
        서비스 초기화

        Args:
            db: 데이터베이스 세션 (AsyncSession 또는 Session)
        """
        self.db = db

    async def commit(self):
        """비동기 커밋 (AsyncSession 사용 시)"""
        if hasattr(self.db, "commit"):
            if hasattr(self.db, "__aenter__"):  # AsyncSession
                await self.db.commit()
            else:  # Session
                self.db.commit()
        else:
            logger.warning("Database session not available for commit")

    async def rollback(self):
        """비동기 롤백 (AsyncSession 사용 시)"""
        if hasattr(self.db, "rollback"):
            if hasattr(self.db, "__aenter__"):  # AsyncSession
                await self.db.rollback()
            else:  # Session
                self.db.rollback()
        else:
            logger.warning("Database session not available for rollback")

    def sync_commit(self):
        """동기 커밋 (Session 사용 시)"""
        if hasattr(self.db, "commit"):
            self.db.commit()
        else:
            logger.warning("Database session not available for commit")

    def sync_rollback(self):
        """동기 롤백 (Session 사용 시)"""
        if hasattr(self.db, "rollback"):
            self.db.rollback()
        else:
            logger.warning("Database session not available for rollback")

    async def refresh(self, instance):
        """인스턴스 새로고침"""
        if hasattr(self.db, "refresh"):
            if hasattr(self.db, "__aenter__"):  # AsyncSession
                await self.db.refresh(instance)
            else:  # Session
                self.db.refresh(instance)

    def sync_refresh(self, instance):
        """동기 인스턴스 새로고침"""
        if hasattr(self.db, "refresh"):
            self.db.refresh(instance)


class AsyncBaseService(BaseService):
    """비동기 서비스 전용 기본 클래스"""

    def __init__(self, db: AsyncSession):
        """
        비동기 서비스 초기화

        Args:
            db: AsyncSession
        """
        super().__init__(db)


class SyncBaseService(BaseService):
    """동기 서비스 전용 기본 클래스"""

    def __init__(self, db: Session):
        """
        동기 서비스 초기화

        Args:
            db: Session
        """
        super().__init__(db)
