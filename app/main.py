"""
새김 백엔드 FastAPI 애플리케이션
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

import logging
from datetime import datetime

from app.core.env_config import load_env_file
from app.core.config import get_settings

# 환경 변수 먼저 로드
load_env_file()
from app.api import health, router as api_router
from app.api.auth.google import router as google_router
from app.db.database import create_db_and_tables

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title=settings.app_name,
    description="감성 AI 다이어리 백엔드",
    version=settings.version,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 프로덕션 환경에서만 적용되는 미들웨어
if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(HTTPSRedirectMiddleware)

# Gzip 압축
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "내부 서버 오류가 발생했습니다.",
            "timestamp": datetime.now().isoformat(),
        }
    )

# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    # 데이터베이스 테이블 생성
    create_db_and_tables()

# 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    # 필요한 정리 작업 수행
    pass

# 기본 라우트
@app.get("/", tags=["root"])
async def root():
    return {"message": "새김 API에 오신 것을 환영합니다!"}

# 상태 확인 라우트
@app.get("/status", tags=["status"])
async def status():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.version,
        "environment": settings.environment
    }

# API 라우터 등록
app.include_router(api_router, prefix="/api")  # 일반 API 라우터 (prefix 포함)
app.include_router(google_router)  # Google OAuth 라우터 (prefix 없음)
