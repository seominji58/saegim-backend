"""
트랜잭션 관리 컨텍스트 매니저
데이터베이스 세션의 자동 커밋/롤백을 제공
"""

import logging
from collections.abc import Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TransactionManager:
    """트랜잭션 관리 유틸리티 클래스"""

    @staticmethod
    @contextmanager
    def transaction(session: Session) -> Generator[Session, None, None]:
        """동기 트랜잭션 컨텍스트 매니저

        Args:
            session: 데이터베이스 세션

        Yields:
            Session: 트랜잭션이 관리되는 세션

        Example:
            with TransactionManager.transaction(session) as tx:
                tx.add(user)
                # 자동 커밋 또는 예외 발생시 롤백
        """
        try:
            yield session
            session.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise

    @staticmethod
    @asynccontextmanager
    async def async_transaction(session: AsyncSession) -> AsyncSession:
        """비동기 트랜잭션 컨텍스트 매니저

        Args:
            session: 비동기 데이터베이스 세션

        Yields:
            AsyncSession: 트랜잭션이 관리되는 비동기 세션

        Example:
            async with TransactionManager.async_transaction(session) as tx:
                await tx.add(user)
                # 자동 커밋 또는 예외 발생시 롤백
        """
        try:
            yield session
            await session.commit()
            logger.debug("Async transaction committed successfully")
        except Exception as e:
            await session.rollback()
            logger.error(f"Async transaction rolled back due to error: {e}")
            raise

    @staticmethod
    def safe_execute(session: Session, operation: callable, *args, **kwargs) -> Any:
        """트랜잭션 안전 실행 (동기)

        Args:
            session: 데이터베이스 세션
            operation: 실행할 함수
            *args, **kwargs: 함수 인자들

        Returns:
            Any: 함수 실행 결과
        """
        with TransactionManager.transaction(session):
            return operation(*args, **kwargs)

    @staticmethod
    async def async_safe_execute(
        session: AsyncSession, operation: callable, *args, **kwargs
    ) -> Any:
        """트랜잭션 안전 실행 (비동기)

        Args:
            session: 비동기 데이터베이스 세션
            operation: 실행할 비동기 함수
            *args, **kwargs: 함수 인자들

        Returns:
            Any: 함수 실행 결과
        """
        async with TransactionManager.async_transaction(session):
            return await operation(*args, **kwargs)


def transaction_required(func):
    """트랜잭션 데코레이터 (동기)"""

    def wrapper(self, *args, **kwargs):
        if not hasattr(self, "db") or self.db is None:
            raise ValueError("Database session is required for transaction")

        with TransactionManager.transaction(self.db):
            return func(self, *args, **kwargs)

    return wrapper


def async_transaction_required(func):
    """트랜잭션 데코레이터 (비동기)"""

    async def wrapper(self, *args, **kwargs):
        if not hasattr(self, "db") or self.db is None:
            raise ValueError("Database session is required for transaction")

        async with TransactionManager.async_transaction(self.db):
            return await func(self, *args, **kwargs)

    return wrapper
