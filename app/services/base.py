"""
통일된 서비스 기본 클래스 (리팩토링됨)
중복된 트랜잭션 관리 코드 제거 및 컨텍스트 매니저 통합
"""

import logging
from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class BaseService:
    """모든 서비스의 기본 클래스"""

    def __init__(self, db: Union[AsyncSession, Session, None] = None):
        """
        서비스 초기화

        Args:
            db: 데이터베이스 세션 (AsyncSession 또는 Session)
        """
        self.db = db
        self._is_async_session = isinstance(db, AsyncSession)

    def transaction(self):
        """트랜잭션 컨텍스트 매니저 반환

        Returns:
            트랜잭션 컨텍스트 매니저 (동기 또는 비동기)

        Example:
            # 동기
            with service.transaction() as tx:
                tx.add(user)

            # 비동기
            async with service.transaction() as tx:
                await tx.add(user)
        """
        if self.db is None:
            raise ValueError("Database session not available")

        if self._is_async_session:
            return TransactionManager.async_transaction(self.db)
        else:
            return TransactionManager.transaction(self.db)

    def safe_execute(self, operation: callable, *args, **kwargs):
        """트랜잭션 안전 실행

        Args:
            operation: 실행할 함수
            *args, **kwargs: 함수 인자들

        Returns:
            함수 실행 결과
        """
        if self.db is None:
            raise ValueError("Database session not available")

        if self._is_async_session:
            return TransactionManager.async_safe_execute(
                self.db, operation, *args, **kwargs
            )
        else:
            return TransactionManager.safe_execute(self.db, operation, *args, **kwargs)

    def refresh(self, instance):
        """인스턴스 새로고침 (동기/비동기 자동 감지)"""
        if self.db is None:
            logger.warning("Database session not available for refresh")
            return

        if self._is_async_session:
            # 비동기는 호출하는 곳에서 await 해야 함
            return self.db.refresh(instance)
        else:
            self.db.refresh(instance)


# 레거시 호환성을 위한 별칭 (향후 제거 예정)
AsyncBaseService = BaseService
SyncBaseService = BaseService
