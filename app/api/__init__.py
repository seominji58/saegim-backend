"""
API 라우터
"""
from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.auth.google import router as google_router

router = APIRouter()

router.include_router(health_router)
router.include_router(google_router)