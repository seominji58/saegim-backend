"""
API 라우터
"""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.auth.google import router as google_router
from app.api.auth.logout import router as logout_router
from app.api.auth.signup import router as signup_router
from app.api.auth.profile import router as profile_router
from app.api.auth.change_email import router as change_email_router
from app.api.auth.change_password import router as change_password_router
from app.api.auth.refresh import router as refresh_router
from app.api.auth.forgot_password import router as forgot_password_router
from app.api.auth.withdraw import router as withdraw_router
from app.api.auth.restore import router as restore_router
from app.api.admin.cleanup import router as cleanup_router
from app.api.diary import router as diary_router
from app.api.notification import router as notification_router

router = APIRouter()

router.include_router(health_router)
router.include_router(diary_router, prefix="/api/diary")
router.include_router(
    notification_router, prefix="/api/notifications"
)  # 통합된 알림 API

# Auth 라우터들을 /api/auth prefix로 통일
router.include_router(google_router, prefix="/api/auth")
router.include_router(logout_router, prefix="/api/auth")
router.include_router(signup_router, prefix="/api/auth")
router.include_router(profile_router, prefix="/api/auth")
router.include_router(change_email_router, prefix="/api/auth")
router.include_router(change_password_router, prefix="/api/auth")
router.include_router(refresh_router, prefix="/api/auth")
router.include_router(forgot_password_router, prefix="/api/auth/forgot-password")
router.include_router(withdraw_router, prefix="/api/auth")
router.include_router(restore_router, prefix="/api/auth")
router.include_router(cleanup_router, prefix="/api/admin")
