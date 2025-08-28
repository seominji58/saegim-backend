"""
애플리케이션 생명주기 관리
FastAPI lifespan context manager
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import create_db_and_tables

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리

    시작 시:
    - 데이터베이스 테이블 생성
    - 필요한 초기화 작업 수행

    종료 시:
    - 연결 종료 및 리소스 정리
    """
    # === 시작 이벤트 ===
    logger.info("애플리케이션 시작 중...")

    try:
        # 데이터베이스 테이블 생성
        create_db_and_tables()
        logger.info("✅ 데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.warning(f"⚠️ 데이터베이스 연결 실패: {e}")
        logger.info("데이터베이스 없이 서버를 시작합니다.")

    # 기타 초기화 작업 (필요 시 추가)
    # - Redis 연결 확인
    # - 외부 API 연결 테스트
    # - 백그라운드 태스크 시작

    logger.info("🚀 애플리케이션 시작 완료")

    yield  # 애플리케이션 실행

    # === 종료 이벤트 ===
    logger.info("🛑 애플리케이션 종료 중...")

    # 정리 작업 수행
    # - 데이터베이스 연결 종료
    # - Redis 연결 종료
    # - 백그라운드 태스크 중지
    # - 임시 파일 정리

    logger.info("✅ 애플리케이션 종료 완료")
