"""
새김 백엔드 FastAPI 애플리케이션
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api import router as api_router
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.env_config import load_env_file
from app.core.lifespan import lifespan
from app.db.database import get_session
from app.models.user import User
from app.schemas.base import BaseResponse
from app.schemas.create_diary import CreateDiaryRequest
from app.services.ai_log import AIService
from app.services.create_diary import diary_service

# 환경 변수 먼저 로드
load_env_file()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


# lifespan은 app.core.lifespan에서 import


# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title=settings.app_name,
    description="감성 AI 다이어리 백엔드",
    version=settings.version,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# MinIO를 사용하므로 정적 파일 서빙 불필요


def custom_openapi():
    """
    Swagger UI에 JWT Bearer Token 인증 버튼을 추가하기 위한 OpenAPI 스키마 커스터마이징
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # JWT Bearer Token Security Scheme 추가
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer {token}'",
        }
    }

    # 모든 보호된 엔드포인트에 기본 보안 적용
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            # 인증이 필요없는 엔드포인트 제외 (로그인, 회원가입, health 등)
            if (
                path.startswith("/api/auth/")
                or path in ["/", "/status", "/docs", "/redoc", "/openapi.json"]
                or path.startswith("/health")
            ):
                continue

            # 기타 모든 엔드포인트에 Bearer 토큰 보안 적용
            if "security" not in openapi_schema["paths"][path][method]:
                openapi_schema["paths"][path][method]["security"] = [{"bearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# 커스텀 OpenAPI 스키마 적용
app.openapi = custom_openapi

# 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # .env에서 설정된 origins 사용
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],  # 보안 강화: 구체적 헤더만 허용
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


# 기존 deprecated 이벤트 핸들러 제거됨 - lifespan으로 대체


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
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
    db=Depends(get_session),
):
    # AI 사용 로그 생성 로직
    service = diary_service(db)
    return await service.create_ai_usage_log(
        user_id,
        api_type,
        session_id,
        regeneration_count,
        tokens_used,
        request_data,
        response_data,
    )


# AI 텍스트 생성 API
@app.post("/api/ai-generate", tags=["ai"])
async def generate_ai_text(
    data: CreateDiaryRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_session),
):
    ai_service = AIService(db)
    result = await ai_service.generate_ai_text(current_user.id, data)
    print("result", result)
    return BaseResponse(data=result)


# API 라우터 등록
app.include_router(api_router)  # 일반 API 라우터 (prefix 포함)
