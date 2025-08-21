"""
API 라우터
"""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.auth.google import router as google_router
from app.api.auth.logout import router as logout_router
from app.api.auth.signup import router as signup_router
from app.api.diary import router as diary_router
from app.api.fcm import router as fcm_router

router = APIRouter()

router.include_router(health_router)
router.include_router(diary_router, prefix="/api/diary")
router.include_router(fcm_router, prefix="/api/fcm")

# Auth 라우터들을 /api/auth prefix로 통일
router.include_router(google_router, prefix="/api/auth")
router.include_router(logout_router, prefix="/api/auth")
router.include_router(signup_router, prefix="/api/auth")
