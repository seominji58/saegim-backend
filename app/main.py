"""
새김 백엔드 FastAPI 애플리케이션
"""

from fastapi import FastAPI
from app.core.config import get_settings
from app.api import health

settings = get_settings()

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title=settings.app_name,
    description="감성 AI 다이어리 백엔드",
    version=settings.version,
)

# 라우터 등록
app.include_router(health.router, tags=["health"])
