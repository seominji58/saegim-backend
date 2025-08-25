"""
새김 백엔드 FastAPI 애플리케이션
"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.core.env_config import load_env_file
from app.core.config import get_settings
from app.core.deps import get_db, get_current_user
from app.db.database import get_session
from app.models.user import User

# 환경 변수 먼저 로드
load_env_file()
from app.api import health, router as api_router
from app.db.database import create_db_and_tables
from app.schemas.create_diary import CreateDiaryRequest
from app.schemas.base import BaseResponse

# AI 사용 로그 생성 서비스 
from app.services.create_diary import diary_service

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
    allow_origins=settings.cors_origins,  # .env에서 설정된 origins 사용
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
        },
    )


# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    # 데이터베이스 테이블 생성 (임시로 비활성화)
    try:
        create_db_and_tables()
    except Exception as e:
        logger.warning(f"데이터베이스 연결 실패: {e}")
        logger.info("데이터베이스 없이 서버를 시작합니다.")


# 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    # 필요한 정리 작업 수행
    pass


# 기본 라우트
@app.get("/", tags=["root"])
async def root():
    return {"message": "새김 API에 오신 것을 환영합니다!"}


# 기존 auth 경로를 새로운 api/auth 경로로 리다이렉트
@app.get("/auth/google/login", tags=["redirect"])
async def redirect_google_login():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/api/auth/google/login", status_code=307)


@app.get("/auth/google/callback", tags=["redirect"])
async def redirect_google_callback():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/api/auth/google/callback", status_code=307)


@app.get("/auth/google/token/{token_id}", tags=["redirect"])
async def redirect_google_token(token_id: str):
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"/api/auth/google/token/{token_id}", status_code=307)


@app.post("/auth/logout", tags=["redirect"])
async def redirect_logout():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/api/auth/logout", status_code=307)


# 상태 확인 라우트
@app.get("/status", tags=["status"])
async def status():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
    }

# ai_log 생성 라우트
@app.post("/api/ai-usage-log", tags=["ai"])
async def create_ai_usage_log(
    user_id: str,
    api_type: str,
    session_id: str,
    regeneration_count: int = 1,
    tokens_used: int = 0,
    request_data: dict = None,
    response_data: dict = None,
    db=Depends(get_session)
):
    # AI 사용 로그 생성 로직
    service = diary_service(db)
    return await service.create_ai_usage_log(
        user_id, api_type, session_id, regeneration_count, 
        tokens_used, request_data, response_data
    )

# saegim-backend/app/main.py
from app.services.ai_log import AIService

# AI 텍스트 생성 API
@app.post("/api/ai-generate", tags=["ai"])
async def generate_ai_text(  
    data: CreateDiaryRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_session)
):
    ai_service = AIService(db)
    result = await ai_service.generate_ai_text(current_user.id, data)
    print('result', result)
    return BaseResponse(data=result)

# API 라우터 등록
app.include_router(api_router)  # 일반 API 라우터 (prefix 포함)
