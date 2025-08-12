"""
의존성 주입 (Dependency Injection)
"""
from typing import Generator
from app.db.database import get_session
from sqlmodel import Session


def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성"""
    return get_session()