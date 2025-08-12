"""
데이터베이스 연결 설정
"""
from sqlmodel import SQLModel, create_engine, Session
from app.core.config import get_settings

settings = get_settings()

# PostgreSQL 엔진 생성
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug  # 쿼리 로깅
)


def create_db_and_tables():
    """데이터베이스 테이블 생성"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """데이터베이스 세션 의존성"""
    with Session(engine) as session:
        yield session