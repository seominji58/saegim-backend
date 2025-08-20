"""
데이터베이스 연결 설정
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.core.config import get_settings
from app.models.base import Base

settings = get_settings()

# PostgreSQL 엔진 생성
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    pool_pre_ping=True,
    echo=settings.database_echo,
    connect_args={
        "sslmode": settings.database_ssl_mode,
        "connect_timeout": 10,
    }
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables() -> None:
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성"""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_session_context():
    """컨텍스트 매니저로 사용할 수 있는 세션 팩토리"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()